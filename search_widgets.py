"""Search widgets — Ricerca partite, immobili e ricerca fuzzy unificata.

Estratto da gui_widgets.py in v1.0.0 per ridurre la dimensione del modulo
monolitico. Le classi sono re-esportate da gui_widgets.py per compatibilità.
"""
from __future__ import annotations

import csv
import logging
from datetime import date, datetime
from typing import Dict, List, Optional, TYPE_CHECKING

from PyQt6.QtCore import (
    QAbstractTableModel, QModelIndex, QPoint, QSize, QSortFilterProxyModel,
    Qt, QThread, QTimer, pyqtSignal,
)
from PyQt6.QtGui import QColor, QIcon
from PyQt6.QtWidgets import (
    QAbstractItemView, QApplication, QCheckBox, QComboBox, QDialog,
    QFileDialog, QFrame, QGridLayout, QGroupBox, QHBoxLayout, QHeaderView,
    QLabel, QLineEdit, QMenu, QMessageBox, QProgressBar, QPushButton,
    QSlider, QSpinBox, QStyle, QTabWidget, QTableView, QTableWidget,
    QTableWidgetItem, QVBoxLayout, QWidget,
)

from app_paths import get_icon_path
from app_utils import BulkReportPDF, FPDF_AVAILABLE, prompt_to_open_file
from foliarium.ui.widgets.custom import show_status_message as _show_status_message
from dialogs import (
    ComuneSelectionDialog, LocalitaSelectionDialog,
    ModificaImmobileDialog, ModificaLocalitaDialog, ModificaPossessoreDialog,
    PartitaDetailsDialog,
)

try:
    from catasto_db_manager import DBMError
except ImportError:
    class DBMError(Exception):
        pass

if TYPE_CHECKING:
    from catasto_db_manager import CatastoDBManager  # noqa: F401

logger = logging.getLogger("CatastoGUI.search_widgets")


class _PartiteSearchWorker(QThread):
    """Esegue search_partite in background per non bloccare la UI."""
    results_ready = pyqtSignal(list)
    error_occurred = pyqtSignal(str)

    def __init__(self, db_manager, comune_id, numero, possessore, natura,
                 partita_id=None, parent=None):
        super().__init__(parent)
        self._db = db_manager
        self._comune_id = comune_id
        self._numero = numero
        self._possessore = possessore
        self._natura = natura
        self._partita_id = partita_id

    def run(self):
        try:
            partite = self._db.search_partite(
                comune_id=self._comune_id,
                numero_partita=self._numero,
                possessore=self._possessore,
                immobile_natura=self._natura,
                partita_id=self._partita_id,
            )
            self.results_ready.emit(partite or [])
        except Exception as e:
            self.error_occurred.emit(str(e))


class PartitaResultCard(QFrame):
    """Card cliccabile per un risultato di ricerca partite."""
    card_clicked = pyqtSignal(int)
    context_menu_requested = pyqtSignal(int, QPoint)

    _STATO_STYLE: dict[str, tuple[str, str]] = {
        "attiva":   ("#E8F5E9", "#1B5E20"),
        "inattiva": ("#F5F5F5", "#616161"),
        "aperta":   ("#E3F2FD", "#0D47A1"),
        "chiusa":   ("#FFF3E0", "#BF360C"),
    }

    def __init__(self, partita_data: dict, parent=None):
        super().__init__(parent)
        self._partita_id: int = partita_data.get('id', -1)
        self._partita_data = partita_data
        self.setObjectName("resultCard")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setFrameShadow(QFrame.Shadow.Raised)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(
            lambda pos: self.context_menu_requested.emit(
                self._partita_id, self.mapToGlobal(pos)))

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(3)

        # Top row: numero partita + chip stato
        row1 = QHBoxLayout()
        row1.setSpacing(8)

        numero = partita_data.get('numero_partita', '—')
        suffisso = (partita_data.get('suffisso_partita') or '').strip()
        suf_display = f"/{suffisso}" if suffisso else ""
        numero_lbl = QLabel(f"<b>N. {numero}{suf_display}</b>")
        numero_lbl.setObjectName("cardTitle")
        row1.addWidget(numero_lbl)
        row1.addStretch()

        stato = (partita_data.get('stato') or '').strip()
        bg, fg = self._STATO_STYLE.get(stato.lower(), ("#F5F5F5", "#424242"))
        stato_lbl = QLabel(stato or "—")
        stato_lbl.setStyleSheet(
            f"background:{bg}; color:{fg}; border-radius:9px; "
            f"padding:1px 9px; font-size:9pt; font-weight:600;"
        )
        row1.addWidget(stato_lbl)
        layout.addLayout(row1)

        # Comune
        comune = partita_data.get('comune_nome', '')
        if comune:
            comune_lbl = QLabel(comune)
            comune_lbl.setObjectName("cardSubtitle")
            layout.addWidget(comune_lbl)

        # Tipo
        tipo = partita_data.get('tipo', '')
        if tipo:
            tipo_lbl = QLabel(tipo)
            tipo_lbl.setObjectName("cardMeta")
            layout.addWidget(tipo_lbl)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.card_clicked.emit(self._partita_id)
        super().mousePressEvent(event)

    def set_selected(self, selected: bool):
        self.setProperty("selected", "true" if selected else "false")
        self.style().unpolish(self)
        self.style().polish(self)


_PARTITE_COLS = ["ID", "N° Partita", "Comune", "Stato", "Tipo", "Data Impianto"]
_COL_STATO = 3  # colonna usata dal proxy filter


class PartiteTableModel(QAbstractTableModel):
    """Modello dati per la tabella delle partite catastali.

    Ogni riga è un dict restituito da search_partite(); l'ID è esposto
    tramite Qt.ItemDataRole.UserRole sulla colonna 0 per un recupero
    affidabile anche dopo ordinamento.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._data: list[dict] = []

    # ── API pubblica ───────────────────────────────────────────────

    def load(self, partite: list[dict]) -> None:
        self.beginResetModel()
        self._data = partite
        self.endResetModel()

    def partita_id_at(self, source_row: int) -> Optional[int]:
        if 0 <= source_row < len(self._data):
            return self._data[source_row].get('id')
        return None

    def row_count(self) -> int:
        return len(self._data)

    # ── QAbstractTableModel interface ─────────────────────────────

    def rowCount(self, parent=QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self._data)

    def columnCount(self, parent=QModelIndex()) -> int:
        return 0 if parent.isValid() else len(_PARTITE_COLS)

    def headerData(self, section: int, orientation, role=Qt.ItemDataRole.DisplayRole):
        if orientation == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.DisplayRole:
            return _PARTITE_COLS[section]
        return None

    def data(self, index: QModelIndex, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None
        row, col = index.row(), index.column()
        p = self._data[row]

        if role == Qt.ItemDataRole.DisplayRole:
            if col == 0:
                pid = p.get('id')
                return str(pid) if pid is not None else '—'
            if col == 1:
                suf = (p.get('suffisso_partita') or '').strip()
                num = p.get('numero_partita', '')
                return f"{num}/{suf}" if suf else str(num)
            if col == 2:
                return p.get('comune_nome', '')
            if col == 3:
                return p.get('stato', '')
            if col == 4:
                return p.get('tipo', '')
            if col == 5:
                return str(p.get('data_impianto') or '—')

        if role == Qt.ItemDataRole.UserRole and col == 0:
            return p.get('id')

        if role == Qt.ItemDataRole.TextAlignmentRole and col == 0:
            return Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter

        return None

    def flags(self, index: QModelIndex):
        if not index.isValid():
            return Qt.ItemFlag.NoItemFlags
        return Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable

    def sort(self, column: int, order=Qt.SortOrder.AscendingOrder) -> None:
        reverse = (order == Qt.SortOrder.DescendingOrder)
        keys = {0: 'id', 1: 'numero_partita', 2: 'comune_nome',
                3: 'stato', 4: 'tipo', 5: 'data_impianto'}
        key = keys.get(column, 'id')
        self.layoutAboutToBeChanged.emit()
        self._data.sort(
            key=lambda p: (p.get(key) is None, str(p.get(key) or '')),
            reverse=reverse,
        )
        self.layoutChanged.emit()


class _PartiteFilterProxy(QSortFilterProxyModel):
    """Filtra per stato; stringa vuota = mostra tutto."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._stato: str = ""

    def set_stato(self, stato: str) -> None:
        self._stato = stato.strip().lower()
        self.invalidateFilter()

    def filterAcceptsRow(self, source_row: int, source_parent: QModelIndex) -> bool:
        if not self._stato:
            return True
        idx = self.sourceModel().index(source_row, _COL_STATO, source_parent)
        cell = (self.sourceModel().data(idx) or "").strip().lower()
        return cell == self._stato


