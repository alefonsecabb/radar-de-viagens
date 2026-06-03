"""
Costa Cruzeiros — scraper de promoções e transatlânticos.
Também opera cruzeiros de reposicionamento nas temporadas de primavera/outono.
"""
from __future__ import annotations

from datetime import date

from bs4 import BeautifulSoup

from src.scrapers._playwright_helpers import fetch_page_content
from src.scrapers.base_scraper import BaseScraper, Deal
from src.utils.config import PASSENGERS
from src.utils.logger import get_logger

logger = get_logger(__name__)

PROMO_URL = "https://www.costacruises.com/en/offer-list.html"


class CostaCruisesScraper(BaseScraper):
    limiter_key = "cruises"

    def _fetch(self) -> list[Deal]:
        html = fetch_page_content(PROMO_URL, wait_selector="[class*='cruise'], [class*='offer'], [class*='card']")
        if not html:
            return []

        soup = BeautifulSoup(html, "lxml")
        deals = []
        today = date.today().isoformat()

        cards = (
            soup.select("[class*='cruise-card'], [class*='itinerary-card']")
            or soup.select("[class*='offer-item']")
            or soup.select("article")
        )

        for card in cards[:8]:
            price_el  = card.select_one("[class*='price'], [class*='valor']")
            name_el   = card.select_one("[class*='ship'], [class*='navio'], [class*='name']")
            nights_el = card.select_one("[class*='nights'], [class*='noites'], [class*='duration']")
            route_el  = card.select_one("[class*='route'], [class*='rota'], [class*='itinerary']")
            link_el   = card.select_one("a[href]")

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

            ship  = name_el.get_text(strip=True) if name_el else "Costa"
            route = route_el.get_text(strip=True) if route_el else ""
            nights = 0
            if nights_el:
                for part in nights_el.get_text(strip=True).split():
                    if part.isdigit():
                        nights = int(part)
                        break

            # Detecta cruzeiro de reposicionamento pelo texto da rota
            is_repo = any(kw in route.lower() for kw in ["transatl", "reposicion", "europa", "genova", "barcelona"])

            url = link_el["href"] if link_el else PROMO_URL
            if url.startswith("/"):
                url = "https://www.costacruises.com" + url

            deals.append(Deal(
                type="cruise_repositioning" if is_repo else "package",
                title=f"Costa {ship} — {route or 'Cruzeiro'} ({nights} noites)",
                price_brl=price_brl,
                total_3pax_brl=round(price_brl * PASSENGERS, 2),
                source="costa",
                booking_url=url,
                retrieved_at=today,
                ship=ship,
                nights=nights,
                is_repositioning=is_repo,
            ))

        return deals
