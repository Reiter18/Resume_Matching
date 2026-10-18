import sys

from app.db import SessionLocal
from app.ingestion import run_source

if __name__ == "__main__":
    name = sys.argv[1]
    pages = int(sys.argv[2]) if len(sys.argv) > 2 else 1
    with SessionLocal() as s:
        print(f"сохранено: {run_source(s, name, pages)}")