class RicercaPartiteWidget(QWidget):
    def __init__(self, db_manager, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self._selected_partita_id: Optional[int] = None
        self._all_partite: list[dict] = []
        self._comune_id: Optional[int] = None
        self._search_worker: Optional[_PartiteSearchWorker] = None

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(12)

        # Titolo pagina
        title = QLabel("Ricerca Partite")
        title.setObjectName("pageTitle")
        main_layout.addWidget(title)
        subtitle = QLabel("Cerca per comune, numero, ID, possessore o natura dell'immobile. Lascia vuoti i campi per elencare tutto.")
        subtitle.setObjectName("pageSubtitle")
        main_layout.addWidget(subtitle)

        group = QGroupBox("Filtri di ricerca")
        group_layout = QVBoxLayout(group)
        group_layout.setSpacing(10)

        # ─────────────────────────────────────────────────────────
        # Riga 1: Comune | N° Partita | ID Partita | Stato
        # ─────────────────────────────────────────────────────────
        row1 = QGridLayout()
        row1.setHorizontalSpacing(12)
        row1.setVerticalSpacing(4)
        row1.setColumnStretch(1, 2)  # comune si espande
        row1.setColumnStretch(3, 1)  # n° si espande un po'
        row1.setColumnStretch(5, 1)  # id si espande un po'
        row1.setColumnStretch(7, 1)  # stato si espande un po'

        _lbl_comune = QLabel("Comune:")
        _lbl_comune.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        row1.addWidget(_lbl_comune, 0, 0)
        self._comune_btn = QPushButton("Tutti i comuni")
        self._comune_btn.setObjectName("secondaryButton")
        self._comune_btn.clicked.connect(self._select_comune)
        row1.addWidget(self._comune_btn, 0, 1)

        _lbl_num = QLabel("N° Partita:")
        _lbl_num.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        row1.addWidget(_lbl_num, 0, 2)
        self._numero_edit = QSpinBox()
        self._numero_edit.setMinimum(0)
        self._numero_edit.setMaximum(999999)
        self._numero_edit.setSpecialValueText("—")
        self._numero_edit.setToolTip("Numero della partita catastale (0 = qualsiasi)")
        row1.addWidget(self._numero_edit, 0, 3)

        _lbl_id = QLabel("ID:")
        _lbl_id.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        _lbl_id.setToolTip("Identificativo univoco interno della partita nel database")
        row1.addWidget(_lbl_id, 0, 4)
        self._id_edit = QSpinBox()
        self._id_edit.setMinimum(0)
        self._id_edit.setMaximum(9999999)
        self._id_edit.setSpecialValueText("—")
        self._id_edit.setToolTip("ID interno partita (0 = qualsiasi)")
        row1.addWidget(self._id_edit, 0, 5)

        _lbl_stato = QLabel("Stato:")
        _lbl_stato.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        row1.addWidget(_lbl_stato, 0, 6)
        self._stato_combo = QComboBox()
        self._stato_combo.addItems(["Tutte", "Attiva", "Inattiva", "Aperta", "Chiusa"])
        self._stato_combo.currentTextChanged.connect(self._on_stato_combo_changed)
        row1.addWidget(self._stato_combo, 0, 7)

        group_layout.addLayout(row1)

        # ─────────────────────────────────────────────────────────
        # Riga 2: Possessore | Natura immobile | [Cerca] [Pulisci]
        # ─────────────────────────────────────────────────────────
        row2 = QGridLayout()
        row2.setHorizontalSpacing(12)
        row2.setVerticalSpacing(4)
        row2.setColumnStretch(1, 3)
        row2.setColumnStretch(3, 3)

        _lbl_poss = QLabel("Possessore:")
        _lbl_poss.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        row2.addWidget(_lbl_poss, 0, 0)
        self._possessore_edit = QLineEdit()
        self._possessore_edit.setPlaceholderText("Nome o parte del nome del possessore…")
        self._possessore_edit.returnPressed.connect(self.do_search)
        row2.addWidget(self._possessore_edit, 0, 1)

        _lbl_nat = QLabel("Natura immobile:")
        _lbl_nat.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        row2.addWidget(_lbl_nat, 0, 2)
        self._natura_edit = QLineEdit()
        self._natura_edit.setPlaceholderText("Es. casa, prato, bosco…")
        self._natura_edit.returnPressed.connect(self.do_search)
        row2.addWidget(self._natura_edit, 0, 3)

        _btn_row = QHBoxLayout()
        _btn_row.setSpacing(8)
        _clear_btn = QPushButton("Pulisci")
        _clear_btn.setObjectName("secondaryButton")
        _clear_btn.clicked.connect(self._clear_search)
        self._search_btn = QPushButton("Cerca")
        self._search_btn.clicked.connect(self.do_search)
        _btn_row.addWidget(_clear_btn)
        _btn_row.addWidget(self._search_btn)
        row2.addLayout(_btn_row, 0, 4)

        group_layout.addLayout(row2)

        # Loading progress bar (hidden by default)
        self._loading_bar = QProgressBar()
        self._loading_bar.setRange(0, 0)
        self._loading_bar.setFixedHeight(3)
        self._loading_bar.setVisible(False)
        self._loading_bar.setTextVisible(False)
        group_layout.addWidget(self._loading_bar)

        # Conteggio risultati
        count_layout = QHBoxLayout()
        count_layout.setContentsMargins(0, 0, 0, 0)
        self._count_label = QLabel("Nessuna ricerca eseguita.")
        self._count_label.setObjectName("resultCountLabel")
        count_layout.addStretch()
        count_layout.addWidget(self._count_label)
        group_layout.addLayout(count_layout)

        # ─────────────────────────────────────────────────────────
        # Tabella risultati — QTableView + PartiteTableModel
        # Colonne: ID | N° Partita | Comune | Stato | Tipo | Data Impianto
        # ─────────────────────────────────────────────────────────
        self._model = PartiteTableModel(self)
        self._proxy = _PartiteFilterProxy(self)
        self._proxy.setSourceModel(self._model)

        self._table = QTableView()
        self._table.setModel(self._proxy)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._table.setAlternatingRowColors(True)
        self._table.setSortingEnabled(True)
        self._table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._table.verticalHeader().setVisible(False)
        hh = self._table.horizontalHeader()
        hh.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        hh.setStretchLastSection(True)
        self._table.setColumnWidth(0, 60)   # ID
        self._table.setColumnWidth(1, 90)   # N° Partita
        self._table.setColumnWidth(2, 170)  # Comune
        self._table.setColumnWidth(3, 80)   # Stato
        self._table.setColumnWidth(4, 100)  # Tipo
        self._table.selectionModel().currentRowChanged.connect(self._on_current_row_changed)
        self._table.doubleClicked.connect(lambda: self.show_details())
        self._table.customContextMenuRequested.connect(self._on_context_menu)
        group_layout.addWidget(self._table, 1)

        # ─────────────────────────────────────────────────────────
        # Bottoni azione (come ElencoComuniWidget)
        # ─────────────────────────────────────────────────────────
        action_layout = QHBoxLayout()
        action_layout.setContentsMargins(0, 0, 0, 0)
        action_layout.setSpacing(8)

        self._btn_open_full = QPushButton("Apri Dettagli Completi")
        self._btn_open_full.setEnabled(False)
        self._btn_open_full.clicked.connect(self.show_details)
        action_layout.addWidget(self._btn_open_full)

        self._btn_albero = QPushButton("Albero Genealogico")
        self._btn_albero.setObjectName("secondaryButton")
        self._btn_albero.setEnabled(False)
        self._btn_albero.clicked.connect(self._apri_albero)
        action_layout.addWidget(self._btn_albero)

        action_layout.addStretch()

        self._btn_copy_id = QPushButton("Copia ID")
        self._btn_copy_id.setObjectName("secondaryButton")
        self._btn_copy_id.setEnabled(False)
        self._btn_copy_id.clicked.connect(lambda: QApplication.clipboard().setText(
            str(self._selected_partita_id or "")))
        action_layout.addWidget(self._btn_copy_id)

        self._btn_archivia = QPushButton("Archivia Partita")
        self._btn_archivia.setObjectName("dangerButton")
        self._btn_archivia.setEnabled(False)
        self._btn_archivia.setToolTip("Archivia la partita selezionata (non viene eliminata, solo nascosta)")
        self._btn_archivia.clicked.connect(self._azione_archivia_partita)
        action_layout.addWidget(self._btn_archivia)

        group_layout.addLayout(action_layout)

        main_layout.addWidget(group)


    def _select_comune(self):
        dialog = ComuneSelectionDialog(self.db_manager, self)
        if dialog.exec() == QDialog.DialogCode.Accepted and dialog.selected_comune_id:
            self._comune_id = dialog.selected_comune_id
            self._comune_btn.setText(dialog.selected_comune_name or "Comune...")

    def _clear_search(self):
        if self._search_worker and self._search_worker.isRunning():
            self._search_worker.quit()
            self._search_worker.wait(500)
        self._loading_bar.setVisible(False)
        self._search_btn.setEnabled(True)
        self._comune_id = None
        self._comune_btn.setText("Tutti i comuni")
        self._numero_edit.setValue(0)
        self._id_edit.setValue(0)
        self._possessore_edit.clear()
        self._natura_edit.clear()
        self._stato_combo.setCurrentText("Tutte")
        self._model.load([])
        self._proxy.set_stato("")
        self._all_partite.clear()
        self._selected_partita_id = None
        self._count_label.setText("Nessuna ricerca eseguita.")
        for btn in (self._btn_open_full, self._btn_albero, self._btn_copy_id, self._btn_archivia):
            btn.setEnabled(False)

    def _on_stato_combo_changed(self, text: str):
        """Quando il combo filtro stato cambia, aggiorna la visibilità righe."""
        self._update_row_visibility()

    def _update_row_visibility(self):
        """Aggiorna il filtro proxy in base al combo stato."""
        stato_filtro = self._stato_combo.currentText()
        if stato_filtro == "Tutte":
            stato_filtro = ""
        self._proxy.set_stato(stato_filtro)

        visible = self._proxy.rowCount()
        total = self._model.row_count()
        if stato_filtro:
            self._count_label.setText(f"{visible} di {total} partite mostrate.")
        else:
            self._count_label.setText(f"{total} partite trovate.")

    def do_search(self):
        # Cancel any running search
        if self._search_worker and self._search_worker.isRunning():
            self._search_worker.quit()
            self._search_worker.wait(500)

        numero_val = self._numero_edit.value()
        numero = numero_val if numero_val > 0 else None
        id_val = self._id_edit.value()
        partita_id = id_val if id_val > 0 else None
        possessore = self._possessore_edit.text().strip() or None
        natura = self._natura_edit.text().strip() or None

        self._search_btn.setEnabled(False)
        self._loading_bar.setVisible(True)
        self._count_label.setText("Ricerca in corso…")

        self._search_worker = _PartiteSearchWorker(
            self.db_manager, self._comune_id, numero, possessore, natura,
            partita_id=partita_id, parent=self
        )
        self._search_worker.results_ready.connect(self._on_search_results)
        self._search_worker.error_occurred.connect(self._on_search_error)
        self._search_worker.start()

    def _on_search_results(self, partite: list):
        self._loading_bar.setVisible(False)
        self._search_btn.setEnabled(True)

        self._all_partite = partite
        truncated = bool(self._all_partite and self._all_partite[-1].get('_truncated'))

        self._model.load(self._all_partite)

        self._selected_partita_id = None
        for btn in (self._btn_open_full, self._btn_albero, self._btn_copy_id, self._btn_archivia):
            btn.setEnabled(False)

        self._update_row_visibility()

        if truncated:
            self._count_label.setText(
                f"Visualizzate le prime {len(self._all_partite)} partite. "
                f"Affina la ricerca per risultati più precisi.")

    def _on_search_error(self, error_msg: str):
        self._loading_bar.setVisible(False)
        self._search_btn.setEnabled(True)
        self._count_label.setText("Errore durante la ricerca.")
        logging.getLogger("CatastoGUI").error(f"Errore ricerca partite: {error_msg}")
        QMessageBox.critical(self, "Errore di Ricerca",
                             f"Si è verificato un errore durante la ricerca:\n\n{error_msg}"
                             "\n\nSe l'errore riguarda la colonna 'archiviato', eseguire "
                             "la migrazione del database: sql_scripts/migrations/add_soft_delete.sql")

    def _on_current_row_changed(self, current: QModelIndex, _previous: QModelIndex):
        source = self._proxy.mapToSource(current)
        partita_id = self._model.partita_id_at(source.row()) if source.isValid() else None
        self._selected_partita_id = partita_id
        enabled = partita_id is not None
        for btn in (self._btn_open_full, self._btn_albero, self._btn_copy_id, self._btn_archivia):
            btn.setEnabled(enabled)

    def show_details(self):
        if not self._selected_partita_id:
            QMessageBox.warning(self, "Attenzione", "Seleziona una partita dalla lista.")
            return
        try:
            partita = self.db_manager.get_partita_details(self._selected_partita_id)
            if partita:
                from foliarium.ui.dialogs.partita import PartitaDetailsDialog
                dlg = PartitaDetailsDialog(partita, self)
                dlg.exec()
        except Exception as e:
            QMessageBox.critical(self, "Errore", f"Impossibile caricare i dettagli: {e}")

    def _apri_albero(self):
        if not self._selected_partita_id:
            return
        try:
            from foliarium.ui.dialogs.partita import AlberoGeneralogicoDialog
            dlg = AlberoGeneralogicoDialog(self.db_manager, self._selected_partita_id, self)
            dlg.exec()
        except Exception as e:
            QMessageBox.critical(self, "Errore", str(e))

    def _on_context_menu(self, pos: QPoint):
        proxy_index = self._table.indexAt(pos)
        if not proxy_index.isValid():
            return
        source_index = self._proxy.mapToSource(proxy_index)
        source_row = source_index.row()
        partita_id = self._model.partita_id_at(source_row)
        if partita_id is None:
            return
        numero_index = self._model.index(source_row, 1)
        numero_text = self._model.data(numero_index) or ''

        self._table.selectRow(proxy_index.row())

        menu = QMenu(self)
        menu.addAction(
            QApplication.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogContentsView),
            "Apri Dettagli Completi"
        ).triggered.connect(self.show_details)
        menu.addSeparator()
        menu.addAction(f"Copia Numero Partita ({numero_text})").triggered.connect(
            lambda: QApplication.clipboard().setText(numero_text))
        menu.addAction(f"Copia ID ({partita_id})").triggered.connect(
            lambda: QApplication.clipboard().setText(str(partita_id)))
        menu.addSeparator()
        menu.addAction(
            QApplication.style().standardIcon(QStyle.StandardPixmap.SP_TrashIcon),
            f"Archivia Partita N. {numero_text}"
        ).triggered.connect(lambda: self._archivia_partita(partita_id, numero_text))
        menu.exec(self._table.viewport().mapToGlobal(pos))

    def _archivia_partita(self, partita_id: int, numero_text: str):
        risposta = QMessageBox.question(
            self, "Archivia Partita",
            f"Archiviare la partita N. {numero_text}?\n\n"
            "La partita non verrà eliminata ma nascosta dalle ricerche.\n"
            "Puoi ripristinarla in qualsiasi momento dal pannello Archivio.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if risposta != QMessageBox.StandardButton.Yes:
            return
        try:
            self.db_manager.archivia_partita(partita_id)
            self.do_search()
            _show_status_message(f"Partita N. {numero_text} archiviata con successo.", 4000)
        except Exception as e:
            QMessageBox.critical(self, "Errore", f"Impossibile archiviare la partita:\n{e}")

    def _azione_archivia_partita(self):
        """Archivia la partita selezionata tramite pulsante."""
        if not self._selected_partita_id:
            return
        row = self._table.currentRow()
        numero_text = self._table.item(row, 0).text() if row >= 0 and self._table.item(row, 0) else str(self._selected_partita_id)
        self._archivia_partita(self._selected_partita_id, numero_text)


class RicercaAvanzataImmobiliWidget(QWidget):
    def __init__(self, db_manager: CatastoDBManager, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.logger = logging.getLogger(f"CatastoGUI.{self.__class__.__name__}")
        self.selected_comune_id: Optional[int] = None
        self.selected_localita_id: Optional[int] = None

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(12)

        # Header pagina
        _title = QLabel("Ricerca Avanzata Immobili")
        _title.setObjectName("pageTitle")
        main_layout.addWidget(_title)
        _subtitle = QLabel("Filtra per natura, classificazione, dimensioni, possessore o ubicazione. Lascia vuoti i campi per non filtrare.")
        _subtitle.setObjectName("pageSubtitle")
        main_layout.addWidget(_subtitle)

        criteria_group = QGroupBox("Criteri di Ricerca")
        criteria_layout = QGridLayout(criteria_group)
        criteria_layout.setHorizontalSpacing(12)
        criteria_layout.setVerticalSpacing(10)
        criteria_layout.setColumnStretch(1, 1)

        def _label(text: str) -> QLabel:
            lbl = QLabel(text)
            lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            return lbl

        # Riga 0: Comune
        criteria_layout.addWidget(_label("Comune:"), 0, 0)
        self.comune_display_label = QLabel("Qualsiasi comune")
        self.comune_display_label.setProperty("muted", "true")
        criteria_layout.addWidget(self.comune_display_label, 0, 1)
        self.btn_seleziona_comune = QPushButton("Seleziona…")
        self.btn_seleziona_comune.setObjectName("secondaryButton")
        self.btn_seleziona_comune.clicked.connect(self._seleziona_comune_per_ricerca)
        criteria_layout.addWidget(self.btn_seleziona_comune, 0, 2)
        self.btn_reset_comune = QPushButton("Reset")
        self.btn_reset_comune.setObjectName("ghostButton")
        self.btn_reset_comune.clicked.connect(self._reset_comune_ricerca)
        criteria_layout.addWidget(self.btn_reset_comune, 0, 3)

        # Riga 1: Località
        criteria_layout.addWidget(_label("Località:"), 1, 0)
        self.localita_display_label = QLabel("Qualsiasi località")
        self.localita_display_label.setProperty("muted", "true")
        criteria_layout.addWidget(self.localita_display_label, 1, 1)
        self.btn_seleziona_localita = QPushButton("Seleziona…")
        self.btn_seleziona_localita.setObjectName("secondaryButton")
        self.btn_seleziona_localita.clicked.connect(self._seleziona_localita_per_ricerca)
        self.btn_seleziona_localita.setEnabled(False)
        criteria_layout.addWidget(self.btn_seleziona_localita, 1, 2)
        self.btn_reset_localita = QPushButton("Reset")
        self.btn_reset_localita.setObjectName("ghostButton")
        self.btn_reset_localita.clicked.connect(self._reset_localita_ricerca)
        criteria_layout.addWidget(self.btn_reset_localita, 1, 3)

        # Riga 2: Natura
        criteria_layout.addWidget(_label("Natura immobile:"), 2, 0)
        self.natura_edit = QLineEdit()
        self.natura_edit.setPlaceholderText("Es. Casa, Terreno…")
        criteria_layout.addWidget(self.natura_edit, 2, 1, 1, 3)

        # Riga 3: Classificazione
        criteria_layout.addWidget(_label("Classificazione:"), 3, 0)
        self.classificazione_edit = QLineEdit()
        self.classificazione_edit.setPlaceholderText("Es. Abitazione civile, Oliveto…")
        criteria_layout.addWidget(self.classificazione_edit, 3, 1, 1, 3)

        # Riga 4: Consistenza
        criteria_layout.addWidget(_label("Consistenza (testo):"), 4, 0)
        self.consistenza_search_edit = QLineEdit()
        self.consistenza_search_edit.setPlaceholderText("Es. 120, are, vani — ricerca parziale")
        criteria_layout.addWidget(self.consistenza_search_edit, 4, 1, 1, 3)

        # Riga 5: Numero Piani
        criteria_layout.addWidget(_label("Piani min:"), 5, 0)
        self.piani_min_spinbox = QSpinBox()
        self.piani_min_spinbox.setMinimum(0)
        self.piani_min_spinbox.setValue(0)
        criteria_layout.addWidget(self.piani_min_spinbox, 5, 1)
        _lbl_pmax = QLabel("Piani max:")
        _lbl_pmax.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        criteria_layout.addWidget(_lbl_pmax, 5, 2)
        self.piani_max_spinbox = QSpinBox()
        self.piani_max_spinbox.setMinimum(0)
        self.piani_max_spinbox.setMaximum(99)
        self.piani_max_spinbox.setValue(0)
        self.piani_max_spinbox.setSpecialValueText("Qualsiasi")
        criteria_layout.addWidget(self.piani_max_spinbox, 5, 3)

        # Riga 6: Numero Vani
        criteria_layout.addWidget(_label("Vani min:"), 6, 0)
        self.vani_min_spinbox = QSpinBox()
        self.vani_min_spinbox.setMinimum(0)
        self.vani_min_spinbox.setValue(0)
        criteria_layout.addWidget(self.vani_min_spinbox, 6, 1)
        _lbl_vmax = QLabel("Vani max:")
        _lbl_vmax.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        criteria_layout.addWidget(_lbl_vmax, 6, 2)
        self.vani_max_spinbox = QSpinBox()
        self.vani_max_spinbox.setMinimum(0)
        self.vani_max_spinbox.setMaximum(999)
        self.vani_max_spinbox.setValue(0)
        self.vani_max_spinbox.setSpecialValueText("Qualsiasi")
        criteria_layout.addWidget(self.vani_max_spinbox, 6, 3)

        # Riga 7: Nome Possessore
        criteria_layout.addWidget(_label("Possessore:"), 7, 0)
        self.nome_possessore_edit = QLineEdit()
        self.nome_possessore_edit.setPlaceholderText("Parte del nome del possessore — ricerca parziale")
        criteria_layout.addWidget(self.nome_possessore_edit, 7, 1, 1, 3)

        main_layout.addWidget(criteria_group)

        # Bottoni — primario a destra, allineati come negli altri form
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        btn_row.addStretch()
        self.btn_esegui_ricerca_immobili = QPushButton("Esegui Ricerca")
        self.btn_esegui_ricerca_immobili.setDefault(True)
        self.btn_esegui_ricerca_immobili.setIcon(
            QApplication.style().standardIcon(QStyle.StandardPixmap.SP_DialogApplyButton))
        self.btn_esegui_ricerca_immobili.clicked.connect(self._esegui_ricerca_effettiva)
        btn_row.addWidget(self.btn_esegui_ricerca_immobili)
        main_layout.addLayout(btn_row)

        results_group = QGroupBox("Risultati Ricerca")
        results_layout = QVBoxLayout(results_group)
        self.risultati_immobili_table = QTableWidget()
        # Colonne basate sulla funzione SQL cerca_immobili_avanzato
        self.risultati_immobili_table.setColumnCount(10)
        self.risultati_immobili_table.setHorizontalHeaderLabels([
            "ID Imm.", "Part. N.", "Comune", "Località", "Natura",
            "Class.", "Consist.", "Piani", "Vani", "Possessori"
        ])
        self.risultati_immobili_table.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers)
        self.risultati_immobili_table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows)
        self.risultati_immobili_table.setAlternatingRowColors(True)
        self.risultati_immobili_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Interactive)
        self.risultati_immobili_table.horizontalHeader().setStretchLastSection(True)
        self.risultati_immobili_table.setSortingEnabled(True)
        self.risultati_immobili_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.risultati_immobili_table.customContextMenuRequested.connect(self._apri_menu_immobile)
        self.result_count_label = QLabel("Nessuna ricerca eseguita.")
        self.result_count_label.setObjectName("resultCountLabel")
        results_layout.addWidget(self.result_count_label)
        results_layout.addWidget(self.risultati_immobili_table)
        main_layout.addWidget(results_group)

        self.setLayout(main_layout)

    def _seleziona_comune_per_ricerca(self):
        dialog = ComuneSelectionDialog(self.db_manager, self)
        if dialog.exec() == QDialog.DialogCode.Accepted and dialog.selected_comune_id:
            self.selected_comune_id = dialog.selected_comune_id
            self.comune_display_label.setText(
                f"{dialog.selected_comune_name} (ID: {self.selected_comune_id})")
            self.btn_seleziona_localita.setEnabled(True)
            self._reset_localita_ricerca()
        elif not self.selected_comune_id:
            self.comune_display_label.setText("Qualsiasi comune")
            self.btn_seleziona_localita.setEnabled(False)

    def _reset_comune_ricerca(self):
        self.selected_comune_id = None
        self.comune_display_label.setText("Qualsiasi comune")
        self.btn_seleziona_localita.setEnabled(False)
        self._reset_localita_ricerca()

    def _seleziona_localita_per_ricerca(self):
        if not self.selected_comune_id:
            QMessageBox.warning(
                self, "Comune Mancante", "Seleziona prima un comune per filtrare le località.")
            return

        # Apre LocalitaSelectionDialog in MODALITÀ SELEZIONE
        dialog = LocalitaSelectionDialog(self.db_manager, self.selected_comune_id, self,
                                         selection_mode=True)

        if dialog.exec() == QDialog.DialogCode.Accepted:  # Se l'utente ha premuto "Seleziona" nel dialogo
            if dialog.selected_localita_id is not None and dialog.selected_localita_name is not None:
                self.selected_localita_id = dialog.selected_localita_id
                self.localita_display_label.setText(
                    f"{dialog.selected_localita_name} (ID: {self.selected_localita_id})")
                logging.getLogger("CatastoGUI").info(
                    f"RicercaAvanzataImmobili: Località selezionata ID: {self.selected_localita_id}, Nome: {dialog.selected_localita_name}")
            else:
                # Questo caso è improbabile se _conferma_selezione funziona, ma per sicurezza
                logging.getLogger("CatastoGUI").warning(
                    "RicercaAvanzataImmobili: LocalitaSelectionDialog accettato ma nessun ID/nome località valido è stato restituito.")
                # Potrebbe essere utile resettare qui, o lasciare la selezione precedente.
                # self._reset_localita_ricerca()
        # else: # Dialogo annullato (premuto "Annulla" o chiuso)
            # Non fare nulla, la selezione precedente (o nessuna selezione) rimane.
            # Non è necessario chiamare self._reset_localita_ricerca() a meno che non sia il comportamento desiderato.
            logging.getLogger("CatastoGUI").info(
                "Selezione località annullata o dialogo chiuso.")

    def _reset_localita_ricerca(self):
        self.selected_localita_id = None
        self.localita_display_label.setText("Qualsiasi località")

    def _esegui_ricerca_effettiva(self):
        p_comune_id = self.selected_comune_id
        p_localita_id = self.selected_localita_id
        p_natura = self.natura_edit.text().strip() or None
        p_classificazione = self.classificazione_edit.text().strip() or None
        # Campo unico per ricerca testuale consistenza
        p_consistenza_search = self.consistenza_search_edit.text().strip() or None

        p_piani_min = self.piani_min_spinbox.value(
        ) if self.piani_min_spinbox.value() > 0 else None
        p_piani_max = self.piani_max_spinbox.value() if self.piani_max_spinbox.value(
        ) != 0 else None  # 0 è speciale "Qualsiasi"

        p_vani_min = self.vani_min_spinbox.value(
        ) if self.vani_min_spinbox.value() > 0 else None
        p_vani_max = self.vani_max_spinbox.value(
        ) if self.vani_max_spinbox.value() != 0 else None

        p_nome_possessore = self.nome_possessore_edit.text().strip() or None

        self.logger.debug(
            "Parametri inviati a ricerca_avanzata_immobili_gui: "
            f"comune_id={p_comune_id}, localita_id={p_localita_id}, "
            f"natura='{p_natura}', classificazione='{p_classificazione}', "
            f"consistenza='{p_consistenza_search}', piani={p_piani_min}-{p_piani_max}, "
            f"vani={p_vani_min}-{p_vani_max}, nome_possessore='{p_nome_possessore}'"
        )

        try:
            immobili_trovati = self.db_manager.ricerca_avanzata_immobili_gui(
                comune_id=p_comune_id,
                localita_id=p_localita_id,
                natura_search=p_natura,
                classificazione_search=p_classificazione,
                consistenza_search=p_consistenza_search,
                piani_min=p_piani_min,
                piani_max=p_piani_max,
                vani_min=p_vani_min,
                vani_max=p_vani_max,
                nome_possessore_search=p_nome_possessore,
                data_inizio_possesso_search=None,  # Non ancora in GUI
                data_fine_possesso_search=None    # Non ancora in GUI
            )

            self.risultati_immobili_table.setSortingEnabled(False)
            self.risultati_immobili_table.setRowCount(0)
            if immobili_trovati:
                self.risultati_immobili_table.setRowCount(
                    len(immobili_trovati))
                for row_idx, immobile in enumerate(immobili_trovati):
                    col = 0
                    self.risultati_immobili_table.setItem(
                        row_idx, col, QTableWidgetItem(str(immobile.get('id_immobile', ''))))
                    col += 1
                    self.risultati_immobili_table.setItem(
                        row_idx, col, QTableWidgetItem(str(immobile.get('numero_partita', ''))))
                    col += 1
                    self.risultati_immobili_table.setItem(
                        row_idx, col, QTableWidgetItem(immobile.get('comune_nome', '')))
                    col += 1
                    localita_display = f"{immobile.get('localita_nome', '')}"
                    if immobile.get('civico'):
                        localita_display += f", {immobile.get('civico')}"
                    if immobile.get('localita_tipo'):
                        localita_display += f" ({immobile.get('localita_tipo')})"
                    self.risultati_immobili_table.setItem(
                        row_idx, col, QTableWidgetItem(localita_display.strip()))
                    col += 1
                    self.risultati_immobili_table.setItem(
                        row_idx, col, QTableWidgetItem(immobile.get('natura', '')))
                    col += 1
                    self.risultati_immobili_table.setItem(
                        row_idx, col, QTableWidgetItem(immobile.get('classificazione', '')))
                    col += 1
                    self.risultati_immobili_table.setItem(
                        row_idx, col, QTableWidgetItem(immobile.get('consistenza', '')))
                    col += 1
                    self.risultati_immobili_table.setItem(row_idx, col, QTableWidgetItem(str(
                        immobile.get('numero_piani', '')) if immobile.get('numero_piani') is not None else ''))
                    col += 1
                    self.risultati_immobili_table.setItem(row_idx, col, QTableWidgetItem(str(
                        immobile.get('numero_vani', '')) if immobile.get('numero_vani') is not None else ''))
                    col += 1
                    self.risultati_immobili_table.setItem(
                        row_idx, col, QTableWidgetItem(immobile.get('possessori_attuali', '')))
                    col += 1  # Campo dalla funzione SQL

                self.risultati_immobili_table.setSortingEnabled(True)
                self.result_count_label.setText(f"{len(immobili_trovati)} immobili trovati.")
                _show_status_message(f"Ricerca completata: {len(immobili_trovati)} immobili trovati.", 4000)
            else:
                self.risultati_immobili_table.setSortingEnabled(True)
                self.result_count_label.setText("Nessun immobile trovato con i criteri specificati.")
        except AttributeError as ae:
            logging.getLogger("CatastoGUI").error(
                f"Metodo di ricerca immobili non trovato nel db_manager: {ae}", exc_info=True)
            QMessageBox.critical(
                self, "Errore Interno", f"Funzionalità di ricerca non implementata correttamente nel gestore DB: {ae}")
        except Exception as e:
            logging.getLogger("CatastoGUI").error(
                f"Errore durante la ricerca avanzata immobili: {e}", exc_info=True)
            QMessageBox.critical(self, "Errore Ricerca",
                                 f"Si è verificato un errore imprevisto: {e}")

    def _apri_menu_immobile(self, position: QPoint):
        index = self.risultati_immobili_table.indexAt(position)
        if not index.isValid():
            return
        row = index.row()
        def _cell(col):
            item = self.risultati_immobili_table.item(row, col)
            return item.text() if item else ""
        id_imm, numero, comune, _, natura = _cell(0), _cell(1), _cell(2), _cell(3), _cell(4)
        menu = QMenu(self.risultati_immobili_table)
        menu.addAction(f"ID Immobile: {id_imm}").triggered.connect(
            lambda: QApplication.clipboard().setText(id_imm))
        menu.addAction(f"Partita N.: {numero}").triggered.connect(
            lambda: QApplication.clipboard().setText(numero))
        menu.addAction(f"Comune: {comune}").triggered.connect(
            lambda: QApplication.clipboard().setText(comune))
        if natura:
            menu.addAction(f"Natura: {natura}").triggered.connect(
                lambda: QApplication.clipboard().setText(natura))
        menu.exec(self.risultati_immobili_table.viewport().mapToGlobal(position))

