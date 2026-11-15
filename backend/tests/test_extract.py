from types import SimpleNamespace

from app.extract import SkillExtractor, resume_experience, vacancy_params
from app.skills_data import SKILLS

TERMS = [(n, n) for n, _, _, _ in SKILLS] + [(a, n) for n, _, _, aliases in SKILLS for a in aliases]
EXTRACTOR = SkillExtractor(TERMS)


def vacancy(text, **kw):
    base = dict(
        title="Developer", description_text=text, work_format="unknown", schedule=None, hours_per_week=None,
        experience_years_min=None, salary_min=None, salary_max=None, salary_currency=None,
    )  # fmt: skip
    return SimpleNamespace(**{**base, **kw})


def test_skills_synonyms_cases_and_no_false_matches():
    found = EXTRACTOR.find("Знаю питон, Постгрес и K8s. Python3, CI/CD, C++ и C#, Node.js. Java, не JavaScript. R&D")
    assert found == ["python", "postgresql", "kubernetes", "ci/cd", "c++", "c#", "node.js", "java", "javascript"]
    assert EXTRACTOR.find("javascripting, pythonic, dockerfiles") == []  
    assert SkillExtractor([]).find("python") == []


def test_vacancy_params_from_text():
    cases = [
        ("Fully remote. 40 hours per week. Gleitzeit. 3+ years of experience", dict(
            work_format="remote", hours_per_week=40, schedule="flexible", experience_years_min=3.0)),
        ("Hybrid work model, mindestens 2 Jahre Berufserfahrung", dict(work_format="hybrid", experience_years_min=2.0)),
        ("Gehalt: 50.000 - 70.000 € per year", dict(salary_min=4167, salary_max=5833, salary_currency="EUR")),
        ("от 150 000 до 200 000 руб., вахтовый метод", dict(salary_min=150000, salary_max=200000, salary_currency="RUB", schedule="rotational")),
        ("Up to 70k EUR", dict(salary_min=None, salary_max=5833, salary_currency="EUR")),
        ("We raised $500 million. $25 per hour. No experience required", dict(salary_min=None, experience_years_min=0.0)),
    ]  # fmt: skip
    for text, expected in cases:
        got = vacancy_params(vacancy(text))
        assert {k: got[k] for k in expected} == expected, text


def test_source_values_win_and_resume_experience():
    got = vacancy_params(vacancy("Hybrid, 40 hours per week, 5000 EUR", work_format="remote", hours_per_week=20, salary_min=1))
    assert (got["work_format"], got["hours_per_week"], got["salary_min"]) == ("remote", 20, 1)
    assert resume_experience("Опыт работы: 5 лет в backend") == 5.0
    assert resume_experience("Python, Docker. Работал в Яндексе") is None
