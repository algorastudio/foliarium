"""Dialog selezione possessore."""

import logging
import os
from datetime import date
from typing import Optional, Dict, Any

from PyQt6.QtCore import (QDate, Qt, QTimer)
from PyQt6.QtGui import (QBrush, QColor)
from PyQt6.QtWidgets import (QAbstractItemView, QApplication,
                             QCheckBox, QComboBox, QDateEdit,
                             QDialog, QDoubleSpinBox,
                             QFileDialog, QFormLayout, QGridLayout, QGroupBox,
                             QHBoxLayout, QHeaderView, QLabel, QLineEdit,
                             QMessageBox, QPushButton, QSpinBox, QStyle,
                             QTabWidget, QSplitter, QTableWidget,
                             QTableWidgetItem, QTextEdit, QTreeWidget, QTreeWidgetItem,
                             QVBoxLayout, QWidget, QTextBrowser,
                             QDialogButtonBox)

from catasto_db_manager import CatastoDBManager
from foliarium.ui.widgets.custom import ImmobiliTableWidget

from app_utils import (GenericTextReportPDF, FPDF_AVAILABLE, prompt_to_open_file)
from foliarium.ui.dialogs.export_ import PDFApreviewDialog

from foliarium.ui.dialogs.admin import datetime_to_qdate, qdate_to_datetime

try:
    from catasto_db_manager import DBMError, DBUniqueConstraintError, DBNotFoundError, DBDataError
except ImportError:
    class DBMError(Exception): pass
    class DBUniqueConstraintError(DBMError): pass
    class DBNotFoundError(DBMError): pass
    class DBDataError(DBMError): pass


