"""
registrazione_proprieta.py — Widget per la registrazione iniziale di una proprieta'.

Estratto da partita_workflow_widgets.py (Sprint 3 refactor — six-hats).
La classe e' anche re-esportata da partita_workflow_widgets per
preservare la backward compatibility con i consumer esistenti.
"""
from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from PyQt6.QtCore import (
    QDate, Qt, pyqtSignal,
)
from PyQt6.QtWidgets import (
    QAbstractItemView, QComboBox, QCompleter, QDateEdit, QDialog,
    QFormLayout, QFrame, QGridLayout, QGroupBox, QHBoxLayout, QLabel,
    QLineEdit, QMessageBox, QPushButton, QSpinBox, QStackedWidget, QTabWidget,
    QTableWidget, QTableWidgetItem, QTextBrowser, QVBoxLayout, QWidget,
)

from app_utils import (
    format_indirizzo,
)
from foliarium.ui.widgets.custom import (
    LazyLoadedWidget,
)
from dialogs import (
    ComuneSelectionDialog, CreatePossessoreDialog, DettagliLegamePossessoreDialog,
)

try:
    from catasto_db_manager import (
        DBMError, DBUniqueConstraintError, DBDataError,
    )
except ImportError:
    class DBMError(Exception):
        pass

if TYPE_CHECKING:
    from catasto_db_manager import CatastoDBManager  # noqa: F401

logger = logging.getLogger("CatastoGUI.registrazione_proprieta")


