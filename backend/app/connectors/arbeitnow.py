import logging
import time
from datetime import datetime, timezone
from typing import Iterator, Optional

import httpx
from bs4 import BeautifulSoup
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.config import settings
from app.connectors.base import BaseConnector, SourceUnavailable
from app.schemas import NormalizedVacancy
from app.schemas.vacancy import detect_work_format

log = logging.getLogger(__name__)


class _Transient(Exception):
    pass


def html_to_text(html: str) -> str:
    return " ".join(BeautifulSoup(html or "", "html.parser").get_text(" ").split())


class ArbeitnowConnector(BaseConnector):
    name = "arbeitnow"
    base_url = "https://arbeitnow.com/api/job-board-api"

    def __init__(self, client: Optional[httpx.Client] = None, retry_wait: float = 1.0, page_delay: float = 0.5):
        self.client = client or httpx.Client(timeout=settings.http_timeout, headers={"User-Agent": settings.user_agent})
        self.page_delay = page_delay
        self._get = retry(
            retry=retry_if_exception_type(_Transient),
            stop=stop_after_attempt(settings.http_retries),
            wait=wait_exponential(multiplier=retry_wait, max=10),
            reraise=True,
        )(self._get_once)

    def _get_once(self, url: str) -> dict:
        try:
            resp = self.client.get(url, follow_redirects=True)
        except (httpx.TimeoutException, httpx.TransportError) as e:
            raise _Transient(str(e)) from e
        if resp.status_code == 429 or resp.status_code >= 500:
            raise _Transient(f"HTTP {resp.status_code}")
        if resp.status_code != 200:
            raise SourceUnavailable(f"{self.name}: HTTP {resp.status_code}")
        try:
            return resp.json()
        except ValueError as e:
            raise SourceUnavailable(f"{self.name}: невалидный JSON") from e

    def fetch(self, max_pages: int = 1) -> Iterator[NormalizedVacancy]:
        url: Optional[str] = self.base_url
        for page in range(max_pages):
            if not url:
                return
            try:
                payload = self._get(url)
            except _Transient as e:
                raise SourceUnavailable(f"{self.name}: недоступен после ретраев ({e})") from e
            for raw in payload.get("data", []):
                try:
                    yield self.normalize(raw)
                except (KeyError, ValueError, TypeError) as e:  
                    log.warning("%s: пропущена запись %r: %s", self.name, raw.get("slug"), e)
            url = (payload.get("links") or {}).get("next")
            if url and page < max_pages - 1:
                time.sleep(self.page_delay)

    def normalize(self, raw: dict) -> NormalizedVacancy:
        text = html_to_text(raw.get("description", ""))
        return NormalizedVacancy(
            source=self.name,
            external_id=str(raw["slug"]),
            url=raw["url"],
            title=raw["title"],
            company=raw["company_name"],
            location=raw.get("location") or None,
            work_format=detect_work_format(
                raw.get("remote"), f"{raw.get('title', '')} {text}", bool(raw.get("location"))
            ),
            employment_types=raw.get("job_types") or [],
            description_text=text,
            tags=raw.get("tags") or [],
            published_at=datetime.fromtimestamp(int(raw["created_at"]), tz=timezone.utc),
        )
