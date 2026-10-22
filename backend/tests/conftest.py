import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.exc import OperationalError

from app.celery_app import celery_app
from app.db import SessionLocal, engine
from app.models import Base


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
