"""
analysis/rule_classifier.py
Clasificador inicial basado en reglas interpretables.

Sirve como baseline auditable antes de incorporar modelos IA pagos.
"""

from __future__ import annotations

from typing import Any

from processing.text_cleaner import normalize_for_matching

KEYWORDS = {
    "ideologia_de_genero": ["ideologia de genero", "agenda de genero", "genero impuesto"],
    "denuncias_falsas": ["denuncias falsas", "falsa denuncia", "falsas denuncias", "denuncia falsa"],
    "anti_esi": ["esi", "educacion sexual integral", "adoctrinamiento sexual"],
    "antiaborto": ["aborto", "pro vida", "provida", "pañuelo verde", "panueloverde"],
    "privilegios_feministas": ["privilegios feministas", "curro feminista", "lobby feminista", "ministerio de la mujer"],
    "victimizacion_masculina": ["hombres victimas", "varones victimas", "guerra contra los hombres", "guerra contra los varones"],
    "familia_tradicional": ["familia tradicional", "defender la familia", "destruir la familia"],
    "manosfera_redpill": ["red pill", "redpill", "manosfera", "mgtow", "alfa", "beta"],
    "anti_cuotas_paridad": ["cupo femenino", "cuotas", "paridad", "merito"],
    "ataque_referentes_feministas": ["feminazi", "feminazis", "feminista resentida"],
}

STRATEGY_KEYWORDS = {
    "victimizacion": ["victimas", "discriminados", "nos arruinan", "nadie defiende a los hombres"],
    "inversion_acusacion": ["las verdaderas violentas", "ellas tambien", "los hombres tambien"],
    "ridiculizacion": ["feminazi", "ridiculas", "lloran", "delirio"],
    "generalizacion_caso_particular": ["siempre", "todas", "nunca", "cada vez que", "otro caso mas"],
    "apelacion_sentido_comun": ["sentido comun", "la realidad", "es obvio", "todos sabemos"],
    "enemigo_moral": ["adoctrinan", "destruyen", "corrompen", "enfermos"],
    "apropiacion_lenguaje_derechos": ["igualdad real", "derechos de los hombres", "discriminacion contra hombres"],
    "provocacion_escandalo": ["escandalo", "vergüenza", "verguenza", "basta", "hartos"],
    "sarcasmo_meme": ["jaja", "meme", "payasas", "clown", "😂", "🤣"],
    "deslegitimacion_institucional": ["curro", "caja", "negocio", "ministerio", "ong"],
}

NETWORK_KEYWORDS = {
    "hashtag": ["#"],
    "mencion": ["@"],
    "enlace_externo": ["http://", "https://", "www."],
    "repost": ["rt ", "repost"],
    "quote": ["citado", "quote"],
    "reply": ["respuesta", "respondo"],
    "clip_captura": ["clip", "captura", "video", "miren este"],
}

TARGET_KEYWORDS = {
    "feminismo_general": ["feminismo", "feministas"],
    "politicas_publicas": ["ministerio", "ley", "esi", "cupo", "paridad"],
    "justicia": ["juez", "jueza", "fiscal", "denuncia", "condena"],
    "educacion": ["escuela", "docente", "esi", "adoctrinamiento"],
    "referentes_publicas": ["periodista", "diputada", "ministra", "militante"],
}


def _first_match(text_norm: str, mapping: dict[str, list[str]], default: str = "otro") -> tuple[str, str | None]:
    for label, terms in mapping.items():
        for term in terms:
            if normalize_for_matching(term) in text_norm:
                return label, term
    return default, None


def classify_text(text: str) -> dict[str, Any]:
    text_norm = normalize_for_matching(text)
    frame, frame_term = _first_match(text_norm, KEYWORDS, default="otro")
    strategy, strategy_term = _first_match(text_norm, STRATEGY_KEYWORDS, default="otro")
    network_strategy, _ = _first_match(text.lower(), NETWORK_KEYWORDS, default="otro")
    target, _ = _first_match(text_norm, TARGET_KEYWORDS, default="otro")

    if frame == "otro" and strategy == "otro":
        relevance = "irrelevante"
        intensity = "baja"
        confidence = 0.25
    elif frame in {"ataque_referentes_feministas", "manosfera_redpill"} or strategy in {"ridiculizacion", "enemigo_moral"}:
        relevance = "antifeminismo_explicito"
        intensity = "media"
        confidence = 0.65
    elif frame in {"denuncias_falsas", "ideologia_de_genero", "anti_esi", "victimizacion_masculina"}:
        relevance = "antifeminismo_explicito"
        intensity = "media"
        confidence = 0.7
    else:
        relevance = "critica_politica"
        intensity = "baja"
        confidence = 0.55

    concept = frame if frame != "otro" else None
    explanation_parts = []
    if frame_term:
        explanation_parts.append(f"Detecta marco por expresión: {frame_term}")
    if strategy_term:
        explanation_parts.append(f"Detecta estrategia por expresión: {strategy_term}")
    explanation = "; ".join(explanation_parts) or "Sin coincidencias fuertes en reglas iniciales."

    return {
        "relevance": relevance,
        "frame": frame,
        "intensity": intensity,
        "discursive_strategy": strategy,
        "network_strategy": network_strategy,
        "target": target,
        "concept": concept,
        "model_used": "rules_v0",
        "prompt_version": "rules_0.1",
        "confidence": confidence,
        "explanation": explanation,
    }


def classify_dataframe(df) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for _, post in df.iterrows():
        result = classify_text(str(post.get("text", "")))
        result["post_id"] = int(post["id"])
        rows.append(result)
    return rows

# fin analysis/rule_classifier.py
