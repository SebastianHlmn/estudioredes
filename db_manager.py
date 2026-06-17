"""
db_manager.py
Capa SQLite para EstudioRedes.

Diseño inicial:
- Proyectos temáticos reutilizables.
- Corridas de relevamiento trazables.
- Datos crudos y normalizados.
- Entidades extraídas.
- Clasificaciones discursivas.
- Menciones conceptuales y etapas de cristalización.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import pandas as pd

from config import AUTHOR_HASH_SALT, DATABASE_PATH, DEFAULT_PROJECT_NAME


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def hash_value(value: str | None) -> str | None:
    if value is None:
        return None
    raw = f"{AUTHOR_HASH_SALT}:{value}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:24]


def get_connection() -> sqlite3.Connection:
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DATABASE_PATH)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON;")
    return con


def init_db() -> None:
    con = get_connection()
    cur = con.cursor()

    cur.executescript(
        """
        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            description TEXT,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS codebooks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            version TEXT NOT NULL,
            description TEXT,
            schema_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY(project_id) REFERENCES projects(id)
        );

        CREATE TABLE IF NOT EXISTS collection_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            source TEXT NOT NULL,
            platform TEXT NOT NULL,
            query TEXT,
            started_at TEXT NOT NULL,
            finished_at TEXT,
            max_results INTEGER,
            retrieved_count INTEGER DEFAULT 0,
            estimated_cost_usd REAL DEFAULT 0,
            status TEXT NOT NULL DEFAULT 'created',
            notes TEXT,
            FOREIGN KEY(project_id) REFERENCES projects(id)
        );

        CREATE TABLE IF NOT EXISTS raw_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            collection_run_id INTEGER NOT NULL,
            platform TEXT NOT NULL,
            external_id TEXT,
            raw_json TEXT NOT NULL,
            collected_at TEXT NOT NULL,
            hash_content TEXT NOT NULL,
            FOREIGN KEY(collection_run_id) REFERENCES collection_runs(id)
        );

        CREATE UNIQUE INDEX IF NOT EXISTS idx_raw_unique
        ON raw_items(platform, external_id, hash_content);

        CREATE TABLE IF NOT EXISTS posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            collection_run_id INTEGER,
            platform TEXT NOT NULL,
            external_id TEXT,
            author_id_hash TEXT,
            author_label TEXT,
            created_at TEXT,
            text TEXT NOT NULL,
            clean_text TEXT,
            url TEXT,
            conversation_id TEXT,
            parent_id TEXT,
            reposted_id TEXT,
            like_count INTEGER DEFAULT 0,
            reply_count INTEGER DEFAULT 0,
            repost_count INTEGER DEFAULT 0,
            quote_count INTEGER DEFAULT 0,
            view_count INTEGER DEFAULT 0,
            is_duplicate INTEGER DEFAULT 0,
            inserted_at TEXT NOT NULL,
            FOREIGN KEY(project_id) REFERENCES projects(id),
            FOREIGN KEY(collection_run_id) REFERENCES collection_runs(id)
        );

        CREATE INDEX IF NOT EXISTS idx_posts_project_date
        ON posts(project_id, created_at);

        CREATE UNIQUE INDEX IF NOT EXISTS idx_posts_unique_external
        ON posts(platform, external_id)
        WHERE external_id IS NOT NULL;

        CREATE TABLE IF NOT EXISTS post_entities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            post_id INTEGER NOT NULL,
            entity_type TEXT NOT NULL,
            entity_value TEXT NOT NULL,
            FOREIGN KEY(post_id) REFERENCES posts(id)
        );

        CREATE INDEX IF NOT EXISTS idx_entities_type_value
        ON post_entities(entity_type, entity_value);

        CREATE TABLE IF NOT EXISTS classifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            post_id INTEGER NOT NULL,
            relevance TEXT,
            frame TEXT,
            intensity TEXT,
            discursive_strategy TEXT,
            network_strategy TEXT,
            target TEXT,
            concept TEXT,
            model_used TEXT NOT NULL,
            prompt_version TEXT NOT NULL,
            confidence REAL,
            explanation TEXT,
            reviewed_human INTEGER DEFAULT 0,
            reviewed_label TEXT,
            classified_at TEXT NOT NULL,
            FOREIGN KEY(post_id) REFERENCES posts(id)
        );

        CREATE INDEX IF NOT EXISTS idx_classifications_post
        ON classifications(post_id);

        CREATE TABLE IF NOT EXISTS concept_mentions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            post_id INTEGER NOT NULL,
            concept TEXT NOT NULL,
            expression_detected TEXT NOT NULL,
            normalized_concept TEXT NOT NULL,
            stage TEXT NOT NULL,
            platform TEXT NOT NULL,
            created_at TEXT,
            detected_at TEXT NOT NULL,
            FOREIGN KEY(post_id) REFERENCES posts(id)
        );

        CREATE INDEX IF NOT EXISTS idx_concept_mentions_concept_date
        ON concept_mentions(normalized_concept, created_at);

        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            event_date TEXT NOT NULL,
            event_name TEXT NOT NULL,
            event_type TEXT,
            description TEXT,
            related_keywords TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY(project_id) REFERENCES projects(id)
        );
        """
    )

    con.commit()
    con.close()
    seed_defaults()


def seed_defaults() -> None:
    project_id = get_or_create_project(
        DEFAULT_PROJECT_NAME,
        "Primera investigación: discurso antifeminista, estrategias discursivas, circulación en redes y cristalización conceptual.",
    )
    if not list_codebooks(project_id):
        create_default_codebook(project_id)


def get_or_create_project(name: str, description: str = "") -> int:
    con = get_connection()
    cur = con.cursor()
    cur.execute("SELECT id FROM projects WHERE name = ?", (name,))
    row = cur.fetchone()
    if row:
        con.close()
        return int(row["id"])
    cur.execute(
        "INSERT INTO projects(name, description, created_at) VALUES (?, ?, ?)",
        (name, description, now_iso()),
    )
    con.commit()
    project_id = int(cur.lastrowid)
    con.close()
    return project_id


def list_projects() -> pd.DataFrame:
    con = get_connection()
    df = pd.read_sql_query("SELECT * FROM projects ORDER BY created_at DESC", con)
    con.close()
    return df


def list_codebooks(project_id: int) -> pd.DataFrame:
    con = get_connection()
    df = pd.read_sql_query(
        "SELECT * FROM codebooks WHERE project_id = ? ORDER BY created_at DESC",
        con,
        params=(project_id,),
    )
    con.close()
    return df


def create_default_codebook(project_id: int) -> int:
    schema = {
        "relevance": [
            "irrelevante",
            "mencion_lateral",
            "critica_politica",
            "antifeminismo_explicito",
            "misoginia",
            "hostigamiento",
            "violencia_simbolica_amenaza",
        ],
        "frames": [
            "ideologia_de_genero",
            "denuncias_falsas",
            "anti_esi",
            "antiaborto",
            "privilegios_feministas",
            "victimizacion_masculina",
            "familia_tradicional",
            "manosfera_redpill",
            "anti_cuotas_paridad",
            "ataque_referentes_feministas",
            "otro",
        ],
        "discursive_strategies": [
            "victimizacion",
            "inversion_acusacion",
            "ridiculizacion",
            "generalizacion_caso_particular",
            "apelacion_sentido_comun",
            "enemigo_moral",
            "apropiacion_lenguaje_derechos",
            "provocacion_escandalo",
            "sarcasmo_meme",
            "deslegitimacion_institucional",
            "otro",
        ],
        "network_strategies": [
            "hashtag",
            "repost",
            "quote",
            "reply",
            "mencion",
            "enlace_externo",
            "clip_captura",
            "amplificacion_cuenta_central",
            "circulacion_comunitaria",
            "otro",
        ],
    }
    con = get_connection()
    cur = con.cursor()
    cur.execute(
        """
        INSERT INTO codebooks(project_id, name, version, description, schema_json, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            project_id,
            "Codebook discurso antifeminista",
            "0.1",
            "Codebook inicial para clasificación discursiva y de circulación.",
            json.dumps(schema, ensure_ascii=False, indent=2),
            now_iso(),
        ),
    )
    con.commit()
    codebook_id = int(cur.lastrowid)
    con.close()
    return codebook_id


