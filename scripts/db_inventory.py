"""
scripts/db_inventory.py
Inventario rápido de la base SQLite de EstudioRedes.

Uso:
    python scripts/db_inventory.py
"""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config import DATABASE_PATH
from db_manager import db_inventory, init_db


def main() -> None:
    init_db()
    print(f"Base SQLite: {DATABASE_PATH}")
    print("-" * 80)
    df = db_inventory()
    print(df.to_string(index=False))


if __name__ == "__main__":
    main()

# fin scripts/db_inventory.py
