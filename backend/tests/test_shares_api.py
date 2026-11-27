from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.main import app
from app.models import ShareLink
from app.sharing import hash_token
from tests.test_auth import login_headers


@pytest.fixture()
def client(db):
    return TestClient(app)


def test_share_link_stores_only_hash_and_can_be_revoked(client, db):
    a, b = login_headers(client, "a@example.com"), login_headers(client, "b@example.com")
    assert client.get("/shares").status_code == 401

    body = {
        "title": "Для друга",
        "allowed_fields": ["score_breakdown", "matches"],
        "min_score": 70,
        "expires_in_days": 3,
    }
    res = client.post("/shares", json=body, headers=a)
    assert res.status_code == 201
    created = res.json()
    token = created.pop("token")
    assert (
        created["allowed_fields"] == ["matches", "score_breakdown"]
        and created["min_score"] == 70
        and created["active"] is True
    )

    row = db.scalar(select(ShareLink))
    assert row.token_hash == hash_token(token) and token not in str(vars(row))  # в базе только хеш
    assert abs((row.expires_at - datetime.now(timezone.utc)) - timedelta(days=3)) < timedelta(minutes=1)

    listed = client.get("/shares", headers=a).json()
    assert [x["id"] for x in listed] == [created["id"]] and "token" not in listed[0]
    assert client.get("/shares", headers=b).json() == []
    assert client.delete(f"/shares/{created['id']}", headers=b).status_code == 404  

    revoked = client.delete(f"/shares/{created['id']}", headers=a).json()
    assert revoked["active"] is False and revoked["revoked_at"] is not None
    assert (
        client.delete(f"/shares/{created['id']}", headers=a).json()["revoked_at"] == revoked["revoked_at"]
    ) 


def test_share_link_validation_and_active_limit(client, db):
    h = login_headers(client)
    bad = [
        {"allowed_fields": ["resume_text"]},
        {"expires_in_days": 0},
        {"expires_in_days": 366},
        {"min_score": 101},
        {"title": "x" * 101},
    ]
    for body in bad:
        assert client.post("/shares", json=body, headers=h).status_code == 422, body
    assert client.post("/shares", json={}, headers=h).json()["allowed_fields"] == [
        "matches"
    ]  

    for _ in range(19):
        assert client.post("/shares", json={}, headers=h).status_code == 201
    assert client.post("/shares", json={}, headers=h).status_code == 409  

    oldest = client.get("/shares", headers=h).json()[-1]["id"]
    client.delete(f"/shares/{oldest}", headers=h)
    assert client.post("/shares", json={}, headers=h).status_code == 201  

    link = db.scalars(select(ShareLink).where(ShareLink.revoked_at.is_(None))).first()
    link.expires_at = datetime.now(timezone.utc) - timedelta(days=1)  
    db.commit()
    assert client.post("/shares", json={}, headers=h).status_code == 201
    assert [x["active"] for x in client.get("/shares", headers=h).json()].count(False) == 2  
