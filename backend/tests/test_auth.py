from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.security import create_access_token, decode_access_token, hash_password, verify_password


@pytest.fixture()
def client(db):
    return TestClient(app)


def register(client, email="user@example.com", password="correct-horse-1"):
    return client.post("/auth/register", json={"email": email, "password": password})


def login_headers(client, email="user@example.com", password="correct-horse-1"):
    register(client, email, password)
    token = client.post("/auth/login", json={"email": email, "password": password}).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_register_login_me_flow(client):
    r = register(client)
    assert r.status_code == 201 and r.json()["email"] == "user@example.com"
    assert "password" not in r.text and "hash" not in r.text
    headers = login_headers(client)
    assert client.get("/me", headers=headers).json()["email"] == "user@example.com"


def test_wrong_password_and_unknown_email_look_the_same(client):
    register(client)
    a = client.post("/auth/login", json={"email": "user@example.com", "password": "wrong-password"})
    b = client.post("/auth/login", json={"email": "nobody@example.com", "password": "whatever-123"})
    assert a.status_code == b.status_code == 401 and a.json() == b.json()


def test_protected_endpoints_need_valid_token(client):
    assert client.get("/me").status_code == 401
    assert client.get("/vacancies").status_code == 401
    assert client.get("/resumes/me").status_code == 401
    assert client.get("/me", headers={"Authorization": "Bearer garbage"}).status_code == 401


def test_register_rules(client):
    assert register(client, "Ivan@Example.com").status_code == 201
    assert register(client, "ivan@example.COM").status_code == 409  
    login = client.post("/auth/login", json={"email": "IVAN@example.com", "password": "correct-horse-1"})
    assert login.status_code == 200
    assert register(client, "other@example.com", "short").status_code == 422
    assert register(client, "not-an-email").status_code == 422


def test_tokens_and_password_hashing():
    old = create_access_token(1, now=datetime.now(timezone.utc) - timedelta(hours=3))
    assert decode_access_token(old) is None  # просрочен
    good = create_access_token(1)
    assert decode_access_token(good) == 1 and decode_access_token(good[:-3] + "abc") is None  
    h = hash_password("my-secret-pass")
    assert h != "my-secret-pass" and verify_password("my-secret-pass", h) and not verify_password("other", h)
