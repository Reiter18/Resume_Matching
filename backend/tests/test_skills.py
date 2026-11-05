import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.main import app
from app.models import Skill, SkillAlias
from app.skills import SkillDictionary, clean_name, seed_skills, squash
from app.skills_data import CATEGORIES, SKILLS, WEIGHTS
from tests.test_auth import login_headers

# данные словаря 


def test_dictionary_data_is_consistent():
    names = [s[0] for s in SKILLS]
    assert len(names) == len(set(names)), "повторяющиеся канонические имена"
    keys: dict[str, str] = {}
    for name, category, tier, aliases in SKILLS:
        assert category in CATEGORIES and tier in WEIGHTS
        assert name == clean_name(name), f"каноническое имя должно быть в нижнем регистре: {name}"
        for variant in [name, *aliases]:
            key = squash(variant)
            assert key, f"пустой синоним у {name}"
            assert keys.setdefault(key, name) == name, f"синоним {variant!r} указывает на два разных навыка"
    assert len(SKILLS) >= 120


# логика словаря 


@pytest.fixture()
def dictionary(db):
    seed_skills(db)
    return SkillDictionary.load(db)


def test_normalize_dedups_keeps_order_and_reports_unknown(dictionary):
    skills, unknown = dictionary.normalize(["Postgres", "JS", "postgresql", "питон", "Cooking", "  ", "js"])
    assert skills == ["postgresql", "javascript", "python", "cooking"]
    assert unknown == ["cooking"]


def test_search_ranking_and_alias_hint(dictionary):
    names = [s.name for s, _ in dictionary.search("py")]
    assert names[0] == "python" and "pytest" in names and "pytorch" in names  
    found = dict((s.name, alias) for s, alias in dictionary.search("постг"))
    assert found == {"postgresql": "постгрес"} or found.get("postgresql") in ("постгрес", "постгре", "постгресс")
    exact = dictionary.search("react")
    assert exact[0][0].name == "react" and exact[0][1] is None  
    assert dictionary.search("") == [] and dictionary.search("zzzzzz") == []
    assert len(dictionary.search("a", limit=3)) <= 3


# загрузка в БД 


def test_seed_is_idempotent_and_cleans_stale_aliases(db):
    skills, aliases = seed_skills(db)
    assert skills == len(SKILLS) and aliases > 250
    count = lambda model: db.scalar(select(func.count()).select_from(model))  # noqa: E731
    first = (count(Skill), count(SkillAlias))
    python_id = db.scalar(select(Skill.id).where(Skill.name == "python"))
    db.add(SkillAlias(alias="устаревший синоним", skill_id=python_id))
    db.commit()
    seed_skills(db)
    assert (count(Skill), count(SkillAlias)) == first  
    assert db.get(SkillAlias, "устаревший синоним") is None


# API 


@pytest.fixture()
def client(db):
    seed_skills(db)
    return TestClient(app)


LONG_CV = "Backend developer. " + "Python FastAPI PostgreSQL Docker. " * 5


def test_resume_skills_edit_flow(client):
    h = login_headers(client)
    assert client.put("/resumes/me/skills", json={"skills": ["python"]}, headers=h).status_code == 404  
    client.post("/resumes/text", json={"text": LONG_CV}, headers=h)
    r = client.put("/resumes/me/skills", json={"skills": ["Postgres", "питон", "JS", "python", "Кулинария"]}, headers=h)
    assert r.status_code == 200
    assert r.json()["skills"] == ["postgresql", "python", "javascript", "кулинария"]
    assert r.json()["unknown_skills"] == ["кулинария"]
    again = client.get("/resumes/me", headers=h).json()  
    assert again["skills"] == r.json()["skills"] and again["unknown_skills"] == ["кулинария"]
    new = client.post("/resumes/text", json={"text": LONG_CV + " more"}, headers=h).json()
    assert new["skills"] == [] and new["unknown_skills"] == []  


def test_resume_skills_validation_and_privacy(client):
    a, b = login_headers(client, "a@example.com"), login_headers(client, "b@example.com")
    client.post("/resumes/text", json={"text": LONG_CV}, headers=a)
    client.post("/resumes/text", json={"text": LONG_CV}, headers=b)
    assert client.put("/resumes/me/skills", json={"skills": ["x" * 51]}, headers=a).status_code == 422
    assert client.put("/resumes/me/skills", json={"skills": ["a"] * 101}, headers=a).status_code == 422
    client.put("/resumes/me/skills", json={"skills": ["python"]}, headers=a)
    assert client.get("/resumes/me", headers=b).json()["skills"] == [] 
    assert client.put("/resumes/me/skills", json={"skills": ["python"]}).status_code == 401


SYNONYMS = [
    ("postgres", "postgresql"), ("PostgreSQL", "postgresql"), ("постгрес", "postgresql"), ("js", "javascript"),
    ("питон", "python"), ("  Python 3 ", "python"), ("Node JS", "node.js"), ("nodejs", "node.js"),
    ("scikit learn", "scikit-learn"), ("sklearn", "scikit-learn"), ("CI CD", "ci/cd"), ("K8s", "kubernetes"),
    ("C#", "c#"), ("c sharp", "c#"), ("C++", "c++"), (".NET Core", ".net"), ("машинное обучение", "machine learning"),
    ("docker-compose", "docker compose"),
]  


def test_synonyms_unknown_words_and_weights(dictionary):
    wrong = [(w, dictionary.canonical(w)) for w, expected in SYNONYMS if dictionary.canonical(w) != expected]
    assert not wrong, wrong
    assert dictionary.canonical("totally-unknown-tech") is None and dictionary.canonical("   ") is None
    w = {s.name: s.weight for s in dictionary.skills.values()}
    assert w["git"] < w["python"] < w["kubernetes"]  


def test_skills_api(client):
    assert client.get("/skills?q=py").status_code == 401
    assert client.post("/skills/normalize", json={"names": ["js"]}).status_code == 401
    h = login_headers(client)
    found = client.get("/skills?q=postg", headers=h).json()
    assert found[0]["name"] == "postgresql" and found[0]["category"] == "database"
    assert client.get("/skills", headers=h).json() == []
    assert client.get("/skills?q=py&limit=500", headers=h).status_code == 422
    r = client.post("/skills/normalize", json={"names": ["Postgres", "JS", "Cooking"]}, headers=h).json()
    assert r == {"skills": ["postgresql", "javascript", "cooking"], "unknown": ["cooking"]}
    assert client.post("/skills/normalize", json={"names": ["x"] * 101}, headers=h).status_code == 422
