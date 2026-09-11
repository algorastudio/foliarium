"""
tests/unit/test_unsaved_and_shortcuts.py
========================================
Unit test di due protezioni introdotte con la revisione euristica:

  - il rilevamento delle modifiche non salvate (UnsavedFormMixin e il guard
    di CatastoMainWindow)
  - il set di scorciatoie da tastiera

La soglia del mixin e' deliberatamente alta: un avviso che scatta quando
non serve insegna a ignorarlo, quindi i test la fissano esplicitamente.
"""

from __future__ import annotations

import os
import sys
from unittest.mock import MagicMock

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:
    from PyQt6.QtWidgets import (QApplication, QCheckBox, QComboBox, QLineEdit,
                                 QSpinBox, QVBoxLayout, QWidget)
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
def modulo(app):
    """Un form con un campo di testo, un menu a tendina e due contatori."""
    from foliarium.ui.widgets.custom import UnsavedFormMixin

    class Modulo(UnsavedFormMixin, QWidget):
        def __init__(self):
            super().__init__()
            layout = QVBoxLayout(self)
            self.testo = QLineEdit()
            self.tendina = QComboBox()
            self.tendina.addItems(["primo", "secondo", "terzo"])
            self.numero = QSpinBox()
            self.spunta = QCheckBox()
            for campo in (self.testo, self.tendina, self.numero, self.spunta):
                layout.addWidget(campo)

    w = Modulo()
    yield w
    w.deleteLater()


class TestUnsavedFormMixin:

    def test_senza_riferimento_non_avvisa(self, modulo):
        """Finche' mark_form_clean non e' stato chiamato non si avvisa."""
        modulo.testo.setText("qualcosa")
        assert modulo.has_unsaved_changes() is False

    def test_nessuna_modifica(self, modulo):
        modulo.mark_form_clean()
        assert modulo.has_unsaved_changes() is False

    def test_testo_digitato_basta_da_solo(self, modulo):
        modulo.mark_form_clean()
        modulo.testo.setText("Rossi Mario")
        assert modulo.has_unsaved_changes() is True

    def test_una_sola_selezione_non_basta(self, modulo):
        """Sfiorare un menu a tendina non è lavoro da proteggere."""
        modulo.mark_form_clean()
        modulo.tendina.setCurrentIndex(1)
        assert modulo.has_unsaved_changes() is False

    def test_due_selezioni_bastano(self, modulo):
        modulo.mark_form_clean()
        modulo.tendina.setCurrentIndex(1)
        modulo.numero.setValue(7)
        assert modulo.has_unsaved_changes() is True

    def test_valori_di_default_non_contano(self, modulo):
        """La provincia precompilata non deve risultare 'da salvare'."""
        modulo.testo.setText("SV")
        modulo.numero.setValue(1)
        modulo.mark_form_clean()
        assert modulo.has_unsaved_changes() is False

    def test_discard_azzera(self, modulo):
        modulo.mark_form_clean()
        modulo.testo.setText("dati")
        assert modulo.has_unsaved_changes() is True
        modulo.discard_pending_changes()
        assert modulo.has_unsaved_changes() is False


class TestGuardDiNavigazione:

    def test_pagina_senza_protocollo_non_blocca(self, app):
        import gui_main
        assert gui_main.CatastoMainWindow._page_has_unsaved_changes(QWidget()) is False

    def test_pagina_che_solleva_non_blocca(self, app):
        """Una pagina difettosa non deve impedire di navigare."""
        import gui_main
        pagina = MagicMock()
        pagina.has_unsaved_changes.side_effect = RuntimeError("widget distrutto")
        assert gui_main.CatastoMainWindow._page_has_unsaved_changes(pagina) is False

    def test_pagina_con_modifiche_viene_rilevata(self, app):
        import gui_main
        pagina = MagicMock()
        pagina.has_unsaved_changes.return_value = True
        assert gui_main.CatastoMainWindow._page_has_unsaved_changes(pagina) is True


