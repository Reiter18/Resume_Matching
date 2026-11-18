from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models import Source, Vacancy
from app.skills import seed_skills
from tests.test_auth import login_headers


@pytest.fixture()
def client(db):
    seed_skills(db)
    src = Source(name="fake", base_url="https://fake")
    db.add(src)
    db.flush()
    for i, (title, skills, fmt) in enumerate(
        [("A", ["python", "docker"], "remote"), ("B", ["java"], "onsite"), ("C", ["python", "kubernetes"], "unknown")], start=1
    ):
        db.add(Vacancy(
            source_id=src.id, external_id=str(i), url="https://x", title=title, company="Acme", description_text="d",
            published_at=datetime(2026, 10, 1, tzinfo=timezone.utc), content_hash=str(i), dedup_key=str(i), company_key="acme",
            skills=skills, work_format=fmt,
        ))  # fmt: skip
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
