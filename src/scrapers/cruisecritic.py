"""
CruiseCritic — agrega cruzeiros de reposicionamento de múltiplas companhias.
Ótima fonte para encontrar transatlânticos baratos saindo das Américas.
HTML pré-renderizado → requests + BS4 suficiente.
"""
from __future__ import annotations

from datetime import date

from bs4 import BeautifulSoup

from src.scrapers.base_scraper import BaseScraper, Deal
from src.utils.config import PASSENGERS
from src.utils.http_client import build_session
from src.utils.logger import get_logger

logger = get_logger(__name__)

# Lista de cruzeiros de reposicionamento transatlânticos
REPO_URL = "https://www.cruisecritic.com/articles.cfm?ID=594"
SEARCH_URL = "https://www.cruisecritic.com/cruises/deals/"


class CruiseCriticScraper(BaseScraper):
    limiter_key = "cruises"

    def __init__(self) -> None:
        super().__init__()
        self._session = build_session()

    def _fetch(self) -> list[Deal]:
        deals = []
        for url in [REPO_URL, SEARCH_URL]:
            try:
                resp = self._session.get(url, timeout=15)
                resp.raise_for_status()
                deals.extend(self._parse(resp.text, url))
            except Exception as exc:
                logger.warning(f"CruiseCritic ({url}): {exc}")
        return deals

    def _parse(self, html: str, source_url: str) -> list[Deal]:
        soup = BeautifulSoup(html, "lxml")
        deals = []
        today = date.today().isoformat()

        # CruiseCritic usa estrutura de listagem variável
        cards = (
            soup.select(".listing-card, .cruise-listing")
            or soup.select("[class*='cruise-result']")
            or soup.select("article")
        )

        for card in cards[:8]:
            price_el = card.select_one("[class*='price'], [class*='rate'], [itemprop='price']")
            name_el  = card.select_one("[class*='ship-name'], [class*='cruise-name'], h3")
            nights_el= card.select_one("[class*='nights'], [class*='duration']")
            line_el  = card.select_one("[class*='cruise-line'], [class*='line-name']")
            link_el  = card.select_one("a[href]")

            if not price_el:
                continue

            price_text = (
                price_el.get_text(strip=True)
                .replace("$", "").replace(",", "").strip()
            )
            try:
                price_usd = float(price_text)
                price_brl = round(price_usd * 5.7, 2)
            except ValueError:
                continue

            ship  = name_el.get_text(strip=True) if name_el else "Cruzeiro"
            line  = line_el.get_text(strip=True) if line_el else ""
            nights = 0
            if nights_el:
                for part in nights_el.get_text(strip=True).split():
                    if part.isdigit():
                        nights = int(part)
                        break

            url = link_el["href"] if link_el else source_url
            if url.startswith("/"):
                url = "https://www.cruisecritic.com" + url

            deals.append(Deal(
                type="cruise_repositioning",
                title=f"{line} {ship} — Transatlântico ({nights} noites)",
                price_brl=price_brl,
                total_3pax_brl=round(price_brl * PASSENGERS, 2),
                source="cruisecritic",
                booking_url=url,
                retrieved_at=today,
                ship=ship,
                nights=nights,
                is_repositioning=True,
            ))

        return deals