class TestScorciatoie:

    def test_nessuna_sequenza_duplicata(self, app):
        """Due binding sulla stessa sequenza rendono la scorciatoia inerte."""
        import gui_main
        sequenze = [voce[0] for voce in gui_main.CatastoMainWindow._SHORTCUTS]
        assert len(sequenze) == len(set(sequenze))

    def test_ogni_scorciatoia_punta_a_un_metodo_esistente(self, app):
        import gui_main
        mancanti = [
            metodo for _, _, metodo, _ in gui_main.CatastoMainWindow._SHORTCUTS
            if not hasattr(gui_main.CatastoMainWindow, metodo)
        ]
        assert mancanti == []

    def test_le_voci_di_menu_non_registrano_un_secondo_binding(self, app):
        """F1 e Ctrl+/ stanno sulle QAction: non vanno duplicate."""
        import gui_main
        finestra = gui_main.CatastoMainWindow("127.0.0.1")
        try:
            finestra._install_shortcuts()
            registrate = {s.key().toString() for s in finestra._shortcut_objects}
            assert "F1" not in registrate
            assert "Ctrl+/" not in registrate
            assert {"Ctrl+K", "Ctrl+S", "Ctrl+F", "Alt+Left"} <= registrate
        finally:
            finestra.deleteLater()

    def test_installazione_idempotente(self, app):
        """Il cambio operatore non deve accumulare scorciatoie ambigue."""
        import gui_main
        finestra = gui_main.CatastoMainWindow("127.0.0.1")
        try:
            finestra._install_shortcuts()
            quante = len(finestra._shortcut_objects)
            finestra._install_shortcuts()
            finestra._install_shortcuts()
            assert len(finestra._shortcut_objects) == quante
        finally:
            finestra.deleteLater()


class TestImportConProgresso:

    def test_worker_riporta_avanzamento_e_risultato(self, app):
        from foliarium.ui.import_progress import ImportWorker

        def importa(percorso, progress_cb=None):
            for i in range(5):
                progress_cb(i, 5)
            return {"success": list(range(5)), "errors": [], "interrotto": False}

        worker = ImportWorker(importa, "file.csv")
        avanzamenti, esiti = [], []
        worker.progresso.connect(lambda a, b: avanzamenti.append((a, b)))
        worker.finito.connect(esiti.append)
        worker.start()
        worker.wait(5000)
        app.processEvents()

        assert avanzamenti == [(0, 5), (1, 5), (2, 5), (3, 5), (4, 5)]
        assert esiti and esiti[0]["interrotto"] is False

    def test_annulla_ferma_l_elaborazione(self, app):
        """Annulla interrompe: le righe gia' inserite restano."""
        from foliarium.ui.import_progress import ImportWorker

        def importa(percorso, progress_cb=None):
            fatte = []
            for i in range(100):
                if not progress_cb(i, 100):
                    return {"success": fatte, "errors": [], "interrotto": True}
                fatte.append(i)
            return {"success": fatte, "errors": [], "interrotto": False}

        worker = ImportWorker(importa, "file.csv")
        esiti = []
        worker.finito.connect(esiti.append)
        worker.annulla()          # annullato prima ancora di partire
        worker.start()
        worker.wait(5000)
        app.processEvents()

        assert esiti and esiti[0]["interrotto"] is True
        assert esiti[0]["success"] == []

    def test_eccezione_viaggia_al_thread_gui(self, app):
        from foliarium.ui.import_progress import ImportWorker

        def importa(percorso, progress_cb=None):
            raise IOError("file illeggibile")

        worker = ImportWorker(importa, "file.csv")
        errori = []
        worker.fallito.connect(errori.append)
        worker.start()
        worker.wait(5000)
        app.processEvents()

        assert errori and isinstance(errori[0], IOError)


class TestCronologiaNavigazione:
    """Alt+Sinistra deve restare coerente anche se la navigazione è rifiutata."""

    @pytest.fixture
    def finestra(self, app):
        import gui_main
        w = gui_main.CatastoMainWindow("127.0.0.1")
        w._page_index = {"home": 0, "comuni": 1, "partite": 2}
        for _ in range(3):
            w.stack.addWidget(QWidget())
        yield w
        w.deleteLater()

    def test_senza_cronologia_avvisa_e_non_naviga(self, finestra):
        finestra._nav_history = ["home"]
        finestra._shortcut_indietro()
        assert finestra._nav_history == ["home"]

    def test_torna_alla_pagina_precedente(self, finestra, app):
        from PyQt6.QtTest import QTest

        finestra.stack.setCurrentIndex(finestra._page_index["comuni"])
        finestra._nav_history = ["home", "comuni"]
        finestra._shortcut_indietro()
        # navigate_to reinserisce la pagina raggiunta
        assert finestra._nav_history == ["home"]
        # il cambio pagina avviene al termine della dissolvenza
        QTest.qWait(400)
        assert finestra.stack.currentIndex() == finestra._page_index["home"]

    def test_cronologia_intatta_se_l_utente_annulla(self, finestra, monkeypatch):
        """Annullare al prompt non deve far saltare una pagina al giro dopo."""
        finestra.stack.setCurrentIndex(finestra._page_index["comuni"])
        finestra._nav_history = ["home", "comuni"]
        monkeypatch.setattr(type(finestra), "_confirm_leaving_page",
                            lambda self, widget, testo: False)

        finestra._shortcut_indietro()

        assert finestra._nav_history == ["home", "comuni"]
        assert finestra.stack.currentIndex() == finestra._page_index["comuni"]
