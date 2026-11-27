import logging
import re
import time
from datetime import datetime
from html import unescape
from typing import Iterator
from urllib.parse import urlsplit

from bs4 import BeautifulSoup

from app.connectors.base import HttpConnector, SourceUnavailable
from app.schemas import NormalizedVacancy
from app.schemas.vacancy import EMPLOYMENT_MAP, detect_work_format

log = logging.getLogger(__name__)

SCHEDULES = {
    "полный рабочий день": "full_day",
    "гибкий график": "flexible",
    "сменный график": "shift",
    "вахтовый метод": "rotational",
}


def positive_salary(value) -> int | None:
    try:
        amount = int(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return amount if amount > 0 else None


_BLOCK_TAGS = ("p", "div", "li", "ul", "ol", "blockquote", "section", "h1", "h2", "h3", "h4", "pre", "tr")
_HTML_TAG = re.compile(
    r"</?(?:" + "|".join((*_BLOCK_TAGS, "br", "span", "a", "b", "strong", "i", "em", "table", "td")) + r")\b", re.I
)


def _formatted_text(value) -> str:
    if not isinstance(value, str):
        return ""
    decoded = unescape(value)
    if _HTML_TAG.search(value) or _HTML_TAG.search(decoded):
        soup = BeautifulSoup(value if _HTML_TAG.search(value) else decoded, "html.parser")
        for tag in soup.find_all(("script", "style")):
            tag.decompose()
        for tag in soup.find_all("br"):
            tag.replace_with("\n")
        for tag in soup.find_all(_BLOCK_TAGS):
            tag.insert_before("\n• " if tag.name == "li" else "\n")
            if tag.name != "li":
                tag.insert_after("\n")
        value = unescape(soup.get_text())
    else:
        value = decoded
    return "\n".join(line.strip() for line in value.splitlines()).strip()


def _vacancy_description(raw: dict, requirement: dict) -> str:
    def field(label: str, value) -> str:
        text = _formatted_text(value)
        return f"{label}: {text}" if text and text.casefold() != "не указано" else ""

    def unique_texts(values) -> str:
        return ", ".join(dict.fromkeys(text for value in values if (text := _formatted_text(value))))

    skills = unique_texts(raw.get("skills") or [])
    addresses = unique_texts(
        address.get("location")
        for address in ((raw.get("addresses") or {}).get("address") or [])
        if isinstance(address, dict)
    )
    if addresses and raw.get("addressOffice"):
        addresses += f", офис {raw['addressOffice']}"

    sections = (
        ("Должностные обязанности", (_formatted_text(raw.get("duty")),)),
        (
            "Требования к кандидату",
            (
                field("Квалификация", raw.get("qualification")),
                field("Образование", requirement.get("education")),
                field("Требования к навыкам и инструментам", skills),
                field("Медицинские документы", raw.get("medicalDocuments")),
                field("Медицинская справка", raw.get("medicalCertificate")),
                _formatted_text(raw.get("requirements")),
            ),
        ),
        (
            "Данные по вакансии",
            (
                field("Типовая позиция", raw.get("typicalPosition")),
                field("Сфера деятельности", (raw.get("category") or {}).get("specialisation")),
                field("Адрес рабочего места", addresses),
                field("Занятость", raw.get("employment")),
                field("График", raw.get("schedule")),
                field("Уточнение графика", raw.get("scheduleTypeComment")),
            ),
        ),
        (
            "Условия работы и льготы",
            (
                field("Условия труда", raw.get("conditions")),
                field("Льготы", raw.get("benefit")),
                _formatted_text(raw.get("benefitDetails")),
                _formatted_text((raw.get("term") or {}).get("text")),
                field("Вакансия для категории", raw.get("social_protected")),
                _formatted_text(requirement.get("qualification")),
            ),
        ),
    )
    blocks = []
    for title, lines in sections:
        body = "\n".join(dict.fromkeys(line for line in lines if line))
        if body:
            blocks.append(f"{title}\n{body}")
    return "\n\n".join(blocks)


class TrudvsemConnector(HttpConnector):

    name = "trudvsem"
    base_url = "https://opendata.trudvsem.ru/api/v1/vacancies"
    timeout = 60.0
    queries = ("python", "программист", "разработчик")
    page_size = 50

    def fetch(self, max_pages: int = 1) -> Iterator[NormalizedVacancy]:
        seen: set[str] = set()
        for query in self.queries:
            for page in range(max_pages):
                if page or query != self.queries[0]:
                    time.sleep(self.page_delay)
                payload = self.get_json(self.base_url, {"text": query, "limit": self.page_size, "offset": page})
                if str(payload.get("status")) != "200":
                    raise SourceUnavailable(f"{self.name}: API вернул статус {payload.get('status')}")
                results = payload.get("results")
                items = results.get("vacancies") if isinstance(results, dict) else None
                if not isinstance(items, list):
                    raise SourceUnavailable(f"{self.name}: API не вернул список вакансий")
                for item in items:
                    try:
                        vacancy = self.normalize(item["vacancy"])
                    except (AttributeError, KeyError, TypeError, ValueError) as exc:
                        log.warning("%s: пропущена запись: %s", self.name, exc)
                        continue
                    if vacancy.external_id not in seen:
                        seen.add(vacancy.external_id)
                        yield vacancy
                if len(items) < self.page_size:
                    break

    def normalize(self, raw: dict) -> NormalizedVacancy:
        requirement = raw.get("requirement") or {}
        description = _vacancy_description(raw, requirement)
        location = (raw.get("region") or {}).get("name")
        if not location:
            addresses = (raw.get("addresses") or {}).get("address") or []
            location = next(
                (address["location"] for address in addresses if isinstance(address, dict) and address.get("location")),
                None,
            )
        schedule = (raw.get("schedule") or "").strip().lower()
        employment = (raw.get("employment") or "").strip().lower()
        work_format = detect_work_format(
            "удал" in f"{schedule} {employment}", f"{raw['job-name']} {description}", bool(location)
        )
        low, high = positive_salary(raw.get("salary_min")), positive_salary(raw.get("salary_max"))
        currency = (raw.get("currency") or "руб").lower()
        if "руб" not in currency and currency.strip("«». ") not in {"rub", "rur", "₽"}:
            low = high = None
        if low and high and high < low:
            low, high = high, low

        url = raw["vac_url"]
        parsed_url = urlsplit(url)
        if not raw["id"] or parsed_url.scheme not in {"http", "https"} or not parsed_url.hostname:
            raise ValueError("отсутствует ID или ссылка на вакансию")
        return NormalizedVacancy(
            source=self.name,
            external_id=str(raw["id"]),
            url=url,
            title=raw["job-name"],
            company=raw["company"]["name"],
            location=location,
            work_format=work_format,
            employment_types=[EMPLOYMENT_MAP[employment]] if employment in EMPLOYMENT_MAP else [],
            schedule=SCHEDULES.get(schedule),
            experience_years_min=requirement.get("experience"),
            salary_min=low,
            salary_max=high,
            salary_currency="RUB" if low or high else None,
            description_text=description,
            tags=[item for item in raw.get("skills") or [] if isinstance(item, str)],
            published_at=datetime.fromisoformat(raw.get("creation-date") or raw["date_modify"]),
        )
