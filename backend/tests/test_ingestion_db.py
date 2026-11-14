from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import func, select

from app import ingestion
from app.connectors import REGISTRY, BaseConnector, SourceUnavailable
from app.ingestion import circuit_open, run_source
from app.models import Source, Vacancy
from app.schemas import NormalizedVacancy


def make_vacancy(ext: str, title: str = "Python Dev") -> NormalizedVacancy:
    return NormalizedVacancy(
        source="fake",
        external_id=ext,
        url="https://x/" + ext,
        title=title,
        company="Acme",
        description_text="desc",
        published_at=datetime(2026, 10, 1, tzinfo=timezone.utc),
    )


class FakeConnector(BaseConnector):
    name = "fake"
    base_url = "https://fake"
    items: list = []
    fail = False
    calls = 0

    def fetch(self, max_pages=1):
        FakeConnector.calls += 1
        if FakeConnector.fail:
            raise SourceUnavailable("fake is down")
        yield from FakeConnector.items


@pytest.fixture()
def fake(monkeypatch):
    FakeConnector.items, FakeConnector.fail, FakeConnector.calls = [make_vacancy("1"), make_vacancy("2")], False, 0
    monkeypatch.setitem(REGISTRY, "fake", FakeConnector)
    return FakeConnector


def count(db):
    return db.scalar(select(func.count()).select_from(Vacancy))


def test_upsert_is_idempotent_and_updates(db, fake):
    assert run_source(db, "fake") == 2 and count(db) == 2
    fake.items = [make_vacancy("1", "Senior Python Dev"), make_vacancy("2")]
    run_source(db, "fake")
    assert count(db) == 2  
    assert db.scalar(select(Vacancy.title).where(Vacancy.external_id == "1")) == "Senior Python Dev"
    assert db.scalar(select(Source.last_success_at)) is not None


def test_failure_is_recorded_and_does_not_raise(db, fake):
    run_source(db, "fake")
    fake.fail = True
    assert run_source(db, "fake") == 0
    src = db.scalar(select(Source))
    assert src.consecutive_failures == 1 and "down" in src.last_error and count(db) == 2  


def test_circuit_breaker_opens_and_closes(db, fake, monkeypatch):
    monkeypatch.setattr(ingestion.settings, "breaker_threshold", 3)
    fake.fail = True
    for _ in range(3):
        run_source(db, "fake")
    calls = fake.calls
    run_source(db, "fake")  
    assert fake.calls == calls
    src = db.scalar(select(Source))
    later = src.last_failure_at + timedelta(seconds=ingestion.settings.breaker_cooldown_seconds + 1)
    assert circuit_open(src) and not circuit_open(src, now=later)
