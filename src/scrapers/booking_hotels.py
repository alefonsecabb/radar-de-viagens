"""
Booking.com — busca hotéis baratos em destinos populares via requests + BS4.
Monitora as páginas de listagem com parâmetros de baixa temporada.
"""
from __future__ import annotations

from datetime import date, timedelta

from bs4 import BeautifulSoup

from src.scrapers.base_scraper import BaseScraper, Deal
from src.utils.config import PASSENGERS
from src.utils.http_client import build_session
from src.utils.logger import get_logger
from src.utils.rate_limiter import LIMITERS

logger = get_logger(__name__)

# Destinos a verificar (slug da URL do Booking)
DESTINATIONS = [
    ("Lisboa", "pt/lisboa"),
    ("Madrid", "es/madri"),
    ("Paris", "fr/paris"),
    ("Roma", "it/roma"),
    ("Barcelona", "es/barcelona"),
    ("Praga", "cz/praga"),
    ("Viena", "at/viena"),
    ("Amsterdã", "nl/amsterda"),
    ("Bangkok", "th/bangkok"),
    ("Cancún", "mx/cancun"),
]

BASE_URL = "https://www.booking.com/searchresults/pt-br.html"


class BookingHotelsScraper(BaseScraper):
    limiter_key = "booking"

    def __init__(self) -> None:
        super().__init__()
        self._session = build_session()

    def _fetch(self) -> list[Deal]:
        deals = []
        check_in  = (date.today() + timedelta(days=60)).isoformat()
        check_out = (date.today() + timedelta(days=67)).isoformat()

        for city_name, ss in DESTINATIONS[:5]:  # 5 destinos por execução
            LIMITERS["booking"].acquire()
            try:
                deals.extend(self._search_city(city_name, ss, check_in, check_out))
            except Exception as exc:
                logger.warning(f"Booking ({city_name}): {exc}")
        return deals

    def _search_city(self, city: str, ss: str, check_in: str, check_out: str) -> list[Deal]:
        params = {
            "ss": ss,
            "checkin": check_in,
            "checkout": check_out,
            "group_adults": PASSENGERS,
            "no_rooms": 1,
            "order": "price",
            "nflt": "ht_id%3D204",  # apenas hotéis
        }
        resp = self._session.get(BASE_URL, params=params, timeout=15)
        resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "lxml")
        deals = []
        today = date.today().isoformat()

        cards = soup.select('[data-testid="property-card"]')[:5]
        for card in cards:
            name_el  = card.select_one('[data-testid="title"]')
            price_el = card.select_one('[data-testid="price-and-discounted-price"]')
            link_el  = card.select_one('a[data-testid="title-link"]')
            stars_el = card.select_one('[aria-label*="estrelas"], [aria-label*="stars"]')

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

            name  = name_el.get_text(strip=True) if name_el else city
            url   = link_el["href"] if link_el else ""
            stars = 0
            if stars_el:
                txt = stars_el.get("aria-label", "")
                for ch in txt:
                    if ch.isdigit():
                        stars = int(ch)
                        break

            deals.append(Deal(
                type="hotel",
                title=f"{name} — {city} (7 noites)",
                price_brl=round(price_brl / 7, 2),
                total_3pax_brl=round(price_brl, 2),
                source="booking",
                booking_url=url,
                retrieved_at=today,
                destination=city,
                hotel_name=name,
                hotel_stars=stars,
                nights=7,
                outbound_date=check_in,
                return_date=check_out,
            ))

        return deals
