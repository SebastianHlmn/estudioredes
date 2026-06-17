"""
pages/02_Procesamiento_guiado.py
Procesamiento guiado: muestra qué se procesa, con qué criterios y qué resultados produjo.
"""

from __future__ import annotations

import sqlite3

import pandas as pd
import streamlit as st

from analysis.concept_tracker import CONCEPT_EXPRESSIONS, build_concept_mentions, summarize_crystallization
from analysis.rule_classifier import KEYWORDS, STRATEGY_KEYWORDS, classify_dataframe
from config import DATABASE_PATH, DEFAULT_PROJECT_NAME
from db_manager import (
    concept_mentions_df,
    get_or_create_project,
    init_db,
    insert_classifications,
    insert_concept_mentions,
    list_posts,
    list_projects,
    pending_classification,
)

st.set_page_config(page_title="Procesamiento guiado", page_icon="⚙️", layout="wide")


@st.cache_data(ttl=5)
def read_sql(query: str, params: tuple = ()) -> pd.DataFrame:
    con = sqlite3.connect(DATABASE_PATH)
    df = pd.read_sql_query(query, con, params=params)
    con.close()
    return df


def project_selector() -> int:
    projects = list_projects()
    if projects.empty:
        project_id = get_or_create_project(DEFAULT_PROJECT_NAME)
        projects = list_projects()
    options = dict(zip(projects["name"], projects["id"]))
    selected = st.sidebar.selectbox("Proyecto", list(options.keys()))
    return int(options[selected])


def keyword_df(mapping: dict[str, list[str]], label_col: str) -> pd.DataFrame:
    rows = []
    for label, terms in mapping.items():
        for term in terms:
            rows.append({label_col: label, "expresion": term})
    return pd.DataFrame(rows)


def render_input_state(project_id: int) -> pd.DataFrame:
    st.header("1. Qué tiene la base para procesar")
    posts = list_posts(project_id, limit=100000)
    pending = pending_classification(project_id, limit=100000)
    concepts = concept_mentions_df(project_id)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Posts/tweets guardados", len(posts))
    c2.metric("Pendientes de clasificar", len(pending))
    c3.metric("Ya clasificados", max(len(posts) - len(pending), 0))
    c4.metric("Menciones conceptuales", len(concepts))

    if posts.empty:
        st.warning(
            "No hay posts/tweets normalizados para procesar. Revisá `Datos relevados`: puede haber raw API guardado pero sin posts normalizados, o X pudo haber devuelto muy poco."
        )
        return posts

    st.subheader("Tweets/posts disponibles")
    view_cols = [
        "id",
        "collection_run_id",
        "platform",
        "external_id",
        "author_id_hash",
        "created_at",
        "text",
        "relevance",
        "frame",
        "discursive_strategy",
        "concept",
        "confidence",
    ]
    view_cols = [c for c in view_cols if c in posts.columns]
    st.dataframe(posts[view_cols].head(500), use_container_width=True, hide_index=True)
    return posts


def render_what_it_searches() -> None:
    st.header("2. Qué busca el procesamiento actual")
    st.write(
        "En esta versión el procesamiento tiene dos componentes: una clasificación inicial por reglas interpretables y una detección de conceptos. "
        "Esto funciona como baseline auditable antes de incorporar IA."
    )

    tab1, tab2, tab3 = st.tabs(["Marcos discursivos", "Estrategias", "Conceptos"])
    with tab1:
        st.write("El clasificador busca estas expresiones para asignar `frame`.")
        st.dataframe(keyword_df(KEYWORDS, "frame"), use_container_width=True, hide_index=True)
    with tab2:
        st.write("El clasificador busca estas expresiones para asignar `discursive_strategy`.")
        st.dataframe(keyword_df(STRATEGY_KEYWORDS, "estrategia"), use_container_width=True, hide_index=True)
    with tab3:
        st.write("El detector de conceptos busca estas expresiones para llenar `concept_mentions`.")
        st.dataframe(keyword_df(CONCEPT_EXPRESSIONS, "concepto"), use_container_width=True, hide_index=True)

    st.info(
        "Si el procesamiento 'no encuentra nada', puede ser porque los tweets no contienen estas expresiones exactas. "
        "Eso no significa que no haya discurso relevante: significa que el baseline por reglas quedó corto y hay que ampliar vocabulario o pasar a IA."
    )


