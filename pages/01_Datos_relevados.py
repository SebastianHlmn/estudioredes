"""
pages/01_Datos_relevados.py
Vista clara de qué se relevó, qué se guardó y qué está pendiente.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pandas as pd
import streamlit as st

from config import DATABASE_PATH, DEFAULT_PROJECT_NAME
from db_manager import db_inventory, get_or_create_project, init_db, list_projects

st.set_page_config(page_title="Datos relevados", page_icon="📦", layout="wide")


@st.cache_data(ttl=5)
def read_sql(query: str, params: tuple = ()) -> pd.DataFrame:
    con = sqlite3.connect(DATABASE_PATH)
    df = pd.read_sql_query(query, con, params=params)
    con.close()
    return df


def table_count(table: str, where: str = "", params: tuple = ()) -> int:
    con = sqlite3.connect(DATABASE_PATH)
    cur = con.cursor()
    sql = f"SELECT COUNT(*) FROM {table}"
    if where:
        sql += f" WHERE {where}"
    try:
        cur.execute(sql, params)
        value = int(cur.fetchone()[0])
    except sqlite3.OperationalError:
        value = 0
    con.close()
    return value


def project_selector() -> int:
    projects = list_projects()
    if projects.empty:
        project_id = get_or_create_project(DEFAULT_PROJECT_NAME)
        projects = list_projects()
    options = dict(zip(projects["name"], projects["id"]))
    selected = st.sidebar.selectbox("Proyecto", list(options.keys()))
    return int(options[selected])


def safe_preview_json(raw: str, max_chars: int = 2500) -> str:
    try:
        obj = json.loads(raw)
        text = json.dumps(obj, ensure_ascii=False, indent=2)
    except Exception:
        text = str(raw)
    if len(text) > max_chars:
        return text[:max_chars] + "\n... [recortado para vista]"
    return text


def render_status(project_id: int) -> None:
    raw_count = table_count(
        "raw_items",
        "collection_run_id IN (SELECT id FROM collection_runs WHERE project_id = ?)",
        (project_id,),
    )
    posts_count = table_count("posts", "project_id = ?", (project_id,))
    authors_count = table_count("authors", "project_id = ?", (project_id,))
    entities_count = table_count(
        "post_entities",
        "post_id IN (SELECT id FROM posts WHERE project_id = ?)",
        (project_id,),
    )
    classifications_count = table_count(
        "classifications",
        "post_id IN (SELECT id FROM posts WHERE project_id = ?)",
        (project_id,),
    )
    concepts_count = table_count(
        "concept_mentions",
        "post_id IN (SELECT id FROM posts WHERE project_id = ?)",
        (project_id,),
    )
    runs_count = table_count("collection_runs", "project_id = ?", (project_id,))

    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric("Corridas", runs_count)
    c2.metric("Raw API", raw_count)
    c3.metric("Posts/tweets", posts_count)
    c4.metric("Autores", authors_count)
    c5.metric("Entidades", entities_count)
    c6.metric("Clasificaciones", classifications_count)

    st.subheader("Lectura del estado")
    if raw_count == 0 and posts_count == 0:
        st.info("Todavía no hay relevamientos guardados. Ejecutá una carga manual, CSV o X desde la app principal.")
    elif raw_count > 0 and posts_count == 0:
        st.warning(
            "Hay respuestas crudas de API guardadas, pero no hay posts normalizados. "
            "Esto puede indicar que X no devolvió `data`, o que falló/queda pendiente la normalización. El raw no se perdió."
        )
    elif posts_count > 0 and classifications_count == 0:
        st.warning(
            "Hay posts/tweets guardados, pero todavía no están clasificados. "
            "Andá a la página `Procesamiento guiado` para ver qué va a procesar y ejecutar clasificación/detección de conceptos."
        )
    elif posts_count > 0:
        st.success("Hay posts guardados y la base tiene material para analizar.")

    if posts_count > 0 and entities_count == 0:
        st.info(
            "No hay entidades extraídas. Puede ser normal si los tweets no traen hashtags, menciones o URLs. "
            "También puede indicar que necesitamos ampliar la extracción de entidades."
        )

    if authors_count > 0:
        st.caption(
            "Los perfiles/autores se guardan por defecto como hash para cuidar privacidad y costo. "
            "El enriquecimiento con nombres públicos o métricas de perfil debe hacerse selectivamente."
        )


def render_runs(project_id: int) -> None:
    st.header("1. Corridas de relevamiento")
    df = read_sql(
        """
        SELECT
            r.id AS run_id,
            r.started_at,
            r.finished_at,
            r.source,
            r.platform,
            r.status,
            r.max_results,
            r.retrieved_count AS devueltos_api,
            r.estimated_cost_usd,
            COUNT(DISTINCT raw.id) AS raw_pages,
            COUNT(DISTINCT p.id) AS posts_guardados,
            COUNT(DISTINCT e.id) AS entidades,
            r.query,
            r.notes
        FROM collection_runs r
        LEFT JOIN raw_items raw ON raw.collection_run_id = r.id
        LEFT JOIN posts p ON p.collection_run_id = r.id
        LEFT JOIN post_entities e ON e.post_id = p.id
        WHERE r.project_id = ?
        GROUP BY r.id
        ORDER BY r.started_at DESC
        """,
        (project_id,),
    )
    if df.empty:
        st.info("No hay corridas.")
    else:
        st.dataframe(df, use_container_width=True, hide_index=True)


def render_posts(project_id: int) -> None:
    st.header("2. Tweets / posts normalizados")
    df = read_sql(
        """
        SELECT
            p.id,
            p.collection_run_id,
            p.platform,
            p.external_id,
            p.url,
            p.author_id_hash,
            p.created_at,
            p.conversation_id,
            p.parent_id,
            p.reposted_id,
            p.like_count,
            p.reply_count,
            p.repost_count,
            p.quote_count,
            p.view_count,
            p.text
        FROM posts p
        WHERE p.project_id = ?
        ORDER BY COALESCE(p.created_at, p.inserted_at) DESC
        LIMIT 1000
        """,
        (project_id,),
    )
    if df.empty:
        st.info("No hay tweets/posts normalizados guardados.")
        return

    runs = ["Todas"] + [str(v) for v in sorted(df["collection_run_id"].dropna().unique(), reverse=True)]
    selected_run = st.selectbox("Filtrar por corrida", runs, key="posts_run_filter")
    view = df.copy()
    if selected_run != "Todas":
        view = view[view["collection_run_id"].astype(str) == selected_run]

    text_filter = st.text_input("Buscar texto dentro de tweets/posts", value="")
    if text_filter:
        view = view[view["text"].str.contains(text_filter, case=False, na=False)]

    st.caption(f"Mostrando {len(view)} de {len(df)} posts cargados en la vista.")
    st.dataframe(view, use_container_width=True, hide_index=True)

    with st.expander("Lectura rápida de textos", expanded=False):
        for _, row in view.head(30).iterrows():
            st.markdown(f"**Post interno {row['id']}** · corrida `{row['collection_run_id']}` · autor `{str(row['author_id_hash'])[:12]}`")
            if pd.notna(row.get("url")) and str(row.get("url")):
                st.markdown(f"[Abrir post]({row['url']})")
            st.write(row["text"])
            st.divider()


def render_authors(project_id: int) -> None:
    st.header("3. Perfiles / autores detectados")
    df = read_sql(
        """
        SELECT
            a.id,
            a.platform,
            a.author_id_hash,
            a.public_label,
            a.author_type,
            a.is_public_figure,
            a.enrichment_status,
            a.first_seen_at,
            a.last_seen_at,
            COUNT(p.id) AS posts_guardados,
            SUM(COALESCE(p.like_count,0) + COALESCE(p.reply_count,0) + COALESCE(p.repost_count,0) + COALESCE(p.quote_count,0)) AS interacciones_publicas
        FROM authors a
        LEFT JOIN posts p
            ON p.project_id = a.project_id
           AND p.platform = a.platform
           AND p.author_id_hash = a.author_id_hash
        WHERE a.project_id = ?
        GROUP BY a.id
        ORDER BY posts_guardados DESC, interacciones_publicas DESC
        """,
        (project_id,),
    )
    if df.empty:
        st.info(
            "No hay perfiles/autores en la tabla `authors`. "
            "Si hay posts, esto se completa automáticamente con los nuevos relevamientos."
        )
        return
    st.dataframe(df, use_container_width=True, hide_index=True)
    st.caption(
        "Por ahora son autores hasheados. Para identificar figuras públicas podemos hacer enriquecimiento selectivo, documentado y con costo controlado."
    )


def render_entities(project_id: int) -> None:
    st.header("4. Hashtags, menciones y URLs extraídas")
    df = read_sql(
        """
        SELECT
            e.id,
            e.post_id,
            p.collection_run_id,
            e.entity_type,
            e.entity_value,
            p.text
        FROM post_entities e
        JOIN posts p ON p.id = e.post_id
        WHERE p.project_id = ?
        ORDER BY e.entity_type, e.entity_value
        """,
        (project_id,),
    )
    if df.empty:
        st.info("No hay entidades extraídas para los posts actuales.")
        return

    summary = (
        df.groupby(["entity_type", "entity_value"])
        .size()
        .reset_index(name="cantidad")
        .sort_values(["cantidad", "entity_type", "entity_value"], ascending=[False, True, True])
    )
    st.subheader("Ranking")
    st.dataframe(summary, use_container_width=True, hide_index=True)
    st.subheader("Detalle")
    st.dataframe(df, use_container_width=True, hide_index=True)


def render_raw(project_id: int) -> None:
    st.header("5. Respuestas crudas de API")
    df = read_sql(
        """
        SELECT
            raw.id,
            raw.collection_run_id,
            raw.platform,
            raw.external_id,
            raw.collected_at,
            raw.hash_content,
            LENGTH(raw.raw_json) AS raw_json_chars,
            r.query,
            raw.raw_json
        FROM raw_items raw
        JOIN collection_runs r ON r.id = raw.collection_run_id
        WHERE r.project_id = ?
        ORDER BY raw.collected_at DESC
        LIMIT 200
        """,
        (project_id,),
    )
    if df.empty:
        st.info("No hay raw API guardado.")
        return

    visible = df.drop(columns=["raw_json"])
    st.dataframe(visible, use_container_width=True, hide_index=True)

    selected_raw = st.selectbox("Ver raw_json", df["id"].astype(str).tolist())
    row = df[df["id"].astype(str) == selected_raw].iloc[0]
    st.code(safe_preview_json(row["raw_json"]), language="json")


def render_processing_state(project_id: int) -> None:
    st.header("6. Estado de procesamiento")
    df = read_sql(
        """
        SELECT
            p.id,
            p.collection_run_id,
            p.platform,
            p.created_at,
            CASE WHEN c.id IS NULL THEN 0 ELSE 1 END AS clasificado,
            c.relevance,
            c.frame,
            c.discursive_strategy,
            c.confidence,
            p.text
        FROM posts p
        LEFT JOIN (
            SELECT c1.*
            FROM classifications c1
            JOIN (
                SELECT post_id, MAX(id) AS max_id
                FROM classifications
                GROUP BY post_id
            ) last_c ON c1.id = last_c.max_id
        ) c ON c.post_id = p.id
        WHERE p.project_id = ?
        ORDER BY COALESCE(p.created_at, p.inserted_at) DESC
        LIMIT 1000
        """,
        (project_id,),
    )
    if df.empty:
        st.info("No hay posts para procesar.")
        return

    c1, c2, c3 = st.columns(3)
    c1.metric("Posts", len(df))
    c2.metric("Clasificados", int(df["clasificado"].sum()))
    c3.metric("Pendientes", int((df["clasificado"] == 0).sum()))
    st.dataframe(df, use_container_width=True, hide_index=True)


def main() -> None:
    init_db()
    st.title("📦 Datos relevados")
    st.write(
        "Esta vista muestra qué hay efectivamente guardado en la base: corridas, raw API, tweets/posts, perfiles/autores, entidades y estado de procesamiento."
    )

    project_id = project_selector()

    with st.expander("Inventario completo de tablas", expanded=False):
        st.dataframe(db_inventory(), use_container_width=True, hide_index=True)

    render_status(project_id)
    st.divider()
    render_runs(project_id)
    st.divider()
    render_posts(project_id)
    st.divider()
    render_authors(project_id)
    st.divider()
    render_entities(project_id)
    st.divider()
    render_raw(project_id)
    st.divider()
    render_processing_state(project_id)


if __name__ == "__main__":
    main()

# fin pages/01_Datos_relevados.py