class UnifiedFuzzySearchThread(QThread):
    """Thread unificato per eseguire ricerche fuzzy in background."""
    results_ready = pyqtSignal(dict)
    error_occurred = pyqtSignal(str)
    progress_updated = pyqtSignal(int)

    def __init__(self, gin_search_manager, query_text, options):
        super().__init__()
        self.gin_search_manager = gin_search_manager
        self.query_text = query_text
        self.options = options

    def run(self):
        """Esegue la ricerca fuzzy."""
        try:
            self.progress_updated.emit(10)
            
            threshold = self.options.get('threshold', 0.3)

            # --- MODIFICA: Logica di ricerca semplificata ---
            # Questo thread ora chiama un metodo unificato che a sua volta
            # orchestra le ricerche individuali.
            # Assumiamo che `gin_search_manager` abbia un metodo come `search_all_entities_fuzzy`.
            if not hasattr(self.gin_search_manager, 'search_all_entities_fuzzy'):
                self.error_occurred.emit("Il DB Manager non supporta 'search_all_entities_fuzzy'.")
                return

            self.progress_updated.emit(30)

            results_data = self.gin_search_manager.search_all_entities_fuzzy(
                query_text=self.query_text,
                search_possessori=self.options.get('search_possessori', True),
                search_localita=self.options.get('search_localita', True),
                search_immobili=self.options.get('search_immobili', True),
                search_variazioni=self.options.get('search_variazioni', True),
                search_contratti=self.options.get('search_contratti', True),
                search_partite=self.options.get('search_partite', True),
                max_results_per_type=self.options.get('max_results_per_type', 50),
                similarity_threshold=threshold
            )

            # Prepara il dizionario finale per l'emissione del segnale
            final_results = {
                'query_text': self.query_text,
                'threshold': threshold,
                'timestamp': datetime.now(),
                'total_results': sum(len(entities) for entities in results_data.values()),
                'results_by_type': results_data # Mantiene la struttura per tipo
            }

            self.progress_updated.emit(100)
            self.results_ready.emit(final_results)

        except Exception as e:
            logging.getLogger(__name__).error(f"Errore nel thread di ricerca: {e}", exc_info=True)
            self.error_occurred.emit(str(e))


