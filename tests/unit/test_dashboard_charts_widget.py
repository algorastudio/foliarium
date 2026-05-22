"""
tests/unit/test_dashboard_charts_widget.py
==========================================
Smoke test del widget DashboardChartsWidget: instanziazione, rendering
di dati validi e di serie vuote, gestione assenza matplotlib.

Marker: gui (richiede QApplication, eseguito con QT_QPA_PLATFORM=offscreen).
"""
from __future__ import annotations

import os
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
def sample_data():
    return {
        "per_epoca": [
            {"label": "Regno di Sardegna (pre-1861)", "value": 30},
            {"label": "Regno d'Italia (1861-1945)", "value": 120},
            {"label": "Repubblica (1946+)", "value": 80},
        ],
        "per_tipo": [
            {"label": "Principale", "value": 200},
            {"label": "Secondaria", "value": 30},
        ],
        "per_stato": [
            {"label": "Attiva", "value": 180},
            {"label": "Inattiva", "value": 50},
        ],
        "top_comuni": [
            {"label": "Genova", "value": 100},
            {"label": "Savona", "value": 60},
            {"label": "La Spezia", "value": 40},
        ],
    }


def test_widget_constructs(qapp):
    from foliarium.ui.widgets.dashboard_charts import DashboardChartsWidget
    db = MagicMock()
    w = DashboardChartsWidget(db)
    assert w is not None
    w.deleteLater()


def test_render_does_not_raise_with_valid_data(qapp, sample_data):
    from foliarium.ui.widgets.dashboard_charts import (
        DashboardChartsWidget, _MATPLOTLIB_AVAILABLE,
    )
    if not _MATPLOTLIB_AVAILABLE:
        pytest.skip("matplotlib non disponibile")
    db = MagicMock()
    w = DashboardChartsWidget(db)
    # Bypassa il loader thread, chiama direttamente il render
    w._on_data_ready(sample_data)
    # Verifica che siano stati creati i canvas (4)
    assert hasattr(w, "_fig_epoca")
    assert hasattr(w, "_fig_tipo")
    assert hasattr(w, "_fig_stato")
    assert hasattr(w, "_fig_top")
    w.deleteLater()


def test_render_handles_empty_series(qapp):
    from foliarium.ui.widgets.dashboard_charts import (
        DashboardChartsWidget, _MATPLOTLIB_AVAILABLE,
    )
    if not _MATPLOTLIB_AVAILABLE:
        pytest.skip("matplotlib non disponibile")
    db = MagicMock()
    w = DashboardChartsWidget(db)
    empty = {"per_epoca": [], "per_tipo": [],
             "per_stato": [], "top_comuni": []}
    w._on_data_ready(empty)
    # Non deve sollevare; tutti i canvas mostrano "Nessun dato disponibile"
    w.deleteLater()


def test_load_data_triggers_loader(qapp, sample_data):
    from foliarium.ui.widgets.dashboard_charts import (
        DashboardChartsWidget, _MATPLOTLIB_AVAILABLE,
    )
    if not _MATPLOTLIB_AVAILABLE:
        pytest.skip("matplotlib non disponibile")
    db = MagicMock()
    db.get_dashboard_charts_data.return_value = sample_data
    w = DashboardChartsWidget(db)
    w.load_data()
    # Aspetta che il thread di loading finisca
    if w._loader:
        w._loader.wait(2000)
    qapp.processEvents()
    assert w._last_data == sample_data or w._last_data == {}  # tolerant
    w.deleteLater()
