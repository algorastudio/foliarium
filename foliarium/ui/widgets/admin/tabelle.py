"""Tabelle di sistema: tipi localita, periodi storici, tipi possesso."""
from __future__ import annotations

import csv
import json
import os
import logging
from datetime import date
from typing import Optional, Dict, List, Any, TYPE_CHECKING

from PyQt6.QtCore import (
    QAbstractTableModel, QDateTime, QModelIndex, QPoint, QProcess, QProcessEnvironment,
    QSettings, QSortFilterProxyModel, Qt, pyqtSlot,
)
from PyQt6.QtGui import QColor, QFont
from PyQt6.QtWidgets import (
    QAbstractItemView, QApplication,
    QComboBox, QDateTimeEdit, QDialog, QDialogButtonBox,
    QFileDialog, QFormLayout, QFrame, QGroupBox, QHBoxLayout, QHeaderView,
    QInputDialog, QLabel, QLineEdit, QMenu,
    QMessageBox, QProgressBar, QPushButton, QSpinBox, QStyle,
    QTabWidget, QTableView, QTableWidget, QTableWidgetItem,
    QTextEdit, QVBoxLayout, QWidget,
    QSplitter,
)

from catasto_exceptions import (
    DBMError, DBUniqueConstraintError, DBDataError,
)
from foliarium.ui.widgets.custom import LazyLoadedWidget
from dialogs import (
    CreateUserDialog, PeriodoStoricoEditDialog,
    _hash_password,
)

if TYPE_CHECKING:
    from catasto_db_manager import CatastoDBManager

logger = logging.getLogger("CatastoGUI.admin_widgets")


from foliarium.ui.widgets.custom import show_status_message as _show_status_message