# ========================================================================
# WIDGET PRINCIPALE UNIFICATO
# ========================================================================

class UnifiedFuzzySearchWidget(QWidget):
    """Widget unificato per ricerca fuzzy con una singola interfaccia robusta."""

    # --- MODIFICA: Il costruttore non ha più il parametro 'mode' ---
    def __init__(self, db_manager, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.parent_window = parent
        self.logger = logging.getLogger(__name__)

        # Inizializza componenti GIN. Assumiamo che db_manager sia già esteso.
        self.gin_search = self.db_manager

        # Variabili di stato
        self.current_results = {}
        self.search_thread = None
        self.search_timer = QTimer()
        self.search_timer.setSingleShot(True)
        self.search_timer.timeout.connect(self._perform_search)

        # Setup UI
        self._init_ui() # --- MODIFICA: Chiamata a un singolo metodo di setup UI
        self._setup_signals()
        self._check_gin_status()

  
    def _init_ui(self):
        """Configura l'interfaccia utente unificata con un layout robusto."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(12)

        # Titolo e sottotitolo pagina
        _title = QLabel("Ricerca Globale")
        _title.setObjectName("pageTitle")
        main_layout.addWidget(_title)
        _subtitle = QLabel("Ricerca fuzzy in possessori, località, immobili, variazioni, contratti e partite. Usa la soglia per ampliare o restringere i match.")
        _subtitle.setObjectName("pageSubtitle")
        main_layout.addWidget(_subtitle)

        # Contenitore principale con stretch
        content_container_widget = QWidget()
        content_layout = QVBoxLayout(content_container_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(10)

        # === AREA RICERCA — card bianca ===
        search_frame = QFrame()
        search_frame.setObjectName("card")
        search_frame.setMaximumHeight(130)
        search_layout = QVBoxLayout(search_frame)
        search_layout.setContentsMargins(14, 12, 14, 12)
        search_layout.setSpacing(10)

        # Riga 1: search box prominente
        search_row = QHBoxLayout()
        search_row.setSpacing(8)
        _lbl_search = QLabel()
        _lbl_search.setPixmap(QIcon(str(get_icon_path("search"))).pixmap(QSize(18, 18)))
        search_row.addWidget(_lbl_search)
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Cerca in possessori, località, immobili, variazioni, contratti, partite…")
        self.search_edit.setMinimumHeight(36)
        search_row.addWidget(self.search_edit, 1)
        self.clear_btn = QPushButton()
        self.clear_btn.setObjectName("secondaryButton")
        self.clear_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_LineEditClearButton))
        self.clear_btn.setToolTip("Pulisci ricerca")
        self.clear_btn.setMaximumWidth(36)
        self.clear_btn.setMinimumWidth(36)
        search_row.addWidget(self.clear_btn)
        self.search_btn = QPushButton("Cerca")
        self.search_btn.setDefault(True)
        self.search_btn.setMinimumWidth(110)
        search_row.addWidget(self.search_btn)
        search_layout.addLayout(search_row)

        # Riga 2: controlli avanzati (soglia, max risultati, export)
        controls_row = QHBoxLayout()
        controls_row.setSpacing(10)
        _lbl_soglia = QLabel("Soglia:")
        _lbl_soglia.setProperty("muted", "true")
        controls_row.addWidget(_lbl_soglia)
        self.precision_slider = QSlider(Qt.Orientation.Horizontal)
        self.precision_slider.setRange(10, 90)
        self.precision_slider.setValue(30)
        self.precision_slider.setMaximumWidth(130)
        controls_row.addWidget(self.precision_slider)

        self.precision_label = QLabel("0.30")
        self.precision_label.setMinimumWidth(36)
        controls_row.addWidget(self.precision_label)

        controls_row.addSpacing(12)

        _lbl_max = QLabel("Max risultati:")
        _lbl_max.setProperty("muted", "true")
        controls_row.addWidget(_lbl_max)
        self.max_results_combo = QComboBox()
        self.max_results_combo.addItems(["50", "100", "200", "500"])
        self.max_results_combo.setCurrentText("100")
        self.max_results_combo.setMaximumWidth(80)
        controls_row.addWidget(self.max_results_combo)

        controls_row.addStretch()

        self.btn_export_csv = QPushButton("Esporta CSV")
        self.btn_export_csv.setObjectName("secondaryButton")
        self.btn_export_csv.setEnabled(False)
        controls_row.addWidget(self.btn_export_csv)

        self.btn_export_pdf = QPushButton("Esporta PDF")
        self.btn_export_pdf.setObjectName("secondaryButton")
        self.btn_export_pdf.setEnabled(False)
        if not FPDF_AVAILABLE:
            self.btn_export_pdf.setToolTip("Libreria FPDF2 non trovata. Funzione non disponibile.")
        controls_row.addWidget(self.btn_export_pdf)

        search_layout.addLayout(controls_row)
        # --- FINE BLOCCO DA SOSTITUIRE ---
        
        content_layout.addWidget(search_frame) # AGGIUNTO AL CONTENT_LAYOUT

        # === CHECKBOXES (da aggiungere al content_layout) ===
        types_layout = QHBoxLayout()
        types_group = QGroupBox("Cerca in:")
        types_group_layout = QHBoxLayout(types_group)
        # ... (tutte le checkbox vengono create e aggiunte a types_group_layout come prima) ...
        self.search_possessori_cb = QCheckBox("Possessori"); self.search_possessori_cb.setIcon(QIcon(str(get_icon_path("users")))); self.search_possessori_cb.setChecked(True); types_group_layout.addWidget(self.search_possessori_cb)
        self.search_localita_cb = QCheckBox("Località"); self.search_localita_cb.setIcon(QIcon(str(get_icon_path("map-pin")))); self.search_localita_cb.setChecked(True); types_group_layout.addWidget(self.search_localita_cb)
        self.search_immobili_cb = QCheckBox("Immobili"); self.search_immobili_cb.setIcon(QIcon(str(get_icon_path("building")))); self.search_immobili_cb.setChecked(True); types_group_layout.addWidget(self.search_immobili_cb)
        self.search_variazioni_cb = QCheckBox("Variazioni"); self.search_variazioni_cb.setIcon(QIcon(str(get_icon_path("report")))); self.search_variazioni_cb.setChecked(True); types_group_layout.addWidget(self.search_variazioni_cb)
        self.search_contratti_cb = QCheckBox("Contratti"); self.search_contratti_cb.setIcon(QIcon(str(get_icon_path("file-text")))); self.search_contratti_cb.setChecked(True); types_group_layout.addWidget(self.search_contratti_cb)
        self.search_partite_cb = QCheckBox("Partite"); self.search_partite_cb.setIcon(QIcon(str(get_icon_path("bar-chart")))); self.search_partite_cb.setChecked(True); types_group_layout.addWidget(self.search_partite_cb)
        types_layout.addWidget(types_group)

        content_layout.addLayout(types_layout) # AGGIUNTO AL CONTENT_LAYOUT

        # === AREA RISULTATI (da aggiungere al content_layout) ===
        self.results_tabs = QTabWidget()
        self.results_tabs.setMinimumHeight(400)
        # ... (tutta la creazione delle tabelle e l'aggiunta a results_tabs rimane identica) ...
        self.unified_table = self._create_table_widget(["Tipo", "Nome/Descrizione", "Dettagli", "Similarità", "Campo"], [1, 2], 3); self.results_tabs.addTab(self.unified_table, QIcon(str(get_icon_path("search"))), "Tutti")
        self.possessori_table = self._create_table_widget(["Nome Completo", "Comune", "Partite", "Similitud."], [0], 3); self.results_tabs.addTab(self.possessori_table, QIcon(str(get_icon_path("users"))), "Possessori")
        self.localita_table = self._create_table_widget(["Nome", "Tipo", "Civico", "Comune", "Immobili", "Similitud."], [0, 3], 5); self.results_tabs.addTab(self.localita_table, QIcon(str(get_icon_path("map-pin"))), "Località")
        self.immobili_table = self._create_table_widget(["Natura", "Classificazione", "Partita", "Suffisso", "Comune", "Similitud."], [1, 4], 5); self.results_tabs.addTab(self.immobili_table, QIcon(str(get_icon_path("building"))), "Immobili")
        self.variazioni_table = self._create_table_widget(["Tipo", "Data", "Rif. e Partita Origine", "Similitud."], [2], 3)
        self.results_tabs.addTab(self.variazioni_table, QIcon(str(get_icon_path("report"))), "Variazioni")
        self.contratti_table = self._create_table_widget(["Tipo", "Data", "Partita", "Similitud."], [0], 3); self.results_tabs.addTab(self.contratti_table, QIcon(str(get_icon_path("file-text"))), "Contratti")
        # --- MODIFICA QUESTA RIGA ---
        self.partite_table = self._create_table_widget(
            ["Numero", "Suffisso", "Possessori", "Tipo", "Stato", "Data Impianto", "Comune", "Similitud."],
            [2, 6],  # Indici delle colonne da espandere (Possessori e Comune)
            7        # L'indice della colonna 'Similitud.' ora è 7
        )
        self.results_tabs.addTab(self.partite_table, QIcon(str(get_icon_path("bar-chart"))), "Partite")

        content_layout.addWidget(self.results_tabs) # AGGIUNTO AL CONTENT_LAYOUT

        # --- AGGIUNTA DEL CONTENITORE AL LAYOUT PRINCIPALE ---
        # Diamo a tutto il blocco dei contenuti un fattore di stretch > 0
        main_layout.addWidget(content_container_widget, 1)

        # === STATUS BAR ===
        status_frame = QFrame()
        status_frame.setObjectName("fuzzyStatusBar")
        status_frame.setMaximumHeight(32)
        status_layout = QHBoxLayout(status_frame)
        status_layout.setContentsMargins(10, 4, 10, 4)
        self.stats_label = QLabel("Inserire almeno 3 caratteri per iniziare")
        self.stats_label.setProperty("muted", "true")
        status_layout.addWidget(self.stats_label)
        status_layout.addStretch()
        self.indices_status_label = QLabel("Verifica indici…")
        self.indices_status_label.setProperty("muted", "true")
        status_layout.addWidget(self.indices_status_label)

        main_layout.addWidget(status_frame)

        self.search_edit.setFocus()

    def _create_table_widget(self, headers, stretch_columns, similarity_col_index):
        """Helper per creare una QTableWidget standardizzata."""
        table = QTableWidget()
        table.setColumnCount(len(headers))
        table.setHorizontalHeaderLabels(headers)
        table.setAlternatingRowColors(True)
        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        header = table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        header.setStretchLastSection(True)
        
        # Salva l'indice della colonna di similarità per usi futuri (es. colorazione)
        table.setProperty("similarity_col", similarity_col_index)
        return table

    def _setup_signals(self):
        """Configura i segnali."""
        self.search_edit.textChanged.connect(self._on_search_text_changed)
        self.search_btn.clicked.connect(self._perform_search)
        self.clear_btn.clicked.connect(self._clear_search)
        
        self.precision_slider.valueChanged.connect(lambda v: self.precision_label.setText(f"{v/100:.2f}"))
        self.precision_slider.sliderReleased.connect(self._trigger_search_if_text)

        self.max_results_combo.currentTextChanged.connect(self._trigger_search_if_text)
        # --- MODIFICA QUI: Colleghiamo i nuovi pulsanti ---
        # Rimuoviamo la vecchia riga: self.export_btn.clicked.connect(self._export_results)
        self.btn_export_csv.clicked.connect(self._handle_export_csv)
        self.btn_export_pdf.clicked.connect(self._handle_export_pdf)

        # Checkbox
        for cb in [self.search_possessori_cb, self.search_localita_cb, self.search_immobili_cb,
                   self.search_variazioni_cb, self.search_contratti_cb, self.search_partite_cb]: # AGGIUNTE NUOVE CHECKBOX
            cb.toggled.connect(self._trigger_search_if_text)

        # Double-click
        
        # --- MODIFICA QUI: Colleghiamo il doppio click per tutte le tabelle ---
        self.unified_table.doubleClicked.connect(self._on_unified_double_click)
        self.possessori_table.doubleClicked.connect(self._on_possessori_double_click)
        self.localita_table.doubleClicked.connect(self._on_localita_double_click)
        self.immobili_table.doubleClicked.connect(self._on_immobili_double_click)
        self.variazioni_table.doubleClicked.connect(self._on_variazioni_double_click)
        self.contratti_table.doubleClicked.connect(self._on_contratti_double_click)
        self.partite_table.doubleClicked.connect(self._on_partite_double_click)

    def _check_gin_status(self):
        """Verifica lo stato degli indici GIN."""
        if not self.gin_search or not hasattr(self.gin_search, 'verify_gin_indices'):
            self.indices_status_label.setText("Ricerca non disponibile")
            return
        try:
            result = self.gin_search.verify_gin_indices()
            if result.get('status') == 'OK' and result.get('gin_indices', 0) > 0:
                self.indices_status_label.setText(f"Indici GIN attivi ({result['gin_indices']})")
            else:
                self.indices_status_label.setText("Indici GIN mancanti o non validi")
        except Exception as e:
            self.indices_status_label.setText("Errore verifica indici")
            self.logger.error(f"Errore verifica indici GIN: {e}")

    def _on_search_text_changed(self, text):
        """Gestisce il cambiamento del testo di ricerca."""
        if len(text) >= 3:
            self.search_timer.start(800) # Delay per evitare ricerche a ogni tasto
            self.stats_label.setText("Pronto per la ricerca...")
        else:
            self.search_timer.stop()
            self._clear_results()
            self.stats_label.setText(f"Inserire almeno {3 - len(text)} caratteri in più")

    def _trigger_search_if_text(self):
        """Rilancia la ricerca se c'è abbastanza testo."""
        if len(self.search_edit.text().strip()) >= 3:
            self._perform_search()

    def _perform_search(self):
        """Esegue la ricerca vera e propria, gestendo il thread precedente."""
        query_text = self.search_edit.text().strip()
        if len(query_text) < 3:
            return

        if not self.gin_search:
            QMessageBox.warning(self, "Errore", "Sistema di ricerca fuzzy non disponibile.")
            return

        # --- MODIFICA CRUCIALE: Gestione del thread esistente ---
        if self.search_thread and self.search_thread.isRunning():
            self.logger.debug("Ricerca precedente ancora in corso. Tentativo di fermarla.")
            self.search_thread.quit()  # Chiede al thread di terminare in modo pulito
            self.search_thread.wait(500) # Attende al massimo 500ms
            if self.search_thread.isRunning():
                self.logger.warning("Il thread precedente non si è fermato in tempo, terminazione forzata.")
                self.search_thread.terminate() # Estrema ratio
                self.search_thread.wait()

        search_options = {
            'threshold': self.precision_slider.value() / 100.0,
            'max_results': int(self.max_results_combo.currentText()),
            'search_possessori': self.search_possessori_cb.isChecked(),
            'search_localita': self.search_localita_cb.isChecked(),
            'search_immobili': self.search_immobili_cb.isChecked(),
            # --- AGGIUNGERE QUESTE OPZIONI ---
            'search_variazioni': self.search_variazioni_cb.isChecked(),
            'search_contratti': self.search_contratti_cb.isChecked(),
            'search_partite': self.search_partite_cb.isChecked(),
        }

        
        self.search_btn.setEnabled(False)
        self.stats_label.setText("Ricerca in corso...")
        
        self.search_thread = UnifiedFuzzySearchThread(self.gin_search, query_text, search_options)
        self.search_thread.results_ready.connect(self._display_results)
        self.search_thread.error_occurred.connect(self._handle_search_error)
        self.search_thread.finished.connect(lambda: self.search_btn.setEnabled(True))
        self.search_thread.start()

    def _display_results(self, results):
        """Visualizza i risultati della ricerca."""
        self.current_results = results
        results_by_type = results.get('results_by_type', {})
        
        self._populate_unified_table(results_by_type)
        self._populate_individual_tables(results_by_type)
        self._update_tab_counters(results_by_type)
        
        total = results.get('total_results', 0)
        self.stats_label.setText(f"Trovati {total} risultati per '{results.get('query_text')}'")
        # --- MODIFICA QUI ---
        self.btn_export_csv.setEnabled(total > 0)
        if FPDF_AVAILABLE:
            self.btn_export_pdf.setEnabled(total > 0)
    
    def _populate_table(self, table: QTableWidget, data: List[Dict], row_mapper_func):
        """Funzione helper per popolare una QTableWidget."""
        table.setRowCount(0)
        table.setRowCount(len(data))
        similarity_col = table.property("similarity_col")

        for row_idx, item_data in enumerate(data):
            row_content = row_mapper_func(item_data)
            for col_idx, cell_text in enumerate(row_content):
                item = QTableWidgetItem(str(cell_text))
                if col_idx == 0: # Salva i dati completi nel primo item della riga
                    item.setData(Qt.ItemDataRole.UserRole, item_data)
                
                # Applica colorazione alla colonna di similarità
                if similarity_col is not None and col_idx == similarity_col:
                    try:
                        similarity = float(cell_text)
                        if similarity > 0.7: item.setBackground(QColor("#d4edda")) # Verde
                        elif similarity > 0.5: item.setBackground(QColor("#fff3cd")) # Giallo
                        else: item.setBackground(QColor("#f8d7da")) # Rosso
                    except (ValueError, TypeError):
                        pass
                
                table.setItem(row_idx, col_idx, item)

    def _populate_unified_table(self, results_by_type: Dict[str, List]):
        self.unified_table.setRowCount(0)
        row = 0
        _type_icon_names = {
            'possessore': 'users', 'localita': 'map-pin', 'immobile': 'building',
            'variazione': 'report', 'contratto': 'file-text', 'partita': 'bar-chart'
        }
        _type_labels = {
            'possessore': 'Possessore', 'localita': 'Località', 'immobile': 'Immobile',
            'variazione': 'Variazione', 'contratto': 'Contratto', 'partita': 'Partita'
        }
        for entity_type, entities in results_by_type.items():
            for entity in entities:
                self.unified_table.insertRow(row)
                _icon_name = _type_icon_names.get(entity_type, 'file-text')
                _tipo_item = QTableWidgetItem(_type_labels.get(entity_type, entity_type.title()))
                _tipo_item.setIcon(QIcon(str(get_icon_path(_icon_name))))

                # ["Tipo", "Nome/Descrizione", "Dettagli", "Similarità", "Campo"]
                self.unified_table.setItem(row, 0, _tipo_item)
                self.unified_table.item(row, 0).setData(Qt.ItemDataRole.UserRole, {'type': entity_type, 'data': entity}) # Salva dati per doppio click
                
                self.unified_table.setItem(row, 1, QTableWidgetItem(entity.get('display_text', '')))
                self.unified_table.setItem(row, 2, QTableWidgetItem(entity.get('detail_text', '')))
                self.unified_table.setItem(row, 3, QTableWidgetItem(f"{entity.get('similarity_score', 0):.3f}"))
                self.unified_table.setItem(row, 4, QTableWidgetItem(entity.get('search_field', '')))
                row += 1

    def _populate_individual_tables(self, results_by_type: Dict[str, List]):
        self._populate_table(self.possessori_table, results_by_type.get('possessore', []), 
            lambda p: [p.get('nome_completo', ''), p.get('comune_nome', ''), p.get('num_partite', 0), f"{p.get('similarity_score', 0):.3f}"])
        
        # --- MODIFICA QUESTA CHIAMATA ---
        self._populate_table(self.localita_table, results_by_type.get('localita', []),
            lambda l: [
                l.get('nome', ''),
                l.get('tipo', '') or '',      # Aggiunto
                l.get('civico', '') or '',    # Aggiunto
                l.get('comune_nome', ''),
                l.get('num_immobili', 0),
                f"{l.get('similarity_score', 0):.3f}"
            ]
        )
        # --- MODIFICA QUESTA CHIAMATA ---
        self._populate_table(self.immobili_table, results_by_type.get('immobile', []), 
            lambda i: [
                i.get('natura', ''),
                i.get('classificazione', ''),
                i.get('numero_partita', ''),
                i.get('suffisso_partita', '') or '', # Aggiunto il valore per la nuova colonna
                i.get('comune_nome', ''),
                f"{i.get('similarity_score', 0):.3f}"
            ]
        )

        self._populate_table(self.variazioni_table, results_by_type.get('variazione', []),
            lambda v: [
                v.get('tipo', ''),
                v.get('data_variazione', ''),
                v.get('detail_text', ''), # Usa detail_text per la nuova colonna
                f"{v.get('similarity_score', 0):.3f}"])

        self._populate_table(self.contratti_table, results_by_type.get('contratto', []), 
            lambda c: [c.get('tipo', ''), c.get('data_contratto', ''), c.get('numero_partita', ''), f"{c.get('similarity_score', 0):.3f}"])

        self._populate_table(self.partite_table, results_by_type.get('partita', []), 
            lambda pt: [
                pt.get('numero_partita', ''),
                pt.get('suffisso_partita', '') or '',
                pt.get('possessori_concatenati', '') or '', # NUOVA COLONNA
                pt.get('tipo_partita', ''),
                pt.get('stato', ''),
                str(pt.get('data_impianto', '')) if pt.get('data_impianto') else '',
                pt.get('comune_nome', ''),
                f"{pt.get('similarity_score', 0):.3f}"
            ]
        )
    def _update_tab_counters(self, results_by_type: Dict[str, List]):
        """Aggiorna i contatori nei titoli dei tab."""
        # --- MODIFICA: La logica di base_index non è più necessaria ---
        self.results_tabs.setTabText(0, f"Tutti ({sum(len(v) for v in results_by_type.values())})")
        self.results_tabs.setTabText(1, f"Possessori ({len(results_by_type.get('possessore', []))})")
        self.results_tabs.setTabText(2, f"Località ({len(results_by_type.get('localita', []))})")
        self.results_tabs.setTabText(3, f"Immobili ({len(results_by_type.get('immobile', []))})")
        self.results_tabs.setTabText(4, f"Variazioni ({len(results_by_type.get('variazione', []))})")
        self.results_tabs.setTabText(5, f"Contratti ({len(results_by_type.get('contratto', []))})")
        self.results_tabs.setTabText(6, f"Partite ({len(results_by_type.get('partita', []))})")

    def _clear_results(self):
        """Pulisce tutti i risultati e i contatori."""
        tables = [
            self.unified_table, self.possessori_table, self.localita_table, 
            self.immobili_table, self.variazioni_table, self.contratti_table, 
            self.partite_table
        ]
        for table in tables:
            table.setRowCount(0)
        
        self._update_tab_counters({})
        
        # --- MODIFICA QUI: Disabilita i nuovi pulsanti invece del vecchio ---
        self.btn_export_csv.setEnabled(False)
        self.btn_export_pdf.setEnabled(False)
        
        self.current_results = {}

    def _handle_search_error(self, error_message):
        """Gestisce gli errori di ricerca."""
        self.search_btn.setEnabled(True)
        self.stats_label.setText("Errore ricerca")
        self.logger.error(f"Errore ricerca fuzzy: {error_message}")
        QMessageBox.critical(self, "Errore Ricerca", f"Si è verificato un errore:\n{error_message}")

    def _clear_search(self):
        """Pulisce il campo di ricerca e i risultati."""
        self.search_edit.clear()
        self._clear_results()
        self.stats_label.setText("Pronto")


    def _on_unified_double_click(self, index):
        """
        Gestisce il doppio click nella tabella unificata, chiamando il gestore appropriato.
        """
        if not index.isValid(): return
            
        item_con_dati = self.unified_table.item(index.row(), 0)
        if not item_con_dati: return

        full_item_data = item_con_dati.data(Qt.ItemDataRole.UserRole)
        if not isinstance(full_item_data, dict): return

        entity_type = full_item_data.get('type')

        # Simula un evento di doppio click sul tab appropriato
        if entity_type == 'partita':
            self._on_partite_double_click(index)
        elif entity_type == 'possessore':
            self._on_possessori_double_click(index)
        elif entity_type == 'localita':
            self._on_localita_double_click(index)
        elif entity_type == 'immobile':
            self._on_immobili_double_click(index)
        elif entity_type == 'variazione':
            self._on_variazioni_double_click(index)
        elif entity_type == 'contratto':
            self._on_contratti_double_click(index)
        else:
            QMessageBox.warning(self, "Tipo Sconosciuto", f"Nessuna azione di dettaglio definita per il tipo '{entity_type}'.")
    def _handle_export_csv(self):
        """Esporta i risultati correnti della ricerca unificata in un file CSV."""
        if not self.current_results or not self.current_results.get('total_results', 0) > 0:
            QMessageBox.warning(self, "Nessun Risultato", "Non ci sono risultati da esportare.")
            return

        query_text = self.current_results.get('query_text', 'ricerca')
        default_filename = f"ricerca_fuzzy_{query_text}_{date.today().isoformat()}.csv"
        filename, _ = QFileDialog.getSaveFileName(self, "Esporta Risultati in CSV", default_filename, "File CSV (*.csv)")

        if not filename:
            return

        try:
            with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
                # Usiamo le intestazioni della tabella "Tutti"
                headers = ['Tipo Entità', 'Nome/Descrizione', 'Dettagli', 'Similarità', 'Campo Trovato']
                writer = csv.writer(csvfile, delimiter=';')
                writer.writerow(headers)
                
                for entity_type, entities in self.current_results.get('results_by_type', {}).items():
                    for entity in entities:
                        writer.writerow([
                            entity_type,
                            entity.get('display_text', ''),
                            entity.get('detail_text', ''),
                            f"{entity.get('similarity_score', 0):.3f}",
                            entity.get('search_field', '')
                        ])
            prompt_to_open_file(self, filename)
        except Exception as e:
            self.logger.error(f"Errore esportazione CSV fuzzy: {e}", exc_info=True)
            QMessageBox.critical(self, "Errore Esportazione", f"Impossibile salvare il file CSV:\n{e}")

    def _handle_export_pdf(self):
        """Esporta i risultati correnti della ricerca unificata in un file PDF."""
        if not self.current_results or not self.current_results.get('total_results', 0) > 0:
            QMessageBox.warning(self, "Nessun Risultato", "Non ci sono risultati da esportare.")
            return
            
        query_text = self.current_results.get('query_text', 'ricerca')
        default_filename = f"ricerca_fuzzy_{query_text}_{date.today().isoformat()}.pdf"
        filename, _ = QFileDialog.getSaveFileName(self, "Esporta Risultati in PDF", default_filename, "File PDF (*.pdf)")

        if not filename:
            return

        try:
            pdf = BulkReportPDF(report_title=f"Risultati Ricerca Fuzzy per '{query_text}'")
            pdf.alias_nb_pages()
            pdf.set_font('Times', '', 12)
            pdf.set_auto_page_break(auto=True, margin=15)
            pdf.add_page()
            
            for entity_type, entities in self.current_results.get('results_by_type', {}).items():
                if not entities: continue
                
                pdf.set_font('Helvetica', 'B', 12)
                pdf.cell(0, 10, f"Risultati per: {entity_type.title()} ({len(entities)})", ln=1)
                
                headers = ['Nome/Descrizione', 'Dettagli', 'Similarità']
                # Adattiamo i dati per la tabella
                data_rows = [
                    (entity.get('display_text', ''), entity.get('detail_text', ''), f"{entity.get('similarity_score', 0):.3f}")
                    for entity in entities
                ]
                # La classe BulkReportPDF gestirà la creazione della tabella
                pdf.print_table(headers, data_rows)
                pdf.ln(5)

            pdf.output(filename)
            prompt_to_open_file(self, filename)
        except Exception as e:
            self.logger.error(f"Errore esportazione PDF fuzzy: {e}", exc_info=True)
            QMessageBox.critical(self, "Errore Esportazione", f"Impossibile generare il file PDF:\n{e}")
   

    def _get_entity_id_from_table(self, table: QTableWidget, index) -> Optional[int]:
        """Helper generico per estrarre l'ID dell'entità da una riga della tabella."""
        if not index.isValid():
            return None

        # I dati completi sono sempre salvati nella UserRole della prima colonna (indice 0)
        item_con_dati = table.item(index.row(), 0)
        if not item_con_dati:
            return None
            
        entity_data_wrapper = item_con_dati.data(Qt.ItemDataRole.UserRole)
        if not isinstance(entity_data_wrapper, dict):
            return None

        # Gestisce sia il tab "Tutti" (dove i dati sono annidati in 'data') 
        # sia i tab specifici (dove i dati sono al primo livello).
        if 'data' in entity_data_wrapper and isinstance(entity_data_wrapper['data'], dict):
            return entity_data_wrapper['data'].get('entity_id')
        elif 'entity_id' in entity_data_wrapper:
            return entity_data_wrapper.get('entity_id')

        return None

    def _on_possessori_double_click(self, index):
        entity_id = self._get_entity_id_from_table(self.possessori_table, index)
        if entity_id:
            dialog = ModificaPossessoreDialog(self.db_manager, entity_id, self)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                self._perform_search() # Aggiorna i risultati se ci sono state modifiche

    def _on_localita_double_click(self, index):
        entity_id = self._get_entity_id_from_table(self.localita_table, index)
        if entity_id:
            localita_details = self.db_manager.get_localita_details(entity_id)
            if localita_details and localita_details.get('comune_id'):
                dialog = ModificaLocalitaDialog(self.db_manager, entity_id, localita_details.get('comune_id'), self)
                if dialog.exec() == QDialog.DialogCode.Accepted:
                    self._perform_search()
            else:
                QMessageBox.warning(self, "Errore Dati", f"Impossibile caricare i dettagli per la località ID {entity_id}.")

    def _on_immobili_double_click(self, index):
        entity_id = self._get_entity_id_from_table(self.immobili_table, index)
        if entity_id:
            immobile_details = self.db_manager.get_immobile_details(entity_id)
            if immobile_details and immobile_details.get('partita_id'):
                partita_details = self.db_manager.get_partita_details(immobile_details.get('partita_id'))
                if partita_details and partita_details.get('comune_id'):
                    dialog = ModificaImmobileDialog(self.db_manager, entity_id, partita_details.get('comune_id'), self)
                    if dialog.exec() == QDialog.DialogCode.Accepted:
                        self._perform_search()
                else:
                    QMessageBox.warning(self, "Errore Dati", f"Impossibile determinare il comune per l'immobile ID {entity_id}.")
            else:
                 QMessageBox.warning(self, "Errore Dati", f"Impossibile caricare i dettagli per l'immobile ID {entity_id}.")

    def _on_partite_double_click(self, index):
        entity_id = self._get_entity_id_from_table(self.partite_table, index)
        if entity_id:
            full_details = self.db_manager.get_partita_details(entity_id)
            if full_details:
                dialog = PartitaDetailsDialog(full_details, self)
                dialog.exec()
            else:
                QMessageBox.warning(self, "Errore Dati", f"Impossibile caricare i dettagli per la partita ID {entity_id}.")

    def _show_generic_details_popup(self, table: QTableWidget, index: 'QModelIndex', entity_type_name: str):
        """Mostra un popup leggibile per entità senza un dialogo di dettaglio dedicato."""
        item_con_dati = table.item(index.row(), 0)
        if not item_con_dati: return
        entity_data = item_con_dati.data(Qt.ItemDataRole.UserRole)
        entity_id = entity_data.get('entity_id', 'N/A')

        testo_formattato = f"<h3>Dettagli - {entity_type_name.title()} ID: {entity_id}</h3>"
        testo_formattato += "<table border='0' cellspacing='5'>"
        for key, value in entity_data.items():
            chiave_formattata = key.replace('_', ' ').title()
            testo_formattato += f"<tr><td><b>{chiave_formattata}:</b></td><td>{value}</td></tr>"
        testo_formattato += "</table>"
        QMessageBox.information(self, f"Dettagli - {entity_type_name.title()}", testo_formattato)

    def _on_variazioni_double_click(self, index):
        self._show_generic_details_popup(self.variazioni_table, index, 'variazione')

    def _on_contratti_double_click(self, index):
        self._show_generic_details_popup(self.contratti_table, index, 'contratto')
