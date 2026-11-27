from datetime import datetime, timezone

import httpx
import pytest

from app.connectors import REGISTRY, SourceUnavailable, TrudvsemConnector


def vacancy(vacancy_id, **fields):
    return {
        "vacancy": {
            "id": vacancy_id,
            "vac_url": f"https://trudvsem.ru/vacancy/card/123/{vacancy_id}",
            "job-name": "Python-разработчик",
            "company": {"name": "Пример"},
            "region": {"name": "Пермский край"},
            "creation-date": "2026-11-11",
            "employment": "Дистанционная (удаленная) работа",
            "schedule": "Неполный рабочий день/неполная рабочая неделя",
            "salary_min": 40000,
            "salary_max": 60000,
            "currency": "«руб.»",
            "duty": "<p>Разработка на Python</p>",
            "requirements": "<ul><li>Знание SQL</li><li>Опыт с Docker</li></ul>",
            "qualification": "Middle",
            "requirement": {"experience": 3, "education": "Высшее образование"},
            "skills": ["PostgreSQL (Postgres)", "PostgreSQL (Postgres)"],
            **fields,
        }
    }


def connector(client):
    result = TrudvsemConnector(client, retry_wait=0, page_delay=0)
    result.queries = ("python", "разработчик")
    result.page_size = 2
    return result


def test_trudvsem_pagination_and_normalization():
    requests = []

    def handle(request):
        offset = int(request.url.params["offset"])
        query = request.url.params["text"]
        assert request.url.params["limit"] == "2"
        requests.append((query, offset))
        pages = {
            ("python", 0): [None, vacancy("remote")],
            ("python", 1): [
                vacancy("office", employment="Полная занятость", schedule="Полный рабочий день", salary_min=0)
            ],
            ("разработчик", 0): [vacancy("remote")],
        }
        return httpx.Response(200, json={"status": "200", "results": {"vacancies": pages[(query, offset)]}})

    with httpx.Client(transport=httpx.MockTransport(handle)) as client:
        remote, office = list(connector(client).fetch(max_pages=3))

    assert REGISTRY["trudvsem"] is TrudvsemConnector
    assert requests == [("python", 0), ("python", 1), ("разработчик", 0)]
    assert (remote.external_id, office.external_id) == ("remote", "office")
    assert remote.work_format == "remote" and remote.employment_types == []
    assert remote.location == "Пермский край"
    assert "Должностные обязанности\nРазработка на Python" in remote.description_text
    assert "Требования к навыкам и инструментам: PostgreSQL (Postgres)" in remote.description_text
    assert "• Знание SQL\n• Опыт с Docker" in remote.description_text
    assert remote.published_at == datetime(2026, 11, 11, tzinfo=timezone.utc)
    assert remote.experience_years_min == 3
    assert remote.tags == ["postgresql (postgres)"]
    assert (remote.salary_min, remote.salary_max, remote.salary_currency) == (40000, 60000, "RUB")
    assert office.work_format == "onsite"
    assert office.employment_types == ["full_time"] and office.schedule == "full_day"
    assert office.salary_min is None


@pytest.mark.parametrize("status, payload", [(503, {}), (200, {"status": "500"}), (200, {"status": "200"})])
def test_trudvsem_reports_source_failure(status, payload):
    with httpx.Client(transport=httpx.MockTransport(lambda _: httpx.Response(status, json=payload))) as client:
        with pytest.raises(SourceUnavailable):
            list(connector(client).fetch())


def test_trudvsem_keeps_duties_when_no_requirements_are_provided():
    raw = vacancy(
        "duties",
        requirements=None,
        qualification=None,
        requirement={"education": "Не указано"},
        skills=[],
        schedule=None,
        employment=None,
        addresses={"address": None},
    )["vacancy"]
    with httpx.Client() as client:
        assert connector(client).normalize(raw).description_text == "Должностные обязанности\nРазработка на Python"


def test_trudvsem_keeps_full_text_and_details_from_the_source():
    raw = vacancy(
        "details",
        duty="Первая строка\nВторая строка: C++ < 20",
        requirements="&lt;ul&gt;&lt;li&gt;Знать Git&lt;/li&gt;&lt;li&gt;Писать тесты&lt;/li&gt;&lt;/ul&gt;",
        requirement={"education": "Высшее", "qualification": "Оформление по ТК"},
        addresses={"address": [{"location": "Пермь, ул. Примерная, 1"}]},
        addressOffice="28",
        typicalPosition="Программист",
        category={"specialisation": "Информационные технологии"},
        conditions="Допустимые",
        benefit="Добровольное медицинское страхование",
        benefitDetails="<p>Полис после испытательного срока</p>",
        term={"text": "Компенсация проезда"},
    )["vacancy"]
    with httpx.Client() as client:
        description = connector(client).normalize(raw).description_text

    for text in (
        "Первая строка\nВторая строка: C++ < 20",
        "• Знать Git\n• Писать тесты",
        "Квалификация: Middle",
        "Типовая позиция: Программист",
        "Сфера деятельности: Информационные технологии",
        "Адрес рабочего места: Пермь, ул. Примерная, 1, офис 28",
        "Условия работы и льготы",
        "Полис после испытательного срока",
        "Добровольное медицинское страхование",
        "Компенсация проезда",
        "Оформление по ТК",
    ):
        assert text in description
    assert description.count("PostgreSQL (Postgres)") == 1
