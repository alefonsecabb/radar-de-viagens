"""
PassagensPromo.com.br — agrega promoções de passagens aéreas publicadas
por companhias e agências. HTML estático, sem API key.
"""
from __future__ import annotations

from datetime import date

from bs4 import BeautifulSoup

from src.scrapers.base_scraper import BaseScraper, Deal
from src.utils.config import PASSENGERS
from src.utils.http_client import build_session
from src.utils.logger import get_logger

logger = get_logger(__name__)

BASE_URL = "https://www.passagenspromo.com.br"
FEED_URL = f"{BASE_URL}/passagens-aereas"


class PassagensPromoScraper(BaseScraper):
    limiter_key = "booking"

    def __init__(self) -> None:
        super().__init__()
        self._session = build_session()

    def _fetch(self) -> list[Deal]:
        try:
            resp = self._session.get(FEED_URL, timeout=15)
            resp.raise_for_status()
        except Exception as exc:
            logger.warning(f"PassagensPromo: {exc}")
            return []

        soup = BeautifulSoup(resp.text, "lxml")
        deals = []
        today = date.today().isoformat()

        cards = (
            soup.select("article.deal, article.promo, .deal-card")
            or soup.select("[class*='deal'], [class*='promo'], [class*='offer']")
            or soup.select("article")
        )

        for card in cards[:15]:
            title_el = card.select_one("h2, h3, [class*='title']")
            price_el  = card.select_one("[class*='price'], [class*='valor']")
            link_el   = card.select_one("a[href]")

            if not title_el:
                continue

            title = title_el.get_text(strip=True)

            price_brl = 0.0
            if price_el:
                txt = (
                    price_el.get_text(strip=True)
                    .replace("R$", "").replace(".", "").replace(",", ".").strip()
                )
                try:
                    price_brl = float(txt)
                except ValueError:
                    pass

            url = link_el["href"] if link_el else FEED_URL
            if url.startswith("/"):
                url = BASE_URL + url

            deals.append(Deal(
                type="flight",
                title=title,
                price_brl=price_brl if price_brl > 0 else 999.0,
                total_3pax_brl=round((price_brl if price_brl > 0 else 999.0) * PASSENGERS, 2),
                source="passagenspromo",
                booking_url=url,
                retrieved_at=today,
            ))

        logger.info(f"PassagensPromo: {len(deals)} promoções encontradas")
        return deals
