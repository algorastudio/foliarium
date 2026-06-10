"""
tests/unit/test_top_bar_api_indicator.py
========================================
Test del nuovo indicatore API in TopBarWidget (foliarium/ui/top_bar.py).

Verifica:
* set_api_status(running=True, port=N) imposta testo verde con porta visibile.
* set_api_status(error="...") imposta testo errore + tooltip.
* set_api_status(running=False) torna allo stato off.
* Click sull'indicatore emette api_status_clicked.
"""

from __future__ import annotations

import pytest


try:
    from PyQt6.QtCore import Qt  # noqa: F401
    _QT_OK = True
except ImportError:
    _QT_OK = False


pytestmark = [
    pytest.mark.unit,
    pytest.mark.gui,
    pytest.mark.skipif(not _QT_OK, reason="PyQt6 non disponibile"),
]


@pytest.fixture
def app():
    from PyQt6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


class TestApiIndicator:

    def test_default_state_is_off(self, qtbot, app):
        from foliarium.ui.top_bar import TopBarWidget
        bar = TopBarWidget()
        qtbot.addWidget(bar)
        assert bar._api_indicator.text() == "● API: off"
        assert bar._api_indicator.property("apiStatus") == "off"

    def test_running_shows_port(self, qtbot, app):
        from foliarium.ui.top_bar import TopBarWidget
        bar = TopBarWidget()
        qtbot.addWidget(bar)
        bar.set_api_status(running=True, port=8765)
        assert "8765" in bar._api_indicator.text()
        assert "on" in bar._api_indicator.text().lower()
        assert bar._api_indicator.property("apiStatus") == "running"

    def test_error_sets_tooltip(self, qtbot, app):
        from foliarium.ui.top_bar import TopBarWidget
        bar = TopBarWidget()
        qtbot.addWidget(bar)
        bar.set_api_status(running=False, error="Porta 8765 occupata")
        assert bar._api_indicator.property("apiStatus") == "error"
        assert "Porta 8765 occupata" in bar._api_indicator.toolTip()
        assert "errore" in bar._api_indicator.text().lower()

    def test_off_reset(self, qtbot, app):
        from foliarium.ui.top_bar import TopBarWidget
        bar = TopBarWidget()
        qtbot.addWidget(bar)
        bar.set_api_status(running=True, port=8765)
        bar.set_api_status(running=False)
        assert bar._api_indicator.text() == "● API: off"
        assert bar._api_indicator.property("apiStatus") == "off"

    def test_click_emits_signal(self, qtbot, app):
        from foliarium.ui.top_bar import TopBarWidget

        bar = TopBarWidget()
        qtbot.addWidget(bar)
        captured = []
        bar.api_status_clicked.connect(lambda: captured.append(True))

        # L'handler è collegato come mousePressEvent dell'indicatore.
        # Lo invoco direttamente: il contratto da verificare è il segnale,
        # non l'event-loop di Qt.
        bar._on_api_indicator_clicked(None)
        assert captured == [True]
