"""
foliarium/ui/widgets/comuni.py — Elenco e gestione comuni.

Estratto da gui_widgets.py (Sprint 3.8 refactor — six-hats).

Contiene:
- _ComuniLoaderWorker (QThread): carica l'elenco comuni in background
- ComuniTableModel (QAbstractTableModel): modello tabellare per QTableView
- ElencoComuniWidget (LazyLoadedWidget): vista lista con filtro + azioni
"""

from __future__ import annotations

import logging
from typing import Optional, Tuple, TYPE_CHECKING

from PyQt6.QtCore import (
    QAbstractTableModel,
    QModelIndex,
    QPoint,
    QSortFilterProxyModel,
    Qt,
    QThread,
    pyqtSignal,
)
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QDialog,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMenu,
    QMessageBox,
    QPushButton,
    QStyle,
    QTableView,
    QVBoxLayout,
)

from dialogs import (
    LocalitaSelectionDialog,
    ModificaComuneDialog,
    PartiteComuneDialog,
    PossessoriComuneDialog,
)
from foliarium.ui.widgets.custom import LazyLoadedWidget, show_status_message as _show_status_message

if TYPE_CHECKING:
    from catasto_db_manager import CatastoDBManager  # noqa: F401


class _ComuniLoaderWorker(QThread):
    """Carica l'elenco comuni dal DB in background per non bloccare la UI."""
    results_ready = pyqtSignal(list)
    error_occurred = pyqtSignal(str)

    def __init__(self, db_manager, parent=None):
        super().__init__(parent)
        self._db = db_manager

    def run(self):
        try:
            result = self._db.get_all_comuni_details()
            self.results_ready.emit(result or [])
        except Exception as e:
            self.error_occurred.emit(str(e))


_COMUNI_COLS = [
    "ID", "Nome Comune", "Cod. Catastale", "Provincia",
    "Data Istituzione", "Data Soppressione", "Note",
]


