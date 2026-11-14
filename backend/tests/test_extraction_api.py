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
    return TestClient(app)


def test_resume_gets_skills_and_experience_automatically(client):
    h = login_headers(client)
    text = "Backend developer. Опыт работы: 5 лет. Python, Постгрес, Docker."
    r = client.post("/resumes/text", json={"text": text}, headers=h).json()
    assert r["skills"] == ["python", "postgresql", "docker"] and r["experience_years"] == 5.0


def test_vacancy_skill_filter_understands_synonyms(client, db):
    src = Source(name="fake", base_url="https://fake")
    db.add(src)
    db.flush()
    now = datetime(2026, 10, 1, tzinfo=timezone.utc)
    for i, skills in enumerate([["python"], ["java"]], start=1):
        db.add(Vacancy(
            source_id=src.id, external_id=str(i), url="https://x", title=f"Dev {i}", company="Acme", description_text="d",
            published_at=now, content_hash=str(i), dedup_key=str(i), company_key="acme", skills=skills, experience_years_min=2,
        ))  # fmt: skip
    db.commit()
    page = client.get("/vacancies?skill=питон", headers=login_headers(client)).json()
    assert [v["title"] for v in page["items"]] == ["Dev 1"] and page["items"][0]["experience_years_min"] == 2
