from abc import ABC, abstractmethod
from typing import Iterator

from app.schemas import NormalizedVacancy


class SourceUnavailable(Exception):
    """Сделать"""


class BaseConnector(ABC):
    name: str
    base_url: str

    @abstractmethod
    def fetch(self, max_pages: int = 1) -> Iterator[NormalizedVacancy]:
        """Сделать"""
