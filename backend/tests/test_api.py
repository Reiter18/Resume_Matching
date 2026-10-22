from fastapi.testclient import TestClient

from app.main import app
from app.models import Source

client = TestClient(app)


def test_health_reports_components():
    body = client.get("/health").json()
    assert set(body) == {"status", "db", "redis"}


def test_sources_lists_state(db):
    db.add(Source(name="arbeitnow", base_url="https://x", consecutive_failures=2, last_error="HTTP 500"))
    db.commit()
    data = client.get("/sources").json()
    assert data[0]["name"] == "arbeitnow" and data[0]["consecutive_failures"] == 2
