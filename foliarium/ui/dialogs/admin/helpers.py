"""Helper di conversione date e gestione password."""
from __future__ import annotations

import logging
import os
import sys
from datetime import date
from typing import Optional, Dict, Any

from PyQt6.QtCore import (QDate, QSettings, Qt)
from PyQt6.QtGui import (QDesktopServices, QFont, QPixmap)
from PyQt6.QtPdf import QPdfDocument
from PyQt6.QtPdfWidgets import QPdfView
from PyQt6.QtWidgets import (QAbstractItemView, QApplication,
                             QCheckBox, QComboBox, QDialog,
                             QFileDialog, QFormLayout, QFrame, QGridLayout, QGroupBox,
                             QHBoxLayout, QHeaderView, QLabel, QLineEdit,
                             QMessageBox, QPushButton, QSpinBox, QStyle,
                             QSplitter, QTableWidget, QTableWidgetItem,
                             QTreeWidget, QTreeWidgetItem, QVBoxLayout,
                             QWidget, QTextBrowser, QDialogButtonBox,
                             QRadioButton, QGraphicsScene, QGraphicsView)
from PyQt6.QtGui import QPainter
from app_paths import get_resource_path, get_resource_path as resource_path, get_doc_path  # noqa: F401
from config import (
    SETTINGS_DB_TYPE, SETTINGS_DB_HOST, SETTINGS_DB_PORT,
    SETTINGS_DB_NAME, SETTINGS_DB_USER, SETTINGS_DB_SCHEMA, SETTINGS_DB_PASSWORD,
    SETTINGS_SMTP_ENABLED, SETTINGS_SMTP_HOST, SETTINGS_SMTP_PORT,
    SETTINGS_SMTP_USER, SETTINGS_SMTP_USE_TLS, SETTINGS_SMTP_FROM_ADDR,
    SETTINGS_EMAIL_ON_CREATE, SETTINGS_EMAIL_ON_PASSWD,
    SETTINGS_EMAIL_ON_ROLE, SETTINGS_EMAIL_ON_LOGIN,
    SETTINGS_LICENSE_FILE_PATH, SETTINGS_LICENSE_NETWORK_SHARE,
)
from catasto_db_manager import CatastoDBManager
from catasto_exceptions import DBMError, DBUniqueConstraintError, DBNotFoundError, DBDataError  # noqa: F401
from foliarium.ui.widgets.custom import QPasswordLineEdit, show_status_message as _show_status_message
from core.auth_manager import AuthManager as _AuthManager

try:
    import keyring
except ImportError:
    keyring = None

try:
    import markdown
except ImportError:
    markdown = None

try:
    import yaml
except ImportError:
    yaml = None


def qdate_to_datetime(q_date: QDate) -> Optional[date]:
    if q_date.isNull() or not q_date.isValid():  # Controlla anche isValid
        return None
    return date(q_date.year(), q_date.month(), q_date.day())


def datetime_to_qdate(dt_date: Optional[date]) -> QDate:
    if dt_date is None:
        return QDate()  # Restituisce una QDate "nulla"
    return QDate(dt_date.year, dt_date.month, dt_date.day)
def _validate_password_strength(password: str) -> tuple:
    """Verifica i requisiti minimi della password.
    Restituisce (True, '') se valida, oppure (False, messaggio_errore).
    Requisiti: almeno 8 caratteri, almeno 1 cifra.
    """
    if len(password) < 8:
        return False, "La password deve essere di almeno 8 caratteri."
    if not any(c.isdigit() for c in password):
        return False, "La password deve contenere almeno un numero."
    return True, ""


# Hash/verifica password: logica centralizzata in core.auth_manager (_AuthManager importato a riga 44)
def _hash_password(password: str) -> str:
    """Genera un hash sicuro per la password usando bcrypt."""
    return _AuthManager._hash_password(password)

def _verify_password(stored_hash: str, provided_password: str) -> bool:
    """Verifica se la password fornita corrisponde all'hash memorizzato."""
    return _AuthManager._verify_password(stored_hash, provided_password)


# ---------------------------------------------------------------------------
# Import comuni e località da CSV / ISTAT
# ---------------------------------------------------------------------------


# Estratto in import_dialogs.py — backward compat re-export




