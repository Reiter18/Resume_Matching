import argparse
import sys

from app.connectors import REGISTRY
from app.db import SessionLocal
from app.dedup import dedup_all
from app.ingestion import run_source
from app.skills import seed_skills


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
    args = parser.parse_args(argv)

    with SessionLocal() as session:
        if args.command == "ingest":
            print(f"сохранено: {run_source(session, args.source, args.pages)}")
        elif args.command == "dedup":
            stats = dedup_all(session)
            print(f"проверено: {stats.checked}, найдено дублей: {stats.duplicates}")
        elif args.command == "seed-skills":
            skills, aliases = seed_skills(session)
            print(f"навыков: {skills}, синонимов: {aliases}")


if __name__ == "__main__":
    main(sys.argv[1:])
