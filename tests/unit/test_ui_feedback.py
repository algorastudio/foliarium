"""
tests/unit/test_ui_feedback.py
==============================
Unit test dei riscontri che l'interfaccia deve dare all'utente:

  - campi obbligatori mancanti segnalati, non ignorati in silenzio
  - ogni voce di navigazione descritta da un tooltip
  - date mostrate nel formato italiano

Sono i comportamenti introdotti dalla revisione euristica: senza test
tornerebbero a regredire alla prima modifica dei form.
"""

from __future__ import annotations

import os
import sys

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:
    from PyQt6.QtWidgets import QApplication, QLineEdit, QVBoxLayout, QWidget
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
def form(app):
    """Un form visibile con tre campi: il focus richiede una finestra mostrata."""
    w = QWidget()
    layout = QVBoxLayout(w)
    campi = [QLineEdit(), QLineEdit(), QLineEdit()]
    for c in campi:
        layout.addWidget(c)
    w.show()
    app.processEvents()
    yield w, campi
    w.close()


@pytest.fixture
def status_messages(monkeypatch):
    """Cattura i messaggi diretti alla status bar."""
    from foliarium.ui.widgets import insertion
    catturati = []
    monkeypatch.setattr(
        insertion, "_show_status_message",
        lambda msg, timeout_ms=4000: catturati.append(msg),
    )
    return catturati


class TestCheckRequired:

    def test_tutti_compilati_passa_e_pulisce_gli_errori(self, form, status_messages):
        from foliarium.ui.widgets.insertion import _check_required
        _, (a, b, _c) = form
        a.setText("Savona")
        b.setText("SV")

        assert _check_required([(a, True, "Nome"), (b, True, "Provincia")]) is True
        assert a.property("error") == "false"
        assert b.property("error") == "false"
        assert status_messages == []

    def test_campo_mancante_marcato_e_annunciato(self, form, status_messages):
        from foliarium.ui.widgets.insertion import _check_required
        _, (a, b, _c) = form
        b.setText("SV")

        assert _check_required([(a, False, "Nome Comune"), (b, True, "Provincia")]) is False
        assert a.property("error") == "true"
        assert b.property("error") == "false"
        assert status_messages == ["Campo obbligatorio mancante: Nome Comune."]

    def test_piu_campi_mancanti_elencati_tutti(self, form, status_messages):
        from foliarium.ui.widgets.insertion import _check_required
        _, (a, b, c) = form

        _check_required([
            (a, False, "Nome Comune"),
            (b, True, "Provincia"),
            (c, False, "Regione"),
        ])
        assert status_messages == ["Campi obbligatori mancanti: Nome Comune, Regione."]

    def test_focus_sul_primo_campo_mancante(self, form, status_messages, app):
        from foliarium.ui.widgets.insertion import _check_required
        _, (a, b, c) = form
        c.setFocus()
        app.processEvents()

        _check_required([
            (a, False, "Nome Comune"),
            (b, True, "Provincia"),
            (c, False, "Regione"),
        ])
        app.processEvents()
        assert a.hasFocus(), "il focus deve portare l'utente sul primo campo da compilare"


class TestSidebarTooltip:

    @pytest.mark.parametrize("is_admin", [False, True])
    def test_ogni_voce_ha_tooltip_e_statustip(self, app, is_admin):
        from foliarium.ui.sidebar import SidebarWidget
        sidebar = SidebarWidget()
        sidebar.build_nav(is_admin=is_admin, fuzzy_available=True)

        assert sidebar._buttons, "la navigazione non deve essere vuota"
        senza_tooltip = [p for p, b in sidebar._buttons.items() if not b.toolTip()]
        assert senza_tooltip == []
        senza_statustip = [p for p, b in sidebar._buttons.items() if not b.statusTip()]
        assert senza_statustip == []