class ComuniTableModel(QAbstractTableModel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._data: list[dict] = []

    def load(self, comuni: list[dict]) -> None:
        self.beginResetModel()
        self._data = comuni
        self.endResetModel()

    def comune_id_at(self, source_row: int) -> Optional[int]:
        if 0 <= source_row < len(self._data):
            return self._data[source_row].get('id')
        return None

    def comune_name_at(self, source_row: int) -> str:
        if 0 <= source_row < len(self._data):
            return self._data[source_row].get('nome_comune', '')
        return ''

    def row_count(self) -> int:
        return len(self._data)

    def rowCount(self, parent=QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self._data)

    def columnCount(self, parent=QModelIndex()) -> int:
        return 0 if parent.isValid() else len(_COMUNI_COLS)

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if role == Qt.ItemDataRole.DisplayRole and orientation == Qt.Orientation.Horizontal:
            return _COMUNI_COLS[section] if 0 <= section < len(_COMUNI_COLS) else None
        return None

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None
        row, col = index.row(), index.column()
        if not (0 <= row < len(self._data) and 0 <= col < len(_COMUNI_COLS)):
            return None
        comune = self._data[row]
        if role in (Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.EditRole):
            if col == 0:
                val = comune.get('id')
                return int(val) if (role == Qt.ItemDataRole.EditRole and val is not None) else (str(val) if val is not None else '')
            if col == 1: return comune.get('nome_comune', '') or ''
            if col == 2: return comune.get('codice_catastale', '') or ''
            if col == 3: return comune.get('provincia', '') or ''
            if col == 4:
                d = comune.get('data_istituzione')
                return str(d) if d else ''
            if col == 5:
                d = comune.get('data_soppressione')
                return str(d) if d else ''
            if col == 6: return comune.get('note', '') or ''
        if role == Qt.ItemDataRole.TextAlignmentRole and col == 0:
            return int(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        return None

    def flags(self, index):
        return Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable

    def sort(self, column, order=Qt.SortOrder.AscendingOrder):
        if not self._data:
            return
        _keys = {
            0: 'id', 1: 'nome_comune', 2: 'codice_catastale',
            3: 'provincia', 4: 'data_istituzione', 5: 'data_soppressione', 6: 'note',
        }
        key = _keys.get(column, 'nome_comune')
        self.layoutAboutToBeChanged.emit()
        self._data.sort(
            key=lambda r: (r.get(key) is None, r.get(key) or ''),
            reverse=(order == Qt.SortOrder.DescendingOrder),
        )
        self.layoutChanged.emit()


class ElencoComuniWidget(LazyLoadedWidget):
    def __init__(self, db_manager: 'CatastoDBManager', parent=None):
        super().__init__(parent)
        self.logger.debug("Inizializzazione di ElencoComuniWidget")
        if db_manager:
            self.db_manager = db_manager
            self.logger.info(f"Widget inizializzato CORRETTAMENTE con DBManager (ID Oggetto: {id(self.db_manager)})")
        else:
            self.db_manager = None
            self.logger.error("ERRORE CRITICO: ElencoComuniWidget inizializzato SENZA un DBManager valido!")
            QMessageBox.critical(self, "Errore Widget", "Il widget dei comuni non ha ricevuto il gestore del database.")
            return

        layout = QVBoxLayout(self)

        comuni_group = QGroupBox("Elenco Comuni Registrati")
        comuni_layout = QVBoxLayout(comuni_group)

        self.filter_comuni_edit = QLineEdit()
        self.filter_comuni_edit.setPlaceholderText("Filtra per nome, provincia...")
        self.filter_comuni_edit.textChanged.connect(self.apply_filter)
        comuni_layout.addWidget(self.filter_comuni_edit)

        self._comuni_model = ComuniTableModel(self)
        self._comuni_proxy = QSortFilterProxyModel(self)
        self._comuni_proxy.setSourceModel(self._comuni_model)
        self._comuni_proxy.setFilterCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self._comuni_proxy.setFilterKeyColumn(-1)

        self.comuni_table = QTableView()
        self.comuni_table.setModel(self._comuni_proxy)
        self.comuni_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.comuni_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.comuni_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.comuni_table.setAlternatingRowColors(True)
        self.comuni_table.setSortingEnabled(True)
        _hdr = self.comuni_table.horizontalHeader()
        _hdr.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        _hdr.setStretchLastSection(True)
        self.comuni_table.setColumnWidth(0, 45)
        self.comuni_table.setColumnWidth(1, 200)
        self.comuni_table.setColumnWidth(2, 110)
        self.comuni_table.setColumnWidth(3, 80)
        self.comuni_table.setColumnWidth(4, 120)
        self.comuni_table.setColumnWidth(5, 120)
        self.comuni_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.comuni_table.customContextMenuRequested.connect(self.apri_menu_contestuale_comune)
        self.comuni_table.selectionModel().selectionChanged.connect(self._update_action_buttons_state)

        self._loading_lbl = QLabel("Caricamento in corso…")
        self._loading_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._loading_lbl.setObjectName("pageSubtitle")
        self._loading_lbl.setVisible(False)
        comuni_layout.addWidget(self._loading_lbl)
        comuni_layout.addWidget(self.comuni_table)

        action_buttons_layout = QHBoxLayout()

        self.btn_modifica_comune = QPushButton("Modifica Comune Selezionato")
        self.btn_modifica_comune.clicked.connect(self.azione_modifica_comune)
        self.btn_modifica_comune.setEnabled(False)
        action_buttons_layout.addWidget(self.btn_modifica_comune)
        self.btn_mostra_partite = QPushButton("Mostra Partite del Comune Selezionato")
        self.btn_mostra_partite.clicked.connect(self.azione_mostra_partite)
        action_buttons_layout.addWidget(self.btn_mostra_partite)

        self.btn_mostra_possessori = QPushButton("Mostra Possessori del Comune Selezionato")
        self.btn_mostra_possessori.clicked.connect(self.azione_mostra_possessori)
        action_buttons_layout.addWidget(self.btn_mostra_possessori)

        self.btn_mostra_localita = QPushButton("Mostra Località del Comune Selezionato")
        self.btn_mostra_localita.clicked.connect(self.azione_mostra_localita)
        action_buttons_layout.addWidget(self.btn_mostra_localita)

        action_buttons_layout.addStretch()

        self.btn_archivia_comune = QPushButton("Archivia Comune")
        self.btn_archivia_comune.setObjectName("dangerButton")
        self.btn_archivia_comune.setEnabled(False)
        self.btn_archivia_comune.setToolTip("Archivia il comune selezionato (non viene eliminato, solo nascosto)")
        self.btn_archivia_comune.clicked.connect(self._azione_archivia_comune)
        action_buttons_layout.addWidget(self.btn_archivia_comune)
        comuni_layout.addLayout(action_buttons_layout)
        layout.addWidget(comuni_group)
        self.setLayout(layout)

        self.logger.info("Chiamata a load_comuni_data() da __init__.")

    def load_data(self):
        """Avvia il caricamento dell'elenco comuni in background (non blocca la UI)."""
        if not self.db_manager:
            self.logger.error("load_data chiamato ma self.db_manager è None!")
            return
        if hasattr(self, '_loader') and self._loader.isRunning():
            return

        self._comuni_model.load([])
        self._loading_lbl.setVisible(True)
        self.comuni_table.setVisible(False)
        self.filter_comuni_edit.setEnabled(False)

        self._loader = _ComuniLoaderWorker(self.db_manager, self)
        self._loader.results_ready.connect(self._on_comuni_loaded)
        self._loader.error_occurred.connect(self._on_comuni_error)
        self._loader.start()
        self.logger.debug("_ComuniLoaderWorker avviato.")

    def _on_comuni_loaded(self, comuni_list: list):
        self._comuni_model.load(comuni_list)
        self._loading_lbl.setVisible(False)
        self.comuni_table.setVisible(True)
        self.filter_comuni_edit.setEnabled(True)
        if not comuni_list:
            self.logger.warning("Nessun comune restituito dal DB.")
        else:
            self.comuni_table.resizeColumnsToContents()
            self.comuni_table.setColumnWidth(0, 45)
        self.logger.debug("Tabella comuni popolata con %d righe.", len(comuni_list))

    def _on_comuni_error(self, error_msg: str):
        self._loading_lbl.setVisible(False)
        self.comuni_table.setVisible(True)
        self.filter_comuni_edit.setEnabled(True)
        self.logger.error("Errore caricamento comuni: %s", error_msg)
        QMessageBox.critical(self, "Errore Caricamento Dati",
                             f"Impossibile caricare l'elenco dei comuni:\n{error_msg}")

    def _load_data_on_first_show(self):
        """Hook per il lazy loading della classe base."""
        self.load_data()

    def _slot_modifica_dati_comune(self, comune_id: int):
        self.logger.info(f"Menu contestuale: richiesta modifica per comune ID {comune_id}")
        dialog = ModificaComuneDialog(self.db_manager, comune_id, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.logger.info(f"Dati del comune ID {comune_id} modificati. Aggiornamento lista comuni.")
            self.load_data()
        else:
            self.logger.info(f"Modifica del comune ID {comune_id} annullata dall'utente.")

    def azione_modifica_comune(self):
        selected_info = self._get_selected_comune_info_from_table()
        if selected_info:
            comune_id, _ = selected_info
            self._slot_modifica_dati_comune(comune_id)
        else:
            QMessageBox.information(self, "Nessuna Selezione", "Seleziona un comune dalla tabella per modificarlo.")

    def apply_filter(self):
        self._comuni_proxy.setFilterFixedString(self.filter_comuni_edit.text().strip())

    def _get_selected_comune_info_from_table(self) -> Optional[Tuple[int, str]]:
        proxy_idx = self.comuni_table.currentIndex()
        if not proxy_idx.isValid():
            return None
        source_row = self._comuni_proxy.mapToSource(proxy_idx).row()
        comune_id = self._comuni_model.comune_id_at(source_row)
        if comune_id is None:
            return None
        return comune_id, self._comuni_model.comune_name_at(source_row)

    def mostra_partite_del_comune(self, proxy_index: QModelIndex):
        if not proxy_index.isValid():
            return
        source_row = self._comuni_proxy.mapToSource(proxy_index).row()
        comune_id = self._comuni_model.comune_id_at(source_row)
        nome_comune = self._comuni_model.comune_name_at(source_row)
        if comune_id is None:
            return
        dialog = PartiteComuneDialog(self.db_manager, comune_id, nome_comune, self)
        dialog.exec()

    def apri_menu_contestuale_comune(self, position: QPoint):
        proxy_index = self.comuni_table.indexAt(position)
        if not proxy_index.isValid():
            return
        source_row = self._comuni_proxy.mapToSource(proxy_index).row()
        comune_id_selezionato = self._comuni_model.comune_id_at(source_row)
        nome_comune_selezionato = self._comuni_model.comune_name_at(source_row)
        if comune_id_selezionato is None:
            return

        menu = QMenu(self.comuni_table)
        action_vedi_partite = menu.addAction(QApplication.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogContentsView), "Visualizza Partite")
        action_vedi_partite.triggered.connect(lambda: self._slot_vedi_partite_comune(comune_id_selezionato, nome_comune_selezionato))

        action_vedi_possessori = menu.addAction(QApplication.style().standardIcon(QStyle.StandardPixmap.SP_DirLinkIcon), "Visualizza Possessori")
        action_vedi_possessori.triggered.connect(lambda: self._slot_vedi_possessori_comune(comune_id_selezionato, nome_comune_selezionato))

        action_vedi_localita = menu.addAction(QApplication.style().standardIcon(QStyle.StandardPixmap.SP_DirHomeIcon), "Visualizza Località")
        action_vedi_localita.triggered.connect(lambda: self._slot_vedi_localita_comune(comune_id_selezionato, nome_comune_selezionato))

        menu.addSeparator()

        action_modifica_comune = menu.addAction("Modifica Dati Comune")
        action_modifica_comune.triggered.connect(
            lambda: self._slot_modifica_dati_comune(comune_id_selezionato)
        )

        menu.addSeparator()

        action_archivia = menu.addAction(
            QApplication.style().standardIcon(QStyle.StandardPixmap.SP_TrashIcon),
            f"Archivia '{nome_comune_selezionato}'"
        )
        action_archivia.triggered.connect(
            lambda: self._slot_archivia_comune(comune_id_selezionato, nome_comune_selezionato)
        )

        menu.exec(self.comuni_table.viewport().mapToGlobal(position))

    def _slot_archivia_comune(self, comune_id: int, nome: str):
        risposta = QMessageBox.question(
            self, "Archivia Comune",
            f"Archiviare il comune '{nome}'?\n\n"
            "Il comune non verrà eliminato ma nascosto dalle liste.\n"
            "Le partite e i possessori collegati resteranno visibili.\n"
            "Puoi ripristinarlo in qualsiasi momento dal pannello Archivio.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if risposta != QMessageBox.StandardButton.Yes:
            return
        try:
            self.db_manager.archivia_comune(comune_id)
            self.load_data()
            _show_status_message(f"Comune '{nome}' archiviato con successo.", 4000)
        except Exception as e:
            QMessageBox.critical(self, "Errore", f"Impossibile archiviare il comune:\n{e}")

    def _slot_vedi_partite_comune(self, comune_id: int, nome_comune: str):
        self.logger.info(f"Azione: Visualizza partite per comune ID {comune_id} ('{nome_comune}')")
        dialog = PartiteComuneDialog(self.db_manager, comune_id, nome_comune, self)
        dialog.exec()

    def _slot_vedi_possessori_comune(self, comune_id: int, nome_comune: str):
        self.logger.info(f"Azione: Visualizza possessori per comune ID {comune_id} ('{nome_comune}')")
        dialog = PossessoriComuneDialog(self.db_manager, comune_id, nome_comune, self)
        dialog.exec()

    def _slot_vedi_localita_comune(self, comune_id: int, nome_comune: str):
        self.logger.info(f"Azione: Visualizza località per comune ID {comune_id} ('{nome_comune}')")
        dialog = LocalitaSelectionDialog(self.db_manager, comune_id, self, selection_mode=False)
        dialog.setWindowTitle(f"Località del Comune di {nome_comune}")
        dialog.exec()

    def azione_mostra_partite(self):
        selected_info = self._get_selected_comune_info_from_table()
        if selected_info:
            self._slot_vedi_partite_comune(selected_info[0], selected_info[1])
        else:
            QMessageBox.information(self, "Nessuna Selezione", "Seleziona un comune dalla tabella.")

    def azione_mostra_possessori(self):
        selected_info = self._get_selected_comune_info_from_table()
        if selected_info:
            self._slot_vedi_possessori_comune(selected_info[0], selected_info[1])
        else:
            QMessageBox.information(self, "Nessuna Selezione", "Seleziona un comune dalla tabella.")

    def azione_mostra_localita(self):
        selected_info = self._get_selected_comune_info_from_table()
        if selected_info:
            self._slot_vedi_localita_comune(selected_info[0], selected_info[1])
        else:
            QMessageBox.information(self, "Nessuna Selezione", "Seleziona un comune dalla tabella.")

    def _update_action_buttons_state(self):
        has_selection = self.comuni_table.selectionModel().hasSelection()
        self.btn_modifica_comune.setEnabled(has_selection)
        self.btn_mostra_partite.setEnabled(has_selection)
        self.btn_mostra_possessori.setEnabled(has_selection)
        self.btn_mostra_localita.setEnabled(has_selection)
        self.btn_archivia_comune.setEnabled(has_selection)

    def _azione_archivia_comune(self):
        info = self._get_selected_comune_info_from_table()
        if info is None:
            return
        comune_id, nome = info
        self._slot_archivia_comune(comune_id, nome)


__all__ = [
    "_ComuniLoaderWorker",
    "ComuniTableModel",
    "ElencoComuniWidget",
]
