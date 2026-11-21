import logging

from celery import Task
from sqlalchemy.exc import OperationalError

from app.celery_app import celery_app
from app.db import SessionLocal
from app.dedup import dedup_all
from app.ingestion import run_source
from app.matching import match_all, match_resume
from app.models import DeadLetter, Resume

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
        saved = run_source(session, name, max_pages)
    if saved:
        dedup_vacancies.delay()  
    return saved


@celery_app.task(
    bind=True,
    base=DeadLetterTask,
    name="app.tasks.dedup_vacancies",
    autoretry_for=(OperationalError,),
    retry_backoff=True,
    max_retries=3,
)
def dedup_vacancies(self) -> dict:
    with SessionLocal() as session:
        stats = dedup_all(session)
    match_new.delay() 
    return {"checked": stats.checked, "duplicates": stats.duplicates}


@celery_app.task(
    bind=True,
    base=DeadLetterTask,
    name="app.tasks.match_new",
    autoretry_for=(OperationalError,),
    retry_backoff=True,
    max_retries=3,
)
def match_new(self) -> int:
    with SessionLocal() as session:
        return match_all(session, only_new=True)


@celery_app.task(
    bind=True,
    base=DeadLetterTask,
    name="app.tasks.match_resume",
    autoretry_for=(OperationalError,),
    retry_backoff=True,
    max_retries=3,
)
def match_resume_task(self, resume_id: int) -> int:
    with SessionLocal() as session:
        resume = session.get(Resume, resume_id)
        return match_resume(session, resume) if resume else 0


def enqueue_match(resume_id: int) -> None:
    try:
        match_resume_task.delay(resume_id)
    except Exception:
        log.warning("не удалось поставить пересчёт резюме %s в очередь", resume_id, exc_info=True)
