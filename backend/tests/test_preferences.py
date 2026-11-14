import pytest
from fastapi.testclient import TestClient

from app.main import app
from tests.test_auth import login_headers


@pytest.fixture()
def client(db):
    return TestClient(app)


def test_preferences_default_save_and_private(client):
    a, b = login_headers(client, "a@example.com"), login_headers(client, "b@example.com")
    empty = client.get("/me/preferences", headers=a).json()
    assert empty["work_formats"] == [] and empty["must_have"] == [] and empty["min_salary"] is None

    body = {
        "work_formats": ["remote", "remote", "hybrid"], "locations": [" Berlin ", "", "Berlin"],
        "min_salary": 4000, "salary_currency": "EUR", "min_hours_per_week": 20, "must_have": ["work_format", "salary"],
    }  # fmt: skip
    saved = client.put("/me/preferences", json=body, headers=a)
    assert saved.status_code == 200
    assert saved.json()["work_formats"] == ["remote", "hybrid"] and saved.json()["locations"] == ["Berlin"]
    client.put("/me/preferences", json={**body, "min_salary": 5000}, headers=a)  
    assert client.get("/me/preferences", headers=a).json()["min_salary"] == 5000
    assert client.get("/me/preferences", headers=b).json()["min_salary"] is None
    assert client.get("/me/preferences").status_code == 401


def test_preferences_validation(client):
    h = login_headers(client)
    bad = [
        {"work_formats": ["moon"]},
        {"min_salary": 4000},  
        {"min_hours_per_week": 30, "max_hours_per_week": 20},
        {"must_have": ["salary"]},  
        {"must_have": ["color"]},
    ]
    for body in bad:
        assert client.put("/me/preferences", json=body, headers=h).status_code == 422, body
