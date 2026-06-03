"""
MelhoresDestinos.com.br — blog/agregador de promoções de passagens e pacotes,
muito popular no Brasil. Publica alertas de erro de preço e promoções relâmpago.
"""
from __future__ import annotations

from datetime import date

from bs4 import BeautifulSoup

from src.scrapers.base_scraper import BaseScraper, Deal
from src.utils.config import PASSENGERS
from src.utils.http_client import build_session
from src.utils.logger import get_logger

logger = get_logger(__name__)

BASE_URL = "https://www.melhoresdestinos.com.br"
FEED_URL = f"{BASE_URL}/passagens-aereas"


class MelhoresDestinosScraper(BaseScraper):
    limiter_key = "booking"

    def __init__(self) -> None:
        super().__init__()
        self._session = build_session()

    def _fetch(self) -> list[Deal]:
        for url in [FEED_URL, BASE_URL]:
            try:
                resp = self._session.get(url, timeout=15)
                resp.raise_for_status()
                deals = self._parse(resp.text)
                if deals:
                    return deals
            except Exception as exc:
                logger.warning(f"MelhoresDestinos ({url}): {exc}")
        return []

    def _parse(self, html: str) -> list[Deal]:
        soup = BeautifulSoup(html, "lxml")
        deals = []
        today = date.today().isoformat()

        cards = (
            soup.select("article.post, article.deal")
            or soup.select("[class*='post'], [class*='deal']")
            or soup.select("article")
        )

        for card in cards[:15]:
            title_el = card.select_one("h2, h3, .entry-title, [class*='title']")
            price_el  = card.select_one("[class*='price'], [class*='valor'], strong, b")
            link_el   = card.select_one("a[href]")

            if not title_el:
                continue

            title = title_el.get_text(strip=True)
            if not any(kw in title.lower() for kw in ["passagem", "voo", "promoç", "r$", "hotel", "cruzeiro", "pacote"]):
                continue

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

            deals.append(Deal(
                type="flight",
                title=title,
                price_brl=price_brl,
                total_3pax_brl=round(price_brl * PASSENGERS, 2),
                source="melhores_destinos",
                booking_url=url,
                retrieved_at=today,
            ))

        logger.info(f"MelhoresDestinos: {len(deals)} promoções encontradas")
        return deals
