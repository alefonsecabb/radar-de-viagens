"""
LATAM Airlines — página de ofertas e promoções.
URL alvo: https://www.latamairlines.com/br/pt/ofertas
"""
from __future__ import annotations

from datetime import date

from bs4 import BeautifulSoup

from src.scrapers._playwright_helpers import fetch_page_content
from src.scrapers.base_scraper import BaseScraper, Deal
from src.utils.config import PASSENGERS
from src.utils.logger import get_logger

logger = get_logger(__name__)

PROMO_URL = "https://www.latamairlines.com/br/pt/ofertas"


class LatamFlightsScraper(BaseScraper):
    limiter_key = "airlines"

    def _fetch(self) -> list[Deal]:
        html = fetch_page_content(PROMO_URL, wait_selector="[class*='offer'], [class*='deal'], [class*='promo']")
        if not html:
            return []

        soup = BeautifulSoup(html, "lxml")
        deals = []
        today = date.today().isoformat()

        cards = (
            soup.select("[class*='OfferCard'], [class*='offer-card']")
            or soup.select("[data-testid*='offer']")
            or soup.select("[class*='promo']")
        )

        for card in cards[:10]:
            price_el = card.select_one("[class*='price'], [class*='Price'], [class*='valor']")
            dest_el  = card.select_one("[class*='destination'], [class*='Destination'], [class*='city']")
            link_el  = card.select_one("a[href]")

            if not price_el:
                continue

            price_text = (
                price_el.get_text(strip=True)
                .replace("R$", "").replace("BRL", "")
                .replace(".", "").replace(",", ".").strip()
            )
            try:
                price_brl = float(price_text)
            except ValueError:
                continue

            destination = dest_el.get_text(strip=True) if dest_el else "Destino LATAM"
            url = link_el["href"] if link_el else PROMO_URL
            if url.startswith("/"):
                url = "https://www.latamairlines.com" + url

            deals.append(Deal(
                type="flight",
                title=f"GRU/CGH → {destination} — LATAM (promoção)",
                price_brl=price_brl,
                total_3pax_brl=round(price_brl * PASSENGERS, 2),
                source="latam",
                booking_url=url,
                retrieved_at=today,
                origin="GRU",
                destination=destination,
                airline="LATAM",
            ))

        logger.info(f"LATAM: {len(deals)} promoções encontradas")
        return deals
