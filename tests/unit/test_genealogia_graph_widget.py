"""
tests/unit/test_genealogia_graph_widget.py
==========================================
Smoke test del GenealogiaGraphWidget: instanziazione, caricamento di
una partita, espansione di un nodo, gestione errori.

Marker: gui (richiede QApplication, eseguito con QT_QPA_PLATFORM=offscreen).
"""
from __future__ import annotations

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


def _partita(pid, numero, comune="Genova", stato="attiva",
             possessori="ROSSI MARIO", tipo_variazione=None,
             data_variazione=None):
    return {
        "id": pid,
        "numero_partita": numero,
        "suffisso_partita": "",
        "tipo": "principale",
        "stato": stato,
        "data_impianto": date(1900, 1, 1),
        "data_chiusura": None,
        "comune_nome": comune,
        "possessori": possessori,
        "tipo_variazione": tipo_variazione,
        "data_variazione": data_variazione,
        "nominativo_riferimento": None,
    }


@pytest.fixture
def mock_db():
    db = MagicMock()
    # Genealogia per partita 100: 2 predecessori, 2 successori
    genealogia_100 = {
        "partita": _partita(100, 100),
        "predecessori": [
            _partita(50, 50, tipo_variazione="Frazionamento",
                     data_variazione=date(1880, 3, 15)),
            _partita(51, 51, tipo_variazione="Vendita",
                     data_variazione=date(1882, 5, 1)),
        ],
        "successori": [
            _partita(200, 200, tipo_variazione="Successione",
                     data_variazione=date(1925, 7, 10)),
            _partita(201, 201, tipo_variazione="Donazione",
                     data_variazione=date(1928, 11, 20)),
        ],
    }
    # Genealogia espandibile per il successore 200
    genealogia_200 = {
        "partita": _partita(200, 200),
        "predecessori": [_partita(100, 100)],
        "successori": [
            _partita(300, 300, tipo_variazione="Vendita",
                     data_variazione=date(1950, 1, 1)),
        ],
    }
    # Genealogia vuota per i nodi foglia
    genealogia_default = {
        "partita": None,
        "predecessori": [],
        "successori": [],
    }

    def _get(pid):
        if pid == 100:
            return genealogia_100
        if pid == 200:
            return genealogia_200
        return {"partita": _partita(pid, pid), "predecessori": [], "successori": []}

    db.get_genealogia_partita.side_effect = _get
    return db


def test_widget_constructs(qapp, mock_db):
    from foliarium.ui.widgets.genealogia_graph import GenealogiaGraphWidget
    w = GenealogiaGraphWidget(mock_db)
    assert w is not None
    assert w.current_partita_id is None
    w.deleteLater()


def test_load_partita_populates_graph(qapp, mock_db):
    from foliarium.ui.widgets.genealogia_graph import GenealogiaGraphWidget
    w = GenealogiaGraphWidget(mock_db)
    w.load_partita(100)
    # 1 centrale + 2 predecessori + 2 successori = 5 nodi
    assert len(w._nodes) == 5
    # 2 edges per predecessori + 2 per successori = 4
    assert len(w._edges) == 4
    # Layers: -1 per predecessori, 0 centrale, +1 successori
    assert w._layers[100] == 0
    assert w._layers[50] == -1
    assert w._layers[200] == 1
    # Header aggiornato
    assert "Partita 100" in w.header_label.text()
    w.deleteLater()


def test_load_partita_handles_missing_data(qapp):
    from foliarium.ui.widgets.genealogia_graph import GenealogiaGraphWidget
    db = MagicMock()
    db.get_genealogia_partita.return_value = None
    w = GenealogiaGraphWidget(db)
    w.load_partita(999)
    assert len(w._nodes) == 0
    assert "Nessun dato" in w.header_label.text()
    w.deleteLater()


def test_load_partita_handles_db_error(qapp):
    from foliarium.ui.widgets.genealogia_graph import GenealogiaGraphWidget
    db = MagicMock()
    db.get_genealogia_partita.side_effect = Exception("DB giù")
    w = GenealogiaGraphWidget(db)
    w.load_partita(999)  # non deve sollevare
    assert "Errore" in w.header_label.text()
    w.deleteLater()


def test_expand_node_adds_descendants(qapp, mock_db):
    from foliarium.ui.widgets.genealogia_graph import GenealogiaGraphWidget
    w = GenealogiaGraphWidget(mock_db)
    w.load_partita(100)
    # Espandi il successore 200 → aggiunge la 300
    node_200 = w._nodes[200]
    w._expand_node(node_200)
    assert 300 in w._nodes
    assert w._layers[300] == 2  # layer +1 rispetto a 200
    assert node_200.is_expanded is True
    w.deleteLater()


def test_expand_all_walks_frontier(qapp, mock_db):
    from foliarium.ui.widgets.genealogia_graph import GenealogiaGraphWidget
    w = GenealogiaGraphWidget(mock_db)
    w.load_partita(100)
    initial_count = len(w._nodes)
    w.expand_all(max_depth=3)
    # Almeno la 300 (espandibile da 200) deve essere stata aggiunta
    assert len(w._nodes) > initial_count
    # Tutti i nodi devono risultare espansi
    assert all(n.is_expanded for n in w._nodes.values())
    w.deleteLater()


def test_central_node_is_marked(qapp, mock_db):
    from foliarium.ui.widgets.genealogia_graph import GenealogiaGraphWidget
    w = GenealogiaGraphWidget(mock_db)
    w.load_partita(100)
    assert w._nodes[100].is_central is True
    assert w._nodes[200].is_central is False
    w.deleteLater()


def test_no_duplicate_edges(qapp, mock_db):
    """Espandere lo stesso nodo due volte non deve duplicare gli archi."""
    from foliarium.ui.widgets.genealogia_graph import GenealogiaGraphWidget
    w = GenealogiaGraphWidget(mock_db)
    w.load_partita(100)
    n_edges_before = len(w._edges)
    # Forza re-integrazione manuale
    node_200 = w._nodes[200]
    node_200.is_expanded = False
    w._expand_node(node_200)
    # Le edge originali centrale↔200 non vengono duplicate
    new_edges = len(w._edges) - n_edges_before
    # 200 ha 1 successore 300 → 1 nuovo edge
    assert new_edges == 1
    w.deleteLater()
