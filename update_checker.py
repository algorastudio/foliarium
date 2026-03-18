"""
update_checker.py — Verifica aggiornamenti Foliarium tramite GitHub Releases API

Esegue il controllo in background (QThread) per non bloccare la UI.
Supporta:
  - Skip versione specifica (persistito in QSettings)
  - Disabilitazione controllo automatico (QSettings)
  - Mostra changelog dalla release GitHub
  - Trigger manuale dal menu Help
"""
import json
import logging
import urllib.request
import urllib.error
from typing import Optional

from PyQt6.QtCore import QThread, pyqtSignal

logger = logging.getLogger("CatastoGUI")

GITHUB_API_URL = "https://api.github.com/repos/santoromarco74/catasto/releases/latest"
RELEASES_PAGE_URL = "https://github.com/santoromarco74/catasto/releases"


def _parse_version(v: str) -> tuple:
    """Converte '1.5.0' o 'v1.5.0' in (1, 5, 0)."""
    v = v.lstrip("v")
    try:
        return tuple(int(x) for x in v.split(".")[:3])
    except (ValueError, AttributeError):
        return (0, 0, 0)


class UpdateCheckerWorker(QThread):
    """
    Esegue il controllo aggiornamenti in background.
    Segnali:
      update_available(remote_version_str, release_notes)  — nuova versione trovata
      up_to_date()                                          — versione corrente aggiornata
      check_failed(error_msg)                               — errore di rete o parsing
    """
    update_available = pyqtSignal(str, str)   # (versione_remota, note_release)
    up_to_date = pyqtSignal()
    check_failed = pyqtSignal(str)

    def __init__(self, current_version: str, parent=None):
        super().__init__(parent)
        self.current_version = current_version

    def run(self):
        try:
            req = urllib.request.Request(
                GITHUB_API_URL,
                headers={
                    "User-Agent": f"Foliarium/{self.current_version}",
                    "Accept": "application/vnd.github.v3+json",
                }
            )
            with urllib.request.urlopen(req, timeout=5) as response:
                data = json.loads(response.read().decode("utf-8"))

            remote_tag = data.get("tag_name", "")
            remote_version = _parse_version(remote_tag)
            local_version = _parse_version(self.current_version)
            release_notes = (data.get("body") or "").strip()

            # Tronca le note se troppo lunghe
            if len(release_notes) > 800:
                release_notes = release_notes[:800] + "\n…"

            if remote_version > local_version:
                remote_str = remote_tag.lstrip("v")
                logger.info(f"Aggiornamento disponibile: {remote_str} (locale: {self.current_version})")
                self.update_available.emit(remote_str, release_notes)
            else:
                logger.debug(f"Versione aggiornata: {self.current_version}")
                self.up_to_date.emit()

        except urllib.error.URLError:
            logger.debug("Controllo aggiornamenti: impossibile raggiungere GitHub")
            self.check_failed.emit("Impossibile raggiungere GitHub")
        except Exception as e:
            logger.debug(f"Controllo aggiornamenti fallito: {e}")
            self.check_failed.emit(str(e))


