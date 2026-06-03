"""
TAP Air Portugal — página de promoções para o Brasil.
Essencial para rotas GRU → Europa (Lisboa como hub).
URL alvo: https://www.flytap.com/pt-br/voos-baratos
"""
from __future__ import annotations

from datetime import date

from bs4 import BeautifulSoup

from src.scrapers._playwright_helpers import fetch_page_content
from src.scrapers.base_scraper import BaseScraper, Deal
from src.utils.config import PASSENGERS
from src.utils.logger import get_logger

logger = get_logger(__name__)

PROMO_URL = "https://www.flytap.com/pt-br/voos-baratos"


class TapFlightsScraper(BaseScraper):
    limiter_key = "airlines"

    def _fetch(self) -> list[Deal]:
        html = fetch_page_content(PROMO_URL, wait_selector="[class*='deal'], [class*='offer'], [class*='fare']")
        if not html:
            return []

        soup = BeautifulSoup(html, "lxml")
        deals = []
        today = date.today().isoformat()

        cards = (
            soup.select("[class*='deal-card'], [class*='DealCard']")
            or soup.select("[class*='fare-card'], [class*='FareCard']")
            or soup.select("[class*='offer']")
        )

        for card in cards[:10]:
            price_el = card.select_one("[class*='price'], [class*='Price'], [class*='amount']")
            dest_el  = card.select_one("[class*='destination'], [class*='city'], [class*='name']")
            link_el  = card.select_one("a[href]")

            if not price_el:
                continue

            price_text = (
                price_el.get_text(strip=True)
                .replace("R$", "").replace("EUR", "").replace("€", "")
                .replace(".", "").replace(",", ".").strip()
            )
            try:
                price_brl = float(price_text)
                # Se o preço vier em EUR, converte aproximadamente
                if price_brl < 500:
                    price_brl *= 6.0
            except ValueError:
                continue

            destination = dest_el.get_text(strip=True) if dest_el else "Lisboa / Europa"
            url = link_el["href"] if link_el else PROMO_URL
            if url.startswith("/"):
                url = "https://www.flytap.com" + url

            deals.append(Deal(
                type="flight",
                title=f"GRU → {destination} — TAP Portugal (promoção)",
                price_brl=price_brl,
                total_3pax_brl=round(price_brl * PASSENGERS, 2),
                source="tap",
                booking_url=url,
                retrieved_at=today,
                origin="GRU",
                destination=destination,
                airline="TAP",
            ))

        logger.info(f"TAP: {len(deals)} promoções encontradas")
        return deals
