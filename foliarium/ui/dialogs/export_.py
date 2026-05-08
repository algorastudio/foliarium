"""
foliarium/ui/dialogs/export_.py — Dialog di anteprima per le esportazioni.
"""
from __future__ import annotations

from typing import List, Any

from PyQt6.QtWidgets import (
    QAbstractItemView, QDialog, QDialogButtonBox,
    QTableWidget, QTableWidgetItem, QTextEdit, QVBoxLayout,
)


class PDFApreviewDialog(QDialog):
    """Anteprima testuale prima di procedere con l'esportazione PDF."""

    def __init__(self, text_content: str, parent=None, title: str = "Anteprima Esportazione PDF"):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumSize(700, 500)

        layout = QVBoxLayout(self)
        self.text_preview = QTextEdit()
        self.text_preview.setReadOnly(True)
        self.text_preview.setFontFamily("Courier New")
        self.text_preview.setPlainText(text_content)
        layout.addWidget(self.text_preview)

        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.button(QDialogButtonBox.StandardButton.Ok).setText("Procedi con Esportazione PDF")
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)


class CSVApreviewDialog(QDialog):
    """Anteprima tabellare prima di procedere con l'esportazione CSV."""

    def __init__(
        self,
        headers: List[str],
        data_rows: List[List[Any]],
        parent=None,
        title: str = "Anteprima Esportazione CSV",
    ):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumSize(600, 400)

        layout = QVBoxLayout(self)
        table = QTableWidget()
        table.setColumnCount(len(headers))
        table.setHorizontalHeaderLabels(headers)
        table.setAlternatingRowColors(True)
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        table.setRowCount(len(data_rows))
        for r, row_data in enumerate(data_rows):
            for c, cell in enumerate(row_data):
                table.setItem(r, c, QTableWidgetItem(str(cell)))
        table.resizeColumnsToContents()
        layout.addWidget(table)

        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.button(QDialogButtonBox.StandardButton.Ok).setText("Procedi con Esportazione")
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
