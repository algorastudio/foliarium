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

from api.routes import auth, comuni, partite, possessori, dashboard, audit, genealogia, timeline, immobili
from api.deps import set_db_manager

logger = logging.getLogger("FoliariumAPI")


def _init_db_from_env():
    """Inizializza il DB manager da variabili d'ambiente (nessuna dipendenza da PyQt6)."""
    from catasto_db_manager import CatastoDBManager
    host = os.environ.get("DB_HOST", "localhost")
    user = os.environ.get("DB_USER", "postgres")
    password = os.environ.get("DB_PASS", "postgres")
    dbname = os.environ.get("DB_NAME", "catasto_storico")
    port = int(os.environ.get("DB_PORT", "5432"))
    schema = os.environ.get("DB_SCHEMA", "catasto")
    mgr = CatastoDBManager(dbname=dbname, user=user, password=password,
                           host=host, port=port, schema=schema)
    ok = mgr.initialize_main_pool()
    if not ok:
        raise RuntimeError(f"Impossibile connettersi al database {user}@{host}:{port}/{dbname}")
    set_db_manager(mgr)
    logger.info("DB manager inizializzato: %s@%s:%s/%s", user, host, port, dbname)


def create_app(db_manager=None) -> FastAPI:
    app = FastAPI(title="Foliarium API", version="1.0.0", docs_url="/api/docs")

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
        _init_db_from_env()

    app.include_router(auth.router, prefix="/api")
    app.include_router(comuni.router, prefix="/api")
    app.include_router(partite.router, prefix="/api")
    app.include_router(possessori.router, prefix="/api")
    app.include_router(dashboard.router, prefix="/api")
    app.include_router(audit.router, prefix="/api")
    app.include_router(genealogia.router, prefix="/api")
    app.include_router(timeline.router, prefix="/api")
    app.include_router(immobili.router, prefix="/api")

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