def create_collection_run(
    project_id: int,
    source: str,
    platform: str,
    query: str | None,
    max_results: int | None,
    estimated_cost_usd: float = 0.0,
    notes: str = "",
) -> int:
    con = get_connection()
    cur = con.cursor()
    cur.execute(
        """
        INSERT INTO collection_runs(
            project_id, source, platform, query, started_at, max_results,
            estimated_cost_usd, status, notes
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (project_id, source, platform, query, now_iso(), max_results, estimated_cost_usd, "running", notes),
    )
    con.commit()
    run_id = int(cur.lastrowid)
    con.close()
    return run_id


def finish_collection_run(run_id: int, status: str, retrieved_count: int, notes: str = "") -> None:
    con = get_connection()
    con.execute(
        """
        UPDATE collection_runs
        SET finished_at = ?, status = ?, retrieved_count = ?, notes = COALESCE(NULLIF(?, ''), notes)
        WHERE id = ?
        """,
        (now_iso(), status, retrieved_count, notes, run_id),
    )
    con.commit()
    con.close()


def insert_raw_item(collection_run_id: int, platform: str, external_id: str | None, raw: dict[str, Any]) -> None:
    raw_json = json.dumps(raw, ensure_ascii=False, sort_keys=True)
    content_hash = hashlib.sha256(raw_json.encode("utf-8")).hexdigest()
    con = get_connection()
    con.execute(
        """
        INSERT OR IGNORE INTO raw_items(collection_run_id, platform, external_id, raw_json, collected_at, hash_content)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (collection_run_id, platform, external_id, raw_json, now_iso(), content_hash),
    )
    con.commit()
    con.close()


