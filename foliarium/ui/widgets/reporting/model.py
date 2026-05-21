"""Model tabellare generico per le viste di reporting."""
from __future__ import annotations

import os
import csv
import logging
from datetime import date, datetime
from typing import Optional, List, Dict, Any, TYPE_CHECKING

import pandas as pd

from PyQt6.QtCore import (
    QAbstractTableModel, QDate, QModelIndex, QPoint, Qt, QUrl,
)
from PyQt6.QtGui import (
    QDesktopServices,
)
from PyQt6.QtWidgets import (
    QAbstractItemView, QApplication,
    QComboBox, QDateEdit, QDialog, QFileDialog,
    QFormLayout, QFrame, QGridLayout, QGroupBox,
    QHBoxLayout, QHeaderView, QLabel,
    QLineEdit, QMenu, QMessageBox, QProgressDialog,
    QPushButton, QSpinBox, QStyle, QTabWidget,
    QTableView, QTextBrowser, QTextEdit, QVBoxLayout,
    QWidget,
)

from app_utils import BulkReportPDF, FPDF_AVAILABLE, GenericTextReportPDF, _get_default_export_path
from catasto_exceptions import DBMError, DBDataError, DBNotFoundError, DBUniqueConstraintError  # noqa: F401
from dialogs import (
    AlberoGeneralogicoDialog, ConfrontoPartiteDialog,
    ComuneSelectionDialog, PartitaSearchDialog, PossessoreSelectionDialog,
)
from foliarium.ui.widgets.custom import LazyLoadedWidget

if TYPE_CHECKING:
    from catasto_db_manager import CatastoDBManager

logger = logging.getLogger("CatastoGUI.reporting_widgets")


class SimpleRowsModel(QAbstractTableModel):
    """Modello generico per tabelle read-only: ogni riga è una list[Any]."""

    def __init__(self, headers: List[str], parent=None, numeric_cols: Optional[List[int]] = None):
        super().__init__(parent)
        self._headers = list(headers)
        self._rows: List[List[Any]] = []
        self._numeric_cols = set(numeric_cols or [])

    def load(self, rows: List[List[Any]]) -> None:
        self.beginResetModel()
        self._rows = [list(r) for r in rows]
        self.endResetModel()

    def row_at(self, row: int) -> List[Any]:
        return self._rows[row] if 0 <= row < len(self._rows) else []

    def cell(self, row: int, col: int) -> Any:
        r = self.row_at(row)
        return r[col] if 0 <= col < len(r) else None

    def row_count(self) -> int:
        return len(self._rows)

    def rowCount(self, parent=QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self._rows)

    def columnCount(self, parent=QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self._headers)

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if role == Qt.ItemDataRole.DisplayRole and orientation == Qt.Orientation.Horizontal:
            return self._headers[section] if 0 <= section < len(self._headers) else None
        return None

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None
        row, col = index.row(), index.column()
        if not (0 <= row < len(self._rows) and 0 <= col < len(self._headers)):
            return None
        values = self._rows[row]
        val = values[col] if col < len(values) else None
        if role in (Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.EditRole):
            if role == Qt.ItemDataRole.EditRole and col in self._numeric_cols:
                try:
                    return float(val)
                except (ValueError, TypeError):
                    return 0.0
            return str(val) if val is not None else ''
        if role == Qt.ItemDataRole.TextAlignmentRole and col in self._numeric_cols:
            return int(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        return None

    def flags(self, index):
        return Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable

    def sort(self, column, order=Qt.SortOrder.AscendingOrder):
        if not self._rows or column >= len(self._headers):
            return
        self.layoutAboutToBeChanged.emit()
        numeric = column in self._numeric_cols
        def _key(r):
            v = r[column] if column < len(r) else None
            if numeric:
                try:
                    return (False, float(v))
                except (ValueError, TypeError):
                    return (True, 0.0)
            return (v is None, v if v is not None else '')
        self._rows.sort(key=_key, reverse=(order == Qt.SortOrder.DescendingOrder))
        self.layoutChanged.emit()




