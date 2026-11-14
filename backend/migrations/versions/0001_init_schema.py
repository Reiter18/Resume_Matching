import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "dead_letters",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("task_name", sa.String(length=200), nullable=False),
        sa.Column("task_id", sa.String(length=100), nullable=True),
        sa.Column("args", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("error", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "skills",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("weight", sa.Float(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_table(
        "sources",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=50), nullable=False),
        sa.Column("base_url", sa.String(length=255), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("consecutive_failures", sa.Integer(), nullable=False),
        sa.Column("last_success_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_failure_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )
    op.create_table(
        "notification_settings",
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("min_score", sa.Float(), nullable=False),
        sa.Column("digest", sa.String(length=10), nullable=False),
        sa.Column("in_app_enabled", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id"),
    )
    op.create_table(
        "resumes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=True),
        sa.Column("raw_text", sa.Text(), nullable=False),
        sa.Column("skills", sa.ARRAY(sa.String()), nullable=False),
        sa.Column("experience_years", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_resumes_user_id"), "resumes", ["user_id"], unique=False)
    op.create_table(
        "search_preferences",
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("work_formats", sa.ARRAY(sa.String()), nullable=False),
        sa.Column("employment_types", sa.ARRAY(sa.String()), nullable=False),
        sa.Column("schedules", sa.ARRAY(sa.String()), nullable=False),
        sa.Column("locations", sa.ARRAY(sa.String()), nullable=False),
        sa.Column("min_hours_per_week", sa.Integer(), nullable=True),
        sa.Column("max_hours_per_week", sa.Integer(), nullable=True),
        sa.Column("min_salary", sa.Integer(), nullable=True),
        sa.Column("salary_currency", sa.String(length=3), nullable=True),
        sa.Column("must_have", sa.ARRAY(sa.String()), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id"),
    )
    op.create_table(
        "share_links",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=100), nullable=True),
        sa.Column("allowed_fields", sa.ARRAY(sa.String()), nullable=False),
        sa.Column("min_score", sa.Float(), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("view_count", sa.Integer(), nullable=False),
        sa.Column("last_viewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash"),
    )
    op.create_index(op.f("ix_share_links_user_id"), "share_links", ["user_id"], unique=False)
    op.create_table(
        "skill_aliases",
        sa.Column("alias", sa.String(length=100), nullable=False),
        sa.Column("skill_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["skill_id"], ["skills.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("alias"),
    )
    op.create_table(
        "vacancies",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("source_id", sa.Integer(), nullable=False),
        sa.Column("external_id", sa.String(length=255), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("company", sa.String(length=255), nullable=False),
        sa.Column("location", sa.String(length=255), nullable=True),
        sa.Column("work_format", sa.String(length=10), nullable=False),
        sa.Column("employment_types", sa.ARRAY(sa.String()), nullable=False),
        sa.Column("schedule", sa.String(length=20), nullable=True),
        sa.Column("hours_per_week", sa.Integer(), nullable=True),
        sa.Column("experience_years_min", sa.Float(), nullable=True),
        sa.Column("salary_min", sa.Integer(), nullable=True),
        sa.Column("salary_max", sa.Integer(), nullable=True),
        sa.Column("salary_currency", sa.String(length=3), nullable=True),
        sa.Column("description_text", sa.Text(), nullable=False),
        sa.Column("tags", sa.ARRAY(sa.String()), nullable=False),
        sa.Column("skills", sa.ARRAY(sa.String()), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("dedup_key", sa.String(length=255), nullable=False),
        sa.Column("canonical_id", sa.BigInteger(), nullable=True),
        sa.Column("fetched_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["canonical_id"],
            ["vacancies.id"],
        ),
        sa.ForeignKeyConstraint(
            ["source_id"],
            ["sources.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source_id", "external_id", name="uq_vacancy_source_external"),
    )
    op.create_index("ix_vacancies_content_hash", "vacancies", ["content_hash"], unique=False)
    op.create_index("ix_vacancies_dedup_key", "vacancies", ["dedup_key"], unique=False)
    op.create_index("ix_vacancies_published_at", "vacancies", ["published_at"], unique=False)
    op.create_index("ix_vacancies_skills", "vacancies", ["skills"], unique=False, postgresql_using="gin")
    op.create_table(
        "vacancy_matches",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("resume_id", sa.Integer(), nullable=False),
        sa.Column("vacancy_id", sa.BigInteger(), nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("explanation", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["resume_id"], ["resumes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["vacancy_id"], ["vacancies.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("resume_id", "vacancy_id", name="uq_match_resume_vacancy"),
    )
    op.create_index("ix_matches_resume_score", "vacancy_matches", ["resume_id", "score"], unique=False)
    op.create_table(
        "notifications",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("match_id", sa.BigInteger(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["match_id"], ["vacancy_matches.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_notifications_user_unread", "notifications", ["user_id", "read_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_notifications_user_unread", table_name="notifications")
    op.drop_table("notifications")
    op.drop_index("ix_matches_resume_score", table_name="vacancy_matches")
    op.drop_table("vacancy_matches")
    op.drop_index("ix_vacancies_skills", table_name="vacancies", postgresql_using="gin")
    op.drop_index("ix_vacancies_published_at", table_name="vacancies")
    op.drop_index("ix_vacancies_dedup_key", table_name="vacancies")
    op.drop_index("ix_vacancies_content_hash", table_name="vacancies")
    op.drop_table("vacancies")
    op.drop_table("skill_aliases")
    op.drop_index(op.f("ix_share_links_user_id"), table_name="share_links")
    op.drop_table("share_links")
    op.drop_table("search_preferences")
    op.drop_index(op.f("ix_resumes_user_id"), table_name="resumes")
    op.drop_table("resumes")
    op.drop_table("notification_settings")
    op.drop_table("users")
    op.drop_table("sources")
    op.drop_table("skills")
    op.drop_table("dead_letters")
