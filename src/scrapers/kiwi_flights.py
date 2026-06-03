"""
Kiwi.com Tequila API — busca de voos para qualquer destino.
API gratuita, sem prazo de encerramento. Cobre todas as companhias
(Azul, LATAM, GOL, TAP, Swiss, etc.) num único endpoint.

Documentação: https://tequila.kiwi.com/portal/docs/tequila-api/search_api
"""
from __future__ import annotations

from datetime import date, timedelta

import requests

from src.scrapers.base_scraper import BaseScraper, Deal, ScraperUnavailableError
from src.utils.config import (
    KIWI_API_KEY,
    ORIGIN_AIRPORTS,
    PASSENGERS,
    SEARCH_WINDOW_DAYS,
)
from src.utils.logger import get_logger

logger = get_logger(__name__)

BASE_URL = "https://api.tequila.kiwi.com/v2/search"


class KiwiFlightsScraper(BaseScraper):
    limiter_key = "amadeus"  # reutiliza o mesmo bucket de rate limiting

    def __init__(self) -> None:
        super().__init__()
        if not KIWI_API_KEY:
            raise ScraperUnavailableError("KIWI_API_KEY não configurada")
        self._headers = {"apikey": KIWI_API_KEY}

    def _fetch(self) -> list[Deal]:
        deals: list[Deal] = []

        # Janela de partida: de 30 a 180 dias a partir de hoje
        date_from = (date.today() + timedelta(days=30)).strftime("%d/%m/%Y")
        date_to   = (date.today() + timedelta(days=SEARCH_WINDOW_DAYS)).strftime("%d/%m/%Y")
        # Retorno: 7 a 21 dias após a partida
        ret_from  = (date.today() + timedelta(days=37)).strftime("%d/%m/%Y")
        ret_to    = (date.today() + timedelta(days=SEARCH_WINDOW_DAYS + 21)).strftime("%d/%m/%Y")

        for origin in ORIGIN_AIRPORTS:
            deals.extend(self._search(origin, "anywhere", date_from, date_to, ret_from, ret_to))

        return deals

    def _search(
        self,
        origin: str,
        destination: str,
        date_from: str,
        date_to: str,
        ret_from: str,
        ret_to: str,
    ) -> list[Deal]:
        params = {
            "fly_from":    origin,
            "fly_to":      destination,
            "date_from":   date_from,
            "date_to":     date_to,
            "return_from": ret_from,
            "return_to":   ret_to,
            "adults":      PASSENGERS,
            "curr":        "BRL",
            "limit":       15,
            "sort":        "price",
            "vehicle_type": "aircraft",
        }

        try:
            resp = requests.get(BASE_URL, headers=self._headers, params=params, timeout=20)
            resp.raise_for_status()
        except requests.HTTPError as exc:
            logger.warning(f"Kiwi ({origin}→{destination}): HTTP {exc.response.status_code}")
            return []
        except requests.RequestException as exc:
            logger.warning(f"Kiwi ({origin}→{destination}): {exc}")
            return []

        data = resp.json().get("data", [])
        results = []
        today = date.today().isoformat()

        for flight in data:
            price_brl = float(flight.get("price", 0))
            if price_brl <= 0:
                continue

            airlines  = ", ".join(flight.get("airlines", [])) or "—"
            city_to   = flight.get("cityTo", flight.get("flyTo", ""))
            country   = flight.get("countryTo", {}).get("name", "")
            dest_label = f"{city_to}, {country}".strip(", ")
            dep_iata  = flight.get("flyFrom", origin)
            arr_iata  = flight.get("flyTo", "")
            dep_ts    = flight.get("dTime", 0)
            dep_date  = date.fromtimestamp(dep_ts).isoformat() if dep_ts else ""
            nights    = flight.get("nightsInDest") or 0
            ret_date  = (date.fromtimestamp(dep_ts) + timedelta(days=nights)).isoformat() if dep_ts and nights else ""
            stops     = max(0, len(flight.get("route", [])) - 1)
            link      = flight.get("deep_link", "https://www.kiwi.com")

            results.append(Deal(
                type="flight",
                title=f"{dep_iata} → {dest_label} — Ida e Volta ({PASSENGERS} pax)",
                price_brl=round(price_brl / PASSENGERS, 2),
                total_3pax_brl=round(price_brl, 2),
                source="kiwi",
                booking_url=link,
                retrieved_at=today,
                origin=dep_iata,
                destination=arr_iata,
                outbound_date=dep_date,
                return_date=ret_date,
                airline=airlines,
                stops=stops,
                nights=nights,
            ))

        logger.info(f"Kiwi ({origin}→{destination}): {len(results)} voos encontrados")
        return results
