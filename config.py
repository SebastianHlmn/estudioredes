"""
config.py
Configuración central del proyecto EstudioRedes.
"""

from __future__ import annotations

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
RAW_DATA_DIR = Path(os.getenv("RAW_DATA_DIR", str(DATA_DIR / "raw")))
EXPORTS_DIR = Path(os.getenv("EXPORTS_DIR", str(BASE_DIR / "exports")))
DATABASE_PATH = Path(os.getenv("DATABASE_PATH", str(DATA_DIR / "estudioredes.sqlite")))

DEFAULT_PROJECT_NAME = os.getenv("DEFAULT_PROJECT_NAME", "Discurso antifeminista")

X_BEARER_TOKEN = os.getenv("X_BEARER_TOKEN", "").strip()
X_PRICE_PER_POST_USD = float(os.getenv("X_PRICE_PER_POST_USD", "0.005"))
X_DAILY_BUDGET_USD = float(os.getenv("X_DAILY_BUDGET_USD", "50"))

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

AUTHOR_HASH_SALT = os.getenv("AUTHOR_HASH_SALT", "dev_salt_change_me")


def ensure_directories() -> None:
    """Crea carpetas locales necesarias para datos y exportaciones."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)


ensure_directories()

# fin config.py
