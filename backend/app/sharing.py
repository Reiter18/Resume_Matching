import hashlib
import secrets
from datetime import datetime, timezone
from typing import Optional

ALLOWED_FIELDS = {"matches", "score_breakdown", "skills", "salary_expectations"}
DEFAULT_FIELDS = ["matches"]


def new_token() -> str:
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def validate_fields(fields: list[str]) -> list[str]:
    bad = set(fields) - ALLOWED_FIELDS
    if bad:
        raise ValueError(f"нельзя открывать по ссылке: {sorted(bad)}")
    return sorted(set(fields)) or DEFAULT_FIELDS


def is_active(expires_at: Optional[datetime], revoked_at: Optional[datetime], now: Optional[datetime] = None) -> bool:
    now = now or datetime.now(timezone.utc)
    return revoked_at is None and (expires_at is None or expires_at > now)


def build_public_payload(matches: list[dict], allowed_fields: list[str], min_score: Optional[float] = None) -> dict:
    """Собирает ответ публичной страницы по белому списку. Каждый match: {title, company, url, score, breakdown, ...}."""
    allowed = set(allowed_fields) & ALLOWED_FIELDS
    items = []
    for m in matches:
        if min_score is not None and m["score"] < min_score:
            continue
        item = {"title": m["title"], "company": m["company"], "url": m["url"], "score": m["score"]}
        if "score_breakdown" in allowed:
            item["breakdown"] = m.get("breakdown")
        items.append(item)
    out = {"matches": items} if "matches" in allowed else {}
    return out
