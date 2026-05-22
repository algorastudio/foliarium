"""
tests/unit/test_nuova_partita_wizard_drafts.py
==============================================
Unit/GUI test della funzionalita' bozza nel NuovaPartitaWizardWidget:
serializzazione -> roundtrip restore, autosave gating, eliminazione
post-registrazione.

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


@pytest.fixture
def mock_db():
    db = MagicMock()
    db.get_localita_by_comune.return_value = [
        {"id": 10, "nome": "Via Roma", "tipologia_stradale": "Via"},
        {"id": 11, "nome": "Piazza Centrale", "tipologia_stradale": "Piazza"},
    ]
    db.search_possessori_by_term_globally.return_value = []
    # Save/load drafts: comportamento semplificato
    db.save_partita_draft.return_value = 1
    db.delete_partita_draft.return_value = True
    return db


@pytest.fixture
def wizard(qapp, mock_db):
    from foliarium.ui.widgets.workflow.nuova_partita_wizard import (
        NuovaPartitaWizardWidget,
    )
    w = NuovaPartitaWizardWidget(mock_db, utente_info={}, utente_id=7)
    # Disabilita l'autosave timer per evitare effetti collaterali
    w._autosave_timer.stop()
    yield w
    w.deleteLater()


def _fill_basic_state(w):
    """Popola lo stato del wizard con dati minimi: comune + numero + 1 possessore + 1 immobile."""
    w._comune_id = 1
    w._comune_nome = "Genova"
    w._s1_comune_label.setText("Genova")
    w._s1_numero.setValue(42)
    w._s1_suffisso.setText("bis")
    from PyQt6.QtCore import QDate
    w._s1_data_imp.setDate(QDate(1925, 6, 15))
    w._s1_tipo.setCurrentText("Principale")
    w._s1_stato.setCurrentText("Attiva")

    # Possessori (chiamato direttamente per bypassare i dialog)
    w._s2_append_possessore(100, "ROSSI MARIO", titolo="Proprietario")
    w._s2_append_possessore(101, "VERDI LUIGI", titolo="Usufruttuario")

    # Immobili
    w._s3_append_immobile(
        natura="Casa", localita_id=10,
        localita_text="Via Roma (Via)", classif="A/3")
    w._s3_append_immobile(
        natura="Magazzino", localita_id=11,
        localita_text="Piazza Centrale (Piazza)", classif="C/2")


class TestSerializeRestore:

    def test_serialize_captures_all_state(self, wizard):
        _fill_basic_state(wizard)
        payload = wizard._serialize_state()

        assert payload["schema_version"] == 1
        assert payload["comune"] == {"id": 1, "nome": "Genova"}
        assert payload["partita"]["numero"] == 42
        assert payload["partita"]["suffisso"] == "bis"
        assert payload["partita"]["data_impianto"] == "1925-06-15"
        assert payload["partita"]["tipo"] == "Principale"
        assert payload["partita"]["stato"] == "Attiva"

        assert len(payload["possessori"]) == 2
        assert payload["possessori"][0]["id"] == 100
        assert payload["possessori"][0]["nome"] == "ROSSI MARIO"
        assert payload["possessori"][1]["titolo"] == "Usufruttuario"

        assert len(payload["immobili"]) == 2
        assert payload["immobili"][0]["natura"] == "Casa"
        assert payload["immobili"][0]["localita_id"] == 10
        assert payload["immobili"][1]["classificazione"] == "C/2"

    def test_roundtrip_serialize_restore(self, wizard, qapp):
        _fill_basic_state(wizard)
        snapshot = wizard._serialize_state()

        # Resetta e ripristina
        wizard._reset_wizard(confirm=False)
        assert wizard._s1_numero.value() == 1  # davvero resettato
        assert wizard._s2_table.rowCount() == 0

        wizard._restore_state(snapshot)

        # Verifica round-trip
        assert wizard._comune_id == 1
        assert wizard._comune_nome == "Genova"
        assert wizard._s1_numero.value() == 42
        assert wizard._s1_suffisso.text() == "bis"
        assert wizard._s1_data_imp.date().toString("yyyy-MM-dd") == "1925-06-15"
        assert wizard._s1_tipo.currentText() == "Principale"
        assert wizard._s2_table.rowCount() == 2
        assert wizard._s3_table.rowCount() == 2

        # Il dirty-flag deve essere ripulito dopo restore
        assert wizard._dirty is False


class TestDirtyTracking:

    def test_clean_after_construction(self, wizard):
        assert wizard._dirty is False

    def test_setting_value_marks_dirty(self, wizard):
        wizard._s1_numero.setValue(99)
        assert wizard._dirty is True

    def test_restore_does_not_mark_dirty(self, wizard):
        _fill_basic_state(wizard)
        payload = wizard._serialize_state()
        wizard._reset_wizard(confirm=False)
        wizard._restore_state(payload)
        assert wizard._dirty is False


class TestAutosaveGating:

    def test_autosave_skipped_when_clean(self, wizard, mock_db):
        # Nessuna modifica → no save chiamato
        wizard._on_autosave_tick()
        mock_db.save_partita_draft.assert_not_called()

    def test_autosave_skipped_when_no_meaningful_content(self, wizard, mock_db):
        # Sporco ma stato vuoto (nessun comune, nessun possessore/immobile, suffisso vuoto)
        wizard._dirty = True
        wizard._on_autosave_tick()
        mock_db.save_partita_draft.assert_not_called()

    def test_autosave_persists_when_dirty_and_meaningful(self, wizard, mock_db):
        wizard._comune_id = 1
        wizard._comune_nome = "Genova"
        wizard._dirty = True
        wizard._on_autosave_tick()
        mock_db.save_partita_draft.assert_called_once()
        # draft_id None la prima volta -> INSERT
        kwargs = mock_db.save_partita_draft.call_args.kwargs
        assert kwargs["draft_id"] is None
        assert kwargs["utente_id"] == 7
        assert wizard._current_draft_id == 1
        assert wizard._dirty is False


class TestRegistrationDeletesDraft:

    def test_successful_registration_deletes_draft(self, wizard, mock_db):
        _fill_basic_state(wizard)
        wizard._current_draft_id = 555
        mock_db.create_partita.return_value = 9999

        wizard._registra_tutto()

        mock_db.create_partita.assert_called_once()
        mock_db.delete_partita_draft.assert_called_once_with(
            555, utente_id=7)
        assert wizard._current_draft_id is None
