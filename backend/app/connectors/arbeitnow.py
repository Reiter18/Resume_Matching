import logging
import time
from datetime import datetime, timezone
from typing import Iterator, Optional

from app.connectors.base import HttpConnector, html_to_text
from app.schemas import NormalizedVacancy
from app.schemas.vacancy import detect_work_format

log = logging.getLogger(__name__)


class ArbeitnowConnector(HttpConnector):
    name = "arbeitnow"
    base_url = "https://arbeitnow.com/api/job-board-api"

    def fetch(self, max_pages: int = 1) -> Iterator[NormalizedVacancy]:
        url: Optional[str] = self.base_url
        for page in range(max_pages):
            if not url:
                return
            payload = self.get_json(url)
            for raw in payload.get("data", []):
                try:
                    yield self.normalize(raw)
                except (KeyError, ValueError, TypeError) as e:
                    log.warning(
                        "%s: пропущена запись %r: %s", self.name, raw.get("slug") if isinstance(raw, dict) else None, e
                    )
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
