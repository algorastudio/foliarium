# config.py

APP_VERSION = "1.6.0"
APP_NAME    = "Foliarium"
APP_SUBTITLE = "Archivio Catastale Storico"

import logging
import os
import sys
from logging.handlers import RotatingFileHandler

# Ora questo import è sicuro, perché app_paths è autonomo
from app_paths import LOG_DIR, get_log_file_path

from PyQt6.QtCore import QStandardPaths, QCoreApplication

# --- CONFIGURAZIONI AMBIENTE E CI/CD (GITHUB ACTIONS) ---
# GitHub Actions imposta automaticamente le variabili 'CI' e 'GITHUB_ACTIONS' a 'true'.
# Usiamo questo flag per capire se l'app sta girando sul server di test o sul PC di un utente.
IS_TEST_ENV = os.environ.get('CI') == 'true' or os.environ.get('GITHUB_ACTIONS') == 'true'

# --- MODALITÀ DEMO ---
# Attivata con argomento --demo oppure variabile d'ambiente FOLIARIUM_DEMO=1
IS_DEMO_MODE = '--demo' in sys.argv or os.environ.get('FOLIARIUM_DEMO', '') == '1'

# Credenziali del DB demo.
# In modalità embedded (PostgreSQL portabile nel bundle) demo_launcher.py
# sovrascrive queste env var con 127.0.0.1:15432 prima della connessione.
DEMO_DB_HOST = os.environ.get('DEMO_DB_HOST', '127.0.0.1')
DEMO_DB_NAME = os.environ.get('DEMO_DB_NAME', 'catasto_storico')
DEMO_DB_USER = os.environ.get('DEMO_DB_USER', 'demo_user')
DEMO_DB_PASS = os.environ.get('DEMO_DB_PASS', 'demo2025')
DEMO_DB_PORT = os.environ.get('DEMO_DB_PORT', '15432')   # porta dedicata demo
# Username/password autologin per la modalità demo
DEMO_LOGIN_USER = 'demo'
DEMO_LOGIN_PASS = 'demo2025'

# Leggiamo le credenziali dalle variabili d'ambiente (fornite dal file .yml di GitHub Actions).
# Se non ci sono (es. uso normale), usiamo dei valori di default sicuri.
ENV_DB_HOST = os.environ.get('DB_HOST', 'localhost')
ENV_DB_NAME = os.environ.get('DB_NAME', 'catasto_storico')
ENV_DB_USER = os.environ.get('DB_USER', 'postgres')
ENV_DB_PASS = os.environ.get('DB_PASS', '')
ENV_DB_PORT = os.environ.get('DB_PORT', '5432')


# --- Nomi per le chiavi di QSettings ---
SETTINGS_DB_TYPE = "Database/Type"
SETTINGS_DB_HOST = "Database/Host"
SETTINGS_DB_PORT = "Database/Port"
SETTINGS_DB_NAME = "Database/DBName"
SETTINGS_DB_USER = "Database/User"
SETTINGS_DB_SCHEMA = "Database/Schema"
# Non salviamo la password in QSettings (Corretto! Ottima pratica di sicurezza)
SETTINGS_DB_PASSWORD = "Database/Password"

# --- Nomi per le chiavi UI in QSettings ---
SETTINGS_UI_CURRENT_STYLE = "UI/CurrentStyle"
SETTINGS_UI_AUTO_THEME = "UI/AutoTheme"
SETTINGS_UI_WIN11_STYLE = "UI/Win11NativeStyle"

# --- Notifiche email (SMTP) ---
SETTINGS_SMTP_ENABLED   = "Email/Enabled"
SETTINGS_SMTP_HOST      = "Email/Host"
SETTINGS_SMTP_PORT      = "Email/Port"        # default 587
SETTINGS_SMTP_USER      = "Email/User"
SETTINGS_SMTP_USE_TLS   = "Email/UseTLS"      # default True
SETTINGS_SMTP_FROM_ADDR = "Email/FromAddress"
SETTINGS_EMAIL_ON_CREATE = "Email/OnCreate"   # default True
SETTINGS_EMAIL_ON_PASSWD = "Email/OnPassword" # default True
SETTINGS_EMAIL_ON_ROLE   = "Email/OnRole"     # default True
SETTINGS_EMAIL_ON_LOGIN  = "Email/OnLogin"    # default True

