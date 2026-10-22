import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.config import settings
from app.connectors import REGISTRY, SourceUnavailable
from app.models import Source, Vacancy

log = logging.getLogger(__name__)


def circuit_open(source: Source, now: Optional[datetime] = None) -> bool:
    now = now or datetime.now(timezone.utc)
    if source.consecutive_failures < settings.breaker_threshold or source.last_failure_at is None:
        return False
    return (now - source.last_failure_at).total_seconds() < settings.breaker_cooldown_seconds


def run_source(session: Session, name: str, max_pages: int = 1) -> int:
    connector = REGISTRY[name]()
    source = session.scalar(select(Source).where(Source.name == name))
    if source is None:
        source = Source(name=name, base_url=connector.base_url)
        session.add(source)
        session.flush()

    if circuit_open(source):
        log.warning("источник %s временно отключён (%s сбоев подряд)", name, source.consecutive_failures)
        return 0

    saved = 0
    try:
        for v in connector.fetch(max_pages=max_pages):
            stmt = insert(Vacancy).values(
                source_id=source.id,
                external_id=v.external_id,
                url=v.url,
                title=v.title,
                company=v.company,
                location=v.location,
                work_format=v.work_format,
                employment_types=v.employment_types,
                schedule=v.schedule,
                hours_per_week=v.hours_per_week,
                experience_years_min=v.experience_years_min,
                salary_min=v.salary_min,
                salary_max=v.salary_max,
                salary_currency=v.salary_currency,
                description_text=v.description_text,
                tags=v.tags,
                published_at=v.published_at,
                content_hash=v.content_hash,
                dedup_key=v.dedup_key,
            )
            stmt = stmt.on_conflict_do_update(
                constraint="uq_vacancy_source_external",
                set_={
                    "title": stmt.excluded.title,
                    "description_text": stmt.excluded.description_text,
                    "content_hash": stmt.excluded.content_hash,
                    "fetched_at": datetime.now(timezone.utc),
                },
            )
            session.execute(stmt)
            saved += 1
        source.consecutive_failures, source.last_error = 0, None
        source.last_success_at = datetime.now(timezone.utc)
    except SourceUnavailable as e:
        source.consecutive_failures += 1
        source.last_failure_at = datetime.now(timezone.utc)
        source.last_error = str(e)
        log.error("источник %s недоступен: %s", name, e)
    session.commit()
    return saved
