import json
from pathlib import Path

import httpx
import pytest

from app.connectors import ArbeitnowConnector, SourceUnavailable

FIXTURE = json.loads((Path(__file__).parent / "fixtures" / "arbeitnow_page1.json").read_text())


def make(handler):
    client = httpx.Client(transport=httpx.MockTransport(handler))
    return ArbeitnowConnector(client=client, retry_wait=0, page_delay=0)


def test_normalization_and_skip_broken_record():
    c = make(lambda req: httpx.Response(200, json=FIXTURE))
    items = list(c.fetch())
    assert [i.external_id for i in items] == ["python-dev-berlin-123", "ml-eng-munich-456"]  
    v = items[0]
    assert v.company == "Acme GmbH"                       
    assert v.description_text == "We use FastAPI and PostgreSQL. Docker"  
    assert v.tags == ["software development", "python"]  
    assert v.work_format == "remote" and v.published_at.tzinfo is not None
    assert v.employment_types == ["full_time"]
    assert items[1].work_format == "onsite"
    assert v.dedup_key == "acmegmbh:juniorpythondevelopermfd"
    assert len(v.content_hash) == 64


def test_retries_on_5xx_then_succeeds():
    calls = {"n": 0}

    def handler(req):
        calls["n"] += 1
        return httpx.Response(503) if calls["n"] < 3 else httpx.Response(200, json=FIXTURE)

    assert len(list(make(handler).fetch())) == 2 and calls["n"] == 3


def test_source_down_raises_source_unavailable():
    with pytest.raises(SourceUnavailable):
        list(make(lambda req: httpx.Response(500)).fetch())


def test_timeout_is_handled():
    def handler(req):
        raise httpx.ConnectTimeout("t")

    with pytest.raises(SourceUnavailable):
        list(make(handler).fetch())


def test_follows_pagination():
    seen = []

    def handler(req):
        seen.append(str(req.url))
        page2 = {"data": [], "links": {"next": None}}
        return httpx.Response(200, json=FIXTURE if "page=2" not in str(req.url) else page2)

    list(make(handler).fetch(max_pages=2))
    assert seen[1].endswith("page=2")


def test_hybrid_detected_from_text():
    raw = {"slug": "h1", "company_name": "C", "title": "Dev", "description": "<p>Hybrid, 3 days in office</p>",
           "remote": False, "url": "https://x", "location": "Berlin", "created_at": 1759650000, "job_types": ["Part Time"]}
    v = ArbeitnowConnector(client=httpx.Client()).normalize(raw)
    assert v.work_format == "hybrid" and v.employment_types == ["part_time"]
