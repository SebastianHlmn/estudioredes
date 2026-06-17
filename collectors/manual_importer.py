"""
collectors/manual_importer.py
Ingreso manual o por CSV para plataformas sin API conectada.
"""

from __future__ import annotations

from typing import Any

import pandas as pd

from processing.text_cleaner import enrich_text_record

REQUIRED_TEXT_COLUMNS = ["text", "texto", "contenido", "post", "publicacion"]


def detect_text_column(df: pd.DataFrame) -> str | None:
    lower_map = {c.lower().strip(): c for c in df.columns}
    for candidate in REQUIRED_TEXT_COLUMNS:
        if candidate in lower_map:
            return lower_map[candidate]
    return None


def dataframe_to_posts(
    df: pd.DataFrame,
    project_id: int,
    collection_run_id: int,
    default_platform: str = "manual",
) -> list[dict[str, Any]]:
    text_col = detect_text_column(df)
    if text_col is None:
        raise ValueError(
            "No encontré columna de texto. Usá una columna llamada text, texto, contenido, post o publicacion."
        )

    posts: list[dict[str, Any]] = []
    for idx, row in df.iterrows():
        text = str(row.get(text_col, "")).strip()
        if not text or text.lower() == "nan":
            continue
        platform = str(row.get("platform", row.get("plataforma", default_platform)) or default_platform)
        created_at = row.get("created_at", row.get("fecha", None))
        external_id = row.get("external_id", row.get("id", None))
        author = row.get("author_id", row.get("autor", row.get("usuario", None)))
        base = {
            "project_id": project_id,
            "collection_run_id": collection_run_id,
            "platform": platform,
            "external_id": None if pd.isna(external_id) else str(external_id),
            "author_id": None if pd.isna(author) else str(author),
            "author_label": None,
            "created_at": None if pd.isna(created_at) else str(created_at),
            "text": text,
            "url": None if pd.isna(row.get("url", None)) else str(row.get("url")),
        }
        posts.append(enrich_text_record(base))
    return posts


def single_text_to_post(
    text: str,
    project_id: int,
    collection_run_id: int,
    platform: str = "manual",
    author: str | None = None,
    created_at: str | None = None,
    url: str | None = None,
) -> dict[str, Any]:
    base = {
        "project_id": project_id,
        "collection_run_id": collection_run_id,
        "platform": platform,
        "external_id": None,
        "author_id": author,
        "author_label": None,
        "created_at": created_at,
        "text": text,
        "url": url,
    }
    return enrich_text_record(base)

# fin collectors/manual_importer.py
