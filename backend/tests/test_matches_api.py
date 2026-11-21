from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, select

from app import tasks
from app.main import app
from app.matching import match_resume
from app.models import Resume, Source, Vacancy, VacancyMatch
from app.skills import seed_skills
from tests.test_auth import login_headers

NOW = datetime(2026, 10, 1, tzinfo=timezone.utc)


def add_vacancy(db, source, i, title, skills, fmt="unknown"):
    db.add(Vacancy(
        source_id=source.id, external_id=str(i), url="https://x", title=title, company="Acme", description_text="d",
        published_at=NOW, content_hash=str(i), dedup_key=str(i), company_key="acme", skills=skills, work_format=fmt,
    ))  # fmt: skip


@pytest.fixture()
def client(db):
    seed_skills(db)
    src = Source(name="fake", base_url="https://fake")
    db.add(src)
    db.flush()
    for i, (title, skills, fmt) in enumerate(
        [("A", ["python", "docker"], "remote"), ("B", ["java"], "onsite"), ("C", ["python", "kubernetes"], "unknown")], start=1
    ):
        add_vacancy(db, src, i, title, skills, fmt)
    db.commit()
    return TestClient(app)


def titles(client, h):
    return [m["vacancy"]["title"] for m in client.get("/matches", headers=h).json()["items"]]


def test_matches_ranked_filtered_by_must_have_and_need_resume(client):
    h = login_headers(client)
    assert client.get("/matches", headers=h).status_code == 404  
    assert client.get("/matches").status_code == 401

    client.post("/resumes/text", json={"text": "Backend developer. Python, Docker."}, headers=h)
    page = client.get("/matches", headers=h).json()
    assert [m["vacancy"]["title"] for m in page["items"]] == ["A", "C", "B"]
    assert page["items"][0]["score"] == 100 and page["items"][0]["criteria"]["skills"]["matched"] == ["python", "docker"]
    assert client.get("/matches?min_score=40", headers=h).json()["total"] == 2

    client.put("/me/preferences", json={"work_formats": ["remote"], "must_have": ["work_format"]}, headers=h)
    assert titles(client, h) == ["A", "C"]  


def test_single_match_hidden_flag_and_pending(client, db):
    h = login_headers(client)
    client.post("/resumes/text", json={"text": "Backend developer. Python, Docker."}, headers=h)
    client.put("/me/preferences", json={"work_formats": ["remote"], "must_have": ["work_format"]}, headers=h)
    ids = {v.title: v.id for v in db.scalars(select(Vacancy))}

    a = client.get(f"/matches/{ids['A']}", headers=h).json()
    assert a["score"] == 100 and a["hidden"] is False and a["criteria"]["work_format"]["status"] == "match"
    assert client.get(f"/matches/{ids['B']}", headers=h).json()["hidden"] is True  
    assert client.get("/matches/9999", headers=h).status_code == 404

    db.execute(delete(VacancyMatch))  
    db.commit()
    assert client.get("/matches", headers=h).json()["pending"] is True
    assert client.get(f"/matches/{ids['A']}", headers=h).status_code == 404


def test_pipeline_recomputes_only_new_and_changed(client, db):
    client.post("/resumes/text", json={"text": "Python, Docker."}, headers=login_headers(client))
    resume = db.scalar(select(Resume))
    assert match_resume(db, resume, only_new=True) == 0  

    source = db.scalar(select(Source))
    add_vacancy(db, source, 4, "D", ["python"])
    add_vacancy(db, source, 5, "E", ["python"])
    db.scalar(select(Vacancy).where(Vacancy.title == "E")).canonical_id = db.scalar(select(Vacancy.id).where(Vacancy.title == "A"))
    db.commit()
    assert match_resume(db, resume, only_new=True) == 1  

    db.scalar(select(Vacancy).where(Vacancy.title == "A")).fetched_at = datetime.now(timezone.utc) + timedelta(minutes=1)
    db.commit()
    assert match_resume(db, resume, only_new=True) == 1  
    assert match_resume(db, resume) == 4  


def test_enqueue_does_not_raise_when_broker_is_down(monkeypatch):
    def boom(*args, **kwargs):
        raise ConnectionError("redis недоступен")

    monkeypatch.setattr(tasks.match_resume_task, "delay", boom)
    tasks.enqueue_match(1)  
