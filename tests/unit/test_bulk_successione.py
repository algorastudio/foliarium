"""
tests/unit/test_bulk_successione.py
===================================
Test del wizard BulkSuccessioneWizard:
  - parse_quota (helper di parsing frazioni)
  - validazione step (quote sum=1, immobili selezionati, ecc.)
  - flusso atomico: chiamata a registra_passaggio_proprieta con i
    parametri attesi

Marker: gui (richiede QApplication, eseguito con QT_QPA_PLATFORM=offscreen).
"""
from __future__ import annotations

import os
from datetime import date
from fractions import Fraction
from unittest.mock import MagicMock

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault(
    "FOLIARIUM_LICENSE_KEY",
    "deadbeefcafebabe0123456789abcdef0123456789abcdef0123456789abcdef",
)

pytestmark = [pytest.mark.unit]


# ── parse_quota: test puri (no Qt) ────────────────────────────────────

class TestParseQuota:

    def test_fraction(self):
        from foliarium.ui.widgets.workflow.bulk_successione import parse_quota
        assert parse_quota("1/2") == Fraction(1, 2)
        assert parse_quota("3/4") == Fraction(3, 4)
        assert parse_quota("1/1") == Fraction(1)

    def test_integer(self):
        from foliarium.ui.widgets.workflow.bulk_successione import parse_quota
        assert parse_quota("1") == Fraction(1)
        assert parse_quota("0") == Fraction(0)

    def test_decimal(self):
        from foliarium.ui.widgets.workflow.bulk_successione import parse_quota
        assert parse_quota("0.5") == Fraction(1, 2)
        assert parse_quota("0.25") == Fraction(1, 4)

    def test_empty(self):
        from foliarium.ui.widgets.workflow.bulk_successione import parse_quota
        assert parse_quota("") is None
        assert parse_quota("   ") is None
        assert parse_quota(None) is None  # type: ignore[arg-type]

    def test_invalid(self):
        from foliarium.ui.widgets.workflow.bulk_successione import parse_quota
        assert parse_quota("abc") is None
        assert parse_quota("1/0") is None  # divisione per zero
        assert parse_quota("1/2/3") is None

    def test_whitespace_tolerant(self):
        from foliarium.ui.widgets.workflow.bulk_successione import parse_quota
        assert parse_quota(" 1/2 ") == Fraction(1, 2)


# ── Wizard tests (GUI) ────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def _silence_message_boxes(monkeypatch):
    """I QMessageBox modali bloccano i test headless: convertiamoli in no-op."""
    from PyQt6.QtWidgets import QMessageBox
    monkeypatch.setattr(QMessageBox, "warning",
                        lambda *a, **k: QMessageBox.StandardButton.Ok)
    monkeypatch.setattr(QMessageBox, "information",
                        lambda *a, **k: QMessageBox.StandardButton.Ok)
    monkeypatch.setattr(QMessageBox, "critical",
                        lambda *a, **k: QMessageBox.StandardButton.Ok)