class PossessoreSelectionDialog(QDialog):
    def __init__(self, db_manager: CatastoDBManager, comune_id: Optional[int], parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        # comune_id ora è un filtro iniziale opzionale, non un requisito fisso
        self.comune_id_filter = comune_id
        self.selected_possessore = None
        self.logger = logging.getLogger(f"CatastoGUI.{self.__class__.__name__}")

        self.setWindowTitle("Seleziona o Crea Possessore")
        self.setMinimumSize(700, 500)

        self._initUI()
        self.load_data()

    def _initUI(self):
        layout = QVBoxLayout(self)
        self.tabs = QTabWidget()

        # --- Tab 1: Seleziona Esistente ---
        select_tab = QWidget()
        select_layout = QVBoxLayout(select_tab)
        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("Filtra per nome:"))
        self.filter_edit = QLineEdit()
        self.filter_edit.setPlaceholderText("Digita per filtrare su tutti i comuni...")
        self.filter_edit.textChanged.connect(self.filter_possessori)
        filter_layout.addWidget(self.filter_edit)
        select_layout.addLayout(filter_layout)

        self.possessori_table = QTableWidget()
        # Aggiungiamo il comune di riferimento alla tabella
        self.possessori_table.setColumnCount(5)
        self.possessori_table.setHorizontalHeaderLabels(["ID", "Nome Completo", "Paternità", "Comune Riferimento", "Stato"])
        self.possessori_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.possessori_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.possessori_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.possessori_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.possessori_table.itemDoubleClicked.connect(self.handle_selection)
        select_layout.addWidget(self.possessori_table)
        self.tabs.addTab(select_tab, "Seleziona Esistente")

        # --- Tab 2: Crea Nuovo ---
        create_tab = QWidget()
        create_layout = QFormLayout(create_tab)
        self.cognome_edit = QLineEdit()
        create_layout.addRow("Cognome e Nome (*):", self.cognome_edit)
        self.paternita_edit = QLineEdit()
        create_layout.addRow("Paternità:", self.paternita_edit)
        self.nome_completo_edit = QLineEdit()
        create_layout.addRow("Nome Completo (*):", self.nome_completo_edit)

        # --- MODIFICA CHIAVE: Combo per selezionare il comune del NUOVO possessore ---
        self.new_poss_comune_combo = QComboBox()
        create_layout.addRow("Comune di Riferimento (*):", self.new_poss_comune_combo)

        self.attivo_checkbox = QCheckBox("Attivo")
        self.attivo_checkbox.setChecked(True)
        create_layout.addRow(self.attivo_checkbox)
        self.tabs.addTab(create_tab, "Crea Nuovo")

        layout.addWidget(self.tabs)

        buttons_layout = QHBoxLayout()
        self.ok_button = QPushButton("Seleziona")
        self.ok_button.clicked.connect(self.handle_selection)
        buttons_layout.addWidget(self.ok_button)
        self.cancel_button = QPushButton("Annulla")
        self.cancel_button.clicked.connect(self.reject)
        buttons_layout.addWidget(self.cancel_button)
        layout.addLayout(buttons_layout)

    def load_data(self):
        """Carica i dati per entrambi i tab (lista possessori e lista comuni)."""
        self._load_possessori_for_table()
        self._load_comuni_for_combo()

    def _load_possessori_for_table(self, filter_text=None):
        self.possessori_table.setRowCount(0)
        try:
            # Se è stato passato un comune_id, filtra per quello. Altrimenti, ricerca globale.
            if self.comune_id_filter:
                possessori_list = self.db_manager.get_possessori_by_comune(self.comune_id_filter, filter_text)
            else:
                possessori_list = self.db_manager.search_possessori_by_term_globally(filter_text)

            self.possessori_table.setRowCount(len(possessori_list))
            for row, pos_data in enumerate(possessori_list):
                self.possessori_table.setItem(row, 0, QTableWidgetItem(str(pos_data.get('id', ''))))
                self.possessori_table.setItem(row, 1, QTableWidgetItem(pos_data.get('nome_completo', '')))
                self.possessori_table.setItem(row, 2, QTableWidgetItem(pos_data.get('paternita', '')))
                self.possessori_table.setItem(row, 3, QTableWidgetItem(pos_data.get('comune_riferimento_nome', '')))
                self.possessori_table.setItem(row, 4, QTableWidgetItem("Attivo" if pos_data.get('attivo', False) else "Non Attivo"))
            self.possessori_table.resizeColumnsToContents()
        except DBMError as e:
            QMessageBox.critical(self, "Errore", f"Impossibile caricare i possessori: {e}")

    def _load_comuni_for_combo(self):
        self.new_poss_comune_combo.clear()
        try:
            comuni = self.db_manager.get_elenco_comuni_semplice()
            self.new_poss_comune_combo.addItem("--- Seleziona Comune ---", None)
            for id, nome in comuni:
                self.new_poss_comune_combo.addItem(nome, id)
        except DBMError:
            self.new_poss_comune_combo.addItem("Errore caricamento", None)

    def filter_possessori(self):
        self._load_possessori_for_table(self.filter_edit.text().strip())

    def handle_selection(self):
        if self.tabs.currentIndex() == 0: # Tab "Seleziona Esistente"
            selected = self.possessori_table.selectedItems()
            if not selected:
                QMessageBox.warning(self, "Nessuna Selezione", "Seleziona un possessore dalla tabella.")
                return
            row = selected[0].row()
            id_poss = int(self.possessori_table.item(row, 0).text())
            # Recuperiamo tutti i dettagli per assicurarci di averli
            self.selected_possessore = self.db_manager.get_possessore_full_details(id_poss)
            self.accept()

        elif self.tabs.currentIndex() == 1: # Tab "Crea Nuovo"
            nome_completo = self.nome_completo_edit.text().strip()
            cognome_nome = self.cognome_edit.text().strip()
            paternita = self.paternita_edit.text().strip() or None
            comune_id = self.new_poss_comune_combo.currentData()

            if not nome_completo or not cognome_nome or comune_id is None:
                QMessageBox.warning(self, "Dati Mancanti", "Nome completo, Cognome/Nome e Comune sono obbligatori.")
                return

            try:
                new_id = self.db_manager.create_possessore(
                    nome_completo=nome_completo,
                    cognome_nome=cognome_nome,
                    paternita=paternita,
                    comune_riferimento_id=comune_id,
                    attivo=self.attivo_checkbox.isChecked()
                )
                self.selected_possessore = self.db_manager.get_possessore_full_details(new_id)
                QMessageBox.information(self, "Successo", f"Nuovo possessore '{nome_completo}' creato con successo.")
                self.accept()
            except (DBMError, DBUniqueConstraintError) as e:
                QMessageBox.critical(self, "Errore Creazione", str(e))

