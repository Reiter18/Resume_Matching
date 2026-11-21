import json
import sys
from pathlib import Path
from types import SimpleNamespace

from app.scoring import WEIGHTS, score_vacancy
from app.skills_data import SKILLS
from app.skills_data import WEIGHTS as TIER_WEIGHTS

SKILL_WEIGHTS = {name: TIER_WEIGHTS[tier] for name, _, tier, _ in SKILLS}
PREFS = dict(
    work_formats=[], employment_types=[], schedules=[], locations=[], min_hours_per_week=None,
    max_hours_per_week=None, min_salary=None, salary_currency=None, must_have=[],
)  # fmt: skip
VACANCY = dict(
    skills=[], work_format="unknown", employment_types=[], schedule=None, hours_per_week=None, location=None,
    salary_min=None, salary_max=None, salary_currency=None, experience_years_min=None,
)  # fmt: skip
RESUME = dict(skills=[], experience_years=None)


def variants():
    yield "только навыки", {k: int(k == "skills") for k in WEIGHTS}, False
    yield "многокритериальный, текущие веса", WEIGHTS, True
    rest = sum(w for k, w in WEIGHTS.items() if k != "skills")
    for share in (20, 30, 50, 60, 70, 80):  
        yield f"доля навыков {share}%", {k: share if k == "skills" else w * (100 - share) / rest for k, w in WEIGHTS.items()}, True


def auc(scores, labels):
    pos = [s for s, y in zip(scores, labels, strict=True) if y]
    neg = [s for s, y in zip(scores, labels, strict=True) if not y]
    pairs = [(p > n) + 0.5 * (p == n) for p in pos for n in neg]
    return sum(pairs) / len(pairs) if pairs else None


def precision_at(scores, labels, k=3):
    top = sorted(zip(scores, labels, strict=True), key=lambda x: (-x[0], x[1]))[:k]  
    return sum(y for _, y in top) / len(top)


def evaluate(path):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    profiles = [p for p in data["profiles"] if any(v.get("label") is not None for v in p["vacancies"])]
    pairs = sum(v.get("label") is not None for p in profiles for v in p["vacancies"])
    if not pairs:
        sys.exit("Нет размеченных пар: проставьте у вакансий label 1 (подходит) или 0 (не подходит) вместо null.")
    print(f"Профилей: {len(profiles)}, размеченных пар: {pairs}" + (" (ДЕМО-данные)" if data.get("demo") else ""))
    print("| Вариант | AUC | P@3 |\n|---|---|---|")
    for name, weights, use_must in variants():
        aucs, precs = [], []
        for p in profiles:
            resume = SimpleNamespace(**{**RESUME, **p["resume"]})
            prefs = SimpleNamespace(**{**PREFS, **p["prefs"]})
            if not use_must:
                prefs.must_have = []
            labeled = [v for v in p["vacancies"] if v.get("label") is not None]
            scores = []
            for v in labeled:
                m = score_vacancy(resume, prefs, SimpleNamespace(**{**VACANCY, **v}), SKILL_WEIGHTS, weights)
                scores.append(-1 if m["hidden"] else m["score"] or 0)  
            labels = [v["label"] for v in labeled]
            if (a := auc(scores, labels)) is not None:
                aucs.append(a)
            precs.append(precision_at(scores, labels))
        auc_text = f"{sum(aucs) / len(aucs):.3f}" if aucs else "—"
        print(f"| {name} | {auc_text} | {sum(precs) / len(precs):.3f} |")
    if len(aucs) < len(profiles):
        print(f"\nAUC посчитан по {len(aucs)} из {len(profiles)} профилей: нужны метки обоих классов (и 1, и 0).")
    if pairs < 100:
        print("\nВыборка мала (<100 пар): выводы предварительные.")


def export(user_id, n):
    from sqlalchemy import func, select

    from app.db import SessionLocal
    from app.models import Resume, SearchPreferences, Vacancy
    from app.schemas.api import Preferences

    with SessionLocal() as s:
        resume = s.scalar(select(Resume).where(Resume.user_id == user_id))
        prefs = Preferences.model_validate(s.get(SearchPreferences, user_id) or {}).model_dump()
        rows = s.scalars(select(Vacancy).where(Vacancy.canonical_id.is_(None)).order_by(func.random()).limit(n)).all()
        keys = [k for k in VACANCY] + ["title", "company", "url"]
        profile = {
            "name": f"user {user_id}",
            "resume": {"skills": resume.skills, "experience_years": resume.experience_years},
            "prefs": prefs,
            "vacancies": [{"label": None, **{k: getattr(v, k) for k in keys}} for v in rows],
        }
    print(json.dumps({"profiles": [profile]}, ensure_ascii=False, indent=1, default=str))


if __name__ == "__main__":
    args = sys.argv[1:]
    if args[:1] == ["export"]:
        export(int(args[1]), int(args[2]) if len(args) > 2 else 30)
    else:
        evaluate(args[0] if args else Path(__file__).with_name("labeled_demo.json"))