@pytest.mark.gui
class TestWizardGui:

    @pytest.fixture(scope="class")
    def qapp(self):
        from PyQt6.QtWidgets import QApplication
        import sys
        app = QApplication.instance()
        if app is None:
            app = QApplication(sys.argv)
        return app

    @pytest.fixture
    def mock_db(self):
        db = MagicMock()
        db.search_partite.return_value = [{
            "id": 42,
            "comune_id": 1,
            "numero_partita": 42,
            "suffisso_partita": None,
            "stato": "attiva",
            "tipo": "principale",
        }]
        db.get_partita_details.return_value = {
            "id": 42,
            "numero_partita": 42,
            "stato": "attiva",
            "immobili": [
                {"id": 100, "natura": "Casa", "localita_nome": "Via Roma",
                 "classificazione": "A/3"},
                {"id": 101, "natura": "Magazzino", "localita_nome": "Via Roma",
                 "classificazione": "C/2"},
                {"id": 102, "natura": "Terreno", "localita_nome": "Via Mare",
                 "classificazione": None},
            ],
        }
        db.search_possessori_by_term_globally.return_value = []
        db.registra_passaggio_proprieta.return_value = True
        return db

    @pytest.fixture
    def wizard(self, qapp, mock_db):
        from foliarium.ui.widgets.workflow.bulk_successione import (
            BulkSuccessioneWizard,
        )
        w = BulkSuccessioneWizard(mock_db)
        yield w
        w.deleteLater()

    def _setup_origine(self, wizard):
        wizard._s1_comune_id = 1
        wizard._s1_comune_nome = "Genova"
        wizard._s1_numero.setValue(42)
        wizard._s1_load_partita()

    def test_construct(self, wizard):
        assert wizard._step == 0
        assert wizard._origine_partita is None

    def test_load_partita_populates_state(self, wizard, mock_db):
        self._setup_origine(wizard)
        assert wizard._origine_partita is not None
        assert wizard._origine_partita["id"] == 42
        assert len(wizard._immobili_origine) == 3

    def test_step1_validation_blocks_without_origine(self, wizard):
        # Senza load_partita → validate deve fallire
        ok = wizard._validate_current_step()
        assert ok is False

    def test_step1_validation_passes_with_origine(self, wizard):
        self._setup_origine(wizard)
        ok = wizard._validate_current_step()
        assert ok is True
        # Tipo variazione catturato
        assert wizard._tipo_variazione in ("Successione", "Vendita",
                                           "Donazione", "Permuta", "Divisione")

    def test_step2_select_all_then_none(self, wizard):
        self._setup_origine(wizard)
        wizard._s2_populate()
        wizard._s2_set_all(False)
        assert wizard._s2_get_selected_ids() == []
        wizard._s2_set_all(True)
        assert sorted(wizard._s2_get_selected_ids()) == [100, 101, 102]

    def test_step2_validation_requires_selection(self, wizard):
        self._setup_origine(wizard)
        wizard._step = 1
        wizard._s2_populate()
        wizard._s2_set_all(False)
        ok = wizard._validate_current_step()
        assert ok is False

    def test_step3_quote_sum_must_be_1(self, wizard):
        self._setup_origine(wizard)
        wizard._s3_add_erede(10, "ROSSI ANNA", quota="1/2")
        wizard._s3_add_erede(11, "ROSSI MARIO", quota="1/3")
        wizard._step = 2
        ok = wizard._validate_current_step()
        assert ok is False  # 1/2 + 1/3 = 5/6, non 1

    def test_step3_quote_sum_valid(self, wizard):
        self._setup_origine(wizard)
        wizard._s3_add_erede(10, "ROSSI ANNA", quota="1/2")
        wizard._s3_add_erede(11, "ROSSI MARIO", quota="1/2")
        wizard._step = 2
        ok = wizard._validate_current_step()
        assert ok is True
        assert len(wizard._eredi) == 2
        assert all(e["quota"] in ("1/2",) for e in wizard._eredi)

    def test_step3_requires_at_least_one_erede(self, wizard):
        self._setup_origine(wizard)
        wizard._step = 2
        ok = wizard._validate_current_step()
        assert ok is False

    def test_full_flow_calls_atomic_procedure(self, wizard, mock_db):
        from PyQt6.QtWidgets import QMessageBox
        from unittest.mock import patch
        from PyQt6.QtCore import QDate

        # Step 1
        self._setup_origine(wizard)
        # Step 2: tutti gli immobili
        wizard._s2_populate()
        wizard._immobili_selezionati_ids = wizard._s2_get_selected_ids()
        # Step 3: 3 eredi con 1/3 ciascuno
        wizard._s3_dest_numero.setValue(999)
        wizard._s3_add_erede(10, "ROSSI ANNA", quota="1/3")
        wizard._s3_add_erede(11, "ROSSI MARIO", quota="1/3")
        wizard._s3_add_erede(12, "ROSSI LUIGI", quota="1/3")
        wizard._eredi = wizard._s3_collect_eredi()
        assert wizard._eredi is not None
        # Step 4
        wizard._s4_tipo_contratto.setText("Dichiarazione di successione")
        wizard._s4_data_variazione.setDate(QDate(1925, 7, 10))
        wizard._s4_data_contratto.setDate(QDate(1925, 7, 1))
        wizard._s4_notaio.setText("Mario Bianchi")
        wizard._s4_repertorio.setText("REP-2025-01")
        wizard._tipo_variazione = "Successione"

        # Conferma → Yes
        with patch.object(QMessageBox, "question",
                          return_value=QMessageBox.StandardButton.Yes):
            wizard._eseguire_operazione()

        mock_db.registra_passaggio_proprieta.assert_called_once()
        kwargs = mock_db.registra_passaggio_proprieta.call_args.kwargs
        assert kwargs["partita_origine_id"] == 42
        assert kwargs["comune_id_nuova_partita"] == 1
        assert kwargs["numero_nuova_partita"] == 999
        assert kwargs["tipo_variazione"] == "Successione"
        assert kwargs["tipo_contratto"] == "Dichiarazione di successione"
        assert kwargs["data_variazione"] == date(1925, 7, 10)
        assert kwargs["notaio"] == "Mario Bianchi"
        assert kwargs["repertorio"] == "REP-2025-01"
        # Tutti e 3 gli immobili sono stati passati
        assert sorted(kwargs["immobili_da_trasferire_ids"]) == [100, 101, 102]
        # Eredi: 3 dict con possessore_id, titolo, quota
        eredi_list = kwargs["nuovi_possessori_list"]
        assert len(eredi_list) == 3
        assert {e["possessore_id"] for e in eredi_list} == {10, 11, 12}
        assert all(e["quota"] == "1/3" for e in eredi_list)
        # Dopo il successo il wizard si resetta
        assert wizard._origine_partita is None

    def test_db_error_blocks_reset(self, wizard, mock_db):
        from PyQt6.QtWidgets import QMessageBox
        from unittest.mock import patch
        mock_db.registra_passaggio_proprieta.side_effect = Exception("FK violated")

        self._setup_origine(wizard)
        wizard._s2_populate()
        wizard._immobili_selezionati_ids = wizard._s2_get_selected_ids()
        wizard._s3_dest_numero.setValue(999)
        wizard._s3_add_erede(10, "ROSSI ANNA", quota="1")
        wizard._eredi = wizard._s3_collect_eredi()
        wizard._s4_tipo_contratto.setText("Atto pubblico")

        with patch.object(QMessageBox, "question",
                          return_value=QMessageBox.StandardButton.Yes):
            with patch.object(QMessageBox, "critical") as crit:
                wizard._eseguire_operazione()
                crit.assert_called_once()

        # Non resettato: l'utente può correggere e riprovare
        assert wizard._origine_partita is not None
