import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.main import app
from app.models import Resume, User
from tests.test_auth import login_headers

PASSWORD = "correct-horse-1"


@pytest.fixture()
def client(db):
    return TestClient(app)


def test_update_profile_name(client):
    h = login_headers(client)
    assert client.get("/me", headers=h).json()["full_name"] is None
    r = client.patch("/me", json={"full_name": "  Иван   Петров "}, headers=h)
    assert r.status_code == 200 and r.json()["full_name"] == "Иван Петров"  # пробелы нормализованы
    assert client.patch("/me", json={"full_name": "   "}, headers=h).json()["full_name"] is None
    assert client.patch("/me", json={"full_name": "x" * 101}, headers=h).status_code == 422
    assert client.patch("/me", json={"full_name": "Иван"}).status_code == 401


def test_change_password_flow(client):
    h = login_headers(client)
    new = "brand-new-pass-2"
    assert (
        client.post("/me/password", json={"current_password": "wrong", "new_password": new}, headers=h).status_code
        == 400
    )
    same = client.post("/me/password", json={"current_password": PASSWORD, "new_password": PASSWORD}, headers=h)
    assert same.status_code == 400
    weak = client.post("/me/password", json={"current_password": PASSWORD, "new_password": "short"}, headers=h)
    assert weak.status_code == 422
    ok = client.post("/me/password", json={"current_password": PASSWORD, "new_password": new}, headers=h)
    assert ok.status_code == 204
    assert client.post("/auth/login", json={"email": "user@example.com", "password": PASSWORD}).status_code == 401
    assert client.post("/auth/login", json={"email": "user@example.com", "password": new}).status_code == 200


def test_wrong_password_errors_are_not_401(client):
    h = login_headers(client)
    r = client.post("/me/password", json={"current_password": "nope-nope", "new_password": "another-pass-9"}, headers=h)
    assert r.status_code == 400
    assert client.request("DELETE", "/me", json={"password": "nope-nope"}, headers=h).status_code == 400
    assert client.get("/me", headers=h).status_code == 200  


def test_delete_account_removes_user_and_resume(client, db):
    h = login_headers(client)
    other = login_headers(client, "other@example.com")
    long_text = "Backend developer. " + "Python FastAPI PostgreSQL Docker. " * 5
    client.post("/resumes/text", json={"text": long_text}, headers=h)
    client.post("/resumes/text", json={"text": long_text}, headers=other)

    assert client.request("DELETE", "/me", json={"password": "wrong-pass-1"}, headers=h).status_code == 400
    assert client.request("DELETE", "/me", json={"password": PASSWORD}, headers=h).status_code == 204

    db.expire_all()
    assert db.scalar(select(func.count()).select_from(User)) == 1  
    assert db.scalar(select(func.count()).select_from(Resume)) == 1  
    assert client.get("/me", headers=h).status_code == 401  
    assert client.post("/auth/login", json={"email": "user@example.com", "password": PASSWORD}).status_code == 401
    assert client.get("/me", headers=other).status_code == 200
