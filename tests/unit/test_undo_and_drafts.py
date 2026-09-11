"""
tests/unit/test_undo_and_drafts.py
==================================
Unit test dell'annullamento e delle bozze dei moduli.

L'annullamento è deliberatamente limitato: una sola azione, con scadenza,
eseguita come operazione inversa sul database. Questi test fissano quei
confini, perché allargarli su un archivio condiviso significherebbe
sovrascrivere il lavoro di un altro archivista.
"""

from __future__ import annotations

import os
import sys
from unittest.mock import MagicMock

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:
    from PyQt6.QtWidgets import QApplication
    _QT_OK = True
except ImportError:
    _QT_OK = False

pytestmark = [
    pytest.mark.unit,
    pytest.mark.gui,
    pytest.mark.skipif(not _QT_OK, reason="PyQt6 non disponibile"),
]


@pytest.fixture(scope="module")
def app():
    inst = QApplication.instance()
    if inst is None:
        inst = QApplication(sys.argv)
    yield inst


@pytest.fixture
def gestore(app):
    from foliarium.ui.undo import GestoreAnnullamento
    g = GestoreAnnullamento(durata_ms=60_000)
    yield g
    g.dimentica()


class TestGestoreAnnullamento:

    def test_senza_azione_non_fa_nulla(self, gestore):
        assert gestore.ha_azione() is False
        assert gestore.annulla_ultima() is None

    def test_annullamento_esegue_l_inversa(self, gestore):
        from foliarium.ui.undo import AzioneAnnullabile
        eseguito = []
        gestore.registra(AzioneAnnullabile(
            "Comune «Savona» archiviato",
            lambda: eseguito.append("ripristina"),
            al_termine=lambda: eseguito.append("ricarica vista"),
        ))

        descrizione = gestore.annulla_ultima()

        assert descrizione == "Comune «Savona» archiviato"
        assert eseguito == ["ripristina", "ricarica vista"]

    def test_una_sola_azione_alla_volta(self, gestore):
        """Registrarne una nuova scarta la precedente: niente pila profonda."""
        from foliarium.ui.undo import AzioneAnnullabile
        eseguito = []
        gestore.registra(AzioneAnnullabile("prima", lambda: eseguito.append("prima")))
        gestore.registra(AzioneAnnullabile("seconda", lambda: eseguito.append("seconda")))

        gestore.annulla_ultima()

        assert eseguito == ["seconda"]
        assert gestore.ha_azione() is False

    def test_non_si_annulla_due_volte(self, gestore):
        from foliarium.ui.undo import AzioneAnnullabile
        eseguito = []
        gestore.registra(AzioneAnnullabile("x", lambda: eseguito.append("x")))

        gestore.annulla_ultima()
        assert gestore.annulla_ultima() is None
        assert eseguito == ["x"]

    def test_errore_dell_inversa_propagato_e_azione_consumata(self, gestore):
        """Se un altro utente è già intervenuto, l'inversa fallisce.

        L'azione va comunque consumata: ritentarla al buio non ha senso.
        """
        from foliarium.ui.undo import AzioneAnnullabile

        def inversa_fallita():
            raise RuntimeError("record già ripristinato da un altro utente")

        gestore.registra(AzioneAnnullabile("Partita archiviata", inversa_fallita))

        with pytest.raises(RuntimeError):
            gestore.annulla_ultima()
        assert gestore.ha_azione() is False

    def test_al_termine_che_fallisce_non_invalida_l_annullamento(self, gestore):
        """L'aggiornamento della vista è accessorio: non deve propagare."""
        from foliarium.ui.undo import AzioneAnnullabile

        def vista_rotta():
            raise RuntimeError("widget distrutto")

        gestore.registra(AzioneAnnullabile(
            "Comune archiviato", lambda: None, al_termine=vista_rotta))

        assert gestore.annulla_ultima() == "Comune archiviato"

    def test_dimentica_scarta_senza_eseguire(self, gestore):
        from foliarium.ui.undo import AzioneAnnullabile
        eseguito = []
        gestore.registra(AzioneAnnullabile("x", lambda: eseguito.append("x")))

        gestore.dimentica()

        assert gestore.ha_azione() is False
        assert eseguito == []

    def test_scadenza_toglie_l_offerta(self, app):
        """Passato il tempo, l'annullamento non è più proposto."""
        from PyQt6.QtTest import QTest
        from foliarium.ui.undo import AzioneAnnullabile, GestoreAnnullamento

        g = GestoreAnnullamento(durata_ms=120)
        g.registra(AzioneAnnullabile("x", lambda: None))
        assert g.ha_azione() is True

        QTest.qWait(300)
        assert g.ha_azione() is False

    def test_segnali_emessi(self, gestore):
        from foliarium.ui.undo import AzioneAnnullabile
        disponibili, esauriti = [], []
        gestore.disponibile.connect(disponibili.append)
        gestore.esaurito.connect(lambda: esauriti.append(True))

        gestore.registra(AzioneAnnullabile("Comune archiviato", lambda: None))
        gestore.annulla_ultima()

        assert disponibili == ["Comune archiviato"]
        assert len(esauriti) == 1


