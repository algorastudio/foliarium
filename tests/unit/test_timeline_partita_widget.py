"""
tests/unit/test_timeline_partita_widget.py
==========================================
Smoke test del TimelinePartitaWidget: instanziazione, popolamento,
ordinamento cronologico/inverso, gestione lista vuota.

Marker: gui (richiede QApplication, eseguito con QT_QPA_PLATFORM=offscreen).
"""
from __future__ import annotations

import os
from datetime import date

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
def sample_variazioni():
    return [
        {
            "id": 1, "tipo": "Frazionamento",
            "data_variazione": date(1900, 3, 15),
            "partita_origine_id": 42, "partita_destinazione_id": 145,
            "origine_numero_partita": 42, "origine_comune_nome": "Genova",
            "destinazione_numero_partita": 145, "destinazione_comune_nome": "Genova",
            "tipo_contratto": "Atto pubblico",
            "data_contratto": date(1900, 3, 12),
            "notaio": "Giovanni Rossi", "repertorio": "1234",
            "contratto_note": None,
        },
        {
            "id": 2, "tipo": "Vendita",
            "data_variazione": date(1923, 5, 3),
            "partita_origine_id": 145, "partita_destinazione_id": 280,
            "origine_numero_partita": 145, "origine_comune_nome": "Genova",
            "destinazione_numero_partita": 280, "destinazione_comune_nome": "Genova",
            "tipo_contratto": "Compravendita",
            "data_contratto": date(1923, 5, 1),
            "notaio": "Maria Bianchi", "repertorio": "5678",
            "contratto_note": "Vendita parziale",
        },
        {
            "id": 3, "tipo": "Successione",
            "data_variazione": date(1955, 11, 20),
            "partita_origine_id": 280, "partita_destinazione_id": 410,
            "origine_numero_partita": 280, "origine_comune_nome": "Genova",
            "destinazione_numero_partita": 410, "destinazione_comune_nome": "Genova",
            "tipo_contratto": None, "data_contratto": None,
            "notaio": None, "repertorio": None, "contratto_note": None,
        },
    ]


def test_widget_constructs_empty(qapp):
    from foliarium.ui.widgets.timeline_partita import TimelinePartitaWidget
    w = TimelinePartitaWidget(variazioni=[])
    assert w is not None
    assert "Nessuna variazione" in w._count_label.text()
    w.deleteLater()


def test_widget_populates_entries(qapp, sample_variazioni):
    from foliarium.ui.widgets.timeline_partita import (
        TimelinePartitaWidget, _TimelineEntry,
    )
    w = TimelinePartitaWidget(
        variazioni=sample_variazioni, current_partita_id=145)
    # Conteggio entry (escluso lo stretch finale)
    entries = [
        w._container_layout.itemAt(i).widget()
        for i in range(w._container_layout.count() - 1)
    ]
    entries = [e for e in entries if isinstance(e, _TimelineEntry)]
    assert len(entries) == 3
    w.deleteLater()


def test_chronological_order(qapp, sample_variazioni):
    """Default: ordine cronologico (più vecchia in cima)."""
    from foliarium.ui.widgets.timeline_partita import (
        TimelinePartitaWidget, _TimelineEntry,
    )
    w = TimelinePartitaWidget(variazioni=sample_variazioni)
    entries = [
        w._container_layout.itemAt(i).widget()
        for i in range(w._container_layout.count() - 1)
    ]
    entries = [e for e in entries if isinstance(e, _TimelineEntry)]
    assert entries[0].variazione["id"] == 1   # 1900
    assert entries[1].variazione["id"] == 2   # 1923
    assert entries[2].variazione["id"] == 3   # 1955
    # is_first / is_last sono coerenti
    assert entries[0].is_first is True
    assert entries[-1].is_last is True
    w.deleteLater()


def test_toggle_order_reverses(qapp, sample_variazioni):
    from foliarium.ui.widgets.timeline_partita import (
        TimelinePartitaWidget, _TimelineEntry,
    )
    w = TimelinePartitaWidget(variazioni=sample_variazioni)
    w._toggle_order()
    entries = [
        w._container_layout.itemAt(i).widget()
        for i in range(w._container_layout.count() - 1)
    ]
    entries = [e for e in entries if isinstance(e, _TimelineEntry)]
    assert entries[0].variazione["id"] == 3   # 1955 più recente in cima
    assert entries[-1].variazione["id"] == 1
    w.deleteLater()


def test_current_partita_highlighted(qapp, sample_variazioni):
    """La partita corrente compare in <b>...</b> nella descrizione."""
    from foliarium.ui.widgets.timeline_partita import (
        TimelinePartitaWidget, _TimelineEntry,
    )
    w = TimelinePartitaWidget(
        variazioni=sample_variazioni, current_partita_id=145)
    entries = [
        w._container_layout.itemAt(i).widget()
        for i in range(w._container_layout.count() - 1)
    ]
    entries = [e for e in entries if isinstance(e, _TimelineEntry)]
    # La var #1 ha la 145 come destinazione (deve essere bold)
    flow1 = entries[0]._flow_description()
    assert "<b>Partita N.145" in flow1
    # La var #2 ha la 145 come origine (deve essere bold)
    flow2 = entries[1]._flow_description()
    assert "<b>Partita N.145" in flow2
    w.deleteLater()


def test_entry_with_contract_has_toggle(qapp, sample_variazioni):
    from foliarium.ui.widgets.timeline_partita import (
        TimelinePartitaWidget, _TimelineEntry,
    )
    w = TimelinePartitaWidget(variazioni=sample_variazioni)
    entries = [
        w._container_layout.itemAt(i).widget()
        for i in range(w._container_layout.count() - 1)
    ]
    entries = [e for e in entries if isinstance(e, _TimelineEntry)]
    # Variazione #1 ha contratto → toggle button presente
    assert hasattr(entries[0], "_toggle_btn")
    # Variazione #3 non ha contratto/note/repertorio → no toggle
    assert not hasattr(entries[2], "_toggle_btn")
    w.deleteLater()


def test_handles_iso_string_dates(qapp):
    """Le date possono arrivare come stringhe ISO; non deve crashare."""
    from foliarium.ui.widgets.timeline_partita import TimelinePartitaWidget
    variazioni = [
        {"id": 1, "tipo": "Vendita", "data_variazione": "1900-03-15"},
        {"id": 2, "tipo": "Successione", "data_variazione": "1955-11-20"},
    ]
    w = TimelinePartitaWidget(variazioni=variazioni)
    # Deve essere ordinata correttamente nonostante le stringhe
    assert "2 variazioni" in w._count_label.text()
    w.deleteLater()
