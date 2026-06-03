"""
Swiss International Air Lines — ofertas para a Europa.
Grupo Lufthansa; excelente para rotas via Zurique/Genebra.
URL alvo: https://www.swiss.com/br/pt/book/special-offers
"""
from __future__ import annotations

from datetime import date

from bs4 import BeautifulSoup

from src.scrapers._playwright_helpers import fetch_page_content
from src.scrapers.base_scraper import BaseScraper, Deal
from src.utils.config import PASSENGERS
from src.utils.logger import get_logger

logger = get_logger(__name__)

PROMO_URL = "https://www.swiss.com/br/pt/book/special-offers"


class SwissFlightsScraper(BaseScraper):
    limiter_key = "airlines"

    def _fetch(self) -> list[Deal]:
        html = fetch_page_content(PROMO_URL, wait_selector="[class*='offer'], [class*='deal'], [class*='fare']")
        if not html:
            return []

        soup = BeautifulSoup(html, "lxml")
        deals = []
        today = date.today().isoformat()

        cards = (
            soup.select("[class*='offer-item'], [class*='OfferItem']")
            or soup.select("[class*='deal'], [class*='promo']")
            or soup.select("[class*='fare-teaser']")
        )

        for card in cards[:10]:
            price_el = card.select_one("[class*='price'], [class*='amount'], [class*='fare']")
            dest_el  = card.select_one("[class*='destination'], [class*='city'], [class*='location']")
            link_el  = card.select_one("a[href]")

            if not price_el:
                continue

            price_text = (
                price_el.get_text(strip=True)
                .replace("CHF", "").replace("EUR", "").replace("R$", "").replace("€", "")
                .replace(".", "").replace(",", ".").strip()
            )
            try:
                price_brl = float(price_text)
                # Converte CHF/EUR se necessário (valores < 2000 provavelmente em moeda estrangeira)
                if price_brl < 500:
                    price_brl *= 6.2
            except ValueError:
                continue

            destination = dest_el.get_text(strip=True) if dest_el else "Zurique / Europa"
            url = link_el["href"] if link_el else PROMO_URL
            if url.startswith("/"):
                url = "https://www.swiss.com" + url

            deals.append(Deal(
                type="flight",
                title=f"GRU → {destination} — Swiss (promoção)",
                price_brl=price_brl,
                total_3pax_brl=round(price_brl * PASSENGERS, 2),
                source="swiss",
                booking_url=url,
                retrieved_at=today,
                origin="GRU",
                destination=destination,
                airline="Swiss",
            ))

        logger.info(f"Swiss: {len(deals)} promoções encontradas")
        return deals
