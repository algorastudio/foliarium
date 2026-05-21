"""
foliarium/ui/widgets/admin/ — Widget di amministrazione.

Package estratto dal modulo monolitico widgets/admin.py (2.300 LOC).
Suddiviso per dominio:
  utenti.py    — UtentiTableModel, GestioneUtentiWidget
  audit.py     — AuditLogTableModel, AuditLogViewerWidget
  backup.py    — BackupWidget
  archivio.py  — GenericRecordsModel, ArchivioWidget
  tabelle.py   — GestioneTipiLocalitaWidget, GestionePeriodiStoriciWidget,
                 TipiPossessoWidget, TabelleDiSistemaWidget

Questo __init__ re-esporta tutte le classi: gli import esistenti
(`from foliarium.ui.widgets.admin import ...`) restano invariati.
"""

from foliarium.ui.widgets.admin.utenti import (        # noqa: F401
    UtentiTableModel,
    GestioneUtentiWidget,
)
from foliarium.ui.widgets.admin.audit import (         # noqa: F401
    AuditLogTableModel,
    AuditLogViewerWidget,
)
from foliarium.ui.widgets.admin.backup import BackupWidget          # noqa: F401
from foliarium.ui.widgets.admin.archivio import (      # noqa: F401
    GenericRecordsModel,
    ArchivioWidget,
)
from foliarium.ui.widgets.admin.tabelle import (       # noqa: F401
    GestioneTipiLocalitaWidget,
    GestionePeriodiStoriciWidget,
    TipiPossessoWidget,
    TabelleDiSistemaWidget,
)

__all__ = [
    "UtentiTableModel",
    "GestioneUtentiWidget",
    "AuditLogTableModel",
    "AuditLogViewerWidget",
    "BackupWidget",
    "GenericRecordsModel",
    "ArchivioWidget",
    "GestioneTipiLocalitaWidget",
    "GestionePeriodiStoriciWidget",
    "TipiPossessoWidget",
    "TabelleDiSistemaWidget",
]
