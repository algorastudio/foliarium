"""
tests/unit/test_startup.py
==========================
Unit test del modulo foliarium.ui.startup.

Le tre funzioni (splash, EULA, licenza) sono orchestratori con side
effect su QSettings + sys.exit. I test mockano splash/welcome/license
manager e verificano il flusso di controllo.
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
    return logging.getLogger("test_startup")


@pytest.fixture
def isolated_settings(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    QSettings.setDefaultFormat(QSettings.Format.IniFormat)
    QSettings.setPath(
        QSettings.Format.IniFormat,
        QSettings.Scope.UserScope,
        str(tmp_path),
    )
    return QSettings("FoliariumTest", "StartupTest")


class TestShowSplashScreen:

    def test_skipped_in_test_env(self, app):
        from foliarium.ui import startup
        with patch.object(startup, "IS_TEST_ENV", True), \
             patch("foliarium.ui.splash.FoliariumSplashScreen") as mock_splash:
            startup.show_splash_screen(app)
        mock_splash.assert_not_called()

    def test_shows_and_closes_splash_when_not_in_test_env(self, app):
        from foliarium.ui import startup

        mock_splash_inst = MagicMock()
        fake_splash_mod = MagicMock(FoliariumSplashScreen=MagicMock(return_value=mock_splash_inst))

        with patch.object(startup, "IS_TEST_ENV", False), \
             patch.dict(sys.modules, {"foliarium.ui.splash": fake_splash_mod}), \
             patch.object(startup.time, "sleep") as mock_sleep:
            startup.show_splash_screen(app, duration_seconds=0.1)
        mock_splash_inst.show.assert_called_once()
        mock_splash_inst.close.assert_called_once()
        mock_sleep.assert_called_once_with(0.1)


class TestEnsureEulaAccepted:

    def test_returns_immediately_when_version_matches(
        self, app, isolated_settings, logger,
    ):
        from foliarium.ui import startup
        from config import EULA_VERSION, SETTINGS_EULA_ACCEPTED

        s = QSettings()
        s.setValue(SETTINGS_EULA_ACCEPTED, EULA_VERSION)
        s.sync()

        # Se aprisse WelcomeScreen, il test fallirebbe per import error o
        # per side effect; lo mockiamo per sicurezza
        fake_gw = MagicMock(WelcomeScreen=MagicMock())
        with patch.dict(sys.modules, {"gui_widgets": fake_gw}):
            startup.ensure_eula_accepted(logger)
        fake_gw.WelcomeScreen.assert_not_called()

    def test_opens_welcome_when_version_missing(
        self, app, isolated_settings, logger,
    ):
        from foliarium.ui import startup
        from config import EULA_VERSION, SETTINGS_EULA_ACCEPTED

        mock_welcome_inst = MagicMock()
        mock_welcome_inst.exec.return_value = QDialog.DialogCode.Accepted
        fake_gw = MagicMock(WelcomeScreen=MagicMock(return_value=mock_welcome_inst))

        with patch.dict(sys.modules, {"gui_widgets": fake_gw}):
            startup.ensure_eula_accepted(logger)

        # Dopo l'accettazione, la versione viene scritta in QSettings
        s = QSettings()
        assert s.value(SETTINGS_EULA_ACCEPTED, "", type=str) == EULA_VERSION

    def test_rejected_exits_zero(
        self, app, isolated_settings, logger,
    ):
        from foliarium.ui import startup

        mock_welcome_inst = MagicMock()
        mock_welcome_inst.exec.return_value = QDialog.DialogCode.Rejected
        fake_gw = MagicMock(WelcomeScreen=MagicMock(return_value=mock_welcome_inst))

        with patch.dict(sys.modules, {"gui_widgets": fake_gw}), \
             pytest.raises(SystemExit) as ei:
            startup.ensure_eula_accepted(logger)
        assert ei.value.code == 0

    def test_version_mismatch_reopens_welcome(
        self, app, isolated_settings, logger,
    ):
        """Versione precedente accettata != EULA_VERSION corrente → riapre."""
        from foliarium.ui import startup
        from config import SETTINGS_EULA_ACCEPTED

        s = QSettings()
        s.setValue(SETTINGS_EULA_ACCEPTED, "0.0.0-old")
        s.sync()

        mock_welcome_inst = MagicMock()
        mock_welcome_inst.exec.return_value = QDialog.DialogCode.Accepted
        fake_gw = MagicMock(WelcomeScreen=MagicMock(return_value=mock_welcome_inst))

        with patch.dict(sys.modules, {"gui_widgets": fake_gw}):
            startup.ensure_eula_accepted(logger)
        fake_gw.WelcomeScreen.assert_called_once()


class TestValidateLicenseAndAcquireSeat:

    def _build_fake_license_module(self, *, valid, allowed, seats=1, max_seats=2,
                                   error_message=None, licensed_to="Test",
                                   license_type="standard"):
        mock_info = MagicMock()
        mock_info.is_valid = valid
        mock_info.error_message = error_message
        mock_info.licensed_to = licensed_to
        mock_info.license_type = license_type

        mock_mgr = MagicMock()
        mock_mgr.validate.return_value = mock_info
        mock_mgr.acquire_seat.return_value = (allowed, seats, max_seats)

        fake_mod = MagicMock(LicenseManager=MagicMock(return_value=mock_mgr))
        return fake_mod, mock_mgr

    def test_invalid_license_exits_one(self, logger):
        from foliarium.ui import startup
        fake_mod, _ = self._build_fake_license_module(
            valid=False, allowed=False, error_message="firma errata",
        )
        with patch.dict(sys.modules,
                        {"foliarium.core.services.license": fake_mod}), \
             patch.object(startup, "QMessageBox"), \
             pytest.raises(SystemExit) as ei:
            startup.validate_license_and_acquire_seat(logger)
        assert ei.value.code == 1

    def test_seats_exhausted_exits_one(self, logger):
        from foliarium.ui import startup
        fake_mod, _ = self._build_fake_license_module(
            valid=True, allowed=False, seats=3, max_seats=2,
        )
        with patch.dict(sys.modules,
                        {"foliarium.core.services.license": fake_mod}), \
             patch.object(startup, "QMessageBox"), \
             pytest.raises(SystemExit) as ei:
            startup.validate_license_and_acquire_seat(logger)
        assert ei.value.code == 1

    def test_happy_path_returns_license_manager(self, logger):
        from foliarium.ui import startup
        fake_mod, mock_mgr = self._build_fake_license_module(
            valid=True, allowed=True, seats=1, max_seats=2,
        )
        with patch.dict(sys.modules,
                        {"foliarium.core.services.license": fake_mod}):
            result = startup.validate_license_and_acquire_seat(logger)
        assert result is mock_mgr
        mock_mgr.validate.assert_called_once()
        mock_mgr.acquire_seat.assert_called_once()
