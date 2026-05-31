"""
tests/unit/test_albero_genealogico_dialog_args.py
=================================================
Regressione per il bug "AttributeError: 'int' object has no attribute
'get_genealogia_partita'".

Causa originale: in foliarium/ui/widgets/search/partite.py::_apri_albero
il dialog AlberoGeneralogicoDialog veniva costruito con gli argomenti
invertiti — (db_manager, partita_id) invece di (partita_id, db_manager) —
perche' altri dialog del progetto usano l'ordine opposto.

Questo test blocca due cose:
1. La firma di AlberoGeneralogicoDialog resta (partita_id, db_manager, ...).
2. La guardia anti-scambio solleva TypeError chiaro se db_manager arriva
   come int.

Marker: gui (richiede QApplication, eseguito con QT_QPA_PLATFORM=offscreen).
"""
from __future__ import annotations

import inspect
import os
from datetime import date
from unittest.mock import MagicMock

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault(
    "FOLIARIUM_LICENSE_KEY",
    "deadbeefcafebabe0123456789abcdef0123456789abcdef0123456789abcdef",
)

pytestmark = [pytest.mark.unit, pytest.mark.gui]


@pytest.fixture(scope="module")
def qapp():
    from PyQt6.QtWidgets import QApplication
    import sys
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    return app


@pytest.fixture
def mock_db():
    db = MagicMock()
    db.get_genealogia_partita.return_value = {
        "partita": {
            "id": 92, "numero_partita": 92, "suffisso_partita": "",
            "tipo": "principale", "stato": "attiva",
            "data_impianto": date(1900, 1, 1), "data_chiusura": None,
            "comune_nome": "Genova", "possessori": "ROSSI MARIO",
            "tipo_variazione": None, "data_variazione": None,
            "nominativo_riferimento": None,
        },
        "predecessori": [],
        "successori": [],
    }
    return db


def test_signature_is_partita_id_first():
    """La firma deve restare (partita_id, db_manager, parent)."""
    from foliarium.ui.dialogs.partita.genealogia import AlberoGeneralogicoDialog
    params = list(inspect.signature(AlberoGeneralogicoDialog.__init__).parameters)
    # ['self', 'partita_id', 'db_manager', 'parent']
    assert params[1] == "partita_id"
    assert params[2] == "db_manager"


def test_correct_order_stores_manager(qapp, mock_db):
    """Con l'ordine corretto, self.db_manager espone get_genealogia_partita."""
    from foliarium.ui.dialogs.partita.genealogia import AlberoGeneralogicoDialog
    dlg = AlberoGeneralogicoDialog(92, mock_db)
    assert dlg.partita_id == 92
    assert dlg.db_manager is mock_db
    mock_db.get_genealogia_partita.assert_called_once_with(92)
    dlg.deleteLater()


def test_swapped_args_raise_typeerror(qapp, mock_db):
    """Se db_manager arriva come int (argomenti scambiati) -> TypeError chiaro."""
    from foliarium.ui.dialogs.partita.genealogia import AlberoGeneralogicoDialog
    with pytest.raises(TypeError, match="ordine argomenti"):
        # Scambio: db_manager prima, partita_id dopo (il bug originale)
        AlberoGeneralogicoDialog(mock_db, 92)


def test_apri_albero_callsite_uses_correct_order(qapp, mock_db):
    """Verifica che il call site corretto in search/partite.py non
    sollevi piu' l'AttributeError originale.

    Costruiamo il widget di ricerca con db mockato, impostiamo una
    partita selezionata e invochiamo _apri_albero: prima del fix
    sollevava 'int object has no attribute get_genealogia_partita'.
    """
    from foliarium.ui.widgets.search.partite import RicercaPartiteWidget

    w = RicercaPartiteWidget(mock_db)
    w._selected_partita_id = 92
    # Evitiamo che il dialog entri nell'event loop modale
    import foliarium.ui.dialogs.partita.genealogia as gmod
    orig_exec = gmod.AlberoGeneralogicoDialog.exec
    gmod.AlberoGeneralogicoDialog.exec = lambda self: 0
    try:
        # Non deve sollevare
        w._apri_albero()
    finally:
        gmod.AlberoGeneralogicoDialog.exec = orig_exec
        w.deleteLater()

    # Il dialog ha chiamato il metodo sul vero db_manager
    mock_db.get_genealogia_partita.assert_called_with(92)
