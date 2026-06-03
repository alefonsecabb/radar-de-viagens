"""
Calcula score de cada deal comparando preço atual vs média histórica.
score = ((avg - price) / avg) * 100
Labels: HOT >= 40%, GOOD >= 20%, FAIR >= 5%, SKIP < 5%
"""
from __future__ import annotations

from src.scrapers.base_scraper import Deal
from src.scoring.price_history import get_moving_avg
from src.utils.config import SCORE_FAIR, SCORE_GOOD, SCORE_HOT
from src.utils.logger import get_logger

logger = get_logger(__name__)


def _label(score: float) -> str:
    if score >= SCORE_HOT:
        return "HOT"
    if score >= SCORE_GOOD:
        return "GOOD"
    if score >= SCORE_FAIR:
        return "FAIR"
    return "SKIP"


def score_deal(deal: Deal) -> Deal:
    avg = get_moving_avg(deal.type, deal)
    if avg and avg > 0 and deal.price_brl > 0:
        raw_score = ((avg - deal.price_brl) / avg) * 100
        deal.discount_pct = round(raw_score, 1)
        deal.score = round(raw_score, 1)
    else:
        # Sem histórico suficiente — score neutro, deal ainda aparece
        deal.discount_pct = 0.0
        deal.score = 0.0
    deal.label = _label(deal.score)
    return deal


def score_all(deals: list[Deal]) -> list[Deal]:
    scored = [score_deal(d) for d in deals]
    # Remove deals piores que a média (score muito negativo = armadilha de preço)
    scored = [d for d in scored if d.score > -20]
    scored.sort(key=lambda d: d.score, reverse=True)
    return scored
