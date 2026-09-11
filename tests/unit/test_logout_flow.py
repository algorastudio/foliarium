"""
tests/unit/test_logout_flow.py
==============================
Unit test del flusso di logout di CatastoMainWindow.

Il logout non deve chiudere l'applicazione: su una postazione condivisa
il cambio operatore deve costare un login, non un riavvio. Questi test
bloccano quel comportamento e le condizioni che lo rendono ripetibile
(niente scorciatoie o timer duplicati al secondo accesso).
"""

from __future__ import annotations

import os
import sys
from unittest.mock import MagicMock, patch

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:
    from PyQt6.QtWidgets import QApplication, QDialog
    _QT_OK = True
except ImportError:
    _QT_OK = False


pytestmark = [
    pytest.mark.unit,
    pytest.mark.gui,
    pytest.mark.skipif(not _QT_OK, reason="PyQt6 non disponibile"),
]


@pytest.fixture(scope="module")
def app():
    inst = QApplication.instance()
    if inst is None:
        inst = QApplication(sys.argv)
    yield inst


@pytest.fixture
def window(app):
    """MainWindow con una sessione utente fittizia gia' attiva."""
    import gui_main
    win = gui_main.CatastoMainWindow("127.0.0.1")
    win.db_manager = MagicMock()
    win.db_manager.logout_user.return_value = True
    win.pool_initialized_successful = True
    win.logged_in_user_id = 7
    win.logged_in_user_info = {"username": "mrossi", "ruolo": "archivista"}
    win.current_session_id = "abcdef12-0000-0000-0000-000000000000"
    yield win
    # La finestra installa un filtro eventi sull'intera QApplication e lo
    # rimuove solo in closeEvent: senza questo resterebbe agganciato a un
    # oggetto distrutto per tutto il resto della sessione di test.
    QApplication.instance().removeEventFilter(win)
    win.deleteLater()


class TestHandleLogout:

    def test_non_chiude_l_applicazione(self, window):
        with patch.object(type(window), "close") as close, \
             patch.object(type(window), "_login_another_user") as riapri:
            window.handle_logout()

        close.assert_not_called()
        riapri.assert_called_once()

    def test_registra_il_logout_sul_database(self, window):
        with patch.object(type(window), "_login_another_user"):
            window.handle_logout()

        window.db_manager.logout_user.assert_called_once_with(
            7, "abcdef12-0000-0000-0000-000000000000", "127.0.0.1")

    def test_azzera_la_sessione_utente(self, window):
        with patch.object(type(window), "_login_another_user"):
            window.handle_logout()

        assert window.logged_in_user_id is None
        assert window.logged_in_user_info is None
        assert window.current_session_id is None
        assert window.session.is_authenticated is False
        assert window.stack.count() == 0
        assert window._page_index == {}
        assert not window.sidebar.isVisible()

    def test_la_connessione_al_db_resta_aperta_per_il_prossimo_utente(self, window):
        """Il pool non va chiuso: serve al login successivo."""
        with patch.object(type(window), "_login_another_user"):
            window.handle_logout()

        window.db_manager.close_pool.assert_not_called()
        assert window.db_manager is not None

    def test_senza_sessione_attiva_non_fa_nulla(self, window):
        window.logged_in_user_id = None
        with patch.object(type(window), "_login_another_user") as riapri:
            window.handle_logout()

        riapri.assert_not_called()
        window.db_manager.logout_user.assert_not_called()


class TestLoginAnotherUser:

    def test_login_riuscito_riconfigura_la_finestra(self, window):
        import gui_main
        dialogo = MagicMock()
        dialogo.exec.return_value = QDialog.DialogCode.Accepted
        dialogo.logged_in_user_id = 9
        dialogo.logged_in_user_info = {"username": "gverdi", "ruolo": "admin"}
        dialogo.current_session_id_from_dialog = "sessione-nuova"

        with patch.object(gui_main, "LoginDialog", return_value=dialogo), \
             patch.object(type(window), "perform_initial_setup") as setup, \
             patch.object(type(window), "close") as close:
            window._login_another_user()

        close.assert_not_called()
        setup.assert_called_once_with(
            window.db_manager, 9,
            {"username": "gverdi", "ruolo": "admin"}, "sessione-nuova")

    def test_login_annullato_chiude_l_applicazione(self, window):
        import gui_main
        dialogo = MagicMock()
        dialogo.exec.return_value = QDialog.DialogCode.Rejected

        with patch.object(gui_main, "LoginDialog", return_value=dialogo), \
             patch.object(type(window), "perform_initial_setup") as setup, \
             patch.object(type(window), "close") as close:
            window._login_another_user()

        setup.assert_not_called()
        close.assert_called_once()


class TestStopPageWorkers:

    def test_ferma_solo_i_worker_in_esecuzione(self, window):
        pagina = MagicMock()
        pagina._loader.isRunning.return_value = True
        pagina._dash_loader.isRunning.return_value = False

        window._stop_page_workers(pagina)

        pagina._loader.quit.assert_called_once()
        pagina._dash_loader.quit.assert_not_called()
