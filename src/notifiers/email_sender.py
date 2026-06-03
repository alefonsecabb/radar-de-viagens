"""
Envia o digest diário de barganhas via Gmail SMTP (porta 465 / SSL).
Credenciais via variável de ambiente GMAIL_APP_PASSWORD.
"""
from __future__ import annotations

import smtplib
import ssl
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from zoneinfo import ZoneInfo

from jinja2 import Environment, FileSystemLoader

from src.scrapers.base_scraper import Deal
from src.utils.config import GMAIL_APP_PASSWORD, GMAIL_USER, RECIPIENT_EMAIL, TEMPLATES_DIR
from src.utils.logger import get_logger

logger = get_logger(__name__)

BRT = ZoneInfo("America/Sao_Paulo")


def _render_html(deals: list[Deal], stats: dict) -> str:
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=True,
    )
    template = env.get_template("email_daily.html")
    now_brt = datetime.now(BRT).strftime("%d/%m/%Y às %H:%M")
    return template.render(
        deals=deals,
        stats=stats,
        timestamp_brt=now_brt,
        run_date=datetime.now(BRT).strftime("%d/%m/%Y"),
    )


def send_digest(deals: list[Deal], stats: dict, failed_sources: list[str]) -> None:
    if not GMAIL_USER or not GMAIL_APP_PASSWORD:
        logger.warning("Credenciais Gmail não configuradas — e-mail não enviado")
        return

    html_body = _render_html(deals, stats)

    msg = MIMEMultipart("alternative")
    msg["Subject"] = (
        f"✈ Radar de Viagens — {len(deals)} barganhas em {datetime.now(BRT).strftime('%d/%m/%Y')}"
    )
    msg["From"] = f"Radar de Viagens <{GMAIL_USER}>"
    msg["To"] = RECIPIENT_EMAIL

    if failed_sources:
        note = f"<p style='color:#888;font-size:12px'>⚠ Fontes indisponíveis hoje: {', '.join(failed_sources)}</p>"
        html_body = html_body.replace("</body>", note + "</body>")

    msg.attach(MIMEText(html_body, "html", "utf-8"))

    ctx = ssl.create_default_context()
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=ctx) as server:
            server.login(GMAIL_USER, GMAIL_APP_PASSWORD)
            server.sendmail(GMAIL_USER, RECIPIENT_EMAIL, msg.as_string())
        logger.info(f"E-mail enviado para {RECIPIENT_EMAIL}")
    except smtplib.SMTPException as exc:
        logger.error(f"Falha ao enviar e-mail: {exc}")
