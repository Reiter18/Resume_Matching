import re
import unicodedata
from typing import Optional

SEP = r"[\s\-_/]+"


def _squash(s: str) -> str:
    return re.sub(SEP, "", unicodedata.normalize("NFKC", s).lower())


class SkillExtractor:
    def __init__(self, terms: list[tuple[str, str]]):  
        self.canon: dict[str, str] = {}
        patterns = []
        for term, name in terms:
            parts = [p for p in re.split(SEP, term.lower()) if p]
            if not parts:
                continue
            self.canon.setdefault(_squash(term), name)
            pat = r"[\s\-_/]*".join(re.escape(p) for p in parts)
            if re.fullmatch(r"[а-яё]{5,}", parts[-1]):  
                pat += r"[а-яё]{0,2}"
            patterns.append(pat)
        patterns.sort(key=len, reverse=True)  
        self.rx = re.compile(r"(?<![\w#+])(?:" + "|".join(patterns) + r")(?![\w#+])", re.I) if patterns else None

    def _name(self, found: str) -> Optional[str]:
        key = _squash(found)
        for cut in (0, 1, 2):
            if name := self.canon.get(key[: len(key) - cut]):
                return name
        return None

    def find(self, text: str) -> list[str]:
        if not self.rx:
            return []
        names = (self._name(m.group(0)) for m in self.rx.finditer(text))
        return list(dict.fromkeys(n for n in names if n))  



_HYBRID = re.compile(r"hybrid(?!\s+cloud)|гибрид|teilweise\s+(?:remote|home\s?office)|home\s?office", re.I)
_REMOTE = re.compile(r"\bremote\b|удал[её]н|дистанцион|work from home|\bwfh\b", re.I)
_ONSITE = re.compile(r"on-?site|vor\s+ort|в\s+офисе|office[- ]based", re.I)

_SCHEDULES = [
    ("rotational", re.compile(r"вахт|rotational", re.I)),
    ("shift", re.compile(r"shift work|shift schedule|night shifts?|schicht(?:arbeit|dienst)|посменн|сменн\w+ график|в смены", re.I)),
    ("flexible", re.compile(r"flexible (?:working )?hours|flexible arbeitszeit|gleitzeit|flex-?time|гибкий график|свободный график", re.I)),
    ("full_day", re.compile(r"полный рабочий день|full[- ]day|\b5/2\b|пятидневк", re.I)),
]  # fmt: skip

_HOURS = re.compile(
    r"(\d{1,2})\s*(?:[-–]\s*\d{1,2}\s*)?(?:h|hrs?|hours?|stunden|std\.?|ч|час\w*)\s*(?:/|per|a|pro|в|each)?\s*(?:week|wk|woche|нед\w*)"
    r"|(\d{1,2})[- ]?(?:stunden|std)[- ]?woche",
    re.I,
)  # fmt: skip

_CTX = re.compile(r"experience|erfahrung|опыт|стаж", re.I)
_YEARS = re.compile(r"(\d{1,2})\s*(?:[-–]\s*\d{1,2}\s*)?\+?\s*(?:years?|yrs?|jahre?n?|лет|года?|год)\b", re.I)
_NO_EXP = re.compile(r"no experience|keine (?:berufs)?erfahrung|без опыта", re.I)

_CUR = r"€|eur(?:o)?\b|\$|usd\b|£|gbp\b|₽|руб(?:\.|лей|ля)?|rub\b|р\."
_NUM = r"(?:\d{1,3}(?:[ .,\u00a0\u202f]\d{3})+|\d+(?:[.,]\d+)?)(?:\s?[kк]\b)?"
_SALARY = re.compile(
    rf"(?P<c1>{_CUR})?\s*(?P<a>{_NUM})(?:\s*(?:-|–|—|bis|to|до)\s*(?P<c2>{_CUR})?\s*(?P<b>{_NUM}))?\s*(?P<c3>{_CUR})?", re.I
)
_YEAR_WORDS = re.compile(r"per year|p\.?a\.|/\s?(?:year|yr|jahr|год)|pro jahr|jährlich|annual|yearly|jahresgehalt|в год|годов", re.I)
_HOUR_WORDS = re.compile(r"per hour|/\s?h\b|pro stunde|stündlich|hourly|в час|/\s?час", re.I)
_BIG = re.compile(r"\s*(?:million|mio|mln|billion|bn|млн|млрд|%)", re.I)


