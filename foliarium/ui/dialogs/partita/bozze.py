"""
foliarium/ui/dialogs/partita/bozze.py — Dialog per gestire le bozze del
wizard Nuova Partita (lista, ripresa, eliminazione).
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

logger = logging.getLogger("CatastoGUI.bozze_dialog")


class BozzePartitaDialog(QDialog):
    """Dialog di selezione di una bozza salvata.

    Mostra le bozze dell'utente corrente con timestamp ultima modifica,
    permette di riprenderne una o eliminarla. Espone:
      - selected_draft_id: int | None       — id della bozza scelta
      - selected_draft_payload: dict | None — payload della bozza scelta
    """

    def __init__(self, db_manager, utente_id: Optional[int], parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.utente_id = utente_id

        self.selected_draft_id: Optional[int] = None
        self.selected_draft_payload: Optional[Dict[str, Any]] = None

        self._drafts: List[Dict[str, Any]] = []

        self.setWindowTitle("Bozze salvate — Nuova Partita")
        self.setMinimumSize(640, 360)
        self._build_ui()
        self._reload()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        layout.addWidget(QLabel("Seleziona una bozza da riprendere:"))

        self._table = QTableWidget()
        self._table.setColumnCount(3)
        self._table.setHorizontalHeaderLabels(["Titolo", "Creata", "Ultima modifica"])
        self._table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Interactive)
        self._table.horizontalHeader().setStretchLastSection(True)
        self._table.itemDoubleClicked.connect(lambda *_: self._accept_selected())
        layout.addWidget(self._table, 1)

        actions_row = QHBoxLayout()
        self._btn_delete = QPushButton("Elimina")
        self._btn_delete.setObjectName("secondaryButton")
        self._btn_delete.clicked.connect(self._delete_selected)
        actions_row.addWidget(self._btn_delete)
        actions_row.addStretch()
        layout.addLayout(actions_row)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Riprendi")
        buttons.accepted.connect(self._accept_selected)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _reload(self):
        try:
            self._drafts = self.db_manager.list_partita_drafts(self.utente_id) or []
        except Exception as e:
            logger.error(f"Errore caricamento bozze: {e}", exc_info=True)
            QMessageBox.critical(
                self, "Errore", f"Impossibile caricare le bozze:\n{e}")
            self._drafts = []

        self._table.setRowCount(0)
        for d in self._drafts:
            row = self._table.rowCount()
            self._table.insertRow(row)
            titolo_item = QTableWidgetItem(d.get("titolo") or "(senza titolo)")
            titolo_item.setData(Qt.ItemDataRole.UserRole, d.get("id"))
            self._table.setItem(row, 0, titolo_item)
            created = d.get("created_at")
            updated = d.get("updated_at")
            self._table.setItem(
                row, 1,
                QTableWidgetItem(created.strftime("%d/%m/%Y %H:%M") if created else ""))
            self._table.setItem(
                row, 2,
                QTableWidgetItem(updated.strftime("%d/%m/%Y %H:%M") if updated else ""))

        if self._drafts:
            self._table.selectRow(0)

    def _current_draft_id(self) -> Optional[int]:
        row = self._table.currentRow()
        if row < 0:
            return None
        item = self._table.item(row, 0)
        if not item:
            return None
        return item.data(Qt.ItemDataRole.UserRole)

    def _accept_selected(self):
        draft_id = self._current_draft_id()
        if draft_id is None:
            QMessageBox.information(
                self, "Selezione", "Seleziona una bozza dall'elenco.")
            return
        try:
            full = self.db_manager.load_partita_draft(
                int(draft_id), utente_id=self.utente_id)
        except Exception as e:
            logger.error(f"Errore caricamento bozza {draft_id}: {e}", exc_info=True)
            QMessageBox.critical(
                self, "Errore", f"Impossibile caricare la bozza:\n{e}")
            return

        self.selected_draft_id = int(full["id"])
        self.selected_draft_payload = full.get("payload") or {}
        self.accept()

    def _delete_selected(self):
        draft_id = self._current_draft_id()
        if draft_id is None:
            return
        reply = QMessageBox.question(
            self, "Elimina bozza",
            "Eliminare definitivamente la bozza selezionata?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No)
        if reply != QMessageBox.StandardButton.Yes:
            return
        try:
            self.db_manager.delete_partita_draft(
                int(draft_id), utente_id=self.utente_id)
        except Exception as e:
            logger.error(f"Errore eliminazione bozza {draft_id}: {e}", exc_info=True)
            QMessageBox.critical(
                self, "Errore", f"Impossibile eliminare la bozza:\n{e}")
            return
        self._reload()
