import argparse
import sys

from sqlalchemy import func, select

from app.connectors import REGISTRY
from app.db import SessionLocal
from app.dedup import dedup_all
from app.extract import SkillExtractor, resume_experience, vacancy_params
from app.ingestion import run_source
from app.models import Resume, Vacancy
from app.skills import SkillDictionary, seed_skills


def extract_all(session) -> tuple[int, int]:
    extractor = SkillExtractor(SkillDictionary.load(session).terms())
    vacancies = session.scalars(select(Vacancy)).all()
    for v in vacancies:
        v.skills = extractor.find(f"{v.title}\n{' '.join(v.tags or [])}\n{v.description_text}")
        for key, value in vacancy_params(v).items():
            setattr(v, key, value)
    resumes = session.scalars(select(Resume).where(func.cardinality(Resume.skills) == 0)).all()
    for r in resumes:
        r.skills, r.experience_years = extractor.find(r.raw_text)[:100], resume_experience(r.raw_text)
    session.commit()
    return len(vacancies), len(resumes)


def main(argv: list[str]) -> None:
    if argv and argv[0] in REGISTRY:  
        argv = ["ingest", *argv]
    parser = argparse.ArgumentParser(prog="app.cli", description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    ing = sub.add_parser("ingest")
    ing.add_argument("source", choices=sorted(REGISTRY))
    ing.add_argument("pages", nargs="?", type=int, default=1)
    sub.add_parser("dedup")
    sub.add_parser("seed-skills")
    sub.add_parser("extract")
    args = parser.parse_args(argv)

    with SessionLocal() as session:
        if args.command == "ingest":
            print(f"сохранено: {run_source(session, args.source, args.pages)}")
        elif args.command == "dedup":
            stats = dedup_all(session)
            print(f"проверено: {stats.checked}, найдено дублей: {stats.duplicates}")
        elif args.command == "extract":
            print("вакансий: {}, резюме: {}".format(*extract_all(session)))
        elif args.command == "seed-skills":
            skills, aliases = seed_skills(session)
            print(f"навыков: {skills}, синонимов: {aliases}")


if __name__ == "__main__":
    main(sys.argv[1:])
