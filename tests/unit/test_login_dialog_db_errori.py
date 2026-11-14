"""
tests/unit/test_login_dialog_db_errori.py
=========================================
Il dialogo di login della GUI non deve scambiare un database irraggiungibile
per una password sbagliata.

``get_user_credentials`` ora solleva ``DBMError`` quando la query fallisce
invece di restituire ``None``. ``LoginDialog.handle_login`` deve mostrare
l'errore con ``show_user_error`` (messaggio in italiano, dettagli tecnici a
scomparsa) e non «Username o Password errati».
"""
from __future__ import annotations

import os
import sys
from unittest.mock import MagicMock, patch

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:
    from PyQt6.QtWidgets import QApplication
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
def login_mod(app):
    import foliarium.ui.dialogs.admin.login as mod
    return mod


def _dialogo(login_mod, db_manager, username="admin", password="segreta"):
    dlg = login_mod.LoginDialog(db_manager, "127.0.0.1")
    dlg.username_edit.setText(username)
    dlg.password_edit.setText(password)
    return dlg


def _messaggi_warning(qmb_mock):
    return [c.args[2] for c in qmb_mock.warning.call_args_list if len(c.args) >= 3]


class TestLoginDialogErroreDatabase:

    def test_errore_db_mostra_errore_comprensibile_non_password_errata(self, login_mod):
        from catasto_exceptions import DBMError

        errore = DBMError("Database non raggiungibile")
        db = MagicMock()
        db.get_user_credentials = MagicMock(side_effect=errore)
        dlg = _dialogo(login_mod, db)

        with patch.object(login_mod, "QMessageBox") as qmb, \
                patch.object(login_mod, "show_user_error") as sue:
            dlg.handle_login()

        sue.assert_called_once()
        assert sue.call_args.args[0] is dlg
        assert sue.call_args.args[2] is errore
        assert not any("errati" in m for m in _messaggi_warning(qmb))
        assert dlg.logged_in_user_id is None
        db.register_access.assert_not_called()

    def test_utente_inesistente_resta_username_o_password_errati(self, login_mod):
        db = MagicMock()
        db.get_user_credentials = MagicMock(return_value=None)
        dlg = _dialogo(login_mod, db)

        with patch.object(login_mod, "QMessageBox") as qmb, \
                patch.object(login_mod, "show_user_error") as sue:
            dlg.handle_login()

        sue.assert_not_called()
        assert any("Username o Password errati" in m for m in _messaggi_warning(qmb))
        assert dlg.logged_in_user_id is None
