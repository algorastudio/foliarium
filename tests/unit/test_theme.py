"""
tests/unit/test_theme.py
========================
Unit test del modulo foliarium.ui.theme.

Le funzioni di tema sono pure (ricevono QApplication esplicitamente) e
possono essere testate in isolamento, senza QMainWindow.

Richiedono una QApplication offscreen — la fixture di sessione la crea
una sola volta e la riusa fra tutti i test.
"""

from __future__ import annotations

import os
import sys
from unittest.mock import patch

import pytest


# QT_QPA_PLATFORM=offscreen abilita Qt6 in CI headless
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:
    from PyQt6.QtCore import QSettings, Qt
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
def isolated_settings(tmp_path, monkeypatch):
    """Isola QSettings su un file temporaneo per non sporcare quello reale."""
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    QSettings.setDefaultFormat(QSettings.Format.IniFormat)
    QSettings.setPath(
        QSettings.Format.IniFormat,
        QSettings.Scope.UserScope,
        str(tmp_path),
    )
    yield QSettings("FoliariumTest", "ThemeTest")


class TestResetAppStyle:

    def test_reset_app_style_no_crash(self, app):
        """reset_app_style applica Fusion senza sollevare eccezioni."""
        from foliarium.ui import theme
        theme.reset_app_style(app)
        # Non si puo' asserire .objectName() di setStyle in modo portabile,
        # ma se Fusion non e' applicabile setStyle ritorna silenziosamente.
        assert app.style() is not None

    def test_reset_app_style_uses_global_app_when_omitted(self, app):
        from foliarium.ui import theme
        theme.reset_app_style()
        assert QApplication.instance() is app


class TestApplyStylesheet:

    def test_apply_stylesheet_unknown_file_returns_false(self, app):
        from foliarium.ui import theme
        result = theme.apply_stylesheet("file_che_non_esiste_xyz.qss", app)
        assert result is False

    def test_apply_stylesheet_real_file_returns_true(self, app):
        """Usa un file QSS effettivamente presente in styles/."""
        from foliarium.ui import theme
        from app_paths import get_available_styles

        available = get_available_styles()
        if not available:
            pytest.skip("Nessuno stylesheet QSS presente nel progetto")

        chosen = available[0]
        result = theme.apply_stylesheet(chosen, app)
        assert result is True
        # Side effect: lo stylesheet e' stato applicato
        assert app.styleSheet() != ""


class TestApplyAutoTheme:

    def test_apply_auto_theme_returns_a_known_theme_file(self, app):
        from foliarium.ui import theme
        from config import AUTO_THEME_DARK, AUTO_THEME_LIGHT

        result = theme.apply_auto_theme(app)
        # Puo' essere None se il file non esiste in styles/, ma se ritorna
        # un valore deve essere uno dei due predefiniti.
        assert result in (None, AUTO_THEME_DARK, AUTO_THEME_LIGHT)


class TestIsWin11StyleAvailable:

    def test_returns_bool(self):
        from foliarium.ui import theme
        result = theme.is_win11_style_available()
        assert isinstance(result, bool)

    def test_consistent_with_qstylefactory(self):
        from PyQt6.QtWidgets import QStyleFactory
        from foliarium.ui import theme
        assert theme.is_win11_style_available() == (
            "windows11" in QStyleFactory.keys()
        )


class TestApplyInitialThemeFromSettings:

    def test_returns_none_and_does_not_crash_with_default_settings(
        self, app, isolated_settings,
    ):
        """Con QSettings vuote (default) deve applicare il tema di default
        senza sollevare eccezioni."""
        from foliarium.ui import theme
        # Non deve sollevare
        theme.apply_initial_theme_from_settings(app)

    def test_respects_win11_setting_when_available(
        self, app, isolated_settings, monkeypatch,
    ):
        """Se Win11 e' attivo in QSettings e disponibile, viene applicato."""
        from foliarium.ui import theme
        from config import SETTINGS_UI_WIN11_STYLE

        if not theme.is_win11_style_available():
            pytest.skip("Stile Windows11 non disponibile in questa build di Qt")

        s = QSettings()
        s.setValue(SETTINGS_UI_WIN11_STYLE, True)
        s.sync()

        # Mock di setStyle per verificare la chiamata senza dipendere
        # dall'effettiva applicazione del tema in ambiente offscreen
        with patch.object(app, "setStyle") as mock_set_style:
            theme.apply_initial_theme_from_settings(app)
            mock_set_style.assert_called_with("windows11")

    def test_respects_auto_theme_setting(
        self, app, isolated_settings,
    ):
        """Con SETTINGS_UI_AUTO_THEME=True viene chiamato apply_auto_theme."""
        from foliarium.ui import theme
        from config import SETTINGS_UI_AUTO_THEME, SETTINGS_UI_WIN11_STYLE

        s = QSettings()
        s.setValue(SETTINGS_UI_WIN11_STYLE, False)
        s.setValue(SETTINGS_UI_AUTO_THEME, True)
        s.sync()

        with patch.object(theme, "apply_auto_theme") as mock_auto:
            theme.apply_initial_theme_from_settings(app)
            mock_auto.assert_called_once()
