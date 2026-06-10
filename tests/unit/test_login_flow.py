"""
tests/unit/test_login_flow.py
=============================
Unit test del modulo foliarium.ui.login_flow.

Le funzioni sono orchestrazioni: leggono QSettings, aprono dialog,
costruiscono CatastoDBManager. I test mockano i collaboratori esterni
(CatastoDBManager, DBConfigDialog, LoginDialog, keyring) e verificano
solo il flusso di controllo (cancel→sys.exit, retry-on-error, ecc.).
"""

from __future__ import annotations

import logging
import os
import sys
from unittest.mock import MagicMock, patch

import pytest


os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:
    from PyQt6.QtCore import QSettings
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
def logger():
    return logging.getLogger("test_login_flow")


@pytest.fixture
def isolated_settings(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    QSettings.setDefaultFormat(QSettings.Format.IniFormat)
    QSettings.setPath(
        QSettings.Format.IniFormat,
        QSettings.Scope.UserScope,
        str(tmp_path),
    )
    return QSettings("FoliariumTest", "LoginFlowTest")


def _populate_settings(settings, *, password="pwd", dbname="db", user="u"):
    from config import (
        SETTINGS_DB_HOST,
        SETTINGS_DB_NAME,
        SETTINGS_DB_PASSWORD,
        SETTINGS_DB_PORT,
        SETTINGS_DB_USER,
    )
    settings.setValue(SETTINGS_DB_HOST, "localhost")
    settings.setValue(SETTINGS_DB_PORT, 5432)
    settings.setValue(SETTINGS_DB_NAME, dbname)
    settings.setValue(SETTINGS_DB_USER, user)
    settings.setValue(SETTINGS_DB_PASSWORD, password)
    settings.sync()


class TestTryAutoconnectDb:

    def test_returns_none_when_settings_incomplete(self, isolated_settings, logger):
        from foliarium.ui import login_flow
        # Settings vuote → password mancante → None senza tentare connessione
        with patch.object(login_flow, "CatastoDBManager") as mock_db, \
             patch.object(login_flow, "_get_password_from_keyring_safe", return_value=None):
            result = login_flow.try_autoconnect_db(isolated_settings, logger)
        assert result is None
        mock_db.assert_not_called()

    def test_returns_db_on_success(self, isolated_settings, logger):
        from foliarium.ui import login_flow
        _populate_settings(isolated_settings)

        mock_instance = MagicMock()
        mock_instance.initialize_main_pool.return_value = True
        with patch.object(login_flow, "CatastoDBManager", return_value=mock_instance) as mock_db:
            result = login_flow.try_autoconnect_db(isolated_settings, logger)
        assert result is mock_instance
        mock_db.assert_called_once()

    def test_returns_none_when_pool_init_fails(self, isolated_settings, logger):
        from foliarium.ui import login_flow
        _populate_settings(isolated_settings)

        mock_instance = MagicMock()
        mock_instance.initialize_main_pool.return_value = False
        with patch.object(login_flow, "CatastoDBManager", return_value=mock_instance):
            result = login_flow.try_autoconnect_db(isolated_settings, logger)
        assert result is None

    def test_returns_none_when_constructor_raises(self, isolated_settings, logger):
        from foliarium.ui import login_flow
        _populate_settings(isolated_settings)

        with patch.object(login_flow, "CatastoDBManager", side_effect=RuntimeError("boom")):
            result = login_flow.try_autoconnect_db(isolated_settings, logger)
        assert result is None

    def test_falls_back_to_keyring_when_password_not_in_settings(
        self, isolated_settings, logger,
    ):
        from foliarium.ui import login_flow
        _populate_settings(isolated_settings, password="")  # password vuota in QSettings

        mock_instance = MagicMock()
        mock_instance.initialize_main_pool.return_value = True
        with patch.object(login_flow, "CatastoDBManager", return_value=mock_instance) as mock_db, \
             patch.object(login_flow, "_get_password_from_keyring_safe",
                          return_value="from-keyring") as mock_kr:
            result = login_flow.try_autoconnect_db(isolated_settings, logger)
        assert result is mock_instance
        mock_kr.assert_called_once()
        # La password passata a CatastoDBManager deve provenire dal keyring
        _, kwargs = mock_db.call_args
        assert kwargs["password"] == "from-keyring"


class TestGetPasswordFromKeyringSafe:

    def test_returns_none_when_app_utils_raises(self):
        from foliarium.ui import login_flow
        with patch("app_utils.get_password_from_keyring", side_effect=RuntimeError("x")):
            result = login_flow._get_password_from_keyring_safe("h", "u")
        assert result is None

    def test_returns_value_from_keyring(self):
        from foliarium.ui import login_flow
        with patch("app_utils.get_password_from_keyring", return_value="secret"):
            result = login_flow._get_password_from_keyring_safe("h", "u")
        assert result == "secret"


class TestConnectDbWithDialog:

    def test_user_cancels_calls_sys_exit_and_releases_seat(self, logger):
        from foliarium.ui import login_flow

        mock_dialog_cls = MagicMock()
        mock_dialog_inst = MagicMock()
        mock_dialog_inst.exec.return_value = QDialog.DialogCode.Rejected
        mock_dialog_cls.return_value = mock_dialog_inst

        mock_license = MagicMock()

        with patch.dict(sys.modules, {"dialogs": MagicMock(DBConfigDialog=mock_dialog_cls)}), \
             patch.object(login_flow, "QMessageBox"), \
             pytest.raises(SystemExit) as ei:
            login_flow.connect_db_with_dialog(logger, license_mgr=mock_license)
        assert ei.value.code == 0
        mock_license.release_seat.assert_called_once()

    def test_success_returns_db_after_dialog(self, logger):
        from foliarium.ui import login_flow

        mock_dialog_cls = MagicMock()
        mock_dialog_inst = MagicMock()
        mock_dialog_inst.exec.return_value = QDialog.DialogCode.Accepted
        mock_dialog_inst.get_config_values.return_value = {
            "host": "h", "port": 5432, "dbname": "db", "user": "u", "password": "p",
        }
        mock_dialog_cls.return_value = mock_dialog_inst

        mock_db_inst = MagicMock()
        mock_db_inst.initialize_main_pool.return_value = True

        with patch.dict(sys.modules, {"dialogs": MagicMock(DBConfigDialog=mock_dialog_cls)}), \
             patch.object(login_flow, "QMessageBox"), \
             patch.object(login_flow, "CatastoDBManager", return_value=mock_db_inst):
            result = login_flow.connect_db_with_dialog(logger)
        assert result is mock_db_inst

    def test_constructor_error_retries_loop(self, logger):
        """Se CatastoDBManager() solleva, il loop deve riprovare; al 2° giro
        l'utente annulla e si esce."""
        from foliarium.ui import login_flow

        accepted = QDialog.DialogCode.Accepted
        rejected = QDialog.DialogCode.Rejected

        mock_dialog_cls = MagicMock()
        first = MagicMock(); first.exec.return_value = accepted
        first.get_config_values.return_value = {
            "host": "h", "port": 5432, "dbname": "db", "user": "u", "password": "p",
        }
        second = MagicMock(); second.exec.return_value = rejected
        mock_dialog_cls.side_effect = [first, second]

        with patch.dict(sys.modules, {"dialogs": MagicMock(DBConfigDialog=mock_dialog_cls)}), \
             patch.object(login_flow, "QMessageBox"), \
             patch.object(login_flow, "CatastoDBManager", side_effect=RuntimeError("boom")), \
             pytest.raises(SystemExit):
            login_flow.connect_db_with_dialog(logger)
        # Due iterazioni del loop
        assert mock_dialog_cls.call_count == 2


class TestEnsureDbConnection:

    def test_uses_autoconnect_when_available(self, isolated_settings, logger):
        from foliarium.ui import login_flow

        mock_db = MagicMock(); mock_db.pool = MagicMock()
        main_window = MagicMock()

        with patch.object(login_flow, "try_autoconnect_db", return_value=mock_db) as mock_auto, \
             patch.object(login_flow, "connect_db_with_dialog") as mock_manual:
            result = login_flow.ensure_db_connection(main_window, isolated_settings, logger)
        assert result is mock_db
        assert main_window.db_manager is mock_db
        assert main_window.pool_initialized_successful is True
        mock_auto.assert_called_once()
        mock_manual.assert_not_called()

    def test_falls_back_to_dialog_when_autoconnect_fails(self, isolated_settings, logger):
        from foliarium.ui import login_flow

        mock_db = MagicMock()
        main_window = MagicMock()

        with patch.object(login_flow, "try_autoconnect_db", return_value=None), \
             patch.object(login_flow, "connect_db_with_dialog",
                          return_value=mock_db) as mock_manual:
            result = login_flow.ensure_db_connection(main_window, isolated_settings, logger)
        assert result is mock_db
        mock_manual.assert_called_once()

    def test_falls_back_when_pool_is_none(self, isolated_settings, logger):
        """try_autoconnect_db ritorna un manager ma .pool=None → fallback."""
        from foliarium.ui import login_flow

        broken = MagicMock(); broken.pool = None
        good = MagicMock()
        main_window = MagicMock()

        with patch.object(login_flow, "try_autoconnect_db", return_value=broken), \
             patch.object(login_flow, "connect_db_with_dialog",
                          return_value=good) as mock_manual:
            result = login_flow.ensure_db_connection(main_window, isolated_settings, logger)
        assert result is good
        mock_manual.assert_called_once()


class TestPerformUserLogin:

    def test_user_cancels_calls_sys_exit(self, logger):
        from foliarium.ui import login_flow

        mock_dialog_cls = MagicMock()
        mock_dialog_inst = MagicMock()
        mock_dialog_inst.exec.return_value = QDialog.DialogCode.Rejected
        mock_dialog_cls.return_value = mock_dialog_inst

        # Modulo finto per foliarium.ui.dialogs.admin
        fake_admin = MagicMock(LoginDialog=mock_dialog_cls)
        mock_license = MagicMock()

        with patch.dict(sys.modules, {"foliarium.ui.dialogs.admin": fake_admin}), \
             pytest.raises(SystemExit) as ei:
            login_flow.perform_user_login(
                db_manager=MagicMock(),
                client_ip="127.0.0.1",
                parent=None,
                logger=logger,
                license_mgr=mock_license,
            )
        assert ei.value.code == 0
        mock_license.release_seat.assert_called_once()

    def test_success_returns_tuple(self, logger):
        from foliarium.ui import login_flow

        mock_dialog_inst = MagicMock()
        mock_dialog_inst.exec.return_value = QDialog.DialogCode.Accepted
        mock_dialog_inst.logged_in_user_id = 42
        mock_dialog_inst.logged_in_user_info = {"username": "alice"}
        mock_dialog_inst.current_session_id_from_dialog = 7
        fake_admin = MagicMock(LoginDialog=MagicMock(return_value=mock_dialog_inst))

        with patch.dict(sys.modules, {"foliarium.ui.dialogs.admin": fake_admin}):
            uid, info, sid = login_flow.perform_user_login(
                db_manager=MagicMock(),
                client_ip="127.0.0.1",
                parent=None,
                logger=logger,
            )
        assert uid == 42
        assert info == {"username": "alice"}
        assert sid == 7
