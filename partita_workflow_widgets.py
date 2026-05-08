"""Partita workflow widgets — registrazione proprietà, wizard nuova partita,
operazioni (frazionamento/passaggi/duplicazione/scissione).

Estratto da gui_widgets.py in v1.0.0 per ridurre la dimensione del modulo
monolitico. Le classi sono re-esportate da gui_widgets.py per compatibilità.
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

logger = logging.getLogger("CatastoGUI.partita_workflow_widgets")


class RegistrazioneProprietaWidget(LazyLoadedWidget):
    partita_creata_per_operazioni_collegate = pyqtSignal(int, int)

    def __init__(self, db_manager: 'CatastoDBManager', parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.comune_id: Optional[int] = None
        self.possessori_data: List[Dict[str, Any]] = []
        self.immobili_data: List[Dict[str, Any]] = []
        self.localita_cache: List[Dict[str, Any]] = []
        self.possessori_cache: List[Dict[str, Any]] = []
        self.immobili_cache: List[Dict[str, Any]] = []
        self._initUI()

    def _initUI(self):
        main_layout = QVBoxLayout(self)
        scroll_area = QScrollArea(); scroll_area.setWidgetResizable(True)
        main_layout.addWidget(scroll_area)
        container_widget = QWidget(); layout = QVBoxLayout(container_widget)
        scroll_area.setWidget(container_widget)
        
        # --- 1. DATI PARTITA (LAYOUT COMPATTO) ---
        form_group = QGroupBox("1. Dati della Nuova Partita")
        form_layout = QGridLayout(form_group)
        self.comune_display = QLabel("Nessun comune selezionato."); self.comune_display.setStyleSheet("font-weight: bold;")
        self.comune_button = QPushButton("Seleziona Comune..."); self.comune_button.clicked.connect(self._select_comune)
        form_layout.addWidget(QLabel("Comune (*):"), 0, 0); form_layout.addWidget(self.comune_display, 0, 1, 1, 2)
        form_layout.addWidget(self.comune_button, 0, 3)
        
        # --- INIZIO MODIFICA LAYOUT ---
        self.num_partita_edit = QSpinBox(); self.num_partita_edit.setRange(1, 9999999)
        self.suffisso_partita_edit = QLineEdit(); self.suffisso_partita_edit.setPlaceholderText("Es. A"); self.suffisso_partita_edit.setMaximumWidth(80)
        self.data_edit = QDateEdit(calendarPopup=True); self.data_edit.setDate(QDate.currentDate()); self.data_edit.setDisplayFormat("yyyy-MM-dd")
        
        partita_line_layout = QHBoxLayout()
        partita_line_layout.addWidget(QLabel("Numero Partita (*):")); partita_line_layout.addWidget(self.num_partita_edit)
        partita_line_layout.addWidget(QLabel("Suffisso:")); partita_line_layout.addWidget(self.suffisso_partita_edit)
        partita_line_layout.addStretch()
        form_layout.addLayout(partita_line_layout, 1, 0, 1, 4)
        
        form_layout.addWidget(QLabel("Data Impianto (*):"), 2, 0); form_layout.addWidget(self.data_edit, 2, 1)
        # --- FINE MODIFICA LAYOUT ---
        
        layout.addWidget(form_group)

        # --- 2. POSSESSORI (FLUSSO MIGLIORATO) ---
        possessori_group = QGroupBox("2. Possessori Associati")
        possessori_layout = QVBoxLayout(possessori_group)
        self.possessori_table = QTableWidget(); self.possessori_table.setColumnCount(4); self.possessori_table.setHorizontalHeaderLabels(["ID", "Nome Completo", "Titolo", "Quota"])
        self.possessori_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive); self.possessori_table.horizontalHeader().setStretchLastSection(True); self.possessori_table.setMinimumHeight(120)
        self.btn_rem_poss = QPushButton("Rimuovi Selezionato"); self.btn_rem_poss.clicked.connect(self.remove_possessore)
        possessori_layout.addWidget(self.possessori_table); possessori_layout.addWidget(self.btn_rem_poss, 0, Qt.AlignmentFlag.AlignRight)
        
        add_poss_group = QGroupBox("Aggiungi Possessore"); add_poss_layout = QGridLayout(add_poss_group)
        self.possessore_search_combo = QComboBox(); self.possessore_search_combo.setEditable(True); self.possessore_search_combo.setPlaceholderText("Cerca possessore esistente...")
        self.possessore_search_combo.completer().setCompletionMode(QCompleter.CompletionMode.PopupCompletion); self.possessore_search_combo.completer().setFilterMode(Qt.MatchFlag.MatchContains)
        self.btn_add_selected_poss = QPushButton("Aggiungi Selezionato"); self.btn_add_selected_poss.clicked.connect(self._add_selected_possessore)
        self.btn_create_new_poss = QPushButton("Crea Nuovo..."); self.btn_create_new_poss.clicked.connect(self._create_and_add_new_possessore)
        add_poss_layout.addWidget(QLabel("Cerca:"), 0, 0); add_poss_layout.addWidget(self.possessore_search_combo, 0, 1)
        add_poss_layout.addWidget(self.btn_add_selected_poss, 0, 2); add_poss_layout.addWidget(self.btn_create_new_poss, 0, 3)
        possessori_layout.addWidget(add_poss_group); layout.addWidget(possessori_group)

        # --- 3. IMMOBILI (FLUSSO MIGLIORATO) ---
        immobili_group = QGroupBox("3. Immobili Associati"); immobili_layout = QVBoxLayout(immobili_group)
        self.immobili_table = QTableWidget(); self.immobili_table.setColumnCount(5); self.immobili_table.setHorizontalHeaderLabels(["Natura", "Località", "Classificazione", "Consistenza", "Piani/Vani"])
        self.immobili_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive); self.immobili_table.horizontalHeader().setStretchLastSection(True); self.immobili_table.setMinimumHeight(120)
        self.btn_rem_imm = QPushButton("Rimuovi Selezionato"); self.btn_rem_imm.clicked.connect(self.remove_immobile)
        immobili_layout.addWidget(self.immobili_table); immobili_layout.addWidget(self.btn_rem_imm, 0, Qt.AlignmentFlag.AlignRight)
        add_imm_tabs = QTabWidget(); add_imm_tabs.addTab(self._create_add_immobile_esistente_tab(), "Aggiungi Esistente"); add_imm_tabs.addTab(self._create_add_immobile_nuovo_tab(), "Crea Nuovo")
        immobili_layout.addWidget(add_imm_tabs); layout.addWidget(immobili_group)

        # --- 4. REGISTRAZIONE FINALE ---
        self.btn_registra_proprieta = QPushButton("Registra Nuova Proprietà e Tutti i Componenti"); self.btn_registra_proprieta.clicked.connect(self._salva_proprieta)
        self.btn_registra_proprieta.setStyleSheet("font-weight: bold; padding: 10px; background-color: #d4edda; border: 1px solid #c3e6cb;"); 
        self.btn_registra_proprieta.setEnabled(False) # Inizia disabilitato
        layout.addWidget(self.btn_registra_proprieta); layout.addStretch(1)
        
        self._update_registra_button_state()

    def _update_registra_button_state(self):
        """
        Abilita il pulsante di registrazione finale solo se tutte le 
        condizioni necessarie sono soddisfatte.
        """
        is_ready = bool(
            self.comune_id and      # Deve essere selezionato un comune
            self.possessori_data and  # La lista possessori non deve essere vuota
            self.immobili_data       # La lista immobili non deve essere vuota
        )
        self.btn_registra_proprieta.setEnabled(is_ready)

        if is_ready:
            self.btn_registra_proprieta.setToolTip("Pronto per registrare la proprietà nel database.")
        else:
            reasons = []
            if not self.comune_id: reasons.append("selezionare un comune")
            if not self.possessori_data: reasons.append("aggiungere almeno un possessore")
            if not self.immobili_data: reasons.append("aggiungere almeno un immobile")
            tooltip_text = f"Per abilitare, è necessario: {', '.join(reasons)}."
            self.btn_registra_proprieta.setToolTip(tooltip_text)

    
    def _create_add_immobile_esistente_tab(self):
        widget = QWidget(); layout = QGridLayout(widget)
        self.imm_search_combo = QComboBox(); self.imm_search_combo.setEditable(True); self.imm_search_combo.setPlaceholderText("Seleziona prima un comune...")
        self.imm_search_combo.setEnabled(False); self.imm_search_combo.completer().setCompletionMode(QCompleter.CompletionMode.PopupCompletion); self.imm_search_combo.completer().setFilterMode(Qt.MatchFlag.MatchContains)
        self.btn_add_existing_imm = QPushButton("Aggiungi Selezionato"); self.btn_add_existing_imm.clicked.connect(self._add_existing_immobile)
        layout.addWidget(QLabel("Cerca Immobile:"), 0, 0); layout.addWidget(self.imm_search_combo, 0, 1); layout.addWidget(self.btn_add_existing_imm, 0, 2)
        return widget

    def _create_add_immobile_nuovo_tab(self):
        widget = QWidget(); layout = QGridLayout(widget)
        self.imm_natura_edit = QLineEdit(); layout.addWidget(QLabel("Natura (*):"), 0, 0); layout.addWidget(self.imm_natura_edit, 0, 1)
        self.imm_localita_combo = QComboBox(); self.imm_localita_combo.setPlaceholderText("Seleziona prima un comune..."); self.imm_localita_combo.setEnabled(False)
        layout.addWidget(QLabel("Località (*):"), 0, 2); layout.addWidget(self.imm_localita_combo, 0, 3)
        self.imm_classificazione_edit = QLineEdit(); layout.addWidget(QLabel("Classificazione:"), 1, 0); layout.addWidget(self.imm_classificazione_edit, 1, 1)
        self.imm_consistenza_edit = QLineEdit(); layout.addWidget(QLabel("Consistenza:"), 1, 2); layout.addWidget(self.imm_consistenza_edit, 1, 3)
        self.imm_piani_spin = QSpinBox(); self.imm_piani_spin.setRange(0, 99); layout.addWidget(QLabel("Piani:"), 2, 0); layout.addWidget(self.imm_piani_spin, 2, 1)
        self.imm_vani_spin = QSpinBox(); self.imm_vani_spin.setRange(0, 99); layout.addWidget(QLabel("Vani:"), 2, 2); layout.addWidget(self.imm_vani_spin, 2, 3)
        self.btn_add_inline_immobile = QPushButton("Aggiungi alla Lista"); self.btn_add_inline_immobile.clicked.connect(self._add_inline_immobile)
        layout.addWidget(self.btn_add_inline_immobile, 3, 3, Qt.AlignmentFlag.AlignRight)
        return widget

    def _load_data_on_first_show(self):
        """
        Metodo per il lazy loading. Carica la lista globale dei possessori
        la prima volta che questo widget viene visualizzato.
        """
        self.logger.info("Esecuzione lazy loading per RegistrazioneProprietaWidget...")
        self._load_possessori_for_combo()

    def _select_comune(self):
        dialog = ComuneSelectionDialog(self.db_manager, self)
        if dialog.exec() == QDialog.DialogCode.Accepted and dialog.selected_comune_id:
            self.comune_id = dialog.selected_comune_id
            self.comune_display.setText(f"{dialog.selected_comune_name} (ID: {self.comune_id})")
            self.logger.info(f"Comune selezionato ID: {self.comune_id}. Caricamento dati dipendenti...")
            self._load_localita_for_combo()
            self._load_immobili_for_combo()
            self._load_possessori_for_combo()
            self._update_registra_button_state()

    def _load_possessori_for_combo(self):
        """Carica tutti i possessori per la combobox di ricerca."""
        if self.possessori_cache: # Non ricaricare se la cache è già piena
            return
        self.possessore_search_combo.clear(); self.possessore_search_combo.addItem("--- Cerca o Seleziona ---", None)
        try:
            self.possessori_cache = self.db_manager.search_possessori_by_term_globally(None, limit=5000)
            for poss in self.possessori_cache:
                self.possessore_search_combo.addItem(f"{poss['nome_completo']} (Comune: {poss['comune_riferimento_nome']})", poss['id'])
            self.logger.info(f"Caricati {len(self.possessori_cache)} possessori nella combobox.")
        except DBMError as e:
            self.logger.error(f"Errore caricamento possessori globali: {e}")

    def _load_localita_for_combo(self):
        self.imm_localita_combo.clear()
        self.imm_localita_combo.setEnabled(False)
        self.imm_localita_combo.addItem("--- Caricamento ---", None)
        if not self.comune_id: return
        try:
            self.localita_cache = self.db_manager.get_localita_by_comune(self.comune_id)
            self.imm_localita_combo.clear()
            if self.localita_cache:
                self.imm_localita_combo.addItem("--- Seleziona Località ---", None)
                for loc in self.localita_cache:
                    self.imm_localita_combo.addItem(f"{loc['nome']} ({loc.get('tipo', 'N/D')})", loc['id'])
                self.imm_localita_combo.setEnabled(True)
            else:
                self.imm_localita_combo.addItem("Nessuna località per questo comune", None)
        except DBMError as e: self.logger.error(f"Errore caricamento località: {e}")


    def _load_immobili_for_combo(self):
        self.imm_search_combo.clear()
        self.imm_search_combo.setEnabled(False)
        self.imm_search_combo.addItem("--- Caricamento ---", None)
        if not self.comune_id: return
        try:
            self.immobili_cache = self.db_manager.get_immobili_by_comune(self.comune_id)
            self.imm_search_combo.clear()
            if self.immobili_cache:
                self.imm_search_combo.addItem("--- Cerca Immobile Esistente ---", None)
                for imm in self.immobili_cache:
                    self.imm_search_combo.addItem(f"{imm['natura']} in {imm['localita_nome']}", imm['id'])
                self.imm_search_combo.setEnabled(True)
            else:
                self.imm_search_combo.addItem("Nessun immobile in questo comune", None)
        except DBMError as e: self.logger.error(f"Errore caricamento immobili: {e}")
     # Nuovi Metodi Slot per i pulsanti inline
    def _add_selected_possessore(self):
        possessore_id = self.possessore_search_combo.currentData()
        if not possessore_id: return QMessageBox.warning(self, "Selezione Mancante", "Seleziona un possessore.")

        # Evita duplicati
        if any(p['id'] == possessore_id for p in self.possessori_data):
            return QMessageBox.information(self, "Già Presente", "Questo possessore è già nella lista.")

        dettagli = DettagliLegamePossessoreDialog.get_details_for_new_legame(self.possessore_search_combo.currentText(), 'principale', self)
        if dettagli:
            self.possessori_data.append({"id": possessore_id, "nome_completo": self.possessore_search_combo.currentText(), **dettagli})
            self.update_possessori_table()


    def _create_and_add_new_possessore(self):
        dialog = CreatePossessoreDialog(self.db_manager, self)
        if dialog.exec() == QDialog.DialogCode.Accepted and dialog.nuovo_possessore_dati:
            poss_info = dialog.nuovo_possessore_dati
            self._load_possessori_for_combo() # Ricarica la lista per includere il nuovo
            # Aggiungi direttamente alla lista della partita corrente
            dettagli = DettagliLegamePossessoreDialog.get_details_for_new_legame(poss_info.get('nome_completo'), 'principale', self)
            if dettagli:
                self.possessori_data.append({"id": poss_info['id'], "nome_completo": poss_info['nome_completo'], **dettagli})
                self.update_possessori_table()
    def _add_existing_immobile(self):
        immobile_id = self.imm_search_combo.currentData()
        if not immobile_id: return QMessageBox.warning(self, "Selezione Mancante", "Seleziona un immobile.")

        if any(i.get('id') == immobile_id for i in self.immobili_data):
            return QMessageBox.information(self, "Già Presente", "Questo immobile è già nella lista.")

        # Trova i dettagli dell'immobile dalla cache
        imm_details = next((i for i in self.immobili_cache if i['id'] == immobile_id), None)
        if imm_details:
            self.immobili_data.append(imm_details)
            self.update_immobili_table()

    def _add_inline_immobile(self):
        natura = self.imm_natura_edit.text().strip()
        localita_id = self.imm_localita_combo.currentData()
        if not natura or localita_id is None: return QMessageBox.warning(self, "Dati Mancanti", "Natura e Località sono obbligatori.")

        immobile_dict = {
            'natura': natura,
            'localita_id': localita_id,
            'localita_nome': self.imm_localita_combo.currentText(),
            'classificazione': self.imm_classificazione_edit.text().strip(),
            'consistenza': self.imm_consistenza_edit.text().strip(),
            'numero_piani': self.imm_piani_spin.value(),
            'numero_vani': self.imm_vani_spin.value()
        }  # (come prima)
        self.immobili_data.append(immobile_dict)
        self.update_immobili_table()
        self._pulisci_form_immobile()

    def _pulisci_form_immobile(self):
        self.imm_natura_edit.clear(); self.imm_classificazione_edit.clear(); self.imm_consistenza_edit.clear()
        self.imm_localita_combo.setCurrentIndex(0); self.imm_piani_spin.setValue(0); self.imm_vani_spin.setValue(0)
    
    def update_possessori_table(self):
        self.possessori_table.setRowCount(len(self.possessori_data))
        for i, dati in enumerate(self.possessori_data):
            self.possessori_table.setItem(i, 0, QTableWidgetItem(str(dati.get('id'))))
            self.possessori_table.setItem(i, 1, QTableWidgetItem(dati.get('nome_completo')))
            self.possessori_table.setItem(i, 2, QTableWidgetItem(dati.get('titolo')))
            self.possessori_table.setItem(i, 3, QTableWidgetItem(dati.get('quota')))
        self._update_registra_button_state()
        
    def update_immobili_table(self):
        self.immobili_table.setRowCount(len(self.immobili_data))
        for i, imm in enumerate(self.immobili_data):
            immobile = imm if isinstance(imm, dict) else imm.to_dict()  # Assicurati che sia un dizionario
            self.immobili_table.setItem(
                i, 0, QTableWidgetItem(immobile.get('natura', '')))
            self.immobili_table.setItem(i, 1, QTableWidgetItem(
                immobile.get('localita_nome', '')))
            self.immobili_table.setItem(i, 2, QTableWidgetItem(
                immobile.get('classificazione', '')))
            self.immobili_table.setItem(
                i, 3, QTableWidgetItem(immobile.get('consistenza', '')))

            piani_vani = ""
            if 'numero_piani' in immobile and immobile['numero_piani']:
                piani_vani += f"Piani: {immobile['numero_piani']}"
            if 'numero_vani' in immobile and immobile['numero_vani']:
                if piani_vani:
                    piani_vani += ", "
                piani_vani += f"Vani: {immobile['numero_vani']}"

            self.immobili_table.setItem(i, 4, QTableWidgetItem(piani_vani))
        self._update_registra_button_state()
    def remove_possessore(self):
        """Rimuove il possessore selezionato dalla lista."""
        selected_rows = self.possessori_table.selectedIndexes()
        if not selected_rows:
            QMessageBox.warning(self, "Attenzione",
                                "Seleziona un possessore da rimuovere.")
            return

        row = selected_rows[0].row()
        if 0 <= row < len(self.possessori_data):
            del self.possessori_data[row]
            self.update_possessori_table()
        self._update_registra_button_state()
        
    def remove_immobile(self):
        """Rimuove l'immobile selezionato dalla lista."""
        selected_rows = self.immobili_table.selectedIndexes()
        if not selected_rows:
            QMessageBox.warning(self, "Attenzione",
                                "Seleziona un immobile da rimuovere.")
            return

        row = selected_rows[0].row()
        if 0 <= row < len(self.immobili_data):
            del self.immobili_data[row]
            self.update_immobili_table()
        self._update_registra_button_state()
        
    
        
    def _salva_proprieta(self):
        self.logger.info("Avvio registrazione nuova proprietà...")
        if not self.comune_id:
            QMessageBox.warning(self, "Dati Mancanti", "Selezionare un comune.")
            return
        if not self.possessori_data:
            QMessageBox.warning(self, "Dati Mancanti", "Aggiungere almeno un possessore.")
            return
        if not self.immobili_data:
            QMessageBox.warning(self, "Dati Mancanti", "Aggiungere almeno un immobile.")
            return

        numero_partita = self.num_partita_edit.value()
        # Legge correttamente il valore del suffisso dalla UI
        suffisso_partita = self.suffisso_partita_edit.text().strip() or None 
        data_impianto_dt = self.data_edit.date().toPyDate()

        try:
            possessori_json_str = json.dumps(self.possessori_data)
            immobili_json_str = json.dumps(self.immobili_data)
        except TypeError as te:
            self.logger.error(f"Errore serializzazione JSON per nuova proprietà: {te}")
            QMessageBox.critical(self, "Errore Dati", f"Errore nella preparazione dei dati per il database: {te}")
            return

        try:
            # Chiamata al DB Manager, ora completa con tutti gli argomenti
            nuova_partita_id = self.db_manager.registra_nuova_proprieta(
                comune_id=self.comune_id,
                numero_partita=numero_partita,
                data_impianto=data_impianto_dt,
                possessori_json_str=possessori_json_str,
                immobili_json_str=immobili_json_str,
                suffisso_partita=suffisso_partita  # <<< QUESTA È LA RIGA MANCANTE, ORA AGGIUNTA
            )

            if nuova_partita_id is not None and self.comune_id is not None:
                suffisso_display = f" (Suffisso: {suffisso_partita})" if suffisso_partita else ""
                msg_success = f"Nuova proprietà (Partita N.{numero_partita}{suffisso_display}, ID: {nuova_partita_id}) registrata con successo."
                self.logger.info(msg_success)

                reply = QMessageBox.question(self, "Registrazione Completata",
                                             f"{msg_success}\n\nVuoi procedere con operazioni collegate (es. Duplicazione) su questa o un'altra partita?",
                                             QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)

                if reply == QMessageBox.StandardButton.Yes:
                    self.partita_creata_per_operazioni_collegate.emit(nuova_partita_id, self.comune_id)

                self._pulisci_form_registrazione()

        except (DBUniqueConstraintError, DBDataError, DBMError) as e_db:
            self.logger.error(f"Errore DB registrazione proprietà: {e_db}")
            QMessageBox.critical(self, "Errore Database", str(e_db))
        except Exception as e_gen:
            self.logger.critical(f"Errore imprevisto registrazione proprietà: {e_gen}", exc_info=True)
            QMessageBox.critical(self, "Errore Imprevisto", f"Errore: {type(e_gen).__name__}: {e_gen}")
        self.logger.info("Registrazione proprietà completata.")
    """ 
    def add_possessore(self):
        
        if not self.comune_id:
            QMessageBox.warning(self, "Comune Mancante", "Selezionare un comune per la partita prima di aggiungere un possessore.")
            return

        # --- MODIFICA CHIAVE QUI ---
        # Passiamo 'None' come comune_id per indicare al dialogo di non filtrare
        # e permettere la selezione/creazione da qualsiasi comune.
        dialog_sel_poss = PossessoreSelectionDialog(self.db_manager, comune_id=None, parent=self)
        # --- FINE MODIFICA ---

        if dialog_sel_poss.exec() == QDialog.DialogCode.Accepted and dialog_sel_poss.selected_possessore:
            selected_possessore_info = dialog_sel_poss.selected_possessore
        
        # 2. Dialogo per chiedere i dettagli del LEGAME (Titolo, Quota)
        # Usiamo il metodo statico che abbiamo già preparato
        dettagli_legame = DettagliLegamePossessoreDialog.get_details_for_new_legame(
            nome_possessore=selected_possessore_info.get('nome_completo', 'N/D'),
            tipo_partita_attuale='principale', # Per una nuova proprietà, è 'principale'
            parent=self
        )

        if not dettagli_legame:
            self.logger.info("Definizione dettagli del legame annullata.")
            return

        # 3. Combina le informazioni e aggiungile alla lista dati
        dati_completi_possessore = {
            "id": selected_possessore_info.get('id'),
            "nome_completo": selected_possessore_info.get('nome_completo'),
            "titolo": dettagli_legame.get('titolo'), # Obbligatorio
            "quota": dettagli_legame.get('quota')   # Opzionale
        }
        
        self.possessori_data.append(dati_completi_possessore)
        self.update_possessori_table()

    

    

    def add_immobile(self):
       
        dialog = ImmobileDialog(self.db_manager, self.comune_id, self)
        result = dialog.exec()

        if result == QDialog.DialogCode.Accepted and dialog.immobile_data:
            self.immobili_data.append(dialog.immobile_data)
            self.update_immobili_table()


    """

    def _pulisci_form_registrazione(self):
       
        logging.getLogger("CatastoGUI").info(
            "Pulizia campi del form Registrazione Proprietà.")

        # Reset Comune selezionato
        self.comune_id = None
        self.comune_display_name = None  # Se usa una variabile per il nome del comune
        if hasattr(self, 'comune_display') and isinstance(self.comune_display, QLabel):
            self.comune_display.setText("Nessun comune selezionato")

        # Reset Numero Partita
        if hasattr(self, 'num_partita_edit') and isinstance(self.num_partita_edit, QSpinBox):
            # O un valore di default sensato come 1
            self.num_partita_edit.setValue(self.num_partita_edit.minimum())

        # Reset Data Impianto
        if hasattr(self, 'data_edit') and isinstance(self.data_edit, QDateEdit):
            self.data_edit.setDate(QDate.currentDate())

        # Reset liste dati interni
        self.possessori_data = []
        self.immobili_data = []

        # Aggiorna/Pulisci le tabelle UI dei possessori e immobili (se le ha)
        # Metodo che popola/pulisce la QTableWidget dei possessori
        if hasattr(self, 'update_possessori_table'):
            self.update_possessori_table()
        # Alternativa se non c'è update_xxx
        elif hasattr(self, 'possessori_table') and isinstance(self.possessori_table, QTableWidget):
            self.possessori_table.setRowCount(0)

        # Metodo che popola/pulisce la QTableWidget degli immobili
        if hasattr(self, 'update_immobili_table'):
            self.update_immobili_table()
        elif hasattr(self, 'immobili_table') and isinstance(self.immobili_table, QTableWidget):
            self.immobili_table.setRowCount(0)

        # Imposta il focus su un campo iniziale, ad esempio il pulsante per selezionare il comune
        if hasattr(self, 'comune_button') and isinstance(self.comune_button, QPushButton):
            self.comune_button.setFocus()
        elif hasattr(self, 'num_partita_edit'):  # O il campo numero partita
            self.num_partita_edit.setFocus()

        logging.getLogger("CatastoGUI").info(
            "Campi form Registrazione Proprietà puliti.")


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
        title.setStyleSheet("font-size:14pt; font-weight:600; color:#3F51B5;")
        layout.addWidget(title)

        form_group = QGroupBox("Informazioni Generali")
        form_layout = QFormLayout(form_group)
        form_layout.setSpacing(10)

        self._s1_comune_label = QLabel("Nessun comune selezionato")
        self._s1_comune_label.setStyleSheet("color:#757575; font-style:italic;")
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
            self._s1_comune_label.setStyleSheet("color:#212121;")

    def _build_step2(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(32, 24, 32, 24)
        layout.setSpacing(12)

        title = QLabel("Aggiungi Possessori (Opzionale)")
        title.setStyleSheet("font-size:14pt; font-weight:600; color:#3F51B5;")
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
        title.setStyleSheet("font-size:14pt; font-weight:600; color:#3F51B5;")
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
        title.setStyleSheet("font-size:14pt; font-weight:600; color:#3F51B5;")
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
            tipo = self._s1_tipo.currentText()
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


class OperazioniPartitaWidget(QWidget):
    # Aggiungi questo __init__ se non c'è
    def __init__(self, db_manager: CatastoDBManager, parent=None):
        super().__init__(parent)
        self.logger = logging.getLogger(f"CatastoGUI.{self.__class__.__name__}") # AGGIUNGI QUESTA RIGA
        self.db_manager = db_manager
        self.selected_partita_id_source: Optional[int] = None
        self.selected_partita_comune_id_source: Optional[int] = None
        self.selected_partita_comune_nome_source: Optional[str] = None
        self.selected_immobile_id_transfer: Optional[int] = None
        self._pp_temp_nuovi_possessori: List[Dict[str, Any]] = []

        self.partita_destinazione_valida: bool = False

        self._initUI()

    def _initUI(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(15)

        # --- 1. Selezione Partita Sorgente (Comune a tutti i tab sottostanti) ---
        source_partita_group = QGroupBox("Selezione Partita Sorgente")
        source_partita_layout = QGridLayout(source_partita_group)

        source_partita_layout.addWidget(QLabel("ID Partita Sorgente:"), 0, 0)
        self.source_partita_id_spinbox = QSpinBox()
        self.source_partita_id_spinbox.setRange(
            1, 9999999)  # Range ampio per ID
        self.source_partita_id_spinbox.setToolTip(
            "Inserisci l'ID della partita o usa 'Cerca'")
        source_partita_layout.addWidget(self.source_partita_id_spinbox, 0, 1)

        self.btn_cerca_source_partita = QPushButton(QApplication.style().standardIcon(
            QStyle.StandardPixmap.SP_FileDialogContentsView), " Cerca Partita...")
        self.btn_cerca_source_partita.setToolTip(
            "Cerca una partita esistente da usare come sorgente")
        self.btn_cerca_source_partita.clicked.connect(
            self._cerca_partita_sorgente)
        source_partita_layout.addWidget(self.btn_cerca_source_partita, 0, 2)

        # Pulsante per caricare la partita dall'ID inserito nello SpinBox
        self.btn_load_source_partita_from_id = QPushButton(QApplication.style().standardIcon(QStyle.StandardPixmap.SP_ArrowRight), " Carica da ID")
        self.btn_load_source_partita_from_id.setToolTip("Carica i dettagli della partita usando l'ID inserito")
        self.btn_load_source_partita_from_id.clicked.connect(self._load_partita_sorgente_from_spinbox)
        source_partita_layout.addWidget(self.btn_load_source_partita_from_id, 0, 3)

        self.source_partita_info_label = QLabel(
            "Nessuna partita sorgente selezionata.")
        self.source_partita_info_label.setWordWrap(True)
        self.source_partita_info_label.setStyleSheet(
            "QLabel { padding: 5px; background-color: #e8f0fe; border: 1px solid #d0e0ff; border-radius: 3px; min-height: 2em; }")
        source_partita_layout.addWidget(
            self.source_partita_info_label, 1, 0, 1, 4)  # Span su 4 colonne
        main_layout.addWidget(source_partita_group)

        # --- 2. QTabWidget per le diverse operazioni ---
        self.operazioni_tabs = QTabWidget()
        main_layout.addWidget(self.operazioni_tabs, 1)

        # --- Creazione dei Tab ---
        self._crea_tab_duplica_partita()
        self._crea_tab_trasferisci_immobile()
        self._crea_tab_passaggio_proprieta()

        self.setLayout(main_layout)

    def _crea_tab_duplica_partita(self):
        duplica_widget = QWidget()
        duplica_main_layout = QVBoxLayout(duplica_widget)
        duplica_group = QGroupBox("Opzioni per la Duplicazione")
        
        # Usiamo un GridLayout per un layout più pulito
        duplica_form_layout = QGridLayout(duplica_group)
        duplica_form_layout.setSpacing(10)

        # Riga 0: Nuovo Numero e Nuovo Suffisso
        duplica_form_layout.addWidget(QLabel("Nuovo Numero Partita (*):"), 0, 0)
        self.nuovo_numero_partita_spinbox = QSpinBox()
        self.nuovo_numero_partita_spinbox.setRange(1, 9999999)
        duplica_form_layout.addWidget(self.nuovo_numero_partita_spinbox, 0, 1)

        # --- CAMPO SUFFISSO AGGIUNTO QUI ---
        duplica_form_layout.addWidget(QLabel("Suffisso Nuova Partita (opz.):"), 0, 2)
        self.duplica_suffisso_partita_edit = QLineEdit()
        self.duplica_suffisso_partita_edit.setPlaceholderText("Es. bis, A")
        self.duplica_suffisso_partita_edit.setMaxLength(20)
        duplica_form_layout.addWidget(self.duplica_suffisso_partita_edit, 0, 3)
        
        # Colonna "elastica" per non allargare i campi
        duplica_form_layout.setColumnStretch(4, 1)

        # Riga 1 e 2: Checkbox
        self.duplica_mantieni_poss_check = QCheckBox("Mantieni Possessori Originali nella Nuova Partita")
        self.duplica_mantieni_poss_check.setChecked(True)
        duplica_form_layout.addWidget(self.duplica_mantieni_poss_check, 1, 0, 1, 4) # Span su 4 colonne

        self.duplica_mantieni_imm_check = QCheckBox("Copia gli Immobili Originali nella Nuova Partita")
        self.duplica_mantieni_imm_check.setChecked(False)
        duplica_form_layout.addWidget(self.duplica_mantieni_imm_check, 2, 0, 1, 4)

        # Riga 3: Pulsante
        self.btn_esegui_duplicazione = QPushButton(QApplication.style().standardIcon(
            QStyle.StandardPixmap.SP_DialogApplyButton), " Esegui Duplicazione")
        self.btn_esegui_duplicazione.clicked.connect(self._esegui_duplicazione_partita)
        duplica_form_layout.addWidget(self.btn_esegui_duplicazione, 3, 0, 1, 4, Qt.AlignmentFlag.AlignRight)

        duplica_main_layout.addWidget(duplica_group)
        duplica_main_layout.addStretch(1)
        self.operazioni_tabs.addTab(duplica_widget, "Duplica Partita")

    def _crea_tab_trasferisci_immobile(self):
        transfer_widget = QWidget()
        transfer_main_layout = QVBoxLayout(transfer_widget)
        transfer_group = QGroupBox("Dettagli Trasferimento Immobile")
        transfer_form_layout = QFormLayout(transfer_group)
        transfer_form_layout.setSpacing(10)

        # ... (Tabella self.immobili_partita_sorgente_table e self.immobile_id_transfer_label come prima) ...
        transfer_form_layout.addRow(
            QLabel("Immobili nella Partita Sorgente (selezionarne uno):"))
        self.immobili_partita_sorgente_table = QTableWidget()
        # Rimuovere setColumnCount e setHorizontalHeaderLabels da qui se _carica_immobili_partita_sorgente lo fa dinamicamente
        self.immobili_partita_sorgente_table.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection)
        self.immobili_partita_sorgente_table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows)
        self.immobili_partita_sorgente_table.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers)
        self.immobili_partita_sorgente_table.setMinimumHeight(180)
        self.immobili_partita_sorgente_table.itemSelectionChanged.connect(
            self._immobile_sorgente_selezionato)
        transfer_form_layout.addRow(self.immobili_partita_sorgente_table)

        self.immobile_id_transfer_label = QLabel(
            "Nessun immobile selezionato dalla lista sottostante.")
        self.immobile_id_transfer_label.setStyleSheet(
            "font-style: italic; color: #555;")
        transfer_form_layout.addRow(self.immobile_id_transfer_label)

        # --- Modifiche per Partita Destinazione ---
        # Contenitore per spinbox e nuovo pulsante
        dest_partita_id_container = QWidget()
        dest_partita_id_layout = QHBoxLayout(dest_partita_id_container)
        dest_partita_id_layout.setContentsMargins(0, 0, 0, 0)
        dest_partita_id_layout.setSpacing(5)

        self.dest_partita_id_spinbox = QSpinBox()
        self.dest_partita_id_spinbox.setRange(1, 9999999)
        self.dest_partita_id_spinbox.setToolTip(
            "Inserisci l'ID della partita di destinazione o usa 'Cerca'")
        # Il '1' dà più stretch allo spinbox
        dest_partita_id_layout.addWidget(self.dest_partita_id_spinbox, 1)

        # NUOVO PULSANTE "Carica ID"
        self.btn_carica_dest_partita_da_id = QPushButton(
            "Carica ID")  # Testo breve, o icona SP_ArrowRight
        self.btn_carica_dest_partita_da_id.setToolTip(
            "Verifica e carica i dettagli della partita con l'ID inserito")
        self.btn_carica_dest_partita_da_id.clicked.connect(
            self._load_partita_destinazione_from_spinbox)
        dest_partita_id_layout.addWidget(self.btn_carica_dest_partita_da_id)

        self.btn_cerca_dest_partita = QPushButton(
            "Cerca...")  # Testo più breve
        self.btn_cerca_dest_partita.setToolTip(
            "Cerca una partita esistente da usare come destinazione")
        self.btn_cerca_dest_partita.clicked.connect(
            self._cerca_partita_destinazione)
        dest_partita_id_layout.addWidget(self.btn_cerca_dest_partita)

        transfer_form_layout.addRow(
            "ID Partita Destinazione (*):", dest_partita_id_container)
        # --- Fine Modifiche per Partita Destinazione ---

        self.dest_partita_info_label = QLabel(
            "Nessuna partita destinazione selezionata o verificata.")  # Testo iniziale modificato
        self.dest_partita_info_label.setStyleSheet(
            "font-style: italic; color: #555; padding: 3px; background-color: #E8F0FE; border: 1px solid #B0C4DE; border-radius: 3px;")
        self.dest_partita_info_label.setWordWrap(True)
        transfer_form_layout.addRow(self.dest_partita_info_label)

        self.transfer_registra_var_check = QCheckBox(
            "Registra Variazione Catastale per questo Trasferimento")
        self.transfer_registra_var_check.setChecked(
            True)  # Default a True potrebbe essere sensato
        transfer_form_layout.addRow(self.transfer_registra_var_check)

        self.btn_esegui_trasferimento = QPushButton(QApplication.style().standardIcon(
            QStyle.StandardPixmap.SP_DialogApplyButton), " Esegui Trasferimento Immobile")
        self.btn_esegui_trasferimento.clicked.connect(
            self._esegui_trasferimento_immobile)
        self.btn_esegui_trasferimento.setEnabled(False)  # Inizia disabilitato
        transfer_form_layout.addRow(self.btn_esegui_trasferimento)

        transfer_main_layout.addWidget(transfer_group)
        transfer_main_layout.addStretch(1)
        self.operazioni_tabs.addTab(transfer_widget, "Trasferisci Immobile")

        # Connetti i segnali per aggiornare lo stato del pulsante "Esegui Trasferimento"
        self.dest_partita_id_spinbox.valueChanged.connect(
            self._update_transfer_button_state_conditionally)
        self.immobili_partita_sorgente_table.itemSelectionChanged.connect(
            self._update_transfer_button_state_conditionally)

    def _crea_tab_passaggio_proprieta(self):
        # --- Tab Passaggio Proprietà (Voltura) ---
        passaggio_widget_main_container = QWidget()
        passaggio_tab_layout = QVBoxLayout(passaggio_widget_main_container)
        passaggio_scroll = QScrollArea(passaggio_widget_main_container)
        passaggio_scroll.setWidgetResizable(True)
        passaggio_scroll_content_widget = QWidget()
        passaggio_main_layout_scroll = QVBoxLayout(
            passaggio_scroll_content_widget)
        passaggio_main_layout_scroll.setSpacing(15)

        
        dati_atto_group = QGroupBox(
            "Dati Nuova Partita e Atto di Trasferimento")
        passaggio_form_layout = QFormLayout(dati_atto_group)
        passaggio_form_layout.setSpacing(10)

        # ... (campi esistenti prima di tipo atto/contratto) ...
        self.pp_nuova_partita_numero_spinbox = QSpinBox()
        self.pp_nuova_partita_numero_spinbox.setRange(1, 9999999)
        passaggio_form_layout.addRow(
            "Numero Nuova Partita (*):", self.pp_nuova_partita_numero_spinbox)
        self.pp_nuova_partita_comune_label = QLabel(
            "Il comune sarà lo stesso della partita sorgente.")
        passaggio_form_layout.addRow(
            "Comune Nuova Partita:", self.pp_nuova_partita_comune_label)
         # NUOVO CAMPO: Suffisso Partita per Passaggio Proprietà
        self.pp_suffisso_nuova_partita_edit = QLineEdit()
        self.pp_suffisso_nuova_partita_edit.setPlaceholderText("Es. bis, ter, A, B (opzionale)")
        self.pp_suffisso_nuova_partita_edit.setMaxLength(20)
        passaggio_form_layout.addRow("Suffisso Nuova Partita (opz.):", self.pp_suffisso_nuova_partita_edit) # AGGIUNTO
            

        self.pp_tipo_variazione_combo = QComboBox()
        tipi_variazione_validi = ['Vendita', 'Acquisto', 'Successione',
                                  'Variazione', 'Frazionamento', 'Divisione', 'Trasferimento', 'Altro']
        self.pp_tipo_variazione_combo.addItems(tipi_variazione_validi)
        if tipi_variazione_validi:
            self.pp_tipo_variazione_combo.setCurrentIndex(0)
        passaggio_form_layout.addRow(
            "Tipo Variazione (*):", self.pp_tipo_variazione_combo)

        self.pp_data_variazione_edit = QDateEdit(calendarPopup=True)
        self.pp_data_variazione_edit.setDisplayFormat("yyyy-MM-dd")
        self.pp_data_variazione_edit.setDate(QDate.currentDate())
        passaggio_form_layout.addRow(
            "Data Variazione (*):", self.pp_data_variazione_edit)
        
        # --- MODIFICA QUI: SOSTITUISCI QLineEdit con QComboBox ---
        self.pp_tipo_contratto_combo = QComboBox() # CAMBIATO IN COMBOBOX
        # Lista dei tipi di atto/contratto comuni
        tipi_atto_validi = [
            "Atto di Compravendita",
            "Dichiarazione di Successione",
            "Atto di Donazione",
            "Sentenza Giudiziale",
            "Atto di Divisione",
            "Verbale di Asta Pubblica",
            "Permuta",
            "Usucapione",
            "Altro Atto Pubblico",
            "Scrittura Privata"
        ]
        self.pp_tipo_contratto_combo.addItems(tipi_atto_validi)
        # Se vuoi un valore iniziale diverso o "Seleziona tipo..." puoi aggiungerlo
        self.pp_tipo_contratto_combo.insertItem(0, "Seleziona Tipo...") # Aggiunge un placeholder
        self.pp_tipo_contratto_combo.setCurrentIndex(0) # Seleziona il placeholder inizialmente
        
        passaggio_form_layout.addRow(
            "Tipo Atto/Contratto (*):", self.pp_tipo_contratto_combo) # USATO IL NUOVO WIDGET
        # --- FINE MODIFICA ---

        self.pp_data_contratto_edit = QDateEdit(calendarPopup=True)
        self.pp_data_contratto_edit.setDisplayFormat("yyyy-MM-dd")
        self.pp_data_contratto_edit.setDate(QDate.currentDate())
        passaggio_form_layout.addRow(
            "Data Atto/Contratto (*):", self.pp_data_contratto_edit)
        self.pp_notaio_edit = QLineEdit()
        passaggio_form_layout.addRow(
            "Notaio/Autorità Emittente:", self.pp_notaio_edit)
        self.pp_repertorio_edit = QLineEdit()
        passaggio_form_layout.addRow(
            "N. Repertorio/Protocollo:", self.pp_repertorio_edit)
        self.pp_note_variazione_edit = QTextEdit()
        self.pp_note_variazione_edit.setMinimumHeight(60)
        passaggio_form_layout.addRow(
            "Note Variazione:", self.pp_note_variazione_edit)
        passaggio_main_layout_scroll.addWidget(dati_atto_group)

        immobili_transfer_group_pp = QGroupBox(
            "Immobili da Includere nella Nuova Partita")
        immobili_transfer_layout_pp = QVBoxLayout(immobili_transfer_group_pp)
        self.pp_trasferisci_tutti_immobili_check = QCheckBox(
            "Includi TUTTI gli immobili dalla partita sorgente")
        self.pp_trasferisci_tutti_immobili_check.setChecked(True)
        self.pp_trasferisci_tutti_immobili_check.toggled.connect(
            self._toggle_selezione_immobili_pp)
        immobili_transfer_layout_pp.addWidget(
            self.pp_trasferisci_tutti_immobili_check)
        self.pp_immobili_da_selezionare_table = QTableWidget()
        self.pp_immobili_da_selezionare_table.setColumnCount(4)
        self.pp_immobili_da_selezionare_table.setHorizontalHeaderLabels(
            ["Sel.", "ID Imm.", "Natura", "Località"])
        self.pp_immobili_da_selezionare_table.setSelectionMode(
            QAbstractItemView.SelectionMode.NoSelection)
        self.pp_immobili_da_selezionare_table.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers)
        self.pp_immobili_da_selezionare_table.setMinimumHeight(150)
        self.pp_immobili_da_selezionare_table.setVisible(False)
        immobili_transfer_layout_pp.addWidget(
            self.pp_immobili_da_selezionare_table)
        passaggio_main_layout_scroll.addWidget(immobili_transfer_group_pp)

        nuovi_poss_group = QGroupBox("Nuovi Possessori per la Nuova Partita")
        nuovi_poss_layout = QVBoxLayout(nuovi_poss_group)
        self.pp_nuovi_possessori_table = QTableWidget()
        self.pp_nuovi_possessori_table.setColumnCount(4)
        self.pp_nuovi_possessori_table.setHorizontalHeaderLabels(
            ["ID Poss.", "Nome Completo", "Titolo (*)", "Quota"])
        self.pp_nuovi_possessori_table.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers)
        self.pp_nuovi_possessori_table.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection)
        self.pp_nuovi_possessori_table.horizontalHeader(
        ).setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.pp_nuovi_possessori_table.horizontalHeader().setStretchLastSection(True)
        self.pp_nuovi_possessori_table.setMinimumHeight(150)
        nuovi_poss_layout.addWidget(self.pp_nuovi_possessori_table)
        nuovi_poss_buttons_layout = QHBoxLayout()
        self.pp_btn_aggiungi_nuovo_possessore = QPushButton(
            # O QStyle.StandardPixmap.SP_FileLinkIcon o QStyle.StandardPixmap.SP_ToolBarAddButton
            QApplication.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogNewFolder),
            " Aggiungi Possessore..."
        )
        self.pp_btn_aggiungi_nuovo_possessore.setToolTip(
            "Aggiungi un nuovo possessore (o seleziona uno esistente) alla lista per la nuova partita")
        self.pp_btn_aggiungi_nuovo_possessore.clicked.connect(
            self._pp_aggiungi_nuovo_possessore)
        nuovi_poss_buttons_layout.addWidget(
            self.pp_btn_aggiungi_nuovo_possessore)

       # CORREZIONE ICONA QUI:
        self.pp_btn_rimuovi_nuovo_possessore = QPushButton(
            # O QStyle.StandardPixmap.SP_DialogDiscardButton
            QApplication.style().standardIcon(QStyle.StandardPixmap.SP_TrashIcon),
            " Rimuovi Selezionato"
        )
        self.pp_btn_rimuovi_nuovo_possessore = QPushButton(QApplication.style(
            # Esempio Icona
        ).standardIcon(QStyle.StandardPixmap.SP_TrashIcon), " Rimuovi Selezionato")
        self.pp_btn_rimuovi_nuovo_possessore.clicked.connect(
            self._pp_rimuovi_nuovo_possessore_selezionato)
        nuovi_poss_buttons_layout.addWidget(
            self.pp_btn_rimuovi_nuovo_possessore)
        nuovi_poss_buttons_layout.addStretch()
        nuovi_poss_layout.addLayout(nuovi_poss_buttons_layout)
        passaggio_main_layout_scroll.addWidget(nuovi_poss_group)

        self.pp_btn_esegui_passaggio = QPushButton(QApplication.style().standardIcon(
            QStyle.StandardPixmap.SP_DialogApplyButton), " Esegui Passaggio Proprietà")
        self.pp_btn_esegui_passaggio.clicked.connect(
            self._esegui_passaggio_proprieta)
        passaggio_main_layout_scroll.addWidget(
            self.pp_btn_esegui_passaggio, 0, Qt.AlignmentFlag.AlignRight)
        passaggio_main_layout_scroll.addStretch(1)

        passaggio_scroll.setWidget(passaggio_scroll_content_widget)
        passaggio_tab_layout.addWidget(passaggio_scroll)
        self.operazioni_tabs.addTab(
            passaggio_widget_main_container, "Passaggio Proprietà (Voltura)")

    # --- Metodi Helper e Handler ---

    def _load_partita_destinazione_from_spinbox(self):
        partita_id_dest = self.dest_partita_id_spinbox.value()
        self.dest_partita_info_label.setText("Verifica ID partita destinazione...")
        self.partita_destinazione_valida = False

        if partita_id_dest <= 0:
            self.dest_partita_info_label.setText("<font color='red'>ID partita destinazione non valido.</font>")
            self._update_transfer_button_state_conditionally()
            return

        partita_details = self.db_manager.get_partita_details(partita_id_dest)

        if partita_details:
            stato = partita_details.get('stato')
            comune = partita_details.get('comune_nome', 'N/D')
            numero = partita_details.get('numero_partita', 'N/D')
            # --- AGGIUNTA LETTURA SUFFISSO ---
            suffisso = partita_details.get('suffisso_partita')
            suffisso_display = f" (suffisso: {suffisso})" if suffisso else ""

            if self.selected_partita_id_source is not None and partita_id_dest == self.selected_partita_id_source:
                self.dest_partita_info_label.setText(f"<font color='red'>Errore: La destinazione non può essere uguale alla sorgente.</font>")
                self.partita_destinazione_valida = False
            elif stato != 'attiva':
                self.dest_partita_info_label.setText(f"<font color='red'>Errore: La partita N.{numero}{suffisso_display} non è attiva.</font>")
                self.partita_destinazione_valida = False
            else:
                self.dest_partita_info_label.setText(f"Destinazione: N. {numero}{suffisso_display} (Comune: {comune}, ID: {partita_id_dest})")
                self.partita_destinazione_valida = True
        else:
            self.dest_partita_info_label.setText(f"<font color='red'>Partita destinazione con ID {partita_id_dest} non trovata.</font>")
            self.partita_destinazione_valida = False

        self._update_transfer_button_state_conditionally()

    def _cerca_partita_destinazione(self):
        dialog = PartitaSearchDialog(self.db_manager, self)
        if dialog.exec() == QDialog.DialogCode.Accepted and dialog.selected_partita_id:
            selected_id = dialog.selected_partita_id
            self.dest_partita_id_spinbox.setValue(
                selected_id)  # Imposta lo spinbox
            # Chiama la logica di caricamento e validazione
            self._load_partita_destinazione_from_spinbox()
        # else: Non fare nulla se l'utente annulla, la label non cambia o è già impostata
        # self._update_transfer_button_state_conditionally() # _load_partita_destinazione_from_spinbox lo fa già

    def _update_transfer_button_state_conditionally(self):
        """Abilita il pulsante 'Esegui Trasferimento' solo se tutte le condizioni sono soddisfatte."""
        is_enabled = False
        immobile_selezionato = self.selected_immobile_id_transfer is not None
        # Verifica solo che un ID sia nello spinbox
        id_partita_dest_inserito = self.dest_partita_id_spinbox.value() > 0

        partita_dest_diversa_da_sorgente = True
        if self.selected_partita_id_source is not None and id_partita_dest_inserito:
            partita_dest_diversa_da_sorgente = (
                self.dest_partita_id_spinbox.value() != self.selected_partita_id_source)

        if immobile_selezionato and id_partita_dest_inserito and \
           self.partita_destinazione_valida and partita_dest_diversa_da_sorgente:
            is_enabled = True

        self.btn_esegui_trasferimento.setEnabled(is_enabled)

        # Aggiorna tooltip per guidare l'utente
        if not is_enabled:
            reasons = []
            if not immobile_selezionato:
                reasons.append(
                    "selezionare un immobile dalla tabella sorgente")
            if not id_partita_dest_inserito:
                reasons.append(
                    "inserire un ID per la partita destinazione e caricarne i dettagli")
            elif not self.partita_destinazione_valida:
                reasons.append(
                    "la partita destinazione non è valida o non è attiva (controllare messaggio sopra)")
            if not partita_dest_diversa_da_sorgente and id_partita_dest_inserito:
                reasons.append(
                    "la partita destinazione deve essere diversa dalla sorgente")

            if reasons:
                self.btn_esegui_trasferimento.setToolTip(
                    "Per abilitare: " + " e ".join(reasons) + ".")
            # Caso in cui tutti i singoli check passano ma la combinazione logica di is_enabled è False (improbabile con la logica sopra)
            else:
                self.btn_esegui_trasferimento.setToolTip(
                    "Verificare tutti i campi per il trasferimento.")
        else:
            self.btn_esegui_trasferimento.setToolTip(
                "Esegue il trasferimento dell'immobile selezionato alla partita destinazione.")

    # Modifichi anche _immobile_sorgente_selezionato per chiamare l'aggiornamento del pulsante

    def _immobile_sorgente_selezionato(self):
        # ... (logica esistente per impostare self.selected_immobile_id_transfer e self.immobile_id_transfer_label)
        selected_rows = self.immobili_partita_sorgente_table.selectionModel().selectedRows()
        if not selected_rows:
            self.selected_immobile_id_transfer = None
            self.immobile_id_transfer_label.setText(
                "Nessun immobile selezionato dalla lista.")
        else:
            row = selected_rows[0].row()
            # ID Imm.
            id_item = self.immobili_partita_sorgente_table.item(row, 0)
            natura_item = self.immobili_partita_sorgente_table.item(
                row, 1)  # Natura

            if id_item and id_item.text().isdigit():
                self.selected_immobile_id_transfer = int(id_item.text())
                natura_text = natura_item.text() if natura_item else "N/D"
                self.immobile_id_transfer_label.setText(
                    f"Immobile da trasferire: ID {self.selected_immobile_id_transfer} (Natura: {natura_text})")
            else:
                self.selected_immobile_id_transfer = None
                self.immobile_id_transfer_label.setText(
                    "Selezione immobile non valida.")

        self._update_transfer_button_state_conditionally()

    def _cerca_partita_sorgente(self):
        """Apre il dialogo per cercare una partita sorgente."""
        # ... (suo codice esistente)
        dialog = PartitaSearchDialog(self.db_manager, self)
        if dialog.exec() == QDialog.DialogCode.Accepted and dialog.selected_partita_id:
            self.source_partita_id_spinbox.setValue(
                dialog.selected_partita_id)  # Imposta lo spinbox
            self.selected_partita_id_source = dialog.selected_partita_id   # Imposta l'ID
            self._aggiorna_info_partita_sorgente()  # Carica i dettagli
        
            if not self.selected_partita_id_source:  # Resetta solo se non c'era già una selezione
                self.source_partita_info_label.setText(
                    "Nessuna partita sorgente selezionata.")
                self.selected_partita_comune_id_source = None
                self.selected_partita_comune_nome_source = None
                if hasattr(self, 'immobili_partita_sorgente_table'):
                    self.immobili_partita_sorgente_table.setRowCount(0)
                if hasattr(self, 'pp_immobili_da_selezionare_table'):
                    self.pp_immobili_da_selezionare_table.setRowCount(0)
                if hasattr(self, 'pp_nuova_partita_comune_label'):
                    self.pp_nuova_partita_comune_label.setText(
                        "Il comune sarà lo stesso della partita sorgente.")

    def _aggiorna_info_partita_sorgente(self):
        """
        Recupera e visualizza i dettagli della partita sorgente (selected_partita_id_source)
        e popola le UI dipendenti (es. tabella immobili per trasferimento).
        """
        # Pulisci le UI dipendenti prima di caricarne di nuove o se non c'è sorgente
        if hasattr(self, 'immobili_partita_sorgente_table'):
            self.immobili_partita_sorgente_table.setRowCount(0)
            if hasattr(self, 'selected_immobile_id_transfer'):
                self.selected_immobile_id_transfer = None
            if hasattr(self, 'immobile_id_transfer_label'):
                self.immobile_id_transfer_label.setText(
                    "Nessun immobile selezionato.")

        if hasattr(self, 'pp_immobili_da_selezionare_table'):  # Per il tab Passaggio Proprietà
            self.pp_immobili_da_selezionare_table.setRowCount(0)

        if hasattr(self, 'pp_nuova_partita_comune_label'):
            self.pp_nuova_partita_comune_label.setText(
                "Il comune sarà lo stesso della partita sorgente.")

        if self.selected_partita_id_source and self.selected_partita_id_source > 0:
            partita_details = self.db_manager.get_partita_details(
                self.selected_partita_id_source)
            if partita_details:
                self.selected_partita_comune_id_source = partita_details.get(
                    'comune_id')  # Salva per uso futuro
                self.selected_partita_comune_nome_source = partita_details.get(
                    'comune_nome', 'N/D')

                self.source_partita_info_label.setText(
                    f"Partita Sorgente: N. {partita_details.get('numero_partita')} "
                    f"(Comune: {self.selected_partita_comune_nome_source} [ID: {self.selected_partita_comune_id_source}], Partita ID: {self.selected_partita_id_source})"
                )
                immobili = partita_details.get('immobili', [])

                # Popola la tabella immobili nel tab "Trasferisci Immobile"
                if hasattr(self, '_carica_immobili_partita_sorgente'):
                    self._carica_immobili_partita_sorgente(immobili)

                # Popola la tabella immobili nel tab "Passaggio Proprietà"
                if hasattr(self, '_pp_carica_immobili_per_selezione'):
                    self._pp_carica_immobili_per_selezione(immobili)

                # Aggiorna etichetta comune nel tab "Passaggio Proprietà"
                if hasattr(self, 'pp_nuova_partita_comune_label') and self.selected_partita_comune_nome_source and self.selected_partita_comune_id_source:
                    self.pp_nuova_partita_comune_label.setText(
                        f"{self.selected_partita_comune_nome_source} (ID: {self.selected_partita_comune_id_source})"
                    )
            else:  # Partita non trovata
                self.source_partita_info_label.setText(
                    f"Partita sorgente con ID {self.selected_partita_id_source} non trovata o errore nel recupero dettagli.")
                self.selected_partita_id_source = None  # Resetta se non trovata
                self.selected_partita_comune_id_source = None
                self.selected_partita_comune_nome_source = None
        else:  # Nessun ID sorgente valido
            self.source_partita_info_label.setText(
                "Nessuna partita sorgente selezionata o ID non valido.")
            self.selected_partita_id_source = None
            self.selected_partita_comune_id_source = None
            self.selected_partita_comune_nome_source = None

        # Aggiorna lo stato dei pulsanti che dipendono dalla selezione della partita sorgente/destinazione
        if hasattr(self, '_update_transfer_button_state_conditionally'):
            self._update_transfer_button_state_conditionally()
        # Aggiungere chiamate simili per aggiornare lo stato dei pulsanti negli altri sotto-tab se necessario

    def _esegui_duplicazione_partita(self):
        self.logger.info("Avvio _esegui_duplicazione_partita.")

        if self.selected_partita_id_source is None:
            QMessageBox.warning(self, "Selezione Mancante", "Selezionare una partita sorgente prima di duplicare.")
            return
        if self.selected_partita_comune_id_source is None:
            QMessageBox.warning(self, "Errore Interno", "Comune della partita sorgente non determinato.")
            return

        nuovo_numero = self.nuovo_numero_partita_spinbox.value()
        # --- LETTURA VALORE SUFFISSO ---
        nuovo_suffisso = self.duplica_suffisso_partita_edit.text().strip() or None

        if nuovo_numero <= 0:
            QMessageBox.warning(self, "Dati Non Validi", "Il nuovo numero di partita deve essere un valore positivo.")
            return

        # --- VERIFICA UNICITÀ CON SUFFISSO ---
        try:
            existing_partita = self.db_manager.search_partite(
                comune_id=self.selected_partita_comune_id_source,
                numero_partita=nuovo_numero,
                suffisso_partita=nuovo_suffisso
            )
            if existing_partita:
                suffisso_display = f" (suffisso: {nuovo_suffisso})" if nuovo_suffisso else ""
                QMessageBox.warning(self, "Errore Duplicazione",
                                    f"Esiste già una partita con il numero {nuovo_numero}{suffisso_display} "
                                    f"nel comune '{self.selected_partita_comune_nome_source}'.")
                return
        except DBMError as e:
            QMessageBox.critical(self, "Errore Verifica Partita", f"Errore durante la verifica del numero partita:\n{str(e)}")
            return
        
        mant_poss = self.duplica_mantieni_poss_check.isChecked()
        mant_imm = self.duplica_mantieni_imm_check.isChecked()
        
        try:
            # --- CHIAMATA AL DB MANAGER CON SUFFISSO ---
            success = self.db_manager.duplicate_partita(
                partita_id_originale=self.selected_partita_id_source,
                nuovo_numero_partita=nuovo_numero,
                mantenere_possessori=mant_poss,
                mantenere_immobili=mant_imm,
                nuovo_suffisso=nuovo_suffisso
            )
            
            if success:
                suffisso_display = f" (suffisso: {nuovo_suffisso})" if nuovo_suffisso else ""
                _show_status_message(
                    f"Partita ID {self.selected_partita_id_source} duplicata in nuova partita "
                    f"N. {nuovo_numero}{suffisso_display}.", 5000)
                self.nuovo_numero_partita_spinbox.setValue(1)
                self.duplica_suffisso_partita_edit.clear()
            else:
                QMessageBox.critical(self, "Errore Operazione", "La duplicazione della partita non è stata completata.")
        except DBMError as e:
            QMessageBox.critical(self, "Errore Duplicazione", f"Impossibile duplicare la partita:\n{str(e)}")
        except Exception as e_gen:
            self.logger.critical(f"Errore imprevisto durante la duplicazione: {e_gen}", exc_info=True)
            QMessageBox.critical(self, "Errore Imprevisto", f"Errore di sistema:\n{str(e_gen)}")


    def _carica_immobili_partita_sorgente(self, immobili_data: List[Dict[str, Any]]):
        table = self.immobili_partita_sorgente_table

        # --- NUOVE INTESTAZIONI ---
        nuove_colonne = ["ID Imm.", "Natura",
                         "Classificazione", "Consistenza", "Località Completa"]
        table.setColumnCount(len(nuove_colonne))
        table.setHorizontalHeaderLabels(nuove_colonne)
        # --- FINE NUOVE INTESTAZIONI ---

        table.setRowCount(0)
        table.setSortingEnabled(False)
        self.selected_immobile_id_transfer = None
        self.immobile_id_transfer_label.setText(
            "Nessun immobile selezionato dalla lista sottostante.")

        if immobili_data:
            table.setRowCount(len(immobili_data))
            for row, immobile in enumerate(immobili_data):
                col = 0
                table.setItem(row, col, QTableWidgetItem(
                    str(immobile.get('id', 'N/D'))))
                col += 1
                table.setItem(row, col, QTableWidgetItem(
                    immobile.get('natura', 'N/D')))
                col += 1

                # --- NUOVE COLONNE ---
                table.setItem(row, col, QTableWidgetItem(
                    immobile.get('classificazione', 'N/D')))
                col += 1
                table.setItem(row, col, QTableWidgetItem(
                    immobile.get('consistenza', 'N/D')))
                col += 1
                # --- FINE NUOVE COLONNE ---

                loc_nome = immobile.get('localita_nome', '')
                loc_tipo = immobile.get('localita_tipo', '')
                loc_civico = immobile.get('civico', '')
                loc_text = loc_nome
                if loc_tipo:
                    loc_text += f" ({loc_tipo})"
                if loc_civico:  # Civico potrebbe essere 0 o stringa vuota se non presente
                    loc_text += f", civ. {loc_civico}"
                table.setItem(row, col, QTableWidgetItem(loc_text.strip()))
                col += 1

            table.resizeColumnsToContents()  # Adatta dopo aver popolato
            # O imposta larghezze specifiche per una migliore leggibilità
            # table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents) # ID
            # table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Interactive) # Natura
            # table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch) # Località
        else:
            table.setRowCount(1)
            no_imm_item = QTableWidgetItem(
                "Nessun immobile associato a questa partita sorgente.")
            no_imm_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            table.setItem(0, 0, no_imm_item)
            # Occupa tutte le colonne
            table.setSpan(0, 0, 1, table.columnCount())

        table.setSortingEnabled(True)

    def _esegui_trasferimento_immobile(self):
        if self.selected_immobile_id_transfer is None:
            QMessageBox.warning(self, "Selezione Mancante",
                                "Selezionare un immobile dalla partita sorgente da trasferire.")
            return
        id_partita_dest = self.dest_partita_id_spinbox.value()
        if id_partita_dest <= 0:
            QMessageBox.warning(
                self, "Dati Non Validi", "Selezionare o inserire un ID partita di destinazione valido.")
            return
        if self.selected_partita_id_source is not None and id_partita_dest == self.selected_partita_id_source:
            QMessageBox.warning(self, "Operazione Non Valida",
                                "La partita di destinazione non può essere uguale alla partita sorgente.")
            return

        registra_var = self.transfer_registra_var_check.isChecked()
        try:
            success = self.db_manager.transfer_immobile(
                self.selected_immobile_id_transfer, id_partita_dest, registra_var
            )
            if success:
                _show_status_message(
                    f"Immobile ID {self.selected_immobile_id_transfer} trasferito "
                    f"alla partita ID {id_partita_dest}.", 5000)
                self._aggiorna_info_partita_sorgente()  # Ricarica immobili sorgente
                self.dest_partita_id_spinbox.setValue(
                    self.dest_partita_id_spinbox.minimum())
                self.dest_partita_info_label.setText(
                    "Nessuna partita destinazione selezionata.")
                self.transfer_registra_var_check.setChecked(False)
        except DBMError as e:
            QMessageBox.critical(self, "Errore Trasferimento",
                                 f"Errore durante il trasferimento dell'immobile:\n{str(e)}")
        except Exception as e_gen:
            logging.getLogger("CatastoGUI").critical(
                f"Errore imprevisto trasferimento immobile: {e_gen}", exc_info=True)
            QMessageBox.critical(self, "Errore Imprevisto",
                                 f"Errore:\n{type(e_gen).__name__}: {str(e_gen)}")

    def _toggle_selezione_immobili_pp(self, checked: bool):
        if hasattr(self, 'pp_immobili_da_selezionare_table'):
            self.pp_immobili_da_selezionare_table.setVisible(not checked)
            if checked and hasattr(self, '_pp_pulisci_selezione_immobili_specifici'):
                self._pp_pulisci_selezione_immobili_specifici()

    def _pp_pulisci_selezione_immobili_specifici(self):
        if hasattr(self, 'pp_immobili_da_selezionare_table'):
            table = self.pp_immobili_da_selezionare_table
            for row in range(table.rowCount()):
                cell_widget = table.cellWidget(row, 0)
                if isinstance(cell_widget, QCheckBox):
                    cell_widget.setChecked(False)

    def _pp_carica_immobili_per_selezione(self, immobili_data: List[Dict[str, Any]]):
        if not hasattr(self, 'pp_immobili_da_selezionare_table'):
            logging.getLogger("CatastoGUI").error(
                "Tabella 'pp_immobili_da_selezionare_table' non inizializzata.")
            return
        table = self.pp_immobili_da_selezionare_table
        table.setRowCount(0)
        table.setSortingEnabled(False)
        if immobili_data:
            table.setRowCount(len(immobili_data))
            for row, immobile in enumerate(immobili_data):
                chk = QCheckBox()
                chk.setProperty("immobile_id", immobile.get('id'))
                table.setCellWidget(row, 0, chk)
                id_i = QTableWidgetItem(str(immobile.get('id', 'N/D')))
                id_i.setFlags(id_i.flags() & ~Qt.ItemFlag.ItemIsEditable)
                table.setItem(row, 1, id_i)
                nat_i = QTableWidgetItem(immobile.get('natura', 'N/D'))
                nat_i.setFlags(nat_i.flags() & ~Qt.ItemFlag.ItemIsEditable)
                table.setItem(row, 2, nat_i)
                loc_t = f"{immobile.get('localita_nome', '')} {immobile.get('civico', '')}".strip(
                )
                loc_i = QTableWidgetItem(loc_t)
                loc_i.setFlags(loc_i.flags() & ~Qt.ItemFlag.ItemIsEditable)
                table.setItem(row, 3, loc_i)
            # Configurazione resize mode per le colonne
            table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)  # Checkbox
            table.setColumnWidth(0, 35)
            table.horizontalHeader().setSectionResizeMode(
                1, QHeaderView.ResizeMode.ResizeToContents)  # ID
            table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Interactive)  # Natura
            table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Interactive)  # Località
            table.horizontalHeader().setStretchLastSection(True)
        else:
            table.setRowCount(1)
            msg_item = QTableWidgetItem(
                "Nessun immobile disponibile nella partita sorgente per la selezione.")
            msg_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            table.setItem(0, 0, msg_item)
            table.setSpan(0, 0, 1, table.columnCount())
        table.setSortingEnabled(True)

    def _pp_aggiungi_nuovo_possessore(self):
        if not self.selected_partita_comune_id_source:
            QMessageBox.warning(
                self, "Comune Mancante", "Selezionare una partita sorgente per determinare il comune di riferimento dei nuovi possessori.")
            return
        dialog_sel_poss = PossessoreSelectionDialog(
            self.db_manager, self.selected_partita_comune_id_source, self)
        dialog_sel_poss.setWindowTitle(
            "Seleziona o Crea Nuovo Possessore per Nuova Partita")
        possessore_info_completa_sel = None
        if dialog_sel_poss.exec() == QDialog.DialogCode.Accepted:
            if hasattr(dialog_sel_poss, 'selected_possessore') and dialog_sel_poss.selected_possessore:
                poss_id_sel = dialog_sel_poss.selected_possessore.get('id')
                if poss_id_sel:
                    dettagli_poss_db = self.db_manager.get_possessore_full_details(
                        poss_id_sel)
                    if dettagli_poss_db:
                        possessore_info_completa_sel = dettagli_poss_db
                    else:
                        QMessageBox.warning(
                            self, "Errore", f"Impossibile recuperare dettagli per possessore ID {poss_id_sel}.")
                        return
                else:
                    QMessageBox.warning(
                        self, "Errore", "Nessun ID possessore valido dalla selezione.")
                    return
            else:
                logging.getLogger("CatastoGUI").warning(
                    "PossessoreSelectionDialog non ha restituito 'selected_possessore'.")
                return
        else:
            logging.getLogger("CatastoGUI").info(
                "Aggiunta possessore per PP annullata (selezione/creazione).")
            return

        if not possessore_info_completa_sel or possessore_info_completa_sel.get('id') is None:
            QMessageBox.warning(
                self, "Errore", "Dati del possessore non validi.")
            return

        dettagli_leg = DettagliLegamePossessoreDialog.get_details_for_new_legame(
            nome_possessore=possessore_info_completa_sel.get(
                "nome_completo", "N/D"),
            tipo_partita_attuale='principale', parent=self
        )
        if dettagli_leg:
            self._pp_temp_nuovi_possessori.append({
                "possessore_id": possessore_info_completa_sel.get("id"),
                "nome_completo": possessore_info_completa_sel.get("nome_completo"),
                "cognome_nome": possessore_info_completa_sel.get("cognome_nome"),
                "paternita": possessore_info_completa_sel.get("paternita"),
                "comune_riferimento_id": possessore_info_completa_sel.get("comune_riferimento_id"),
                "attivo": possessore_info_completa_sel.get("attivo", True),
                "titolo": dettagli_leg["titolo"],
                "quota": dettagli_leg["quota"]
            })
            self._pp_aggiorna_tabella_nuovi_possessori()
        else:
            logging.getLogger("CatastoGUI").info(
                "Aggiunta dettagli legame per PP annullata.")

    def _pp_rimuovi_nuovo_possessore_selezionato(self):
        selected_rows = self.pp_nuovi_possessori_table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(
                self, "Nessuna Selezione", "Seleziona un possessore dalla lista dei nuovi possessori da rimuovere.")
            return
        row_to_remove = selected_rows[0].row()
        if 0 <= row_to_remove < len(self._pp_temp_nuovi_possessori):
            del self._pp_temp_nuovi_possessori[row_to_remove]
            self._pp_aggiorna_tabella_nuovi_possessori()

    def _pp_aggiorna_tabella_nuovi_possessori(self):
        table = self.pp_nuovi_possessori_table
        table.setRowCount(0)
        table.setSortingEnabled(False)
        if self._pp_temp_nuovi_possessori:
            table.setRowCount(len(self._pp_temp_nuovi_possessori))
            for r, pd in enumerate(self._pp_temp_nuovi_possessori):
                table.setItem(r, 0, QTableWidgetItem(
                    str(pd.get("possessore_id"))))
                table.setItem(r, 1, QTableWidgetItem(pd.get("nome_completo")))
                table.setItem(r, 2, QTableWidgetItem(pd.get("titolo")))
                table.setItem(r, 3, QTableWidgetItem(pd.get("quota", "")))
            table.resizeColumnsToContents()
        table.setSortingEnabled(True)

    def _load_partita_sorgente_from_spinbox(self):
        """
        Carica i dettagli della partita sorgente usando l'ID
        inserito nello QSpinBox self.source_partita_id_spinbox.
        """
        partita_id_val = self.source_partita_id_spinbox.value()
        if partita_id_val > 0:
            self.selected_partita_id_source = partita_id_val  # Imposta l'ID della sorgente
            # Chiamata al metodo esistente che carica e visualizza i dettagli della partita sorgente
            # e popola anche la tabella degli immobili nel tab "Trasferisci Immobile"
            self._aggiorna_info_partita_sorgente()
        else:
            QMessageBox.warning(
                self, "ID Non Valido", "Inserire un ID partita sorgente valido (maggiore di zero).")
            # Potrebbe voler resettare le info se l'ID non è valido
            self.selected_partita_id_source = None
            # Chiamata per pulire le label e le tabelle
            self._aggiorna_info_partita_sorgente()

    # --- MODIFICA IN _esegui_passaggio_proprieta PER LEGGERE DA COMBOBOX ---
    def _esegui_passaggio_proprieta(self):
        self.logger.info("Avvio _esegui_passaggio_proprieta.")

        # --- 1. Validazione Dati Partita Sorgente ---
        if self.selected_partita_id_source is None or self.selected_partita_comune_id_source is None:
            QMessageBox.warning(self, "Selezione Mancante", "Selezionare una partita sorgente valida prima di procedere.")
            return

        # --- 2. Validazione Dati Nuova Partita ---
        nuova_part_num = self.pp_nuova_partita_numero_spinbox.value()
        suffisso_nuova_partita = self.pp_suffisso_nuova_partita_edit.text().strip() or None # Leggi il suffisso
        if nuova_part_num <= 0:
            QMessageBox.warning(self, "Dati Mancanti", "Il 'Numero Nuova Partita' non può essere zero o negativo.")
            self.pp_nuova_partita_numero_spinbox.setFocus()
            self.pp_nuova_partita_numero_spinbox.selectAll()
            return

        try:
                # La ricerca di esistenza deve ora usare anche il suffisso
                existing_partita_check = self.db_manager.search_partite(
                    comune_id=self.selected_partita_comune_id_source,
                    numero_partita=nuova_part_num,
                    suffisso_partita=suffisso_nuova_partita # PASSA IL SUFFISSO ALLA RICERCA
                )
                if existing_partita_check:
                    QMessageBox.warning(self, "Errore Creazione Partita",
                                        f"Esiste già una partita con il numero {nuova_part_num} "
                                        f"{('('+suffisso_nuova_partita+')' if suffisso_nuova_partita else '')} "
                                        f"nel comune '{self.selected_partita_comune_nome_source}'. Scegliere un numero/suffisso diverso.")
                    self.pp_nuova_partita_numero_spinbox.setFocus()
                    return
        except DBMError as e:
            self.logger.error(f"Errore DB durante la verifica di esistenza della nuova partita: {e}", exc_info=True)
            QMessageBox.critical(self, "Errore Verifica Partita",
                                 f"Errore durante la verifica di disponibilità del numero partita:\n{str(e)}")
            return
        except Exception as e:
            self.logger.critical(f"Errore imprevisto durante la verifica di esistenza della nuova partita: {e}", exc_info=True)
            QMessageBox.critical(self, "Errore Imprevisto", f"Si è verificato un errore inatteso durante la verifica del numero partita:\n{str(e)}")
            return


        # --- 3. Validazione Dati Atto/Contratto ---
        tipo_variazione = self.pp_tipo_variazione_combo.currentText()
        if not tipo_variazione or tipo_variazione.strip() == "Seleziona Tipo...": # Assicurati che non sia il placeholder
            QMessageBox.warning(self, "Dati Atto Mancanti", "Selezionare un 'Tipo Variazione' valido.")
            self.pp_tipo_variazione_combo.setFocus()
            return

        data_variazione_q = self.pp_data_variazione_edit.date()
        if not data_variazione_q.isValid():
            QMessageBox.warning(self, "Dati Atto Mancanti", "La 'Data Variazione' è obbligatoria e deve essere valida.")
            self.pp_data_variazione_edit.setFocus()
            return
        data_variazione = data_variazione_q.toPyDate()

        # Leggi il tipo di contratto dalla QComboBox e validalo
        tipo_contratto = self.pp_tipo_contratto_combo.currentText()
        if tipo_contratto == "Seleziona Tipo..." or not tipo_contratto.strip():
            QMessageBox.warning(self, "Dati Atto Mancanti", "Selezionare un 'Tipo Atto/Contratto' valido.")
            self.pp_tipo_contratto_combo.setFocus()
            return
        
        data_contratto_q = self.pp_data_contratto_edit.date()
        if not data_contratto_q.isValid():
            QMessageBox.warning(self, "Dati Atto Mancanti", "La 'Data Atto/Contratto' è obbligatoria e deve essere valida.")
            self.pp_data_contratto_edit.setFocus()
            return
        data_contratto = data_contratto_q.toPyDate()

        # Altri campi opzionali
        notaio = self.pp_notaio_edit.text().strip() or None
        repertorio = self.pp_repertorio_edit.text().strip() or None
        note_v = self.pp_note_variazione_edit.toPlainText().strip() or None
        suffisso_nuova_partita=suffisso_nuova_partita # AGGIUNTO

        # --- 4. Validazione Nuovi Possessori ---
        if not self._pp_temp_nuovi_possessori:
            QMessageBox.warning(self, "Possessori Mancanti", "Aggiungere almeno un nuovo possessore per la nuova partita.")
            # Puoi anche impostare il focus al pulsante "Aggiungi Possessore" qui
            return
        
        # Prepara la lista di possessori per il DB, includendo i dettagli del legame
        lista_possessori_per_db = []
        for poss_data_ui in self._pp_temp_nuovi_possessori:
            # Assicurati che tutte le chiavi necessarie alla procedura SQL siano presenti nel dizionario
            lista_possessori_per_db.append({
                "possessore_id": poss_data_ui.get("possessore_id"),
                "nome_completo": poss_data_ui.get("nome_completo"),
                "cognome_nome": poss_data_ui.get("cognome_nome"), # Potrebbe non essere sempre presente o obbligatorio
                "paternita": poss_data_ui.get("paternita"),       # Potrebbe non essere sempre presente o obbligatorio
                "comune_id": poss_data_ui.get("comune_riferimento_id"), # ID del comune di riferimento del possessore
                "attivo": poss_data_ui.get("attivo", True),
                "titolo": poss_data_ui.get("titolo"),
                "quota": poss_data_ui.get("quota")
            })
        self.logger.debug(f"PP: Lista possessori inviata al DBManager: {lista_possessori_per_db}")


        # --- 5. Validazione e Selezione Immobili da Trasferire ---
        imm_ids_trasf: List[int] = []
        if self.pp_trasferisci_tutti_immobili_check.isChecked():
            # Se la checkbox "Includi TUTTI" è spuntata, raccogli tutti gli ID immobili dal table model
            source_table_immobili = self.immobili_partita_sorgente_table # Questa tabella è popolata con gli immobili della sorgente
            for r in range(source_table_immobili.rowCount()):
                id_itm_widget = source_table_immobili.item(r, 0) # Assumendo ID Imm. è nella prima colonna
                if id_itm_widget and id_itm_widget.text().isdigit():
                    imm_ids_trasf.append(int(id_itm_widget.text()))
            
            if not imm_ids_trasf:
                QMessageBox.warning(self, "Immobili Mancanti", "La partita sorgente non contiene immobili da trasferire, ma 'Includi TUTTI' è selezionato.")
                return

        else:
            # Altrimenti, raccogli solo gli ID degli immobili selezionati individualmente nella tabella
            sel_tbl_imm = self.pp_immobili_da_selezionare_table
            for r in range(sel_tbl_imm.rowCount()):
                chk_widget = sel_tbl_imm.cellWidget(r, 0) # La checkbox è nella colonna 0
                if isinstance(chk_widget, QCheckBox) and chk_widget.isChecked():
                    id_itm_widget = sel_tbl_imm.item(r, 1) # L'ID immobile è nella colonna 1 (dopo la checkbox)
                    if id_itm_widget and id_itm_widget.text().isdigit():
                        imm_ids_trasf.append(int(id_itm_widget.text()))
            
            if not imm_ids_trasf:
                QMessageBox.warning(self, "Immobili Mancanti", "Nessun immobile è stato selezionato per il trasferimento. Selezionare almeno un immobile o spuntare 'Includi TUTTI'.")
                return

        self.logger.debug(f"PP: Immobili da trasferire IDs: {imm_ids_trasf}")

        # --- 6. Esecuzione della Procedura nel DBManager ---
        try:
            success = self.db_manager.registra_passaggio_proprieta(
                partita_origine_id=self.selected_partita_id_source,
                comune_id_nuova_partita=self.selected_partita_comune_id_source,
                numero_nuova_partita=nuova_part_num,
                tipo_variazione=tipo_variazione,
                data_variazione=data_variazione,
                tipo_contratto=tipo_contratto,
                data_contratto=data_contratto,
                notaio=notaio,
                repertorio=repertorio,
                nuovi_possessori_list=lista_possessori_per_db,
                immobili_da_trasferire_ids=imm_ids_trasf if imm_ids_trasf else None, # Passa None se lista vuota
                note_variazione=note_v
            )

            # --- 7. Gestione del Successo o Fallimento ---
            if success:
                _show_status_message(
                    "Passaggio di proprietà registrato: nuova partita creata e immobili trasferiti.", 5000)
                self.logger.info("Passaggio di proprietà eseguito con successo.")
                self._pulisci_campi_passaggio_proprieta() # Chiama un metodo per pulire i campi
                # Ricarica i dati della partita sorgente per riflettere i cambiamenti (es. immobili rimossi)
                self._aggiorna_info_partita_sorgente()
            else:
                # Questo blocco else dovrebbe essere raggiunto solo se il db_manager restituisce False
                # senza sollevare eccezioni, ma le eccezioni sono preferibili.
                self.logger.error("registra_passaggio_proprieta ha restituito False senza eccezioni.")
                QMessageBox.critical(self, "Errore Operazione", "Il passaggio di proprietà non è stato completato (errore sconosciuto). Controllare i log.")

        except (DBUniqueConstraintError, DBDataError, DBMError) as e:
            self.logger.error(f"Errore DB durante la registrazione del passaggio di proprietà: {e}", exc_info=True)
            QMessageBox.critical(self, "Errore Operazione",
                                 f"Impossibile registrare il passaggio di proprietà a causa di un errore nel database:\n{str(e)}")
        except Exception as e_gen:
            self.logger.critical(f"Errore imprevisto durante l'esecuzione del passaggio di proprietà: {e_gen}", exc_info=True)
            QMessageBox.critical(self, "Errore Critico Imprevisto",
                                 f"Si è verificato un errore di sistema inatteso durante l'operazione:\n{type(e_gen).__name__}: {str(e_gen)}")

    def _pulisci_campi_passaggio_proprieta(self):
        self.pp_nuova_partita_numero_spinbox.setValue(self.pp_nuova_partita_numero_spinbox.minimum())
        self.pp_tipo_variazione_combo.setCurrentIndex(0)
        self.pp_data_variazione_edit.setDate(QDate.currentDate())
        self.pp_tipo_contratto_combo.setCurrentIndex(0) # Resetta la ComboBox
        self.pp_data_contratto_edit.setDate(QDate.currentDate())
        self.pp_notaio_edit.clear()
        self.pp_repertorio_edit.clear()
        self.pp_note_variazione_edit.clear()
        self.pp_trasferisci_tutti_immobili_check.setChecked(True) # Reimposta a default
        self._pp_temp_nuovi_possessori.clear() # Pulisci la lista interna
        self._pp_aggiorna_tabella_nuovi_possessori() # Aggiorna la tabella visualizzata
        self.logger.info("Campi del form Passaggio Proprietà puliti.")


    def seleziona_e_carica_partita_sorgente(self, partita_id: int):
        """Imposta l'ID della partita sorgente e carica i suoi dettagli."""
        logging.getLogger("CatastoGUI").info(
            f"OperazioniPartitaWidget: Impostazione partita sorgente ID: {partita_id} da chiamata esterna.")
        self.source_partita_id_spinbox.setValue(partita_id)
        # Usa il metodo esistente per caricare i dati
        self._load_partita_sorgente_from_spinbox()


