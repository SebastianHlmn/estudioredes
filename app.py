"""
app.py
EstudioRedes - MVP inicial.

Aplicación Streamlit para relevamiento, procesamiento, visualización,
análisis discursivo y reportes de conversaciones públicas en redes.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

from analysis.concept_tracker import build_concept_mentions, summarize_crystallization
from analysis.rule_classifier import classify_dataframe
from collectors.manual_importer import dataframe_to_posts, single_text_to_post
from collectors.x_collector import XCollectorError, estimate_x_cost, search_recent
from collectors.x_query_builder import (
    build_seed_post_queries,
    build_thematic_query,
    extract_x_post_id,
    split_terms,
)
from config import (
    DATABASE_PATH,
    DEFAULT_PROJECT_NAME,
    X_BEARER_TOKEN,
    X_PRICE_PER_POST_USD,
    get_config_diagnostics,
)
from db_manager import (
    concept_mentions_df,
    create_collection_run,
    finish_collection_run,
    get_or_create_project,
    init_db,
    insert_classifications,
    insert_concept_mentions,
    insert_posts,
    insert_raw_item,
    list_collection_runs,
    list_posts,
    list_projects,
    pending_classification,
)
from reports.report_generator import generate_basic_report

st.set_page_config(
    page_title="EstudioRedes",
    page_icon="🕸️",
    layout="wide",
)


def read_entities(project_id: int) -> pd.DataFrame:
    con = sqlite3.connect(DATABASE_PATH)
    df = pd.read_sql_query(
        """
        SELECT e.*
        FROM post_entities e
        JOIN posts p ON p.id = e.post_id
        WHERE p.project_id = ?
        """,
        con,
        params=(project_id,),
    )
    con.close()
    return df


def sidebar_project_selector() -> int:
    projects = list_projects()
    if projects.empty:
        project_id = get_or_create_project(DEFAULT_PROJECT_NAME)
        projects = list_projects()
    options = dict(zip(projects["name"], projects["id"]))
    selected = st.sidebar.selectbox("Proyecto", list(options.keys()))
    return int(options[selected])


def render_config_diagnostics() -> None:
    with st.sidebar.expander("Diagnóstico .env / claves", expanded=not bool(X_BEARER_TOKEN)):
        diag = get_config_diagnostics()
        st.write("**Archivo .env detectado:**", "sí" if diag["env_exists"] else "no")
        st.caption(str(diag["env_path"]))
        st.write("**X_BEARER_TOKEN:**", diag["x_bearer_token"])
        st.write("**Base SQLite:**")
        st.caption(str(diag["database_path"]))
        if not X_BEARER_TOKEN:
            st.warning("La app no está viendo X_BEARER_TOKEN. Revisá que exista .env en la raíz y reiniciá Streamlit.")


def run_x_query(
    project_id: int,
    query: str,
    max_results: int,
    notes: str,
    source_label: str = "api",
) -> tuple[int, int]:
    estimated = estimate_x_cost(int(max_results), X_PRICE_PER_POST_USD)
    run_id = create_collection_run(
        project_id=project_id,
        source=source_label,
        platform="x",
        query=query,
        max_results=int(max_results),
        estimated_cost_usd=estimated,
        notes=notes,
    )
    try:
        posts, raw_payloads = search_recent(query, project_id, run_id, int(max_results))
        for payload in raw_payloads:
            insert_raw_item(run_id, "x", None, payload)
        inserted = insert_posts(posts)
        finish_collection_run(run_id, "finished", inserted)
        return run_id, inserted
    except XCollectorError as exc:
        finish_collection_run(run_id, "error", 0, notes=str(exc))
        raise


def tab_inicio(project_id: int) -> None:
    st.header("EstudioRedes")
    st.write(
        "Aplicación de investigación social computacional para estudiar conversaciones públicas, "
        "estrategias discursivas, redes de circulación y trayectorias conceptuales."
    )

    posts = list_posts(project_id, limit=100000)
    runs = list_collection_runs(project_id)
    concepts = concept_mentions_df(project_id)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Publicaciones", len(posts))
    c2.metric("Corridas", len(runs))
    c3.metric("Conceptos detectados", len(concepts))
    c4.metric("Base", str(DATABASE_PATH.name))

    st.subheader("Investigación inicial")
    st.markdown(
        """
        **Tema inicial:** análisis crítico de ideas antifeministas en redes sociales.  
        **Objeto ampliable:** la app está preparada para crear nuevas investigaciones con otros codebooks, fuentes y clasificadores.
        """
    )

    st.subheader("Arquitectura funcional")
    st.code(
        """Relevamiento → Normalización → Clasificación → Conceptos → Redes → Reportes""",
        language="text",
    )


def tab_relevamiento(project_id: int) -> None:
    st.header("Relevamiento")
    st.write("Carga manual, CSV, queries libres de X y relevamientos orientados a redes exploratorias.")

    mode = st.radio(
        "Modo de carga",
        [
            "Texto manual",
            "CSV",
            "X: query libre",
            "X: red temática",
            "X: desde post semilla",
        ],
        horizontal=False,
    )

    if mode == "Texto manual":
        with st.form("manual_text_form"):
            platform = st.text_input("Plataforma", value="manual")
            text = st.text_area("Texto de la publicación", height=180)
            author = st.text_input("Autor / usuario opcional")
            created_at = st.text_input("Fecha opcional")
            url = st.text_input("URL opcional")
            submitted = st.form_submit_button("Guardar publicación")
        if submitted:
            if not text.strip():
                st.error("Pegá un texto para guardar.")
            else:
                run_id = create_collection_run(
                    project_id=project_id,
                    source="manual",
                    platform=platform,
                    query="texto_manual",
                    max_results=1,
                    estimated_cost_usd=0,
                    notes="Carga manual desde Streamlit",
                )
                post = single_text_to_post(
                    text=text,
                    project_id=project_id,
                    collection_run_id=run_id,
                    platform=platform,
                    author=author or None,
                    created_at=created_at or None,
                    url=url or None,
                )
                inserted = insert_posts([post])
                finish_collection_run(run_id, "finished", inserted)
                st.success(f"Publicación guardada. Insertadas: {inserted}")

    elif mode == "CSV":
        st.info("El CSV debe tener una columna text, texto, contenido, post o publicacion.")
        uploaded = st.file_uploader("Subir CSV", type=["csv"])
        default_platform = st.text_input("Plataforma por defecto", value="manual_csv")
        if uploaded is not None:
            df = pd.read_csv(uploaded)
            st.dataframe(df.head(20), use_container_width=True)
            if st.button("Importar CSV"):
                run_id = create_collection_run(
                    project_id=project_id,
                    source="csv",
                    platform=default_platform,
                    query="csv_upload",
                    max_results=len(df),
                    estimated_cost_usd=0,
                    notes=f"Archivo: {uploaded.name}",
                )
                try:
                    posts = dataframe_to_posts(df, project_id, run_id, default_platform)
                    inserted = insert_posts(posts)
                    finish_collection_run(run_id, "finished", inserted)
                    st.success(f"CSV importado. Insertadas: {inserted}")
                except Exception as exc:
                    finish_collection_run(run_id, "error", 0, notes=str(exc))
                    st.error(str(exc))

    elif mode == "X: query libre":
        st.subheader("X / Twitter Recent Search - query libre")
        if not X_BEARER_TOKEN:
            st.warning("Falta X_BEARER_TOKEN en .env. Podés preparar la query y estimar costo, pero no ejecutar.")

        query = st.text_area(
            "Query X",
            value='("denuncias falsas" OR "falsas denuncias") lang:es -is:retweet',
            height=120,
        )
        max_results = st.number_input("Máximo de posts", min_value=10, max_value=10000, value=100, step=10)
        estimated = estimate_x_cost(int(max_results), X_PRICE_PER_POST_USD)
        st.metric("Costo estimado", f"USD {estimated:.2f}")
        st.caption("El precio real debe confirmarse en la consola de X. Este valor es configurable en .env.")

        if st.button("Ejecutar búsqueda en X", disabled=not bool(X_BEARER_TOKEN)):
            try:
                _, inserted = run_x_query(
                    project_id=project_id,
                    query=query,
                    max_results=int(max_results),
                    notes="Recent Search API - query libre",
                )
                st.success(f"Búsqueda finalizada. Posts normalizados insertados: {inserted}")
            except XCollectorError as exc:
                st.error(str(exc))

    elif mode == "X: red temática":
        st.subheader("X / Twitter - red exploratoria por temática")
        st.write(
            "Este modo sirve para mapear actores hasheados, hashtags, menciones, dominios y conceptos alrededor de una temática. "
            "Primero conviene usar pocos resultados y revisar ruido."
        )
        if not X_BEARER_TOKEN:
            st.warning("Falta X_BEARER_TOKEN en .env. Podés construir la query, pero no ejecutar.")

        col1, col2 = st.columns(2)
        with col1:
            core_raw = st.text_area(
                "Núcleo conceptual",
                value='falsa denuncia, falsas denuncias, denuncia falsa, denuncias falsas',
                height=110,
                help="Separá términos por coma o salto de línea. Las frases con espacios se ponen entre comillas automáticamente.",
            )
        with col2:
            context_raw = st.text_area(
                "Contexto / anclajes",
                value='feminismo, feminista, feministas, género, genero, mujer, mujeres, varones, hombres',
                height=110,
                help="Términos que reducen ruido y acercan la búsqueda al universo de análisis.",
            )

        c1, c2, c3, c4 = st.columns(4)
        include_replies = c1.checkbox("Incluir respuestas", value=True)
        include_retweets = c2.checkbox("Incluir retweets", value=False)
        only_quotes = c3.checkbox("Solo citas", value=False)
        require_mentions = c4.checkbox("Exigir menciones", value=False)
        require_links = st.checkbox("Exigir links", value=False)
        max_results = st.number_input("Máximo de posts", min_value=10, max_value=10000, value=100, step=10, key="thematic_max")

        query = build_thematic_query(
            core_terms=split_terms(core_raw),
            context_terms=split_terms(context_raw),
            lang="es",
            include_replies=include_replies,
            include_retweets=include_retweets,
            only_quotes=only_quotes,
            require_links=require_links,
            require_mentions=require_mentions,
        )
        estimated = estimate_x_cost(int(max_results), X_PRICE_PER_POST_USD)

        st.subheader("Query construida")
        st.code(query, language="text")
        st.caption(f"Caracteres: {len(query)} / 512 para Recent Search self-serve")
        st.metric("Costo estimado", f"USD {estimated:.2f}")

        if len(query) > 512:
            st.error("La query supera 512 caracteres. Recortá términos para Recent Search.")

        if st.button("Ejecutar red temática", disabled=(not bool(X_BEARER_TOKEN) or len(query) > 512)):
            try:
                _, inserted = run_x_query(
                    project_id=project_id,
                    query=query,
                    max_results=int(max_results),
                    notes="Red exploratoria temática - posts only",
                    source_label="api_network_theme",
                )
                st.success(f"Relevamiento temático finalizado. Posts insertados: {inserted}")
                st.info("Ahora revisá Dashboard, Redes y luego Procesamiento → detectar conceptos/clasificar.")
            except XCollectorError as exc:
                st.error(str(exc))

    else:
        st.subheader("X / Twitter - red desde post semilla")
        st.write(
            "Este modo parte de un post público y arma una red de conversación, respuestas directas y citas. "
            "Es útil cuando una figura pública activa un tema y queremos observar cómo se discute y amplifica."
        )
        if not X_BEARER_TOKEN:
            st.warning("Falta X_BEARER_TOKEN en .env. Podés construir las queries, pero no ejecutar.")

        seed_url = st.text_input(
            "URL o ID del post semilla",
            value="https://x.com/carolinalosada/status/1930341949384601860",
        )
        post_id = extract_x_post_id(seed_url)
        if post_id:
            st.success(f"ID detectado: {post_id}")
        else:
            st.error("No pude detectar el ID del post. Pegá una URL de X con /status/ o el ID numérico.")

        c1, c2, c3, c4 = st.columns(4)
        include_conversation = c1.checkbox("Conversación", value=True)
        include_direct_replies = c2.checkbox("Respuestas directas", value=True)
        include_quotes = c3.checkbox("Citas", value=True)
        include_retweets = c4.checkbox("Retweets", value=False)
        max_per_query = st.number_input("Máximo por query", min_value=10, max_value=1000, value=100, step=10, key="seed_max")

        built = []
        if post_id:
            built = build_seed_post_queries(
                post_id=post_id,
                lang="es",
                include_conversation=include_conversation,
                include_direct_replies=include_direct_replies,
                include_quotes=include_quotes,
                include_retweets=include_retweets,
            )

        st.subheader("Queries construidas")
        total_estimated = estimate_x_cost(int(max_per_query) * len(built), X_PRICE_PER_POST_USD)
        for item in built:
            st.markdown(f"**{item.label}** — {item.objective}")
            st.code(item.query, language="text")
        st.metric("Costo máximo estimado", f"USD {total_estimated:.2f}")
        st.caption("Puede costar menos si X devuelve menos posts que el máximo solicitado.")

        if st.button("Ejecutar red desde post semilla", disabled=(not bool(X_BEARER_TOKEN) or not bool(built))):
            total_inserted = 0
            errors = []
            for item in built:
                try:
                    _, inserted = run_x_query(
                        project_id=project_id,
                        query=item.query,
                        max_results=int(max_per_query),
                        notes=f"Red desde post semilla {post_id} - {item.label}: {item.objective}",
                        source_label="api_network_seed",
                    )
                    total_inserted += inserted
                except XCollectorError as exc:
                    errors.append(f"{item.label}: {exc}")
            if errors:
                st.error("\n".join(errors))
            st.success(f"Red desde semilla finalizada. Posts insertados: {total_inserted}")
            st.info("Ahora revisá Redes para hashtags/menciones y Procesamiento para clasificar/detectar conceptos.")

    st.subheader("Corridas")
    st.dataframe(list_collection_runs(project_id), use_container_width=True)


def tab_procesamiento(project_id: int) -> None:
    st.header("Procesamiento y clasificación")

    pending = pending_classification(project_id, limit=1000)
    st.metric("Pendientes de clasificación", len(pending))

    col1, col2 = st.columns(2)
    with col1:
        limit = st.number_input("Cantidad a clasificar", min_value=1, max_value=1000, value=100, step=50)
        if st.button("Clasificar pendientes con reglas 0.1"):
            df = pending_classification(project_id, limit=int(limit))
            rows = classify_dataframe(df)
            inserted = insert_classifications(rows)
            st.success(f"Clasificaciones insertadas: {inserted}")

    with col2:
        if st.button("Detectar conceptos en publicaciones"):
            posts = list_posts(project_id, limit=100000)
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

    st.subheader("Muestra de publicaciones")
    st.dataframe(list_posts(project_id, limit=200), use_container_width=True)


def tab_dashboard(project_id: int) -> None:
    st.header("Dashboard")
    posts = list_posts(project_id, limit=100000)
    if posts.empty:
        st.info("Todavía no hay publicaciones cargadas.")
        return

    posts["date"] = pd.to_datetime(posts["created_at"], errors="coerce").dt.date

    c1, c2, c3 = st.columns(3)
    c1.metric("Publicaciones", len(posts))
    c2.metric("Plataformas", posts["platform"].nunique())
    c3.metric("Clasificadas", posts["frame"].notna().sum())

    if posts["date"].notna().any():
        by_date = posts.dropna(subset=["date"]).groupby("date").size().reset_index(name="publicaciones")
        fig = px.line(by_date, x="date", y="publicaciones", title="Evolución temporal")
        st.plotly_chart(fig, use_container_width=True)

    col1, col2 = st.columns(2)
    with col1:
        if "frame" in posts.columns:
            frame_df = posts.groupby("frame", dropna=False).size().reset_index(name="publicaciones")
            frame_df = frame_df.sort_values("publicaciones", ascending=False)
            fig = px.bar(frame_df, x="publicaciones", y="frame", orientation="h", title="Marcos discursivos")
            st.plotly_chart(fig, use_container_width=True)
    with col2:
        if "discursive_strategy" in posts.columns:
            strat_df = posts.groupby("discursive_strategy", dropna=False).size().reset_index(name="publicaciones")
            strat_df = strat_df.sort_values("publicaciones", ascending=False)
            fig = px.bar(strat_df, x="publicaciones", y="discursive_strategy", orientation="h", title="Estrategias discursivas")
            st.plotly_chart(fig, use_container_width=True)

    entities = read_entities(project_id)
    if not entities.empty:
        st.subheader("Entidades extraídas")
        ent_type = st.selectbox("Tipo", sorted(entities["entity_type"].unique()))
        top = (
            entities[entities["entity_type"] == ent_type]
            .groupby("entity_value")
            .size()
            .reset_index(name="cantidad")
            .sort_values("cantidad", ascending=False)
            .head(30)
        )
        st.dataframe(top, use_container_width=True)


def tab_conceptos(project_id: int) -> None:
    st.header("Conceptos y cristalización")
    concepts = concept_mentions_df(project_id)
    if concepts.empty:
        st.info("Todavía no hay conceptos detectados. Ejecutá detección desde Procesamiento.")
        return

    summary = summarize_crystallization(concepts)
    st.subheader("Resumen de trayectorias")
    st.dataframe(summary, use_container_width=True)

    selected = st.selectbox("Concepto", summary["concepto"].tolist())
    df = concepts[concepts["normalized_concept"] == selected].copy()
    df["date"] = pd.to_datetime(df["created_at"], errors="coerce").dt.date
    if df["date"].notna().any():
        trend = df.dropna(subset=["date"]).groupby("date").size().reset_index(name="menciones")
        fig = px.line(trend, x="date", y="menciones", title=f"Trayectoria: {selected}")
        st.plotly_chart(fig, use_container_width=True)

    st.subheader("Menciones")
    st.dataframe(df, use_container_width=True)


def tab_redes(project_id: int) -> None:
    st.header("Redes")
    posts = list_posts(project_id, limit=100000)
    entities = read_entities(project_id)
    if posts.empty and entities.empty:
        st.info("Todavía no hay datos para construir redes.")
        return

    st.subheader("Nodos de autores hasheados")
    if not posts.empty and "author_id_hash" in posts.columns:
        authors = (
            posts.dropna(subset=["author_id_hash"])
            .groupby("author_id_hash")
            .agg(
                publicaciones=("id", "count"),
                likes=("like_count", "sum"),
                replies=("reply_count", "sum"),
                reposts=("repost_count", "sum"),
                quotes=("quote_count", "sum"),
            )
            .reset_index()
        )
        if not authors.empty:
            authors["interacciones_publicas"] = authors[["likes", "replies", "reposts", "quotes"]].sum(axis=1)
            authors = authors.sort_values(["publicaciones", "interacciones_publicas"], ascending=False).head(30)
            st.dataframe(authors, use_container_width=True)
        else:
            st.info("Todavía no hay autores detectados.")

    if not entities.empty:
        st.subheader("Entidades y coocurrencias")
        entity_type = st.selectbox("Tipo de entidad", sorted(entities["entity_type"].unique()))
        df = entities[entities["entity_type"] == entity_type]
        if df.empty:
            st.info("Sin datos para este tipo de entidad.")
            return
        top = df.groupby("entity_value").size().reset_index(name="cantidad").sort_values("cantidad", ascending=False).head(50)
        fig = px.bar(top, x="cantidad", y="entity_value", orientation="h", title=f"Top {entity_type}")
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(top, use_container_width=True)

    st.caption(
        "Esta red inicial usa autores hasheados, hashtags, menciones y URLs. "
        "La siguiente iteración agregará grafo interactivo y detección de comunidades."
    )


def tab_reportes(project_id: int) -> None:
    st.header("Reportes")
    posts = list_posts(project_id, limit=100000)
    concepts = concept_mentions_df(project_id)
    concept_summary = summarize_crystallization(concepts)

    project_name = DEFAULT_PROJECT_NAME
    if st.button("Generar reporte Word inicial"):
        path = generate_basic_report(project_name, posts, concept_summary)
        st.success(f"Reporte generado: {path}")
        with open(path, "rb") as f:
            st.download_button(
                "Descargar reporte",
                data=f.read(),
                file_name=Path(path).name,
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )

    st.subheader("Datos disponibles")
    st.dataframe(posts.head(200), use_container_width=True)


def main() -> None:
    init_db()
    st.sidebar.title("EstudioRedes")
    render_config_diagnostics()
    project_id = sidebar_project_selector()

    tabs = st.tabs([
        "Inicio",
        "Relevamiento",
        "Procesamiento",
        "Dashboard",
        "Conceptos",
        "Redes",
        "Reportes",
    ])

    with tabs[0]:
        tab_inicio(project_id)
    with tabs[1]:
        tab_relevamiento(project_id)
    with tabs[2]:
        tab_procesamiento(project_id)
    with tabs[3]:
        tab_dashboard(project_id)
    with tabs[4]:
        tab_conceptos(project_id)
    with tabs[5]:
        tab_redes(project_id)
    with tabs[6]:
        tab_reportes(project_id)


if __name__ == "__main__":
    main()

# fin app.py
