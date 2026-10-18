from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateIndex, CreateTable

from app.models import Base


def test_ddl_compiles_for_postgres():
    d = postgresql.dialect()
    for t in Base.metadata.sorted_tables:
        ddl = str(CreateTable(t).compile(dialect=d))
        assert t.name in ddl
        for ix in t.indexes:
            str(CreateIndex(ix).compile(dialect=d))
    ix = {i.name: i for i in Base.metadata.tables["vacancies"].indexes}
    assert "USING gin" in str(CreateIndex(ix["ix_vacancies_skills"]).compile(dialect=d))
    assert "vector" not in str(CreateTable(Base.metadata.tables["vacancies"]).compile(dialect=d)).lower()
