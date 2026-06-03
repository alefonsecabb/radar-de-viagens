"""
Helpers compartilhados para scrapers que usam Playwright headless.
Mantém uma instância de browser reutilizável dentro da execução.
"""
from __future__ import annotations

import asyncio
from typing import Optional

from src.utils.logger import get_logger

logger = get_logger(__name__)


def fetch_page_content(
    url: str,
    wait_selector: Optional[str] = None,
    timeout: int = 20_000,
    extra_headers: Optional[dict] = None,
) -> str:
    """Carrega a URL com Playwright e retorna o HTML renderizado."""
    try:
        return asyncio.run(_fetch(url, wait_selector, timeout, extra_headers))
    except Exception as exc:
        logger.warning(f"Playwright falhou para {url}: {exc}")
        return ""


async def _fetch(
    url: str,
    wait_selector: Optional[str],
    timeout: int,
    extra_headers: Optional[dict],
) -> str:
    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            locale="pt-BR",
            viewport={"width": 1280, "height": 800},
        )
        if extra_headers:
            await context.set_extra_http_headers(extra_headers)

        page = await context.new_page()

        try:
            # domcontentloaded é muito mais rápido que networkidle
            await page.goto(url, wait_until="domcontentloaded", timeout=timeout)
            # Aguarda mais um pouco para JS renderizar o conteúdo
            await page.wait_for_timeout(3000)
            if wait_selector:
                try:
                    await page.wait_for_selector(wait_selector, timeout=8000)
                except Exception:
                    pass  # Continua mesmo se o seletor não aparecer
            content = await page.content()
        finally:
            await browser.close()

    return content