class RegistrazioneProprietaWidget(LazyLoadedWidget):
    """Wizard 4-step per la registrazione atomica di una nuova proprietà
    (partita + possessori + immobili in un'unica transazione SQL)."""

    partita_creata_per_operazioni_collegate = pyqtSignal(int, int)

    def __init__(self, db_manager: 'CatastoDBManager', parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self._step = 0
        self._comune_id: Optional[int] = None
        self._comune_nome: str = ""
        self._possessori_data: List[Dict[str, Any]] = []
        self._immobili_data: List[Dict[str, Any]] = []
        self._localita_cache: List[Dict[str, Any]] = []
        self._possessori_cache: List[Dict[str, Any]] = []
        self._immobili_cache: List[Dict[str, Any]] = []
        self._build_ui()

    # ── UI BUILD ─────────────────────────────────────────────────────────────

    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        step_bar = QFrame()
        step_bar.setObjectName("wizardStepBar")
        step_bar.setFixedHeight(56)
        step_layout = QHBoxLayout(step_bar)
        step_layout.setContentsMargins(32, 0, 32, 0)
        step_layout.setSpacing(12)

        self._step_labels: list = []
        for i, name in enumerate(["Dati Partita", "Possessori", "Immobili", "Riepilogo"]):
            lbl = QLabel(f"{i + 1}. {name}")
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._step_labels.append(lbl)
            step_layout.addWidget(lbl)
        step_layout.addStretch()
        main_layout.addWidget(step_bar)

        self._stack = QStackedWidget()
        self._stack.addWidget(self._build_step1())
        self._stack.addWidget(self._build_step2())
        self._stack.addWidget(self._build_step3())
        self._stack.addWidget(self._build_step4())
        main_layout.addWidget(self._stack, 1)

        nav_bar = QFrame()
        nav_layout = QHBoxLayout(nav_bar)
        nav_layout.setContentsMargins(20, 12, 20, 12)
        nav_layout.setSpacing(8)

        self._btn_back = QPushButton("← Indietro")
        self._btn_back.setObjectName("secondaryButton")
        self._btn_back.setEnabled(False)
        self._btn_back.clicked.connect(self._go_back)
        nav_layout.addWidget(self._btn_back)
        nav_layout.addStretch()

        self._btn_reset = QPushButton("Ricomincia")
        self._btn_reset.setObjectName("secondaryButton")
        self._btn_reset.clicked.connect(self._reset_wizard)
        nav_layout.addWidget(self._btn_reset)

        self._btn_next = QPushButton("Avanti →")
        self._btn_next.clicked.connect(self._go_next)
        nav_layout.addWidget(self._btn_next)

        main_layout.addWidget(nav_bar)
        self._update_nav()

    def _build_step1(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(32, 24, 32, 24)
        layout.setSpacing(12)

        title = QLabel("Dati della Partita")
        title.setObjectName("wizardStepTitle")
        layout.addWidget(title)

        form_group = QGroupBox("Informazioni Generali")
        form_layout = QFormLayout(form_group)
        form_layout.setSpacing(10)

        self._s1_comune_label = QLabel("Nessun comune selezionato")
        self._s1_comune_label.setProperty("muted", "true"); self._s1_comune_label.style().unpolish(self._s1_comune_label); self._s1_comune_label.style().polish(self._s1_comune_label)
        comune_btn = QPushButton("Seleziona...")
        comune_btn.setObjectName("secondaryButton")
        comune_btn.clicked.connect(self._s1_select_comune)
        comune_row = QHBoxLayout()
        comune_row.addWidget(self._s1_comune_label, 1)
        comune_row.addWidget(comune_btn)
        form_layout.addRow("Comune: *", comune_row)

        self._s1_numero = QSpinBox()
        self._s1_numero.setMinimum(1)
        self._s1_numero.setMaximum(99999)
        form_layout.addRow("Numero Partita: *", self._s1_numero)

        self._s1_suffisso = QLineEdit()
        self._s1_suffisso.setPlaceholderText("Es. A, B, bis (opzionale)")
        form_layout.addRow("Suffisso:", self._s1_suffisso)

        self._s1_data_imp = QDateEdit()
        self._s1_data_imp.setCalendarPopup(True)
        self._s1_data_imp.setDate(QDate.currentDate())
        self._s1_data_imp.setDisplayFormat("dd/MM/yyyy")
        form_layout.addRow("Data Impianto: *", self._s1_data_imp)

        layout.addWidget(form_group)
        layout.addStretch()
        return w

    def _build_step2(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(32, 24, 32, 24)
        layout.setSpacing(12)

        title = QLabel("Possessori")
        title.setObjectName("wizardStepTitle")
        layout.addWidget(title)

        self._s2_poss_table = QTableWidget()
        self._s2_poss_table.setColumnCount(4)
        self._s2_poss_table.setHorizontalHeaderLabels(["ID", "Nome Completo", "Titolo", "Quota"])
        self._s2_poss_table.horizontalHeader().setStretchLastSection(True)
        self._s2_poss_table.setMinimumHeight(140)
        self._s2_poss_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._s2_poss_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        layout.addWidget(self._s2_poss_table)

        btn_rem_row = QHBoxLayout()
        btn_rem_row.addStretch()
        btn_rem_poss = QPushButton("Rimuovi Selezionato")
        btn_rem_poss.setObjectName("secondaryButton")
        btn_rem_poss.clicked.connect(self._s2_remove_possessore)
        btn_rem_row.addWidget(btn_rem_poss)
        layout.addLayout(btn_rem_row)

        add_group = QGroupBox("Aggiungi Possessore")
        add_layout = QGridLayout(add_group)

        self._s2_search_combo = QComboBox()
        self._s2_search_combo.setEditable(True)
        self._s2_search_combo.setPlaceholderText("Cerca possessore esistente...")
        self._s2_search_combo.completer().setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        self._s2_search_combo.completer().setFilterMode(Qt.MatchFlag.MatchContains)
        add_layout.addWidget(QLabel("Cerca:"), 0, 0)
        add_layout.addWidget(self._s2_search_combo, 0, 1)

        btn_add_sel = QPushButton("Aggiungi Selezionato")
        btn_add_sel.clicked.connect(self._s2_add_selected)
        add_layout.addWidget(btn_add_sel, 0, 2)

        btn_create = QPushButton("Crea Nuovo...")
        btn_create.setObjectName("secondaryButton")
        btn_create.clicked.connect(self._s2_create_and_add)
        add_layout.addWidget(btn_create, 0, 3)

        layout.addWidget(add_group)
        layout.addStretch()
        return w

    def _build_step3(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(32, 24, 32, 24)
        layout.setSpacing(12)

        title = QLabel("Immobili")
        title.setObjectName("wizardStepTitle")
        layout.addWidget(title)

        self._s3_imm_table = QTableWidget()
        self._s3_imm_table.setColumnCount(5)
        self._s3_imm_table.setHorizontalHeaderLabels(["Natura", "Località", "Classificazione", "Consistenza", "Piani/Vani"])
        self._s3_imm_table.horizontalHeader().setStretchLastSection(True)
        self._s3_imm_table.setMinimumHeight(140)
        self._s3_imm_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._s3_imm_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        layout.addWidget(self._s3_imm_table)

        btn_rem_row = QHBoxLayout()
        btn_rem_row.addStretch()
        btn_rem_imm = QPushButton("Rimuovi Selezionato")
        btn_rem_imm.setObjectName("secondaryButton")
        btn_rem_imm.clicked.connect(self._s3_remove_immobile)
        btn_rem_row.addWidget(btn_rem_imm)
        layout.addLayout(btn_rem_row)

        add_tabs = QTabWidget()

        tab_exist = QWidget()
        exist_layout = QGridLayout(tab_exist)
        self._s3_exist_combo = QComboBox()
        self._s3_exist_combo.setEditable(True)
        self._s3_exist_combo.setPlaceholderText("Seleziona prima un comune nel passo 1...")
        self._s3_exist_combo.setEnabled(False)
        self._s3_exist_combo.completer().setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        self._s3_exist_combo.completer().setFilterMode(Qt.MatchFlag.MatchContains)
        btn_add_exist = QPushButton("Aggiungi")
        btn_add_exist.clicked.connect(self._s3_add_existing)
        exist_layout.addWidget(QLabel("Immobile:"), 0, 0)
        exist_layout.addWidget(self._s3_exist_combo, 0, 1)
        exist_layout.addWidget(btn_add_exist, 0, 2)
        add_tabs.addTab(tab_exist, "Aggiungi Esistente")

        tab_new = QWidget()
        new_layout = QGridLayout(tab_new)
        self._s3_natura_edit = QLineEdit()
        new_layout.addWidget(QLabel("Natura (*):"), 0, 0)
        new_layout.addWidget(self._s3_natura_edit, 0, 1)

        self._s3_localita_combo = QComboBox()
        self._s3_localita_combo.setPlaceholderText("Seleziona prima un comune...")
        self._s3_localita_combo.setEnabled(False)
        new_layout.addWidget(QLabel("Località (*):"), 0, 2)
        new_layout.addWidget(self._s3_localita_combo, 0, 3)

        self._s3_class_edit = QLineEdit()
        new_layout.addWidget(QLabel("Classificazione:"), 1, 0)
        new_layout.addWidget(self._s3_class_edit, 1, 1)

        self._s3_consist_edit = QLineEdit()
        new_layout.addWidget(QLabel("Consistenza:"), 1, 2)
        new_layout.addWidget(self._s3_consist_edit, 1, 3)

        self._s3_piani_spin = QSpinBox()
        self._s3_piani_spin.setRange(0, 99)
        new_layout.addWidget(QLabel("Piani:"), 2, 0)
        new_layout.addWidget(self._s3_piani_spin, 2, 1)

        self._s3_vani_spin = QSpinBox()
        self._s3_vani_spin.setRange(0, 99)
        new_layout.addWidget(QLabel("Vani:"), 2, 2)
        new_layout.addWidget(self._s3_vani_spin, 2, 3)

        self._s3_civico_edit = QLineEdit()
        self._s3_civico_edit.setPlaceholderText("Es. 17, 17/A, s.n.c.")
        new_layout.addWidget(QLabel("N. Civico:"), 3, 0)
        new_layout.addWidget(self._s3_civico_edit, 3, 1)

        btn_add_new = QPushButton("Aggiungi alla Lista")
        btn_add_new.clicked.connect(self._s3_add_inline)
        new_layout.addWidget(btn_add_new, 3, 3, Qt.AlignmentFlag.AlignRight)
        add_tabs.addTab(tab_new, "Crea Nuovo")

        layout.addWidget(add_tabs)
        layout.addStretch()
        return w

    def _build_step4(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(32, 24, 32, 24)
        layout.setSpacing(12)

        title = QLabel("Riepilogo e Conferma")
        title.setObjectName("wizardStepTitle")
        layout.addWidget(title)

        self._s4_browser = QTextBrowser()
        self._s4_browser.setOpenExternalLinks(False)
        layout.addWidget(self._s4_browser, 1)
        return w

    # ── NAVIGATION ───────────────────────────────────────────────────────────

    def _update_nav(self):
        total = self._stack.count()
        self._btn_back.setEnabled(self._step > 0)
        self._btn_next.setText("Registra Proprietà" if self._step == total - 1 else "Avanti →")
        self._update_step_bar()

    def _update_step_bar(self):
        for i, lbl in enumerate(self._step_labels):
            if i == self._step:
                state = "current"
            elif i < self._step:
                state = "done"
            else:
                state = "pending"
            lbl.setProperty("stepState", state)
            lbl.style().unpolish(lbl)
            lbl.style().polish(lbl)

    def _go_next(self):
        if self._step == self._stack.count() - 1:
            self._registra_tutto()
            return
        if not self._validate_step(self._step):
            return
        if self._step == 0:
            self._load_comune_dependent_data()
        if self._step == self._stack.count() - 2:
            self._render_riepilogo()
        self._step += 1
        self._stack.setCurrentIndex(self._step)
        self._update_nav()

    def _go_back(self):
        if self._step > 0:
            self._step -= 1
            self._stack.setCurrentIndex(self._step)
            self._update_nav()

    def _validate_step(self, step: int) -> bool:
        if step == 0:
            if not self._comune_id:
                QMessageBox.warning(self, "Dati Mancanti", "Selezionare un comune.")
                return False
        elif step == 1:
            if not self._possessori_data:
                QMessageBox.warning(self, "Dati Mancanti", "Aggiungere almeno un possessore.")
                return False
        elif step == 2:
            if not self._immobili_data:
                QMessageBox.warning(self, "Dati Mancanti", "Aggiungere almeno un immobile.")
                return False
        return True

    def _reset_wizard(self):
        self._step = 0
        self._comune_id = None
        self._comune_nome = ""
        self._possessori_data = []
        self._immobili_data = []
        self._localita_cache = []
        self._possessori_cache = []
        self._immobili_cache = []
        self._s1_comune_label.setText("Nessun comune selezionato")
        self._s1_comune_label.setProperty("muted", "true"); self._s1_comune_label.style().unpolish(self._s1_comune_label); self._s1_comune_label.style().polish(self._s1_comune_label)
        self._s1_numero.setValue(1)
        self._s1_suffisso.clear()
        self._s1_data_imp.setDate(QDate.currentDate())
        self._s2_poss_table.setRowCount(0)
        self._s2_search_combo.clear()
        self._s3_imm_table.setRowCount(0)
        self._s3_exist_combo.clear()
        self._s3_exist_combo.setEnabled(False)
        self._s3_localita_combo.clear()
        self._s3_localita_combo.setEnabled(False)
        self._s3_natura_edit.clear()
        self._s3_class_edit.clear()
        self._s3_consist_edit.clear()
        self._s3_piani_spin.setValue(0)
        self._s3_vani_spin.setValue(0)
        self._s3_civico_edit.clear()
        self._s4_browser.clear()
        self._stack.setCurrentIndex(0)
        self._update_nav()

    # ── STEP 1 ───────────────────────────────────────────────────────────────

    def _s1_select_comune(self):
        dialog = ComuneSelectionDialog(self.db_manager, self)
        if dialog.exec() == QDialog.DialogCode.Accepted and dialog.selected_comune_id:
            self._comune_id = dialog.selected_comune_id
            self._comune_nome = dialog.selected_comune_name
            self._s1_comune_label.setText(self._comune_nome)
            self._s1_comune_label.setProperty("muted", "false"); self._s1_comune_label.style().unpolish(self._s1_comune_label); self._s1_comune_label.style().polish(self._s1_comune_label)

    def _load_comune_dependent_data(self):
        self._load_possessori_cache()
        self._load_localita_cache()
        self._load_immobili_cache()

    # ── DATA LOADING ─────────────────────────────────────────────────────────

    def _load_data_on_first_show(self):
        self._load_possessori_cache()

    def _load_possessori_cache(self):
        self._s2_search_combo.clear()
        self._s2_search_combo.addItem("--- Cerca o Seleziona ---", None)
        try:
            self._possessori_cache = self.db_manager.search_possessori_by_term_globally(None, limit=5000)
            for p in self._possessori_cache:
                self._s2_search_combo.addItem(
                    f"{p['nome_completo']} ({p['comune_riferimento_nome']})", p['id'])
        except Exception as e:
            self.logger.error(f"Errore caricamento possessori: {e}")

    def _load_localita_cache(self):
        self._s3_localita_combo.clear()
        self._s3_localita_combo.setEnabled(False)
        if not self._comune_id:
            return
        try:
            self._localita_cache = self.db_manager.get_localita_by_comune(self._comune_id)
            if self._localita_cache:
                self._s3_localita_combo.addItem("--- Seleziona Località ---", None)
                for loc in self._localita_cache:
                    self._s3_localita_combo.addItem(
                        f"{loc['nome']} ({loc.get('tipo', 'N/D')})", loc['id'])
                self._s3_localita_combo.setEnabled(True)
            else:
                self._s3_localita_combo.addItem("Nessuna località per questo comune", None)
        except Exception as e:
            self.logger.error(f"Errore caricamento località: {e}")

    def _load_immobili_cache(self):
        self._s3_exist_combo.clear()
        self._s3_exist_combo.setEnabled(False)
        if not self._comune_id:
            return
        try:
            self._immobili_cache = self.db_manager.get_immobili_by_comune(self._comune_id)
            if self._immobili_cache:
                self._s3_exist_combo.addItem("--- Cerca Immobile ---", None)
                for imm in self._immobili_cache:
                    loc = format_indirizzo(
                        imm.get('tipologia_stradale') or imm.get('localita_tipo'),
                        imm.get('localita_nome'),
                        imm.get('numero_civico'),
                    )
                    self._s3_exist_combo.addItem(f"{imm['natura']} — {loc}", imm['id'])
                self._s3_exist_combo.setEnabled(True)
            else:
                self._s3_exist_combo.addItem("Nessun immobile in questo comune", None)
        except Exception as e:
            self.logger.error(f"Errore caricamento immobili: {e}")

    # ── STEP 2: POSSESSORI ───────────────────────────────────────────────────

    def _s2_add_selected(self):
        possessore_id = self._s2_search_combo.currentData()
        if not possessore_id:
            QMessageBox.warning(self, "Selezione Mancante", "Seleziona un possessore dalla lista.")
            return
        if any(p['id'] == possessore_id for p in self._possessori_data):
            QMessageBox.information(self, "Già Presente", "Questo possessore è già nella lista.")
            return
        dettagli = DettagliLegamePossessoreDialog.get_details_for_new_legame(
            self._s2_search_combo.currentText(), 'principale', self)
        if dettagli:
            self._possessori_data.append({
                "id": possessore_id,
                "nome_completo": self._s2_search_combo.currentText(),
                **dettagli,
            })
            self._refresh_poss_table()

    def _s2_create_and_add(self):
        dialog = CreatePossessoreDialog(self.db_manager, self)
        if dialog.exec() == QDialog.DialogCode.Accepted and dialog.nuovo_possessore_dati:
            info = dialog.nuovo_possessore_dati
            self._load_possessori_cache()
            dettagli = DettagliLegamePossessoreDialog.get_details_for_new_legame(
                info.get('nome_completo'), 'principale', self)
            if dettagli:
                self._possessori_data.append({
                    "id": info['id'],
                    "nome_completo": info['nome_completo'],
                    **dettagli,
                })
                self._refresh_poss_table()

    def _s2_remove_possessore(self):
        rows = self._s2_poss_table.selectedIndexes()
        if not rows:
            QMessageBox.warning(self, "Attenzione", "Seleziona un possessore da rimuovere.")
            return
        row = rows[0].row()
        if 0 <= row < len(self._possessori_data):
            del self._possessori_data[row]
            self._refresh_poss_table()

    def _refresh_poss_table(self):
        self._s2_poss_table.setRowCount(len(self._possessori_data))
        for i, d in enumerate(self._possessori_data):
            self._s2_poss_table.setItem(i, 0, QTableWidgetItem(str(d.get('id', ''))))
            self._s2_poss_table.setItem(i, 1, QTableWidgetItem(d.get('nome_completo', '')))
            self._s2_poss_table.setItem(i, 2, QTableWidgetItem(d.get('titolo', '')))
            self._s2_poss_table.setItem(i, 3, QTableWidgetItem(d.get('quota', '')))

    # ── STEP 3: IMMOBILI ─────────────────────────────────────────────────────

    def _s3_add_existing(self):
        imm_id = self._s3_exist_combo.currentData()
        if not imm_id:
            QMessageBox.warning(self, "Selezione Mancante", "Seleziona un immobile dalla lista.")
            return
        if any(i.get('id') == imm_id for i in self._immobili_data):
            QMessageBox.information(self, "Già Presente", "Questo immobile è già nella lista.")
            return
        details = next((i for i in self._immobili_cache if i['id'] == imm_id), None)
        if details:
            self._immobili_data.append(details)
            self._refresh_imm_table()

    def _s3_add_inline(self):
        natura = self._s3_natura_edit.text().strip()
        localita_id = self._s3_localita_combo.currentData()
        if not natura or localita_id is None:
            QMessageBox.warning(self, "Dati Mancanti", "Natura e Località sono obbligatori.")
            return
        self._immobili_data.append({
            'natura': natura,
            'localita_id': localita_id,
            'localita_nome': self._s3_localita_combo.currentText(),
            'classificazione': self._s3_class_edit.text().strip(),
            'consistenza': self._s3_consist_edit.text().strip(),
            'numero_piani': self._s3_piani_spin.value(),
            'numero_vani': self._s3_vani_spin.value(),
            'numero_civico': self._s3_civico_edit.text().strip() or None,
        })
        self._refresh_imm_table()
        self._s3_natura_edit.clear()
        self._s3_class_edit.clear()
        self._s3_consist_edit.clear()
        self._s3_piani_spin.setValue(0)
        self._s3_vani_spin.setValue(0)
        self._s3_civico_edit.clear()
        self._s3_localita_combo.setCurrentIndex(0)

    def _s3_remove_immobile(self):
        rows = self._s3_imm_table.selectedIndexes()
        if not rows:
            QMessageBox.warning(self, "Attenzione", "Seleziona un immobile da rimuovere.")
            return
        row = rows[0].row()
        if 0 <= row < len(self._immobili_data):
            del self._immobili_data[row]
            self._refresh_imm_table()

    def _refresh_imm_table(self):
        self._s3_imm_table.setRowCount(len(self._immobili_data))
        for i, imm in enumerate(self._immobili_data):
            piani_vani_parts = []
            if imm.get('numero_piani'):
                piani_vani_parts.append(f"Piani: {imm['numero_piani']}")
            if imm.get('numero_vani'):
                piani_vani_parts.append(f"Vani: {imm['numero_vani']}")
            self._s3_imm_table.setItem(i, 0, QTableWidgetItem(imm.get('natura', '')))
            self._s3_imm_table.setItem(i, 1, QTableWidgetItem(format_indirizzo(
                imm.get('tipologia_stradale') or imm.get('localita_tipo'),
                imm.get('localita_nome'),
                imm.get('numero_civico'),
            )))
            self._s3_imm_table.setItem(i, 2, QTableWidgetItem(imm.get('classificazione', '')))
            self._s3_imm_table.setItem(i, 3, QTableWidgetItem(imm.get('consistenza', '')))
            self._s3_imm_table.setItem(i, 4, QTableWidgetItem(", ".join(piani_vani_parts)))

    # ── STEP 4: RIEPILOGO ────────────────────────────────────────────────────

    def _render_riepilogo(self):
        data_imp = self._s1_data_imp.date().toString("dd/MM/yyyy")
        suf = self._s1_suffisso.text().strip()
        suf_disp = f"/{suf}" if suf else ""

        poss_rows = "".join(
            f"<tr><td>{p['nome_completo']}</td><td>{p.get('titolo', '')}</td><td>{p.get('quota', '')}</td></tr>"
            for p in self._possessori_data
        )
        imm_rows = "".join(
            f"<tr><td>{i.get('natura', '')}</td>"
            f"<td>{format_indirizzo(i.get('tipologia_stradale') or i.get('localita_tipo'), i.get('localita_nome'), i.get('numero_civico'))}</td>"
            f"<td>{i.get('classificazione', '')}</td><td>{i.get('consistenza', '')}</td></tr>"
            for i in self._immobili_data
        )

        self._s4_browser.setHtml(f"""
<h3>Partita</h3>
<table border="1" cellpadding="4" cellspacing="0" width="100%">
  <tr><td><b>Comune</b></td><td>{self._comune_nome}</td></tr>
  <tr><td><b>Numero</b></td><td>{self._s1_numero.value()}{suf_disp}</td></tr>
  <tr><td><b>Data Impianto</b></td><td>{data_imp}</td></tr>
</table>
<h3>Possessori ({len(self._possessori_data)})</h3>
<table border="1" cellpadding="4" cellspacing="0" width="100%">
  <tr><th>Nome</th><th>Titolo</th><th>Quota</th></tr>
  {poss_rows}
</table>
<h3>Immobili ({len(self._immobili_data)})</h3>
<table border="1" cellpadding="4" cellspacing="0" width="100%">
  <tr><th>Natura</th><th>Località</th><th>Classificazione</th><th>Consistenza</th></tr>
  {imm_rows}
</table>
""")

    # ── REGISTRAZIONE ────────────────────────────────────────────────────────

    def _registra_tutto(self):
        if not self._comune_id or not self._possessori_data or not self._immobili_data:
            QMessageBox.warning(self, "Dati Incompleti", "Verificare comune, possessori e immobili.")
            return

        numero_partita = self._s1_numero.value()
        suffisso = self._s1_suffisso.text().strip() or None
        data_impianto = self._s1_data_imp.date().toPyDate()

        try:
            possessori_json = json.dumps(self._possessori_data)
            immobili_json = json.dumps(self._immobili_data)
        except TypeError as e:
            QMessageBox.critical(self, "Errore Dati", f"Errore serializzazione JSON: {e}")
            return

        try:
            nuova_partita_id = self.db_manager.registra_nuova_proprieta(
                comune_id=self._comune_id,
                numero_partita=numero_partita,
                data_impianto=data_impianto,
                possessori_json_str=possessori_json,
                immobili_json_str=immobili_json,
                suffisso_partita=suffisso,
            )
        except (DBUniqueConstraintError, DBDataError, DBMError) as e:
            self.logger.error(f"Errore DB registrazione proprietà: {e}")
            QMessageBox.critical(self, "Errore Database", str(e))
            return
        except Exception as e:
            self.logger.error(f"Errore imprevisto registrazione proprietà: {e}", exc_info=True)
            QMessageBox.critical(self, "Errore Imprevisto", str(e))
            return

        suf_disp = f" ({suffisso})" if suffisso else ""
        msg = (f"Proprietà registrata con successo.\n"
               f"Partita N.{numero_partita}{suf_disp} — ID: {nuova_partita_id}")
        reply = QMessageBox.question(
            self, "Registrazione Completata",
            f"{msg}\n\nProcedere con operazioni collegate?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.partita_creata_per_operazioni_collegate.emit(nuova_partita_id, self._comune_id)

        self._reset_wizard()


