"""
tests/integration/test_gui_smoke.py
====================================
Smoke test minimali per i widget GUI estratti nello Sprint 3.8.

Scope: verifica che ogni widget possa essere ISTANZIATO senza errori
con un db_manager mockato, e che i suoi attributi principali siano
presenti. NON testa comportamento utente (per quello serve pytest-qt
con interazione: keyClicks, mouseClick, ecc.).

Motivazione (six-hats analisi Sprint 3.9, opzione 2):
- Gli unit test attuali coprono il DB layer (db/*, foliarium/core/services/*)
- I widget GUI estratti (foliarium/ui/widgets/comuni.py, dashboard.py,
  welcome.py, e gli altri) hanno coverage 0-15% perche' richiedono
  istanziazione Qt
- Questi smoke test colmano il buco senza richiedere DB live o display

Uso:
    QT_QPA_PLATFORM=offscreen pytest tests/integration/test_gui_smoke.py

Dipendenze: pytest-qt (vedi tests/requirements-test.txt).
"""

from __future__ import annotations

import logging
from unittest.mock import MagicMock

import pytest


# Guard PyQt6: se manca, l'intero modulo viene saltato pulito
try:
    from PyQt6.QtCore import Qt  # noqa: F401
    _QT_OK = True
except ImportError:
    _QT_OK = False


pytestmark = [
    pytest.mark.integration,
    pytest.mark.gui,
    pytest.mark.skipif(not _QT_OK, reason="PyQt6 non disponibile"),
]


# ---------------------------------------------------------------------------
# Fixture: db_manager mock conforme a DBManagerProtocol
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_db():
    """Mock di CatastoDBManager. Restituisce dati vuoti su tutti i metodi
    di query usati dai widget all'init / al primo show.

    NON serve coprire l'API completa: solo i metodi che i widget chiamano
    nell'__init__ o nel primo refresh. Aggiungere altri side_effect quando
    si testa un widget che ne tocca di nuovi.
    """
    db = MagicMock()

    # Comuni / partite (ElencoComuniWidget, DashboardWidget loader)
    db.get_all_comuni_details.return_value = []
    db.get_dashboard_stats.return_value = {
        "total_comuni": 0, "total_partite": 0,
        "total_possessori": 0, "total_immobili": 0,
    }
    db.get_recent_session_logs.return_value = []
    db.get_ultimi_inserimenti_dashboard.return_value = {
        "comuni": [], "partite": [], "possessori": [],
    }

    # Logger / schema (per metodi che li toccano)
    db.logger = logging.getLogger("test_gui_smoke")
    db.schema = "catasto"
    return db


# ---------------------------------------------------------------------------
# WelcomeScreen — EULA splash (foliarium/ui/widgets/welcome.py)
# ---------------------------------------------------------------------------

class TestWelcomeScreenSmoke:
    """WelcomeScreen non riceve db_manager; richiede solo qapp + resources."""

    def test_can_instantiate(self, qtbot):
        from foliarium.ui.widgets.welcome import WelcomeScreen
        widget = WelcomeScreen(parent=None)
        qtbot.addWidget(widget)
        assert widget is not None
        # Layout split: branding sx + EULA dx
        assert widget.minimumWidth() >= 900
        # Checkbox + bottoni esistono e hanno stato iniziale corretto
        assert widget.accept_cb is not None
        assert widget.accept_cb.isChecked() is False
        assert widget.continue_btn.isEnabled() is False  # disabilitato finche' non spunta EULA

    def test_continue_button_enables_on_accept(self, qtbot):
        from foliarium.ui.widgets.welcome import WelcomeScreen
        widget = WelcomeScreen(parent=None)
        qtbot.addWidget(widget)
        # Click sulla checkbox → continue diventa enabled
        widget.accept_cb.setChecked(True)
        assert widget.continue_btn.isEnabled() is True
        widget.accept_cb.setChecked(False)
        assert widget.continue_btn.isEnabled() is False


# ---------------------------------------------------------------------------
# ElencoComuniWidget — vista lista comuni (foliarium/ui/widgets/comuni.py)
# ---------------------------------------------------------------------------

class TestElencoComuniWidgetSmoke:

    def test_can_instantiate_with_mock_db(self, qtbot, mock_db):
        from foliarium.ui.widgets.comuni import ElencoComuniWidget
        widget = ElencoComuniWidget(mock_db)
        qtbot.addWidget(widget)
        # Componenti principali presenti
        assert widget.filter_comuni_edit is not None
        assert widget.comuni_table is not None
        assert widget.btn_modifica_comune is not None
        # Bottoni azione disabilitati finche' non c'e' selezione
        assert widget.btn_modifica_comune.isEnabled() is False
        assert widget.btn_archivia_comune.isEnabled() is False

    def test_load_data_triggers_db_query(self, qtbot, mock_db):
        """load_data() avvia _ComuniLoaderWorker in thread separato."""
        from foliarium.ui.widgets.comuni import ElencoComuniWidget
        widget = ElencoComuniWidget(mock_db)
        qtbot.addWidget(widget)
        widget.load_data()
        # Aspetta che il worker thread finisca
        if hasattr(widget, "_loader"):
            widget._loader.wait(2000)
        # Il mock e' stato interrogato almeno una volta
        assert mock_db.get_all_comuni_details.called

    def test_filter_text_updates_proxy(self, qtbot, mock_db):
        """Il QLineEdit di filtro propaga al QSortFilterProxyModel."""
        from foliarium.ui.widgets.comuni import ElencoComuniWidget
        widget = ElencoComuniWidget(mock_db)
        qtbot.addWidget(widget)
        widget.filter_comuni_edit.setText("Genova")
        # apply_filter() viene chiamato via signal textChanged
        assert widget._comuni_proxy.filterRegularExpression().pattern() != ""


