"""
Mantém histórico de preços em arquivos JSON.
Cada arquivo tem estrutura: { "schema_version": "1.0", "updated_at": "...", "<categoria>": { "<chave>": { "entries": [...], "moving_avg_brl": X, "sample_count": N } } }
"""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any

from src.utils.config import HISTORY_DIR, HISTORY_MAX_ENTRIES
from src.utils.logger import get_logger

logger = get_logger(__name__)

_HISTORY_FILES = {
    "flight":               HISTORY_DIR / "flights_history.json",
    "hotel":                HISTORY_DIR / "hotels_history.json",
    "cruise_repositioning": HISTORY_DIR / "cruises_history.json",
    "package":              HISTORY_DIR / "packages_history.json",
}
_CATEGORY_KEYS = {
    "flight":               "routes",
    "hotel":                "hotels",
    "cruise_repositioning": "cruises",
    "package":              "packages",
}


def _load(path: Path) -> dict:
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            logger.warning(f"Histórico corrompido em {path}, reiniciando")
    return {"schema_version": "1.0", "updated_at": "", _CATEGORY_KEYS.get(path.stem.split("_")[0], "items"): {}}


def _save(path: Path, data: dict) -> None:
    data["updated_at"] = date.today().isoformat()
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _deal_key(deal_type: str, deal: Any) -> str:
    """Gera chave única por rota/produto."""
    if deal_type == "flight":
        return f"{deal.origin}-{deal.destination}"
    if deal_type == "hotel":
        return f"{deal.destination}-{deal.hotel_name[:30]}"
    if deal_type == "cruise_repositioning":
        return f"{deal.ship}-{deal.departure_port}-{deal.arrival_port}"
    return f"{deal.title[:40]}"


def get_moving_avg(deal_type: str, deal: Any) -> float | None:
    """Retorna a média histórica de preço por pessoa (BRL) ou None se sem histórico."""
    path = _HISTORY_FILES.get(deal_type)
    if not path:
        return None
    data = _load(path)
    cat_key = _CATEGORY_KEYS[deal_type]
    key = _deal_key(deal_type, deal)
    entry = data.get(cat_key, {}).get(key)
    if not entry or entry.get("sample_count", 0) < 3:
        return None
    return entry.get("moving_avg_brl")


def update_history(deals: list[Any]) -> None:
    """Adiciona os deals ao histórico e recalcula médias móveis."""
    grouped: dict[str, list] = {}
    for deal in deals:
        grouped.setdefault(deal.type, []).append(deal)

    for deal_type, group in grouped.items():
        path = _HISTORY_FILES.get(deal_type)
        if not path:
            continue
        data = _load(path)
        cat_key = _CATEGORY_KEYS[deal_type]
        bucket = data.setdefault(cat_key, {})

        for deal in group:
            key = _deal_key(deal_type, deal)
            item = bucket.setdefault(key, {"entries": [], "moving_avg_brl": 0.0, "sample_count": 0})
            item["entries"].append({
                "date": date.today().isoformat(),
                "price_brl": deal.price_brl,
            })
            # Trunca ao máximo configurado
            if len(item["entries"]) > HISTORY_MAX_ENTRIES:
                item["entries"] = item["entries"][-HISTORY_MAX_ENTRIES:]
            prices = [e["price_brl"] for e in item["entries"]]
            item["moving_avg_brl"] = round(sum(prices) / len(prices), 2)
            item["sample_count"] = len(prices)

        _save(path, data)
        logger.info(f"Histórico atualizado: {deal_type} ({len(group)} registros)")
