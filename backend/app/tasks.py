import logging

from celery import Task
from sqlalchemy.exc import OperationalError

from app.celery_app import celery_app
from app.db import SessionLocal
from app.ingestion import run_source
from app.models import DeadLetter

log = logging.getLogger(__name__)


class DeadLetterTask(Task):
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        log.error("задача %s упала: %s", self.name, exc)
        with SessionLocal() as s:
            s.add(
                DeadLetter(
                    task_name=self.name,
                    task_id=task_id,
                    args={"args": list(args or ()), "kwargs": dict(kwargs or {})},
                    error=repr(exc)[:2000],
                )
            )
            s.commit()


@celery_app.task(
    bind=True,
    base=DeadLetterTask,
    name="app.tasks.ingest_source",
    autoretry_for=(OperationalError,),
    retry_backoff=True,
    retry_backoff_max=300,
    retry_jitter=True,
    max_retries=3,
)
def ingest_source(self, name: str, max_pages: int = 1) -> int:
    with SessionLocal() as session:
        return run_source(session, name, max_pages)
