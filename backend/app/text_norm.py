import re

LEGAL_FORMS = {
    "gmbh", "ag", "kg", "ug", "se", "mbh", "co", "ltd", "llc", "inc", "corp", "plc", "limited", "sa", "bv", "oy", "ab",
    "ооо", "оао", "зао", "пао", "ао", "ип", "нко",
}  # fmt: skip

_TOKEN = re.compile(r"[a-zа-яё0-9]+")


def company_key(company: str) -> str:
    tokens = _TOKEN.findall(company.lower())
    core = [t for t in tokens if t not in LEGAL_FORMS]
    return "".join(core or tokens)[:255]


_GENDER = re.compile(
    r"[\(\[]?\b(?:m\s*[/|]\s*[wfd]|w\s*[/|]\s*[mfd]|f\s*[/|]\s*[mwd]|d\s*[/|]\s*[mwf])(?:\s*[/|]\s*[mwfdx])?\b[\)\]]?",
    re.I,
)
_REMOTE_NOISE = re.compile(r"\b(?:remote|удал[её]нно|удал[её]нная работа|hybrid|гибрид)\b", re.I)

SENIORITY = {
    "intern": "intern", "internship": "intern", "trainee": "intern", "werkstudent": "intern", "стажер": "intern", "стажёр": "intern",
    "junior": "junior", "jr": "junior", "джуниор": "junior", "младший": "junior",
    "middle": "middle", "mid": "middle", "мидл": "middle", "средний": "middle",
    "senior": "senior", "sr": "senior", "сеньор": "senior", "старший": "senior",
    "lead": "lead", "leader": "lead", "ведущий": "lead", "principal": "lead", "staff": "lead", "head": "lead", "главный": "lead",
}  


def title_tokens(title: str) -> list[str]:
    cleaned = _REMOTE_NOISE.sub(" ", _GENDER.sub(" ", title))
    return _TOKEN.findall(cleaned.lower())


def normalize_title(title: str) -> str:
    """'Junior Python Developer (m/f/d)' -> 'junior python developer'."""
    return " ".join(title_tokens(title))


def seniority_of(title: str) -> frozenset:
    return frozenset(SENIORITY[t] for t in title_tokens(title) if t in SENIORITY)


def number_tokens(title: str) -> frozenset:
    return frozenset(t for t in title_tokens(title) if t.isdigit())


def normalize_city(location: str | None) -> str:
    if not location:
        return ""
    first = location.lower().split(",")[0]
    first = re.sub(r"\d+", " ", first)
    tokens = [t for t in _TOKEN.findall(first) if t not in {"remote", "anywhere", "worldwide", "удаленно", "удалённо"}]
    return " ".join(tokens)
