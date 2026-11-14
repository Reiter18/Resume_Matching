import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import case, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.config import settings
from app.connectors import REGISTRY, SourceUnavailable
from app.extract import SkillExtractor, vacancy_params
from app.models import Source, Vacancy
from app.skills import SkillDictionary

log = logging.getLogger(__name__)

PARAMS = ("work_format", "schedule", "hours_per_week", "experience_years_min", "salary_min", "salary_max", "salary_currency")


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

    extractor = SkillExtractor(SkillDictionary.load(session).terms())
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
                employment_types=v.employment_types,
                description_text=v.description_text,
                tags=v.tags,
                skills=extractor.find(f"{v.title}\n{' '.join(v.tags)}\n{v.description_text}"),
                published_at=v.published_at,
                content_hash=v.content_hash,
                dedup_key=v.dedup_key,
                company_key=v.company_key,
                **vacancy_params(v),
            )
            changed = Vacancy.content_hash != stmt.excluded.content_hash
            stmt = stmt.on_conflict_do_update(
                constraint="uq_vacancy_source_external",
                set_={
                    "title": stmt.excluded.title,
                    "description_text": stmt.excluded.description_text,
                    "content_hash": stmt.excluded.content_hash,
                    "company_key": stmt.excluded.company_key,
                    **{c: getattr(stmt.excluded, c) for c in ("skills", *PARAMS)},
                    "fetched_at": datetime.now(timezone.utc),
                    "dedup_checked_at": case((changed, None), else_=Vacancy.dedup_checked_at),
                    "canonical_id": case((changed, None), else_=Vacancy.canonical_id),
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
