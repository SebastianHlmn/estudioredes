"""
processing/text_cleaner.py
Limpieza ligera y extracción de entidades textuales.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any

URL_RE = re.compile(r"https?://\S+|www\.\S+", re.IGNORECASE)
HASHTAG_RE = re.compile(r"(?<!\w)#([\wáéíóúñÁÉÍÓÚÑ_]+)", re.UNICODE)
MENTION_RE = re.compile(r"(?<!\w)@([A-Za-z0-9_]{1,30})")
MULTISPACE_RE = re.compile(r"\s+")


def strip_accents(text: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFD", text)
        if unicodedata.category(c) != "Mn"
    )


def normalize_for_matching(text: str) -> str:
    text = text or ""
    text = strip_accents(text.lower())
    text = URL_RE.sub(" ", text)
    text = MULTISPACE_RE.sub(" ", text).strip()
    return text


def clean_text(text: str) -> str:
    text = text or ""
    text = text.replace("\u00a0", " ")
    text = URL_RE.sub(" ", text)
    text = MULTISPACE_RE.sub(" ", text).strip()
    return text


def extract_entities(text: str) -> list[dict[str, Any]]:
    entities: list[dict[str, Any]] = []
    for url in URL_RE.findall(text or ""):
        entities.append({"entity_type": "url", "entity_value": url.rstrip(").,;:")})
    for hashtag in HASHTAG_RE.findall(text or ""):
        entities.append({"entity_type": "hashtag", "entity_value": hashtag.lower()})
    for mention in MENTION_RE.findall(text or ""):
        entities.append({"entity_type": "mention", "entity_value": mention.lower()})
    return entities


def enrich_text_record(record: dict[str, Any]) -> dict[str, Any]:
    text = record.get("text") or ""
    enriched = dict(record)
    enriched["clean_text"] = clean_text(text)
    enriched["entities"] = extract_entities(text)
    return enriched

# fin processing/text_cleaner.py
