"""
nuova_partita_wizard.py — Wizard a 4 step per la creazione guidata di una nuova partita.

Estratto da partita_workflow_widgets.py (Sprint 3 refactor — six-hats).
La classe e' anche re-esportata da partita_workflow_widgets per
preservare la backward compatibility con i consumer esistenti.
"""
from __future__ import annotations

import json
import logging
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Tuple, TYPE_CHECKING

from PyQt6.QtCore import (
    QDate, Qt, QTimer, pyqtSignal, pyqtSlot,
)
from PyQt6.QtGui import QColor, QFont, QIcon
from PyQt6.QtWidgets import (
    QAbstractItemView, QApplication, QCheckBox, QComboBox, QCompleter,
    QDateEdit, QDialog, QDialogButtonBox, QFileDialog, QFormLayout, QFrame,
    QGridLayout, QGroupBox, QHBoxLayout, QHeaderView, QInputDialog, QLabel,
    QLineEdit, QListWidget, QListWidgetItem, QMenu, QMessageBox, QPushButton,
    QScrollArea, QSizePolicy, QSpacerItem, QSpinBox, QSplitter,
    QStackedWidget, QStyle, QTabWidget, QTableWidget, QTableWidgetItem,
    QTextBrowser, QTextEdit, QVBoxLayout, QWidget,
)

from app_paths import get_icon_path
from app_utils import (
    BulkReportPDF, FPDF_AVAILABLE,
    format_indirizzo,
    gui_esporta_partita_pdf, gui_esporta_partita_json, gui_esporta_partita_csv,
    gui_esporta_possessore_pdf, gui_esporta_possessore_json, gui_esporta_possessore_csv,
    GenericTextReportPDF, is_file_locked, get_alternative_filename,
)
from foliarium.ui.widgets.custom import (
    LazyLoadedWidget, QPasswordLineEdit, StatCard,
    show_status_message as _show_status_message,
)
from foliarium.ui.widgets.insertion import (
    InserimentoComuneWidget, InserimentoPossessoreWidget,
    InserimentoLocalitaWidget, InserimentoPartitaWidget,
)
from foliarium.ui.widgets.admin import (
    GestioneTipiLocalitaWidget, GestionePeriodiStoriciWidget,
)
from dialogs import (
    AlberoGeneralogicoDialog, ComuneSelectionDialog, ConfrontoPartiteDialog,
    CreatePossessoreDialog, CreateUserDialog, DBConfigDialog,
    DettagliLegamePossessoreDialog, DocumentViewerDialog, ImmobileDialog,
    LocalitaSelectionDialog, ModificaComuneDialog, ModificaImmobileDialog,
    ModificaLocalitaDialog, ModificaPossessoreDialog, PartitaDetailsDialog,
    PartitaSearchDialog, PartiteComuneDialog, PeriodoStoricoDetailsDialog,
    PeriodoStoricoEditDialog, PossessoreSelectionDialog, PossessoriComuneDialog,
    UserSelectionDialog,
    qdate_to_datetime, datetime_to_qdate,
    _hash_password, _verify_password,
)

try:
    from catasto_db_manager import (
        DBMError, DBUniqueConstraintError, DBNotFoundError, DBDataError,
    )
except ImportError:
    class DBMError(Exception):
        pass

if TYPE_CHECKING:
    from catasto_db_manager import CatastoDBManager  # noqa: F401

logger = logging.getLogger("CatastoGUI.nuova_partita_wizard")