# --- Sicurezza sessione ---
SETTINGS_SESSION_TIMEOUT = "Security/SessionTimeoutMinutes"  # default 15, 0 = disabilitato

# --- EULA / Licenza ---
EULA_VERSION = "1.0"
SETTINGS_EULA_ACCEPTED = "Legal/AcceptedEULAVersion"

# --- GESTIONE LICENZA ---
SETTINGS_LICENSE_FILE_PATH  = "License/FilePath"
SETTINGS_LICENSE_NETWORK_SHARE = "License/NetworkSharePath"
# Percorso default del file di licenza (accanto all'eseguibile)
LICENSE_DEFAULT_FILENAME = "foliarium.license"

# --- AGGIORNAMENTI AUTOMATICI ---
SETTINGS_UPDATE_AUTO_CHECK  = "Updates/AutoCheck"       # bool, default True
SETTINGS_UPDATE_CHANNEL     = "Updates/Channel"         # "stable" | "beta"

# --- Temi usati dall'auto-rilevamento dark/light del sistema operativo ---
AUTO_THEME_DARK = "dark_mode_stylesheet.qss"
AUTO_THEME_LIGHT = "foliarium_styles.qss"

# --- COSTANTI TABELLE INTERFACCIA ---
COLONNE_POSSESSORI_DETTAGLI_NUM = 6
COLONNE_POSSESSORI_DETTAGLI_LABELS = [
    "ID Poss.", "Nome Completo", "Cognome Nome", "Paternità", "Quota", "Titolo"]

COLONNE_VISUALIZZAZIONE_POSSESSORI_NUM = 5
COLONNE_VISUALIZZAZIONE_POSSESSORI_LABELS = [
    "ID", "Nome Completo", "Paternità", "Comune Rif.", "Num. Partite"]

COLONNE_INSERIMENTO_POSSESSORI_NUM = 4
COLONNE_INSERIMENTO_POSSESSORI_LABELS = [
    "ID", "Nome Completo", "Paternità", "Comune Riferimento"]

NUOVE_ETICHETTE_POSSESSORI = ["id", "nome_completo", "codice_fiscale", "data_nascita", "cognome_nome",
                              "paternita", "indirizzo_residenza", "comune_residenza_nome", "attivo", "note", "num_partite"]


# --- MODALITÀ DI SVILUPPO ---
DEVELOPMENT_MODE = True


def setup_global_logging(log_level=logging.INFO):
    """
    Configura il logging globale per l'applicazione, salvando i file
    in una cartella dati utente scrivibile.
    """
    try:
        # Ottiene il percorso standard per i dati dell'applicazione locale.
        log_directory = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppLocalDataLocation)
        
        # Se il percorso non esiste, fallback
        if not log_directory:
            log_directory = os.path.join(os.path.expanduser("~"), "FoliariumAppData")

        # Aggiungiamo una sottocartella 'logs'
        log_directory = os.path.join(log_directory, "logs")

        # Crea la cartella di log se non esiste
        os.makedirs(log_directory, exist_ok=True)

        log_file_path = os.path.join(log_directory, "foliarium_gui.log")

        # Configurazione del logger 'CatastoGUI'
        logger = logging.getLogger("CatastoGUI")
        logger.setLevel(log_level)
        logger.handlers.clear()

        # Formattatore
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'
        )

        # Handler per file con rotazione
        handler_file = RotatingFileHandler(
            log_file_path, maxBytes=5*1024*1024, backupCount=5, encoding='utf-8'
        )
        handler_file.setFormatter(formatter)
        logger.addHandler(handler_file)

        # Handler per console (per debug)
        handler_console = logging.StreamHandler()
        handler_console.setFormatter(formatter)
        logger.addHandler(handler_console)

        # Se siamo in ambiente di test, lo segnaliamo nel log
        if IS_TEST_ENV:
            logger.info("Avvio in modalità TEST AMBIENT (GitHub Actions). I log potrebbero essere limitati.")
        else:
            logger.info(f"Logging configurato. File di log in: {log_file_path}")

    except Exception as e:
        print(f"ERRORE CRITICO durante la configurazione del logging: {e}")
        logging.basicConfig(level=logging.WARNING)
        logging.warning("Utilizzo configurazione di logging di fallback.")