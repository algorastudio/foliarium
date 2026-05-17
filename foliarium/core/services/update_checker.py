"""
update_checker.py — Verifica e download aggiornamenti Foliarium tramite GitHub Releases API

Flusso:
  1. check_for_updates(parent)  — controlla la versione più recente su GitHub
  2. Se disponibile → mostra UpdateAvailableDialog
  3. L'utente clicca "Scarica e installa" → apre UpdateDownloadDialog (QThread)
  4. Il download avanza con progress bar; al termine verifica SHA-256 se disponibile
  5. Lancia l'installer Inno Setup (/SILENT /CLOSEAPPLICATIONS) e chiude l'app
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
from typing import Optional

logger = logging.getLogger("CatastoGUI")

GITHUB_API_URL    = "https://api.github.com/repos/algorastudio/foliarium/releases/latest"
RELEASES_PAGE_URL = "https://github.com/algorastudio/foliarium/releases"

# Nome dell'asset Windows nell'elenco della release (Inno Setup installer)
_ASSET_INSTALLER_SUFFIX = "_Setup.exe"
_ASSET_PORTABLE_SUFFIX  = "_Portabile.zip"
# Nome file checksum opzionale pubblicato insieme all'installer
_CHECKSUM_SUFFIX        = ".sha256"


# ---------------------------------------------------------------------------
# Parsing versione
# ---------------------------------------------------------------------------

def _parse_version(v: str) -> tuple:
    """Converte '1.5.3' o 'v1.5.3' in (1, 5, 3)."""
    v = v.lstrip("v")
    try:
        return tuple(int(x) for x in v.split(".")[:3])
    except (ValueError, AttributeError):
        return (0, 0, 0)


# ---------------------------------------------------------------------------
# Recupera info release da GitHub
# ---------------------------------------------------------------------------

def _fetch_release_info(timeout: int = 5) -> Optional[dict]:
    """Chiama GitHub API e restituisce il dict JSON della release più recente."""
    from config import APP_VERSION
    try:
        req = urllib.request.Request(
            GITHUB_API_URL,
            headers={
                "User-Agent": f"Foliarium/{APP_VERSION}",
                "Accept":     "application/vnd.github.v3+json",
            }
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.URLError:
        logger.debug("Controllo aggiornamenti: GitHub non raggiungibile")
        return None
    except Exception as e:
        logger.debug(f"Controllo aggiornamenti: {e}")
        return None


def _find_asset(assets: list, suffix: str) -> Optional[dict]:
    """Trova il primo asset il cui nome termina con *suffix*."""
    for a in assets:
        if a.get("name", "").endswith(suffix):
            return a
    return None


# ---------------------------------------------------------------------------
# Verifica SHA-256
# ---------------------------------------------------------------------------

def _verify_sha256(file_path: str, expected_hex: str) -> bool:
    """Verifica l'hash SHA-256 di un file scaricato."""
    h = hashlib.sha256()
    try:
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
        return h.hexdigest().lower() == expected_hex.lower().split()[0]
    except Exception as e:
        logger.warning(f"Verifica SHA-256 fallita: {e}")
        return False


def _fetch_checksum(checksum_url: str, timeout: int = 5) -> Optional[str]:
    """Scarica il file .sha256 e restituisce l'hash atteso."""
    try:
        with urllib.request.urlopen(checksum_url, timeout=timeout) as resp:
            return resp.read().decode("utf-8").strip()
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Worker QThread per il download
# ---------------------------------------------------------------------------

