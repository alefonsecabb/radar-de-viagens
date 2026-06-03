from __future__ import annotations
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from src.utils.logger import get_logger
from src.utils.rate_limiter import LIMITERS


class ScraperUnavailableError(Exception):
    pass


@dataclass
class Deal:
    """Oferta de viagem normalizada de qualquer fonte."""
    type: str                    # flight | hotel | cruise_repositioning | package
    title: str
    price_brl: float
    total_3pax_brl: float
    source: str
    booking_url: str
    retrieved_at: str            # ISO8601
    outbound_date: str = ""
    return_date: str = ""
    nights: int = 0
    airline: str = ""
    origin: str = ""
    destination: str = ""
    stops: int = 0
    ship: str = ""
    departure_port: str = ""
    arrival_port: str = ""
    cabin_type: str = ""
    hotel_name: str = ""
    hotel_stars: int = 0
    is_repositioning: bool = False
    score: float = 0.0
    discount_pct: float = 0.0
    label: str = ""
    stale: bool = False
    extra: dict[str, Any] = field(default_factory=dict)


class BaseScraper(ABC):
    """Classe abstrata com retry, rate limiting e fallback flag."""

    limiter_key: str = "packages"
    max_retries: int = 3

    def __init__(self) -> None:
        self.logger = get_logger(self.__class__.__name__)
        self.is_available = True
        self._fail_count = 0

    @abstractmethod
    def _fetch(self) -> list[Deal]:
        ...

    def fetch(self) -> list[Deal]:
        limiter = LIMITERS.get(self.limiter_key)
        for attempt in range(1, self.max_retries + 1):
            try:
                if limiter:
                    limiter.acquire()
                results = self._fetch()
                self._fail_count = 0
                self.is_available = True
                self.logger.info(f"{self.__class__.__name__}: {len(results)} deals encontrados")
                return results
            except ScraperUnavailableError:
                raise
            except Exception as exc:
                self._fail_count += 1
                wait = 2 ** attempt
                self.logger.warning(
                    f"{self.__class__.__name__}: tentativa {attempt}/{self.max_retries} falhou — {exc}. "
                    f"Aguardando {wait}s..."
                )
                if attempt < self.max_retries:
                    time.sleep(wait)
        self.is_available = False
        raise ScraperUnavailableError(
            f"{self.__class__.__name__} indisponível após {self.max_retries} tentativas"
        )
