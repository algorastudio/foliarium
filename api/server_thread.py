"""
api/server_thread.py — QThread che avvia uvicorn in background.
Usato da gui_main.py per integrare il server API nella app PyQt.
"""
import logging

from PyQt6.QtCore import QThread, pyqtSignal

logger = logging.getLogger("FoliariumAPI.Thread")

# Porta e app globali, accessibili dopo l'avvio
_port: int = 0
_server = None


class APIServerThread(QThread):
    """Avvia uvicorn in un daemon thread Python (non nel QThread stesso).

    La porta viene risolta tramite ``api.main.resolve_api_port`` che onora
    ``FOLIARIUM_API_PORT`` (env) o la sezione ``[api]`` di config.ini. Se la
    porta esplicitamente fissata è occupata, viene emesso
    ``pinned_port_busy(port)`` invece di scegliere silenziosamente
    un'altra porta — così la configurazione esterna (es. Claude Desktop)
    non si rompe a ogni riavvio.
    """

    started_ok = pyqtSignal(int)         # porta
    start_error = pyqtSignal(str)        # messaggio errore generico
    pinned_port_busy = pyqtSignal(int)   # porta fissata ma occupata

    def __init__(self, db_manager, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self._port = 0

    def run(self):
        global _port, _server
        try:
            import uvicorn
            from api.main import create_app, resolve_api_port, PinnedPortBusyError

            try:
                self._port = resolve_api_port(default_start=8765)
            except PinnedPortBusyError as e:
                logger.warning("Porta API fissata occupata: %s", e)
                self.pinned_port_busy.emit(e.port)
                return

            _port = self._port

            app = create_app(self.db_manager)

            config = uvicorn.Config(
                app,
                host="127.0.0.1",
                port=self._port,
                log_level="warning",
                loop="asyncio",
            )
            _server = uvicorn.Server(config)

            self.started_ok.emit(self._port)
            _server.run()

        except Exception as e:
            logger.exception("Errore avvio server API")
            self.start_error.emit(str(e))

    def stop(self):
        global _server
        if _server is not None:
            _server.should_exit = True


def get_running_port() -> int:
    """Restituisce la porta correntemente in ascolto (0 se l'API non è attiva).

    Utile a widget esterni (es. indicatore in top bar) per scoprire dove
    sta girando il server senza tenersi un riferimento al thread.
    """
    return _port