# ---------------------------------------------------------------------------
# ComuniTableModel — modello tabellare (foliarium/ui/widgets/comuni.py)
# ---------------------------------------------------------------------------

class TestComuniTableModelSmoke:
    """ComuniTableModel non richiede QApplication, e' puro QAbstractTableModel.
    Lo testiamo qui per copertura."""

    def test_empty_model(self, qtbot):
        from foliarium.ui.widgets.comuni import ComuniTableModel
        m = ComuniTableModel()
        assert m.rowCount() == 0
        assert m.columnCount() == 7

    def test_load_and_access(self, qtbot):
        from foliarium.ui.widgets.comuni import ComuniTableModel
        from PyQt6.QtCore import Qt, QModelIndex
        m = ComuniTableModel()
        m.load([
            {"id": 1, "nome_comune": "Savona", "provincia": "SV"},
            {"id": 2, "nome_comune": "Genova", "provincia": "GE"},
        ])
        assert m.rowCount() == 2
        # Cella 0,1 → nome_comune
        idx = m.index(0, 1, QModelIndex())
        assert m.data(idx, Qt.ItemDataRole.DisplayRole) == "Savona"
        # Helper methods
        assert m.comune_id_at(0) == 1
        assert m.comune_name_at(1) == "Genova"

    def test_sort_by_nome_descending(self, qtbot):
        from foliarium.ui.widgets.comuni import ComuniTableModel
        from PyQt6.QtCore import Qt
        m = ComuniTableModel()
        m.load([
            {"id": 1, "nome_comune": "Savona"},
            {"id": 2, "nome_comune": "Albenga"},
            {"id": 3, "nome_comune": "Genova"},
        ])
        m.sort(1, Qt.SortOrder.DescendingOrder)
        assert m.comune_name_at(0) == "Savona"
        assert m.comune_name_at(2) == "Albenga"


# ---------------------------------------------------------------------------
# DashboardWidget — vista riepilogo (foliarium/ui/widgets/dashboard.py)
# ---------------------------------------------------------------------------

class TestDashboardWidgetSmoke:

    def test_can_instantiate_admin_user(self, qtbot, mock_db):
        from foliarium.ui.widgets.dashboard import DashboardWidget
        user_info = {"nome_completo": "Mario Rossi", "ruolo": "admin"}
        widget = DashboardWidget(mock_db, user_info)
        qtbot.addWidget(widget)
        # 4 StatCard create
        assert widget.stat_comuni_card is not None
        assert widget.stat_partite_card is not None
        assert widget.stat_possessori_card is not None
        assert widget.stat_immobili_card is not None
        # Search edit visibile
        assert widget.search_edit is not None
        # Audit table popolata (vuota) — ha 5 colonne
        assert widget.audit_table.columnCount() == 5
        # is_admin: usato per mostrare il pulsante "Esegui Backup"
        assert widget.is_admin is True

    def test_can_instantiate_non_admin(self, qtbot, mock_db):
        from foliarium.ui.widgets.dashboard import DashboardWidget
        user_info = {"nome_completo": "Luca Bianchi", "ruolo": "operatore"}
        widget = DashboardWidget(mock_db, user_info)
        qtbot.addWidget(widget)
        assert widget.is_admin is False

    def test_handles_none_user_info(self, qtbot, mock_db):
        """current_user_info=None deve essere gestito senza crash."""
        from foliarium.ui.widgets.dashboard import DashboardWidget
        widget = DashboardWidget(mock_db, None)
        qtbot.addWidget(widget)
        assert widget.is_admin is False

    def test_search_signal_emits(self, qtbot, mock_db):
        """Premere Enter sul search edit emette ricerca_globale_richiesta."""
        from foliarium.ui.widgets.dashboard import DashboardWidget
        user_info = {"nome_completo": "Test", "ruolo": "admin"}
        widget = DashboardWidget(mock_db, user_info)
        qtbot.addWidget(widget)
        widget.search_edit.setText("Repubblica")
        with qtbot.waitSignal(widget.ricerca_globale_richiesta, timeout=1000) as sig:
            widget._avvia_ricerca_globale()
        assert sig.args == ["Repubblica"]

    def test_load_initial_data_calls_mock(self, qtbot, mock_db):
        from foliarium.ui.widgets.dashboard import DashboardWidget
        user_info = {"nome_completo": "Test", "ruolo": "admin"}
        widget = DashboardWidget(mock_db, user_info)
        qtbot.addWidget(widget)
        # load_initial_data() viene chiamato in __init__; aspetta il thread
        if hasattr(widget, "_dash_loader"):
            widget._dash_loader.wait(2000)
        assert mock_db.get_dashboard_stats.called
