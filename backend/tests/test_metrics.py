from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from app.main import app
from app.models import Source


def test_metrics_in_prometheus_format(db):
    last_ok = datetime.now(timezone.utc) - timedelta(hours=1)
    db.add(Source(name="fake", base_url="https://x", consecutive_failures=2, last_success_at=last_ok))
    db.commit()

    res = TestClient(app).get("/metrics")
    lines = res.text.splitlines()
    assert res.status_code == 200 and res.headers["content-type"].startswith("text/plain")
    assert 'jobmatch_up{component="db"} 1' in lines
    assert "jobmatch_vacancies_total 0" in lines
    assert 'jobmatch_source_consecutive_failures{source="fake"} 2' in lines
    age = next(line for line in lines if line.startswith('jobmatch_source_last_success_age_seconds{source="fake"}'))
    assert 3590 <= int(age.split()[-1]) <= 3700
