"""
Scoring especial para cruzeiros de reposicionamento.
Esses cruzeiros são inerentemente baratos (o navio precisa se mover de qualquer jeito),
mas têm alta urgência por disponibilidade limitada.

Score base: 50
Bônus aplicados:
  +20 se < 60 dias para saída (urgência)
  +15 se >= 14 noites (ótimo custo-benefício)
  +10 se porto de embarque brasileiro (Santos / Rio)
  +10 se temporada correta (mar–abr ou out–nov)
"""
from __future__ import annotations

from datetime import date

from src.scrapers.base_scraper import Deal
from src.utils.logger import get_logger

logger = get_logger(__name__)

_BR_PORTS = {"Santos", "Rio de Janeiro", "Itajaí", "Salvador"}
_REPOSITIONING_MONTHS = {3, 4, 10, 11}  # primavera e outono


def score_repositioning(deal: Deal) -> Deal:
    if not deal.is_repositioning:
        return deal

    score = 50.0

    # Urgência
    if deal.outbound_date:
        try:
            dep = date.fromisoformat(deal.outbound_date)
            days_away = (dep - date.today()).days
            if 0 < days_away < 60:
                score += 20
                logger.debug(f"{deal.ship}: +20 urgência ({days_away} dias)")
        except ValueError:
            pass

    # Duração
    if deal.nights >= 14:
        score += 15

    # Porto brasileiro
    if any(p.lower() in (deal.departure_port or "").lower() for p in _BR_PORTS):
        score += 10

    # Temporada certa
    if deal.outbound_date:
        try:
            month = date.fromisoformat(deal.outbound_date).month
            if month in _REPOSITIONING_MONTHS:
                score += 10
        except ValueError:
            pass

    deal.score = round(score, 1)
    deal.label = "HOT" if score >= 60 else "GOOD"
    return deal


def score_all_repositioning(deals: list[Deal]) -> list[Deal]:
    return [score_repositioning(d) if d.is_repositioning else d for d in deals]
