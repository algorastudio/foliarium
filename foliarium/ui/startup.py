"""
foliarium/ui/startup.py — Sequenza di avvio: splash, EULA, licenza.

Estratto da gui_main.py (Sprint 3.7 refactor — six-hats).

Tre funzioni dedicate ai check pre-applicazione:

    1. show_splash_screen(app, test_env)
       Mostra la splash 2.5 s, salta in CI/test. Nessun valore di ritorno.

    2. ensure_eula_accepted(logger)
       Verifica che l'EULA della versione corrente sia accettata; in caso
       contrario apre WelcomeScreen. Se l'utente rifiuta, chiama sys.exit(0).

    3. validate_license_and_acquire_seat(logger)
       Valida il file di licenza e acquisisce un seat di rete. Ritorna il
       LicenseManager se OK; sys.exit(1) altrimenti.

Le funzioni mantengono semantica originale (sys.exit, messaggi, log)
per non alterare il comportamento utente.
"""

from __future__ import annotations

import logging
import sys
import time
from typing import Optional

from PyQt6.QtCore import QSettings
from PyQt6.QtWidgets import QApplication, QDialog, QMessageBox

from config import (
    EULA_VERSION,
    IS_TEST_ENV,
    SETTINGS_EULA_ACCEPTED,
)


def show_splash_screen(app: QApplication, duration_seconds: float = 2.5) -> None:
    """
    Mostra la splash screen per `duration_seconds`. Salta in IS_TEST_ENV.
    """
    if IS_TEST_ENV:
        return
    from foliarium.ui.splash import FoliariumSplashScreen
    splash = FoliariumSplashScreen()
    splash.show()
    app.processEvents()
    time.sleep(duration_seconds)
    app.processEvents()
    splash.close()


def ensure_eula_accepted(logger: logging.Logger) -> None:
    """
    Verifica EULA: se la versione accettata in QSettings non coincide con
    EULA_VERSION, apre WelcomeScreen. Se l'utente non accetta, sys.exit(0).
    """
    settings = QSettings()
    accepted_version = settings.value(SETTINGS_EULA_ACCEPTED, "", type=str)
    if accepted_version == EULA_VERSION:
        return

    # Import locale per evitare ciclo con gui_widgets
    from gui_widgets import WelcomeScreen

    welcome = WelcomeScreen(parent=None)
    if welcome.exec() != QDialog.DialogCode.Accepted:
        logger.info("EULA non accettata. Uscita.")
        sys.exit(0)
    settings.setValue(SETTINGS_EULA_ACCEPTED, EULA_VERSION)
    settings.sync()


def validate_license_and_acquire_seat(logger: logging.Logger):
    """
    Verifica il file di licenza e tenta di acquisire un seat di rete.

    Ritorna l'istanza di LicenseManager se tutto OK. In caso di licenza
    non valida o seat esauriti mostra un messaggio all'utente e chiama
    sys.exit(1).
    """
    from foliarium.core.services.license import LicenseManager

    license_mgr = LicenseManager()
    info = license_mgr.validate()
    if not info.is_valid:
        QMessageBox.critical(
            None,
            "Licenza non valida",
            f"<b>Foliarium non può essere avviato.</b><br><br>"
            f"{info.error_message}<br><br>"
            "Contatta il tuo amministratore per ottenere una licenza valida.",
        )
        logger.error("Licenza non valida: %s", info.error_message)
        sys.exit(1)

    allowed, seats, max_seats = license_mgr.acquire_seat()
    if not allowed:
        QMessageBox.critical(
            None,
            "Numero di licenze esaurito",
            f"<b>Impossibile avviare Foliarium.</b><br><br>"
            f"Sono già attive <b>{seats - 1}</b> istanze su {max_seats} "
            "consentite dalla licenza.<br>"
            "Chiudi un'altra sessione e riprova.",
        )
        logger.error("Seat di rete esauriti (%s/%s)", seats, max_seats)
        sys.exit(1)

    logger.info(
        "Licenza OK — intestata a: %s | tipo: %s | seat: %s/%s",
        info.licensed_to, info.license_type, seats, max_seats,
    )
    return license_mgr


__all__ = [
    "show_splash_screen",
    "ensure_eula_accepted",
    "validate_license_and_acquire_seat",
]