class GestioneTipiLocalitaWidget(LazyLoadedWidget):
    def __init__(self, db_manager: 'CatastoDBManager', parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self._initUI()

    def _initUI(self):
        layout = QVBoxLayout(self)
        group = QGroupBox("Gestione Tipologie Località (Via, Piazza, Borgata, etc.)")
        group_layout = QHBoxLayout(group)

        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["ID", "Nome Tipologia", "Descrizione"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        group_layout.addWidget(self.table, 2)

        button_layout = QVBoxLayout()
        btn_add = QPushButton("Aggiungi...")
        btn_add.clicked.connect(self._add_or_edit_item)
        btn_edit = QPushButton("Modifica...")
        btn_edit.clicked.connect(lambda: self._add_or_edit_item(edit_mode=True))
        btn_del = QPushButton("Elimina")
        btn_del.clicked.connect(self._delete_item)
        
        # Aggiungiamo un pulsante di refresh manuale per coerenza
        btn_refresh = QPushButton(QApplication.style().standardIcon(QStyle.StandardPixmap.SP_BrowserReload), " Aggiorna")
        btn_refresh.clicked.connect(self.load_data)

        button_layout.addWidget(btn_add)
        button_layout.addWidget(btn_edit)
        button_layout.addWidget(btn_del)
        button_layout.addSpacing(20)
        button_layout.addWidget(btn_refresh)
        button_layout.addStretch()
        group_layout.addLayout(button_layout, 1)

        layout.addWidget(group)
        self.setLayout(layout)


    def load_data(self):
        """
        Metodo pubblico per caricare o ricaricare i dati delle tipologie di località.
        """
        self.logger.info("Esecuzione di load_data in GestioneTipiLocalitaWidget.")
        self.table.setRowCount(0)
        try:
            tipi = self.db_manager.get_tipi_localita()
            for tipo in tipi:
                row = self.table.rowCount()
                self.table.insertRow(row)
                self.table.setItem(row, 0, QTableWidgetItem(str(tipo['id'])))
                self.table.setItem(row, 1, QTableWidgetItem(tipo['nome']))
                self.table.setItem(row, 2, QTableWidgetItem(tipo.get('descrizione', '')))
            self.table.resizeColumnToContents(0) # Adatta solo la colonna ID
        except DBMError as e:
            QMessageBox.critical(self, "Errore Caricamento", str(e))

    def _load_data_on_first_show(self):
        """
        Metodo per il lazy loading, chiamato dalla classe base.
        Delega il lavoro al metodo pubblico `load_data`.
        """
        self.load_data()


    def _add_or_edit_item(self, edit_mode=False):
        tipo_id, old_nome, old_desc = None, "", ""
        if edit_mode:
            selected_items = self.table.selectedItems()
            if not selected_items:
                QMessageBox.warning(self, "Selezione Mancante", "Seleziona una tipologia da modificare.")
                return
            row = selected_items[0].row()
            tipo_id = int(self.table.item(row, 0).text())
            old_nome = self.table.item(row, 1).text()
            old_desc = self.table.item(row, 2).text()
        
        nome, ok = QInputDialog.getText(self, "Tipologia Località", "Nome:", text=old_nome)
        if ok and nome:
            desc, ok2 = QInputDialog.getText(self, "Tipologia Località", "Descrizione (opzionale):", text=old_desc)
            if ok2:
                try:
                    self.db_manager.gestisci_tipo_localita(tipo_id, nome, desc)
                    self.load_data()
                except (DBMError, DBDataError, DBUniqueConstraintError) as e:
                    QMessageBox.critical(self, "Errore", str(e))

    def _delete_item(self):
        selected_items = self.table.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "Selezione Mancante", "Seleziona una tipologia da eliminare.")
            return
        
        row = selected_items[0].row()
        tipo_id = int(self.table.item(row, 0).text())
        nome = self.table.item(row, 1).text()

        reply = QMessageBox.question(self, "Conferma Eliminazione", f"Sei sicuro di voler eliminare la tipologia '{nome}'?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            try:
                self.db_manager.elimina_tipo_localita(tipo_id)
                self.load_data()
            except DBMError as e:
                QMessageBox.critical(self, "Errore Eliminazione", str(e))


class GestionePeriodiStoriciWidget(LazyLoadedWidget):
    def __init__(self, db_manager: 'CatastoDBManager', parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        # Il self.logger è già gestito dalla classe base LazyLoadedWidget
        self._initUI()

    def _initUI(self):
        layout = QVBoxLayout(self)
        group = QGroupBox("Gestione Periodi Storici")
        group_layout = QHBoxLayout(group)

        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["ID", "Nome Periodo", "Anno Inizio-Fine", "Descrizione"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        group_layout.addWidget(self.table)

        button_layout = QVBoxLayout()
        btn_refresh = QPushButton(QApplication.style().standardIcon(QStyle.StandardPixmap.SP_BrowserReload), " Aggiorna Lista")
        btn_refresh.clicked.connect(self.load_data) # Ora si collega al metodo corretto
        btn_add = QPushButton(QApplication.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogNewFolder), " Aggiungi...")
        btn_add.clicked.connect(self._add_or_edit_item)
        btn_edit = QPushButton(QApplication.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogDetailedView), " Modifica...")
        btn_edit.clicked.connect(lambda: self._add_or_edit_item(edit_mode=True))
        btn_del = QPushButton(QApplication.style().standardIcon(QStyle.StandardPixmap.SP_TrashIcon), " Elimina")
        btn_del.clicked.connect(self._delete_item)
        
        button_layout.addWidget(btn_refresh)
        button_layout.addSpacing(20)
        button_layout.addWidget(btn_add)
        button_layout.addWidget(btn_edit)
        button_layout.addWidget(btn_del)
        button_layout.addStretch()
        group_layout.addLayout(button_layout)

        layout.addWidget(group)

    def _load_data_on_first_show(self):
        """Metodo per il lazy loading, chiamato la prima volta."""
        self.load_data()

    def load_data(self):
        """Carica o ricarica i dati dei periodi storici nella tabella."""
        self.logger.info("Caricamento dati per GestionePeriodiStoriciWidget...")
        self.table.setSortingEnabled(False)
        self.table.setRowCount(0)
        try:
            periodi = self.db_manager.get_historical_periods()
            self.table.setRowCount(len(periodi))
            for row, periodo in enumerate(periodi):
                # Salviamo l'intero dizionario del periodo nell'item ID per un facile accesso
                id_item = QTableWidgetItem(str(periodo['id']))
                id_item.setData(Qt.ItemDataRole.UserRole, periodo)
                self.table.setItem(row, 0, id_item)
                
                self.table.setItem(row, 1, QTableWidgetItem(periodo['nome']))
                
                anno_fine = periodo.get('anno_fine') or 'in corso'
                self.table.setItem(row, 2, QTableWidgetItem(f"{periodo['anno_inizio']} - {anno_fine}"))
                
                self.table.setItem(row, 3, QTableWidgetItem(periodo.get('descrizione', '')))
            self.table.resizeColumnsToContents()
        except DBMError as e:
            QMessageBox.critical(self, "Errore di Caricamento", str(e))
        finally:
            self.table.setSortingEnabled(True)

    def _add_or_edit_item(self, edit_mode=False):
        periodo_data = None
        if edit_mode:
            selected_items = self.table.selectedItems()
            if not selected_items:
                QMessageBox.warning(self, "Selezione Mancante", "Seleziona un periodo da modificare.")
                return
            # Prendi i dati salvati nell'item
            periodo_data = self.table.item(selected_items[0].row(), 0).data(Qt.ItemDataRole.UserRole)
        
        dialog = PeriodoStoricoEditDialog(self.db_manager, periodo_data, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.load_data() # Ricarica la lista dopo la modifica/aggiunta

    def _delete_item(self):
        selected_items = self.table.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "Selezione Mancante", "Seleziona un periodo da eliminare.")
            return
        
        periodo_data = self.table.item(selected_items[0].row(), 0).data(Qt.ItemDataRole.UserRole)
        periodo_id = periodo_data['id']
        nome = periodo_data['nome']

        reply = QMessageBox.question(self, "Conferma Eliminazione", f"Sei sicuro di voler eliminare il periodo '{nome}'?\nQuesta operazione è possibile solo se il periodo non è utilizzato.", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            try:
                self.db_manager.elimina_periodo_storico(periodo_id)
                self.load_data()
            except DBMError as e:
                QMessageBox.critical(self, "Errore Eliminazione", str(e))




class TipiPossessoWidget(LazyLoadedWidget):
    """Gestione tipi di possesso (proprietà esclusiva, comproprietà, usufrutto, etc.)"""

    def __init__(self, db_manager: 'CatastoDBManager', parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self._init_ui()

    def _load_data_on_first_show(self):
        self.load_data()

    def _init_ui(self):
        main_layout = QVBoxLayout()

        title = QLabel("Tipi di Possesso Disponibili")
        title.setObjectName("pageTitle")
        main_layout.addWidget(title)

        # Tabella tipi possesso
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["ID", "Nome", "Descrizione"])
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        main_layout.addWidget(self.table)

        # Bottoni
        buttons_layout = QHBoxLayout()
        btn_nuovo = QPushButton("Aggiungi Tipo")
        btn_nuovo.clicked.connect(self._aggiungi_tipo)
        buttons_layout.addWidget(btn_nuovo)

        btn_modifica = QPushButton("Modifica Selezionato")
        btn_modifica.clicked.connect(self._modifica_tipo)
        btn_modifica.setEnabled(False)
        self.btn_modifica = btn_modifica
        buttons_layout.addWidget(btn_modifica)

        btn_elimina = QPushButton("Elimina Selezionato")
        btn_elimina.setObjectName("dangerButton")
        btn_elimina.clicked.connect(self._elimina_tipo)
        btn_elimina.setEnabled(False)
        self.btn_elimina = btn_elimina
        buttons_layout.addWidget(btn_elimina)

        buttons_layout.addStretch()
        main_layout.addLayout(buttons_layout)

        self.setLayout(main_layout)
        self.table.itemSelectionChanged.connect(self._on_selection_changed)

    def load_data(self):
        """Carica i tipi di possesso dal database."""
        self.table.setRowCount(0)
        try:
            tipi = self.db_manager.get_tipi_possesso()
            for i, tipo in enumerate(tipi):
                self.table.insertRow(i)
                self.table.setItem(i, 0, QTableWidgetItem(str(tipo['id'])))
                self.table.setItem(i, 1, QTableWidgetItem(tipo['nome']))
                self.table.setItem(i, 2, QTableWidgetItem(tipo.get('descrizione') or ''))
        except Exception as e:
            self.logger.error(f"Errore caricamento tipi possesso: {e}")
            QMessageBox.critical(self, "Errore", f"Impossibile caricare i tipi di possesso:\n{e}")

    def _on_selection_changed(self):
        """Abilita/disabilita i bottoni modifica/elimina."""
        has_selection = self.table.currentRow() >= 0
        self.btn_modifica.setEnabled(has_selection)
        self.btn_elimina.setEnabled(has_selection)

    def _aggiungi_tipo(self):
        """Aggiunge un nuovo tipo di possesso."""
        dialog = QDialog(self)
        dialog.setWindowTitle("Aggiungi Tipo di Possesso")
        dialog.setMinimumWidth(400)

        layout = QFormLayout(dialog)
        nome_edit = QLineEdit()
        layout.addRow("Nome (*):", nome_edit)
        descrizione_edit = QTextEdit()
        descrizione_edit.setMinimumHeight(80)
        layout.addRow("Descrizione:", descrizione_edit)

        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)
        layout.addRow(button_box)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            nome = nome_edit.text().strip()
            descrizione = descrizione_edit.toPlainText().strip() or None

            if not nome:
                QMessageBox.warning(self, "Dato Mancante", "Il nome è obbligatorio.")
                return

            try:
                self.db_manager.insert_tipo_possesso(nome, descrizione)
                self.load_data()
                _show_status_message(f"Tipo '{nome}' aggiunto.", 4000)
            except Exception as e:
                QMessageBox.critical(self, "Errore", f"Impossibile aggiungere il tipo:\n{e}")

    def _modifica_tipo(self):
        """Modifica il tipo selezionato."""
        row = self.table.currentRow()
        if row < 0:
            return

        tipo_id = int(self.table.item(row, 0).text())
        nome_attuale = self.table.item(row, 1).text()
        descrizione_attuale = self.table.item(row, 2).text() or ''

        dialog = QDialog(self)
        dialog.setWindowTitle(f"Modifica Tipo: {nome_attuale}")
        dialog.setMinimumWidth(400)

        layout = QFormLayout(dialog)
        nome_edit = QLineEdit()
        nome_edit.setText(nome_attuale)
        layout.addRow("Nome (*):", nome_edit)
        descrizione_edit = QTextEdit()
        descrizione_edit.setMinimumHeight(80)
        descrizione_edit.setPlainText(descrizione_attuale)
        layout.addRow("Descrizione:", descrizione_edit)

        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)
        layout.addRow(button_box)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            nome = nome_edit.text().strip()
            descrizione = descrizione_edit.toPlainText().strip() or None

            if not nome:
                QMessageBox.warning(self, "Dato Mancante", "Il nome è obbligatorio.")
                return

            try:
                self.db_manager.update_tipo_possesso(tipo_id, nome, descrizione)
                self.load_data()
                _show_status_message(f"Tipo '{nome}' aggiornato.", 4000)
            except Exception as e:
                QMessageBox.critical(self, "Errore", f"Impossibile aggiornare il tipo:\n{e}")

    def _elimina_tipo(self):
        """Elimina il tipo selezionato."""
        row = self.table.currentRow()
        if row < 0:
            return

        tipo_id = int(self.table.item(row, 0).text())
        nome = self.table.item(row, 1).text()

        risposta = QMessageBox.question(
            self, "Conferma Eliminazione",
            f"Eliminare il tipo '{nome}'?\n\n"
            "Questa azione non può essere annullata se il tipo non è in uso.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if risposta != QMessageBox.StandardButton.Yes:
            return

        try:
            self.db_manager.delete_tipo_possesso(tipo_id)
            self.load_data()
            _show_status_message(f"Tipo '{nome}' eliminato.", 4000)
        except Exception as e:
            QMessageBox.critical(self, "Errore", f"Impossibile eliminare il tipo:\n{e}")


class TabelleDiSistemaWidget(QWidget):
    """Pagina unificata per le tabelle di lookup del sistema.

    Raggruppa in un solo QTabWidget i tre widget di gestione:
      - Tipi di possesso  (TipiPossessoWidget)
      - Tipi di località  (GestioneTipiLocalitaWidget)
      - Periodi storici   (GestionePeriodiStoriciWidget)

    Sostituisce le tre voci sidebar separate per ridurre il rumore di
    navigazione: queste sono operazioni di configurazione poco frequenti.
    """

    def __init__(self, db_manager: 'CatastoDBManager', parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        intro = QLabel(
            "<b>Tabelle di sistema</b> — gestione delle tabelle di lookup "
            "utilizzate dal database (tipi di possesso, tipi di località, "
            "periodi storici). Modifiche poco frequenti, riservate agli amministratori."
        )
        intro.setWordWrap(True)
        intro.setObjectName("pageSubtitle")
        layout.addWidget(intro)

        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)

        self.tipi_possesso_tab = TipiPossessoWidget(self.db_manager)
        self.tipi_localita_tab = GestioneTipiLocalitaWidget(self.db_manager)
        self.periodi_tab = GestionePeriodiStoriciWidget(self.db_manager)

        self.tabs.addTab(self.tipi_possesso_tab, "Tipi di possesso")
        self.tabs.addTab(self.tipi_localita_tab, "Tipi di località")
        self.tabs.addTab(self.periodi_tab, "Periodi storici")

        layout.addWidget(self.tabs, 1)