def _show_update_dialog(parent_widget, current_version: str, new_version: str,
                        release_notes: str = "") -> None:
    """
    Mostra il dialogo di notifica aggiornamento con tre opzioni:
      - Scarica aggiornamento → apre la pagina releases nel browser
      - Salta questa versione → salva new_version in QSettings (non chiede più per questa release)
      - Ricordamelo dopo     → non fa nulla (chiede di nuovo al prossimo avvio)
    """
    try:
        from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QTextBrowser, QDialogButtonBox, QPushButton
        from PyQt6.QtCore import QUrl, Qt
        from PyQt6.QtGui import QDesktopServices
        from PyQt6.QtCore import QSettings
        from config import SETTINGS_UPDATE_SKIPPED_VER

        dlg = QDialog(parent_widget)
        dlg.setWindowTitle("Aggiornamento disponibile")
        dlg.setMinimumWidth(480)
        layout = QVBoxLayout(dlg)
        layout.setSpacing(12)

        lbl_header = QLabel(
            f"<b>È disponibile una nuova versione di Foliarium!</b><br>"
            f"Versione corrente: <b>{current_version}</b> &nbsp;→&nbsp; "
            f"Nuova versione: <b>{new_version}</b>"
        )
        lbl_header.setWordWrap(True)
        layout.addWidget(lbl_header)

        if release_notes:
            lbl_notes_title = QLabel("<b>Note di rilascio:</b>")
            layout.addWidget(lbl_notes_title)
            notes_browser = QTextBrowser()
            notes_browser.setPlainText(release_notes)
            notes_browser.setMaximumHeight(180)
            notes_browser.setReadOnly(True)
            layout.addWidget(notes_browser)

        btn_box = QDialogButtonBox()
        btn_download = QPushButton("Scarica aggiornamento")
        btn_skip    = QPushButton("Salta questa versione")
        btn_later   = QPushButton("Ricordamelo dopo")

        btn_box.addButton(btn_download, QDialogButtonBox.ButtonRole.AcceptRole)
        btn_box.addButton(btn_skip,    QDialogButtonBox.ButtonRole.ResetRole)
        btn_box.addButton(btn_later,   QDialogButtonBox.ButtonRole.RejectRole)
        layout.addWidget(btn_box)

        clicked = {"btn": None}

        def _on_download():
            clicked["btn"] = "download"
            dlg.accept()

        def _on_skip():
            clicked["btn"] = "skip"
            dlg.reject()

        def _on_later():
            clicked["btn"] = "later"
            dlg.reject()

        btn_download.clicked.connect(_on_download)
        btn_skip.clicked.connect(_on_skip)
        btn_later.clicked.connect(_on_later)

        dlg.exec()

        if clicked["btn"] == "download":
            QDesktopServices.openUrl(QUrl(RELEASES_PAGE_URL))
        elif clicked["btn"] == "skip":
            settings = QSettings()
            settings.setValue(SETTINGS_UPDATE_SKIPPED_VER, new_version)
            logger.info(f"Versione {new_version} contrassegnata come da saltare")

    except Exception as e:
        logger.warning(f"Impossibile mostrare dialogo aggiornamento: {e}")


def start_background_check(parent_widget, manual: bool = False) -> Optional[UpdateCheckerWorker]:
    """
    Avvia il controllo aggiornamenti in un thread separato.

    Args:
        parent_widget: widget padre (per il dialogo); usato anche come parent del QThread
        manual:        True se lanciato dall'utente (menu Help) — mostra sempre
                       il risultato, anche se "già aggiornato"; ignora skip e auto-check flag

    Returns:
        L'istanza UpdateCheckerWorker (il chiamante deve tenerla viva finché il thread finisce),
        oppure None se il check è stato saltato.
    """
    from config import APP_VERSION, IS_TEST_ENV, SETTINGS_UPDATE_AUTO_CHECK, SETTINGS_UPDATE_SKIPPED_VER
    from PyQt6.QtCore import QSettings

    if IS_TEST_ENV and not manual:
        return None

    settings = QSettings()

    # Se il controllo automatico è disabilitato e non è manuale, esci subito
    if not manual:
        auto_check = settings.value(SETTINGS_UPDATE_AUTO_CHECK, True, type=bool)
        if not auto_check:
            logger.debug("Controllo aggiornamenti automatico disabilitato")
            return None

    worker = UpdateCheckerWorker(APP_VERSION, parent=parent_widget)

    def _on_available(remote_version: str, release_notes: str):
        # Skip versione? (solo in automatico, non in manuale)
        if not manual:
            skipped = settings.value(SETTINGS_UPDATE_SKIPPED_VER, "", type=str)
            if skipped == remote_version:
                logger.debug(f"Versione {remote_version} saltata dall'utente")
                return
        _show_update_dialog(parent_widget, APP_VERSION, remote_version, release_notes)

    def _on_up_to_date():
        if manual:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.information(
                parent_widget,
                "Nessun aggiornamento",
                f"Foliarium è aggiornato alla versione <b>{APP_VERSION}</b>.",
            )

    def _on_failed(error_msg: str):
        if manual:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(
                parent_widget,
                "Controllo aggiornamenti",
                f"Impossibile verificare la disponibilità di aggiornamenti.\n\n{error_msg}",
            )

    worker.update_available.connect(_on_available)
    worker.up_to_date.connect(_on_up_to_date)
    worker.check_failed.connect(_on_failed)
    worker.start()
    return worker
