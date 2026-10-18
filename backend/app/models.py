from datetime import datetime
from typing import Optional

from sqlalchemy import (
    ARRAY, BigInteger, Boolean, DateTime, Float, ForeignKey, Index, Integer,
    String, Text, UniqueConstraint, func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Source(Base):
    __tablename__ = "sources"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50), unique=True)
    base_url: Mapped[str] = mapped_column(String(255))
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    consecutive_failures: Mapped[int] = mapped_column(Integer, default=0)
    last_success_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    last_error: Mapped[Optional[str]] = mapped_column(Text)


class Skill(Base):
    __tablename__ = "skills"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)  
    weight: Mapped[float] = mapped_column(Float, default=1.0)


class SkillAlias(Base):
    __tablename__ = "skill_aliases"

    alias: Mapped[str] = mapped_column(String(100), primary_key=True)
    skill_id: Mapped[int] = mapped_column(ForeignKey("skills.id", ondelete="CASCADE"))


class Vacancy(Base):
    __tablename__ = "vacancies"
    __table_args__ = (
        UniqueConstraint("source_id", "external_id", name="uq_vacancy_source_external"),
        Index("ix_vacancies_published_at", "published_at"),
        Index("ix_vacancies_dedup_key", "dedup_key"),
        Index("ix_vacancies_content_hash", "content_hash"),
        Index("ix_vacancies_skills", "skills", postgresql_using="gin"),  
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("sources.id"))
    external_id: Mapped[str] = mapped_column(String(255))
    url: Mapped[str] = mapped_column(Text)

    title: Mapped[str] = mapped_column(String(500))
    company: Mapped[str] = mapped_column(String(255))
    location: Mapped[Optional[str]] = mapped_column(String(255))
    work_format: Mapped[str] = mapped_column(String(10), default="unknown")  
    employment_types: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    schedule: Mapped[Optional[str]] = mapped_column(String(20))  
    hours_per_week: Mapped[Optional[int]] = mapped_column(Integer)
    experience_years_min: Mapped[Optional[float]] = mapped_column(Float)
    salary_min: Mapped[Optional[int]] = mapped_column(Integer)  
    salary_max: Mapped[Optional[int]] = mapped_column(Integer)
    salary_currency: Mapped[Optional[str]] = mapped_column(String(3))
    description_text: Mapped[str] = mapped_column(Text)
    tags: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)  
    skills: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)  
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    content_hash: Mapped[str] = mapped_column(String(64))
    dedup_key: Mapped[str] = mapped_column(String(255))
    canonical_id: Mapped[Optional[int]] = mapped_column(ForeignKey("vacancies.id"))  
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    source: Mapped[Source] = relationship()


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Resume(Base):
    __tablename__ = "resumes"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    original_filename: Mapped[Optional[str]] = mapped_column(String(255))
    raw_text: Mapped[str] = mapped_column(Text)
    skills: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    experience_years: Mapped[Optional[float]] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class VacancyMatch(Base):
    __tablename__ = "vacancy_matches"
    __table_args__ = (
        UniqueConstraint("resume_id", "vacancy_id", name="uq_match_resume_vacancy"),
        Index("ix_matches_resume_score", "resume_id", "score"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    resume_id: Mapped[int] = mapped_column(ForeignKey("resumes.id", ondelete="CASCADE"))
    vacancy_id: Mapped[int] = mapped_column(ForeignKey("vacancies.id", ondelete="CASCADE"))
    score: Mapped[float] = mapped_column(Float)  # 0..1
    explanation: Mapped[Optional[dict]] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class SearchPreferences(Base):
    __tablename__ = "search_preferences"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    work_formats: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    employment_types: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    schedules: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    locations: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    min_hours_per_week: Mapped[Optional[int]] = mapped_column(Integer)
    max_hours_per_week: Mapped[Optional[int]] = mapped_column(Integer)
    min_salary: Mapped[Optional[int]] = mapped_column(Integer)  # в месяц
    salary_currency: Mapped[Optional[str]] = mapped_column(String(3))
    must_have: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)


class ShareLink(Base):
    __tablename__ = "share_links"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    title: Mapped[Optional[str]] = mapped_column(String(100))  
    allowed_fields: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    min_score: Mapped[Optional[float]] = mapped_column(Float) 
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    view_count: Mapped[int] = mapped_column(Integer, default=0)
    last_viewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class NotificationSettings(Base):
    __tablename__ = "notification_settings"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    min_score: Mapped[float] = mapped_column(Float, default=0.7)
    digest: Mapped[str] = mapped_column(String(10), default="off")  
    in_app_enabled: Mapped[bool] = mapped_column(Boolean, default=True)


class Notification(Base):
    __tablename__ = "notifications"
    __table_args__ = (Index("ix_notifications_user_unread", "user_id", "read_at"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    match_id: Mapped[int] = mapped_column(ForeignKey("vacancy_matches.id", ondelete="CASCADE"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    read_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
