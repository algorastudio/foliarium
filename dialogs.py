"""
dialogs.py — Facade di re-export per backward compatibility.

I dialog sono implementati in:
  - dialogs_admin.py    (admin, configurazione, sistema)
  - dialogs_partita.py  (partite catastali)
  - dialogs_entity.py   (possessori, comuni, località, periodi storici)
  - import_dialogs.py   (import CSV / ISTAT / OSM)

Questo modulo re-esporta tutte le classi e le funzioni helper
affinché gli import esistenti (`from dialogs import ...`) continuino
a funzionare senza modifiche.
"""

# --- dialogs_admin.py ---
from dialogs_admin import (                                     # noqa: F401
    DBConfigDialog,
    DocumentViewerDialog,
    CreateUserDialog,
    UserSelectionDialog,
    BackupReminderSettingsDialog,
    EulaDialog,
    SMTPSettingsDialog,
    HelpViewerDialog,
    LicenseDialog,
    qdate_to_datetime,
    datetime_to_qdate,
    _validate_password_strength,
    _hash_password,
    _verify_password,
)

# --- dialogs_partita.py ---
from dialogs_partita import (                                   # noqa: F401
    PartitaDetailsDialog,
    ModificaPartitaDialog,
    DuplicaPartitaOptionsDialog,
    ModificaImmobileDialog,
    PossessoreSelectionDialog,
    ImmobileDialog,
    AggiungiDocumentoDialog,
    AlberoGeneralogicoDialog,
    ConfrontoPartiteDialog,
)

# --- dialogs_entity.py ---
from dialogs_entity import (                                    # noqa: F401
    DettagliLegamePossessoreDialog,
    ModificaPossessoreDialog,
    ModificaComuneDialog,
    PossessoriComuneDialog,
    PartiteComuneDialog,
    ModificaLocalitaDialog,
    PeriodoStoricoDetailsDialog,
    ComuneSelectionDialog,
    PartitaSearchDialog,
    CreatePossessoreDialog,
    LocalitaSelectionDialog,
    PeriodoStoricoEditDialog,
)

# --- import_dialogs.py ---
from import_dialogs import (                                    # noqa: F401
    CSVImportResultDialog,
    ImportComuniDialog,
    ImportLocalitaDialog,
    ISTATDownloadWorker,
    OSMLocalitaWorker,
    _mostra_risultati_import,
    _popola_preview_tabella,
)
