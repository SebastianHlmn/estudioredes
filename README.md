# EstudioRedes

Aplicación de investigación social y análisis de redes digitales para relevar, procesar, clasificar, visualizar y reportar conversaciones públicas en distintas plataformas.

La primera investigación configurada será sobre discurso antifeminista, pero la arquitectura está pensada para estudiar múltiples temáticas mediante proyectos, fuentes, codebooks y clasificadores reutilizables.

## Objetivos

- Relevar publicaciones y metadatos desde APIs oficiales, cargas manuales y fuentes abiertas.
- Normalizar datos heterogéneos en una base común.
- Clasificar contenidos con reglas, NLP e IA trazable.
- Analizar estrategias discursivas, estrategias de circulación y trayectorias conceptuales.
- Visualizar series temporales, conceptos, hashtags, enlaces, actores y redes.
- Generar reportes ejecutivos y anexos metodológicos.

## Primera versión

La versión inicial usa:

- Python
- Streamlit
- SQLite
- pandas
- requests
- NetworkX
- Plotly
- python-dotenv

## Instalación rápida

```bash
conda create -n estudioredes python=3.11 -y
conda activate estudioredes
pip install -r requirements.txt
copy .env.example .env
streamlit run app.py
```

En Windows PowerShell:

```powershell
conda create -n estudioredes python=3.11 -y
conda activate estudioredes
pip install -r requirements.txt
Copy-Item .env.example .env
streamlit run app.py
```

## Estructura

```text
estudioredes/
├── app.py
├── config.py
├── db_manager.py
├── requirements.txt
├── .env.example
├── collectors/
├── processing/
├── analysis/
├── reports/
├── tabs/
└── data/
```

## Credenciales

Las claves de APIs se guardan en `.env`. Nunca deben subirse al repositorio.

Variables iniciales:

```text
X_BEARER_TOKEN=
OPENAI_API_KEY=
DEFAULT_PROJECT_NAME=Discurso antifeminista
```

## Estado

MVP inicial en desarrollo.