def render_actions(project_id: int) -> None:
    st.header("3. Ejecutar procesamiento")
    posts = list_posts(project_id, limit=100000)
    pending = pending_classification(project_id, limit=100000)

    if posts.empty:
        st.warning("No hay posts para procesar.")
        return

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Clasificación por reglas")
        st.write("Procesa posts sin clasificación y escribe resultados en `classifications`.")
        limit = st.number_input("Cantidad a clasificar", min_value=1, max_value=10000, value=min(max(len(pending), 1), 200), step=50)
        if st.button("Clasificar pendientes", disabled=pending.empty):
            df = pending_classification(project_id, limit=int(limit))
            rows = classify_dataframe(df)
            inserted = insert_classifications(rows)
            st.success(f"Clasificaciones insertadas: {inserted}")
            st.cache_data.clear()

        if pending.empty:
            st.info("No hay pendientes de clasificación. Ya tienen al menos una clasificación o no hay posts.")

    with col2:
        st.subheader("Detección de conceptos")
        st.write("Busca expresiones conceptuales y escribe resultados en `concept_mentions`.")
        if st.button("Detectar conceptos en todos los posts"):
            existing = concept_mentions_df(project_id)
            existing_keys = set()
            if not existing.empty:
                existing_keys = set(
                    zip(
                        existing["post_id"].astype(int),
                        existing["normalized_concept"].astype(str),
                        existing["expression_detected"].astype(str),
                    )
                )
            rows = []
            for row in build_concept_mentions(posts):
                key = (int(row["post_id"]), str(row["normalized_concept"]), str(row["expression_detected"]))
                if key not in existing_keys:
                    rows.append(row)
            inserted = insert_concept_mentions(rows)
            st.success(f"Menciones conceptuales insertadas: {inserted}")
            if inserted == 0:
                st.warning("No se detectaron conceptos nuevos con el vocabulario actual.")
            st.cache_data.clear()


def render_results(project_id: int) -> None:
    st.header("4. Resultados del procesamiento")
    classified = read_sql(
        """
        SELECT
            p.id AS post_id,
            p.collection_run_id,
            p.created_at,
            p.author_id_hash,
            c.relevance,
            c.frame,
            c.intensity,
            c.discursive_strategy,
            c.network_strategy,
            c.target,
            c.concept,
            c.confidence,
            c.explanation,
            p.text
        FROM posts p
        JOIN classifications c ON c.post_id = p.id
        WHERE p.project_id = ?
        ORDER BY c.id DESC
        LIMIT 1000
        """,
        (project_id,),
    )

    concepts = concept_mentions_df(project_id)

    tab1, tab2, tab3 = st.tabs(["Clasificaciones", "Conceptos", "Resumen conceptual"])
    with tab1:
        if classified.empty:
            st.info("Todavía no hay clasificaciones guardadas.")
        else:
            st.dataframe(classified, use_container_width=True, hide_index=True)
            summary = (
                classified.groupby(["relevance", "frame"], dropna=False)
                .size()
                .reset_index(name="cantidad")
                .sort_values("cantidad", ascending=False)
            )
            st.subheader("Resumen por relevancia y marco")
            st.dataframe(summary, use_container_width=True, hide_index=True)

    with tab2:
        if concepts.empty:
            st.info("Todavía no hay menciones conceptuales guardadas.")
        else:
            st.dataframe(concepts, use_container_width=True, hide_index=True)

    with tab3:
        if concepts.empty:
            st.info("Sin conceptos para resumir.")
        else:
            st.dataframe(summarize_crystallization(concepts), use_container_width=True, hide_index=True)


def main() -> None:
    init_db()
    st.title("⚙️ Procesamiento guiado")
    st.write(
        "Esta pantalla explicita qué datos existen, qué busca el procesamiento actual, qué acciones ejecuta y qué resultados produjo."
    )

    project_id = project_selector()
    render_input_state(project_id)
    st.divider()
    render_what_it_searches()
    st.divider()
    render_actions(project_id)
    st.divider()
    render_results(project_id)


if __name__ == "__main__":
    main()

# fin pages/02_Procesamiento_guiado.py
