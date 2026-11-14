import sqlalchemy as sa
from alembic import op

revision = '0003'
down_revision = '0002'
branch_labels = None
depends_on = None


def _backfill_company_keys() -> None:
    from app.text_norm import company_key

    conn = op.get_bind()
    rows = conn.execute(sa.text("SELECT id, company FROM vacancies")).all()
    if rows:
        conn.execute(
            sa.text("UPDATE vacancies SET company_key = :key WHERE id = :id"),
            [{"id": r.id, "key": company_key(r.company)} for r in rows],
        )


def upgrade() -> None:
    op.add_column('skills', sa.Column('category', sa.String(length=30), nullable=True))
    op.add_column('vacancies', sa.Column('company_key', sa.String(length=255), nullable=False, server_default=''))
    op.add_column('vacancies', sa.Column('dedup_checked_at', sa.DateTime(timezone=True), nullable=True))
    _backfill_company_keys()
    op.alter_column('vacancies', 'company_key', server_default=None)
    op.create_index('ix_vacancies_company_key', 'vacancies', ['company_key'], unique=False)
    op.create_index('ix_vacancies_dedup_pending', 'vacancies', ['id'], unique=False, postgresql_where=sa.text('dedup_checked_at IS NULL'))


def downgrade() -> None:
    op.drop_index('ix_vacancies_dedup_pending', table_name='vacancies', postgresql_where=sa.text('dedup_checked_at IS NULL'))
    op.drop_index('ix_vacancies_company_key', table_name='vacancies')
    op.drop_column('vacancies', 'dedup_checked_at')
    op.drop_column('vacancies', 'company_key')
    op.drop_column('skills', 'category')
