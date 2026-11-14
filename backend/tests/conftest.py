import fakeredis
import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.exc import OperationalError

from app.celery_app import celery_app
from app.db import SessionLocal, engine
from app.main import app
from app.models import Base
from app.ratelimit import LoginLimiter, get_login_limiter


@pytest.fixture(scope="session")
def migrated_db():
    try:
        with engine.connect() as c:
            c.execute(text("select 1"))
    except OperationalError:
        pytest.skip("Postgres недоступен (поднимите docker compose up -d postgres)")
    cfg = Config("alembic.ini")
    with engine.begin() as c:
        c.execute(text("DROP SCHEMA public CASCADE; CREATE SCHEMA public;"))
    command.upgrade(cfg, "head")
    return engine


@pytest.fixture()
def db(migrated_db):
    with SessionLocal() as s:
        yield s
    with migrated_db.begin() as c:
        names = ", ".join(t.name for t in Base.metadata.sorted_tables)
        c.execute(text(f"TRUNCATE {names} RESTART IDENTITY CASCADE"))


@pytest.fixture(autouse=True)
def eager_celery():
    celery_app.conf.task_always_eager = True
    celery_app.conf.task_eager_propagates = False
    yield
    celery_app.conf.task_always_eager = False


@pytest.fixture(autouse=True)
def login_limiter():
    limiter = LoginLimiter(fakeredis.FakeRedis(server=fakeredis.FakeServer()), 5, 30, 900)
    app.dependency_overrides[get_login_limiter] = lambda: limiter
    yield limiter
    app.dependency_overrides.pop(get_login_limiter, None)
