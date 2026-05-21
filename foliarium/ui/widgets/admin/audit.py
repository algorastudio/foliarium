"""Audit log: model + viewer."""
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


_AUDIT_COLS = ["ID", "Data/Ora", "Utente", "Sessione", "Tabella", "Azione", "Record", "IP"]


class AuditLogTableModel(QAbstractTableModel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._data: List[Dict[str, Any]] = []

    def load(self, logs: List[Dict[str, Any]]) -> None:
        self.beginResetModel()
        self._data = logs
        self.endResetModel()

    def log_at(self, source_row: int) -> Dict[str, Any]:
        return self._data[source_row] if 0 <= source_row < len(self._data) else {}

    def rowCount(self, parent=QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self._data)

    def columnCount(self, parent=QModelIndex()) -> int:
        return 0 if parent.isValid() else len(_AUDIT_COLS)

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if role == Qt.ItemDataRole.DisplayRole and orientation == Qt.Orientation.Horizontal:
            return _AUDIT_COLS[section] if 0 <= section < len(_AUDIT_COLS) else None
        return None

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None
        row, col = index.row(), index.column()
        if not (0 <= row < len(self._data) and 0 <= col < len(_AUDIT_COLS)):
            return None
        log = self._data[row]
        if role in (Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.EditRole):
            if col == 0:
                val = log.get('id')
                if role == Qt.ItemDataRole.EditRole and val is not None:
                    return int(val)
                return str(val) if val is not None else ''
            if col == 1:
                ts = log.get('timestamp')
                return ts.strftime("%Y-%m-%d %H:%M:%S") if ts else "N/D"
            if col == 2: return log.get('username', 'N/D') or 'N/D'
            if col == 3:
                sid = log.get('session_id', '') or ''
                return (sid[:8] + '…') if sid else ''
            if col == 4: return log.get('tabella', '') or ''
            if col == 5: return log.get('operazione', '') or ''
            if col == 6:
                val = log.get('record_id')
                if role == Qt.ItemDataRole.EditRole and val is not None:
                    try: return int(val)
                    except (ValueError, TypeError): return str(val)
                return str(val) if val is not None else ''
            if col == 7: return log.get('ip_address', '') or ''
        if role == Qt.ItemDataRole.TextAlignmentRole and col in (0, 6):
            return int(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        return None

    def flags(self, index):
        return Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable

    def sort(self, column, order=Qt.SortOrder.AscendingOrder):
        if not self._data:
            return
        _keys = {0: 'id', 1: 'timestamp', 2: 'username', 3: 'session_id',
                 4: 'tabella', 5: 'operazione', 6: 'record_id', 7: 'ip_address'}
        key = _keys.get(column, 'timestamp')
        self.layoutAboutToBeChanged.emit()
        self._data.sort(
            key=lambda r: (r.get(key) is None, r.get(key) if r.get(key) is not None else ''),
            reverse=(order == Qt.SortOrder.DescendingOrder),
        )
        self.layoutChanged.emit()




class AuditLogViewerWidget(LazyLoadedWidget):
    def __init__(self, db_manager: CatastoDBManager, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        
        # Stato per la paginazione
        self.current_page = 1
        self.page_size = 100  # Record per pagina
        self.total_records = 0
        self.total_pages = 0
        self.current_filters = {}
        
        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(10)

        title = QLabel("Registro Audit")
        title.setObjectName("pageTitle")
        main_layout.addWidget(title)
        subtitle = QLabel("Cronologia delle operazioni INSERT/UPDATE/DELETE eseguite sul database. Filtra per tabella, utente o periodo.")
        subtitle.setObjectName("pageSubtitle")
        main_layout.addWidget(subtitle)

        # === SEZIONE 1: FILTRI (più compatta) ===
        filters_group = QGroupBox("Filtri Ricerca")
        filters_group.setMaximumHeight(140)
        filters_layout = QVBoxLayout(filters_group)
        
        # Prima riga di filtri
        filters_row1 = QHBoxLayout()
        filters_row1.setSpacing(10)
        
        # Tabella
        filters_row1.addWidget(QLabel("Tabella:"))
        self.filter_table_name_edit = QLineEdit()
        self.filter_table_name_edit.setPlaceholderText("Nome tabella...")
        self.filter_table_name_edit.setMaximumWidth(150)
        filters_row1.addWidget(self.filter_table_name_edit)
        
        # Username
        filters_row1.addWidget(QLabel("Utente:"))
        self.filter_app_user_id_edit = QLineEdit()
        self.filter_app_user_id_edit.setPlaceholderText("Username...")
        self.filter_app_user_id_edit.setMaximumWidth(150)
        filters_row1.addWidget(self.filter_app_user_id_edit)
        
        # Operazione
        filters_row1.addWidget(QLabel("Operazione:"))
        self.filter_operation_combo = QComboBox()
        self.filter_operation_combo.addItems(["Tutte", "INSERT", "UPDATE", "DELETE"])
        self.filter_operation_combo.setMaximumWidth(100)
        filters_row1.addWidget(self.filter_operation_combo)
        
        filters_row1.addStretch()
        
        # Seconda riga: Date
        filters_row2 = QHBoxLayout()
        filters_row2.setSpacing(10)
        
        filters_row2.addWidget(QLabel("Da:"))
        self.filter_start_datetime_edit = QDateTimeEdit()
        self.filter_start_datetime_edit.setDateTime(QDateTime.currentDateTime().addDays(-7))
        self.filter_start_datetime_edit.setCalendarPopup(True)
        self.filter_start_datetime_edit.setDisplayFormat("dd/MM/yyyy HH:mm")
        self.filter_start_datetime_edit.setMaximumWidth(150)
        filters_row2.addWidget(self.filter_start_datetime_edit)
        
        filters_row2.addWidget(QLabel("A:"))
        self.filter_end_datetime_edit = QDateTimeEdit()
        self.filter_end_datetime_edit.setDateTime(QDateTime.currentDateTime())
        self.filter_end_datetime_edit.setCalendarPopup(True)
        self.filter_end_datetime_edit.setDisplayFormat("dd/MM/yyyy HH:mm")
        self.filter_end_datetime_edit.setMaximumWidth(150)
        filters_row2.addWidget(self.filter_end_datetime_edit)
        
        # Pulsanti filtro
        self.search_button = QPushButton("Applica")
        self.search_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogApplyButton))
        self.search_button.clicked.connect(self._apply_filters_and_search)
        self.search_button.setMaximumWidth(100)
        filters_row2.addWidget(self.search_button)
        
        self.reset_button = QPushButton("Reset")
        self.reset_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogResetButton))
        self.reset_button.clicked.connect(self._reset_filters)
        self.reset_button.setMaximumWidth(100)
        filters_row2.addWidget(self.reset_button)
        
        filters_row2.addStretch()
        
        filters_layout.addLayout(filters_row1)
        filters_layout.addLayout(filters_row2)
        main_layout.addWidget(filters_group)

        # === SEZIONE 2: AZIONI (toolbar orizzontale) ===
        actions_toolbar = QHBoxLayout()
        actions_toolbar.setSpacing(10)
        
        # Gruppo Pulizia (a sinistra)
        cleanup_frame = QFrame()
        cleanup_frame.setFrameStyle(QFrame.Shape.StyledPanel)
        cleanup_layout = QHBoxLayout(cleanup_frame)
        cleanup_layout.setContentsMargins(10, 5, 10, 5)
        
        cleanup_layout.addWidget(QLabel("Elimina log più vecchi di:"))
        self.days_to_keep_spinbox = QSpinBox()
        self.days_to_keep_spinbox.setRange(1, 3650)
        self.days_to_keep_spinbox.setValue(90)
        self.days_to_keep_spinbox.setMaximumWidth(80)
        cleanup_layout.addWidget(self.days_to_keep_spinbox)
        
        self.days_unit_combo = QComboBox()
        self.days_unit_combo.addItems(["Giorni", "Mesi", "Anni"])
        self.days_unit_combo.setMaximumWidth(80)
        cleanup_layout.addWidget(self.days_unit_combo)
        
        self.btn_cleanup_logs = QPushButton("Pulisci")
        self.btn_cleanup_logs.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_TrashIcon))
        self.btn_cleanup_logs.clicked.connect(self._confirm_and_cleanup_logs)
        cleanup_layout.addWidget(self.btn_cleanup_logs)
        
        actions_toolbar.addWidget(cleanup_frame)
        actions_toolbar.addStretch()
        
        # Gruppo Esportazione (a destra)
        export_frame = QFrame()
        export_frame.setFrameStyle(QFrame.Shape.StyledPanel)
        export_layout = QHBoxLayout(export_frame)
        export_layout.setContentsMargins(10, 5, 10, 5)
        
        self.export_csv_button = QPushButton("CSV")
        self.export_csv_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogDetailedView))
        self.export_csv_button.clicked.connect(self._handle_export_csv)
        export_layout.addWidget(self.export_csv_button)
        
        self.export_xls_button = QPushButton("Excel")
        self.export_xls_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogDetailedView))
        self.export_xls_button.clicked.connect(self._handle_export_xls)
        export_layout.addWidget(self.export_xls_button)
        
        actions_toolbar.addWidget(export_frame)
        main_layout.addLayout(actions_toolbar)

        # === SEZIONE 3: SPLITTER per tabella e dettagli ===
        splitter = QSplitter(Qt.Orientation.Vertical)
        
        # Parte superiore: Tabella con paginazione
        table_widget = QWidget()
        table_layout = QVBoxLayout(table_widget)
        table_layout.setContentsMargins(0, 0, 0, 0)
        table_layout.setSpacing(5)
        
        # Tabella risultati (model/view)
        self._audit_model = AuditLogTableModel(self)
        self.log_table = QTableView()
        self.log_table.setModel(self._audit_model)
        self.log_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.log_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.log_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.log_table.setAlternatingRowColors(True)
        self.log_table.setSortingEnabled(True)

        header = self.log_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(7, QHeaderView.ResizeMode.ResizeToContents)
        header.setStretchLastSection(False)

        self.log_table.selectionModel().selectionChanged.connect(self._display_log_details)
        self.log_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.log_table.customContextMenuRequested.connect(self._apri_menu_contestuale_log)
        table_layout.addWidget(self.log_table)
        
        # Controlli paginazione
        pagination_frame = QFrame()
        pagination_frame.setFrameStyle(QFrame.Shape.StyledPanel)
        pagination_frame.setMaximumHeight(40)
        pagination_layout = QHBoxLayout(pagination_frame)
        pagination_layout.setContentsMargins(5, 2, 5, 2)
        
        self.btn_first_page = QPushButton("<<")
        self.btn_first_page.setToolTip("Prima pagina")
        self.btn_first_page.setMaximumWidth(40)
        self.btn_first_page.clicked.connect(self._go_to_first_page)
        
        self.btn_prev_page = QPushButton("<")
        self.btn_prev_page.setToolTip("Pagina precedente")
        self.btn_prev_page.setMaximumWidth(40)
        self.btn_prev_page.clicked.connect(self._go_to_previous_page)
        
        self.page_info_label = QLabel("Pagina 1 / 1")
        self.page_info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.page_info_label.setMinimumWidth(150)
        
        self.btn_next_page = QPushButton(">")
        self.btn_next_page.setToolTip("Pagina successiva")
        self.btn_next_page.setMaximumWidth(40)
        self.btn_next_page.clicked.connect(self._go_to_next_page)
        
        self.btn_last_page = QPushButton(">>")
        self.btn_last_page.setToolTip("Ultima pagina")
        self.btn_last_page.setMaximumWidth(40)
        self.btn_last_page.clicked.connect(self._go_to_last_page)
        
        pagination_layout.addStretch()
        pagination_layout.addWidget(self.btn_first_page)
        pagination_layout.addWidget(self.btn_prev_page)
        pagination_layout.addWidget(self.page_info_label)
        pagination_layout.addWidget(self.btn_next_page)
        pagination_layout.addWidget(self.btn_last_page)
        pagination_layout.addStretch()
        
        table_layout.addWidget(pagination_frame)
        splitter.addWidget(table_widget)
        
        # Parte inferiore: Dettagli JSON
        details_widget = QWidget()
        details_widget.setMaximumHeight(200)
        details_layout = QVBoxLayout(details_widget)
        details_layout.setContentsMargins(0, 0, 0, 0)
        
        details_label = QLabel("Dettagli Modifica (seleziona una riga)")
        details_label.setObjectName("sectionLabel")
        details_layout.addWidget(details_label)
        
        details_splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Prima colonna
        before_widget = QWidget()
        before_layout = QVBoxLayout(before_widget)
        before_layout.setContentsMargins(5, 0, 5, 0)
        before_layout.addWidget(QLabel("Prima:"))
        self.details_before_text = QTextEdit()
        self.details_before_text.setReadOnly(True)
        self.details_before_text.setFont(QFont("Consolas", 9))
        before_layout.addWidget(self.details_before_text)
        
        # Seconda colonna
        after_widget = QWidget()
        after_layout = QVBoxLayout(after_widget)
        after_layout.setContentsMargins(5, 0, 5, 0)
        after_layout.addWidget(QLabel("Dopo:"))
        self.details_after_text = QTextEdit()
        self.details_after_text.setReadOnly(True)
        self.details_after_text.setFont(QFont("Consolas", 9))
        after_layout.addWidget(self.details_after_text)
        
        details_splitter.addWidget(before_widget)
        details_splitter.addWidget(after_widget)
        details_splitter.setStretchFactor(0, 1)
        details_splitter.setStretchFactor(1, 1)
        
        details_layout.addWidget(details_splitter)
        splitter.addWidget(details_widget)
        
        # Imposta proporzioni iniziali (70% tabella, 30% dettagli)
        splitter.setStretchFactor(0, 7)
        splitter.setStretchFactor(1, 3)
        
        main_layout.addWidget(splitter)

    def _load_data_on_first_show(self):
        """
        Carica i dati iniziali per il visualizzatore di log.
        Viene chiamato una sola volta quando il widget diventa visibile.
        """
        if self._data_loaded:
            return
            
        self.logger.info("AuditLogViewerWidget: Esecuzione lazy loading dei log di audit...")
        self._apply_filters_and_search()
        self._data_loaded = True
    def _get_days_from_ui_input(self) -> int:
        """Converte l'input dell'utente (giorni, mesi, anni) in giorni."""
        value = self.days_to_keep_spinbox.value()
        unit_index = self.days_unit_combo.currentIndex()
        if unit_index == 1: # Mesi
            return value * 30
        elif unit_index == 2: # Anni
            return value * 365
        return value # Giorni

    def _confirm_and_cleanup_logs(self):
        """Chiede conferma all'utente e poi avvia la pulizia dei log."""
        days_to_keep = self._get_days_from_ui_input()

        reply = QMessageBox.question(
            self,
            "Conferma Eliminazione Log di Audit",
            f"Sei sicuro di voler eliminare DEFINITIVAMENTE tutti i log di audit "
            f"più vecchi di {days_to_keep} giorni?\n\n"
            "Questa operazione non può essere annullata.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                self.logger.info(f"Avvio pulizia log di audit più vecchi di {days_to_keep} giorni.")
                QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
                deleted_count = self.db_manager.cleanup_audit_logs(days_to_keep)
                QApplication.restoreOverrideCursor()

                QMessageBox.information(
                    self,
                    "Pulizia Completata",
                    f"Pulizia dei log di audit completata con successo.\n"
                    f"Eliminati {deleted_count} record."
                )
                self._apply_filters_and_search() # Ricarica la tabella
            except DBMError as e:
                QApplication.restoreOverrideCursor()
                QMessageBox.critical(self, "Errore Pulizia Log", f"Si è verificato un errore:\n{str(e)}")
            except Exception as e:
                QApplication.restoreOverrideCursor()
                self.logger.error(f"Errore inatteso durante la pulizia dei log: {e}", exc_info=True)
                QMessageBox.critical(self, "Errore Imprevisto", f"Errore di sistema:\n{str(e)}")


    def _apply_filters_and_search(self):
        """
        Raccoglie i filtri correnti dalla UI, reimposta la paginazione
        e avvia la ricerca dei log.
        """
        self.current_filters = {
            "table_name": self.filter_table_name_edit.text().strip() or None,
            "username": self.filter_app_user_id_edit.text().strip() or None, # Ora questo campo cerca per username
            "operation_char": None,
            "app_user_id": int(self.filter_app_user_id_edit.text()) if self.filter_app_user_id_edit.text().strip().isdigit() else None,
            "start_datetime": self.filter_start_datetime_edit.dateTime().toPyDateTime(),
            "end_datetime": self.filter_end_datetime_edit.dateTime().toPyDateTime(),
        }
        op_text = self.filter_operation_combo.currentText()
        if "INSERT" in op_text:
            self.current_filters["operation_char"] = "I"
        elif "UPDATE" in op_text:
            self.current_filters["operation_char"] = "U"
        elif "DELETE" in op_text:
            self.current_filters["operation_char"] = "D"

        # Quando si applica un nuovo filtro, si torna sempre alla prima pagina
        self.current_page = 1
        self._fetch_and_display_logs()

    def _reset_filters(self):
        self.filter_table_name_edit.clear(); self.filter_operation_combo.setCurrentIndex(0)
        self.filter_app_user_id_edit.clear(); self.filter_start_datetime_edit.setDateTime(QDateTime.currentDateTime().addDays(-7))
        self.filter_end_datetime_edit.setDateTime(QDateTime.currentDateTime())
        self._apply_filters_and_search()

    def _fetch_and_display_logs(self):
        if not self.db_manager or not self.db_manager.pool:
            self._audit_model.load([])
            return
        try:
            logs, self.total_records = self.db_manager.get_audit_logs(
                filters=self.current_filters, page=self.current_page, page_size=self.page_size
            )
            self.total_pages = (self.total_records + self.page_size - 1) // self.page_size if self.total_records > 0 else 1
            self._audit_model.load(logs or [])
            self._update_pagination_controls()
        except DBMError as e:
            self._audit_model.load([])
            QMessageBox.critical(self, "Errore Database", f"Impossibile caricare i log di audit:\n{e}")

    def _update_pagination_controls(self):
        self.page_info_label.setText(f"Pagina {self.current_page} / {self.total_pages} ({self.total_records} risultati)")
        self.btn_first_page.setEnabled(self.current_page > 1)
        self.btn_prev_page.setEnabled(self.current_page > 1)
        self.btn_next_page.setEnabled(self.current_page < self.total_pages)
        self.btn_last_page.setEnabled(self.current_page < self.total_pages)

    def _go_to_first_page(self): self.current_page = 1; self._fetch_and_display_logs()
    def _go_to_previous_page(self): self.current_page -= 1; self._fetch_and_display_logs()
    def _go_to_next_page(self): self.current_page += 1; self._fetch_and_display_logs()
    def _go_to_last_page(self): self.current_page = self.total_pages; self._fetch_and_display_logs()

    def _display_log_details(self):
        selected_rows = self.log_table.selectionModel().selectedRows()
        if not selected_rows:
            self.details_before_text.clear()
            self.details_after_text.clear()
            return
        source_row = selected_rows[0].row()
        log_entry = self._audit_model.log_at(source_row)
        if not log_entry:
            self.details_before_text.clear()
            self.details_after_text.clear()
            return
        d_before = log_entry.get('dati_prima')
        d_after = log_entry.get('dati_dopo')
        self.details_before_text.setText(json.dumps(d_before, indent=4, ensure_ascii=False) if d_before else "")
        self.details_after_text.setText(json.dumps(d_after, indent=4, ensure_ascii=False) if d_after else "")

    def _handle_export_csv(self):
        logs, total = self.db_manager.get_audit_logs(filters=self.current_filters, page=1, page_size=10000) # Esporta fino a 10000 record
        if not logs: QMessageBox.warning(self, "Nessun Dato", "Nessun log da esportare per i filtri correnti."); return
        filename, _ = QFileDialog.getSaveFileName(self, "Esporta Log in CSV", f"audit_log_{date.today()}.csv", "File CSV (*.csv)")
        if not filename: return
        try:
            headers = logs[0].keys()
            with open(filename, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=headers, delimiter=';'); writer.writeheader(); writer.writerows(logs)
            _show_status_message(f"{len(logs)} record di audit esportati in CSV.", 5000)
        except Exception as e: QMessageBox.critical(self, "Errore Esportazione", f"Errore durante l'esportazione CSV:\n{e}")

    def _handle_export_xls(self):
        logs, total = self.db_manager.get_audit_logs(filters=self.current_filters, page=1, page_size=10000)
        if not logs: QMessageBox.warning(self, "Nessun Dato", "Nessun log da esportare."); return
        filename, _ = QFileDialog.getSaveFileName(self, "Esporta Log in Excel", f"audit_log_{date.today()}.xlsx", "File Excel (*.xlsx)")
        if not filename: return
        try:
            import pandas as pd
            df = pd.DataFrame(logs); df.to_excel(filename, index=False, engine='openpyxl')
            _show_status_message(f"{len(logs)} record di audit esportati in Excel.", 5000)
        except ImportError: QMessageBox.critical(self, "Libreria Mancante", "L'esportazione in Excel richiede 'pandas' e 'openpyxl'.")
        except Exception as e: QMessageBox.critical(self, "Errore Esportazione", f"Errore durante l'esportazione Excel:\n{e}")

    def _apri_menu_contestuale_log(self, position: QPoint):
        """Context menu sulla tabella audit log."""
        index = self.log_table.indexAt(position)
        if not index.isValid():
            return
        row = index.row()
        log = self._audit_model.log_at(row)
        if not log:
            return
        id_text = str(log.get('id', '') or '')
        utente_text = log.get('username', '') or ''
        azione_text = log.get('operazione', '') or ''
        ip_text = log.get('ip_address', '') or ''

        menu = QMenu(self.log_table)
        if id_text:
            menu.addAction(f"Copia ID  ({id_text})").triggered.connect(
                lambda: QApplication.clipboard().setText(id_text))
        if utente_text:
            menu.addAction(f"Copia utente  ({utente_text})").triggered.connect(
                lambda: QApplication.clipboard().setText(utente_text))
        if azione_text:
            menu.addAction(f"Copia azione  ({azione_text})").triggered.connect(
                lambda: QApplication.clipboard().setText(azione_text))
        if ip_text:
            menu.addAction(f"Copia IP  ({ip_text})").triggered.connect(
                lambda: QApplication.clipboard().setText(ip_text))
        menu.addSeparator()

        def _copia_riga():
            parts = []
            for col in range(self._audit_model.columnCount()):
                idx = self._audit_model.index(row, col)
                val = self._audit_model.data(idx, Qt.ItemDataRole.DisplayRole)
                parts.append(str(val) if val is not None else "")
            QApplication.clipboard().setText("\t".join(parts))
        menu.addAction("Copia riga intera").triggered.connect(_copia_riga)
        menu.exec(self.log_table.viewport().mapToGlobal(position))




