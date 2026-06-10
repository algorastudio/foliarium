"""
nuova_partita_wizard.py — Wizard a 4 step per la creazione guidata di una nuova partita.

Estratto da partita_workflow_widgets.py (Sprint 3 refactor — six-hats).
La classe e' anche re-esportata da partita_workflow_widgets per
preservare la backward compatibility con i consumer esistenti.

Sprint 4 — Salvataggio in bozza:
  - Persistenza su DB (catasto.partita_draft) dello stato wizard come JSONB
  - Pulsanti "Salva bozza" e "Riprendi bozza..." nella nav-bar
  - Autosave ogni 60s una volta che lo stato è "sporco" (dirty)
  - Eliminazione automatica della bozza dopo registrazione riuscita
"""
from __future__ import annotations

import logging
from datetime import date, datetime
from typing import Any, Dict, Optional

from PyQt6.QtCore import (
    QDate, Qt, QTimer,
)
from PyQt6.QtWidgets import (
    QComboBox, QDateEdit, QDialog, QFormLayout, QFrame,
    QGroupBox, QHBoxLayout, QHeaderView, QInputDialog, QLabel, QLineEdit,
    QListWidget, QListWidgetItem, QMessageBox, QPushButton, QSpinBox,
    QStackedWidget, QTableWidget, QTableWidgetItem, QTextBrowser, QVBoxLayout,
    QWidget,
)

from foliarium.ui.widgets.custom import (
    show_status_message as _show_status_message,
)
from dialogs import (
    ComuneSelectionDialog, CreateLocalitaDialog, CreatePossessoreDialog,
)
from foliarium.ui.dialogs.partita.bozze import BozzePartitaDialog

try:
    from catasto_db_manager import (
        DBMError,
    )
except ImportError:
    class DBMError(Exception):
        pass

try:
    from db.drafts import WIZARD_KIND_NUOVA_PARTITA
except Exception:
    WIZARD_KIND_NUOVA_PARTITA = "nuova_partita_wizard"

try:
    from config import APP_VERSION as _APP_VERSION
except Exception:
    _APP_VERSION = None


logger = logging.getLogger("CatastoGUI.nuova_partita_wizard")

# Intervallo autosave in millisecondi (60s).
AUTOSAVE_INTERVAL_MS = 60_000


