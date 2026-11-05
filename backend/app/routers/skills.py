from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.deps import get_current_user, get_db
from app.models import User
from app.schemas.api import NormalizeIn, NormalizeOut, SkillOut
from app.skills import SkillDictionary

router = APIRouter(prefix="/skills", tags=["skills"])


@router.get("", response_model=list[SkillOut])
def search_skills(
    q: str = Query("", max_length=50, description="часть названия или синонима: 'py', 'постг', 'k8s'"),
    limit: int = Query(10, ge=1, le=30),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    found = SkillDictionary.load(db).search(q, limit)
    return [SkillOut(name=s.name, category=s.category, weight=s.weight, matched_alias=alias) for s, alias in found]


@router.post("/normalize", response_model=NormalizeOut)
def normalize_skills(body: NormalizeIn, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    skills, unknown = SkillDictionary.load(db).normalize(body.names)
    return NormalizeOut(skills=skills, unknown=unknown)
