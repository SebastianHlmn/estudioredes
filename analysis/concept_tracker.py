"""
analysis/concept_tracker.py
Seguimiento de trayectorias conceptuales y cristalización.
"""

from __future__ import annotations

from typing import Any

import pandas as pd

from processing.text_cleaner import normalize_for_matching

CONCEPT_EXPRESSIONS = {
    "ideologia_de_genero": ["ideología de género", "ideologia de genero", "agenda de género", "agenda de genero"],
    "denuncias_falsas": ["denuncias falsas", "falsas denuncias", "falsa denuncia", "denuncia falsa"],
    "adoctrinamiento": ["adoctrinamiento", "adoctrinan", "adoctrinar"],
    "privilegios_feministas": ["privilegios feministas", "curro feminista", "lobby feminista"],
    "guerra_contra_varones": ["guerra contra los hombres", "guerra contra los varones", "hombres víctimas", "varones víctimas"],
    "feminazi": ["feminazi", "feminazis"],
    "familia_tradicional": ["familia tradicional", "defender la familia", "destruir la familia"],
}


def detect_concepts_in_text(text: str) -> list[dict[str, str]]:
    text_norm = normalize_for_matching(text)
    found: list[dict[str, str]] = []
    for concept, expressions in CONCEPT_EXPRESSIONS.items():
        for expression in expressions:
            if normalize_for_matching(expression) in text_norm:
                found.append(
                    {
                        "concept": concept,
                        "expression_detected": expression,
                        "normalized_concept": concept,
                    }
                )
                break
    return found


def build_concept_mentions(posts_df: pd.DataFrame) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for _, post in posts_df.iterrows():
        for item in detect_concepts_in_text(str(post.get("text", ""))):
            rows.append(
                {
                    "post_id": int(post["id"]),
                    "concept": item["concept"],
                    "expression_detected": item["expression_detected"],
                    "normalized_concept": item["normalized_concept"],
                    "stage": "detectado",
                    "platform": post.get("platform"),
                    "created_at": post.get("created_at"),
                }
            )
    return rows


def summarize_crystallization(concepts_df: pd.DataFrame) -> pd.DataFrame:
    if concepts_df.empty:
        return pd.DataFrame(
            columns=["concepto", "primer_registro", "ultimo_registro", "menciones", "plataformas", "etapa"]
        )

    df = concepts_df.copy()
    df["created_at_dt"] = pd.to_datetime(df["created_at"], errors="coerce")
    summary = (
        df.groupby("normalized_concept")
        .agg(
            primer_registro=("created_at_dt", "min"),
            ultimo_registro=("created_at_dt", "max"),
            menciones=("id", "count"),
            plataformas=("platform", lambda x: ", ".join(sorted({str(v) for v in x.dropna()}))),
        )
        .reset_index()
        .rename(columns={"normalized_concept": "concepto"})
    )

    def stage(row) -> str:
        mentions = row["menciones"]
        platforms = len([p for p in str(row["plataformas"]).split(",") if p.strip()])
        if mentions >= 50 and platforms >= 2:
            return "cristalizacion_alta"
        if mentions >= 15:
            return "expansion"
        if mentions >= 3:
            return "circulacion_inicial"
        return "aparicion"

    summary["etapa"] = summary.apply(stage, axis=1)
    return summary.sort_values(["menciones", "concepto"], ascending=[False, True])

# fin analysis/concept_tracker.py
