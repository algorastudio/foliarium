"""foliarium/core/services/audit_retention.py — Retention dei log di audit.

I log di audit non devono essere conservati indefinitamente: la retention va
limitata al tempo necessario alle finalità (sicurezza, tracciabilità) — un
principio di minimizzazione coerente con il GDPR.

La policy è un numero di giorni di conservazione persistito in ``QSettings``
(chiave ``config.SETTINGS_AUDIT_RETENTION_DAYS``). ``0`` = retention disattivata.
All'avvio l'applicazione applica la policy eliminando i log più vecchi.

Le funzioni che leggono/scrivono ``QSettings`` accettano un'istanza opzionale
(iniettabile nei test); l'import di Qt è lazy così il modulo resta importabile
anche in ambienti headless.
"""
from __future__ import annotations

import logging
from typing import Optional

logger = logging.getLogger("CatastoGUI.audit_retention")

#: Chiave QSettings della policy di retention (allineata a
#: ``config.SETTINGS_AUDIT_RETENTION_DAYS``).
RETENTION_DAYS_KEY = "Audit/RetentionDays"


def _settings():
    from PyQt6.QtCore import QSettings
    return QSettings()


def get_retention_days(settings=None) -> int:
    """Giorni di conservazione configurati (0 = retention disattivata)."""
    s = settings if settings is not None else _settings()
    try:
        days = int(s.value(RETENTION_DAYS_KEY, 0, type=int))
    except Exception:
        return 0
    return days if days > 0 else 0


def set_retention_days(days: int, settings=None) -> None:
    """Imposta la policy di retention (giorni). Valori <= 0 la disattivano."""
    s = settings if settings is not None else _settings()
    s.setValue(RETENTION_DAYS_KEY, max(0, int(days)))


def apply_retention(db_manager, days: int) -> Optional[int]:
    """Applica la retention: elimina i log più vecchi di ``days`` giorni.

    Returns:
        Il numero di record eliminati, oppure ``None`` se la retention è
        disattivata (``days <= 0``) o si verifica un errore (best-effort).
    """
    if not days or days <= 0:
        return None
    try:
        deleted = db_manager.cleanup_audit_logs(int(days))
        logger.info("Retention audit applicata: eliminati %s record oltre %s giorni.",
                    deleted, days)
        return deleted
    except Exception as e:
        logger.warning("Retention audit non applicata: %s", e)
        return None


def run_startup_retention(db_manager, settings=None) -> Optional[int]:
    """Legge la policy da QSettings e la applica all'avvio (best-effort)."""
    days = get_retention_days(settings)
    if days <= 0:
        return None
    return apply_retention(db_manager, days)


__all__ = [
    "get_retention_days", "set_retention_days",
    "apply_retention", "run_startup_retention",
]
