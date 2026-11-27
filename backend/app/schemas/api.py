from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator

from app.schemas.vacancy import Schedule
from app.sharing import validate_fields
from app.skills import MAX_SKILL_LEN


class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class LoginIn(BaseModel):
    email: str
    password: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    full_name: Optional[str] = None
    created_at: datetime


class UpdateProfileIn(BaseModel):
    full_name: Optional[str] = Field(None, max_length=100)


class ChangePasswordIn(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8, max_length=128)


class DeleteAccountIn(BaseModel):
    password: str


class VacancyOut(BaseModel):
    id: int
    title: str
    company: str
    location: Optional[str]
    work_format: str
    employment_types: list[str]
    schedule: Optional[str]
    hours_per_week: Optional[int]
    experience_years_min: Optional[float]
    salary_min: Optional[int]
    salary_max: Optional[int]
    salary_currency: Optional[str]
    tags: list[str]
    skills: list[str]
    published_at: datetime
    url: str
    source: str


class DuplicateOut(BaseModel):
    source: str
    url: str


class VacancyDetailOut(VacancyOut):
    description_text: str
    canonical_id: Optional[int] = None
    also_found_at: list[DuplicateOut] = []


class VacancyPage(BaseModel):
    items: list[VacancyOut]
    total: int
    limit: int
    offset: int


class ResumeOut(BaseModel):
    id: int
    original_filename: Optional[str]
    char_count: int
    language: Optional[str]
    experience_years: Optional[float] = None
    preview: str
    skills: list[str]
    unknown_skills: list[str] = []
    created_at: datetime


class ResumeTextIn(BaseModel):
    text: str = Field(min_length=1, max_length=200_000)


class ResumeFullTextOut(BaseModel):
    text: str


class SkillOut(BaseModel):
    name: str
    category: Optional[str]
    weight: float
    matched_alias: Optional[str] = None


class NormalizeIn(BaseModel):
    names: list[str] = Field(max_length=100)


class NormalizeOut(BaseModel):
    skills: list[str]
    unknown: list[str]


class ResumeSkillsIn(BaseModel):
    skills: list[str] = Field(max_length=100)

    @field_validator("skills")
    @classmethod
    def _each_short(cls, v: list[str]) -> list[str]:
        if any(len(item) > MAX_SKILL_LEN for item in v):
            raise ValueError(f"ключевое слово длиннее {MAX_SKILL_LEN} символов")
        return v


Criterion = Literal["work_format", "employment_type", "schedule", "location", "hours", "salary"]
_FILLED = {  
    "work_format": "work_formats", "employment_type": "employment_types", "schedule": "schedules",
    "location": "locations", "salary": "min_salary",
}  # fmt: skip


class Preferences(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    work_formats: list[Literal["remote", "hybrid", "onsite"]] = []
    employment_types: list[Literal["full_time", "part_time", "contract", "internship"]] = []
    schedules: list[Schedule] = []
    locations: list[str] = Field([], max_length=20)
    min_hours_per_week: Optional[int] = Field(None, ge=1, le=80)
    max_hours_per_week: Optional[int] = Field(None, ge=1, le=80)
    min_salary: Optional[int] = Field(None, ge=0, le=10_000_000)  # в месяц
    salary_currency: Optional[Literal["EUR", "USD", "GBP", "RUB"]] = None
    must_have: list[Criterion] = []

    @field_validator("work_formats", "employment_types", "schedules", "must_have")
    @classmethod
    def _unique(cls, v: list[str]) -> list[str]:
        return list(dict.fromkeys(v))

    @field_validator("locations")
    @classmethod
    def _locations(cls, v: list[str]) -> list[str]:
        cleaned = list(dict.fromkeys(" ".join(x.split()) for x in v if x.strip()))
        if any(len(x) > 100 for x in cleaned):
            raise ValueError("название места длиннее 100 символов")
        return cleaned

    @model_validator(mode="after")
    def _consistent(self):
        low, high = self.min_hours_per_week, self.max_hours_per_week
        if low and high and low > high:
            raise ValueError("минимум часов больше максимума")
        if self.min_salary and not self.salary_currency:
            raise ValueError("укажите валюту зарплаты")
        empty = [c for c in self.must_have if not (low or high if c == "hours" else getattr(self, _FILLED[c]))]
        if empty:
            raise ValueError(f"обязательный критерий без значения: {', '.join(empty)}")
        return self


class CriterionOut(BaseModel):
    score: Optional[float]
    weight: float
    status: Literal["match", "partial", "mismatch", "unknown"]
    text: str
    applicable: Optional[bool] = None
    matched: Optional[list[str]] = None
    missing: Optional[list[str]] = None


class SummaryOut(BaseModel):
    matches: list[str]
    gaps: list[str]
    unknown: list[str]


class MatchOut(BaseModel):
    vacancy: VacancyOut
    summary: Optional[SummaryOut] = None
    score: Optional[int]
    confidence: Optional[int] = None
    hidden: bool = False
    criteria: dict[str, CriterionOut]


class MatchPage(BaseModel):
    items: list[MatchOut]
    pending: bool = False
    total: int
    limit: int
    offset: int


class ShareCreate(BaseModel):
    title: Optional[str] = Field(None, max_length=100)
    allowed_fields: list[str] = Field(default_factory=list, validate_default=True)
    min_score: Optional[int] = Field(None, ge=0, le=100)
    expires_in_days: int = Field(7, ge=1, le=365)

    @field_validator("allowed_fields")
    @classmethod
    def _whitelist(cls, fields: list[str]) -> list[str]:
        return validate_fields(fields)


class ShareOut(BaseModel):
    id: int
    title: Optional[str]
    allowed_fields: list[str]
    min_score: Optional[int]
    expires_at: Optional[datetime]
    revoked_at: Optional[datetime]
    created_at: datetime
    view_count: int
    last_viewed_at: Optional[datetime]
    active: bool


class ShareCreated(ShareOut):
    token: str
