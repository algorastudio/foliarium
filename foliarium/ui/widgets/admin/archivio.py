"""Archivio record soft-deleted: model generico + widget."""
from __future__ import annotations

import logging
from typing import Optional, List, Any, TYPE_CHECKING

from PyQt6.QtCore import (
    QAbstractTableModel, QModelIndex, Qt,
)
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QAbstractItemView, QHBoxLayout, QHeaderView,
    QLabel, QMessageBox, QPushButton, QTabWidget, QTableView, QVBoxLayout,
)

from foliarium.ui.widgets.custom import LazyLoadedWidget

if TYPE_CHECKING:
    from catasto_db_manager import CatastoDBManager

logger = logging.getLogger("CatastoGUI.admin_widgets")




class GenericRecordsModel(QAbstractTableModel):
    """Modello generico per tabelle record-oriented: ogni riga è (record_id, [val0, val1, ...])."""

    def __init__(self, headers: List[str], parent=None, muted: bool = False):
        super().__init__(parent)
        self._headers = list(headers)
        self._rows: List[tuple] = []
        self._muted = muted

    def load(self, rows: List[tuple]) -> None:
        self.beginResetModel()
        self._rows = list(rows)
        self.endResetModel()

    def record_id_at(self, row: int) -> Optional[Any]:
        return self._rows[row][0] if 0 <= row < len(self._rows) else None

    def row_values(self, row: int) -> list:
        return self._rows[row][1] if 0 <= row < len(self._rows) else []

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
        values = self._rows[row][1]
        val = values[col] if col < len(values) else None
        if role in (Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.EditRole):
            if role == Qt.ItemDataRole.EditRole and col == 0:
                try:
                    return int(val)
                except (ValueError, TypeError):
                    return str(val) if val is not None else ''
            return str(val) if val is not None else ''
        if role == Qt.ItemDataRole.ForegroundRole and self._muted:
            return QColor("#616161")
        if role == Qt.ItemDataRole.TextAlignmentRole and col == 0:
            return int(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        return None

    def flags(self, index):
        return Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable

    def sort(self, column, order=Qt.SortOrder.AscendingOrder):
        if not self._rows or column >= len(self._headers):
            return
        self.layoutAboutToBeChanged.emit()
        def _key(r):
            vals = r[1]
            v = vals[column] if column < len(vals) else None
            return (v is None, v if v is not None else '')
        self._rows.sort(key=_key, reverse=(order == Qt.SortOrder.DescendingOrder))
        self.layoutChanged.emit()




class ArchivioWidget(LazyLoadedWidget):
    """
    Pannello amministrativo per la visualizzazione, ripristino ed eliminazione
    definitiva degli elementi archiviati.
    Mostra in tab separate: Comuni, Possessori, Località, Partite archiviate.
    """

    def __init__(self, db_manager: "CatastoDBManager", parent=None):
        super().__init__(parent)
        self.db_manager = db_manager

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 12, 16, 12)
        main_layout.setSpacing(8)

        header = QLabel("Archivio — Elementi nascosti (soft delete)")
        header.setObjectName("pageTitle")
        main_layout.addWidget(header)

        sub = QLabel(
            "Gli elementi archiviati non compaiono nelle liste e nelle ricerche. "
            "Usa 'Ripristina' per renderli nuovamente visibili, oppure "
            "'Elimina Definitivamente' per cancellarli in modo permanente."
        )
        sub.setWordWrap(True)
        sub.setObjectName("pageSubtitle")
        main_layout.addWidget(sub)

        self._tabs = QTabWidget()
        self._tabs.currentChanged.connect(self._on_tab_changed)
        main_layout.addWidget(self._tabs, 1)

        # Pulsanti azione (condivisi)
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        self._btn_ripristina = QPushButton("Ripristina Selezionato")
        self._btn_ripristina.setEnabled(False)
        self._btn_ripristina.clicked.connect(self._ripristina_selezionato)
        btn_row.addWidget(self._btn_ripristina)

        self._btn_elimina = QPushButton("Elimina Definitivamente")
        self._btn_elimina.setObjectName("dangerButton")
        self._btn_elimina.setEnabled(False)
        self._btn_elimina.clicked.connect(self._elimina_definitivamente)
        btn_row.addWidget(self._btn_elimina)

        btn_refresh = QPushButton("Aggiorna")
        btn_refresh.setObjectName("secondaryButton")
        btn_refresh.clicked.connect(self.load_data)
        btn_row.addWidget(btn_refresh)
        main_layout.addLayout(btn_row)

        # ── Tab Comuni ──────────────────────────────────────────────────────
        self._t_comuni, self._m_comuni = self._make_table(["ID", "Nome", "Provincia", "Regione", "Archiviato il"])
        self._tabs.addTab(self._t_comuni, "Comuni")

        # ── Tab Possessori ──────────────────────────────────────────────────
        self._t_poss, self._m_poss = self._make_table(["ID", "Nome Completo", "Cognome Nome", "Comune", "Archiviato il"])
        self._tabs.addTab(self._t_poss, "Possessori")

        # ── Tab Località ─────────────────────────────────────────────────────
        self._t_loc, self._m_loc = self._make_table(["ID", "Nome", "Tipologia", "Comune", "Archiviato il"])
        self._tabs.addTab(self._t_loc, "Località")

        # ── Tab Partite ──────────────────────────────────────────────────────
        self._t_part, self._m_part = self._make_table(["ID", "N° Partita", "Comune", "Stato", "Tipo", "Archiviato il"])
        self._tabs.addTab(self._t_part, "Partite")

        self._current_entity: str = "comuni"

    # ── helpers ──────────────────────────────────────────────────────────────

    def _make_table(self, headers: list[str]) -> tuple:
        model = GenericRecordsModel(headers, parent=self, muted=True)
        t = QTableView()
        t.setModel(model)
        t.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        t.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        t.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        t.setAlternatingRowColors(True)
        t.setSortingEnabled(True)
        t.verticalHeader().setVisible(False)
        hh = t.horizontalHeader()
        hh.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        hh.setStretchLastSection(True)
        t.selectionModel().selectionChanged.connect(self._update_button_state)
        return t, model

    def _update_button_state(self):
        tables = {
            "comuni":     self._t_comuni,
            "possessori": self._t_poss,
            "localita":   self._t_loc,
            "partite":    self._t_part,
        }
        has_selection = tables[self._current_entity].selectionModel().hasSelection()
        self._btn_ripristina.setEnabled(has_selection)
        self._btn_elimina.setEnabled(has_selection)

    def _on_tab_changed(self, idx: int):
        self._current_entity = ["comuni", "possessori", "localita", "partite"][idx]
        self._btn_ripristina.setEnabled(False)
        self._btn_elimina.setEnabled(False)

    def _load_data_on_first_show(self):
        self.load_data()

    # ── data loading ─────────────────────────────────────────────────────────

    def load_data(self):
        try:
            data = self.db_manager.get_tutti_archiviati()
        except Exception as e:
            QMessageBox.critical(self, "Errore", f"Impossibile caricare l'archivio:\n{e}")
            return
        self._fill_comuni(data.get("comuni", []))
        self._fill_possessori(data.get("possessori", []))
        self._fill_localita(data.get("localita", []))
        self._fill_partite(data.get("partite", []))
        self._btn_ripristina.setEnabled(False)
        self._btn_elimina.setEnabled(False)
        self._update_tab_titles(data)

    def _update_tab_titles(self, data: dict):
        labels = ["Comuni", "Possessori", "Località", "Partite"]
        keys   = ["comuni", "possessori", "localita", "partite"]
        for i, (label, key) in enumerate(zip(labels, keys)):
            n = len(data.get(key, []))
            self._tabs.setTabText(i, f"{label} ({n})" if n else label)

    def _fill_comuni(self, rows: list):
        self._m_comuni.load([
            (r["id"], [r["id"], r["nome"], r["provincia"], r["regione"],
                       str(r.get("archiviato_il") or "—")[:19]])
            for r in rows
        ])

    def _fill_possessori(self, rows: list):
        self._m_poss.load([
            (r["id"], [r["id"], r.get("nome_completo"), r.get("cognome_nome"),
                       r.get("comune_nome"), str(r.get("archiviato_il") or "—")[:19]])
            for r in rows
        ])

    def _fill_localita(self, rows: list):
        self._m_loc.load([
            (r["id"], [r["id"], r["nome"], r.get("tipologia_stradale"),
                       r.get("comune_nome"), str(r.get("archiviato_il") or "—")[:19]])
            for r in rows
        ])

    def _fill_partite(self, rows: list):
        def _num(r):
            suf = (r.get("suffisso_partita") or "").strip()
            return f"{r['numero_partita']}{f'/{suf}' if suf else ''}"
        self._m_part.load([
            (r["id"], [r["id"], _num(r), r.get("comune_nome"),
                       r.get("stato"), r.get("tipo"),
                       str(r.get("archiviato_il") or "—")[:19]])
            for r in rows
        ])

    # ── ripristino ───────────────────────────────────────────────────────────

    def _current_table_and_model(self):
        tables = {
            "comuni":     (self._t_comuni, self._m_comuni),
            "possessori": (self._t_poss, self._m_poss),
            "localita":   (self._t_loc, self._m_loc),
            "partite":    (self._t_part, self._m_part),
        }
        return tables[self._current_entity]

    def _ripristina_selezionato(self):
        ripristina_fn = {
            "comuni":     self.db_manager.ripristina_comune,
            "possessori": self.db_manager.ripristina_possessore,
            "localita":   self.db_manager.ripristina_localita,
            "partite":    self.db_manager.ripristina_partita,
        }
        entity_label = {
            "comuni": "comune", "possessori": "possessore",
            "localita": "località", "partite": "partita",
        }

        table, model = self._current_table_and_model()
        sel_rows = table.selectionModel().selectedRows()
        if not sel_rows:
            return
        row = sel_rows[0].row()
        record_id = model.record_id_at(row)
        if record_id is None:
            return
        values = model.row_values(row)
        nome = str(values[1]) if len(values) > 1 else str(record_id)
        label = entity_label[self._current_entity]

        risposta = QMessageBox.question(
            self, "Ripristina elemento",
            f"Ripristinare {label} '{nome}'?\n\n"
            "L'elemento tornerà visibile nelle liste e nelle ricerche.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if risposta != QMessageBox.StandardButton.Yes:
            return

        try:
            ripristina_fn[self._current_entity](record_id)
            self.load_data()
        except Exception as e:
            QMessageBox.critical(self, "Errore", f"Impossibile ripristinare:\n{e}")

    # ── eliminazione definitiva ──────────────────────────────────────────────

    def _elimina_definitivamente(self):
        elimina_fn = {
            "comuni":     self.db_manager.elimina_definitivamente_comune,
            "possessori": self.db_manager.elimina_definitivamente_possessore,
            "localita":   self.db_manager.elimina_definitivamente_localita,
            "partite":    self.db_manager.elimina_definitivamente_partita,
        }
        entity_label = {
            "comuni": "comune", "possessori": "possessore",
            "localita": "località", "partite": "partita",
        }

        table, model = self._current_table_and_model()
        sel_rows = table.selectionModel().selectedRows()
        if not sel_rows:
            return
        row = sel_rows[0].row()
        record_id = model.record_id_at(row)
        if record_id is None:
            return
        values = model.row_values(row)
        nome = str(values[1]) if len(values) > 1 else str(record_id)
        label = entity_label[self._current_entity]

        risposta = QMessageBox.warning(
            self, "Eliminazione DEFINITIVA",
            f"ATTENZIONE: Eliminare DEFINITIVAMENTE {label} '{nome}'?\n\n"
            "Questa operazione NON può essere annullata.\n"
            "Tutti i dati correlati (immobili, variazioni, etc.) potrebbero "
            "essere eliminati o causare errori se referenziati.\n\n"
            "Sei sicuro di voler procedere?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if risposta != QMessageBox.StandardButton.Yes:
            return

        try:
            elimina_fn[self._current_entity](record_id)
            self.load_data()
            QMessageBox.information(
                self, "Eliminato",
                f"Il {label} '{nome}' è stato eliminato definitivamente."
            )
        except Exception as e:
            msg = str(e).strip()
            QMessageBox.critical(
                self, "Errore Eliminazione",
                msg if msg else
                f"Impossibile eliminare il {label}. "
                "Potrebbero esserci elementi correlati che lo referenziano."
            )




