import sqlalchemy as sa
from alembic import op

revision = '0004'
down_revision = '0003'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('vacancy_matches', sa.Column('hidden', sa.Boolean(), nullable=False, server_default=sa.text('false')))
    op.alter_column('vacancy_matches', 'score', existing_type=sa.Float(), nullable=True)
    op.drop_index('ix_matches_resume_score', table_name='vacancy_matches')
    op.create_index('ix_matches_resume_visible_score', 'vacancy_matches', ['resume_id', 'hidden', 'score'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_matches_resume_visible_score', table_name='vacancy_matches')
    op.create_index('ix_matches_resume_score', 'vacancy_matches', ['resume_id', 'score'], unique=False)
    op.execute('UPDATE vacancy_matches SET score = 0 WHERE score IS NULL')
    op.alter_column('vacancy_matches', 'score', existing_type=sa.Float(), nullable=False)
    op.drop_column('vacancy_matches', 'hidden')
