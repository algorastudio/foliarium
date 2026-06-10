"""
foliarium/ui/dialogs/entity/ — Dialog su entita anagrafiche.

Package estratto dal modulo monolitico dialogs/entity.py (1.954 LOC).
Suddiviso per entita:
  possessore.py — DettagliLegamePossessoreDialog, ModificaPossessoreDialog,
                  CreatePossessoreDialog
  comune.py     — ModificaComuneDialog, PossessoriComuneDialog,
                  PartiteComuneDialog
  localita.py   — ModificaLocalitaDialog, CreateLocalitaDialog
  periodo.py    — PeriodoStoricoDetailsDialog, PeriodoStoricoEditDialog
  selezione.py  — ComuneSelectionDialog, PartitaSearchDialog,
                  LocalitaSelectionDialog

Questo __init__ re-esporta tutte le classi: gli import esistenti
(`from foliarium.ui.dialogs.entity import ...`) restano invariati.
"""

from foliarium.ui.dialogs.entity.possessore import (   # noqa: F401
    DettagliLegamePossessoreDialog,
    ModificaPossessoreDialog,
    CreatePossessoreDialog,
)
from foliarium.ui.dialogs.entity.comune import (        # noqa: F401
    ModificaComuneDialog,
    PossessoriComuneDialog,
    PartiteComuneDialog,
)
from foliarium.ui.dialogs.entity.localita import (      # noqa: F401
    ModificaLocalitaDialog,
    CreateLocalitaDialog,
)
from foliarium.ui.dialogs.entity.periodo import (       # noqa: F401
    PeriodoStoricoDetailsDialog,
    PeriodoStoricoEditDialog,
)
from foliarium.ui.dialogs.entity.selezione import (     # noqa: F401
    ComuneSelectionDialog,
    PartitaSearchDialog,
    LocalitaSelectionDialog,
)

__all__ = [
    "DettagliLegamePossessoreDialog",
    "ModificaPossessoreDialog",
    "CreatePossessoreDialog",
    "ModificaComuneDialog",
    "PossessoriComuneDialog",
    "PartiteComuneDialog",
    "ModificaLocalitaDialog",
    "CreateLocalitaDialog",
    "PeriodoStoricoDetailsDialog",
    "PeriodoStoricoEditDialog",
    "ComuneSelectionDialog",
    "PartitaSearchDialog",
    "LocalitaSelectionDialog",
]
