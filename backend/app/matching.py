from sqlalchemy import and_, func, or_, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.models import Resume, SearchPreferences, Skill, Vacancy, VacancyMatch
from app.schemas.api import Preferences
from app.scoring import score_vacancy

MAX_CANDIDATES = 5000  
BATCH = 500


def match_resume(session: Session, resume: Resume, only_new: bool = False) -> int:
    prefs = session.get(SearchPreferences, resume.user_id) or Preferences()
    weights = dict(session.execute(select(Skill.name, Skill.weight)).all())

    query = select(Vacancy)
    if only_new:
        query = query.outerjoin(
            VacancyMatch, and_(VacancyMatch.vacancy_id == Vacancy.id, VacancyMatch.resume_id == resume.id)
        ).where(or_(VacancyMatch.id.is_(None), VacancyMatch.created_at < Vacancy.fetched_at))
    vacancies = session.scalars(
        query.where(Vacancy.canonical_id.is_(None)).order_by(Vacancy.published_at.desc(), Vacancy.id.desc()).limit(MAX_CANDIDATES)
    ).all()

    rows = []
    for v in vacancies:
        m = score_vacancy(resume, prefs, v, weights)
        rows.append(dict(resume_id=resume.id, vacancy_id=v.id, score=m["score"], hidden=m["hidden"], explanation={"criteria": m["criteria"], "confidence": m["confidence"]}))
    for i in range(0, len(rows), BATCH):
        stmt = insert(VacancyMatch).values(rows[i : i + BATCH])
        stmt = stmt.on_conflict_do_update(  
            constraint="uq_match_resume_vacancy",
            set_={c: getattr(stmt.excluded, c) for c in ("score", "hidden", "explanation")} | {"created_at": func.now()},
        )
        session.execute(stmt)
    session.commit()
    return len(rows)


def match_all(session: Session, only_new: bool = True) -> int:
    resumes = session.scalars(select(Resume)).all()
    return sum(match_resume(session, r, only_new) for r in resumes)
