"""
MSC Cruzeiros — scraper de promoções e cruzeiros de reposicionamento.
Foco especial em transatlânticos (Santos/Rio → Europa) nos períodos mar-abr e out-nov.
"""
from __future__ import annotations

from datetime import date

from bs4 import BeautifulSoup

from src.scrapers._playwright_helpers import fetch_page_content
from src.scrapers.base_scraper import BaseScraper, Deal
from src.utils.config import PASSENGERS
from src.utils.logger import get_logger

logger = get_logger(__name__)

PROMO_URL = "https://www.msccruises.com.br/cruzeiros/promocoes"
REPOSITIONING_URL = "https://www.msccruises.com.br/cruzeiros/transatlantico"


class MscCruisesScraper(BaseScraper):
    limiter_key = "cruises"

    def _fetch(self) -> list[Deal]:
        deals = []
        for url, is_repo in [(REPOSITIONING_URL, True), (PROMO_URL, False)]:
            try:
                html = fetch_page_content(url, wait_selector="[class*='cruise'], [class*='card'], [class*='offer']")
                deals.extend(self._parse(html, url, is_repo))
            except Exception as exc:
                logger.warning(f"MSC ({url}): {exc}")
        return deals

    def _parse(self, html: str, source_url: str, is_repositioning: bool) -> list[Deal]:
        if not html:
            return []
        soup = BeautifulSoup(html, "lxml")
        deals = []
        today = date.today().isoformat()

        cards = (
            soup.select("[class*='cruise-card'], [class*='CruiseCard']")
            or soup.select("[class*='offer-card'], [class*='OfferCard']")
            or soup.select("article")
        )

        for card in cards[:8]:
            price_el = card.select_one("[class*='price'], [class*='valor'], [class*='tarifa']")
            name_el  = card.select_one("[class*='ship'], [class*='navio'], [class*='name']")
            nights_el= card.select_one("[class*='nights'], [class*='noites'], [class*='duration']")
            dept_el  = card.select_one("[class*='departure'], [class*='saida'], [class*='port']")
            arr_el   = card.select_one("[class*='arrival'], [class*='chegada']")
            link_el  = card.select_one("a[href]")
            date_el  = card.select_one("[class*='date'], [class*='data']")

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

            ship      = name_el.get_text(strip=True) if name_el else "MSC"
            dept_port = dept_el.get_text(strip=True) if dept_el else "Santos"
            arr_port  = arr_el.get_text(strip=True) if arr_el else "Europa"
            dep_date  = date_el.get_text(strip=True) if date_el else ""
            nights    = 0
            if nights_el:
                txt = nights_el.get_text(strip=True)
                for part in txt.split():
                    if part.isdigit():
                        nights = int(part)
                        break

            url = link_el["href"] if link_el else source_url
            if url.startswith("/"):
                url = "https://www.msccruises.com.br" + url

            deal_type = "cruise_repositioning" if is_repositioning else "package"
            title = (
                f"MSC Reposicionamento — {dept_port} → {arr_port} ({nights} noites)"
                if is_repositioning
                else f"MSC Cruzeiro — {dept_port} ({nights} noites)"
            )

            deals.append(Deal(
                type=deal_type,
                title=title,
                price_brl=price_brl,
                total_3pax_brl=round(price_brl * PASSENGERS, 2),
                source="msc",
                booking_url=url,
                retrieved_at=today,
                ship=ship,
                departure_port=dept_port,
                arrival_port=arr_port,
                nights=nights,
                outbound_date=dep_date,
                is_repositioning=is_repositioning,
            ))

        return deals
