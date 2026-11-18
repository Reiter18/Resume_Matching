WEIGHTS = {
    "skills": 40, "work_format": 15, "salary": 15, "location": 10,
    "employment_type": 10, "experience": 5, "schedule": 2.5, "hours": 2.5,
}  # fmt: skip
NEAR = {("hybrid", "remote"), ("hybrid", "onsite"), ("remote", "hybrid"), ("onsite", "hybrid")}
FORMATS = {"remote": "удалённо", "hybrid": "гибрид", "onsite": "офис"}
UNSET = "пожелание не задано"


def _skills(resume, v, weights):
    if not v.skills:
        return None, "в вакансии не найдено ключевых слов"
    if not resume.skills:
        return None, "в резюме нет ключевых слов"
    have = set(resume.skills)
    matched = [s for s in v.skills if s in have]
    missing = [s for s in v.skills if s not in have]
    total = sum(weights.get(s, 1) for s in v.skills)
    score = sum(weights.get(s, 1) for s in matched) / total
    return score, f"совпало {len(matched)} из {len(v.skills)}", {"matched": matched, "missing": missing}


def _work_format(p, v):
    if not p.work_formats:
        return None, UNSET
    if v.work_format == "unknown":
        return None, "формат в вакансии не указан"
    name = FORMATS[v.work_format]
    if v.work_format in p.work_formats:
        return 1.0, f"формат подходит: {name}"
    if any((v.work_format, w) in NEAR for w in p.work_formats):
        return 0.5, f"{name}: рядом с желаемым форматом"
    return 0.0, f"формат не подходит: {name}"


def _salary(p, v):
    if not p.min_salary:
        return None, UNSET
    top = v.salary_max or v.salary_min
    if not top:
        return None, "зарплата в вакансии не указана"
    if v.salary_currency != p.salary_currency:
        return None, f"валюта вакансии {v.salary_currency}, нужна {p.salary_currency}"
    return min(1.0, top / p.min_salary), f"до {top} {v.salary_currency} в месяц при желаемых {p.min_salary}"


def _location(p, v):
    if not p.locations:
        return None, UNSET
    if v.work_format == "remote":
        return None, "вакансия удалённая, место не важно"
    if not v.location:
        return None, "место в вакансии не указано"
    if any(x.casefold() in v.location.casefold() for x in p.locations):
        return 1.0, f"место подходит: {v.location}"
    return 0.0, f"место {v.location}, а нужно: {', '.join(p.locations)}"


def _employment(p, v):
    if not p.employment_types:
        return None, UNSET
    if not v.employment_types:
        return None, "тип занятости в вакансии не указан"
    ok = bool(set(p.employment_types) & set(v.employment_types))
    return (1.0 if ok else 0.0), ("тип занятости подходит" if ok else "тип занятости не подходит")


def _schedule(p, v):
    if not p.schedules:
        return None, UNSET
    if not v.schedule:
        return None, "график в вакансии не указан"
    ok = v.schedule in p.schedules
    return (1.0 if ok else 0.0), ("график подходит" if ok else "график не подходит")


def _hours(p, v):
    low, high = p.min_hours_per_week, p.max_hours_per_week
    if not (low or high):
        return None, UNSET
    if not v.hours_per_week:
        return None, "часы в вакансии не указаны"
    ok = (not low or v.hours_per_week >= low) and (not high or v.hours_per_week <= high)
    return (1.0 if ok else 0.0), f"{v.hours_per_week} ч в неделю: {'подходит' if ok else 'не подходит'}"


def _experience(resume, v):
    need = v.experience_years_min
    if need is None:
        return None, "опыт в вакансии не указан"
    if resume.experience_years is None:
        return None, "в резюме опыт не указан"
    return min(1.0, resume.experience_years / need) if need else 1.0, f"нужно {need:g}, в резюме {resume.experience_years:g}"


def _status(score):
    return "unknown" if score is None else "match" if score >= 1 else "mismatch" if score <= 0 else "partial"


def score_vacancy(resume, prefs, v, weights: dict) -> dict:
    checks = {
        "skills": _skills(resume, v, weights), "work_format": _work_format(prefs, v), "salary": _salary(prefs, v),
        "location": _location(prefs, v), "employment_type": _employment(prefs, v), "schedule": _schedule(prefs, v),
        "hours": _hours(prefs, v), "experience": _experience(resume, v),
    }  # fmt: skip
    criteria = {}
    for key, (score, text, *extra) in checks.items():
        criteria[key] = dict(score=score, weight=WEIGHTS[key], status=_status(score), text=text, **(extra[0] if extra else {}))
    used = [c for c in criteria.values() if c["score"] is not None]
    total = sum(c["weight"] for c in used)
    hidden = any(criteria[k]["status"] in ("partial", "mismatch") for k in prefs.must_have if k in criteria)
    score = sum(c["score"] * c["weight"] for c in used) / total if total else None
    return {"score": None if score is None else round(score, 4), "hidden": hidden, "criteria": criteria}
