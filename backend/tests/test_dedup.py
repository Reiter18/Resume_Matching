from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app import tasks
from app.connectors import REGISTRY, BaseConnector
from app.dedup import compare, dedup_all, locations_compatible
from app.ingestion import run_source
from app.main import app
from app.models import Source, Vacancy
from app.schemas import NormalizedVacancy
from tests.test_auth import login_headers

BASE = datetime(2026, 10, 1, tzinfo=timezone.utc)

DESC_A = (
    "We are looking for a Python developer to join our backend team in Berlin. You will build REST APIs with "
    "FastAPI, work with PostgreSQL and Docker, and take part in code reviews. We offer flexible hours, remote work "
    "options and a modern tech stack. Requirements: 2 years of Python experience, good English, team spirit."
)
DESC_B = (
    "Our data platform team needs an engineer who designs ETL pipelines in Airflow, maintains a Spark cluster, and "
    "supports analysts with ClickHouse queries. You will own data quality, write documentation, and mentor juniors. "
    "Requirements: strong SQL, Python scripting, experience with cloud storage and good communication."
)
DESC_RU = (
    "Мы ищем Python-разработчика в команду бэкенда. Вам предстоит разрабатывать REST API на FastAPI, работать с "
    "PostgreSQL и Docker, участвовать в ревью кода. Предлагаем гибкий график, удалённую работу и современный стек."
)


def v(title, desc, location=None, h=None):
    return SimpleNamespace(title=title, description_text=desc, location=location, content_hash=h or title + desc[:20])


LABELED = [
    (v("Python Developer (m/f/d)", DESC_A, "Berlin"), v("Python Developer", DESC_A, "Berlin"), True),
    (v("Junior Python Developer", DESC_A), v("Python Developer (Junior)", DESC_A), True),
    (v("Python Developer", DESC_A), v("Python Developer", DESC_A + " Apply now through our website."), True),
    (v("Python Developer", DESC_A), v("Python Developer", DESC_A.replace("modern tech stack", "up-to-date tech stack").replace("flexible hours", "flexible working hours")), True),
    (v("Python Developer", DESC_A, "Berlin"), v("Python Developer", DESC_A, "Berlin, Germany"), True),
    (v("Python Developer", DESC_A, None), v("Python Developer", DESC_A, "Berlin"), True),
    (v("Backend-Engineer", DESC_A), v("Backend Engineer", DESC_A), True),
    (v("Python-разработчик", DESC_RU), v("Python разработчик (удалённо)", DESC_RU), True),
    (v("Senior Backend Developer Python", DESC_A), v("Senior Python Backend Developer", DESC_A), True),
    (v("Python Developer", DESC_A, "Remote", h="same"), v("Python Developer", DESC_A, "Berlin", h="same"), True),
    (v("Junior Python Developer", DESC_A), v("Senior Python Developer", DESC_A), False),
    (v("Python Developer", DESC_A, "Berlin"), v("Python Developer", DESC_A, "Munich"), False),
    (v("Python Developer", DESC_A), v("Python Developer", DESC_B), False),
    (v("Python Developer", DESC_A), v("Java Developer", DESC_A), False),
    (v("Data Engineer", DESC_B), v("Data Scientist", DESC_B), False),
    (v("Developer 1", DESC_A), v("Developer 2", DESC_A), False),
    (v("Frontend Developer (React)", DESC_A), v("Backend Developer (Python)", DESC_B), False),
    (v("Python Developer", DESC_A, "Berlin"), v("Python Developer", DESC_A, "Hamburg"), False),
    (v("Werkstudent Python", DESC_A), v("Python Developer", DESC_A), False),
    (v("Teamleiter Backend", DESC_A), v("Backend Developer", DESC_A), False),
]  


# работа с БД 


def mk(db, source, ext, title, company, desc, days=0, location=None):
    src = db.scalar(select(Source).where(Source.name == source)) or Source(name=source, base_url="https://" + source)
    db.add(src)
    db.flush()
    n = NormalizedVacancy(
        source=source, external_id=ext, url=f"https://{source}/{ext}", title=title, company=company, location=location,
        description_text=desc, published_at=BASE + timedelta(days=days),
    )  
    row = Vacancy(
        source_id=src.id, external_id=ext, url=n.url, title=n.title, company=n.company, location=n.location,
        description_text=n.description_text, published_at=n.published_at, content_hash=n.content_hash,
        dedup_key=n.dedup_key, company_key=n.company_key, work_format="unknown", employment_types=[], tags=[], skills=[],
    ) 
    db.add(row)
    db.commit()
    return row


def reload(db, *rows):
    db.expire_all()
    return [db.get(Vacancy, r.id) for r in rows]


def test_exact_duplicate_from_other_source_points_to_earliest(db):
    a = mk(db, "arbeitnow", "1", "Python Developer", "Acme GmbH", DESC_A, days=0)
    b = mk(db, "trudvsem", "9", "Python Developer", "Acme", DESC_A, days=2)
    stats = dedup_all(db)
    a, b = reload(db, a, b)
    assert stats.checked == 2 and stats.duplicates == 1
    assert a.canonical_id is None and b.canonical_id == a.id
    assert dedup_all(db).checked == 0  


def test_earliest_publication_stays_canonical_even_if_inserted_later(db):
    late = mk(db, "s1", "1", "Python Developer", "Acme", DESC_A, days=10)
    early = mk(db, "s2", "2", "Python Developer", "Acme", DESC_A, days=1)  
    dedup_all(db)
    late, early = reload(db, late, early)
    assert early.canonical_id is None and late.canonical_id == early.id


