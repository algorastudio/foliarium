"""
update_checker.py — Verifica aggiornamenti Foliarium tramite GitHub Releases API
"""
import json
import logging
import urllib.request
import urllib.error
from typing import Optional

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


def check_for_updates(parent_widget) -> bool:
    """
    Controlla se esiste una versione più recente su GitHub Releases.
    Mostra un QMessageBox se disponibile.

    Args:
        parent_widget: Widget padre per il QMessageBox (può essere None)

    Returns:
        True se aggiornamento disponibile, False altrimenti
    """
    from config import APP_VERSION, IS_TEST_ENV

    if IS_TEST_ENV:
        return False

    try:
        req = urllib.request.Request(
            GITHUB_API_URL,
            headers={
                "User-Agent": f"Foliarium/{APP_VERSION}",
                "Accept": "application/vnd.github.v3+json",
            }
        )
        with urllib.request.urlopen(req, timeout=3) as response:
            data = json.loads(response.read().decode("utf-8"))

        remote_tag = data.get("tag_name", "")
        remote_version = _parse_version(remote_tag)
        local_version = _parse_version(APP_VERSION)

        if remote_version > local_version:
            remote_str = remote_tag.lstrip("v")
            logger.info(f"Aggiornamento disponibile: {remote_str} (locale: {APP_VERSION})")
            _show_update_dialog(parent_widget, APP_VERSION, remote_str)
            return True

        logger.debug(f"Versione aggiornata: {APP_VERSION}")
        return False

    except urllib.error.URLError:
        logger.debug("Controllo aggiornamenti: impossibile raggiungere GitHub (nessuna connessione)")
        return False
    except Exception as e:
        logger.debug(f"Controllo aggiornamenti fallito: {e}")
        return False


def _show_update_dialog(parent_widget, current_version: str, new_version: str) -> None:
    """Mostra il dialogo di notifica aggiornamento."""
    try:
        from PyQt6.QtWidgets import QMessageBox, QPushButton
        from PyQt6.QtCore import QUrl
        from PyQt6.QtGui import QDesktopServices

        msg = QMessageBox(parent_widget)
        msg.setWindowTitle("Aggiornamento disponibile")
        msg.setIcon(QMessageBox.Icon.Information)
        msg.setText(
            f"<b>È disponibile una nuova versione di Foliarium!</b><br><br>"
            f"Versione corrente: <b>{current_version}</b><br>"
            f"Nuova versione: <b>{new_version}</b>"
        )
        msg.setInformativeText(
            "Visita la pagina delle release per scaricare l'aggiornamento."
        )

        btn_download = msg.addButton("Scarica aggiornamento", QMessageBox.ButtonRole.AcceptRole)
        msg.addButton("Ricordamelo dopo", QMessageBox.ButtonRole.RejectRole)

        msg.exec()

        if msg.clickedButton() == btn_download:
            QDesktopServices.openUrl(QUrl(RELEASES_PAGE_URL))

    except Exception as e:
        logger.warning(f"Impossibile mostrare dialogo aggiornamento: {e}")
