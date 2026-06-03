"""
CVC — pacotes de viagem (maior operadora do Brasil).
Usa Playwright para contornar bloqueios 403.
"""
from __future__ import annotations

from datetime import date

from bs4 import BeautifulSoup

from src.scrapers._playwright_helpers import fetch_page_content
from src.scrapers.base_scraper import BaseScraper, Deal
from src.utils.config import PASSENGERS
from src.utils.logger import get_logger

logger = get_logger(__name__)

PROMO_URL = "https://www.cvc.com.br/pacotes/"


class CvcPackagesScraper(BaseScraper):
    limiter_key = "packages"

    def _fetch(self) -> list[Deal]:
        html = fetch_page_content(
            PROMO_URL,
            wait_selector="[class*='offer'], [class*='card'], [class*='pacote'], article",
        )
        if not html:
            return []

        soup = BeautifulSoup(html, "lxml")
        deals = []
        today = date.today().isoformat()

        cards = (
            soup.select(".offer-card, .product-card, .package-card")
            or soup.select("[class*='offer'], [class*='pacote']")
            or soup.select("article")
        )

        for card in cards[:8]:
            price_el = card.select_one("[class*='price'], [class*='valor'], .price")
            dest_el  = card.select_one("[class*='destination'], [class*='destino'], .destination, h3")
            link_el  = card.select_one("a[href]")
            nights_el= card.select_one("[class*='nights'], [class*='noites']")

            if not price_el:
                continue

            price_text = (
                price_el.get_text(strip=True)
                .replace("R$", "").replace(".", "").replace(",", ".").strip()
            )
            try:
                price_brl = float(price_text)
            except ValueError:
                continue

            dest   = dest_el.get_text(strip=True) if dest_el else "Destino CVC"
            nights = 0
            if nights_el:
                for part in nights_el.get_text(strip=True).split():
                    if part.isdigit():
                        nights = int(part)
                        break

            url = link_el["href"] if link_el else PROMO_URL
            if url.startswith("/"):
                url = "https://www.cvc.com.br" + url

            deals.append(Deal(
                type="package",
                title=f"Pacote CVC — {dest} ({nights or '?'} noites)",
                price_brl=round(price_brl / PASSENGERS, 2),
                total_3pax_brl=price_brl,
                source="cvc",
                booking_url=url,
                retrieved_at=today,
                destination=dest,
                nights=nights,
            ))

        logger.info(f"CVC: {len(deals)} pacotes encontrados")
        return deals