class TestBozzeDeiModuli:

    @pytest.fixture
    def modulo(self, app):
        from foliarium.ui.widgets.insertion import InserimentoComuneWidget
        db = MagicMock()
        db.get_historical_periods.return_value = [
            {"id": 3, "nome": "Napoleonico", "anno_inizio": 1800, "anno_fine": 1814},
        ]
        w = InserimentoComuneWidget(db, {"username": "mrossi"})
        w.utente_id = 7
        w.load_initial_data()
        yield w
        w.deleteLater()

    def test_serializza_tutti_i_tipi_di_campo(self, modulo):
        modulo.nome_comune_edit.setText("Albisola")
        modulo.note_edit.setPlainText("nota")
        modulo.data_istituzione_check.setChecked(True)
        modulo.periodo_combo.setCurrentIndex(1)

        stato = modulo.serializza_bozza()

        assert stato["nome_comune_edit"] == {"tipo": "testo", "valore": "Albisola"}
        assert stato["note_edit"]["tipo"] == "testo_lungo"
        assert stato["data_istituzione_check"] == {"tipo": "spunta", "valore": True}
        assert stato["periodo_combo"]["valore"] == 3
        assert stato["data_istituzione_edit"]["tipo"] == "data"

    def test_ciclo_completo_salva_e_riprendi(self, modulo):
        modulo.nome_comune_edit.setText("Albisola Superiore")
        modulo.regione_edit.setText("Liguria")
        modulo.periodo_combo.setCurrentIndex(1)
        stato = modulo.serializza_bozza()

        modulo.pulisci_campi()
        assert modulo.nome_comune_edit.text() == ""

        modulo.ripristina_bozza(stato)

        assert modulo.nome_comune_edit.text() == "Albisola Superiore"
        assert modulo.regione_edit.text() == "Liguria"
        assert modulo.periodo_combo.currentData() == 3

    def test_il_menu_ripopolato_in_ordine_diverso_ritrova_la_voce(self, modulo):
        """Il testo salvato fa da rete quando l'id non è più fra le scelte."""
        modulo.periodo_combo.setCurrentIndex(1)
        stato = modulo.serializza_bozza()

        modulo.periodo_combo.clear()
        modulo.periodo_combo.addItem("Altro", 99)
        modulo.periodo_combo.addItem("Napoleonico (1800 - 1814)", None)

        modulo.ripristina_bozza(stato)

        assert modulo.periodo_combo.currentText() == "Napoleonico (1800 - 1814)"

    def test_campi_spariti_vengono_ignorati(self, modulo):
        """Una bozza di una versione precedente non deve far crollare il modulo."""
        modulo.ripristina_bozza({
            "campo_che_non_esiste_piu": {"tipo": "testo", "valore": "x"},
            "nome_comune_edit": {"tipo": "testo", "valore": "Savona"},
        })
        assert modulo.nome_comune_edit.text() == "Savona"

    def test_salvataggio_passa_il_tipo_e_l_utente(self, modulo):
        modulo.db_manager.save_partita_draft.return_value = 42
        modulo.nome_comune_edit.setText("Savona")

        assert modulo.save_pending_changes() is True

        chiamata = modulo.db_manager.save_partita_draft.call_args.kwargs
        assert chiamata["wizard_kind"] == "form_inserimento_comune"
        assert chiamata["utente_id"] == 7
        assert chiamata["payload"]["nome_comune_edit"]["valore"] == "Savona"

    def test_dopo_il_salvataggio_il_modulo_non_e_piu_da_salvare(self, modulo):
        modulo.db_manager.save_partita_draft.return_value = 42
        modulo.nome_comune_edit.setText("Savona")
        assert modulo.has_unsaved_changes() is True

        modulo.save_pending_changes()

        assert modulo.has_unsaved_changes() is False

    def test_aggiornamenti_successivi_riusano_la_stessa_bozza(self, modulo):
        modulo.db_manager.save_partita_draft.return_value = 42
        modulo.nome_comune_edit.setText("Savona")
        modulo.save_pending_changes()
        modulo.nome_comune_edit.setText("Savona Vecchia")
        modulo.save_pending_changes()

        assert modulo.db_manager.save_partita_draft.call_args.kwargs["draft_id"] == 42

    def test_ogni_modulo_ha_il_proprio_tipo_di_bozza(self, app):
        """Le liste non devono mescolare moduli diversi."""
        from foliarium.ui.widgets.insertion import (
            InserimentoComuneWidget, InserimentoLocalitaWidget,
            InserimentoPartitaWidget, InserimentoPossessoreWidget,
        )
        tipi = {
            cls._DRAFT_KIND
            for cls in (InserimentoComuneWidget, InserimentoPossessoreWidget,
                        InserimentoLocalitaWidget, InserimentoPartitaWidget)
        }
        assert len(tipi) == 4


class TestRobustezza:
    """Regressioni su due difetti emersi facendo girare la suite completa."""

    def test_il_gestore_sopravvive_alla_raccolta_dei_riferimenti(self, app):
        """Il singleton è un QObject: senza un proprietario stabile l'oggetto
        C++ viene distrutto e ogni uso successivo solleva RuntimeError."""
        import gc

        from foliarium.ui import undo

        undo._gestore = None
        primo = undo.gestore_annullamento()
        del primo
        gc.collect()

        secondo = undo.gestore_annullamento()
        secondo.dimentica()          # deve poter essere usato
        assert secondo.ha_azione() is False

    def test_event_filter_regge_una_finestra_semidistrutta(self, app):
        """Il filtro è installato sulla QApplication e rimosso in closeEvent.

        Se la finestra sparisce per altra via Qt lo chiama comunque: deve
        rispondere, non far abortire il processo dentro il ciclo di eventi.
        """
        from PyQt6.QtCore import QEvent
        import gui_main

        finestra = gui_main.CatastoMainWindow("127.0.0.1")
        try:
            # simula lo stato di un oggetto i cui attributi non ci sono più
            del finestra.logged_in_user_id
            del finestra._inactivity_timer

            assert finestra.eventFilter(None, QEvent(QEvent.Type.MouseMove)) is False
        finally:
            app.removeEventFilter(finestra)
            finestra.deleteLater()
