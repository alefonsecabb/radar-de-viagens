"""
Gera os arquivos JSON consumidos pelo dashboard e pelo e-mail.
"""
from __future__ import annotations

import json
import shutil
from dataclasses import asdict
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from src.scrapers.base_scraper import Deal
from src.utils.config import DOCS_DATA_DIR, LATEST_DIR
from src.utils.logger import get_logger

logger = get_logger(__name__)
BRT = ZoneInfo("America/Sao_Paulo")


def _deal_to_dict(deal: Deal) -> dict:
    d = asdict(deal)
    d.pop("extra", None)
    return d


def build_and_save(
    all_deals: list[Deal],
    sources_consulted: int,
    failed_sources: list[str],
) -> list[Deal]:
    """Gera todos os JSONs e retorna o top 10 para e-mail."""
    now_iso = datetime.now(BRT).isoformat()
    top10 = [d for d in all_deals if d.label in ("HOT", "GOOD", "FAIR")][:10]

    # Estatísticas para o e-mail
    stats = {
        "best_discount": max((d.discount_pct for d in top10), default=0),
        "cruises_found": sum(1 for d in all_deals if "cruise" in d.type),
        "total_deals": len(all_deals),
        "sources_consulted": sources_consulted,
        "sources_failed": failed_sources,
    }

    # top_deals.json
    top_payload = {
        "generated_at": now_iso,
        "run_id": date.today().isoformat(),
        "sources_consulted": sources_consulted,
        "sources_failed": failed_sources,
        "total_deals_found": len(all_deals),
        "stats": stats,
        "top_deals": [_deal_to_dict(d) for d in top10],
    }
    _write(LATEST_DIR / "top_deals.json", top_payload)

    # Por categoria
    categories = {
        "flights_latest":  [d for d in all_deals if d.type == "flight"],
        "hotels_latest":   [d for d in all_deals if d.type == "hotel"],
        "cruises_latest":  [d for d in all_deals if "cruise" in d.type],
        "packages_latest": [d for d in all_deals if d.type == "package"],
    }
    for name, deals in categories.items():
        _write(LATEST_DIR / f"{name}.json", {
            "generated_at": now_iso,
            "count": len(deals),
            "deals": [_deal_to_dict(d) for d in deals],
        })

    # Copia para docs/data/ (GitHub Pages)
    DOCS_DATA_DIR.mkdir(parents=True, exist_ok=True)
    for f in LATEST_DIR.glob("*.json"):
        shutil.copy2(f, DOCS_DATA_DIR / f.name)
    logger.info(f"JSONs gerados em {LATEST_DIR} e copiados para {DOCS_DATA_DIR}")

    return top10, stats


def _write(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
