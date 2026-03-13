# app_paths.py

import sys
import os
import logging
from pathlib import Path

# --- 1. GESTIONE PERCORSO BASE APPLICAZIONE (STATICO) ---

def get_base_dir():
    """
    Restituisce la directory base dell'applicazione (dove si trovano le risorse statiche).
    Funziona sia in sviluppo che in un eseguibile creato da PyInstaller.
    """
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        # Se siamo in un eseguibile PyInstaller, la base è la cartella temporanea _MEIPASS
        return Path(sys._MEIPASS)
    else:
        # Altrimenti, in sviluppo, è la cartella dove si trova questo script
        return Path(__file__).parent

# Definiamo le directory statiche che non cambiano mai
BASE_DIR = get_base_dir()
RESOURCES_DIR = BASE_DIR / "resources"
STYLES_DIR = BASE_DIR / "styles"
DOCS_DIR = BASE_DIR / "docs"


# --- 2. GESTIONE PERCORSI DATI UTENTE (DINAMICI E SCRIVIBILI) ---

def get_user_data_dir():
    """
    Restituisce un percorso scrivibile nella cartella dati dell'utente.
    Es. Windows: C:\\Users\\NOMEUTENTE\\AppData\\Local\\Meridiana
    """
    local_app_data = os.getenv('LOCALAPPDATA')
    if local_app_data:
        # Percorso standard per i dati delle app su Windows
        user_data_dir = Path(local_app_data) / "Meridiana"
    else:
        # Fallback per sistemi non-Windows
        user_data_dir = Path.home() / ".meridiana"
    
    return user_data_dir

# Definiamo le directory dinamiche
APP_DATA_DIR = get_user_data_dir()
ESPORTAZIONI_DIR = APP_DATA_DIR / "esportazioni"
LOG_DIR = APP_DATA_DIR / "logs"

# Creiamo fisicamente queste directory se non esistono.
# Questa operazione è sicura perché APP_DATA_DIR è sempre scrivibile.
ESPORTAZIONI_DIR.mkdir(parents=True, exist_ok=True)
LOG_DIR.mkdir(parents=True, exist_ok=True)


# --- 3. FUNZIONI HELPER PER ACCEDERE AI PERCORSI (DA USARE NEL RESTO DELL'APP) ---

def get_resource_path(relative_path: str) -> Path:
    """
    Ottiene il percorso assoluto di una risorsa nella cartella 'resources'.
    Usa questa funzione per icone, loghi, EULA, etc.
    """
    return RESOURCES_DIR / relative_path

def get_style_path(style_filename: str) -> Path:
    """
    Ottiene il percorso assoluto di un file di stile nella cartella 'styles'.
    """
    return STYLES_DIR / style_filename

def get_log_file_path(log_filename: str = "meridiana.log") -> Path:
    """
    Ottiene il percorso assoluto per un file di log nella cartella dati utente.
    """
    return LOG_DIR / log_filename

def get_available_styles() -> list[str]:
    """
    Scansiona la cartella degli stili e restituisce i nomi dei file .qss disponibili.
    """
    logger = logging.getLogger(__name__)
    if not STYLES_DIR.exists():
        logger.warning(f"La cartella degli stili non esiste: {STYLES_DIR}")
        return []
    try:
        return [f.name for f in STYLES_DIR.iterdir() if f.is_file() and f.suffix == '.qss']
    except Exception as e:
        logger.error(f"Impossibile leggere la cartella degli stili: {e}")
        return []

def load_stylesheet(filename: str) -> str:
    """
    Carica il contenuto di un file di stile.
    """
    logger = logging.getLogger(__name__)
    style_path = get_style_path(filename)
    if not style_path.exists():
        logger.warning(f"File di stile non trovato: {style_path}")
        return ""
    try:
        with open(style_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        logger.error(f"Impossibile caricare il file di stile '{filename}': {e}")
        return ""

def get_logo_path() -> Path:
    """Ritorna il percorso del file del logo."""
    return get_resource_path("logo_meridiana.png")

# Per mantenere la retrocompatibilità con le chiamate `resource_path`
# che potrebbero essere rimaste in giro, la rendiamo un alias di get_resource_path
resource_path = get_resource_path