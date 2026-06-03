import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "data"
HISTORY_DIR = DATA_DIR / "history"
LATEST_DIR = DATA_DIR / "latest"
DOCS_DATA_DIR = BASE_DIR / "docs" / "data"
TEMPLATES_DIR = BASE_DIR / "templates"

# Kiwi.com Tequila API — https://tequila.kiwi.com (gratuito)
KIWI_API_KEY = os.getenv("KIWI_API_KEY", "")

GMAIL_USER = os.getenv("GMAIL_USER", "")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD", "")
RECIPIENT_EMAIL = os.getenv("RECIPIENT_EMAIL", "alefonsecabb@gmail.com")

RUN_ENV = os.getenv("RUN_ENV", "local")

# Aeroportos de origem (família em SP/Campinas)
ORIGIN_AIRPORTS = ["VCP", "GRU", "CGH"]

# Total de passageiros
PASSENGERS = 3

# Janela de busca em dias a partir de hoje
SEARCH_WINDOW_DAYS = 180

# Thresholds de scoring
SCORE_HOT = 40.0
SCORE_GOOD = 20.0
SCORE_FAIR = 5.0

# Máx. de entradas por chave no histórico
HISTORY_MAX_ENTRIES = 90
