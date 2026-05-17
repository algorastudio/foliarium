"""
foliarium.ui.widgets.search — Widget di ricerca catastale.

Tre famiglie di ricerca, ognuna in un modulo dedicato:
    partite.py  — ricerca strutturata partite (worker, model, proxy, widget)
    immobili.py — ricerca avanzata immobili con filtri
    fuzzy.py    — ricerca fuzzy unificata cross-entita' (pg_trgm)

Estratto da search_widgets.py (Sprint 3 refactor — six-hats).
"""

from foliarium.ui.widgets.search.partite import (
    _PartiteFilterProxy,
    _PartiteSearchWorker,
    PartitaResultCard,
    PartiteTableModel,
    RicercaPartiteWidget,
)
from foliarium.ui.widgets.search.immobili import (
    ImmobiliSearchModel,
    RicercaAvanzataImmobiliWidget,
)
from foliarium.ui.widgets.search.fuzzy import (
    FuzzyResultsModel,
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
