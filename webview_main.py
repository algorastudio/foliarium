#!/usr/bin/env python3
"""
webview_main.py — Launcher principale di Foliarium con supporto PyWebView + PyQt6.

Questo è il nuovo entry point dell'applicazione. Decide quale UI usare:
1. PyWebView (predefinito) — UI moderna, FastAPI backend integrato
2. PyQt6 (fallback) — UI classica, QPyQt6 widgets, più stabile

Usare:
    python webview_main.py                  # Tenta PyWebView, fallback a PyQt6
    python webview_main.py --use-pyqt6      # Forza PyQt6
    python webview_main.py --dev            # Dev mode: Vite dev server, HMR
    python webview_main.py --demo           # Demo mode (embedded PostgreSQL)
    python webview_main.py --demo --dev     # Demo + dev mode
"""
import sys
import os
import logging
import argparse
from pathlib import Path


def setup_logging(log_level=logging.INFO):
    """Configura logging globale per il launcher."""
    logging.basicConfig(
        level=log_level,
        format="[%(name)s] %(levelname)s: %(message)s",
    )


def parse_args():
    """Parsa argomenti riga di comando."""
    parser = argparse.ArgumentParser(
        description="Foliarium Launcher",
        epilog="Default: tenta PyWebView, fallback a PyQt6 se necessario",
    )
    parser.add_argument(
        "--use-pyqt6",
        action="store_true",
        help="Forza uso di PyQt6 (salta PyWebView)",
    )
    parser.add_argument(
        "--dev",
        action="store_true",
        help="Dev mode: Vite dev server con HMR, no build React necessario",
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Demo mode: usa PostgreSQL embedded",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Abilita verbose logging (DEBUG level)",
    )
    return parser.parse_args()


def setup_database_and_config(demo_mode: bool = False):
    """
    Inizializza database e config.

    Returns:
        (db_manager, config_dict)
    """
    from config import setup_global_logging, ENV_DB_HOST, ENV_DB_USER, ENV_DB_PASS, ENV_DB_NAME, ENV_DB_PORT
    from catasto_db_manager import CatastoDBManager
    import config as cfg

    setup_global_logging()

    if demo_mode:
        # Demo mode: avvia PostgreSQL embedded e usa credenziali demo
        try:
            from foliarium.core.services.demo_launcher import is_embedded_available, start_demo_postgres
            if not is_embedded_available():
                logging.warning("PostgreSQL embedded non disponibile per demo mode")
                logging.info("Fallback a credenziali di produzione...")
            else:
                start_demo_postgres()
                logging.info("PostgreSQL embedded avviato su porta 15432")
        except Exception as e:
            logging.warning(f"Demo launcher non disponibile: {e}")

    # Determina schema: env var → config.ini → default 'catasto'
    schema = os.environ.get("FOLIARIUM_DB_SCHEMA")
    if not schema:
        schema = cfg._ini_get("database", "schema", "catasto")

    # Crea DB manager con credenziali da config
    db = CatastoDBManager(
        dbname=ENV_DB_NAME,
        user=ENV_DB_USER,
        password=ENV_DB_PASS,
        host=ENV_DB_HOST,
        port=ENV_DB_PORT,
        schema=schema,
    )

    # Retry-loop sull'inizializzazione del pool
    import time
    deadline = time.monotonic() + 60.0
    attempt = 0
    while True:
        attempt += 1
        if db.initialize_main_pool():
            logging.info("Database pool inizializzato correttamente")
            break
        if time.monotonic() >= deadline:
            logging.error("Database pool non inizializzato dopo 60 secondi")
            raise RuntimeError("Impossibile connettersi al database")
        logging.warning(f"Database non pronto (tentativo {attempt}), retry tra 2s…")
        time.sleep(2.0)

    return db


def try_webview(db_manager, dev_mode: bool = False) -> bool:
    """
    Tenta di avviare la modalità PyWebView.

    Args:
        db_manager: CatastoDBManager
        dev_mode: Se True, non compila frontend (usa Vite dev server)

    Returns:
        True se il lancio è riuscito, False se fallback necessario
    """
    try:
        import webview
        logging.info("pywebview disponibile, tentativo lancio...")
    except ImportError:
        logging.info("pywebview non installato, skip PyWebView")
        return False

    try:
        from api.webview_launcher import launch_webview_app

        logging.info(f"Lancio PyWebView (dev_mode={dev_mode})...")
        success = launch_webview_app(db_manager, use_dev_mode=dev_mode)

        if not success:
            logging.warning("PyWebView lancio fallito")
            return False

        return True

    except Exception as e:
        logging.warning(f"Errore PyWebView: {e}", exc_info=True)
        return False


def launch_pyqt6(db_manager) -> bool:
    """
    Lancia la modalità PyQt6 classica.

    Args:
        db_manager: CatastoDBManager

    Returns:
        True se il lancio è riuscito
    """
    try:
        from gui_main import CatastoMainWindow
        from PyQt6.QtWidgets import QApplication

        app = QApplication(sys.argv)
        app.setApplicationName("Foliarium")
        app.setOrganizationName("Algora Studio")

        window = CatastoMainWindow(db_manager)
        window.show()

        logging.info("Foliarium PyQt6 avviato")
        sys.exit(app.exec())

    except Exception as e:
        logging.error(f"Errore lancio PyQt6: {e}", exc_info=True)
        return False


def main():
    """Entry point principale."""
    args = parse_args()

    # Setup logging
    log_level = logging.DEBUG if args.debug else logging.INFO
    setup_logging(log_level)

    logging.info("====== Foliarium Launcher ======")
    logging.info(f"Arguments: use_pyqt6={args.use_pyqt6}, dev={args.dev}, demo={args.demo}")

    # Step 1: Inizializza database
    try:
        db_manager = setup_database_and_config(demo_mode=args.demo)
    except Exception as e:
        logging.error(f"Impossibile inizializzare database: {e}")
        sys.exit(1)

    # Step 2: Sceglie UI
    if args.use_pyqt6:
        logging.info("UI PyQt6 forzato da riga di comando")
        success = launch_pyqt6(db_manager)
    else:
        # Default: tenta PyWebView, fallback a PyQt6
        logging.info("Tentativo PyWebView (con fallback a PyQt6)...")
        if try_webview(db_manager, dev_mode=args.dev):
            success = True
        else:
            logging.info("Fallback a PyQt6...")
            success = launch_pyqt6(db_manager)

    if not success:
        logging.error("Lanciare l'applicazione non è riuscito")
        sys.exit(1)


if __name__ == "__main__":
    main()