def test_different_vacancies_are_not_merged(db):
    rows = [
        mk(db, "s1", "1", "Junior Python Developer", "Acme", DESC_A),
        mk(db, "s1", "2", "Senior Python Developer", "Acme", DESC_A),  
        mk(db, "s1", "3", "Junior Python Developer", "Other Corp", DESC_A),  
        mk(db, "s1", "4", "Junior Python Developer", "Acme", DESC_A, days=200),  
        mk(db, "s1", "5", "Python Developer", "Acme", DESC_B, location="Berlin"),  
    ]
    stats = dedup_all(db)
    assert stats.checked == 5 and stats.duplicates == 0
    assert all(r.canonical_id is None for r in reload(db, *rows))


def test_chain_is_repointed_to_new_original(db):
    a = mk(db, "s1", "1", "Python Developer", "Acme", DESC_A, days=10)
    b = mk(db, "s2", "2", "Python Developer", "Acme", DESC_A, days=11)
    dedup_all(db)
    c = mk(db, "s3", "3", "Python Developer", "Acme", DESC_A, days=1) 
    dedup_all(db)
    a, b, c = reload(db, a, b, c)
    assert c.canonical_id is None and a.canonical_id == c.id and b.canonical_id == c.id 


# изменение вакансии при повторном сборе 


class FakeConnector(BaseConnector):
    name = "s2"
    base_url = "https://s2"
    items: list = []

    def fetch(self, max_pages=1):
        yield from FakeConnector.items


def test_changed_vacancy_is_rechecked_after_new_ingest(db, monkeypatch):
    monkeypatch.setitem(REGISTRY, "s2", FakeConnector)
    original = mk(db, "s1", "1", "Python Developer", "Acme", DESC_A, days=0)
    repost = NormalizedVacancy(
        source="s2", external_id="7", url="https://s2/7", title="Python Developer", company="Acme",
        description_text=DESC_A, published_at=BASE + timedelta(days=1),
    )  
    FakeConnector.items = [repost]
    run_source(db, "s2")
    dedup_all(db)
    row = db.scalar(select(Vacancy).where(Vacancy.external_id == "7"))
    assert row.canonical_id == original.id and row.company_key == "acme"

    run_source(db, "s2")  
    db.expire_all()
    assert db.get(Vacancy, row.id).dedup_checked_at is not None and db.get(Vacancy, row.id).canonical_id == original.id

    FakeConnector.items = [repost.model_copy(update={"description_text": DESC_B})]  
    run_source(db, "s2")
    db.expire_all()
    row = db.get(Vacancy, row.id)
    assert row.dedup_checked_at is None and row.canonical_id is None 
    dedup_all(db)
    assert db.get(Vacancy, row.id).canonical_id is None  


# API, задачи, CLI 


@pytest.fixture()
def client(db):
    return TestClient(app)


def test_list_hides_duplicates_and_detail_lists_other_sources(client, db):
    a = mk(db, "arbeitnow", "1", "Python Developer", "Acme", DESC_A, days=0)
    b = mk(db, "trudvsem", "2", "Python Developer", "Acme", DESC_A, days=1)
    mk(db, "arbeitnow", "3", "Gardener", "Green Ltd", "Garden work " * 20, days=2)
    dedup_all(db)
    h = login_headers(client)
    page = client.get("/vacancies", headers=h).json()
    assert page["total"] == 2 and sorted(i["title"] for i in page["items"]) == ["Gardener", "Python Developer"]

    detail = client.get(f"/vacancies/{a.id}", headers=h).json()
    assert detail["canonical_id"] is None
    assert detail["also_found_at"] == [{"source": "trudvsem", "url": "https://trudvsem/2"}]
    dup = client.get(f"/vacancies/{b.id}", headers=h).json()  
    assert dup["canonical_id"] == a.id and dup["also_found_at"] == [
        {"source": "arbeitnow", "url": "https://arbeitnow/1"}
    ]


def test_dedup_task_and_ingest_triggers_it(db, monkeypatch):
    mk(db, "s1", "1", "Python Developer", "Acme", DESC_A)
    mk(db, "s2", "2", "Python Developer", "Acme", DESC_A, days=1)
    assert tasks.dedup_vacancies.delay().get() == {"checked": 2, "duplicates": 1}

    called = []
    monkeypatch.setattr(tasks, "run_source", lambda session, name, max_pages: 3)
    monkeypatch.setattr(tasks.dedup_vacancies, "delay", lambda: called.append(1))
    tasks.ingest_source.delay("arbeitnow")
    assert called == [1]  
    called.clear()
    monkeypatch.setattr(tasks, "run_source", lambda session, name, max_pages: 0)
    tasks.ingest_source.delay("arbeitnow")
    assert called == [] 


def test_labeled_pairs_and_quality():
    errors, predicted = [], []
    for a, b, expected in LABELED:
        m = compare(a, b)
        predicted.append(m.duplicate)
        if m.duplicate is not expected:
            errors.append(f"{a.title!r} vs {b.title!r}: ожидали {expected}, получили {m}")
    assert not errors, "\n".join(errors)
    tp = sum(p and e for p, (_, _, e) in zip(predicted, LABELED, strict=True))
    assert tp / max(sum(predicted), 1) >= 0.95 and tp / sum(e for *_, e in LABELED) >= 0.9  
    assert locations_compatible("Berlin", "Berlin, Germany") and locations_compatible(None, "Berlin")
    assert not locations_compatible("Berlin", "Munich")