def _make_download_worker_class():
    """Crea la classe DownloadWorker solo quando Qt è disponibile."""
    from PyQt6.QtCore import QThread, pyqtSignal

    class DownloadWorker(QThread):
        """Scarica un file in background e aggiorna il progresso."""

        progress   = pyqtSignal(int)         # 0-100
        finished   = pyqtSignal(str)         # percorso file scaricato
        error      = pyqtSignal(str)         # messaggio di errore

        def __init__(self, url: str, dest_path: str, checksum_url: Optional[str] = None):
            super().__init__()
            self.url          = url
            self.dest_path    = dest_path
            self.checksum_url = checksum_url
            self._cancelled   = False

        def cancel(self):
            self._cancelled = True

        def run(self):
            try:
                req = urllib.request.Request(
                    self.url,
                    headers={"User-Agent": "Foliarium-Updater/1.0"}
                )
                with urllib.request.urlopen(req, timeout=30) as resp:
                    total = int(resp.headers.get("Content-Length", 0))
                    downloaded = 0
                    with open(self.dest_path, "wb") as f:
                        while True:
                            if self._cancelled:
                                self.error.emit("Download annullato dall'utente")
                                return
                            chunk = resp.read(65536)
                            if not chunk:
                                break
                            f.write(chunk)
                            downloaded += len(chunk)
                            if total > 0:
                                self.progress.emit(int(downloaded * 100 / total))
                            else:
                                self.progress.emit(-1)  # indeterminato

                # Verifica checksum opzionale
                if self.checksum_url:
                    expected = _fetch_checksum(self.checksum_url)
                    if expected and not _verify_sha256(self.dest_path, expected):
                        os.unlink(self.dest_path)
                        self.error.emit(
                            "Verifica integrità fallita (checksum SHA-256 non corrispondente).\n"
                            "Il file potrebbe essere corrotto. Riprova."
                        )
                        return

                self.finished.emit(self.dest_path)

            except Exception as e:
                self.error.emit(f"Errore durante il download:\n{e}")

    return DownloadWorker


# ---------------------------------------------------------------------------
# Lancia installer
# ---------------------------------------------------------------------------

def _launch_installer(installer_path: str) -> None:
    """
    Lancia l'installer Inno Setup in modalità silenziosa con
    /CLOSEAPPLICATIONS per chiudere Foliarium prima dell'installazione.
    Poi termina il processo corrente.
    """
    try:
        flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
        subprocess.Popen(
            [installer_path, "/SILENT", "/CLOSEAPPLICATIONS", "/RESTARTAPPLICATIONS"],
            creationflags=flags,
            close_fds=True,
        )
        logger.info(f"Installer avviato: {installer_path}")
    except Exception as e:
        logger.error(f"Impossibile avviare l'installer: {e}")
        raise

    # Chiudi l'app corrente
    from PyQt6.QtWidgets import QApplication
    QApplication.quit()


# ---------------------------------------------------------------------------
# API pubblica
# ---------------------------------------------------------------------------

def check_for_updates(parent_widget) -> bool:
    """
    Controlla se esiste una versione più recente su GitHub Releases.
    Mostra UpdateAvailableDialog se disponibile.

    Returns True se aggiornamento disponibile.
    """
    from config import APP_VERSION, IS_TEST_ENV, IS_DEMO_MODE

    if IS_TEST_ENV or IS_DEMO_MODE:
        return False

    data = _fetch_release_info()
    if not data:
        return False

    remote_tag     = data.get("tag_name", "")
    remote_version = _parse_version(remote_tag)
    local_version  = _parse_version(APP_VERSION)

    if remote_version <= local_version:
        logger.debug(f"Versione aggiornata: {APP_VERSION}")
        return False

    remote_str = remote_tag.lstrip("v")
    logger.info(f"Aggiornamento disponibile: {remote_str} (locale: {APP_VERSION})")
    _show_update_available_dialog(parent_widget, APP_VERSION, remote_str, data)
    return True


def _show_update_available_dialog(parent_widget, current_version: str,
                                   new_version: str, release_data: dict) -> None:
    """Mostra il dialogo 'Aggiornamento disponibile' con opzione di download automatico."""
    try:
        from PyQt6.QtWidgets import QMessageBox
        from PyQt6.QtCore import QUrl
        from PyQt6.QtGui import QDesktopServices

        assets     = release_data.get("assets", [])
        installer  = _find_asset(assets, _ASSET_INSTALLER_SUFFIX)
        release_notes = release_data.get("body", "").strip()

        msg = QMessageBox(parent_widget)
        msg.setWindowTitle("Aggiornamento disponibile")
        msg.setIcon(QMessageBox.Icon.Information)

        body = (
            f"<b>È disponibile una nuova versione di Foliarium!</b><br><br>"
            f"Versione corrente: <b>{current_version}</b><br>"
            f"Nuova versione: &nbsp;&nbsp;&nbsp;<b>{new_version}</b>"
        )
        if release_notes:
            # Mostra solo le prime 3 righe delle note di rilascio
            lines = [l for l in release_notes.splitlines() if l.strip()][:3]
            body += "<br><br><i>" + "<br>".join(lines) + "</i>"
        msg.setText(body)

        btn_auto = None
        if installer:
            btn_auto = msg.addButton(
                "Scarica e installa automaticamente",
                QMessageBox.ButtonRole.AcceptRole
            )
        btn_manual = msg.addButton(
            "Apri pagina download",
            QMessageBox.ButtonRole.ActionRole
        )
        msg.addButton("Ricordamelo dopo", QMessageBox.ButtonRole.RejectRole)

        msg.exec()

        clicked = msg.clickedButton()
        if btn_auto and clicked == btn_auto:
            _start_auto_download(parent_widget, installer, assets, new_version)
        elif clicked == btn_manual:
            QDesktopServices.openUrl(QUrl(RELEASES_PAGE_URL))

    except Exception as e:
        logger.warning(f"Impossibile mostrare il dialogo aggiornamento: {e}")


