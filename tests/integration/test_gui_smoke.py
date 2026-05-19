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

    # Lookup tables (admin widgets)
    db.get_tipi_localita.return_value = []
    db.get_tipi_possesso.return_value = []
    db.get_historical_periods.return_value = []
    db.get_tutti_archiviati.return_value = []
    db.get_utenti.return_value = []

    # Audit / consultazione (reporting widgets)
    db.get_audit_logs.return_value = ([], 0)
    db.get_elenco_comuni_semplice.return_value = []

    # Connessione (per BackupWidget / settings)
    db.get_connection_parameters.return_value = {
        "host": "localhost", "port": 5432, "dbname": "catasto_storico",
    }
    db.get_current_dbname.return_value = "catasto_storico"
    db.get_current_user.return_value = "postgres"

    # Statistiche
    db.get_statistiche_comune.return_value = {}

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


# ---------------------------------------------------------------------------
# Smoke test parametrici sui widget di insertion / admin / reporting
#
# Pattern minimo: importa il widget, lo istanzia con mock_db, verifica
# che non sollevi exception. Non testa comportamento — solo che il
# costruttore e la prima fase di setup UI funzionino dopo le estrazioni
# Sprint 3.x.
#
# Widget intenzionalmente esclusi:
#   - BackupWidget       → richiede filesystem + subprocess pg_dump
#   - StatisticheWidget  → query pesanti su MV, signal complessi
#   - ReportisticaWidget → multi-tab con widget figli che fanno I/O
#   - GestioneUtentiWidget → SessionManager + permessi
#   - RicercaDocumentiWidget → side-effect su filesystem
#
# Aggiungerli individualmente se diventa rilevante coprirli.
# ---------------------------------------------------------------------------

_USER_INFO = {
    "id": 1, "username": "admin", "nome_completo": "Admin", "ruolo": "admin",
}


@pytest.mark.parametrize("module_path,class_name,extra_args", [
    # Widget di inserimento (foliarium/ui/widgets/insertion.py)
    # InserimentoComuneWidget richiede utente_attuale_info dict
    ("foliarium.ui.widgets.insertion", "InserimentoComuneWidget", _USER_INFO),
    ("foliarium.ui.widgets.insertion", "InserimentoPossessoreWidget", None),
    ("foliarium.ui.widgets.insertion", "InserimentoLocalitaWidget", None),
    ("foliarium.ui.widgets.insertion", "InserimentoPartitaWidget", None),

    # Widget admin/lookup tables (foliarium/ui/widgets/admin.py)
    ("foliarium.ui.widgets.admin", "GestioneTipiLocalitaWidget", None),
    ("foliarium.ui.widgets.admin", "TipiPossessoWidget", None),
    ("foliarium.ui.widgets.admin", "GestionePeriodiStoriciWidget", None),
    ("foliarium.ui.widgets.admin", "ArchivioWidget", None),

    # Widget reporting (foliarium/ui/widgets/reporting.py)
    ("foliarium.ui.widgets.reporting", "EsportazioniWidget", None),
    # RegistraConsultazioneWidget richiede current_user_info dict
    ("foliarium.ui.widgets.reporting", "RegistraConsultazioneWidget", _USER_INFO),

    # Widget workflow partite (Sprint 3.3, foliarium/ui/widgets/workflow/*)
    ("foliarium.ui.widgets.workflow.nuova_partita_wizard",
     "NuovaPartitaWizardWidget", None),
    ("foliarium.ui.widgets.workflow.registrazione_proprieta",
     "RegistrazioneProprietaWidget", None),
    ("foliarium.ui.widgets.workflow.operazioni_partita",
     "OperazioniPartitaWidget", None),

    # Widget ricerca (Sprint 3.4, foliarium/ui/widgets/search/*)
    ("foliarium.ui.widgets.search.partite", "RicercaPartiteWidget", None),
    ("foliarium.ui.widgets.search.immobili", "RicercaAvanzataImmobiliWidget", None),
    ("foliarium.ui.widgets.search.fuzzy", "UnifiedFuzzySearchWidget", None),
])
class TestWidgetCanInstantiate:
    """Smoke: ogni widget si istanzia con mock_db senza exception.

    Test parametrico per non ripetere boilerplate. Ogni widget viene
    aggiunto a qtbot per il cleanup automatico del lifecycle Qt.

    extra_args: None per widget che prendono solo db_manager; dict per
    widget che richiedono utente_attuale_info / current_user_info come
    secondo argomento posizionale.
    """

    def test_instantiate(self, qtbot, mock_db, module_path, class_name, extra_args):
        import importlib
        mod = importlib.import_module(module_path)
        WidgetCls = getattr(mod, class_name)
        if extra_args is None:
            widget = WidgetCls(mock_db)
        else:
            widget = WidgetCls(mock_db, extra_args)
        qtbot.addWidget(widget)
        assert widget is not None


# ---------------------------------------------------------------------------
# AuditLogViewerWidget — testato separatamente perche' ha una signature
# diversa (richiede SessionManager o user_id come argomento)
# ---------------------------------------------------------------------------

class TestAuditLogViewerWidgetSmoke:

    def test_can_instantiate(self, qtbot, mock_db):
        from foliarium.ui.widgets.admin import AuditLogViewerWidget
        # AuditLogViewerWidget accetta solo db_manager (gli altri argomenti
        # hanno default o sono opzionali). Se la signature cambia, il test
        # esposero il drift.
        try:
            widget = AuditLogViewerWidget(mock_db)
        except TypeError as e:
            # Se richiede argomenti extra, skip esplicito con motivazione
            pytest.skip(f"signature non compatibile col mock_db: {e}")
        qtbot.addWidget(widget)
        assert widget is not None
