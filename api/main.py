"""
api/main.py — FastAPI app locale per il frontend React.
Avviato da APIServerThread in gui_main.py su porta dinamica.
"""
import sys
import os
import socket
import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

# Aggiungi la root del progetto al path così gli import dei moduli locali funzionano
_PROJECT_ROOT = str(Path(__file__).parent.parent)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from api.routes import auth, comuni, partite, possessori, dashboard, audit, genealogia, timeline
from api.deps import set_db_manager

logger = logging.getLogger("FoliariumAPI")


def _init_db_from_config():
    """Inizializza il DB manager da variabili d'ambiente / config.py (usato in dev)."""
    from api.deps import set_db_manager
    from catasto_db_manager import CatastoDBManager
    import config as cfg

    # Schema: env var FOLIARIUM_DB_SCHEMA → config.ini [database].schema → 'catasto' di default
    schema = os.environ.get("FOLIARIUM_DB_SCHEMA")
    if not schema:
        try:
            schema = cfg._ini_get("database", "schema", "")
        except Exception:
            schema = ""
    if not schema:
        schema = "catasto"  # coerente con il bootstrap script (07a_bootstrap_admin.sql)

    # Password: config.ini / env var → keyring di sistema (stessa fonte usata da gui_main.py)
    password = cfg.ENV_DB_PASS
    if not password:
        try:
            from app_utils import get_password_from_keyring
            password = get_password_from_keyring(
                f"foliarium_db_{cfg.ENV_DB_HOST}", cfg.ENV_DB_USER
            ) or ""
            if password:
                logger.info("Password DB letta dal keyring di sistema.")
        except Exception as e:
            logger.warning("Lettura password dal keyring fallita: %s", e)

    mgr = CatastoDBManager(
        dbname=cfg.ENV_DB_NAME,
        user=cfg.ENV_DB_USER,
        password=password,
        host=cfg.ENV_DB_HOST,
        port=cfg.ENV_DB_PORT,
        schema=schema,
    )
    # Retry-loop sull'inizializzazione del pool: in scenari come docker-compose
    # il container app può partire prima che il container db abbia completato
    # gli script SQL di bootstrap, quindi tentiamo per ~60s.
    import time
    deadline = time.monotonic() + 60.0
    attempt = 0
    while True:
        attempt += 1
        if mgr.initialize_main_pool():
            break
        if time.monotonic() >= deadline:
            logger.error("Pool DB non inizializzato dopo 60s — l'API risponderà 503 finché il DB non è raggiungibile.")
            break
        logger.warning("Pool DB non pronto (tentativo %d), retry tra 2s…", attempt)
        time.sleep(2.0)
    set_db_manager(mgr)
    logger.info("DB manager inizializzato: %s@%s/%s schema=%s",
                cfg.ENV_DB_USER, cfg.ENV_DB_HOST, cfg.ENV_DB_NAME, schema)


def create_app(db_manager=None) -> FastAPI:
    app = FastAPI(
        title="Foliarium API",
        version="1.0.0",
        docs_url="/api/v1/docs",
        redoc_url="/api/v1/redoc",
        openapi_url="/api/v1/openapi.json",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:3000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    if db_manager is not None:
        set_db_manager(db_manager)
    else:
        _init_db_from_config()

    # Mount duale: /api/v1/* (preferito, contratto stabile per integrazioni
    # esterne) + /api/* (legacy, mantenuto per il frontend React esistente).
    # Quando il frontend sarà migrato, /api/* potrà essere rimosso.
    _routers = (
        auth.router, comuni.router, partite.router, possessori.router,
        dashboard.router, audit.router, genealogia.router, timeline.router,
    )
    for r in _routers:
        app.include_router(r, prefix="/api/v1")
        app.include_router(r, prefix="/api", include_in_schema=False)

    # Serve il build React statico (frontend/dist/)
    dist_dir = Path(__file__).parent.parent / "frontend" / "dist"
    if dist_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(dist_dir / "assets")), name="assets")

        @app.get("/{full_path:path}")
        async def spa_fallback(full_path: str):
            index = dist_dir / "index.html"
            return FileResponse(str(index))

    return app


def find_free_port(start: int = 8765) -> int:
    for port in range(start, start + 100):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue
    raise RuntimeError("Nessuna porta libera trovata")
