"""
foliarium/ui/theme.py — Funzioni pure di gestione tema grafico.

Estratto da gui_main.py (Sprint 3.5 refactor — six-hats).

Tre responsabilita' isolate:
    1. Applicazione di un singolo stylesheet QSS (apply_stylesheet)
    2. Tema automatico dark/light basato sull'OS (apply_auto_theme)
    3. Bootstrap del tema al primo avvio leggendo QSettings
       (apply_initial_theme_from_settings)

Le funzioni sono pure: ricevono QApplication esplicitamente, non accedono
a self. La logica di stato del menu (toggle delle QAction) e di
persistenza in QSettings resta nel chiamante perche' e' genuinamente
accoppiata alla view della MainWindow.
"""

from __future__ import annotations

import logging
from typing import Optional

from PyQt6.QtCore import QSettings, Qt
from PyQt6.QtGui import QGuiApplication
from PyQt6.QtWidgets import QApplication, QStyleFactory

from app_paths import load_stylesheet
from config import (
    AUTO_THEME_DARK,
    AUTO_THEME_LIGHT,
    SETTINGS_UI_AUTO_THEME,
    SETTINGS_UI_CURRENT_STYLE,
    SETTINGS_UI_WIN11_STYLE,
)

_log = logging.getLogger("CatastoGUI.theme")


def reset_app_style(app: Optional[QApplication] = None) -> None:
    """Ripristina lo stile Qt 'Fusion' (necessario prima di applicare un QSS)."""
    app = app or QApplication.instance()
    if app is not None:
        app.setStyle(QStyleFactory.create("Fusion"))


def apply_stylesheet(filename: str, app: Optional[QApplication] = None,
                     logger: Optional[logging.Logger] = None) -> bool:
    """Carica e applica il file QSS indicato. Ritorna True se OK."""
    log = logger or _log
    app = app or QApplication.instance()
    if app is None:
        log.warning("apply_stylesheet: QApplication non disponibile")
        return False

    stylesheet = load_stylesheet(filename)
    if not stylesheet:
        log.warning("apply_stylesheet: impossibile caricare '%s'", filename)
        return False

    reset_app_style(app)
    app.setStyleSheet(stylesheet)
    log.info("Tema '%s' applicato.", filename)
    return True


def apply_auto_theme(app: Optional[QApplication] = None,
                     logger: Optional[logging.Logger] = None) -> Optional[str]:
    """
    Applica il tema chiaro/scuro in base allo schema colori del sistema.
    Ritorna il nome del file di stile applicato, o None in caso di errore.
    """
    log = logger or _log
    app = app or QApplication.instance()
    if app is None:
        log.warning("apply_auto_theme: QApplication non disponibile")
        return None

    scheme = QGuiApplication.styleHints().colorScheme()
    theme_file = AUTO_THEME_DARK if scheme == Qt.ColorScheme.Dark else AUTO_THEME_LIGHT
    stylesheet = load_stylesheet(theme_file)
    if not stylesheet:
        log.warning("apply_auto_theme: impossibile caricare '%s'", theme_file)
        return None

    reset_app_style(app)
    app.setStyleSheet(stylesheet)
    log.info("Tema automatico applicato: %s (schema OS: %s)", theme_file, scheme.name)
    return theme_file


def is_win11_style_available() -> bool:
    """True se lo stile nativo Windows 11 e' disponibile in questa build di Qt."""
    return "windows11" in QStyleFactory.keys()


def apply_win11_style(app: Optional[QApplication] = None) -> bool:
    """Attiva lo stile nativo Windows 11 (azzera qualunque QSS personalizzato)."""
    app = app or QApplication.instance()
    if app is None or not is_win11_style_available():
        return False
    app.setStyle("windows11")
    app.setStyleSheet("")
    return True


def apply_initial_theme_from_settings(
    app: Optional[QApplication] = None,
    logger: Optional[logging.Logger] = None,
) -> None:
    """
    Bootstrap del tema al primo avvio leggendo QSettings.

    Ordine di precedenza: Windows11 > Auto (segue OS) > tema QSS salvato
    (default: AUTO_THEME_LIGHT).
    """
    log = logger or _log
    app = app or QApplication.instance()
    if app is None:
        log.warning("apply_initial_theme_from_settings: QApplication non disponibile")
        return

    settings = QSettings()
    if settings.value(SETTINGS_UI_WIN11_STYLE, False, type=bool) \
            and is_win11_style_available():
        app.setStyle("windows11")
        return

    if settings.value(SETTINGS_UI_AUTO_THEME, False, type=bool):
        apply_auto_theme(app, logger=log)
        return

    current_style_file = settings.value(
        SETTINGS_UI_CURRENT_STYLE, AUTO_THEME_LIGHT, type=str,
    )
    stylesheet = load_stylesheet(current_style_file)
    if stylesheet:
        # Forziamo lo stile Fusion come baseline: garantisce palette e
        # rendering identici su qualunque PC, indipendentemente dallo
        # stile Qt di default del sistema operativo (windowsvista,
        # windows11, fusion, gtk, ecc.). Senza questo, i widget non
        # esplicitamente coperti dal QSS ereditavano colori dalla
        # palette dello stile nativo, con risultati illeggibili su PC
        # con schema di sistema diverso da quello dello sviluppatore.
        reset_app_style(app)
        app.setStyleSheet(stylesheet)


__all__ = [
    "reset_app_style",
    "apply_stylesheet",
    "apply_auto_theme",
    "apply_win11_style",
    "is_win11_style_available",
    "apply_initial_theme_from_settings",
]
