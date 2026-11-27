from types import SimpleNamespace

import pytest

from app.scoring import score_vacancy

RESUME = SimpleNamespace(skills=["python", "docker"], experience_years=None)
EXPERIENCED = SimpleNamespace(skills=["python", "docker"], experience_years=3.0)
WEIGHTS = {"python": 3, "docker": 1, "java": 1}


def vac(**kw):
    base = dict(
        skills=[], work_format="unknown", employment_types=[], schedule=None, hours_per_week=None, location=None,
        salary_min=None, salary_max=None, salary_currency=None, experience_years_min=None,
    )  # fmt: skip
    return SimpleNamespace(**{**base, **kw})


def prefs(**kw):
    base = dict(
        work_formats=[], employment_types=[], schedules=[], locations=[], min_hours_per_week=None,
        max_hours_per_week=None, min_salary=None, salary_currency=None, must_have=[],
    )  # fmt: skip
    return SimpleNamespace(**{**base, **kw})


def run(v, p=None, resume=RESUME):
    return score_vacancy(resume, p or prefs(), v, WEIGHTS)


def test_skills_use_weights_and_list_matched_and_missing():
    m = run(vac(skills=["python", "java"]))
    c = m["criteria"]["skills"]
    assert c["score"] == 0.75 and c["status"] == "partial"
    assert c["matched"] == ["python"] and c["missing"] == ["java"]
    assert m["score"] == 0.75 and m["confidence"] == 1.0


def test_score_is_weighted_over_applicable_criteria():
    m = run(vac(skills=["python"], work_format="hybrid"), prefs(work_formats=["remote"]))
    assert m["criteria"]["work_format"]["score"] == 0.5
    assert m["score"] == pytest.approx((40 * 1 + 15 * 0.5) / 55, abs=1e-4)
    assert run(vac())["score"] is None


@pytest.mark.parametrize(
    "key, v, p, expected",
    [
        ("work_format", vac(work_format="onsite"), prefs(work_formats=["remote"]), 0.0),
        ("salary", vac(salary_min=2000, salary_max=3000, salary_currency="EUR"), prefs(min_salary=4000, salary_currency="EUR"), 0.75),
        ("salary", vac(salary_max=9000, salary_currency="USD"), prefs(min_salary=4000, salary_currency="EUR"), None),
        ("location", vac(location="Berlin, Germany"), prefs(locations=["berlin"]), 1.0),
        ("location", vac(location="Munich"), prefs(locations=["Berlin"]), 0.0),
        ("location", vac(work_format="remote", location="Munich"), prefs(locations=["Berlin"]), None),
        ("employment_type", vac(employment_types=["part_time"]), prefs(employment_types=["full_time", "part_time"]), 1.0),
        ("schedule", vac(schedule="shift"), prefs(schedules=["flexible"]), 0.0),
        ("hours", vac(hours_per_week=40), prefs(min_hours_per_week=20, max_hours_per_week=30), 0.0),
        ("hours", vac(hours_per_week=25), prefs(min_hours_per_week=20), 1.0),
        ("experience", vac(experience_years_min=6), prefs(), 0.5),
        ("experience", vac(experience_years_min=0), prefs(), 1.0),
    ],
)  # fmt: skip
def test_each_criterion(key, v, p, expected):
    assert run(v, p, EXPERIENCED)["criteria"][key]["score"] == expected


def test_missing_data_for_applicable_criteria_lowers_score():
    m = run(vac(work_format="hybrid"), prefs(work_formats=["hybrid"]))
    assert m["criteria"]["work_format"]["score"] == 1.0
    assert m["score"] == pytest.approx(15 / 55, abs=1e-4) and m["confidence"] == pytest.approx(15 / 55, abs=1e-4)

    wish = prefs(min_salary=4000, salary_currency="EUR")
    assert run(vac(skills=["python"]), wish)["score"] == pytest.approx(40 / 55, abs=1e-4)
    assert run(vac(skills=["python"]))["score"] == 1.0
    remote = run(vac(skills=["python"], work_format="remote"), prefs(locations=["Berlin"]))
    assert remote["score"] == 1.0


def test_must_have_hides_only_known_mismatch():
    p = prefs(work_formats=["remote"], must_have=["work_format"])
    assert run(vac(work_format="onsite"), p)["hidden"] is True
    assert run(vac(work_format="hybrid"), p)["hidden"] is True
    assert run(vac(work_format="unknown"), p)["hidden"] is False
    assert run(vac(work_format="remote"), p)["hidden"] is False
    assert run(vac(work_format="onsite"), prefs(work_formats=["remote"]))["hidden"] is False


def test_summary_only_reports_applicable_criteria():
    result = run(
        vac(skills=["python", "java"], work_format="remote", schedule="shift"),
        prefs(locations=["Berlin"], min_salary=4000, salary_currency="EUR", schedules=["flexible"]),
    )
    assert result["criteria"]["location"]["applicable"] is False
    assert result["summary"] == {
        "matches": ["навыки: python"],
        "gaps": ["не хватает навыков: java", "график не подходит"],
        "unknown": ["зарплата в вакансии не указана"],
    }
