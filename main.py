"""
Radar de Viagens — orquestrador principal.
Executa todos os scrapers em paralelo, aplica scoring, gera JSONs,
atualiza o dashboard e envia o e-mail diário.
"""
from __future__ import annotations

import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

from src.dashboard.json_builder import build_and_save
from src.dashboard.site_updater import commit_and_push
from src.notifiers.email_sender import send_digest
from src.scrapers.travelpayouts_flights import TravelpayoutsFlightsScraper
from src.scrapers.kiwi_flights import KiwiFlightsScraper
from src.scrapers.passagenspromo import PassagensPromoScraper
from src.scrapers.vaidepromo import VaiDePromoScraper
from src.scrapers.melhores_destinos import MelhoresDestinosScraper
from src.scrapers.azul_flights import AzulFlightsScraper
from src.scrapers.base_scraper import Deal, ScraperUnavailableError
from src.scrapers.booking_hotels import BookingHotelsScraper
from src.scrapers.costa_cruises import CostaCruisesScraper
from src.scrapers.cruisecritic import CruiseCriticScraper
from src.scrapers.cvc_packages import CvcPackagesScraper
from src.scrapers.decolar_packages import DecolarPackagesScraper
from src.scrapers.gol_flights import GolFlightsScraper
from src.scrapers.hurb_packages import HurbPackagesScraper
from src.scrapers.latam_flights import LatamFlightsScraper
from src.scrapers.msc_cruises import MscCruisesScraper
from src.scrapers.swiss_flights import SwissFlightsScraper
from src.scrapers.tap_flights import TapFlightsScraper
from src.scrapers.trivago_hotels import TrivagoHotelsScraper
from src.scoring.deal_scorer import score_all
from src.scoring.price_history import update_history
from src.scoring.repositioning_scorer import score_all_repositioning
from src.utils.logger import get_logger

logger = get_logger(__name__)

SCRAPERS = [
    # Agregadores brasileiros — sem API key, funcionam imediatamente
    PassagensPromoScraper,
    VaiDePromoScraper,
    MelhoresDestinosScraper,
    # APIs de voos — precisam de token (opcionais, degradam graciosamente)
    TravelpayoutsFlightsScraper,
    KiwiFlightsScraper,
    AzulFlightsScraper,
    LatamFlightsScraper,
    GolFlightsScraper,
    TapFlightsScraper,
    SwissFlightsScraper,
    BookingHotelsScraper,
    TrivagoHotelsScraper,
    MscCruisesScraper,
    CostaCruisesScraper,
    CruiseCriticScraper,
    DecolarPackagesScraper,
    HurbPackagesScraper,
    CvcPackagesScraper,
]


def _run_scraper(scraper_class) -> tuple[list[Deal], str | None]:
    name = scraper_class.__name__
    try:
        instance = scraper_class()
        return instance.fetch(), None
    except ScraperUnavailableError as exc:
        logger.warning(f"{name} indisponível: {exc}")
        return [], name
    except Exception as exc:
        logger.error(f"{name} erro inesperado: {exc}", exc_info=True)
        return [], name


def main() -> int:
    logger.info("=== Radar de Viagens iniciado ===")

    all_deals: list[Deal] = []
    failed_sources: list[str] = []

    # 1. Coleta paralela
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = {pool.submit(_run_scraper, cls): cls.__name__ for cls in SCRAPERS}
        for future in as_completed(futures):
            deals, failed = future.result()
            all_deals.extend(deals)
            if failed:
                failed_sources.append(failed)

    logger.info(f"Total bruto: {len(all_deals)} deals | Falhas: {len(failed_sources)}")

    if not all_deals:
        logger.error("Nenhum deal coletado — abortando")
        return 1

    # 2. Atualiza histórico de preços
    update_history(all_deals)

    # 3. Scoring
    all_deals = score_all_repositioning(all_deals)   # cruzeiros de reposicionamento primeiro
    all_deals = score_all(all_deals)                 # todos os demais

    logger.info(f"Após scoring: {len(all_deals)} deals válidos")

    # 4. Gera JSONs e copia para docs/
    top10, stats = build_and_save(
        all_deals=all_deals,
        sources_consulted=len(SCRAPERS) - len(failed_sources),
        failed_sources=failed_sources,
    )

    # 5. Push para GitHub Pages
    commit_and_push()

    # 6. Envia e-mail
    send_digest(top10, stats, failed_sources)

    logger.info("=== Radar de Viagens concluído com sucesso ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
