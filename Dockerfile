# Immagine dello stack web di Foliarium: l'API REST di `api/` e il frontend
# React che l'API serve come contenuto statico.
#
# L'applicazione desktop non c'entra: niente PyQt6, niente librerie Qt di
# sistema. Il contenuto Python e' quello dell'artefatto che
# .github/workflows/main_foliarium.yml pubblica su Azure, con le stesse
# dipendenze (requirements-web.txt).
#
# Si costruisce dalla radice del repository, di solito con docker compose
# (vedi docker/README.md). docker/prova-web.sh la costruisce, avvia lo stack
# e ne verifica il funzionamento; la CI lo esegue a ogni pull request.

# Immagini di base sostituibili: servono dove le build escono da un proxy che
# richiede una CA propria. Normalmente non vanno toccate.
ARG FRONTEND_BASE_IMAGE=node:22-alpine
ARG BASE_IMAGE=python:3.12-slim-bookworm

# ──────────────────────────────────────────────────────────────────────────────
# Stage 1 — build del frontend React (Vite + TypeScript)
# ──────────────────────────────────────────────────────────────────────────────
FROM ${FRONTEND_BASE_IMAGE} AS frontend-build

WORKDIR /app/frontend

# Manifest prima del codice per cache layer pulita
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund

COPY frontend/ ./
RUN npm run build

# ──────────────────────────────────────────────────────────────────────────────
# Stage 2 — runtime: API FastAPI + frontend compilato
# ──────────────────────────────────────────────────────────────────────────────
FROM ${BASE_IMAGE} AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

# Utente senza privilegi. Serve una home scrivibile: app_paths crea
# ~/.foliarium (log, cache, esportazioni) al primo import.
RUN useradd --system --create-home --home-dir /home/foliarium foliarium

WORKDIR /app

# Nessun pacchetto di sistema: psycopg2-binary include gia' libpq.
COPY requirements-web.txt ./
RUN pip install -r requirements-web.txt

# Stesso elenco dell'artefatto Azure (main_foliarium.yml): se cambia uno dei
# due, va cambiato anche l'altro. app_utils.py resta fuori di proposito:
# importa PyQt6, e api/main.py lo usa solo per leggere la password dal
# portachiavi quando DB_PASS manca (nel container c'e' sempre).
COPY api/ ./api/
COPY db/ ./db/
COPY core/ ./core/
COPY utils/ ./utils/
COPY catasto_db_manager.py config.py app_paths.py catasto_exceptions.py \
     validators.py ./

# Frontend buildato dallo stage precedente
COPY --from=frontend-build /app/frontend/dist ./frontend/dist

USER foliarium

EXPOSE 8765

# La SPA risponde su /. In Python perche' l'immagine non ha curl, e
# installarlo richiederebbe apt solo per questo.
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8765/', timeout=4)"]

# Avvia uvicorn in modalità factory (no reload in produzione)
CMD ["uvicorn", "api.main:create_app", "--factory", \
     "--host", "0.0.0.0", "--port", "8765"]
