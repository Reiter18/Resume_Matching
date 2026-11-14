from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

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
