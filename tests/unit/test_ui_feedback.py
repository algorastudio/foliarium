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
