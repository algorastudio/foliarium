"""
tests/unit/test_registrazione_proprieta_drafts.py
=================================================
Unit/GUI test della funzionalita' bozza in RegistrazioneProprietaWidget:
serializzazione -> roundtrip restore, autosave gating, eliminazione
post-registrazione.

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
def mock_db():
    db = MagicMock()
    db.search_possessori_by_term_globally.return_value = []
    db.get_localita_by_comune.return_value = [
        {"id": 10, "nome": "Via Roma", "tipologia_stradale": "Via"},
    ]
    db.get_immobili_by_comune.return_value = []
    db.save_partita_draft.return_value = 1
    db.delete_partita_draft.return_value = True
    return db


@pytest.fixture
def wizard(qapp, mock_db):
    from foliarium.ui.widgets.workflow.registrazione_proprieta import (
        RegistrazioneProprietaWidget,
    )
    w = RegistrazioneProprietaWidget(mock_db, utente_id=7)
    w._autosave_timer.stop()
    yield w
    w.deleteLater()


def _fill_state(w):
    w._comune_id = 1
    w._comune_nome = "Genova"
    w._s1_comune_label.setText("Genova")
    w._s1_numero.setValue(33)
    w._s1_suffisso.setText("ter")
    from PyQt6.QtCore import QDate
    w._s1_data_imp.setDate(QDate(1910, 3, 10))

    w._possessori_data = [
        {"id": 200, "nome_completo": "BIANCHI ANNA",
         "titolo": "Proprietario", "quota": "1/2"},
        {"id": 201, "nome_completo": "BIANCHI CARLO",
         "titolo": "Proprietario", "quota": "1/2"},
    ]
    w._refresh_poss_table()

    w._immobili_data = [
        {"natura": "Casa", "localita_id": 10, "localita_nome": "Via Roma",
         "classificazione": "A/2", "consistenza": "5 vani",
         "numero_piani": 2, "numero_vani": 5, "numero_civico": "12"},
    ]
    w._refresh_imm_table()


class TestSerializeRestore:

    def test_serialize_captures_state(self, wizard):
        _fill_state(wizard)
        payload = wizard._serialize_state()

        assert payload["schema_version"] == 1
        assert payload["comune"] == {"id": 1, "nome": "Genova"}
        assert payload["partita"]["numero"] == 33
        assert payload["partita"]["suffisso"] == "ter"
        assert payload["partita"]["data_impianto"] == "1910-03-10"
        assert len(payload["possessori"]) == 2
        assert payload["possessori"][0]["nome_completo"] == "BIANCHI ANNA"
        assert len(payload["immobili"]) == 1
        assert payload["immobili"][0]["numero_civico"] == "12"

    def test_roundtrip(self, wizard):
        _fill_state(wizard)
        snap = wizard._serialize_state()

        wizard._reset_wizard()
        assert wizard._possessori_data == []
        assert wizard._immobili_data == []

        wizard._restore_state(snap)
        assert wizard._comune_id == 1
        assert wizard._s1_numero.value() == 33
        assert wizard._s1_suffisso.text() == "ter"
        assert len(wizard._possessori_data) == 2
        assert len(wizard._immobili_data) == 1
        assert wizard._dirty is False


class TestDirtyTracking:

    def test_clean_after_construction(self, wizard):
        assert wizard._dirty is False

    def test_setting_value_marks_dirty(self, wizard):
        wizard._s1_numero.setValue(77)
        assert wizard._dirty is True


class TestAutosaveGating:

    def test_skipped_when_clean(self, wizard, mock_db):
        wizard._on_autosave_tick()
        mock_db.save_partita_draft.assert_not_called()

    def test_skipped_when_empty(self, wizard, mock_db):
        wizard._dirty = True
        wizard._on_autosave_tick()
        mock_db.save_partita_draft.assert_not_called()

    def test_persists_when_dirty_and_meaningful(self, wizard, mock_db):
        wizard._comune_id = 1
        wizard._comune_nome = "Genova"
        wizard._dirty = True
        wizard._on_autosave_tick()
        mock_db.save_partita_draft.assert_called_once()
        kwargs = mock_db.save_partita_draft.call_args.kwargs
        assert kwargs["utente_id"] == 7
        assert kwargs["wizard_kind"] == "registrazione_proprieta"
        assert kwargs["draft_id"] is None
        assert wizard._current_draft_id == 1
        assert wizard._dirty is False


class TestRegistrationDeletesDraft:

    def test_successful_registration_deletes_draft(self, wizard, mock_db):
        _fill_state(wizard)
        wizard._current_draft_id = 777
        mock_db.registra_nuova_proprieta.return_value = 12345
        # Patch QMessageBox.question per evitare blocco
        from PyQt6.QtWidgets import QMessageBox
        import unittest.mock as um
        with um.patch.object(QMessageBox, "question",
                             return_value=QMessageBox.StandardButton.No):
            wizard._registra_tutto()

        mock_db.registra_nuova_proprieta.assert_called_once()
        mock_db.delete_partita_draft.assert_called_once_with(
            777, utente_id=7, wizard_kind="registrazione_proprieta")
        assert wizard._current_draft_id is None
