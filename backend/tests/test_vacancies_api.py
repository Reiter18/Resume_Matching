from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models import Source, Vacancy
from tests.test_auth import login_headers


@pytest.fixture()
def client(db):
    return TestClient(app)


@pytest.fixture()
def vacancies(db):
    src = Source(name="fake", base_url="https://fake")
    db.add(src)
    db.flush()
    base = datetime(2026, 10, 1, tzinfo=timezone.utc)

    def v(i, title, company, **kw):
        defaults = dict(
            source_id=src.id, external_id=str(i), url=f"https://x/{i}", title=title, company=company,
            description_text="desc " + title, published_at=base + timedelta(days=i), content_hash=str(i),
            dedup_key=str(i), work_format="onsite", employment_types=["full_time"], tags=[], skills=[],
        )  # fmt: skip
        return Vacancy(**{**defaults, **kw})

    db.add_all([
        v(1, "Python Developer", "Acme", work_format="remote", salary_min=100000, salary_max=150000),
        v(2, "Java Developer", "Beta", employment_types=["part_time"]),
        v(3, "100% Python_Dev", "Gamma"),
        v(4, "Duplicate Python", "Acme", canonical_id=1),
    ])  # fmt: skip
    db.commit()


def test_list_is_paginated_sorted_and_hides_duplicates(client, vacancies):
    h = login_headers(client)
    page = client.get("/vacancies?limit=2", headers=h).json()
    assert page["total"] == 3 and len(page["items"]) == 2  
    assert page["items"][0]["title"] == "100% Python_Dev"  
    rest = client.get("/vacancies?limit=2&offset=2", headers=h).json()
    assert [i["title"] for i in rest["items"]] == ["Python Developer"]
    assert page["items"][0]["source"] == "fake"
    assert "description_text" not in page["items"][0]  


def test_filters(client, vacancies):
    h = login_headers(client)
    def titles(qs):
        return [i["title"] for i in client.get(f"/vacancies?{qs}", headers=h).json()["items"]] 
    assert titles("q=java") == ["Java Developer"]
    assert titles("q=acme") == ["Python Developer"]
    assert titles("work_format=remote") == ["Python Developer"]
    assert titles("employment_type=part_time") == ["Java Developer"]
    assert titles("min_salary=120000") == ["Python Developer"]
    assert titles("min_salary=999999") == []


def test_search_treats_wildcards_literally(client, vacancies):
    h = login_headers(client)
    r = client.get("/vacancies", params={"q": "%"}, headers=h).json()
    assert [i["title"] for i in r["items"]] == ["100% Python_Dev"]  


def test_invalid_params_rejected(client, vacancies):
    h = login_headers(client)
    assert client.get("/vacancies?limit=1000", headers=h).status_code == 422
    assert client.get("/vacancies?work_format=moon", headers=h).status_code == 422


def test_detail_and_404(client, vacancies, db):
    h = login_headers(client)
    first = client.get("/vacancies?q=java", headers=h).json()["items"][0]
    d = client.get(f"/vacancies/{first['id']}", headers=h).json()
    assert d["description_text"] == "desc Java Developer"
    assert client.get("/vacancies/999999", headers=h).status_code == 404
