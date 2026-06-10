# ──────────────────────────────────────────────────────────────────────────────
# Stage 1 — build del frontend React (Vite + TypeScript)
# ──────────────────────────────────────────────────────────────────────────────
FROM node:22-alpine AS frontend-build

WORKDIR /app/frontend

# Manifest prima del codice per cache layer pulita
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund

COPY frontend/ ./
RUN npm run build

# ──────────────────────────────────────────────────────────────────────────────
# Stage 2 — runtime Python + FastAPI + frontend dist
# ──────────────────────────────────────────────────────────────────────────────
FROM python:3.12-slim-bookworm AS runtime

# Librerie native richieste da PyQt6 (anche in modalità offscreen) e psycopg2
RUN apt-get update && apt-get install -y --no-install-recommends \
        libgl1 \
        libegl1 \
        libglib2.0-0 \
        libxkbcommon0 \
        libdbus-1-3 \
        libfontconfig1 \
        libfreetype6 \
        libxcb-cursor0 \
        libxcb-icccm4 \
        libxcb-image0 \
        libxcb-keysyms1 \
        libxcb-randr0 \
        libxcb-render-util0 \
        libxcb-shape0 \
        libxcb-sync1 \
        libxcb-xfixes0 \
        libxcb-xkb1 \
        libxkbcommon-x11-0 \
        libdbus-1-3 \
        libpq5 \
        curl \
    && rm -rf /var/lib/apt/lists/*

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    QT_QPA_PLATFORM=offscreen \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Dipendenze Python
COPY requirements.txt ./
RUN pip install -r requirements.txt

# Copia codice applicativo
COPY api/ ./api/
COPY db/ ./db/
COPY core/ ./core/
COPY sql_scripts/ ./sql_scripts/
COPY app_paths.py app_utils.py catasto_db_manager.py catasto_exceptions.py \
     config.py custom_widgets.py email_service.py license_manager.py \
     update_checker.py run_api.py ./

# Frontend buildato dallo stage precedente
COPY --from=frontend-build /app/frontend/dist ./frontend/dist

EXPOSE 8765

# Default healthcheck — la SPA risponde su /
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -fsS http://127.0.0.1:8765/ > /dev/null || exit 1

# Avvia uvicorn in modalità factory (no reload in produzione)
CMD ["uvicorn", "api.main:create_app", "--factory", \
     "--host", "0.0.0.0", "--port", "8765"]
