"""
Azul Linhas Aéreas — scraper da página de promoções.
Hub principal em VCP (Viracopos), com muitas rotas exclusivas.
URL alvo: https://www.voeazul.com.br/br/pt/home/passagens/promocoes
"""
from __future__ import annotations

from datetime import date

from src.scrapers.base_scraper import BaseScraper, Deal
from src.scrapers._playwright_helpers import fetch_page_content
from src.utils.config import PASSENGERS
from src.utils.logger import get_logger

from bs4 import BeautifulSoup

logger = get_logger(__name__)

PROMO_URL = "https://www.voeazul.com.br/br/pt/home/passagens/promocoes"


class AzulFlightsScraper(BaseScraper):
    limiter_key = "airlines"

    def _fetch(self) -> list[Deal]:
        html = fetch_page_content(PROMO_URL, wait_selector=".promo-card, .offer-card, [class*='promo']")
        if not html:
            return []

        soup = BeautifulSoup(html, "lxml")
        deals = []
        today = date.today().isoformat()

        # A estrutura pode variar — tentamos vários seletores comuns
        cards = (
            soup.select("[class*='promo-card']")
            or soup.select("[class*='offer']")
            or soup.select("[class*='deal']")
        )

        for card in cards[:10]:
            price_el = card.select_one("[class*='price'], [class*='valor'], [class*='tarifa']")
            dest_el  = card.select_one("[class*='dest'], [class*='city'], [class*='destino']")
            link_el  = card.select_one("a[href]")

            if not price_el:
                continue

            price_text = price_el.get_text(strip=True).replace("R$", "").replace(".", "").replace(",", ".").strip()
            try:
                price_brl = float(price_text)
            except ValueError:
                continue

            destination = dest_el.get_text(strip=True) if dest_el else "Destino Azul"
            url = link_el["href"] if link_el else PROMO_URL
            if url.startswith("/"):
                url = "https://www.voeazul.com.br" + url

            deals.append(Deal(
                type="flight",
                title=f"VCP → {destination} — Azul (promoção)",
                price_brl=price_brl,
                total_3pax_brl=round(price_brl * PASSENGERS, 2),
                source="azul",
                booking_url=url,
                retrieved_at=today,
                origin="VCP",
                destination=destination,
                airline="Azul",
            ))

        logger.info(f"Azul: {len(deals)} promoções encontradas")
        return deals
