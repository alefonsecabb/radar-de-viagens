"""
Travelpayouts Data API (Aviasales) — passagens mais baratas por origem/destino.
API gratuita para afiliados. Cadastro em: https://www.travelpayouts.com/developers/api

Endpoints usados:
  /v1/prices/cheap  — tarifas mais baratas por mês, qualquer destino
  /v2/prices/latest — últimas tarifas encontradas saindo de uma origem
"""
from __future__ import annotations

from datetime import date, timedelta

import requests

from src.scrapers.base_scraper import BaseScraper, Deal, ScraperUnavailableError
from src.utils.config import KIWI_API_KEY as TP_TOKEN, ORIGIN_AIRPORTS, PASSENGERS
from src.utils.logger import get_logger

logger = get_logger(__name__)

BASE = "https://api.travelpayouts.com"


class TravelpayoutsFlightsScraper(BaseScraper):
    """
    Usa o token TRAVELPAYOUTS_TOKEN (mesmo env var KIWI_API_KEY por ora —
    basta trocar no .env quando tiver o token Travelpayouts).
    """
    limiter_key = "amadeus"

    def __init__(self) -> None:
        super().__init__()
        if not TP_TOKEN:
            raise ScraperUnavailableError("KIWI_API_KEY / TRAVELPAYOUTS_TOKEN não configurada")
        self._token = TP_TOKEN

    def _fetch(self) -> list[Deal]:
        deals: list[Deal] = []
        # Busca nos próximos 3 meses
        for months_ahead in range(1, 4):
            target = date.today().replace(day=1) + timedelta(days=30 * months_ahead)
            month_str = target.strftime("%Y-%m")
            for origin in ORIGIN_AIRPORTS:
                deals.extend(self._cheap_any_destination(origin, month_str))
        return deals

    def _cheap_any_destination(self, origin: str, month: str) -> list[Deal]:
        """Busca passagens baratas de uma origem para QUALQUER destino no mês."""
        params = {
            "origin":       origin,
            "destination":  "-",      # "-" = qualquer destino
            "depart_date":  month,
            "one_way":      "false",
            "currency":     "brl",
            "token":        self._token,
        }
        try:
            resp = requests.get(f"{BASE}/v1/prices/cheap", params=params, timeout=15)
            resp.raise_for_status()
        except requests.RequestException as exc:
            logger.warning(f"Travelpayouts ({origin}/{month}): {exc}")
            return []

        raw = resp.json()
        if raw.get("success") is False:
            logger.warning(f"Travelpayouts API erro: {raw.get('error')}")
            return []

        results = []
        today_str = date.today().isoformat()
        data = raw.get("data", {})

        for dest_iata, prices in list(data.items())[:10]:
            for dep_date_str, info in prices.items():
                price_brl = float(info.get("price", 0))
                if price_brl <= 0:
                    continue
                airline  = info.get("airline", "")
                dep_date = info.get("departure_at", dep_date_str)[:10]
                ret_date = info.get("return_at", "")[:10]
                transfers = int(info.get("transfers", 0))

                results.append(Deal(
                    type="flight",
                    title=f"{origin} → {dest_iata} — Ida e Volta ({PASSENGERS} pax)",
                    price_brl=round(price_brl, 2),
                    total_3pax_brl=round(price_brl * PASSENGERS, 2),
                    source="travelpayouts",
                    booking_url=f"https://www.aviasales.com/search/{origin}{dep_date.replace('-','')}{dest_iata}2",
                    retrieved_at=today_str,
                    origin=origin,
                    destination=dest_iata,
                    outbound_date=dep_date,
                    return_date=ret_date,
                    airline=airline,
                    stops=transfers,
                ))

        logger.info(f"Travelpayouts ({origin}/{month}): {len(results)} tarifas")
        return results
