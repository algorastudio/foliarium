"""Helper di conversione date e gestione password."""
from __future__ import annotations

from datetime import date
from typing import Optional

from PyQt6.QtCore import (QDate)
from app_paths import get_resource_path, get_resource_path as resource_path, get_doc_path  # noqa: F401
from catasto_exceptions import DBMError, DBUniqueConstraintError, DBNotFoundError, DBDataError  # noqa: F401
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
    """Verifica i requisiti della password (delega a FieldValidator, fonte unica).
    Restituisce (True, '') se valida, oppure (False, messaggio_errore).
    """
    from validators import FieldValidator
    result = FieldValidator.password_strength(password or "")
    return (result.is_valid, "" if result.is_valid else result.error_message)


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




