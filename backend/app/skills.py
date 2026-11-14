import re
import unicodedata
from dataclasses import dataclass
from typing import Optional

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models import Skill, SkillAlias
from app.skills_data import SKILLS, WEIGHTS

MAX_SKILL_LEN = 50


def clean_name(text: str) -> str:
    text = unicodedata.normalize("NFKC", text).strip().lower()
    text = re.sub(r"\s+", " ", text)
    return text.strip(" ,;:")


def squash(text: str) -> str:
    return re.sub(r"[\s\-_/]+", "", clean_name(text))


@dataclass(frozen=True)
class SkillInfo:
    name: str
    category: Optional[str]
    weight: float


class SkillDictionary:
    def __init__(self, skills: list[SkillInfo], aliases: dict[str, str]):
        self.skills = {s.name: s for s in skills}
        self._index: dict[str, str] = {}
        for s in skills:
            self._index[squash(s.name)] = s.name
        for alias, name in aliases.items():
            self._index.setdefault(squash(alias), name)
        self._aliases = aliases

    @classmethod
    def load(cls, session: Session) -> "SkillDictionary":
        rows = session.scalars(select(Skill).order_by(Skill.id)).all()  # порядок вставки = порядок в skills_data
        skills = [SkillInfo(s.name, s.category, s.weight) for s in rows]
        by_id = {s.id: s.name for s in rows}
        aliases = {a.alias: by_id[a.skill_id] for a in session.scalars(select(SkillAlias)) if a.skill_id in by_id}
        return cls(skills, aliases)

    def canonical(self, text: str) -> Optional[str]:
        key = squash(text)
        return self._index.get(key) if key else None

    def normalize(self, names: list[str]) -> tuple[list[str], list[str]]:
        result: list[str] = []
        unknown: list[str] = []
        seen: set[str] = set()
        for raw in names:
            cleaned = clean_name(raw)
            if not cleaned:
                continue
            canon = self.canonical(cleaned)
            value = canon or cleaned
            key = squash(value)
            if key in seen:
                continue
            seen.add(key)
            result.append(value)
            if canon is None:
                unknown.append(value)
        return result, unknown

    def search(self, query: str, limit: int = 10) -> list[tuple[SkillInfo, Optional[str]]]:
        q = squash(query)
        if not q:
            return []
        scored: dict[str, tuple[tuple[int, int, int], Optional[str]]] = {}
        candidates = [(squash(name), name, None) for name in self.skills]
        candidates += [(squash(alias), name, alias) for alias, name in self._aliases.items()]
        for key, name, alias in candidates:
            if key == q:
                rank = 0
            elif key.startswith(q):
                rank = 1
            elif q in key:
                rank = 2
            else:
                continue
            quality = (rank, 0 if alias is None else 1, len(key))
            if name not in scored or quality < scored[name][0]:
                scored[name] = (quality, alias)
        position = {name: i for i, name in enumerate(self.skills)}  
        ordered = sorted(scored.items(), key=lambda kv: (kv[1][0], position[kv[0]]))[:limit]
        return [(self.skills[name], alias) for name, (_, alias) in ordered]


def seed_skills(session: Session) -> tuple[int, int]:
    existing = {s.name: s for s in session.scalars(select(Skill))}
    n_alias = 0
    for name, category, tier, _aliases in SKILLS:
        skill = existing.get(name)
        if skill is None:
            skill = Skill(name=name)
            session.add(skill)
            existing[name] = skill
        skill.category, skill.weight = category, WEIGHTS[tier]
    session.flush()
    for name, _, _, aliases in SKILLS:
        skill = existing[name]
        wanted = {clean_name(a) for a in aliases} - {name}
        session.execute(
            delete(SkillAlias).where(SkillAlias.skill_id == skill.id, SkillAlias.alias.notin_(wanted or {""}))
        )
        have = {a.alias: a for a in session.scalars(select(SkillAlias).where(SkillAlias.alias.in_(wanted or {""})))}
        for alias in wanted:
            if alias in have:
                have[alias].skill_id = skill.id
            else:
                session.add(SkillAlias(alias=alias, skill_id=skill.id))
            n_alias += 1
    session.commit()
    return len(SKILLS), n_alias