class NuovaPartitaWizardWidget(QWidget):
    """Wizard a 4 step per la creazione guidata di una nuova partita.

    Supporta il salvataggio in bozza (manuale e autosave) tramite
    serializzazione dello stato in JSONB nella tabella
    ``catasto.partita_draft``.
    """

    def __init__(self, db_manager, utente_info=None, parent=None,
                 utente_id: Optional[int] = None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.utente_info = utente_info or {}
        # utente_id viene passato esplicitamente da gui_main.py; per
        # backward compat con costruzioni manuali, tentiamo il fallback
        # da utente_info se non fornito.
        self.utente_id: Optional[int] = (
            utente_id if utente_id is not None
            else self.utente_info.get("id") if isinstance(self.utente_info, dict)
            else None
        )
        self._step = 0
        self._comune_id: Optional[int] = None
        self._comune_nome: str = ""

        # Stato bozza
        self._current_draft_id: Optional[int] = None
        self._dirty: bool = False
        self._restoring: bool = False  # disattiva dirty-tracking durante restore

        self._build_ui()

        # Autosave timer (60s, monoshot ripetitivo)
        self._autosave_timer = QTimer(self)
        self._autosave_timer.setInterval(AUTOSAVE_INTERVAL_MS)
        self._autosave_timer.timeout.connect(self._on_autosave_tick)
        self._autosave_timer.start()

    # ──────────────────────────────────────────────────────────────────
    # UI BUILD
    # ──────────────────────────────────────────────────────────────────

    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Step indicator
        step_bar = QFrame()
        step_bar.setObjectName("wizardStepBar")
        step_bar.setFixedHeight(56)
        step_layout = QHBoxLayout(step_bar)
        step_layout.setContentsMargins(32, 0, 32, 0)
        step_layout.setSpacing(12)

        self._step_widgets: list[QWidget] = []
        for i, label in enumerate(["Dati Partita", "Possessori", "Immobili", "Riepilogo"]):
            w = QLabel(f"{i+1}. {label}")
            w.setAlignment(Qt.AlignmentFlag.AlignCenter)
            step_layout.addWidget(w)

        step_layout.addStretch()

        self._draft_status_label = QLabel("")
        self._draft_status_label.setProperty("muted", "true")
        step_layout.addWidget(self._draft_status_label)

        main_layout.addWidget(step_bar)

        # Content area
        self._stack = QStackedWidget()
        self._stack.addWidget(self._build_step1())
        self._stack.addWidget(self._build_step2())
        self._stack.addWidget(self._build_step3())
        self._stack.addWidget(self._build_step4())
        main_layout.addWidget(self._stack, 1)

        # Navigation
        nav_bar = QFrame()
        nav_layout = QHBoxLayout(nav_bar)
        nav_layout.setContentsMargins(20, 12, 20, 12)
        nav_layout.setSpacing(8)

        self._btn_back = QPushButton("← Indietro")
        self._btn_back.setObjectName("secondaryButton")
        self._btn_back.setEnabled(False)
        self._btn_back.clicked.connect(self._go_back)
        nav_layout.addWidget(self._btn_back)

        self._btn_resume = QPushButton("Riprendi bozza...")
        self._btn_resume.setObjectName("secondaryButton")
        self._btn_resume.setToolTip("Apri l'elenco delle bozze salvate")
        self._btn_resume.clicked.connect(self._resume_draft)
        nav_layout.addWidget(self._btn_resume)

        self._btn_save_draft = QPushButton("Salva bozza")
        self._btn_save_draft.setObjectName("secondaryButton")
        self._btn_save_draft.setToolTip("Salva lo stato corrente come bozza riprendibile")
        self._btn_save_draft.clicked.connect(self._save_draft_clicked)
        nav_layout.addWidget(self._btn_save_draft)

        nav_layout.addStretch()

        self._btn_reset = QPushButton("Ricomincia")
        self._btn_reset.setObjectName("secondaryButton")
        self._btn_reset.clicked.connect(self._reset_wizard)
        nav_layout.addWidget(self._btn_reset)

        self._btn_next = QPushButton("Avanti →")
        self._btn_next.clicked.connect(self._go_next)
        nav_layout.addWidget(self._btn_next)

        main_layout.addWidget(nav_bar)

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
        self._s1_numero.setValue(1)
        self._s1_numero.valueChanged.connect(self._mark_dirty)
        form_layout.addRow("Numero Partita: *", self._s1_numero)

        self._s1_suffisso = QLineEdit()
        self._s1_suffisso.setPlaceholderText("Es. A, B, bis (opzionale)")
        self._s1_suffisso.textChanged.connect(self._mark_dirty)
        form_layout.addRow("Suffisso:", self._s1_suffisso)

        self._s1_data_imp = QDateEdit()
        self._s1_data_imp.setCalendarPopup(True)
        self._s1_data_imp.setDate(QDate.currentDate())
        self._s1_data_imp.setDisplayFormat("dd/MM/yyyy")
        self._s1_data_imp.dateChanged.connect(self._mark_dirty)
        form_layout.addRow("Data Impianto: *", self._s1_data_imp)

        self._s1_tipo = QComboBox()
        self._s1_tipo.addItems(["Principale", "Secondaria", "Enfiteusi", "Usufrutto"])
        self._s1_tipo.currentIndexChanged.connect(self._mark_dirty)
        form_layout.addRow("Tipo:", self._s1_tipo)

        self._s1_stato = QComboBox()
        self._s1_stato.addItems(["Attiva", "Inattiva"])
        self._s1_stato.currentIndexChanged.connect(self._mark_dirty)
        form_layout.addRow("Stato:", self._s1_stato)

        layout.addWidget(form_group)
        layout.addStretch()

        return w

    def _s1_select_comune(self):
        dialog = ComuneSelectionDialog(self.db_manager, self)
        if dialog.exec() == QDialog.DialogCode.Accepted and dialog.selected_comune_id:
            self._comune_id = dialog.selected_comune_id
            self._comune_nome = dialog.selected_comune_name
            self._s1_comune_label.setText(self._comune_nome)
            self._s1_comune_label.setProperty("muted", "false"); self._s1_comune_label.style().unpolish(self._s1_comune_label); self._s1_comune_label.style().polish(self._s1_comune_label)
            self._mark_dirty()

    def _build_step2(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(32, 24, 32, 24)
        layout.setSpacing(12)

        title = QLabel("Aggiungi Possessori (Opzionale)")
        title.setObjectName("wizardStepTitle")
        layout.addWidget(title)

        search_row = QHBoxLayout()
        self._s2_search = QLineEdit()
        self._s2_search.setPlaceholderText("Cerca possessore...")
        search_row.addWidget(self._s2_search, 1)

        search_btn = QPushButton("Cerca")
        search_btn.clicked.connect(self._s2_search_possessore)
        search_row.addWidget(search_btn)

        create_btn = QPushButton("Crea Nuovo...")
        create_btn.setObjectName("secondaryButton")
        create_btn.setToolTip("Crea un nuovo possessore e aggiungilo alla partita")
        create_btn.clicked.connect(self._s2_create_possessore)
        search_row.addWidget(create_btn)

        layout.addLayout(search_row)

        layout.addWidget(QLabel("Risultati:"))
        self._s2_results = QListWidget()
        self._s2_results.setMaximumHeight(140)
        self._s2_results.itemDoubleClicked.connect(self._s2_add_from_list)
        layout.addWidget(self._s2_results)

        layout.addWidget(QLabel("Selezionati:"))
        self._s2_table = QTableWidget()
        self._s2_table.setColumnCount(3)
        self._s2_table.setHorizontalHeaderLabels(["Nome", "Titolo", ""])
        self._s2_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self._s2_table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self._s2_table, 1)

        return w

    def _s2_search_possessore(self):
        testo = self._s2_search.text().strip()
        if not testo:
            return
        try:
            results = self.db_manager.search_possessori_by_term_globally(testo, limit=20)
            self._s2_results.clear()
            for p in (results or []):
                item = QListWidgetItem(f"{p.get('nome_completo','')} — {p.get('paternita','')}")
                item.setData(Qt.ItemDataRole.UserRole, p.get('id'))
                self._s2_results.addItem(item)
        except Exception as e:
            logging.getLogger("CatastoGUI").error(f"Errore ricerca possessori: {e}")

    def _s2_add_from_list(self, item: QListWidgetItem):
        poss_id = item.data(Qt.ItemDataRole.UserRole)
        if not poss_id:
            return
        self._s2_append_possessore(poss_id, item.text().split(" — ")[0])

    def _s2_append_possessore(self, poss_id: int, nome: str, titolo: str = "Proprietario"):
        """Aggiunge un possessore alla tabella dei selezionati (se non già presente)."""
        for r in range(self._s2_table.rowCount()):
            it = self._s2_table.item(r, 0)
            if it and it.data(Qt.ItemDataRole.UserRole) == poss_id:
                QMessageBox.information(self, "Già presente",
                                        "Questo possessore è già nella lista.")
                return

        row = self._s2_table.rowCount()
        self._s2_table.insertRow(row)
        nome_item = QTableWidgetItem(nome)
        nome_item.setData(Qt.ItemDataRole.UserRole, poss_id)
        self._s2_table.setItem(row, 0, nome_item)
        self._s2_table.setItem(row, 1, QTableWidgetItem(titolo))

        del_btn = QPushButton("✕")
        del_btn.clicked.connect(
            lambda: (self._remove_row(self._s2_table, del_btn), self._mark_dirty()))
        self._s2_table.setCellWidget(row, 2, del_btn)
        self._mark_dirty()

    @staticmethod
    def _remove_row(table: QTableWidget, btn: QPushButton):
        """Rimuove la riga che contiene il pulsante dato (indice sempre corretto
        anche dopo rimozioni precedenti)."""
        for r in range(table.rowCount()):
            if table.cellWidget(r, table.columnCount() - 1) is btn:
                table.removeRow(r)
                return

    def _s2_create_possessore(self):
        """Apre il dialog di creazione possessore e lo aggiunge alla partita."""
        dialog = CreatePossessoreDialog(self.db_manager, self)
        if dialog.exec() == QDialog.DialogCode.Accepted and dialog.nuovo_possessore_dati:
            info = dialog.nuovo_possessore_dati
            self._s2_append_possessore(info["id"], info.get("nome_completo", ""))

    def _build_step3(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(32, 24, 32, 24)
        layout.setSpacing(12)

        title = QLabel("Aggiungi Immobili (Opzionale)")
        title.setObjectName("wizardStepTitle")
        layout.addWidget(title)

        add_group = QGroupBox("Nuovo Immobile")
        add_layout = QFormLayout(add_group)

        self._s3_natura = QLineEdit()
        self._s3_natura.setPlaceholderText("Es. Casa, Terreno")
        add_layout.addRow("Natura: *", self._s3_natura)

        # La località è obbligatoria: immobile.localita_id è NOT NULL nel DB.
        self._s3_localita = QComboBox()
        self._s3_localita.setPlaceholderText("Seleziona prima un comune...")
        self._s3_new_localita_btn = QPushButton("+ Nuova...")
        self._s3_new_localita_btn.setObjectName("secondaryButton")
        self._s3_new_localita_btn.setToolTip("Crea una nuova località per il comune selezionato")
        self._s3_new_localita_btn.clicked.connect(self._s3_create_localita)
        loc_row = QHBoxLayout()
        loc_row.setContentsMargins(0, 0, 0, 0)
        loc_row.addWidget(self._s3_localita, 1)
        loc_row.addWidget(self._s3_new_localita_btn)
        add_layout.addRow("Località: *", loc_row)

        self._s3_classif = QLineEdit()
        self._s3_classif.setPlaceholderText("Es. A/1, A/2")
        add_layout.addRow("Classificazione:", self._s3_classif)

        add_btn = QPushButton("+ Aggiungi")
        add_btn.clicked.connect(self._s3_add_immobile)
        add_layout.addRow("", add_btn)

        layout.addWidget(add_group)

        layout.addWidget(QLabel("Immobili:"))
        self._s3_table = QTableWidget()
        self._s3_table.setColumnCount(4)
        self._s3_table.setHorizontalHeaderLabels(["Natura", "Località", "Classificazione", ""])
        self._s3_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self._s3_table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self._s3_table, 1)

        return w

    def _load_localita(self):
        """Popola la combo delle località per il comune selezionato."""
        self._s3_localita.clear()
        if not self._comune_id:
            self._s3_localita.setEnabled(False)
            self._s3_new_localita_btn.setEnabled(False)
            return
        self._s3_new_localita_btn.setEnabled(True)
        try:
            localita = self.db_manager.get_localita_by_comune(self._comune_id) or []
        except Exception as e:
            logging.getLogger("CatastoGUI").error(f"Errore caricamento località: {e}")
            localita = []
        if localita:
            self._s3_localita.addItem("--- Seleziona Località ---", None)
            for loc in localita:
                tipo = loc.get("tipologia_stradale") or "N/D"
                self._s3_localita.addItem(f"{loc['nome']} ({tipo})", loc["id"])
            self._s3_localita.setEnabled(True)
        else:
            self._s3_localita.addItem("Nessuna località — usa '+ Nuova...'", None)
            self._s3_localita.setEnabled(False)

    def _s3_create_localita(self):
        if not self._comune_id:
            QMessageBox.warning(self, "Comune mancante",
                                "Seleziona prima un comune al Passo 1.")
            return
        dlg = CreateLocalitaDialog(
            self.db_manager, self._comune_id, self._comune_nome, self)
        if dlg.exec() != QDialog.DialogCode.Accepted or not dlg.nuova_localita_id:
            return
        self._load_localita()
        idx = self._s3_localita.findData(dlg.nuova_localita_id)
        if idx >= 0:
            self._s3_localita.setCurrentIndex(idx)

    def _s3_add_immobile(self):
        natura = self._s3_natura.text().strip()
        if not natura:
            QMessageBox.warning(self, "Attenzione", "Natura obbligatoria.")
            return
        localita_id = self._s3_localita.currentData()
        if not localita_id:
            QMessageBox.warning(self, "Attenzione",
                                "Località obbligatoria. Selezionane una o creane una nuova.")
            return

        self._s3_append_immobile(
            natura=natura,
            localita_id=localita_id,
            localita_text=self._s3_localita.currentText(),
            classif=self._s3_classif.text().strip(),
        )

        self._s3_natura.clear()
        self._s3_classif.clear()

    def _s3_append_immobile(self, natura: str, localita_id: int,
                            localita_text: str, classif: str = ""):
        row = self._s3_table.rowCount()
        self._s3_table.insertRow(row)
        natura_item = QTableWidgetItem(natura)
        natura_item.setData(Qt.ItemDataRole.UserRole, localita_id)
        self._s3_table.setItem(row, 0, natura_item)
        self._s3_table.setItem(row, 1, QTableWidgetItem(localita_text))
        self._s3_table.setItem(row, 2, QTableWidgetItem(classif))

        del_btn = QPushButton("✕")
        del_btn.clicked.connect(
            lambda: (self._remove_row(self._s3_table, del_btn), self._mark_dirty()))
        self._s3_table.setCellWidget(row, 3, del_btn)
        self._mark_dirty()

    def _build_step4(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(32, 24, 32, 24)
        layout.setSpacing(12)

        title = QLabel("Riepilogo e Conferma")
        title.setObjectName("wizardStepTitle")
        layout.addWidget(title)

        self._s4_browser = QTextBrowser()
        self._s4_browser.setMinimumHeight(300)
        layout.addWidget(self._s4_browser, 1)

        self._s4_register_btn = QPushButton("✓ Registra Partita")
        self._s4_register_btn.setMinimumHeight(40)
        self._s4_register_btn.clicked.connect(self._registra_tutto)
        layout.addWidget(self._s4_register_btn)

        return w

    def _render_riepilogo(self):
        numero = self._s1_numero.value()
        suffisso = self._s1_suffisso.text().strip()
        suf_disp = f"/{suffisso}" if suffisso else ""
        data_imp = self._s1_data_imp.date().toString("dd/MM/yyyy")
        tipo = self._s1_tipo.currentText()
        stato = self._s1_stato.currentText()
        comune = self._comune_nome or "Non selezionato"

        n_poss = self._s2_table.rowCount()
        n_imm = self._s3_table.rowCount()

        html = f"""
<style>
body {{ font-family: Segoe UI, Arial; font-size:10pt; }}
h3 {{ color:#3F51B5; margin:12px 0 4px 0; }}
table {{ width:100%; border-collapse:collapse; }}
th {{ background:#E8EAF6; color:#3F51B5; padding:5px 8px; text-align:left; }}
td {{ padding:4px 8px; border-bottom:1px solid #EEE; }}
.ok {{ color:#2E7D32; }}
.warn {{ color:#E65100; }}
</style>
<h3>Partita</h3>
<table>
  <tr><td>Comune</td><td>{comune}</td></tr>
  <tr><td>Numero</td><td>{numero}{suf_disp}</td></tr>
  <tr><td>Data Impianto</td><td>{data_imp}</td></tr>
  <tr><td>Tipo</td><td>{tipo}</td></tr>
  <tr><td>Stato</td><td>{stato}</td></tr>
</table>

<h3>Possessori <span class="{'ok' if n_poss > 0 else 'warn'}">[{n_poss}]</span></h3>
"""
        if n_poss > 0:
            html += '<table><tr><th>Nome</th><th>Titolo</th></tr>'
            for row in range(n_poss):
                nome = self._s2_table.item(row, 0).text() if self._s2_table.item(row, 0) else ""
                titolo = self._s2_table.item(row, 1).text() if self._s2_table.item(row, 1) else ""
                html += f'<tr><td>{nome}</td><td>{titolo}</td></tr>'
            html += '</table>'

        css_class = 'ok' if n_imm > 0 else 'warn'
        html += f'<h3>Immobili <span class="{css_class}">[{n_imm}]</span></h3>'
        if n_imm > 0:
            html += '<table><tr><th>Natura</th><th>Località</th><th>Classificazione</th></tr>'
            for row in range(n_imm):
                natura = self._s3_table.item(row, 0).text() if self._s3_table.item(row, 0) else ""
                localita = self._s3_table.item(row, 1).text() if self._s3_table.item(row, 1) else ""
                classif = self._s3_table.item(row, 2).text() if self._s3_table.item(row, 2) else ""
                html += f'<tr><td>{natura}</td><td>{localita}</td><td>{classif}</td></tr>'
            html += '</table>'

        self._s4_browser.setHtml(html)

    def _go_next(self):
        if self._step == 0:
            if not self._comune_id:
                QMessageBox.warning(self, "Attenzione", "Seleziona un comune.")
                return

        self._step = min(self._step + 1, 3)
        self._stack.setCurrentIndex(self._step)
        if self._step == 2:
            self._load_localita()
        if self._step == 3:
            self._render_riepilogo()
        self._btn_back.setEnabled(self._step > 0)

    def _go_back(self):
        self._step = max(self._step - 1, 0)
        self._stack.setCurrentIndex(self._step)
        self._btn_back.setEnabled(self._step > 0)

    def _reset_wizard(self, *, confirm: bool = True):
        if confirm:
            reply = QMessageBox.question(
                self, "Ricomincia", "Ricominciare il wizard?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply != QMessageBox.StandardButton.Yes:
                return
        self._restoring = True
        try:
            self._step = 0
            self._comune_id = None
            self._comune_nome = ""
            self._s1_comune_label.setText("Nessun comune selezionato")
            self._s1_comune_label.setProperty("muted", "true")
            self._s1_comune_label.style().unpolish(self._s1_comune_label)
            self._s1_comune_label.style().polish(self._s1_comune_label)
            self._s1_numero.setValue(1)
            self._s1_suffisso.clear()
            self._s1_data_imp.setDate(QDate.currentDate())
            self._s1_tipo.setCurrentIndex(0)
            self._s1_stato.setCurrentIndex(0)
            self._s2_search.clear()
            self._s2_results.clear()
            self._s2_table.setRowCount(0)
            self._s3_natura.clear()
            self._s3_classif.clear()
            self._s3_localita.clear()
            self._s3_table.setRowCount(0)
            self._stack.setCurrentIndex(0)
            self._btn_back.setEnabled(False)
            self._current_draft_id = None
            self._dirty = False
            self._update_draft_status()
        finally:
            self._restoring = False

    def _registra_tutto(self):
        if not self._comune_id:
            QMessageBox.warning(self, "Errore", "Comune non selezionato.")
            return

        try:
            numero = self._s1_numero.value()
            suffisso = self._s1_suffisso.text().strip() or None
            data_date = self._s1_data_imp.date()
            data_imp = date(data_date.year(), data_date.month(), data_date.day())
            tipo = self._s1_tipo.currentText().lower()
            stato = self._s1_stato.currentText().lower()

            partita_id = self.db_manager.create_partita(
                comune_id=self._comune_id,
                numero_partita=numero,
                suffisso_partita=suffisso,
                data_impianto=data_imp,
                tipo=tipo,
                stato=stato,
                numero_provenienza=None
            )
        except Exception as e:
            logging.getLogger("CatastoGUI").error(f"Errore registrazione partita: {e}", exc_info=True)
            QMessageBox.critical(self, "Errore", str(e))
            return

        # Possessori e immobili: la partita esiste già; eventuali errori qui
        # vengono raccolti e mostrati, non silenziati.
        errori: list[str] = []

        for row in range(self._s2_table.rowCount()):
            cell = self._s2_table.item(row, 0)
            poss_id = cell.data(Qt.ItemDataRole.UserRole) if cell else None
            titolo = self._s2_table.item(row, 1).text() if self._s2_table.item(row, 1) else ""
            if not poss_id:
                continue
            try:
                self.db_manager.aggiungi_possessore_a_partita(
                    partita_id=partita_id,
                    possessore_id=poss_id,
                    # 'tipo_partita' ammette solo 'principale'/'secondaria'
                    tipo_partita_rel="principale",
                    titolo=titolo or "proprietà esclusiva",
                    quota="1/1",
                )
            except Exception as e:
                nome = cell.text() if cell else str(poss_id)
                logging.getLogger("CatastoGUI").error(
                    f"Errore aggiunta possessore '{nome}': {e}", exc_info=True)
                errori.append(f"Possessore '{nome}': {e}")

        for row in range(self._s3_table.rowCount()):
            cell = self._s3_table.item(row, 0)
            natura = cell.text() if cell else ""
            localita_id = cell.data(Qt.ItemDataRole.UserRole) if cell else None
            classif = self._s3_table.item(row, 2).text() if self._s3_table.item(row, 2) else ""
            if not natura or not localita_id:
                continue
            try:
                self.db_manager.inserisci_immobile(
                    partita_id=partita_id,
                    natura=natura,
                    localita_id=localita_id,
                    classificazione=classif or None,
                )
            except Exception as e:
                logging.getLogger("CatastoGUI").error(
                    f"Errore inserimento immobile '{natura}': {e}", exc_info=True)
                errori.append(f"Immobile '{natura}': {e}")

        if errori:
            QMessageBox.warning(
                self, "Registrazione parziale",
                f"Partita N.{numero} creata (ID: {partita_id}), ma alcuni "
                f"elementi non sono stati salvati:\n\n- " + "\n- ".join(errori))
        else:
            _show_status_message(
                f"Partita N.{numero} registrata con successo (ID: {partita_id}).", 5000)

        # Bozza completata: rimuovila silenziosamente dal DB
        if self._current_draft_id is not None:
            try:
                self.db_manager.delete_partita_draft(
                    self._current_draft_id, utente_id=self.utente_id,
                    wizard_kind=WIZARD_KIND_NUOVA_PARTITA)
            except Exception as e:
                logger.debug(f"Eliminazione bozza post-registrazione fallita: {e}")
            self._current_draft_id = None

        self._reset_wizard(confirm=False)

    # ──────────────────────────────────────────────────────────────────
    # BOZZE — serializzazione, salvataggio, ripresa, autosave
    # ──────────────────────────────────────────────────────────────────

    def _serialize_state(self) -> Dict[str, Any]:
        """Snapshot serializzabile (JSON) dello stato corrente del wizard."""
        possessori = []
        for r in range(self._s2_table.rowCount()):
            nome_item = self._s2_table.item(r, 0)
            tit_item = self._s2_table.item(r, 1)
            if not nome_item:
                continue
            possessori.append({
                "id": nome_item.data(Qt.ItemDataRole.UserRole),
                "nome": nome_item.text(),
                "titolo": tit_item.text() if tit_item else "Proprietario",
            })

        immobili = []
        for r in range(self._s3_table.rowCount()):
            natura_item = self._s3_table.item(r, 0)
            loc_item = self._s3_table.item(r, 1)
            classif_item = self._s3_table.item(r, 2)
            if not natura_item:
                continue
            immobili.append({
                "natura": natura_item.text(),
                "localita_id": natura_item.data(Qt.ItemDataRole.UserRole),
                "localita_text": loc_item.text() if loc_item else "",
                "classificazione": classif_item.text() if classif_item else "",
            })

        return {
            "schema_version": 1,
            "step": self._step,
            "comune": {
                "id": self._comune_id,
                "nome": self._comune_nome,
            },
            "partita": {
                "numero": self._s1_numero.value(),
                "suffisso": self._s1_suffisso.text().strip(),
                "data_impianto": self._s1_data_imp.date().toString("yyyy-MM-dd"),
                "tipo": self._s1_tipo.currentText(),
                "stato": self._s1_stato.currentText(),
            },
            "possessori": possessori,
            "immobili": immobili,
        }

    def _restore_state(self, payload: Dict[str, Any]) -> None:
        """Ripristina lo stato del wizard da uno snapshot."""
        self._restoring = True
        try:
            comune = payload.get("comune") or {}
            self._comune_id = comune.get("id")
            self._comune_nome = comune.get("nome") or ""
            if self._comune_id:
                self._s1_comune_label.setText(self._comune_nome or "(comune)")
                self._s1_comune_label.setProperty("muted", "false")
            else:
                self._s1_comune_label.setText("Nessun comune selezionato")
                self._s1_comune_label.setProperty("muted", "true")
            self._s1_comune_label.style().unpolish(self._s1_comune_label)
            self._s1_comune_label.style().polish(self._s1_comune_label)

            partita = payload.get("partita") or {}
            try:
                self._s1_numero.setValue(int(partita.get("numero") or 1))
            except (TypeError, ValueError):
                self._s1_numero.setValue(1)
            self._s1_suffisso.setText(partita.get("suffisso") or "")
            data_str = partita.get("data_impianto")
            if data_str:
                qd = QDate.fromString(data_str, "yyyy-MM-dd")
                if qd.isValid():
                    self._s1_data_imp.setDate(qd)
            tipo = partita.get("tipo") or ""
            idx = self._s1_tipo.findText(tipo)
            if idx >= 0:
                self._s1_tipo.setCurrentIndex(idx)
            stato = partita.get("stato") or ""
            idx = self._s1_stato.findText(stato)
            if idx >= 0:
                self._s1_stato.setCurrentIndex(idx)

            # Possessori
            self._s2_table.setRowCount(0)
            for p in payload.get("possessori") or []:
                pid = p.get("id")
                nome = p.get("nome") or ""
                titolo = p.get("titolo") or "Proprietario"
                if pid is None:
                    continue
                self._s2_append_possessore(int(pid), nome, titolo=titolo)

            # Immobili — ricarica la combo località prima di restituire
            self._s3_table.setRowCount(0)
            if self._comune_id:
                self._load_localita()
            for im in payload.get("immobili") or []:
                loc_id = im.get("localita_id")
                if loc_id is None:
                    continue
                self._s3_append_immobile(
                    natura=im.get("natura") or "",
                    localita_id=int(loc_id),
                    localita_text=im.get("localita_text") or "",
                    classif=im.get("classificazione") or "",
                )

            # Ripristina lo step e i bottoni di navigazione
            step = int(payload.get("step") or 0)
            self._step = max(0, min(step, 3))
            self._stack.setCurrentIndex(self._step)
            self._btn_back.setEnabled(self._step > 0)
            if self._step == 3:
                self._render_riepilogo()
        finally:
            self._restoring = False
            self._dirty = False
            self._update_draft_status()

    def _default_draft_title(self) -> str:
        n = self._s1_numero.value()
        suf = self._s1_suffisso.text().strip()
        suf_disp = f"/{suf}" if suf else ""
        comune = self._comune_nome or "senza comune"
        return f"{comune} N.{n}{suf_disp} — {datetime.now():%d/%m/%Y %H:%M}"

    def _mark_dirty(self):
        if self._restoring:
            return
        self._dirty = True
        self._update_draft_status()

    def _update_draft_status(self):
        parts: list[str] = []
        if self._current_draft_id is not None:
            parts.append(f"Bozza #{self._current_draft_id}")
        if self._dirty:
            parts.append("• modifiche non salvate")
        self._draft_status_label.setText("  ".join(parts))

    def _save_draft_clicked(self):
        """Salva manualmente la bozza. Se non c'è ancora un draft_id, chiede il titolo."""
        if self._current_draft_id is None:
            default_title = self._default_draft_title()
            title, ok = QInputDialog.getText(
                self, "Salva bozza",
                "Titolo della bozza:",
                text=default_title,
            )
            if not ok:
                return
            title = (title or "").strip() or default_title
            saved_id = self._persist_draft(title=title)
            if saved_id is not None:
                _show_status_message(f"Bozza salvata (id {saved_id}).", 4000)
        else:
            saved_id = self._persist_draft(title=None)
            if saved_id is not None:
                _show_status_message(f"Bozza aggiornata (id {saved_id}).", 4000)

    def _persist_draft(self, title: Optional[str]) -> Optional[int]:
        """Effettua INSERT o UPDATE della bozza. Ritorna l'id (o None se errore)."""
        try:
            payload = self._serialize_state()
            effective_title = title or self._default_draft_title()
            saved_id = self.db_manager.save_partita_draft(
                utente_id=self.utente_id,
                titolo=effective_title,
                payload=payload,
                draft_id=self._current_draft_id,
                app_version=_APP_VERSION,
                wizard_kind=WIZARD_KIND_NUOVA_PARTITA,
            )
            self._current_draft_id = int(saved_id)
            self._dirty = False
            self._update_draft_status()
            return self._current_draft_id
        except Exception as e:
            logger.error(f"Errore salvataggio bozza: {e}", exc_info=True)
            QMessageBox.critical(
                self, "Errore", f"Impossibile salvare la bozza:\n{e}")
            return None

    def _on_autosave_tick(self):
        """Salva la bozza periodicamente se ci sono modifiche pendenti.

        Non crea bozze "vuote": l'autosave si attiva solo se l'utente ha
        già modificato qualcosa (self._dirty) e c'è almeno un dato utile
        (comune selezionato o numero != 1).
        """
        if not self._dirty:
            return
        if not self._has_meaningful_content():
            return
        title = None  # mantiene il titolo se la bozza esiste già
        if self._current_draft_id is None:
            title = self._default_draft_title()
        saved_id = self._persist_draft(title=title)
        if saved_id is not None:
            logger.debug(f"Autosave bozza completato (id {saved_id}).")

    def _has_meaningful_content(self) -> bool:
        if self._comune_id is not None:
            return True
        if self._s2_table.rowCount() > 0 or self._s3_table.rowCount() > 0:
            return True
        if self._s1_suffisso.text().strip():
            return True
        return False

    def _resume_draft(self):
        """Apre il dialog di selezione bozze e ne carica una nel wizard."""
        if self._dirty and self._current_draft_id is None:
            reply = QMessageBox.question(
                self, "Modifiche non salvate",
                "Ci sono modifiche non salvate. Caricare un'altra bozza "
                "le scarterà. Continuare?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No)
            if reply != QMessageBox.StandardButton.Yes:
                return

        dlg = BozzePartitaDialog(
            self.db_manager, self.utente_id, self,
            wizard_kind=WIZARD_KIND_NUOVA_PARTITA,
            window_title="Bozze salvate — Nuova Partita")
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        if dlg.selected_draft_id is None or dlg.selected_draft_payload is None:
            return

        # Reset preventivo (senza conferma) e poi restore
        self._reset_wizard(confirm=False)
        self._restore_state(dlg.selected_draft_payload)
        self._current_draft_id = dlg.selected_draft_id
        self._dirty = False
        self._update_draft_status()
        _show_status_message(
            f"Bozza #{dlg.selected_draft_id} ripresa.", 4000)
