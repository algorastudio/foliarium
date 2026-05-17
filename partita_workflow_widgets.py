"""
partita_workflow_widgets.py — Facade di compatibilita'.

Le 3 classi di workflow sono state spostate in foliarium/ui/widgets/workflow/
durante lo Sprint 3 del refactor six-hats (era 2.209 LOC monolitico).

Questo modulo resta come re-export per non rompere i consumer storici:
    from partita_workflow_widgets import RegistrazioneProprietaWidget  # ok

I nuovi consumer dovrebbero preferire l'import diretto:
    from foliarium.ui.widgets.workflow import RegistrazioneProprietaWidget
"""

from foliarium.ui.widgets.workflow import (
    NuovaPartitaWizardWidget,
    OperazioniPartitaWidget,
    RegistrazioneProprietaWidget,
)

__all__ = [
    "RegistrazioneProprietaWidget",
    "NuovaPartitaWizardWidget",
    "OperazioniPartitaWidget",
]
