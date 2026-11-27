from fastapi.security import HTTPAuthorizationCredentials
from fastapi.testclient import TestClient
from redis.exceptions import ConnectionError

from app import events
from app.main import app
from app.routers.events import stream_user_id
from tests.test_auth import login_headers


def test_event_stream_requires_a_valid_token(db):
    client = TestClient(app)
    assert client.get("/events").status_code == 401
    assert client.get("/events", headers={"Authorization": "Bearer garbage"}).status_code == 401

    headers = login_headers(client)
    token = headers["Authorization"].split()[1]
    user_id = client.get("/me", headers=headers).json()["id"]
    assert stream_user_id(HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)) == user_id


def test_publish_does_not_raise_when_redis_is_down(monkeypatch):
    def boom(*args, **kwargs):
        raise ConnectionError("redis недоступен")

    monkeypatch.setattr(events.Redis, "from_url", boom)
    events.publish(1, {"type": "matches_refreshed"})  
