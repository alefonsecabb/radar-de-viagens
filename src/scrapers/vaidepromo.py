"""
VaiDePromo — um dos maiores agregadores de promoções de passagens do Brasil.
Publica deals em HTML acessível. Sem API key necessária.
"""
from __future__ import annotations

from datetime import date

from bs4 import BeautifulSoup

from src.scrapers._playwright_helpers import fetch_page_content
from src.scrapers.base_scraper import BaseScraper, Deal
from src.utils.config import PASSENGERS
from src.utils.logger import get_logger

logger = get_logger(__name__)

BASE_URL = "https://www.vaidepromo.com.br"
PROMO_URL = f"{BASE_URL}/passagens-aereas"


class VaiDePromoScraper(BaseScraper):
    limiter_key = "booking"

    def _fetch(self) -> list[Deal]:
        html = fetch_page_content(
            PROMO_URL,
            wait_selector="article, [class*='deal'], [class*='offer'], [class*='card']",
        )
        if not html:
            return []

        soup = BeautifulSoup(html, "lxml")
        deals = []
        today = date.today().isoformat()

        cards = (
            soup.select("article")
            or soup.select("[class*='deal-card'], [class*='DealCard']")
            or soup.select("[class*='offer-card']")
        )

        for card in cards[:15]:
            title_el = card.select_one("h2, h3, h4, [class*='title']")
            price_el  = card.select_one("[class*='price'], [class*='valor'], strong")
            link_el   = card.select_one("a[href]")
            origin_el = card.select_one("[class*='origin'], [class*='from']")
            dest_el   = card.select_one("[class*='dest'], [class*='to']")

            if not title_el and not price_el:
                continue

            title = title_el.get_text(strip=True) if title_el else "Promoção VaiDePromo"

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

            url = link_el["href"] if link_el else PROMO_URL
            if url.startswith("/"):
                url = BASE_URL + url

            origin = origin_el.get_text(strip=True) if origin_el else ""
            dest   = dest_el.get_text(strip=True) if dest_el else ""

            deals.append(Deal(
                type="flight",
                title=title,
                price_brl=price_brl if price_brl > 0 else 999.0,
                total_3pax_brl=round((price_brl if price_brl > 0 else 999.0) * PASSENGERS, 2),
                source="vaidepromo",
                booking_url=url,
                retrieved_at=today,
                origin=origin,
                destination=dest,
            ))

        logger.info(f"VaiDePromo: {len(deals)} promoções encontradas")
        return deals
