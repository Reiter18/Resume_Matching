import hashlib
import re
from datetime import datetime, timezone
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator


EMPLOYMENT_MAP = {
    "full time": "full_time", "full-time": "full_time", "полная занятость": "full_time",
    "part time": "part_time", "part-time": "part_time", "частичная занятость": "part_time",
    "contract": "contract", "freelance": "contract", "проектная работа": "contract",
    "internship": "internship", "working student": "internship", "стажировка": "internship",
}
WorkFormat = Literal["remote", "hybrid", "onsite", "unknown"]
Schedule = Literal["full_day", "flexible", "shift", "rotational"]


def detect_work_format(is_remote: Optional[bool], text: str, has_location: bool) -> str:
    """remote -> remote; иначе по словам в тексте hybrid/гибрид; есть локация -> onsite; иначе unknown."""
    t = text.lower()
    if is_remote:
        return "remote"
    if "hybrid" in t or "гибрид" in t:
        return "hybrid"
    return "onsite" if has_location else "unknown"


def _norm(s: str) -> str:
    return re.sub(r"[^a-zа-яё0-9]+", "", s.lower())


class NormalizedVacancy(BaseModel):
    source: str
    external_id: str
    url: str
    title: str = Field(min_length=1, max_length=500)
    company: str = Field(min_length=1, max_length=255)
    location: Optional[str] = None
    work_format: WorkFormat = "unknown"
    employment_types: list[str] = Field(default_factory=list)
    schedule: Optional[Schedule] = None
    hours_per_week: Optional[int] = Field(default=None, ge=1, le=80)
    experience_years_min: Optional[float] = Field(default=None, ge=0)
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    salary_currency: Optional[str] = None
    description_text: str = ""
    tags: list[str] = Field(default_factory=list)
    published_at: datetime

    @field_validator("title", "company", "location", mode="before")
    @classmethod
    def _strip(cls, v):
        return " ".join(v.split()) if isinstance(v, str) else v

    @field_validator("employment_types", mode="before")
    @classmethod
    def _employment(cls, v):
        out = []
        for x in v or []:
            k = EMPLOYMENT_MAP.get(str(x).strip().lower(), str(x).strip().lower().replace(" ", "_"))
            if k and k not in out:
                out.append(k)
        return out

    @field_validator("tags", mode="before")
    @classmethod
    def _lower_unique(cls, v):
        seen, out = set(), []
        for x in v or []:
            x = str(x).strip().lower()
            if x and x not in seen:
                seen.add(x)
                out.append(x)
        return out

    @field_validator("published_at")
    @classmethod
    def _utc(cls, v: datetime) -> datetime:
        return v.replace(tzinfo=timezone.utc) if v.tzinfo is None else v.astimezone(timezone.utc)

    @property
    def dedup_key(self) -> str:
        return f"{_norm(self.company)}:{_norm(self.title)}"[:255]

    @property
    def content_hash(self) -> str:
        raw = f"{_norm(self.title)}|{_norm(self.company)}|{_norm(self.description_text[:2000])}"
        return hashlib.sha256(raw.encode()).hexdigest()
