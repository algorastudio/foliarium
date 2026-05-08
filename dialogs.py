"""
dialogs.py — Facade di re-export per backward compatibility.

I dialog sono implementati in:
  - foliarium/ui/dialogs/admin.py    (admin, configurazione, sistema)
  - foliarium/ui/dialogs/partita.py  (partite catastali)
  - foliarium/ui/dialogs/entity.py   (possessori, comuni, località, periodi storici)
  - foliarium/ui/dialogs/import_.py  (import CSV / ISTAT / OSM)

Questo modulo re-esporta tutte le classi e le funzioni helper
affinché gli import esistenti (`from dialogs import ...`) continuino
a funzionare senza modifiche.
"""

# --- foliarium/ui/dialogs/admin.py ---
from foliarium.ui.dialogs.admin import (                        # noqa: F401
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

# --- foliarium/ui/dialogs/partita.py ---
from foliarium.ui.dialogs.partita import (                      # noqa: F401
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

# --- foliarium/ui/dialogs/entity.py ---
from foliarium.ui.dialogs.entity import (                       # noqa: F401
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

# --- foliarium/ui/dialogs/import_.py ---
from foliarium.ui.dialogs.import_ import (                      # noqa: F401
    CSVImportResultDialog,
    ImportComuniDialog,
    ImportLocalitaDialog,
    ISTATDownloadWorker,
    OSMLocalitaWorker,
    _mostra_risultati_import,
    _popola_preview_tabella,
)
