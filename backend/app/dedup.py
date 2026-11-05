import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional, Protocol

from rapidfuzz import fuzz
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.models import Vacancy
from app.text_norm import normalize_city, normalize_title, number_tokens, seniority_of

log = logging.getLogger(__name__)

TITLE_SAME = 97  
TITLE_CLOSE = 90  
DESC_AGREE = 75  
DESC_MIN = 55  
DESC_COMPARE_CHARS = 1500
MIN_DESC_LEN = 80
WINDOW_DAYS = 90


class VacancyLike(Protocol):
    title: str
    description_text: str
    location: Optional[str]
    content_hash: str


@dataclass(frozen=True)
class Match:
    duplicate: bool
    title: float = 0.0
    description: Optional[float] = None
    reason: str = ""


def locations_compatible(a: Optional[str], b: Optional[str]) -> bool:
    ca, cb = normalize_city(a), normalize_city(b)
    if not ca or not cb:
        return True
    return ca == cb or ca in cb or cb in ca


def compare(a: VacancyLike, b: VacancyLike) -> Match:
    if not locations_compatible(a.location, b.location):
        return Match(False, reason="разные города")
    if a.content_hash == b.content_hash:
        return Match(True, 100.0, 100.0, "одинаковый хеш содержимого")
    if seniority_of(a.title) != seniority_of(b.title):
        return Match(False, reason="разный уровень (junior/senior/...)")
    if number_tokens(a.title) != number_tokens(b.title):
        return Match(False, reason="разные цифры в названии")

    title = fuzz.token_sort_ratio(normalize_title(a.title), normalize_title(b.title))
    if title < TITLE_CLOSE:
        return Match(False, title, reason="названия различаются")

    da, db = a.description_text[:DESC_COMPARE_CHARS], b.description_text[:DESC_COMPARE_CHARS]
    desc = fuzz.token_sort_ratio(da, db) if min(len(da), len(db)) >= MIN_DESC_LEN else None

    if title >= TITLE_SAME and (desc is None or desc >= DESC_MIN):
        return Match(True, title, desc, "одинаковое название, описания не противоречат")
    if desc is not None and desc >= DESC_AGREE:
        return Match(True, title, desc, "похожие название и описание")
    return Match(False, title, desc, "описания различаются")


@dataclass
class DedupStats:
    checked: int = 0
    duplicates: int = 0


def _link(session: Session, v: Vacancy, c: Vacancy) -> None:
    keep, drop = sorted((v, c), key=lambda x: (x.published_at, x.id))
    drop.canonical_id = keep.id
    session.flush()
    session.execute(update(Vacancy).where(Vacancy.canonical_id == drop.id).values(canonical_id=keep.id))


def dedup_pending(session: Session, batch_size: int = 500) -> DedupStats:
    stats = DedupStats()
    pending = session.scalars(
        select(Vacancy).where(Vacancy.dedup_checked_at.is_(None)).order_by(Vacancy.id).limit(batch_size)
    ).all()
    now = datetime.now(timezone.utc)
    window = timedelta(days=WINDOW_DAYS)
    for v in pending:
        if v.canonical_id is not None: 
            v.dedup_checked_at = now
            stats.checked += 1
            continue
        candidates = session.scalars(
            select(Vacancy).where(
                Vacancy.company_key == v.company_key,
                Vacancy.id != v.id,
                Vacancy.canonical_id.is_(None),
                Vacancy.published_at.between(v.published_at - window, v.published_at + window),
            )
        ).all()
        best, best_score = None, -1.0
        for c in candidates:
            m = compare(v, c)
            if m.duplicate and (m.title + (m.description or 0)) > best_score:
                best, best_score = c, m.title + (m.description or 0)
        if best is not None:
            _link(session, v, best)
            stats.duplicates += 1
        v.dedup_checked_at = now
        stats.checked += 1
    session.commit()
    return stats


def dedup_all(session: Session, batch_size: int = 500) -> DedupStats:
    total = DedupStats()
    while True:
        part = dedup_pending(session, batch_size)
        if part.checked == 0:
            return total
        total.checked += part.checked
        total.duplicates += part.duplicates
