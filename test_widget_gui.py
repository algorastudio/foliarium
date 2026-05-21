import sys
import pytest
from PyQt6.QtWidgets import QApplication
from unittest.mock import MagicMock
from foliarium.ui.widgets.genealogia_widget import GenealogiaTimelineWidget, GenealogiaNodeWidget

def test_genealogia_timeline_widget():
    app = QApplication(sys.argv)

    mock_db = MagicMock()
    mock_db.get_genealogia_partita.return_value = {
        "partita": {"id": 2, "numero_partita": 100, "stato": "attiva"},
        "predecessori": [{"id": 1, "numero_partita": 99, "stato": "chiusa"}],
        "successori": [{"id": 3, "numero_partita": 101, "stato": "attiva"}]
    }

    widget = GenealogiaTimelineWidget(mock_db)
    widget.load_partita(2)

    # Check
    assert widget.current_partita_id == 2
    mock_db.get_genealogia_partita.assert_called_once_with(2)

    print("Test passato con successo.")

test_genealogia_timeline_widget()
