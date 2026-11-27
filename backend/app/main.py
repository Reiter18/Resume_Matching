import logging
from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from redis import Redis
from sqlalchemy import func, select, text

from app.config import settings
from app.db import SessionLocal
from app.models import Source, User, Vacancy
from app.routers import account, auth, events, matches, preferences, resumes, shares, skills, vacancies

logging.basicConfig(level=settings.log_level.upper(), format="%(asctime)s %(levelname)s %(name)s: %(message)s")

app = FastAPI(title="JobMatch API")
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins, allow_methods=["*"], allow_headers=["*"])
app.include_router(auth.router)
app.include_router(account.router)
app.include_router(preferences.router)
app.include_router(matches.router)
app.include_router(events.router)
app.include_router(shares.router)
app.include_router(vacancies.router)
app.include_router(resumes.router)
app.include_router(skills.router)


def _check_db() -> bool:
    try:
        with SessionLocal() as s:
            s.execute(text("select 1"))
        return True
    except Exception:
        return False


def _check_redis() -> bool:
    try:
        return bool(Redis.from_url(settings.redis_url, socket_connect_timeout=1).ping())
    except Exception:
        return False


@app.get("/health")
def health():
    db, redis = _check_db(), _check_redis()
    return {"status": "ok" if db and redis else "degraded", "db": db, "redis": redis}


@app.get("/sources")
def sources():
    with SessionLocal() as s:
        rows = s.scalars(select(Source).order_by(Source.name)).all()
        return [
            {
                "name": r.name,
                "enabled": r.enabled,
                "consecutive_failures": r.consecutive_failures,
                "last_success_at": r.last_success_at,
                "last_error": r.last_error,
            }
            for r in rows
        ]


@app.get("/metrics", response_class=PlainTextResponse, include_in_schema=False)
def metrics():
    db = _check_db()
    lines = [f'jobmatch_up{{component="db"}} {int(db)}', f'jobmatch_up{{component="redis"}} {int(_check_redis())}']
    if db:
        now = datetime.now(timezone.utc)
        with SessionLocal() as s:
            lines.append(f"jobmatch_vacancies_total {s.scalar(select(func.count()).select_from(Vacancy))}")
            lines.append(f"jobmatch_users_total {s.scalar(select(func.count()).select_from(User))}")
            for r in s.scalars(select(Source)):
                lines.append(f'jobmatch_source_consecutive_failures{{source="{r.name}"}} {r.consecutive_failures}')
                if r.last_success_at:
                    age = int((now - r.last_success_at).total_seconds())
                    lines.append(f'jobmatch_source_last_success_age_seconds{{source="{r.name}"}} {age}')
    return "\n".join(lines) + "\n"
