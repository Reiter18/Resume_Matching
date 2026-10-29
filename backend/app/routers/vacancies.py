from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import any_, func, literal, or_, select
from sqlalchemy.orm import Session, joinedload

from app.deps import get_current_user, get_db
from app.models import User, Vacancy
from app.schemas.api import VacancyDetailOut, VacancyOut, VacancyPage
from app.schemas.vacancy import WorkFormat

router = APIRouter(prefix="/vacancies", tags=["vacancies"])


def _out(v: Vacancy) -> dict:
    return dict(
        id=v.id, title=v.title, company=v.company, location=v.location, work_format=v.work_format,
        employment_types=v.employment_types or [], schedule=v.schedule, hours_per_week=v.hours_per_week,
        salary_min=v.salary_min, salary_max=v.salary_max, salary_currency=v.salary_currency,
        tags=v.tags or [], skills=v.skills or [], published_at=v.published_at, url=v.url, source=v.source.name,
    )  


@router.get("", response_model=VacancyPage)
def list_vacancies(
    q: Optional[str] = Query(None, max_length=100, description="поиск по названию и компании"),
    work_format: Optional[WorkFormat] = None,
    employment_type: Optional[str] = Query(None, max_length=30),
    min_salary: Optional[int] = Query(None, ge=0, description="в месяц; вакансии без зарплаты не показываются"),
    limit: int = Query(20, ge=1, le=50),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Простой список с фильтрами и пагинацией. Ранжирование по резюме добавится вместе со скорингом."""
    conds = [Vacancy.canonical_id.is_(None)]  
    if q:
        like = "%" + q.strip().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
        conds.append(or_(Vacancy.title.ilike(like, escape="\\"), Vacancy.company.ilike(like, escape="\\")))
    if work_format:
        conds.append(Vacancy.work_format == work_format)
    if employment_type:
        conds.append(literal(employment_type.strip().lower()) == any_(Vacancy.employment_types))
    if min_salary is not None:
        conds.append(or_(Vacancy.salary_max >= min_salary, Vacancy.salary_min >= min_salary))

    total = db.scalar(select(func.count()).select_from(Vacancy).where(*conds)) or 0
    rows = db.scalars(
        select(Vacancy)
        .where(*conds)
        .options(joinedload(Vacancy.source))
        .order_by(Vacancy.published_at.desc(), Vacancy.id.desc())
        .limit(limit)
        .offset(offset)
    ).all()
    return VacancyPage(items=[VacancyOut(**_out(v)) for v in rows], total=total, limit=limit, offset=offset)


@router.get("/{vacancy_id}", response_model=VacancyDetailOut)
def get_vacancy(vacancy_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    v = db.scalar(select(Vacancy).where(Vacancy.id == vacancy_id).options(joinedload(Vacancy.source)))
    if v is None:
        raise HTTPException(404, "Вакансия не найдена")
    return VacancyDetailOut(**_out(v), description_text=v.description_text)
