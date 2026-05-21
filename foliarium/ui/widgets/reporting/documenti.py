"""Widget ricerca full-text documenti storici."""
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
from foliarium.ui.widgets.reporting.model import SimpleRowsModel


class RicercaDocumentiWidget(QWidget):
    """Pannello di ricerca full-text nei documenti storici catastali."""

    COLONNE = ["ID", "Titolo", "Tipo", "Anno", "Comune", "Partita", "Note"]
    KEYS    = ["id", "titolo", "tipo", "anno", "comune_nome", "numero_partita", "note"]

    def __init__(self, db_manager, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.logger = logging.getLogger(f"CatastoGUI.{self.__class__.__name__}")
        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(12)

        title = QLabel("Ricerca Documenti")
        title.setObjectName("pageTitle")
        main_layout.addWidget(title)
        subtitle = QLabel("Cerca tra i documenti storici catastali per parole chiave, tipo e anno.")
        subtitle.setObjectName("pageSubtitle")
        main_layout.addWidget(subtitle)

        # --- Filtri ---
        filtri_group = QGroupBox("Criteri di Ricerca Documenti Storici")
        filtri_layout = QGridLayout(filtri_group)
        filtri_layout.setSpacing(8)

        # Riga 0: Parole chiave titolo
        filtri_layout.addWidget(QLabel("Parole chiave (titolo):"), 0, 0)
        self.titolo_edit = QLineEdit()
        self.titolo_edit.setPlaceholderText("Es. catasto, registro, voltura… (lascia vuoto per tutti)")
        self.titolo_edit.returnPressed.connect(self._esegui_ricerca)
        filtri_layout.addWidget(self.titolo_edit, 0, 1, 1, 3)

        # Riga 1: Tipo documento
        filtri_layout.addWidget(QLabel("Tipo documento:"), 1, 0)
        self.tipo_combo = QComboBox()
        self.tipo_combo.addItem("— Qualsiasi tipo —", None)
        for t in ["Catasto", "Voltura", "Frazionamento", "Successione", "Atto notarile", "Altro"]:
            self.tipo_combo.addItem(t, t)
        filtri_layout.addWidget(self.tipo_combo, 1, 1)

        # Riga 1: Anno da / a
        filtri_layout.addWidget(QLabel("Anno da:"), 1, 2)
        self.anno_da_spin = QSpinBox()
        self.anno_da_spin.setRange(0, 2100)
        self.anno_da_spin.setValue(0)
        self.anno_da_spin.setSpecialValueText("—")
        filtri_layout.addWidget(self.anno_da_spin, 1, 3)

        filtri_layout.addWidget(QLabel("Anno a:"), 2, 2)
        self.anno_a_spin = QSpinBox()
        self.anno_a_spin.setRange(0, 2100)
        self.anno_a_spin.setValue(0)
        self.anno_a_spin.setSpecialValueText("—")
        filtri_layout.addWidget(self.anno_a_spin, 2, 3)

        # Riga 2: ID partita opzionale
        filtri_layout.addWidget(QLabel("ID Partita (opz.):"), 2, 0)
        self.partita_id_spin = QSpinBox()
        self.partita_id_spin.setRange(0, 9999999)
        self.partita_id_spin.setValue(0)
        self.partita_id_spin.setSpecialValueText("—")
        filtri_layout.addWidget(self.partita_id_spin, 2, 1)

        main_layout.addWidget(filtri_group)

        # --- Pulsanti ---
        btn_layout = QHBoxLayout()
        self.btn_cerca = QPushButton("Cerca")
        self.btn_cerca.setIcon(QApplication.style().standardIcon(QStyle.StandardPixmap.SP_DialogApplyButton))
        self.btn_cerca.clicked.connect(self._esegui_ricerca)
        self.btn_reset = QPushButton("Reset Filtri")
        self.btn_reset.clicked.connect(self._reset_filtri)
        self.risultati_label = QLabel("Nessuna ricerca eseguita.")
        btn_layout.addWidget(self.btn_cerca)
        btn_layout.addWidget(self.btn_reset)
        btn_layout.addStretch()
        btn_layout.addWidget(self.risultati_label)
        main_layout.addLayout(btn_layout)

        # --- Tabella risultati (model/view) ---
        self._docs_model = SimpleRowsModel(self.COLONNE, parent=self, numeric_cols=[0, 3])
        self.tabella = QTableView()
        self.tabella.setModel(self._docs_model)
        self.tabella.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tabella.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tabella.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.tabella.setAlternatingRowColors(True)
        hdr = self.tabella.horizontalHeader()
        hdr.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        hdr.setStretchLastSection(True)
        self.tabella.setSortingEnabled(True)
        self.tabella.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tabella.customContextMenuRequested.connect(self._apri_menu_documento)
        main_layout.addWidget(self.tabella, 1)

    def _apri_menu_documento(self, position: QPoint):
        index = self.tabella.indexAt(position)
        if not index.isValid():
            return
        row = index.row()
        def _cell(col):
            val = self._docs_model.cell(row, col)
            return str(val) if val is not None else ""
        id_doc, titolo, _tipo, anno, _comune, partita = (
            _cell(0), _cell(1), _cell(2), _cell(3), _cell(4), _cell(5)
        )
        menu = QMenu(self.tabella)
        menu.addAction(f"Copia titolo: {titolo[:40]}{'…' if len(titolo)>40 else ''}").triggered.connect(
            lambda: QApplication.clipboard().setText(titolo))
        if anno:
            menu.addAction(f"Copia anno: {anno}").triggered.connect(
                lambda: QApplication.clipboard().setText(anno))
        if partita:
            menu.addAction(f"Copia partita: {partita}").triggered.connect(
                lambda: QApplication.clipboard().setText(partita))
        menu.addAction(f"Copia ID: {id_doc}").triggered.connect(
            lambda: QApplication.clipboard().setText(id_doc))
        menu.exec(self.tabella.viewport().mapToGlobal(position))

    def _esegui_ricerca(self):
        titolo = self.titolo_edit.text().strip() or None
        tipo = self.tipo_combo.currentData()
        anno_da = self.anno_da_spin.value() or None
        anno_a = self.anno_a_spin.value() or None
        partita_id = self.partita_id_spin.value() or None

        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            risultati = self.db_manager.search_historical_documents(
                title=titolo,
                doc_type=tipo,
                year_start=anno_da,
                year_end=anno_a,
                partita_id=partita_id,
            )
        except Exception as e:
            self.logger.error(f"Errore ricerca documenti: {e}", exc_info=True)
            risultati = []
        finally:
            QApplication.restoreOverrideCursor()

        self._popola_tabella(risultati)

    def _popola_tabella(self, righe: list):
        if not righe:
            self._docs_model.load([])
            self.risultati_label.setText("Nessun documento trovato.")
            return
        rows = []
        for row in righe:
            if isinstance(row, dict):
                rows.append([row.get(key, '') for key in self.KEYS])
            else:
                rows.append([row[c] if c < len(row) else '' for c in range(len(self.KEYS))])
        self._docs_model.load(rows)
        self.risultati_label.setText(f"{len(rows)} documenti trovati.")
        self.risultati_label.setText(f"{len(righe)} documento/i trovato/i.")

    def _reset_filtri(self):
        self.titolo_edit.clear()
        self.tipo_combo.setCurrentIndex(0)
        self.anno_da_spin.setValue(0)
        self.anno_a_spin.setValue(0)
        self.partita_id_spin.setValue(0)
        self.tabella.setRowCount(0)
        self.risultati_label.setText("Nessuna ricerca eseguita.")




