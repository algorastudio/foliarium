"""
api/webview_launcher.py — PyWebView + FastAPI launcher per modalità web moderna.

Questo modulo avvia una finestra PyWebView che carica il frontend React bundled,
con FastAPI backend in esecuzione in background. È un'alternativa alla modalità
PyQt6 tradizionale.

Funzionalità:
- Auto-build frontend React se necessario (verifica timestamp di src/ vs dist/)
- Avvia FastAPI su porta dinamica
- Carica http://localhost:PORT in PyWebView
- Expose API Python side per operazioni di sistema (log, config, etc.)
- Graceful shutdown con cleanup
"""
import sys
import os
import time
import logging
import subprocess
import threading
from pathlib import Path
from typing import Optional

logger = logging.getLogger("FoliariumWebView")


class WebViewLauncher:
    """Gestore del ciclo di vita PyWebView + FastAPI integrati."""

    def __init__(self, db_manager, use_dev_mode: bool = False):
        """
        Inizializza il launcher.

        Args:
            db_manager: CatastoDBManager connesso al database
            use_dev_mode: Se True, non compila frontend e usa Vite dev server.
                         Utile per development. Default: False (production mode)
        """
        self.db_manager = db_manager
        self.use_dev_mode = use_dev_mode
        self._api_port: Optional[int] = None
        self._api_server_thread: Optional[threading.Thread] = None
        self._server = None

    def _find_free_port(self, start_port: int = 8765) -> int:
        """Trova una porta TCP libera a partire da start_port."""
        import socket
        port = start_port
        while port <= 9999:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                try:
                    s.bind(("127.0.0.1", port))
                    return port
                except OSError:
                    port += 1
        raise RuntimeError("Nessuna porta disponibile tra 8765 e 9999")

    def _ensure_frontend_built(self) -> bool:
        """
        Verifica se il frontend React è stato compilato.
        Se non esiste dist/, tenta una compilazione.

        Returns:
            True se dist/index.html esiste e è utilizzabile, False se fallisce.
        """
        frontend_dir = Path(__file__).parent.parent / "frontend"
        dist_dir = frontend_dir / "dist"
        index_html = dist_dir / "index.html"

        # Se index.html esiste, consideriamo il build valido
        if index_html.exists():
            logger.info(f"Frontend compilato rilevato: {index_html}")
            return True

        logger.warning("Frontend compilato non trovato, tentativo compilazione...")

        # In dev mode, il build non è necessario (usa Vite dev server)
        if self.use_dev_mode:
            logger.info("Dev mode: Vite server utilizzerà il codice source direttamente")
            return True

        # Tentativo compilazione con npm
        if not (frontend_dir / "package.json").exists():
            logger.error("package.json non trovato in frontend/")
            return False

        try:
            logger.info("Esecuzione: cd frontend && npm run build")
            result = subprocess.run(
                ["npm", "run", "build"],
                cwd=str(frontend_dir),
                capture_output=True,
                text=True,
                timeout=300,  # 5 minuti timeout
            )
            if result.returncode != 0:
                logger.error(f"Build frontend fallito:\n{result.stderr}")
                return False

            logger.info("Build frontend completato con successo")
            return index_html.exists()

        except subprocess.TimeoutExpired:
            logger.error("Build frontend timeout (>5 minuti)")
            return False
        except FileNotFoundError:
            logger.error("npm non trovato nel PATH. Installa Node.js.")
            return False
        except Exception as e:
            logger.error(f"Errore durante build frontend: {e}")
            return False

    def _start_fastapi_background(self) -> bool:
        """
        Avvia FastAPI server in un thread daemon.

        Returns:
            True se il server è stato avviato correttamente, False altrimenti.
        """
        try:
            import uvicorn
            from api.main import create_app

            self._api_port = self._find_free_port(8765)

            app = create_app(self.db_manager)

            # Configura StaticFiles per servire il frontend compilato
            # (alternativa: uvicorn serve via --root-path)
            frontend_dist = Path(__file__).parent.parent / "frontend" / "dist"
            if frontend_dist.exists():
                from fastapi.staticfiles import StaticFiles
                from fastapi.responses import FileResponse
                app.mount("/", StaticFiles(directory=str(frontend_dist), html=True), name="static")
                logger.info(f"StaticFiles montato: {frontend_dist}")
            else:
                logger.warning(f"frontend/dist non trovato, StaticFiles non montato")

            config = uvicorn.Config(
                app,
                host="127.0.0.1",
                port=self._api_port,
                log_level="warning",
                loop="asyncio",
                access_log=False,
            )
            self._server = uvicorn.Server(config)

            def run_server():
                try:
                    import asyncio
                    asyncio.run(self._server.serve())
                except Exception as e:
                    logger.error(f"Errore server FastAPI: {e}")

            self._api_server_thread = threading.Thread(target=run_server, daemon=True)
            self._api_server_thread.start()

            # Attesa che il server sia pronto (max 5 secondi)
            for attempt in range(50):
                try:
                    import socket
                    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    s.connect(("127.0.0.1", self._api_port))
                    s.close()
                    logger.info(f"FastAPI server avviato su http://127.0.0.1:{self._api_port}")
                    return True
                except ConnectionRefusedError:
                    time.sleep(0.1)

            logger.error("FastAPI server non è entrato in ascolto entro 5 secondi")
            return False

        except ImportError as e:
            logger.error(f"Dipendenza mancante per FastAPI: {e}")
            return False
        except Exception as e:
            logger.error(f"Errore avvio FastAPI: {e}")
            return False

    def launch(self) -> bool:
        """
        Lancia l'applicazione PyWebView + FastAPI.

        Returns:
            True se il lancio ha successo, False altrimenti.
        """
        logger.info("===== Foliarium WebView Launcher =====")
        logger.info(f"Use dev mode: {self.use_dev_mode}")

        # Step 1: Verifica frontend compilato
        if not self._ensure_frontend_built():
            logger.error("Frontend non disponibile. Fallback a PyQt6.")
            return False

        # Step 2: Avvia FastAPI
        if not self._start_fastapi_background():
            logger.error("FastAPI non si è avviato. Fallback a PyQt6.")
            return False

        # Step 3: Avvia PyWebView
        try:
            import webview

            def on_close():
                """Callback chiusura PyWebView."""
                logger.info("PyWebView chiuso, shutdown in corso...")
                self.shutdown()

            api = WebViewAPI(self.db_manager)

            window = webview.create_window(
                title="Foliarium — Archivio Catastale Storico",
                url=f"http://127.0.0.1:{self._api_port}",
                width=1280,
                height=800,
                min_size=(900, 600),
                background_color="#FFFFFF",
                js_api=api,
            )

            window.events.closed += on_close

            logger.info("Lancio PyWebView...")
            webview.start(debug=False)
            return True

        except ImportError:
            logger.error("pywebview non installato. Fallback a PyQt6.")
            return False
        except Exception as e:
            logger.error(f"Errore lancio PyWebView: {e}")
            return False

    def shutdown(self):
        """Arresto graceful di FastAPI e pulizia."""
        logger.info("Shutdown FastAPI server...")
        if self._server:
            try:
                self._server.should_exit = True
                if self._api_server_thread and self._api_server_thread.is_alive():
                    self._api_server_thread.join(timeout=2.0)
            except Exception as e:
                logger.warning(f"Errore durante shutdown: {e}")


