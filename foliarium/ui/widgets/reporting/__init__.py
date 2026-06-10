"""
foliarium/ui/widgets/reporting/ — Widget di reportistica.

Package estratto dal modulo monolitico widgets/reporting.py (1.850 LOC).
Suddiviso per funzione:
  model.py         — SimpleRowsModel
  documenti.py     — RicercaDocumentiWidget
  esportazioni.py  — EsportazioniWidget
  reportistica.py  — ReportisticaWidget
  statistiche.py   — StatisticheWidget
  consultazione.py — RegistraConsultazioneWidget

Questo __init__ re-esporta tutte le classi: gli import esistenti
(`from foliarium.ui.widgets.reporting import ...`) restano invariati.
"""

from foliarium.ui.widgets.reporting.model import SimpleRowsModel             # noqa: F401
from foliarium.ui.widgets.reporting.documenti import RicercaDocumentiWidget  # noqa: F401
from foliarium.ui.widgets.reporting.esportazioni import EsportazioniWidget   # noqa: F401
from foliarium.ui.widgets.reporting.reportistica import ReportisticaWidget   # noqa: F401
from foliarium.ui.widgets.reporting.statistiche import StatisticheWidget     # noqa: F401
from foliarium.ui.widgets.reporting.consultazione import (                   # noqa: F401
    RegistraConsultazioneWidget,
)

__all__ = [
    "SimpleRowsModel",
    "RicercaDocumentiWidget",
    "EsportazioniWidget",
    "ReportisticaWidget",
    "StatisticheWidget",
    "RegistraConsultazioneWidget",
]
