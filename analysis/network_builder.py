"""
analysis/network_builder.py
Construcción de redes básicas desde entidades extraídas.
"""

from __future__ import annotations

import networkx as nx
import pandas as pd


def build_bipartite_network(posts_df: pd.DataFrame, entity_type: str) -> nx.Graph:
    """
    Construye red bipartita autor-entidad o post-entidad según disponibilidad.
    En MVP usa author_id_hash cuando está disponible; si no, usa post_id.
    """
    graph = nx.Graph()
    if posts_df.empty:
        return graph

    for _, row in posts_df.iterrows():
        actor = row.get("author_id_hash") or f"post:{row.get('id')}"
        if not actor:
            continue
        graph.add_node(actor, node_type="actor")
    return graph


def build_entity_cooccurrence(entities_df: pd.DataFrame, entity_type: str) -> nx.Graph:
    """Red de coocurrencia de hashtags, menciones o URLs por publicación."""
    graph = nx.Graph()
    if entities_df.empty:
        return graph

    df = entities_df[entities_df["entity_type"] == entity_type].copy()
    for post_id, group in df.groupby("post_id"):
        values = sorted(set(group["entity_value"].dropna().astype(str)))
        for value in values:
            graph.add_node(value, node_type=entity_type)
        for i, source in enumerate(values):
            for target in values[i + 1 :]:
                if graph.has_edge(source, target):
                    graph[source][target]["weight"] += 1
                else:
                    graph.add_edge(source, target, weight=1, post_id=post_id)
    return graph


def graph_to_nodes_edges(graph: nx.Graph) -> tuple[pd.DataFrame, pd.DataFrame]:
    nodes = []
    for node, attrs in graph.nodes(data=True):
        nodes.append(
            {
                "id": node,
                "label": str(node),
                "node_type": attrs.get("node_type", "unknown"),
                "degree": graph.degree(node),
            }
        )
    edges = []
    for source, target, attrs in graph.edges(data=True):
        edges.append(
            {
                "source": source,
                "target": target,
                "weight": attrs.get("weight", 1),
            }
        )
    return pd.DataFrame(nodes), pd.DataFrame(edges)


def top_entities(entities_df: pd.DataFrame, entity_type: str, n: int = 20) -> pd.DataFrame:
    if entities_df.empty:
        return pd.DataFrame(columns=["entity_value", "count"])
    df = entities_df[entities_df["entity_type"] == entity_type]
    if df.empty:
        return pd.DataFrame(columns=["entity_value", "count"])
    return (
        df.groupby("entity_value")
        .size()
        .reset_index(name="count")
        .sort_values("count", ascending=False)
        .head(n)
    )

# fin analysis/network_builder.py