class TestFormatiData:

    def test_formato_italiano(self):
        from config import DATE_DISPLAY_FORMAT, DATETIME_DISPLAY_FORMAT
        assert DATE_DISPLAY_FORMAT == "dd/MM/yyyy"
        assert DATETIME_DISPLAY_FORMAT.startswith("dd/MM/yyyy")

    def test_nessun_qdateedit_usa_il_formato_iso(self):
        """I QDateEdit devono passare dalla costante, non da un letterale ISO."""
        import pathlib
        radice = pathlib.Path(__file__).resolve().parents[2]
        colpevoli = []
        for percorso in radice.rglob("*.py"):
            if "tests" in percorso.parts or ".git" in percorso.parts:
                continue
            if 'setDisplayFormat("yyyy-MM-dd' in percorso.read_text(encoding="utf-8"):
                colpevoli.append(str(percorso.relative_to(radice)))
        assert colpevoli == []


class TestManualeTemaScuro:

    @pytest.mark.parametrize("dark", [False, True])
    def test_css_dichiara_sempre_sfondo_e_testo(self, dark):
        from foliarium.ui.dialogs.admin.help_viewer import (
            _HELP_PALETTES, _build_help_css,
        )
        css = _build_help_css(dark)
        palette = _HELP_PALETTES["dark" if dark else "light"]
        assert f"background-color: {palette['bg']}" in css
        assert f"color: {palette['fg']}" in css

    def test_i_due_temi_hanno_sfondi_diversi(self):
        from foliarium.ui.dialogs.admin.help_viewer import _build_help_css
        assert _build_help_css(False) != _build_help_css(True)


class TestAiutoContestuale:
    """F1 deve aprire la sezione che riguarda la schermata in uso."""

    def test_ogni_documento_mappato_esiste(self):
        import pathlib
        import gui_main
        radice = pathlib.Path(__file__).resolve().parents[2] / "docs"
        mancanti = [
            doc for doc in gui_main.CatastoMainWindow._AIUTO_CONTESTUALE.values()
            if not (radice / doc).exists()
        ]
        assert mancanti == []

    def test_le_pagine_principali_sono_coperte(self):
        import gui_main
        mappa = gui_main.CatastoMainWindow._AIUTO_CONTESTUALE
        attese = {"home", "comuni", "partite", "immobili", "ins_comune",
                  "ins_possessore", "esportazioni", "report", "statistiche",
                  "utenti", "backup"}
        assert attese <= set(mappa)


class TestRicercaNelManuale:

    @pytest.fixture
    def manuale(self, app):
        from foliarium.ui.dialogs.admin.help_viewer import HelpViewerDialog
        dlg = HelpViewerDialog()
        yield dlg
        dlg.deleteLater()

    def test_apertura_su_una_pagina_specifica(self, app):
        from foliarium.ui.dialogs.admin.help_viewer import HelpViewerDialog
        dlg = HelpViewerDialog(pagina_iniziale="inserimento.md")
        try:
            assert dlg._history[dlg._history_pos] == "inserimento.md"
        finally:
            dlg.deleteLater()

    def test_termine_presente_trova_pagine(self, manuale):
        risultati = manuale._raccogli_risultati("possessore")
        assert risultati, "il manuale parla di possessori: la ricerca deve trovarli"
        for percorso, titolo, estratto in risultati:
            assert percorso.endswith(".md")
            assert titolo
            assert "<b>" in estratto   # il termine è evidenziato

    def test_termine_assente_non_trova_nulla(self, manuale):
        assert manuale._raccogli_risultati("qwertyzxcvb") == []

    def test_pagina_dei_risultati_vuota_lo_dice(self, manuale):
        manuale.search_edit.setText("qwertyzxcvb")
        manuale._cerca_nel_manuale()
        assert "Nessun risultato" in manuale.content.toPlainText()

    def test_query_troppo_corta_non_cerca(self, manuale):
        manuale._load_page("index.md")
        prima = manuale.lbl_title.text()
        manuale.search_edit.setText("a")
        manuale._cerca_nel_manuale()
        assert manuale.lbl_title.text() == prima

    def test_link_dei_risultati_sono_relativi_alla_radice(self, manuale):
        """Un risultato aperto da una sottocartella non va risolto lì."""
        from PyQt6.QtCore import QUrl

        manuale._load_page("admin/backup.md")
        manuale._on_link_clicked(QUrl("foliarium-doc:inserimento.md"))
        assert manuale._history[manuale._history_pos] == "inserimento.md"

    def test_i_link_interni_restano_relativi_al_documento(self, manuale):
        from PyQt6.QtCore import QUrl

        manuale._load_page("admin/backup.md")
        manuale._on_link_clicked(QUrl("index.md"))
        assert manuale._history[manuale._history_pos] == "admin/index.md"


