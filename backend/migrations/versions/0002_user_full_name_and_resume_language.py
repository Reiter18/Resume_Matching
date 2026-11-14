import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("resumes", sa.Column("language", sa.String(length=10), nullable=True))
    op.add_column("users", sa.Column("full_name", sa.String(length=100), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "full_name")
    op.drop_column("resumes", "language")

