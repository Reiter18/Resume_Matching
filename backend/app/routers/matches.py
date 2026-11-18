from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.deps import get_current_user, get_db
from app.models import Resume, SearchPreferences, Skill, User, Vacancy
from app.routers.vacancies import _out
from app.schemas.api import MatchOut, MatchPage, Preferences, VacancyOut
from app.scoring import score_vacancy

router = APIRouter(prefix="/matches", tags=["matches"])
MAX_CANDIDATES = 5000  


@router.get("", response_model=MatchPage)
def list_matches(
    min_score: int = Query(0, ge=0, le=100, description="минимальный скор, %"),
    limit: int = Query(20, ge=1, le=50),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    resume = db.scalar(select(Resume).where(Resume.user_id == user.id).order_by(Resume.id.desc()))
    if resume is None:
        raise HTTPException(404, "Сначала загрузите резюме")
    prefs = db.get(SearchPreferences, user.id) or Preferences()
    weights = dict(db.execute(select(Skill.name, Skill.weight)).all())
    vacancies = db.scalars(
        select(Vacancy)
        .where(Vacancy.canonical_id.is_(None))
        .options(joinedload(Vacancy.source))
        .order_by(Vacancy.published_at.desc(), Vacancy.id.desc())
        .limit(MAX_CANDIDATES)
    ).all()

    scored = [(v, score_vacancy(resume, prefs, v, weights)) for v in vacancies]
    scored = [(v, m) for v, m in scored if not m["hidden"] and (m["score"] or 0) * 100 >= min_score]
    scored.sort(key=lambda x: -(x[1]["score"] or 0))  
    items = [
        MatchOut(vacancy=VacancyOut(**_out(v)), score=None if m["score"] is None else round(m["score"] * 100), criteria=m["criteria"])
        for v, m in scored[offset : offset + limit]
    ]
    return MatchPage(items=items, total=len(scored), limit=limit, offset=offset)
