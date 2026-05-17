import logging
import os
import socket
from datetime import datetime
from typing import Optional

from PyQt6.QtCore import QStandardPaths
from PyQt6.QtWidgets import QMessageBox

_log = logging.getLogger("CatastoGUI.app_utils")

# Le classi PDF e il flag FPDF_AVAILABLE sono stati estratti in
# foliarium.reporting.pdf. Qui restano re-export di compatibilita' per il
# codice (gui_widgets, partita_workflow_widgets, search_widgets, dialoghi,
# test) che li importa storicamente da app_utils.
from foliarium.reporting.pdf import (
    FPDF_AVAILABLE,
    ModernCatastoPDF,
    PDFPartita,
    PDFPossessore,
    GenericTextReportPDF,
    BulkReportPDF,
)

try:
    import keyring
except ImportError:
    keyring = None
    logging.warning(
        "Libreria 'keyring' non trovata. Salvataggio sicuro password non disponibile."
    )



def format_indirizzo(tipologia: Optional[str], nome: Optional[str],
                     numero_civico: Optional[str] = None) -> str:
    """Concatena tipologia + nome + civico in un indirizzo leggibile.

    Esempi:
        format_indirizzo("Via", "Repubblica", "17")   → "Via Repubblica, 17"
        format_indirizzo("Piazza", "Garibaldi", None) → "Piazza Garibaldi"
        format_indirizzo(None, "Pianello", None)      → "Pianello"
    """
    parts = []
    tipo = (tipologia or "").strip()
    n = (nome or "").strip()
    if tipo:
        parts.append(tipo)
    if n:
        parts.append(n)
    base = " ".join(parts).strip()
    civ = (numero_civico or "").strip()
    if base and civ:
        return f"{base}, {civ}"
    return base or civ or ""


def get_local_ip_address():
    """
    Ottiene l'indirizzo IP locale della macchina con cui si esce sulla rete.
    """
    try:
        # Crea un socket UDP (non invia dati reali) per determinare l'IP di uscita
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0.1)
        # 8.8.8.8 è il DNS di Google, un endpoint affidabile per questo scopo
        s.connect(('8.8.8.8', 1))
        ip = s.getsockname()[0]
    except Exception:
        # Se non c'è connessione di rete o si verifica un errore, usa il fallback
        try:
            ip = socket.gethostbyname(socket.gethostname())
        except socket.gaierror:
            ip = '127.0.0.1'
    finally:
        if 's' in locals():
            s.close()
    return ip


def _get_default_export_path(default_filename: str) -> str:
    """
    Crea la sottocartella 'Esportazioni Foliarium' in Documenti se non esiste e restituisce
    il percorso completo per il file di default.
    """
    cartella_documenti = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DocumentsLocation)
    if not cartella_documenti:
        cartella_documenti = os.path.expanduser("~")
    cartella_esportazioni = os.path.join(cartella_documenti, "Esportazioni Foliarium")
    os.makedirs(cartella_esportazioni, exist_ok=True)
    return os.path.join(cartella_esportazioni, default_filename)


# I wrapper GUI di export (partita/possessore in JSON/CSV/PDF) sono stati
# spostati in foliarium/ui/export/{partita,possessore}.py. Qui restano
# re-export di compatibilita' per i chiamanti storici (gui_widgets,
# partita_workflow_widgets, foliarium/ui/dialogs/partita).
from foliarium.ui.export import (  # noqa: E402
    gui_esporta_partita_csv,
    gui_esporta_partita_json,
    gui_esporta_partita_pdf,
    gui_esporta_possessore_csv,
    gui_esporta_possessore_json,
    gui_esporta_possessore_pdf,
)


def get_password_from_keyring(service_name: str, username: str) -> Optional[str]:
    """
    Recupera una password dal keyring di sistema in modo sicuro.
    Restituisce None se keyring non è disponibile o la password non è trovata.
    """
    if not keyring:
        return None # La libreria non è installata

    try:
        password = keyring.get_password(service_name, username)
        if password:
            logging.getLogger("CatastoGUI").info(f"Password recuperata dal keyring per il servizio '{service_name}' e utente '{username}'.")
        else:
            logging.getLogger("CatastoGUI").info(f"Nessuna password trovata nel keyring per il servizio '{service_name}' e utente '{username}'.")
        return password
    except Exception as e:
        logging.getLogger("CatastoGUI").error(f"Errore durante il recupero della password dal keyring: {e}", exc_info=True)
        return None

def prompt_to_open_file(parent_widget, filename: str):
    """
    Mostra un dialogo che chiede all'utente se vuole aprire il file appena creato.
    Se l'utente accetta, apre il file con l'applicazione di sistema predefinita.
    """
    if not filename:
        return
        
    reply = QMessageBox.question(
        parent_widget,
        "Esportazione Completata",
        f"File salvato con successo.\n\nVuoi aprirlo ora?",
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        QMessageBox.StandardButton.Yes  # Il pulsante 'Sì' è preselezionato
    )

    if reply == QMessageBox.StandardButton.Yes:
        try:
            from PyQt6.QtCore import QUrl
            from PyQt6.QtGui import QDesktopServices
            
            QDesktopServices.openUrl(QUrl.fromLocalFile(filename))
        except Exception as e:
            logging.getLogger("CatastoGUI").error(f"Impossibile aprire il file {filename}: {e}", exc_info=True)
            QMessageBox.critical(parent_widget, "Errore Apertura File", f"Impossibile aprire il file:\n{e}")
            
def is_file_locked(filepath):
    """
    Verifica se un file è bloccato/in uso da un altro processo.
    """
    if not os.path.exists(filepath):
        return False
    
    try:
        # Prova ad aprire il file in modalità esclusiva
        with open(filepath, 'a'):
            pass
        return False
    except (IOError, PermissionError):
        return True

def get_alternative_filename(original_path):
    """
    Genera un nome file alternativo aggiungendo un timestamp.
    """
    base, ext = os.path.splitext(original_path)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{base}_{timestamp}{ext}"


