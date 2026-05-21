"""
foliarium/ui/dialogs/partita/ — Dialog relativi alle partite catastali.

Package estratto dal modulo monolitico dialogs/partita.py (2.797 LOC).
Suddiviso per concetto:
  details.py     — PartitaDetailsDialog
  modifica.py    — ModificaPartitaDialog, DuplicaPartitaOptionsDialog
  immobili.py    — ModificaImmobileDialog, ImmobileDialog
  selezione.py   — PossessoreSelectionDialog
  documento.py   — AggiungiDocumentoDialog
  genealogia.py  — AlberoGeneralogicoDialog, ConfrontoPartiteDialog

Questo __init__ re-esporta tutte le classi: gli import esistenti
(`from foliarium.ui.dialogs.partita import ...`) restano invariati.
"""

from foliarium.ui.dialogs.partita.details import PartitaDetailsDialog        # noqa: F401
from foliarium.ui.dialogs.partita.modifica import (                          # noqa: F401
    ModificaPartitaDialog,
    DuplicaPartitaOptionsDialog,
)
from foliarium.ui.dialogs.partita.immobili import (                          # noqa: F401
    ModificaImmobileDialog,
    ImmobileDialog,
)
from foliarium.ui.dialogs.partita.selezione import PossessoreSelectionDialog  # noqa: F401
from foliarium.ui.dialogs.partita.documento import AggiungiDocumentoDialog    # noqa: F401
from foliarium.ui.dialogs.partita.genealogia import (                        # noqa: F401
    AlberoGeneralogicoDialog,
    ConfrontoPartiteDialog,
)

__all__ = [
    "PartitaDetailsDialog",
    "ModificaPartitaDialog",
    "DuplicaPartitaOptionsDialog",
    "ModificaImmobileDialog",
    "ImmobileDialog",
    "PossessoreSelectionDialog",
    "AggiungiDocumentoDialog",
    "AlberoGeneralogicoDialog",
    "ConfrontoPartiteDialog",
]