class NuovaPartitaWizardWidget(QWidget):
    """Wizard a 4 step per la creazione guidata di una nuova partita."""

    def __init__(self, db_manager, utente_info=None, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.utente_info = utente_info or {}
        self._step = 0
        self._comune_id: Optional[int] = None
        self._comune_nome: str = ""
        self._build_ui()

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
        form_layout.addRow("Numero Partita: *", self._s1_numero)

        self._s1_suffisso = QLineEdit()
        self._s1_suffisso.setPlaceholderText("Es. A, B, bis (opzionale)")
        form_layout.addRow("Suffisso:", self._s1_suffisso)

        self._s1_data_imp = QDateEdit()
        self._s1_data_imp.setCalendarPopup(True)
        self._s1_data_imp.setDate(QDate.currentDate())
        self._s1_data_imp.setDisplayFormat("dd/MM/yyyy")
        form_layout.addRow("Data Impianto: *", self._s1_data_imp)

        self._s1_tipo = QComboBox()
        self._s1_tipo.addItems(["Principale", "Secondaria", "Enfiteusi", "Usufrutto"])
        form_layout.addRow("Tipo:", self._s1_tipo)

        self._s1_stato = QComboBox()
        self._s1_stato.addItems(["Attiva", "Inattiva"])
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

        row = self._s2_table.rowCount()
        self._s2_table.insertRow(row)
        self._s2_table.setItem(row, 0, QTableWidgetItem(item.text().split(" — ")[0]))
        self._s2_table.setItem(row, 1, QTableWidgetItem("Proprietario"))
        self._s2_table.item(row, 0).setData(Qt.ItemDataRole.UserRole, poss_id)

        del_btn = QPushButton("✕")
        del_btn.clicked.connect(lambda: self._s2_table.removeRow(row))
        self._s2_table.setCellWidget(row, 2, del_btn)

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
        add_layout.addRow("Natura:", self._s3_natura)

        self._s3_classif = QLineEdit()
        self._s3_classif.setPlaceholderText("Es. A/1, A/2")
        add_layout.addRow("Classificazione:", self._s3_classif)

        add_btn = QPushButton("+ Aggiungi")
        add_btn.clicked.connect(self._s3_add_immobile)
        add_layout.addRow("", add_btn)

        layout.addWidget(add_group)

        layout.addWidget(QLabel("Immobili:"))
        self._s3_table = QTableWidget()
        self._s3_table.setColumnCount(3)
        self._s3_table.setHorizontalHeaderLabels(["Natura", "Classificazione", ""])
        self._s3_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self._s3_table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self._s3_table, 1)

        return w

    def _s3_add_immobile(self):
        natura = self._s3_natura.text().strip()
        if not natura:
            QMessageBox.warning(self, "Attenzione", "Natura obbligatoria.")
            return

        row = self._s3_table.rowCount()
        self._s3_table.insertRow(row)
        self._s3_table.setItem(row, 0, QTableWidgetItem(natura))
        self._s3_table.setItem(row, 1, QTableWidgetItem(self._s3_classif.text().strip()))

        del_btn = QPushButton("✕")
        del_btn.clicked.connect(lambda: self._s3_table.removeRow(row))
        self._s3_table.setCellWidget(row, 2, del_btn)

        self._s3_natura.clear()
        self._s3_classif.clear()

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
            html += '<table><tr><th>Natura</th><th>Classificazione</th></tr>'
            for row in range(n_imm):
                natura = self._s3_table.item(row, 0).text() if self._s3_table.item(row, 0) else ""
                classif = self._s3_table.item(row, 1).text() if self._s3_table.item(row, 1) else ""
                html += f'<tr><td>{natura}</td><td>{classif}</td></tr>'
            html += '</table>'

        self._s4_browser.setHtml(html)

    def _go_next(self):
        if self._step == 0:
            if not self._comune_id:
                QMessageBox.warning(self, "Attenzione", "Seleziona un comune.")
                return

        self._step = min(self._step + 1, 3)
        self._stack.setCurrentIndex(self._step)
        if self._step == 3:
            self._render_riepilogo()
        self._btn_back.setEnabled(self._step > 0)

    def _go_back(self):
        self._step = max(self._step - 1, 0)
        self._stack.setCurrentIndex(self._step)
        self._btn_back.setEnabled(self._step > 0)

    def _reset_wizard(self):
        reply = QMessageBox.question(
            self, "Ricomincia", "Ricominciare il wizard?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            self._step = 0
            self._comune_id = None
            self._s1_numero.setValue(1)
            self._s1_suffisso.clear()
            self._s1_data_imp.setDate(QDate.currentDate())
            self._s2_table.setRowCount(0)
            self._s3_table.setRowCount(0)
            self._stack.setCurrentIndex(0)
            self._btn_back.setEnabled(False)

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

            for row in range(self._s2_table.rowCount()):
                poss_id = self._s2_table.item(row, 0).data(Qt.ItemDataRole.UserRole) if self._s2_table.item(row, 0) else None
                titolo = self._s2_table.item(row, 1).text() if self._s2_table.item(row, 1) else ""
                if poss_id:
                    try:
                        self.db_manager.aggiungi_possessore_a_partita(
                            partita_id=partita_id,
                            possessore_id=poss_id,
                            tipo_partita_rel="proprietario",
                            titolo=titolo,
                            quota="1/1"
                        )
                    except Exception as e:
                        logging.getLogger("CatastoGUI").warning(f"Errore aggiunta possessore: {e}")

            _show_status_message(f"Partita N.{numero} registrata con successo (ID: {partita_id}).", 5000)
            self._reset_wizard()

        except Exception as e:
            logging.getLogger("CatastoGUI").error(f"Errore registrazione partita: {e}", exc_info=True)
            QMessageBox.critical(self, "Errore", str(e))