def _start_auto_download(parent_widget, installer_asset: dict,
                          all_assets: list, new_version: str) -> None:
    """Apre il dialog di download progress e avvia il QThread."""
    try:
        from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QLabel,
                                      QProgressBar, QPushButton, QHBoxLayout,
                                      QMessageBox)
        from PyQt6.QtCore import Qt

        DownloadWorker = _make_download_worker_class()

        download_url  = installer_asset.get("browser_download_url", "")
        asset_name    = installer_asset.get("name", f"Foliarium_{new_version}_Setup.exe")

        # Cerca il file checksum associato
        checksum_asset = _find_asset(all_assets, asset_name + _CHECKSUM_SUFFIX)
        checksum_url   = checksum_asset.get("browser_download_url") if checksum_asset else None

        # File destinazione nella cartella temp
        dest_path = os.path.join(tempfile.gettempdir(), asset_name)

        dlg = QDialog(parent_widget)
        dlg.setWindowTitle(f"Download aggiornamento v{new_version}")
        dlg.setMinimumWidth(420)
        dlg.setWindowFlag(Qt.WindowType.WindowCloseButtonHint, False)

        layout = QVBoxLayout(dlg)
        lbl_status = QLabel(f"Download in corso: {asset_name}")
        lbl_status.setWordWrap(True)
        layout.addWidget(lbl_status)

        progress_bar = QProgressBar()
        progress_bar.setRange(0, 100)
        layout.addWidget(progress_bar)

        lbl_info = QLabel("Attendere prego…")
        lbl_info.setProperty("status", "pending")
        layout.addWidget(lbl_info)

        btn_layout = QHBoxLayout()
        btn_cancel = QPushButton("Annulla")
        btn_layout.addStretch()
        btn_layout.addWidget(btn_cancel)
        layout.addLayout(btn_layout)

        worker = DownloadWorker(download_url, dest_path, checksum_url)

        def on_progress(pct: int):
            if pct < 0:
                progress_bar.setRange(0, 0)
                lbl_info.setText("Download in corso…")
            else:
                progress_bar.setRange(0, 100)
                progress_bar.setValue(pct)
                lbl_info.setText(f"{pct}% completato")

        def on_finished(path: str):
            btn_cancel.setText("Chiudi")
            lbl_status.setText(f"Download completato.\nAvvio dell'installazione…")
            lbl_info.setText(path)
            try:
                _launch_installer(path)
                dlg.accept()
            except Exception as e:
                QMessageBox.critical(
                    dlg, "Errore installazione",
                    f"Impossibile avviare l'installer:\n{e}\n\n"
                    f"File scaricato in:\n{path}"
                )
                dlg.accept()

        def on_error(msg: str):
            btn_cancel.setText("Chiudi")
            progress_bar.setRange(0, 100)
            progress_bar.setValue(0)
            lbl_status.setText("Download fallito")
            lbl_info.setText(msg)
            lbl_info.setProperty("status", "error")
            lbl_info.style().unpolish(lbl_info)
            lbl_info.style().polish(lbl_info)

        def on_cancel():
            if worker.isRunning():
                worker.cancel()
                worker.wait(3000)
            dlg.reject()

        worker.progress.connect(on_progress)
        worker.finished.connect(on_finished)
        worker.error.connect(on_error)
        btn_cancel.clicked.connect(on_cancel)

        worker.start()
        dlg.exec()

    except Exception as e:
        logger.error(f"_start_auto_download: {e}", exc_info=True)
