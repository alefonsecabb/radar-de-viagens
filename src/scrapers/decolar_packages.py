"""
Decolar.com — pacotes voo + hotel em promoção.
Site tem Cloudflare agressivo; usa Playwright + playwright-stealth.
"""
from __future__ import annotations

from datetime import date

from bs4 import BeautifulSoup

from src.scrapers._playwright_helpers import fetch_page_content
from src.scrapers.base_scraper import BaseScraper, Deal
from src.utils.config import PASSENGERS
from src.utils.logger import get_logger

logger = get_logger(__name__)

PROMO_URL = "https://www.decolar.com/ofertas/pacotes"


class DecolarPackagesScraper(BaseScraper):
    limiter_key = "packages"

    def _fetch(self) -> list[Deal]:
        html = fetch_page_content(
            PROMO_URL,
            wait_selector="[class*='offer'], [class*='package'], [class*='deal']",
        )
        if not html:
            return []

        soup = BeautifulSoup(html, "lxml")
        deals = []
        today = date.today().isoformat()

        cards = (
            soup.select("[class*='offer-card'], [class*='OfferCard']")
            or soup.select("[class*='package-card']")
            or soup.select("[data-testid*='offer']")
        )

        for card in cards[:8]:
            price_el = card.select_one("[class*='price'], [class*='valor'], [class*='Price']")
            dest_el  = card.select_one("[class*='destination'], [class*='city'], [class*='destino']")
            link_el  = card.select_one("a[href]")
            nights_el= card.select_one("[class*='night'], [class*='noite'], [class*='duration']")

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

            dest   = dest_el.get_text(strip=True) if dest_el else "Destino"
            nights = 0
            if nights_el:
                for part in nights_el.get_text(strip=True).split():
                    if part.isdigit():
                        nights = int(part)
                        break

            url = link_el["href"] if link_el else PROMO_URL
            if url.startswith("/"):
                url = "https://www.decolar.com" + url

            deals.append(Deal(
                type="package",
                title=f"Pacote Decolar — {dest} ({nights or '?'} noites)",
                price_brl=round(price_brl / PASSENGERS, 2),
                total_3pax_brl=price_brl,
                source="decolar",
                booking_url=url,
                retrieved_at=today,
                destination=dest,
                nights=nights,
            ))

        logger.info(f"Decolar: {len(deals)} pacotes encontrados")
        return deals
