from sqlalchemy import and_, func, or_, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app import events
from app.models import Resume, SearchPreferences, Skill, Vacancy, VacancyMatch
from app.schemas.api import Preferences
from app.scoring import score_vacancy

MAX_CANDIDATES = 5000
BATCH = 500


def match_resume(session: Session, resume: Resume, only_new: bool = False) -> int:
    # Сериализуем пересчёты одного резюме, чтобы обнаружить новые оценки только один раз.
    user_id = session.scalar(select(Resume.user_id).where(Resume.id == resume.id).with_for_update())
    if user_id is None:
        return 0
    session.refresh(resume)
    prefs = session.get(SearchPreferences, user_id) or Preferences()
    weights = dict(session.execute(select(Skill.name, Skill.weight)).all())

    query = select(Vacancy, VacancyMatch.id).outerjoin(
        VacancyMatch, and_(VacancyMatch.vacancy_id == Vacancy.id, VacancyMatch.resume_id == resume.id)
    )
    if only_new:
        query = query.where(or_(VacancyMatch.id.is_(None), VacancyMatch.created_at < Vacancy.fetched_at))
    vacancies = session.execute(
        query.where(Vacancy.canonical_id.is_(None))
        .order_by(Vacancy.published_at.desc(), Vacancy.id.desc())
        .limit(MAX_CANDIDATES)
    ).all()

    rows, fresh = [], []
    for v, old_match_id in vacancies:
        m = score_vacancy(resume, prefs, v, weights)
        explanation = {key: m[key] for key in ("criteria", "confidence", "summary")}
        rows.append(
            dict(resume_id=resume.id, vacancy_id=v.id, score=m["score"], hidden=m["hidden"], explanation=explanation)
        )
        if old_match_id is None and not m["hidden"] and m["score"] is not None:
            fresh.append((m["score"], v.id, v.title))
    for i in range(0, len(rows), BATCH):
        stmt = insert(VacancyMatch).values(rows[i : i + BATCH])
        stmt = stmt.on_conflict_do_update(
            constraint="uq_match_resume_vacancy",
            set_={c: getattr(stmt.excluded, c) for c in ("score", "hidden", "explanation")}
            | {"created_at": func.now()},
        )
        session.execute(stmt)
    session.commit()
    if not only_new:
        events.publish(user_id, {"type": "matches_refreshed"})
    elif fresh:
        score, vacancy_id, title = max(fresh, key=lambda item: item[0])
        events.publish(
            user_id,
            {
                "type": "new_matches",
                "count": len(fresh),
                "best": {"id": vacancy_id, "title": title, "score": round(score * 100)},
            },
        )
    elif rows:
        events.publish(user_id, {"type": "matches_refreshed"})
    return len(rows)


def match_all(session: Session, only_new: bool = True) -> int:
    resumes = session.scalars(select(Resume)).all()
    return sum(match_resume(session, r, only_new) for r in resumes)