class TestAccessibilitaModuli:

    @pytest.fixture(params=["comune", "possessore", "localita", "partita"])
    def modulo(self, request, app):
        from unittest.mock import MagicMock
        from foliarium.ui.widgets.insertion import (
            InserimentoComuneWidget, InserimentoLocalitaWidget,
            InserimentoPartitaWidget, InserimentoPossessoreWidget,
        )
        db = MagicMock()
        db.get_elenco_comuni_semplice.return_value = [(1, "Savona")]
        db.get_historical_periods.return_value = []
        costruttori = {
            "comune": lambda: InserimentoComuneWidget(db, {"username": "u"}),
            "possessore": lambda: InserimentoPossessoreWidget(db),
            "localita": lambda: InserimentoLocalitaWidget(db),
            "partita": lambda: InserimentoPartitaWidget(db),
        }
        w = costruttori[request.param]()
        for metodo in ("load_initial_data", "_load_data_on_first_show"):
            if hasattr(w, metodo):
                getattr(w, metodo)()
                break
        yield w
        w.deleteLater()

    def test_ogni_campo_ha_un_nome_accessibile(self, modulo):
        """Senza nome accessibile uno screen reader annuncia 'casella di testo'."""
        from PyQt6.QtWidgets import (QComboBox, QDateEdit, QLineEdit, QSpinBox,
                                     QTextEdit, QWidget)
        tipi = (QLineEdit, QComboBox, QTextEdit, QSpinBox, QDateEdit)
        senza_nome = [
            c.objectName() or type(c).__name__
            for c in modulo.findChildren(QWidget)
            if isinstance(c, tipi) and not c.accessibleName()
            and not c.objectName().startswith("qt_")
        ]
        assert senza_nome == []

    def test_nessun_mnemonic_in_conflitto(self, modulo):
        """Due pulsanti con la stessa lettera rendono la scorciatoia inutile."""
        import re
        from PyQt6.QtWidgets import QPushButton

        lettere = [
            m.group(1).lower()
            for b in modulo.findChildren(QPushButton)
            if (m := re.search(r"&(\w)", b.text()))
        ]
        assert len(lettere) == len(set(lettere)), f"lettere ripetute: {lettere}"

    #: Primo campo che il tab deve raggiungere in ciascun modulo.
    PRIMO_CAMPO = {
        "InserimentoComuneWidget": "nome_comune_edit",
        "InserimentoPossessoreWidget": "cognome_nome_edit",
        "InserimentoLocalitaWidget": "comune_button",
        "InserimentoPartitaWidget": "comune_combo",
    }

    def test_l_ordine_di_tabulazione_parte_dal_primo_campo(self, modulo, app):
        """Chi naviga da tastiera deve entrare dal campo in cima al modulo.

        Nei layout a griglia l'ordine di tabulazione segue la costruzione,
        non la posizione: se divergesse servirebbe un setTabOrder esplicito.
        """
        from PyQt6.QtCore import Qt
        from PyQt6.QtWidgets import QWidget

        modulo.show()
        app.processEvents()
        atteso = getattr(modulo, self.PRIMO_CAMPO[type(modulo).__name__])
        raggiungibili = [
            c for c in modulo.findChildren(QWidget)
            if c.focusPolicy() != Qt.FocusPolicy.NoFocus and c.isVisible()
            and not c.objectName().startswith("qt_")
        ]
        assert raggiungibili[0] is atteso, (
            f"il tab entra da {type(raggiungibili[0]).__name__} invece che "
            f"da {self.PRIMO_CAMPO[type(modulo).__name__]}"
        )
