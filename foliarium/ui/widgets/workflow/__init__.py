"""
foliarium.ui.widgets.workflow — Workflow operativi sulle partite.

Contiene i 3 widget principali di workflow, estratti da
partita_workflow_widgets.py (Sprint 3 refactor — six-hats).
"""

from foliarium.ui.widgets.workflow.registrazione_proprieta import (
    RegistrazioneProprietaWidget,
)
from foliarium.ui.widgets.workflow.nuova_partita_wizard import (
    NuovaPartitaWizardWidget,
)
from foliarium.ui.widgets.workflow.operazioni_partita import (
    OperazioniPartitaWidget,
)

__all__ = [
    "RegistrazioneProprietaWidget",
    "NuovaPartitaWizardWidget",
    "OperazioniPartitaWidget",
]