def insert_posts(posts: Iterable[dict[str, Any]]) -> int:
    con = get_connection()
    cur = con.cursor()
    inserted = 0
    for post in posts:
        cur.execute(
            """
            INSERT OR IGNORE INTO posts(
                project_id, collection_run_id, platform, external_id, author_id_hash, author_label,
                created_at, text, clean_text, url, conversation_id, parent_id, reposted_id,
                like_count, reply_count, repost_count, quote_count, view_count, is_duplicate, inserted_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                post.get("project_id"),
                post.get("collection_run_id"),
                post.get("platform"),
                post.get("external_id"),
                hash_value(post.get("author_id")) if post.get("author_id") else post.get("author_id_hash"),
                post.get("author_label"),
                post.get("created_at"),
                post.get("text", ""),
                post.get("clean_text"),
                post.get("url"),
                post.get("conversation_id"),
                post.get("parent_id"),
                post.get("reposted_id"),
                int(post.get("like_count") or 0),
                int(post.get("reply_count") or 0),
                int(post.get("repost_count") or 0),
                int(post.get("quote_count") or 0),
                int(post.get("view_count") or 0),
                int(post.get("is_duplicate") or 0),
                now_iso(),
            ),
        )
        if cur.rowcount > 0:
            inserted += 1
            post_id = int(cur.lastrowid)
            for entity in post.get("entities", []):
                cur.execute(
                    "INSERT INTO post_entities(post_id, entity_type, entity_value) VALUES (?, ?, ?)",
                    (post_id, entity["entity_type"], entity["entity_value"]),
                )
    con.commit()
    con.close()
    return inserted


def list_collection_runs(project_id: int) -> pd.DataFrame:
    con = get_connection()
    df = pd.read_sql_query(
        "SELECT * FROM collection_runs WHERE project_id = ? ORDER BY started_at DESC",
        con,
        params=(project_id,),
    )
    con.close()
    return df


def list_posts(project_id: int, limit: int = 5000) -> pd.DataFrame:
    con = get_connection()
    df = pd.read_sql_query(
        """
        SELECT p.*, c.relevance, c.frame, c.intensity, c.discursive_strategy,
               c.network_strategy, c.target, c.concept, c.confidence
        FROM posts p
        LEFT JOIN (
            SELECT c1.*
            FROM classifications c1
            JOIN (
                SELECT post_id, MAX(id) AS max_id
                FROM classifications
                GROUP BY post_id
            ) last_c ON c1.id = last_c.max_id
        ) c ON p.id = c.post_id
        WHERE p.project_id = ?
        ORDER BY COALESCE(p.created_at, p.inserted_at) DESC
        LIMIT ?
        """,
        con,
        params=(project_id, limit),
    )
    con.close()
    return df


def pending_classification(project_id: int, limit: int = 200) -> pd.DataFrame:
    con = get_connection()
    df = pd.read_sql_query(
        """
        SELECT p.*
        FROM posts p
        LEFT JOIN classifications c ON p.id = c.post_id
        WHERE p.project_id = ? AND c.id IS NULL
        ORDER BY COALESCE(p.created_at, p.inserted_at) DESC
        LIMIT ?
        """,
        con,
        params=(project_id, limit),
    )
    con.close()
    return df


def insert_classifications(rows: Iterable[dict[str, Any]]) -> int:
    con = get_connection()
    cur = con.cursor()
    inserted = 0
    for row in rows:
        cur.execute(
            """
            INSERT INTO classifications(
                post_id, relevance, frame, intensity, discursive_strategy,
                network_strategy, target, concept, model_used, prompt_version,
                confidence, explanation, reviewed_human, reviewed_label, classified_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                row.get("post_id"),
                row.get("relevance"),
                row.get("frame"),
                row.get("intensity"),
                row.get("discursive_strategy"),
                row.get("network_strategy"),
                row.get("target"),
                row.get("concept"),
                row.get("model_used", "rules_v0"),
                row.get("prompt_version", "rules_0.1"),
                row.get("confidence"),
                row.get("explanation"),
                int(row.get("reviewed_human") or 0),
                row.get("reviewed_label"),
                now_iso(),
            ),
        )
        inserted += 1
    con.commit()
    con.close()
    return inserted


def insert_concept_mentions(rows: Iterable[dict[str, Any]]) -> int:
    con = get_connection()
    cur = con.cursor()
    inserted = 0
    for row in rows:
        cur.execute(
            """
            INSERT INTO concept_mentions(
                post_id, concept, expression_detected, normalized_concept,
                stage, platform, created_at, detected_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                row.get("post_id"),
                row.get("concept"),
                row.get("expression_detected"),
                row.get("normalized_concept"),
                row.get("stage"),
                row.get("platform"),
                row.get("created_at"),
                now_iso(),
            ),
        )
        inserted += 1
    con.commit()
    con.close()
    return inserted


def concept_mentions_df(project_id: int) -> pd.DataFrame:
    con = get_connection()
    df = pd.read_sql_query(
        """
        SELECT cm.*
        FROM concept_mentions cm
        JOIN posts p ON p.id = cm.post_id
        WHERE p.project_id = ?
        ORDER BY cm.created_at
        """,
        con,
        params=(project_id,),
    )
    con.close()
    return df

# fin db_manager.py
