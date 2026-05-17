"""
foliarium/ui/login_flow.py — Connessione al DB e login utente.

Estratto da gui_main.py (Sprint 3.6 refactor — six-hats).

Espone 3 funzioni per scomporre il flusso di avvio in stadi indipendenti:

    1. try_autoconnect_db()  — tentativo silenzioso con QSettings + keyring
    2. connect_db_with_dialog()  — fallback interattivo (loop con
       DBConfigDialog finche' la connessione riesce o l'utente annulla)
    3. ensure_db_connection() — combina i due: ritorna sempre un
       CatastoDBManager con pool inizializzato, o chiama sys.exit(0) se
       l'utente annulla la configurazione manuale.

    4. perform_user_login() — apre LoginDialog, ritorna le credenziali
       della sessione, o chiama sys.exit(0) se l'utente annulla.

Le funzioni mantengono la semantica originale (sys.exit con
license_mgr.release_seat() incluso) per preservare il comportamento di
avvio esistente. I chiamanti devono solo passare gli oggetti, non
duplicare la logica.
"""

from __future__ import annotations

import logging
import sys
from typing import Optional, Tuple

from PyQt6.QtCore import QSettings
from PyQt6.QtWidgets import QDialog, QMessageBox

from catasto_db_manager import CatastoDBManager
from config import (
    SETTINGS_DB_HOST,
    SETTINGS_DB_NAME,
    SETTINGS_DB_PASSWORD,
    SETTINGS_DB_PORT,
    SETTINGS_DB_USER,
)


def _get_password_from_keyring_safe(host: str, user: str) -> Optional[str]:
    """Wrapper difensivo: keyring puo' non essere installato."""
    try:
        from app_utils import get_password_from_keyring
        return get_password_from_keyring(host, user)
    except Exception:
        return None


def try_autoconnect_db(
    settings: QSettings,
    logger: logging.Logger,
) -> Optional[CatastoDBManager]:
    """
    Tentativo silenzioso di connessione automatica leggendo QSettings.
    La password viene cercata prima in QSettings, poi nel keyring.

    Ritorna un CatastoDBManager con pool inizializzato, oppure None se
    la connessione automatica non e' possibile o fallisce.
    """
    logger.info("Tentativo di connessione automatica con le impostazioni salvate...")

    saved_password = settings.value(SETTINGS_DB_PASSWORD, "", type=str)
    if not saved_password:
        host = settings.value(SETTINGS_DB_HOST, "localhost", type=str)
        user = settings.value(SETTINGS_DB_USER, "postgres", type=str)
        saved_password = _get_password_from_keyring_safe(host, user)

    saved_config = {
        "host": settings.value(SETTINGS_DB_HOST, "localhost", type=str),
        "port": settings.value(SETTINGS_DB_PORT, 5432, type=int),
        "dbname": settings.value(SETTINGS_DB_NAME, "catasto_storico", type=str),
        "user": settings.value(SETTINGS_DB_USER, "postgres", type=str),
        "password": saved_password or "",
    }

    if not (saved_config["dbname"] and saved_config["user"] and saved_config["password"]):
        logger.info(
            "Dati di connessione incompleti (manca password o altri parametri "
            "essenziali). Skip connessione automatica."
        )
        return None

    try:
        db = CatastoDBManager(**saved_config)
        if db.initialize_main_pool():
            logger.info("Connessione automatica riuscita.")
            return db
        return None
    except Exception as e:
        logger.warning("Errore durante la creazione di CatastoDBManager: %s", e)
        return None


def connect_db_with_dialog(
    logger: logging.Logger,
    license_mgr=None,
) -> CatastoDBManager:
    """
    Fallback interattivo: apre DBConfigDialog in loop finche' la
    connessione riesce. Se l'utente annulla, chiama sys.exit(0) dopo
    aver rilasciato l'eventuale seat di licenza.
    """
    # Import locale per evitare ciclo con dialogs.py
    from dialogs import DBConfigDialog

    logger.warning("Connessione automatica fallita. Apertura dialogo di configurazione manuale.")
    QMessageBox.information(
        None, "Configurazione Database",
        "Impossibile connettersi con le impostazioni salvate. Apriamo la configurazione.",
    )

    while True:
        config_dialog = DBConfigDialog(parent=None)
        if config_dialog.exec() != QDialog.DialogCode.Accepted:
            logger.info("Configurazione manuale annullata. Uscita.")
            if license_mgr is not None:
                try:
                    license_mgr.release_seat()
                except Exception:
                    pass
            sys.exit(0)

        current = config_dialog.get_config_values(include_password=True)
        params = {
            "host": current.get("host"),
            "port": current.get("port"),
            "dbname": current.get("dbname"),
            "user": current.get("user"),
            "password": current.get("password", ""),
        }
        params = {k: v for k, v in params.items() if v is not None}
        params.setdefault("password", "")

        try:
            db = CatastoDBManager(**params)
        except Exception as e:
            logger.error("Errore creazione CatastoDBManager: %s", e)
            QMessageBox.critical(
                None, "Errore Configurazione",
                f"Errore nella configurazione del database: {e}",
            )
            continue

        if db.initialize_main_pool():
            logger.info("Connessione manuale riuscita.")
            return db

        error_details = db.get_last_connect_error_details() or {}
        pgcode = error_details.get("pgcode")
        pgerror_msg = error_details.get("pgerror")
        if pgcode == "28P01":
            QMessageBox.critical(None, "Errore Autenticazione",
                                 "Password o utente errati.")
        else:
            QMessageBox.critical(None, "Errore Connessione",
                                 f"Impossibile connettersi.\n{pgerror_msg}")


def ensure_db_connection(
    main_window,
    settings: QSettings,
    logger: logging.Logger,
    license_mgr=None,
) -> CatastoDBManager:
    """
    Garantisce una connessione DB inizializzata: prima prova
    automatica, poi fallback interattivo. Aggiorna anche
    main_window.db_manager e main_window.pool_initialized_successful.
    """
    db = try_autoconnect_db(settings, logger)
    if db is None or not db.pool:
        db = connect_db_with_dialog(logger, license_mgr=license_mgr)

    main_window.db_manager = db
    main_window.pool_initialized_successful = True
    return db


def perform_user_login(
    db_manager: CatastoDBManager,
    client_ip: str,
    parent,
    logger: logging.Logger,
    license_mgr=None,
) -> Tuple[int, dict, Optional[int]]:
    """
    Apre LoginDialog. Ritorna (user_id, user_info, session_id) in caso di
    successo. Se l'utente annulla, rilascia il seat e chiama sys.exit(0).
    """
    from foliarium.ui.dialogs.admin import LoginDialog

    login_dialog = LoginDialog(db_manager, client_ip, parent=parent)
    if login_dialog.exec() != QDialog.DialogCode.Accepted:
        logger.info("Login utente annullato. Uscita.")
        if license_mgr is not None:
            try:
                license_mgr.release_seat()
            except Exception:
                pass
        sys.exit(0)

    return (
        login_dialog.logged_in_user_id,
        login_dialog.logged_in_user_info,
        login_dialog.current_session_id_from_dialog,
    )


__all__ = [
    "try_autoconnect_db",
    "connect_db_with_dialog",
    "ensure_db_connection",
    "perform_user_login",
]
