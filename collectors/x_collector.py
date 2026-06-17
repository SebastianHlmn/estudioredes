"""
collectors/x_collector.py
Colector inicial para X / Twitter usando API v2 Recent Search.

Requiere X_BEARER_TOKEN en .env.
"""

from __future__ import annotations

from typing import Any

import requests

from config import X_BEARER_TOKEN
from processing.text_cleaner import enrich_text_record

X_RECENT_SEARCH_URL = "https://api.x.com/2/tweets/search/recent"

DEFAULT_TWEET_FIELDS = [
    "id",
    "text",
    "author_id",
    "created_at",
    "conversation_id",
    "public_metrics",
    "referenced_tweets",
    "entities",
    "lang",
]

DEFAULT_EXPANSIONS = [
    "author_id",
    "referenced_tweets.id",
    "referenced_tweets.id.author_id",
    "entities.mentions.username",
]

DEFAULT_USER_FIELDS = ["id", "username", "name", "verified", "public_metrics"]


class XCollectorError(RuntimeError):
    pass


def _headers(bearer_token: str | None = None) -> dict[str, str]:
    token = (bearer_token or X_BEARER_TOKEN).strip()
    if not token:
        raise XCollectorError("Falta X_BEARER_TOKEN. Copiá .env.example a .env y completá el token.")
    return {"Authorization": f"Bearer {token}"}


def estimate_x_cost(max_results: int, price_per_post_usd: float) -> float:
    return round(max_results * price_per_post_usd, 4)


def search_recent(
    query: str,
    project_id: int,
    collection_run_id: int,
    max_results: int = 100,
    bearer_token: str | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """
    Ejecuta búsqueda reciente en X.

    Devuelve:
    - posts normalizados para insertar en SQLite.
    - raw_items originales para auditoría.
    """
    if max_results < 10:
        max_results = 10
    if max_results > 10000:
        max_results = 10000

    collected_posts: list[dict[str, Any]] = []
    raw_items: list[dict[str, Any]] = []
    next_token: str | None = None

    while len(collected_posts) < max_results:
        page_size = min(100, max_results - len(collected_posts))
        params = {
            "query": query,
            "max_results": page_size,
            "tweet.fields": ",".join(DEFAULT_TWEET_FIELDS),
            "expansions": ",".join(DEFAULT_EXPANSIONS),
            "user.fields": ",".join(DEFAULT_USER_FIELDS),
        }
        if next_token:
            params["next_token"] = next_token

        response = requests.get(
            X_RECENT_SEARCH_URL,
            headers=_headers(bearer_token),
            params=params,
            timeout=60,
        )

        if response.status_code >= 400:
            raise XCollectorError(
                f"Error X API {response.status_code}: {response.text[:1000]}"
            )

        payload = response.json()
        raw_items.append(payload)
        users = {
            u.get("id"): u
            for u in payload.get("includes", {}).get("users", [])
            if u.get("id")
        }

        for item in payload.get("data", []):
            metrics = item.get("public_metrics", {}) or {}
            author = users.get(item.get("author_id"), {})
            referenced = item.get("referenced_tweets", []) or []
            parent_id = None
            reposted_id = None
            for ref in referenced:
                if ref.get("type") in {"replied_to", "quoted"}:
                    parent_id = ref.get("id")
                if ref.get("type") == "retweeted":
                    reposted_id = ref.get("id")

            base = {
                "project_id": project_id,
                "collection_run_id": collection_run_id,
                "platform": "x",
                "external_id": item.get("id"),
                "author_id": item.get("author_id"),
                "author_label": author.get("username"),
                "created_at": item.get("created_at"),
                "text": item.get("text", ""),
                "url": f"https://x.com/{author.get('username')}/status/{item.get('id')}" if author.get("username") and item.get("id") else None,
                "conversation_id": item.get("conversation_id"),
                "parent_id": parent_id,
                "reposted_id": reposted_id,
                "like_count": metrics.get("like_count", 0),
                "reply_count": metrics.get("reply_count", 0),
                "repost_count": metrics.get("retweet_count", 0),
                "quote_count": metrics.get("quote_count", 0),
                "view_count": metrics.get("impression_count", 0),
            }
            collected_posts.append(enrich_text_record(base))

        next_token = payload.get("meta", {}).get("next_token")
        if not next_token or not payload.get("data"):
            break

    return collected_posts, raw_items

# fin collectors/x_collector.py
