from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import exists, func, select
from sqlalchemy.orm import Session, joinedload

from app.deps import get_current_user, get_db
from app.models import Resume, User, Vacancy, VacancyMatch
from app.routers.vacancies import _out
from app.schemas.api import MatchOut, MatchPage, VacancyOut

router = APIRouter(prefix="/matches", tags=["matches"])


def _my_resume(db: Session, user: User) -> Resume:
    resume = db.scalar(select(Resume).where(Resume.user_id == user.id).order_by(Resume.id.desc()))
    if resume is None:
        raise HTTPException(404, "Сначала загрузите резюме")
    return resume


def _match_out(v: Vacancy, m: VacancyMatch) -> MatchOut:
    score = None if m.score is None else round(m.score * 100)
    explanation = m.explanation or {}
    confidence = explanation.get("confidence")
    return MatchOut(
        vacancy=VacancyOut(**_out(v)), score=score, confidence=None if confidence is None else round(confidence * 100),
        hidden=m.hidden, criteria=explanation.get("criteria", {}), summary=explanation.get("summary"),
    )  # fmt: skip


@router.get("", response_model=MatchPage)
def list_matches(
    min_score: int = Query(0, ge=0, le=100, description="минимальный скор, %"),
    limit: int = Query(20, ge=1, le=50),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    resume = _my_resume(db, user)
    joined = VacancyMatch.vacancy_id == Vacancy.id
    conds = [VacancyMatch.resume_id == resume.id, VacancyMatch.hidden.is_(False), Vacancy.canonical_id.is_(None)]
    if min_score:
        conds.append(VacancyMatch.score >= min_score / 100)

    total = db.scalar(select(func.count()).select_from(VacancyMatch).join(Vacancy, joined).where(*conds)) or 0
    rows = db.execute(
        select(VacancyMatch, Vacancy)
        .join(Vacancy, joined)
        .where(*conds)
        .options(joinedload(Vacancy.source))
        .order_by(VacancyMatch.score.desc().nullslast(), Vacancy.published_at.desc(), Vacancy.id.desc())
        .limit(limit)
        .offset(offset)
    ).all()
    pending = total == 0 and not db.scalar(select(exists().where(VacancyMatch.resume_id == resume.id)))
    pending = pending and bool(db.scalar(select(exists().where(Vacancy.canonical_id.is_(None)))))
    return MatchPage(
        items=[_match_out(v, m) for m, v in rows], total=total, limit=limit, offset=offset, pending=pending
    )


@router.get("/{vacancy_id}", response_model=MatchOut)
def get_match(vacancy_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    resume = _my_resume(db, user)
    v = db.scalar(select(Vacancy).where(Vacancy.id == vacancy_id).options(joinedload(Vacancy.source)))
    if v is None:
        raise HTTPException(404, "Вакансия не найдена")
    m = db.scalar(
        select(VacancyMatch).where(
            VacancyMatch.resume_id == resume.id, VacancyMatch.vacancy_id == (v.canonical_id or v.id)
        )
    )
    if m is None:
        raise HTTPException(404, "Оценка ещё не готова")
    return _match_out(v, m)
