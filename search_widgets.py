"""
search_widgets.py — Facade di compatibilita'.

Le 10 classi di ricerca (3 famiglie: partite, immobili, fuzzy) sono state
spostate in foliarium/ui/widgets/search/ durante lo Sprint 3 del refactor
six-hats (era 1.841 LOC monolitico).

Questo modulo resta come re-export per non rompere i consumer storici:
    from search_widgets import RicercaPartiteWidget  # ok

I nuovi consumer dovrebbero preferire l'import diretto:
    from foliarium.ui.widgets.search import RicercaPartiteWidget
    # oppure ancora piu' specifico:
    from foliarium.ui.widgets.search.partite import RicercaPartiteWidget
"""

from foliarium.ui.widgets.search import (
    _PartiteFilterProxy,
    _PartiteSearchWorker,
    FuzzyResultsModel,
    ImmobiliSearchModel,
    PartitaResultCard,
    PartiteTableModel,
    RicercaAvanzataImmobiliWidget,
    RicercaPartiteWidget,
    UnifiedFuzzySearchThread,
    UnifiedFuzzySearchWidget,
)

__all__ = [
    "_PartiteSearchWorker",
    "_PartiteFilterProxy",
    "PartitaResultCard",
    "PartiteTableModel",
    "RicercaPartiteWidget",
    "ImmobiliSearchModel",
    "RicercaAvanzataImmobiliWidget",
    "FuzzyResultsModel",
    "UnifiedFuzzySearchThread",
    "UnifiedFuzzySearchWidget",
]
