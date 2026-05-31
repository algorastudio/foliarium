"""
partite.py — Ricerca partite catastali (worker, model, proxy, card e widget).

Estratto da search_widgets.py (Sprint 3 refactor — six-hats).
Le classi sono anche re-esportate da search_widgets per preservare la
backward compatibility con i consumer esistenti.
"""
from __future__ import annotations

import logging
from typing import Optional

from PyQt6.QtCore import (
    QAbstractTableModel, QModelIndex, QPoint, QSortFilterProxyModel, Qt,
    QThread, pyqtSignal,
)
from PyQt6.QtWidgets import (
    QAbstractItemView, QApplication, QComboBox, QDialog, QFrame,
    QGridLayout, QGroupBox, QHBoxLayout, QHeaderView, QLabel, QLineEdit,
    QMenu, QMessageBox, QProgressBar, QPushButton, QSpinBox, QStyle,
    QTableView, QVBoxLayout, QWidget,
)

from foliarium.ui.widgets.custom import show_status_message as _show_status_message
from dialogs import (
    ComuneSelectionDialog,
)

try:
    from catasto_db_manager import DBMError
except ImportError:
    class DBMError(Exception):
        pass


logger = logging.getLogger("CatastoGUI.search.partite")


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
        stato_lbl = QLabel(stato or "—")
        stato_lbl.setObjectName("statoBadge")
        if stato:
            stato_lbl.setProperty("stato", stato.lower())
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

        if role == Qt.ItemDataRole.EditRole:
            if col == 0:
                return p.get('id', 0)
            if col == 1:
                return p.get('numero_partita', 0)
            return self.data(index, Qt.ItemDataRole.DisplayRole)

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
        self._table = QTableView()
        self._model = PartiteTableModel(self)
        #self._proxy = QSortFilterProxyModel(self)
        self._proxy = _PartiteFilterProxy(self)

        self._proxy.setSourceModel(self._model)
        self._table.setModel(self._proxy)
        
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
        row = self._table.currentIndex().row()
        numero_text = str(self._proxy.data(self._proxy.index(row, 1))) if row >= 0 else str(self._selected_partita_id)
        self._archivia_partita(self._selected_partita_id, numero_text)



