"""
Trivago — meta-buscador de hotéis (agrega Booking, Hotels.com, Expedia, etc.).
Usa Playwright pois os preços são carregados dinamicamente via JS.
"""
from __future__ import annotations

from datetime import date, timedelta

from bs4 import BeautifulSoup

from src.scrapers._playwright_helpers import fetch_page_content
from src.scrapers.base_scraper import BaseScraper, Deal
from src.utils.config import PASSENGERS
from src.utils.logger import get_logger

logger = get_logger(__name__)

DESTINATIONS = [
    ("Lisboa",    "br/hotel/pesquisa/lisbon-portugal"),
    ("Paris",     "br/hotel/pesquisa/paris-france"),
    ("Roma",      "br/hotel/pesquisa/rome-italy"),
    ("Bangkok",   "br/hotel/pesquisa/bangkok-thailand"),
    ("Cancún",    "br/hotel/pesquisa/cancun-mexico"),
]

BASE_URL = "https://www.trivago.com.br"


class TrivagoHotelsScraper(BaseScraper):
    limiter_key = "trivago"

    def _fetch(self) -> list[Deal]:
        check_in  = (date.today() + timedelta(days=60)).strftime("%Y-%m-%d")
        check_out = (date.today() + timedelta(days=67)).strftime("%Y-%m-%d")
        deals = []

        for city_name, path in DESTINATIONS[:3]:
            url = f"{BASE_URL}/{path}?checkin={check_in}&checkout={check_out}&adults={PASSENGERS}"
            try:
                deals.extend(self._scrape_city(city_name, url, check_in, check_out))
            except Exception as exc:
                logger.warning(f"Trivago ({city_name}): {exc}")
        return deals

    def _scrape_city(self, city: str, url: str, check_in: str, check_out: str) -> list[Deal]:
        html = fetch_page_content(url, wait_selector="[data-testid='hotel-item'], article, [class*='hotel']")
        if not html:
            return []

        soup = BeautifulSoup(html, "lxml")
        deals = []
        today = date.today().isoformat()

        cards = (
            soup.select("[data-testid='hotel-item']")
            or soup.select("article[class*='hotel']")
            or soup.select("li[class*='hotel']")
        )

        for card in cards[:5]:
            name_el  = card.select_one("[class*='name'], [class*='title'], h3, h2")
            price_el = card.select_one("[class*='price'], [class*='rate'], [data-qa='display-price']")
            link_el  = card.select_one("a[href]")

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

            name = name_el.get_text(strip=True) if name_el else city
            url_link = link_el["href"] if link_el else url
            if url_link.startswith("/"):
                url_link = BASE_URL + url_link

            deals.append(Deal(
                type="hotel",
                title=f"{name} — {city} (7 noites)",
                price_brl=round(price_brl / 7, 2),
                total_3pax_brl=round(price_brl, 2),
                source="trivago",
                booking_url=url_link,
                retrieved_at=today,
                destination=city,
                hotel_name=name,
                nights=7,
                outbound_date=check_in,
                return_date=check_out,
            ))

        return deals