class WebViewAPI:
    """API esposta a PyWebView JavaScript per operazioni di sistema."""

    def __init__(self, db_manager):
        self.db_manager = db_manager
        logger.info("WebViewAPI inizializzata")

    def get_app_version(self) -> str:
        """Restituisce la versione dell'app."""
        from config import APP_VERSION
        return APP_VERSION

    def get_app_info(self) -> dict:
        """Restituisce informazioni generali sull'app."""
        from config import APP_VERSION
        return {
            "name": "Foliarium",
            "version": APP_VERSION,
            "ui": "PyWebView",
            "timestamp": time.time(),
        }

    def log(self, level: str, message: str):
        """Log dal frontend JavaScript."""
        log_func = getattr(logger, level.lower(), logger.info)
        log_func(f"[JS] {message}")

    def exit_app(self):
        """Esce dall'applicazione."""
        logger.info("Richiesta exit da frontend")
        import webview
        webview.api.exit()


def launch_webview_app(db_manager, use_dev_mode: bool = False) -> bool:
    """
    Entry point pubblico: lancia la modalità PyWebView.

    Args:
        db_manager: CatastoDBManager connesso
        use_dev_mode: Abilita Vite dev server (no build necessario)

    Returns:
        True se lancio riuscito, False altrimenti.
    """
    launcher = WebViewLauncher(db_manager, use_dev_mode)
    return launcher.launch()
