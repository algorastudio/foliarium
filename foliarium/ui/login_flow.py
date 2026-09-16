"""
foliarium/ui/login_flow.py — Connessione al DB e login utente.

Estratto da gui_main.py (Sprint 3.6 refactor — six-hats).

Espone 3 funzioni per scomporre il flusso di avvio in stadi indipendenti:

    1. try_autoconnect_db()  — tentativo silenzioso con QSettings,
       keyring e config.ini (vedi _resolve_connection_params)
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

import config as cfg
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


def _env_port() -> int:
    """Porta da config.ini/env come intero. Un valore non numerico vale 5432."""
    try:
        return int(str(cfg.ENV_DB_PORT).strip())
    except (TypeError, ValueError):
        return 5432


def _resolve_connection_params(settings: QSettings) -> dict:
    """
    Risolve i parametri di connessione con precedenza, chiave per chiave:

        QSettings  >  config.ini / variabili d'ambiente  >  default

    I valori `cfg.ENV_DB_*` incorporano gia' la precedenza
    config.ini > env var > default (vedi config.py), quindi qui basta
    usarli come fallback di ogni `settings.value()`.

    Serve perche' al primo avvio dopo l'installazione QSettings e' vuota:
    senza questo fallback l'archivista dovrebbe ridigitare a mano host,
    porta, database, utente e password che l'installer ha gia' scritto in
    config.ini accanto all'eseguibile.

    QSettings resta prioritaria: se l'utente ha configurato la connessione
    dal dialogo, la sua scelta esplicita non viene scavalcata da config.ini.
    """
    return {
        "host": settings.value(SETTINGS_DB_HOST, cfg.ENV_DB_HOST, type=str),
        "port": settings.value(SETTINGS_DB_PORT, _env_port(), type=int),
        "dbname": settings.value(SETTINGS_DB_NAME, cfg.ENV_DB_NAME, type=str),
        "user": settings.value(SETTINGS_DB_USER, cfg.ENV_DB_USER, type=str),
    }


def _targets_configured_server(params: dict) -> bool:
    """
    True se i parametri risolti puntano allo stesso server descritto in
    config.ini / env var.

    La password di config.ini viene usata come fallback solo in quel caso:
    con un host o un database diversi (QSettings che punta altrove) sarebbe
    la credenziale di un altro server, e tentare comunque significherebbe
    spedire una password a una destinazione che non la attende.
    """
    return (
        params["host"] == cfg.ENV_DB_HOST
        and params["port"] == _env_port()
        and params["dbname"] == cfg.ENV_DB_NAME
        and params["user"] == cfg.ENV_DB_USER
    )


def _resolve_password(settings: QSettings, params: dict) -> Tuple[str, str]:
    """
    Risolve la password nell'ordine QSettings > keyring > config.ini/env.
    Ritorna (password, origine); l'origine serve solo per il log.
    """
    password = settings.value(SETTINGS_DB_PASSWORD, "", type=str)
    if password:
        return password, "QSettings"

    from_keyring = _get_password_from_keyring_safe(params["host"], params["user"])
    if from_keyring:
        return from_keyring, "keyring"

    if cfg.ENV_DB_PASS and _targets_configured_server(params):
        return cfg.ENV_DB_PASS, "config.ini/env"

    return "", "nessuna"


def try_autoconnect_db(
    settings: QSettings,
    logger: logging.Logger,
) -> Optional[CatastoDBManager]:
    """
    Tentativo silenzioso di connessione automatica.

    I parametri vengono risolti da QSettings con fallback su config.ini /
    variabili d'ambiente (_resolve_connection_params); la password da
    QSettings, keyring o config.ini (_resolve_password).

    Ritorna un CatastoDBManager con pool inizializzato, oppure None se
    la connessione automatica non e' possibile o fallisce.
    """
    logger.info("Tentativo di connessione automatica con le impostazioni salvate...")

    saved_config = _resolve_connection_params(settings)
    saved_password, password_source = _resolve_password(settings, saved_config)
    saved_config["password"] = saved_password

    if not (saved_config["dbname"] and saved_config["user"] and saved_config["password"]):
        logger.info(
            "Dati di connessione incompleti (manca password o altri parametri "
            "essenziali). Skip connessione automatica."
        )
        return None

    logger.info(
        "Parametri di connessione: %s@%s:%s/%s (password da %s)",
        saved_config["user"], saved_config["host"],
        saved_config["port"], saved_config["dbname"], password_source,
    )

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
    settings: Optional[QSettings] = None,
) -> CatastoDBManager:
    """
    Fallback interattivo: apre DBConfigDialog in loop finche' la
    connessione riesce. Se l'utente annulla, chiama sys.exit(0) dopo
    aver rilasciato l'eventuale seat di licenza.

    Il dialogo viene precompilato con i parametri risolti da QSettings e
    config.ini: senza, mostrerebbe i propri default hardcoded e l'utente
    si troverebbe a correggere a mano valori che il sistema gia' conosce.
    """
    # Import locale per evitare ciclo con dialogs.py
    from dialogs import DBConfigDialog

    logger.warning("Connessione automatica fallita. Apertura dialogo di configurazione manuale.")
    QMessageBox.information(
        None, "Configurazione Database",
        "Impossibile connettersi con le impostazioni salvate. Apriamo la configurazione.",
    )

    initial_config = _resolve_connection_params(settings if settings is not None else QSettings())

    while True:
        config_dialog = DBConfigDialog(parent=None, initial_config=initial_config)
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
        db = connect_db_with_dialog(logger, license_mgr=license_mgr, settings=settings)

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
    "_resolve_connection_params",
    "_resolve_password",
    "try_autoconnect_db",
    "connect_db_with_dialog",
    "ensure_db_connection",
    "perform_user_login",
]