def _work_format(text: str) -> Optional[str]:
    for fmt, rx in (("hybrid", _HYBRID), ("remote", _REMOTE), ("onsite", _ONSITE)):
        if rx.search(text):
            return fmt
    return None


def _schedule(text: str) -> Optional[str]:
    return next((name for name, rx in _SCHEDULES if rx.search(text)), None)


def _hours(text: str) -> Optional[int]:
    m = _HOURS.search(text)
    hours = int(m.group(1) or m.group(2)) if m else 0
    return hours if 1 <= hours <= 80 else None


def _experience(text: str, vacancy: bool = False) -> Optional[float]:
    found = [
        int(m.group(1))
        for m in _YEARS.finditer(text)
        if _CTX.search(text[max(0, m.start() - 40) : m.end() + 40])
    ]
    if found:
        return float(max(found))
    return 0.0 if vacancy and _NO_EXP.search(text) else None


def resume_experience(text: str) -> Optional[float]:
    return _experience(text)


def _amount(s: str) -> float:
    s = s.strip().lower()
    k = s[-1] in "kк"
    s = s.rstrip("kк").strip()
    if re.fullmatch(r"\d{1,3}(?:[ .,\u00a0\u202f]\d{3})+", s):
        s = re.sub(r"\D", "", s)
    s = s.replace(",", ".")
    return float(s) * (1000 if k else 1)


def _currency(s: str) -> str:
    s = s.lower()
    if s == "€" or s.startswith("eur"):
        return "EUR"
    return {"$": "USD", "usd": "USD", "£": "GBP", "gbp": "GBP"}.get(s, "RUB")


def _salary(text: str) -> tuple[Optional[int], Optional[int], Optional[str]]:
    for m in _SALARY.finditer(text):
        cur = m["c1"] or m["c2"] or m["c3"]
        if not cur or _BIG.match(text, m.end()):
            continue
        window = text[max(0, m.start() - 25) : m.end() + 30]
        if _HOUR_WORDS.search(window):
            continue
        lo, hi = _amount(m["a"]), _amount(m["b"]) if m["b"] else None
        if hi and lo < 1000 <= hi and not re.search(r"[kк]$", m["a"], re.I):
            lo *= 1000  
        currency = _currency(cur)
        yearly = bool(_YEAR_WORDS.search(window)) or (currency != "RUB" and lo >= 20_000 and "month" not in window.lower())
        div = 12 if yearly else 1
        lo, hi = round(lo / div), round(hi / div) if hi else None
        if lo < 300 or (hi and hi < lo):
            continue
        if not hi and re.search(r"(?:up to|bis zu|до)\s*$", text[max(0, m.start() - 12) : m.start()], re.I):
            return None, lo, currency
        return lo, hi, currency
    return None, None, None


def vacancy_params(v) -> dict:
    """Параметры вакансии. Значения от источника важнее; пустые добираем из текста."""
    text = f"{v.title}\n{v.description_text}"
    salary = (v.salary_min, v.salary_max, v.salary_currency) if (v.salary_min or v.salary_max) else _salary(text)
    exp = v.experience_years_min if v.experience_years_min is not None else _experience(text, vacancy=True)
    return dict(
        work_format=v.work_format if v.work_format == "remote" else (_work_format(text) or v.work_format),
        schedule=v.schedule or _schedule(text),
        hours_per_week=v.hours_per_week or _hours(text),
        experience_years_min=exp,
        salary_min=salary[0],
        salary_max=salary[1],
        salary_currency=salary[2],
    )
