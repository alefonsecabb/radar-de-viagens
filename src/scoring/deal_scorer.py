"""
Calcula score de cada deal comparando preço atual vs média histórica.
score = ((avg - price) / avg) * 100
Labels: HOT >= 40%, GOOD >= 20%, FAIR >= 5%, SKIP < 5%

Quando não há histórico suficiente (< 3 amostras), usa limiares absolutos
de preço como fallback para não filtrar todos os deals no bootstrap.
"""
from __future__ import annotations

from src.scrapers.base_scraper import Deal
from src.scoring.price_history import get_moving_avg
from src.utils.config import SCORE_FAIR, SCORE_GOOD, SCORE_HOT
from src.utils.logger import get_logger

logger = get_logger(__name__)

# Limiares absolutos (R$/pax) usados quando não há histórico ainda
_FALLBACK_THRESHOLDS: dict[str, list[tuple[float, str]]] = {
    "flight":               [(400, "HOT"), (900,  "GOOD"), (1800, "FAIR")],
    "hotel":                [(120, "HOT"), (250,  "GOOD"), (500,  "FAIR")],
    "cruise_repositioning": [(180, "HOT"), (350,  "GOOD"), (700,  "FAIR")],
    "package":              [(900, "HOT"), (2000, "GOOD"), (4000, "FAIR")],
}


def _label(score: float) -> str:
    if score >= SCORE_HOT:
        return "HOT"
    if score >= SCORE_GOOD:
        return "GOOD"
    if score >= SCORE_FAIR:
        return "FAIR"
    return "SKIP"


def _fallback_label(deal_type: str, price_brl: float) -> str:
    """Label provisório quando não há histórico de preços."""
    if price_brl <= 0:
        return "FAIR"  # preço desconhecido — inclui mesmo assim
    for threshold, label in _FALLBACK_THRESHOLDS.get(deal_type, []):
        if price_brl < threshold:
            return label
    return "SKIP"


def score_deal(deal: Deal) -> Deal:
    avg = get_moving_avg(deal.type, deal)
    if avg and avg > 0 and deal.price_brl > 0:
        raw_score = ((avg - deal.price_brl) / avg) * 100
        deal.discount_pct = round(raw_score, 1)
        deal.score = round(raw_score, 1)
        deal.label = _label(deal.score)
    else:
        deal.discount_pct = 0.0
        deal.score = 0.0
        deal.label = _fallback_label(deal.type, deal.price_brl)
    return deal


def score_all(deals: list[Deal]) -> list[Deal]:
    scored = [score_deal(d) for d in deals]
    # Remove deals piores que a média (score muito negativo = armadilha de preço)
    scored = [d for d in scored if d.score > -20]
    scored.sort(key=lambda d: d.score, reverse=True)
    return scored
