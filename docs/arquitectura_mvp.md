# Arquitectura MVP - EstudioRedes

## Propósito

EstudioRedes es una aplicación versátil para investigar conversaciones públicas en redes sociales y espacios digitales. La primera investigación será sobre discurso antifeminista, pero la arquitectura está diseñada para soportar distintas temáticas mediante proyectos, codebooks, fuentes y clasificadores reutilizables.

## Principios de diseño

1. **Trazabilidad metodológica:** cada dato debe conservar su fuente, query, corrida de relevamiento, fecha de captura y método de clasificación.
2. **Separación por capas:** relevamiento, normalización, clasificación, análisis, visualización y reporte deben poder evolucionar de manera independiente.
3. **Privacidad y proporcionalidad:** se usan datos públicos, autores hasheados y datos crudos fuera del repositorio.
4. **Auditoría:** la app conserva JSON crudo, clasificación aplicada, versión del codebook, modelo y explicación.
5. **Escalabilidad progresiva:** SQLite y Streamlit para MVP; PostgreSQL, pgvector y workers en una etapa posterior.

## Flujo de trabajo

```text
Fuente / API / CSV
        ↓
collection_runs + raw_items
        ↓
posts normalizados + post_entities
        ↓
classifications + concept_mentions
        ↓
dashboard + redes + reportes
```

## Módulos

### Relevamiento

Carga datos desde X / Twitter, CSV o texto manual. Más adelante se incorporarán YouTube, Bluesky, GDELT, Media Cloud, Reddit y conectores adicionales.

### Procesamiento

Limpia texto, extrae hashtags, menciones y URLs, deduplica publicaciones y normaliza datos heterogéneos.

### Clasificación

La primera versión incluye un clasificador por reglas como baseline interpretable. La próxima etapa incorpora IA con prompts versionados, validación humana y comparación entre modelos.

### Conceptos

Detecta expresiones clave y reconstruye trayectorias conceptuales. El objetivo es observar aparición, circulación inicial, expansión y cristalización dentro del sentido común del universo investigado.

### Redes

La primera versión calcula rankings de entidades. La siguiente incorporará grafos de coocurrencia, menciones, hashtags, URLs, actores-conceptos y comunidades.

### Reportes

Genera un informe Word inicial con resumen, distribución por plataforma, marcos discursivos, conceptos y muestra de publicaciones.

## Próximas iteraciones

1. Integrar OpenAI/Gemini/Claude como clasificadores opcionales.
2. Agregar validación humana y comparación entre etiqueta IA y etiqueta revisada.
3. Incorporar YouTube Data API.
4. Incorporar visualización de grafos interactivos.
5. Agregar exportación Excel completa.
6. Migrar opcionalmente a PostgreSQL/pgvector.
7. Incorporar embeddings y clustering semántico.
8. Agregar módulo de eventos y análisis antes/después.
