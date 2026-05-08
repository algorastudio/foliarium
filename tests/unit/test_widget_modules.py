"""
tests/unit/test_widget_modules.py
===================================
Smoke test per la struttura dei moduli widget (post-refactor v1.0.1).

Verificano che:
  1. I moduli estratti (search_widgets, partita_workflow_widgets) siano
     importabili senza errori runtime.
  2. Tutte le classi principali siano accessibili dai moduli corretti.
  3. I re-export in gui_widgets.py (backward compat) puntino alle stesse
     classi (non a copie).

Non istanziano widget: non richiedono QApplication né display.
"""
from __future__ import annotations

import importlib
import pytest

pytestmark = pytest.mark.unit


class TestSearchWidgetsModule:
    """search_widgets.py esporta i widget di ricerca."""

    def test_module_importable(self):
        mod = importlib.import_module("search_widgets")
        assert mod is not None

    def test_ricerca_partite_widget_exported(self):
        from search_widgets import RicercaPartiteWidget
        assert RicercaPartiteWidget is not None

    def test_ricerca_avanzata_immobili_widget_exported(self):
        from search_widgets import RicercaAvanzataImmobiliWidget
        assert RicercaAvanzataImmobiliWidget is not None

    def test_unified_fuzzy_search_widget_exported(self):
        from search_widgets import UnifiedFuzzySearchWidget
        assert UnifiedFuzzySearchWidget is not None

    def test_partita_result_card_exported(self):
        from search_widgets import PartitaResultCard
        assert PartitaResultCard is not None

    def test_unified_fuzzy_search_thread_exported(self):
        from search_widgets import UnifiedFuzzySearchThread
        assert UnifiedFuzzySearchThread is not None


class TestPartitaWorkflowWidgetsModule:
    """partita_workflow_widgets.py esporta i widget di workflow."""

    def test_module_importable(self):
        mod = importlib.import_module("partita_workflow_widgets")
        assert mod is not None

    def test_registrazione_proprieta_widget_exported(self):
        from partita_workflow_widgets import RegistrazioneProprietaWidget
        assert RegistrazioneProprietaWidget is not None

    def test_nuova_partita_wizard_widget_exported(self):
        from partita_workflow_widgets import NuovaPartitaWizardWidget
        assert NuovaPartitaWizardWidget is not None

    def test_operazioni_partita_widget_exported(self):
        from partita_workflow_widgets import OperazioniPartitaWidget
        assert OperazioniPartitaWidget is not None


class TestGuiWidgetsReexports:
    """gui_widgets.py deve re-esportare le classi estratte (backward compat)."""

    def test_ricerca_partite_reexported(self):
        from gui_widgets import RicercaPartiteWidget
        assert RicercaPartiteWidget is not None

    def test_ricerca_avanzata_immobili_reexported(self):
        from gui_widgets import RicercaAvanzataImmobiliWidget
        assert RicercaAvanzataImmobiliWidget is not None

    def test_unified_fuzzy_search_reexported(self):
        from gui_widgets import UnifiedFuzzySearchWidget
        assert UnifiedFuzzySearchWidget is not None

    def test_registrazione_proprieta_reexported(self):
        from gui_widgets import RegistrazioneProprietaWidget
        assert RegistrazioneProprietaWidget is not None

    def test_nuova_partita_wizard_reexported(self):
        from gui_widgets import NuovaPartitaWizardWidget
        assert NuovaPartitaWizardWidget is not None

    def test_operazioni_partita_reexported(self):
        from gui_widgets import OperazioniPartitaWidget
        assert OperazioniPartitaWidget is not None

    def test_search_reexport_is_same_class(self):
        """Il re-export in gui_widgets punta alla classe originale, non a una copia."""
        from search_widgets import RicercaPartiteWidget as original
        from gui_widgets import RicercaPartiteWidget as reexported
        assert original is reexported

    def test_workflow_reexport_is_same_class(self):
        from partita_workflow_widgets import RegistrazioneProprietaWidget as original
        from gui_widgets import RegistrazioneProprietaWidget as reexported
        assert original is reexported

    def test_fuzzy_reexport_is_same_class(self):
        from search_widgets import UnifiedFuzzySearchWidget as original
        from gui_widgets import UnifiedFuzzySearchWidget as reexported
        assert original is reexported
