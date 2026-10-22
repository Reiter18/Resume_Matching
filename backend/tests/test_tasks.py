from sqlalchemy import select

from app import tasks
from app.celery_app import celery_app
from app.models import DeadLetter


def test_ingest_task_calls_run_source(db, monkeypatch):
    monkeypatch.setattr(tasks, "run_source", lambda session, name, max_pages: 7)
    res = tasks.ingest_source.delay("arbeitnow", 2)
    assert res.get() == 7


def test_unexpected_failure_goes_to_dead_letters(db, monkeypatch):
    def boom(session, name, max_pages):
        raise ValueError("баг в коде")

    monkeypatch.setattr(tasks, "run_source", boom)
    res = tasks.ingest_source.delay("arbeitnow")
    assert res.failed()
    dl = db.scalar(select(DeadLetter))
    assert dl is not None and "баг в коде" in dl.error and dl.args["args"] == ["arbeitnow"]


def test_beat_schedule_and_routing_configured():
    assert "ingest-arbeitnow" in celery_app.conf.beat_schedule
    assert celery_app.conf.task_routes["app.tasks.ingest_source"]["queue"] == "ingest"
    assert celery_app.conf.task_acks_late is True
