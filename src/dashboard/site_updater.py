"""
Faz git commit e push dos JSONs atualizados (roda apenas no GitHub Actions).
"""
from __future__ import annotations

import subprocess
from datetime import date

from src.utils.config import BASE_DIR, RUN_ENV
from src.utils.logger import get_logger

logger = get_logger(__name__)


def _run(cmd: list[str]) -> str:
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(BASE_DIR))
    if result.returncode != 0:
        logger.warning(f"git: {result.stderr.strip()}")
    return result.stdout.strip()


def commit_and_push() -> None:
    if RUN_ENV != "github_actions":
        logger.info("Modo local — push automático ignorado")
        return

    _run(["git", "config", "user.name", "Travel Monitor Bot"])
    _run(["git", "config", "user.email", "actions@github.com"])
    _run(["git", "add", "data/", "docs/data/"])

    status = _run(["git", "diff", "--staged", "--quiet"])
    if status == "":
        # Sem mudanças staged — verifica se há diff real
        diff = _run(["git", "diff", "--staged"])
        if not diff:
            logger.info("Sem alterações nos dados — push ignorado")
            return

    today = date.today().isoformat()
    _run(["git", "commit", "-m", f"chore: update travel data {today} [skip ci]"])
    _run(["git", "push"])
    logger.info("Push realizado com sucesso")
