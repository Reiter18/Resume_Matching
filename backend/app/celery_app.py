from celery import Celery

from app.config import settings
from app.connectors import REGISTRY

celery_app = Celery("jobmatch", broker=settings.redis_url, include=["app.tasks"])
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    broker_connection_retry_on_startup=True,
    task_default_queue="default",
    task_routes={"app.tasks.ingest_source": {"queue": "ingest"}},
    beat_schedule={
        f"ingest-{name}": {
            "task": "app.tasks.ingest_source",
            "schedule": settings.ingest_interval_seconds,
            "args": [name],
        }
        for name in REGISTRY
    },
)
