"""
api/server_thread.py — QThread che avvia uvicorn in background.
Usato da gui_main.py per integrare il server API nella app PyQt.
"""
import sys
import threading
import logging
from pathlib import Path

from PyQt6.QtCore import QThread, pyqtSignal

logger = logging.getLogger("FoliariumAPI.Thread")

# Porta e app globali, accessibili dopo l'avvio
_port: int = 0
_server = None


class APIServerThread(QThread):
    """Avvia uvicorn in un daemon thread Python (non nel QThread stesso)."""

    started_ok = pyqtSignal(int)   # porta
    start_error = pyqtSignal(str)  # messaggio errore

    def __init__(self, db_manager, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self._port = 0

    def run(self):
        global _port, _server
        try:
            import uvicorn
            from api.main import create_app, find_free_port

            self._port = find_free_port(8765)
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
