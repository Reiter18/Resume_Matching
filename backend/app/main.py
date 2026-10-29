from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from redis import Redis
from sqlalchemy import select, text

from app.config import settings
from app.db import SessionLocal
from app.models import Source
from app.routers import account, auth, resumes, vacancies

app = FastAPI(title="JobMatch API")
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins, allow_methods=["*"], allow_headers=["*"])
app.include_router(auth.router)
app.include_router(account.router)
app.include_router(vacancies.router)
app.include_router(resumes.router)


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
