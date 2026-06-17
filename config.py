"""
config.py
Configuración central del proyecto EstudioRedes.
"""

from __future__ import annotations

import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
ENV_PATH = BASE_DIR / ".env"

# Importante para Streamlit/Windows/OneDrive:
# cargar explícitamente el .env de la raíz del proyecto, no depender del cwd.
load_dotenv(dotenv_path=ENV_PATH, override=True)

DATA_DIR = BASE_DIR / "data"
RAW_DATA_DIR = Path(os.getenv("RAW_DATA_DIR", str(DATA_DIR / "raw")))
EXPORTS_DIR = Path(os.getenv("EXPORTS_DIR", str(BASE_DIR / "exports")))
DATABASE_PATH = Path(os.getenv("DATABASE_PATH", str(DATA_DIR / "estudioredes.sqlite")))

DEFAULT_PROJECT_NAME = os.getenv("DEFAULT_PROJECT_NAME", "Discurso antifeminista")

X_BEARER_TOKEN = os.getenv("X_BEARER_TOKEN", "").strip().strip('"').strip("'")
X_PRICE_PER_POST_USD = float(os.getenv("X_PRICE_PER_POST_USD", "0.005"))
X_DAILY_BUDGET_USD = float(os.getenv("X_DAILY_BUDGET_USD", "50"))

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip().strip('"').strip("'")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

AUTHOR_HASH_SALT = os.getenv("AUTHOR_HASH_SALT", "dev_salt_change_me")


def mask_secret(value: str, visible: int = 4) -> str:
    """Devuelve una versión enmascarada de una credencial."""
    if not value:
        return "NO DETECTADA"
    if len(value) <= visible * 2:
        return "*" * len(value)
    return f"{value[:visible]}...{value[-visible:]} ({len(value)} chars)"


def get_config_diagnostics() -> dict[str, str | bool]:
    """Información segura para diagnosticar carga de .env sin exponer secrets."""
    return {
        "base_dir": str(BASE_DIR),
        "env_path": str(ENV_PATH),
        "env_exists": ENV_PATH.exists(),
        "database_path": str(DATABASE_PATH),
        "x_bearer_token": mask_secret(X_BEARER_TOKEN),
        "openai_api_key": mask_secret(OPENAI_API_KEY),
    }


def ensure_directories() -> None:
    """Crea carpetas locales necesarias para datos y exportaciones."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)


ensure_directories()

# fin config.py
