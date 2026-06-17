"""
collectors/x_query_builder.py
Herramientas para construir queries de X orientadas a relevamiento temático y redes exploratorias.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

X_POST_ID_RE = re.compile(r"(?:status|statuses)/(\d+)|/i/web/status/(\d+)|(\d{12,25})")


@dataclass
class BuiltQuery:
    label: str
    query: str
    objective: str


def extract_x_post_id(value: str) -> str | None:
    """Extrae ID de post desde URL de X/Twitter o desde texto con ID."""
    if not value:
        return None
    match = X_POST_ID_RE.search(value.strip())
    if not match:
        return None
    for group in match.groups():
        if group:
            return group
    return None


def _quote_term(term: str) -> str:
    term = term.strip()
    if not term:
        return ""
    if " " in term and not (term.startswith('"') and term.endswith('"')):
        return f'"{term}"'
    return term


def _or_group(terms: list[str]) -> str:
    clean = [_quote_term(t) for t in terms if t and t.strip()]
    if not clean:
        return ""
    if len(clean) == 1:
        return clean[0]
    return "(" + " OR ".join(clean) + ")"


def split_terms(raw: str) -> list[str]:
    """Separa términos por coma o salto de línea."""
    if not raw:
        return []
    pieces = []
    for line in raw.splitlines():
        pieces.extend(line.split(","))
    return [p.strip() for p in pieces if p.strip()]


def build_thematic_query(
    core_terms: list[str],
    context_terms: list[str] | None = None,
    lang: str = "es",
    include_replies: bool = True,
    include_retweets: bool = False,
    only_quotes: bool = False,
    require_links: bool = False,
    require_mentions: bool = False,
) -> str:
    """Construye una query temática para X Recent Search."""
    core = _or_group(core_terms)
    context = _or_group(context_terms or [])
    parts = [p for p in [core, context] if p]

    if lang:
        parts.append(f"lang:{lang}")
    if not include_retweets:
        parts.append("-is:retweet")
    if not include_replies:
        parts.append("-is:reply")
    if only_quotes:
        parts.append("is:quote")
    if require_links:
        parts.append("has:links")
    if require_mentions:
        parts.append("has:mentions")

    return " ".join(parts).strip()


def build_seed_post_queries(
    post_id: str,
    lang: str = "es",
    include_conversation: bool = True,
    include_direct_replies: bool = True,
    include_quotes: bool = True,
    include_retweets: bool = False,
) -> list[BuiltQuery]:
    """Queries para expandir una red desde un post semilla."""
    suffix = f" lang:{lang}" if lang else ""
    queries: list[BuiltQuery] = []

    if include_conversation:
        q = f"conversation_id:{post_id}{suffix}"
        if not include_retweets:
            q += " -is:retweet"
        queries.append(
            BuiltQuery(
                label="conversacion",
                query=q,
                objective="Recuperar publicaciones de la conversación/hilo para observar marcos, respuestas y disputa discursiva.",
            )
        )

    if include_direct_replies:
        q = f"in_reply_to_tweet_id:{post_id}{suffix}"
        queries.append(
            BuiltQuery(
                label="respuestas_directas",
                query=q,
                objective="Recuperar respuestas directas al post semilla.",
            )
        )

    if include_quotes:
        q = f"quotes_of_tweet_id:{post_id}{suffix}"
        queries.append(
            BuiltQuery(
                label="citas",
                query=q,
                objective="Recuperar citas del post semilla, útiles para estudiar resignificación y amplificación política.",
            )
        )

    if include_retweets:
        q = f"retweets_of_tweet_id:{post_id}{suffix}"
        queries.append(
            BuiltQuery(
                label="reposts",
                query=q,
                objective="Recuperar reposts/retweets del post semilla.",
            )
        )

    return queries

# fin collectors/x_query_builder.py
