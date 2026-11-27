from abc import ABC, abstractmethod
from typing import Iterator, Optional

import httpx
from bs4 import BeautifulSoup
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.config import settings
from app.schemas import NormalizedVacancy


class SourceUnavailable(Exception):
    """Источник недоступен/сломался. Ловится ингестором: падение одного источника не валит остальные."""


class BaseConnector(ABC):
    name: str
    base_url: str

    @abstractmethod
    def fetch(self, max_pages: int = 1) -> Iterator[NormalizedVacancy]:
        """Отдаёт вакансии в нормализованном виде. При недоступности источника - SourceUnavailable."""


class _Transient(Exception):
    pass


class HttpConnector(BaseConnector):

    timeout: Optional[float] = None  

    def __init__(self, client: Optional[httpx.Client] = None, retry_wait: float = 1.0, page_delay: float = 0.5):
        self.client = client or httpx.Client(
            timeout=self.timeout or settings.http_timeout, headers={"User-Agent": settings.user_agent}
        )
        self.page_delay = page_delay
        self._get = retry(
            retry=retry_if_exception_type(_Transient),
            stop=stop_after_attempt(settings.http_retries),
            wait=wait_exponential(multiplier=retry_wait, max=10),
            reraise=True,
        )(self._get_once)

    def _get_once(self, url: str, params: Optional[dict] = None) -> dict:
        try:
            resp = self.client.get(url, params=params, follow_redirects=True)
        except httpx.TransportError as e:
            raise _Transient(str(e)) from e
        if resp.status_code == 429 or resp.status_code >= 500:
            raise _Transient(f"HTTP {resp.status_code}")
        if resp.status_code != 200:
            raise SourceUnavailable(f"{self.name}: HTTP {resp.status_code}")
        try:
            payload = resp.json()
        except ValueError as e:
            raise SourceUnavailable(f"{self.name}: невалидный JSON") from e

        if not isinstance(payload, dict):
            raise SourceUnavailable(f"{self.name}: ожидался JSON-объект")
        return payload

    def get_json(self, url: str, params: Optional[dict] = None) -> dict:
        try:
            return self._get(url, params)
        except _Transient as e:
            raise SourceUnavailable(f"{self.name}: недоступен после ретраев ({e})") from e


def html_to_text(html: str) -> str:
    text = html or ""
    for _ in range(2):  
        text = " ".join(BeautifulSoup(text, "html.parser").get_text(" ").split())
        if "<" not in text:
            break
    return text
