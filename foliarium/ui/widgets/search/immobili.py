"""
immobili.py — Ricerca avanzata immobili con filtri (model + widget).

Estratto da search_widgets.py (Sprint 3 refactor — six-hats).
Le classi sono anche re-esportate da search_widgets per preservare la
backward compatibility con i consumer esistenti.
"""
from __future__ import annotations

import logging
from typing import Optional, TYPE_CHECKING

from PyQt6.QtCore import (
    QAbstractTableModel, QModelIndex, QPoint, Qt,
)
from PyQt6.QtWidgets import (
    QAbstractItemView, QApplication, QDialog, QGridLayout, QGroupBox,
    QHBoxLayout, QHeaderView, QLabel, QLineEdit, QMenu, QMessageBox,
    QPushButton, QSpinBox, QStyle, QTableView, QVBoxLayout, QWidget,
)

from app_utils import format_indirizzo
from foliarium.ui.widgets.custom import show_status_message as _show_status_message
from dialogs import (
    ComuneSelectionDialog, LocalitaSelectionDialog,
)

try:
    from catasto_db_manager import DBMError
except ImportError:
    class DBMError(Exception):
        pass

if TYPE_CHECKING:
    from catasto_db_manager import CatastoDBManager  # noqa: F401

logger = logging.getLogger("CatastoGUI.search.immobili")

_IMMOBILI_COLS = ["ID Imm.", "Part. N.", "Comune", "Località", "Natura",
                  "Class.", "Consist.", "Piani", "Vani", "Possessori"]


class ImmobiliSearchModel(QAbstractTableModel):
    """Modello per la tabella di RicercaAvanzataImmobiliWidget.

    Ogni riga è un dict restituito da ricerca_avanzata_immobili_gui().
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._data: list[dict] = []

    def load(self, rows: list[dict]) -> None:
        self.beginResetModel()
        self._data = rows
        self.endResetModel()

    def row_count(self) -> int:
        return len(self._data)

    def rowCount(self, parent=QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self._data)

    def columnCount(self, parent=QModelIndex()) -> int:
        return 0 if parent.isValid() else len(_IMMOBILI_COLS)

    def headerData(self, section: int, orientation, role=Qt.ItemDataRole.DisplayRole):
        if orientation == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.DisplayRole:
            return _IMMOBILI_COLS[section]
        return None

    def data(self, index: QModelIndex, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None
        row, col = index.row(), index.column()
        imm = self._data[row]

        if role == Qt.ItemDataRole.DisplayRole:
            if col == 0:
                return str(imm.get('id_immobile', ''))
            if col == 1:
                return str(imm.get('numero_partita', ''))
            if col == 2:
                return imm.get('comune_nome', '')
            if col == 3:
                return format_indirizzo(
                    imm.get('localita_tipo') or imm.get('tipologia_stradale'),
                    imm.get('localita_nome'),
                    imm.get('numero_civico'),
                )
            if col == 4:
                return imm.get('natura', '')
            if col == 5:
                return imm.get('classificazione', '')
            if col == 6:
                return imm.get('consistenza', '')
            if col == 7:
                v = imm.get('numero_piani')
                return str(v) if v is not None else ''
            if col == 8:
                v = imm.get('numero_vani')
                return str(v) if v is not None else ''
            if col == 9:
                return imm.get('possessori_attuali', '')

        if role == Qt.ItemDataRole.EditRole:
            if col == 0:
                return imm.get('id_immobile', 0)
            if col == 1:
                return imm.get('numero_partita', 0)
            if col in (7, 8):
                return imm.get('numero_piani' if col == 7 else 'numero_vani', 0) or 0
            return self.data(index, Qt.ItemDataRole.DisplayRole)

        return None

    def flags(self, index: QModelIndex):
        if not index.isValid():
            return Qt.ItemFlag.NoItemFlags
        return Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable

    def sort(self, column: int, order=Qt.SortOrder.AscendingOrder) -> None:
        reverse = (order == Qt.SortOrder.DescendingOrder)
        keys = {
            0: 'id_immobile', 1: 'numero_partita', 2: 'comune_nome',
            3: 'localita_nome', 4: 'natura', 5: 'classificazione',
            6: 'consistenza', 7: 'numero_piani', 8: 'numero_vani',
            9: 'possessori_attuali',
        }
        key = keys.get(column, 'id_immobile')
        self.layoutAboutToBeChanged.emit()
        self._data.sort(
            key=lambda r: (r.get(key) is None, str(r.get(key) or '')),
            reverse=reverse,
        )
        self.layoutChanged.emit()

    def row_data(self, row: int) -> dict:
        return self._data[row] if 0 <= row < len(self._data) else {}


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
        self._imm_model = ImmobiliSearchModel(self)
        self.risultati_immobili_table = QTableView()
        self.risultati_immobili_table.setModel(self._imm_model)
        self.risultati_immobili_table.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers)
        self.risultati_immobili_table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows)
        self.risultati_immobili_table.setAlternatingRowColors(True)
        self.risultati_immobili_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Interactive)
        self.risultati_immobili_table.horizontalHeader().setStretchLastSection(True)
        self.risultati_immobili_table.setSortingEnabled(True)
        self.risultati_immobili_table.verticalHeader().setVisible(False)
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

            self._imm_model.load(immobili_trovati or [])
            n = self._imm_model.row_count()
            if n:
                self.result_count_label.setText(f"{n} immobili trovati.")
                _show_status_message(f"Ricerca completata: {n} immobili trovati.", 4000)
            else:
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
        imm = self._imm_model.row_data(index.row())
        if not imm:
            return
        id_imm = str(imm.get('id_immobile', ''))
        numero = str(imm.get('numero_partita', ''))
        comune = imm.get('comune_nome', '')
        natura = imm.get('natura', '')
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

