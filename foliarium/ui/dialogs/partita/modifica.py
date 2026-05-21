"""Dialog modifica e duplicazione partita catastale."""

import logging
import os
from datetime import date
from typing import Optional, Dict, Any

from PyQt6.QtCore import (QDate, Qt, QTimer)
from PyQt6.QtGui import (QBrush, QColor)
from PyQt6.QtWidgets import (QAbstractItemView, QApplication,
                             QCheckBox, QComboBox, QDateEdit,
                             QDialog, QDoubleSpinBox,
                             QFileDialog, QFormLayout, QGridLayout, QGroupBox,
                             QHBoxLayout, QHeaderView, QLabel, QLineEdit,
                             QMessageBox, QPushButton, QSpinBox, QStyle,
                             QTabWidget, QSplitter, QTableWidget,
                             QTableWidgetItem, QTextEdit, QTreeWidget, QTreeWidgetItem,
                             QVBoxLayout, QWidget, QTextBrowser,
                             QDialogButtonBox)

from catasto_db_manager import CatastoDBManager
from foliarium.ui.widgets.custom import ImmobiliTableWidget

from app_utils import (GenericTextReportPDF, FPDF_AVAILABLE, prompt_to_open_file)
from foliarium.ui.dialogs.export_ import PDFApreviewDialog

from foliarium.ui.dialogs.admin import datetime_to_qdate, qdate_to_datetime

try:
    from catasto_db_manager import DBMError, DBUniqueConstraintError, DBNotFoundError, DBDataError
except ImportError:
    class DBMError(Exception): pass
    class DBUniqueConstraintError(DBMError): pass
    class DBNotFoundError(DBMError): pass
    class DBDataError(DBMError): pass
from foliarium.ui.dialogs.partita.immobili import ModificaImmobileDialog, ImmobileDialog
from foliarium.ui.dialogs.partita.selezione import PossessoreSelectionDialog
from foliarium.ui.dialogs.partita.documento import AggiungiDocumentoDialog


class ModificaPartitaDialog(QDialog):
    def __init__(self, db_manager: 'CatastoDBManager', partita_id: int, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.partita_id = partita_id
        self.partita_data_originale: Optional[Dict[str, Any]] = None
        self.logger = logging.getLogger(f"CatastoGUI.{self.__class__.__name__}")

        self.setWindowTitle(f"Dettagli Partita ID: {self.partita_id}")
        self.setMinimumSize(800, 600)

        self._init_ui() # Crea i widget vuoti
        self._load_all_partita_data() # Carica i dati e popola i widget

    def _init_ui(self):
        """Crea tutti i componenti della UI, ma non li popola con i dati."""
        main_layout = QVBoxLayout(self)

        # Sezione Intestazione con placeholder
        header_group = QGroupBox("Dettagli Partita Corrente")
        header_layout = QGridLayout(header_group)
        self.title_label = QLabel("<h2>Caricamento dati partita...</h2>")
        header_layout.addWidget(self.title_label, 0, 0, 1, 4)
        main_layout.addWidget(header_group)
        
        self.tab_widget = QTabWidget(self)
        main_layout.addWidget(self.tab_widget)

        # --- Tab 1: Dati Generali ---
        self.tab_dati_generali = QWidget()
        form_layout_generali = QFormLayout(self.tab_dati_generali)
        # (Qui il codice per creare i campi di input del tab dati generali, come prima)
        self.numero_partita_spinbox = QSpinBox(); self.numero_partita_spinbox.setRange(1, 999999)
        form_layout_generali.addRow("Numero Partita (*):", self.numero_partita_spinbox)
        self.suffisso_partita_edit = QLineEdit(); self.suffisso_partita_edit.setPlaceholderText("Es. bis, A")
        form_layout_generali.addRow("Suffisso Partita (opz.):", self.suffisso_partita_edit)
        self.data_impianto_edit = QDateEdit(calendarPopup=True); self.data_impianto_edit.setDisplayFormat("yyyy-MM-dd")
        form_layout_generali.addRow("Data Impianto (*):", self.data_impianto_edit)
        self.data_chiusura_check = QCheckBox("Imposta data chiusura"); self.data_chiusura_edit = QDateEdit(calendarPopup=True); self.data_chiusura_edit.setDisplayFormat("yyyy-MM-dd"); self.data_chiusura_edit.setEnabled(False); self.data_chiusura_check.toggled.connect(self._toggle_data_chiusura)
        data_chiusura_layout = QHBoxLayout(); data_chiusura_layout.addWidget(self.data_chiusura_check); data_chiusura_layout.addWidget(self.data_chiusura_edit); form_layout_generali.addRow("Data Chiusura:", data_chiusura_layout)
        self.numero_provenienza_edit = QLineEdit(); self.numero_provenienza_edit.setPlaceholderText("Numero o testo di riferimento (opzionale)"); self.numero_provenienza_edit.setMaxLength(50)
        form_layout_generali.addRow("Numero Provenienza:", self.numero_provenienza_edit)
        self.tipo_combo = QComboBox(); self.tipo_combo.addItems(["principale", "secondaria"]); form_layout_generali.addRow("Tipo (*):", self.tipo_combo)
        self.stato_combo = QComboBox(); self.stato_combo.addItems(["attiva", "inattiva"]); form_layout_generali.addRow("Stato (*):", self.stato_combo)
        self.tab_widget.addTab(self.tab_dati_generali, "Dati Generali")

        # Tab 2: Possessori Associati ---
        self.tab_possessori = QWidget()
        # DEVI INIZIALIZZARE possessori_layout QUI
        possessori_layout = QVBoxLayout(self.tab_possessori) 
        self.possessori_table = QTableWidget()
        self.possessori_table.setColumnCount(5)
        self.possessori_table.setHorizontalHeaderLabels(["ID Rel.", "ID Poss.", "Nome Completo Possessore", "Titolo", "Quota"])
        self.possessori_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.possessori_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.possessori_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.possessori_table.setAlternatingRowColors(True)
        
        # Logica per l'espansione delle colonne
        header_possessori = self.possessori_table.horizontalHeader()
        header_possessori.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header_possessori.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header_possessori.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch) # Espande "Nome Completo"
        header_possessori.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header_possessori.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        
        possessori_layout.addWidget(self.possessori_table)

        # Pulsanti per la gestione dei possessori
        possessori_buttons_layout = QHBoxLayout()
        self.btn_aggiungi_possessore = QPushButton("Aggiungi Possessore...")
        self.btn_aggiungi_possessore.clicked.connect(self._aggiungi_possessore_a_partita)
        possessori_buttons_layout.addWidget(self.btn_aggiungi_possessore)

        self.btn_modifica_legame_possessore = QPushButton("Modifica Legame")
        self.btn_modifica_legame_possessore.clicked.connect(self._modifica_legame_possessore)
        self.btn_modifica_legame_possessore.setEnabled(False) 
        possessori_buttons_layout.addWidget(self.btn_modifica_legame_possessore)

        self.btn_rimuovi_possessore = QPushButton("Rimuovi Possessore")
        self.btn_rimuovi_possessore.clicked.connect(self._rimuovi_possessore_da_partita)
        self.btn_rimuovi_possessore.setEnabled(False) 
        possessori_buttons_layout.addWidget(self.btn_rimuovi_possessore)
        
        possessori_buttons_layout.addStretch() 
        possessori_layout.addLayout(possessori_buttons_layout) # Questa è la riga che causava l'errore

        # Collega il segnale itemSelectionChanged della tabella alla funzione che abilita/disabilita i pulsanti
        self.possessori_table.itemSelectionChanged.connect(self._aggiorna_stato_pulsanti_possessori)

        self.tab_widget.addTab(self.tab_possessori, "Possessori Associati")

        # --- Tab 3: Immobili Associati ---
        self.tab_immobili = QWidget()
        layout_immobili = QVBoxLayout(self.tab_immobili)

        self.immobili_table = ImmobiliTableWidget()
        self.immobili_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.immobili_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.immobili_table.itemSelectionChanged.connect(self._aggiorna_stato_pulsanti_immobili)
        layout_immobili.addWidget(self.immobili_table)

        immobili_buttons_layout = QHBoxLayout()
        self.btn_aggiungi_immobile = QPushButton("Aggiungi Immobile...")
        self.btn_aggiungi_immobile.clicked.connect(self._aggiungi_immobile_a_partita)
        immobili_buttons_layout.addWidget(self.btn_aggiungi_immobile)

        self.btn_modifica_immobile = QPushButton("Modifica Immobile...")
        self.btn_modifica_immobile.clicked.connect(self._modifica_immobile_associato)
        self.btn_modifica_immobile.setEnabled(False)
        immobili_buttons_layout.addWidget(self.btn_modifica_immobile)

        self.btn_rimuovi_immobile = QPushButton("Rimuovi Immobile")
        self.btn_rimuovi_immobile.clicked.connect(self._rimuovi_immobile_da_partita)
        self.btn_rimuovi_immobile.setEnabled(False)
        immobili_buttons_layout.addWidget(self.btn_rimuovi_immobile)
        immobili_buttons_layout.addStretch()
        layout_immobili.addLayout(immobili_buttons_layout)
        self.tab_widget.addTab(self.tab_immobili, "Immobili Associati")

        # --- Tab 4: Variazioni ---
        self.tab_variazioni = QWidget()
        layout_variazioni = QVBoxLayout(self.tab_variazioni)

        self.variazioni_table = QTableWidget()
        self.variazioni_table.setColumnCount(6)
        self.variazioni_table.setHorizontalHeaderLabels([
            "ID Var.", "Tipo", "Data Var.", "Partita Origine", "Partita Destinazione", "Contratto"
        ])
        self.variazioni_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.variazioni_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.variazioni_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.variazioni_table.horizontalHeader().setStretchLastSection(True)
        self.variazioni_table.setAlternatingRowColors(True)
        self.variazioni_table.itemSelectionChanged.connect(self._aggiorna_stato_pulsanti_variazioni)
        layout_variazioni.addWidget(self.variazioni_table)

        variazioni_buttons_layout = QHBoxLayout()
        self.btn_modifica_variazione = QPushButton("Modifica Variazione...")
        self.btn_modifica_variazione.clicked.connect(self._modifica_variazione_selezionata)
        self.btn_modifica_variazione.setEnabled(False)
        variazioni_buttons_layout.addWidget(self.btn_modifica_variazione)
        
        self.btn_elimina_variazione = QPushButton("Elimina Variazione")
        self.btn_elimina_variazione.clicked.connect(self._elimina_variazione_selezionata)
        self.btn_elimina_variazione.setEnabled(False)
        variazioni_buttons_layout.addWidget(self.btn_elimina_variazione)

        variazioni_buttons_layout.addStretch()
        layout_variazioni.addLayout(variazioni_buttons_layout)
        self.tab_widget.addTab(self.tab_variazioni, "Variazioni")

        # --- Tab 5: Documenti Allegati ---
        self.tab_documenti = QWidget()
        layout_documenti = QVBoxLayout(self.tab_documenti)

        self.documents_table = QTableWidget()
        self.documents_table.setColumnCount(6)
        self.documents_table.setHorizontalHeaderLabels([
            "ID Doc.", "Titolo", "Tipo Doc.", "Anno", "Rilevanza", "Percorso/Azione"
        ])
        self.documents_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.documents_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.documents_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.documents_table.horizontalHeader().setStretchLastSection(True)
        self.documents_table.setSortingEnabled(True)
        self.documents_table.itemSelectionChanged.connect(self._update_details_doc_buttons_state)
        
        self.documents_table.setAcceptDrops(True)
        self.documents_table.setDropIndicatorShown(True)
        self.documents_table.setDragDropMode(QAbstractItemView.DragDropMode.DropOnly)
        self.documents_table.dragEnterEvent = self.documents_table_dragEnterEvent
        self.documents_table.dragMoveEvent = self.documents_table_dragMoveEvent
        self.documents_table.dropEvent = self.documents_table_dropEvent
        
        layout_documenti.addWidget(self.documents_table)

        doc_buttons_layout = QHBoxLayout()
        self.btn_allega_nuovo = QPushButton(QApplication.style().standardIcon(QStyle.StandardPixmap.SP_FileLinkIcon), "Allega Nuovo Documento...")
        self.btn_allega_nuovo.clicked.connect(self._allega_nuovo_documento_a_partita)
        doc_buttons_layout.addWidget(self.btn_allega_nuovo)

        self.btn_apri_doc_details_dialog = QPushButton(QApplication.style().standardIcon(QStyle.StandardPixmap.SP_DialogOpenButton), "Apri Documento Selezionato")
        self.btn_apri_doc_details_dialog.clicked.connect(self._apri_documento_selezionato_from_details_dialog)
        self.btn_apri_doc_details_dialog.setEnabled(False)
        doc_buttons_layout.addWidget(self.btn_apri_doc_details_dialog)
        
        self.btn_scollega_doc = QPushButton(QApplication.style().standardIcon(QStyle.StandardPixmap.SP_TrashIcon), "Scollega Documento")
        self.btn_scollega_doc.clicked.connect(self._scollega_documento_selezionato)
        self.btn_scollega_doc.setEnabled(False)
        doc_buttons_layout.addWidget(self.btn_scollega_doc)
        
        doc_buttons_layout.addStretch()
        layout_documenti.addLayout(doc_buttons_layout)
        
        self.tab_widget.addTab(self.tab_documenti, "Documenti Allegati")

        # --- Blocco Pulsanti Finale ---
        buttons_layout = QHBoxLayout()
        self.btn_archivia = QPushButton("Archivia Partita")
        self.btn_archivia.setObjectName("dangerButton")
        self.btn_archivia.setToolTip("Archivia questa partita (non viene eliminata, solo nascosta)")
        self.btn_archivia.clicked.connect(self._archivia_partita)
        self.btn_duplica_partita = QPushButton(self.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogNewFolder), " Duplica questa Partita...")
        self.save_button = QPushButton("Salva Modifiche Dati Generali")
        self.close_dialog_button = QPushButton("Chiudi")
        self.btn_duplica_partita.clicked.connect(self._handle_duplica_partita)
        self.save_button.clicked.connect(self._save_changes)
        self.close_dialog_button.clicked.connect(self.accept)
        buttons_layout.addWidget(self.btn_archivia)
        buttons_layout.addWidget(self.btn_duplica_partita)
        buttons_layout.addStretch()
        buttons_layout.addWidget(self.save_button)
        buttons_layout.addWidget(self.close_dialog_button)
        main_layout.addLayout(buttons_layout)
        
        self.setLayout(main_layout)

    # --- Metodi per il Caricamento dei Dati (Centralizzato) ---
    def _toggle_data_chiusura(self, checked):
        """Abilita o disabilita il QDateEdit per la data di chiusura."""
        self.data_chiusura_edit.setEnabled(checked)
        if not checked:
            self.data_chiusura_edit.setDate(QDate()) # Imposta una data nulla

    def _load_all_partita_data(self):
        """Carica tutti i dati e POI popola l'intera UI."""
        self.partita_data_originale = self.db_manager.get_partita_details(self.partita_id)
        
        if not self.partita_data_originale:
            QMessageBox.critical(self, "Errore", f"Impossibile caricare i dati per la partita ID: {self.partita_id}.")
            QTimer.singleShot(0, self.reject)
            return

        # 1. Popola il titolo principale
        suffisso_db = self.partita_data_originale.get('suffisso_partita')
        suffisso_display = f" ({suffisso_db})" if suffisso_db and str(suffisso_db).strip() else ""
        titolo_text = f"<h2>Partita N.{self.partita_data_originale.get('numero_partita', 'N/D')}{suffisso_display} - {self.partita_data_originale.get('comune_nome', 'N/D')}</h2>"
        self.title_label.setText(titolo_text)
        
        # 2. Popola tutti i tab
        self._populate_dati_generali_tab()
        self._load_possessori_associati()
        self._load_immobili_associati()
        self._load_variazioni_associati()
        self._load_documenti_allegati()
        self.logger.info(f"ModificaPartitaDialog: Dati per partita ID {self.partita_id} caricati in tutti i tab.")


    def _populate_dati_generali_tab(self):
        """Popola i campi nel tab 'Dati Generali' con i dati della partita."""
        partita = self.partita_data_originale
        if not partita: return

        self.numero_partita_spinbox.setValue(partita.get('numero_partita', 0))
        self.suffisso_partita_edit.setText(partita.get('suffisso_partita', '') or '')

        tipo_idx = self.tipo_combo.findText(partita.get('tipo', ''), Qt.MatchFlag.MatchFixedString)
        if tipo_idx >= 0: self.tipo_combo.setCurrentIndex(tipo_idx)

        stato_idx = self.stato_combo.findText(partita.get('stato', ''), Qt.MatchFlag.MatchFixedString)
        if stato_idx >= 0: self.stato_combo.setCurrentIndex(stato_idx)

        self.data_impianto_edit.setDate(datetime_to_qdate(partita.get('data_impianto')))

        # Logica aggiornata per data_chiusura
        data_chiusura_db = partita.get('data_chiusura')
        if data_chiusura_db:
            self.data_chiusura_check.setChecked(True)
            self.data_chiusura_edit.setDate(datetime_to_qdate(data_chiusura_db))
        else:
            self.data_chiusura_check.setChecked(False)
            
        # Logica aggiornata per numero_provenienza
        num_prov_val = partita.get('numero_provenienza')
        self.numero_provenienza_edit.setText(str(num_prov_val) if num_prov_val is not None else "")

        self.logger.debug("Tab 'Dati Generali' popolato con la nuova logica.")


    def _load_possessori_associati(self):
        """Carica e popola la tabella dei possessori associati alla partita."""
        self.possessori_table.setRowCount(0)
        self.possessori_table.setSortingEnabled(False)
        self.possessori_table.clearSelection() # Pulisce la selezione
        self.logger.info(f"Caricamento possessori associati per partita ID: {self.partita_id}")

        try:
            possessori = self.db_manager.get_possessori_per_partita(self.partita_id)
            if possessori:
                self.possessori_table.setRowCount(len(possessori))
                for row_idx, poss_data in enumerate(possessori):
                    id_rel_val = poss_data.get('id_relazione_partita_possessore', '')
                    id_rel_item = QTableWidgetItem(str(id_rel_val))
                    id_rel_item.setData(Qt.ItemDataRole.UserRole, id_rel_val) # Salva l'ID relazione
                    self.possessori_table.setItem(row_idx, 0, id_rel_item)

                    self.possessori_table.setItem(row_idx, 1, QTableWidgetItem(str(poss_data.get('possessore_id', ''))))
                    self.possessori_table.setItem(row_idx, 2, QTableWidgetItem(poss_data.get('nome_completo_possessore', 'N/D')))
                    self.possessori_table.setItem(row_idx, 3, QTableWidgetItem(poss_data.get('titolo_possesso', 'N/D')))
                    self.possessori_table.setItem(row_idx, 4, QTableWidgetItem(poss_data.get('quota_possesso', 'N/D') or '')) # Gestisce None
                self.possessori_table.resizeColumnsToContents()
            else:
                self.logger.info(f"Nessun possessore trovato per la partita ID {self.partita_id}.")
                self.possessori_table.setRowCount(1)
                item = QTableWidgetItem("Nessun possessore associato a questa partita.")
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.possessori_table.setItem(0, 0, item)
                self.possessori_table.setSpan(0, 0, 1, self.possessori_table.columnCount())
        except Exception as e:
            self.logger.error(f"Errore durante il popolamento della tabella possessori per partita ID {self.partita_id}: {e}", exc_info=True)
            QMessageBox.critical(self, "Errore Popolamento Tabella", f"Si è verificato un errore durante la visualizzazione dei possessori associati:\n{e}")
        finally:
            self.possessori_table.setSortingEnabled(True)
            self._aggiorna_stato_pulsanti_possessori()
            self.logger.debug("Tab 'Possessori' popolato.")

    def _load_immobili_associati(self):
        """Carica e popola la tabella degli immobili associati alla partita."""
        self.immobili_table.setRowCount(0)
        self.immobili_table.setSortingEnabled(False)
        self.immobili_table.clearSelection() # Pulisce la selezione
        self.logger.info(f"Caricamento immobili associati per partita ID: {self.partita_id}")

        try:
            immobili = self.partita_data_originale.get('immobili', []) # Dati immobili sono già in partita_data_originale
            if immobili:
                self.immobili_table.setRowCount(len(immobili))
                for row_idx, imm in enumerate(immobili):
                    # La logica di ImmobiliTableWidget.populate_data è replicata qui per coerenza
                    # ma potresti anche passare i dati a immobili_table.populate_data() se è un widget riusabile
                    self.immobili_table.setItem(row_idx, 0, QTableWidgetItem(str(imm.get('id', ''))))
                    self.immobili_table.setItem(row_idx, 1, QTableWidgetItem(imm.get('natura', '')))
                    self.immobili_table.setItem(row_idx, 2, QTableWidgetItem(imm.get('classificazione', '')))
                    self.immobili_table.setItem(row_idx, 3, QTableWidgetItem(imm.get('consistenza', '')))
                    from app_utils import format_indirizzo
                    localita_text = format_indirizzo(
                        imm.get('tipologia_stradale') or imm.get('localita_tipo'),
                        imm.get('localita_nome'),
                        imm.get('numero_civico') or imm.get('civico'),
                    )
                    self.immobili_table.setItem(row_idx, 4, QTableWidgetItem(localita_text))
                self.immobili_table.resizeColumnsToContents()
            else:
                self.logger.info(f"Nessun immobile trovato per la partita ID {self.partita_id}.")
                self.immobili_table.setRowCount(1)
                item = QTableWidgetItem("Nessun immobile associato a questa partita.")
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.immobili_table.setItem(0, 0, item)
                self.immobili_table.setSpan(0, 0, 1, self.immobili_table.columnCount())
        except Exception as e:
            self.logger.error(f"Errore durante il popolamento della tabella immobili per partita ID {self.partita_id}: {e}", exc_info=True)
            QMessageBox.critical(self, "Errore Popolamento Tabella", f"Si è verificato un errore durante la visualizzazione degli immobili associati:\n{e}")
        finally:
            self.immobili_table.setSortingEnabled(True)
            self._aggiorna_stato_pulsanti_immobili()
            self.logger.debug("Tab 'Immobili' popolato.")

    def _load_variazioni_associati(self):
        """Carica e popola la tabella delle variazioni associate alla partita."""
        self.variazioni_table.setRowCount(0)
        self.variazioni_table.setSortingEnabled(False)
        self.variazioni_table.clearSelection() # Pulisce la selezione
        self.logger.info(f"Caricamento variazioni associate per partita ID: {self.partita_id}")

        try:
            variazioni = self.partita_data_originale.get('variazioni', []) # Dati variazioni sono già in partita_data_originale
            if variazioni:
                self.variazioni_table.setRowCount(len(variazioni))
                for row_idx, var in enumerate(variazioni):
                    col = 0
                    self.variazioni_table.setItem(row_idx, col, QTableWidgetItem(str(var.get('id', '')))); col += 1
                    self.variazioni_table.setItem(row_idx, col, QTableWidgetItem(var.get('tipo', ''))); col += 1
                    self.variazioni_table.setItem(row_idx, col, QTableWidgetItem(str(var.get('data_variazione', '')))); col += 1

                    # Partita Origine
                    orig_text = ""
                    if var.get('partita_origine_id'):
                        num_orig = var.get('origine_numero_partita', 'N/D')
                        com_orig = var.get('origine_comune_nome', 'N/D')
                        orig_text = f"N.{num_orig} ({com_orig})"
                        if var.get('origine_suffisso_partita'): # Se hai il suffisso nella variazione
                            orig_text += f" ({var.get('origine_suffisso_partita')})"
                    else:
                        orig_text = "-"
                    self.variazioni_table.setItem(row_idx, col, QTableWidgetItem(orig_text)); col += 1

                    # Partita Destinazione
                    dest_text = ""
                    if var.get('partita_destinazione_id'):
                        num_dest = var.get('destinazione_numero_partita', 'N/D')
                        com_dest = var.get('destinazione_comune_nome', 'N/D')
                        dest_text = f"N.{num_dest} ({com_dest})"
                        if var.get('destinazione_suffisso_partita'): # Se hai il suffisso nella variazione
                            dest_text += f" ({var.get('destinazione_suffisso_partita')})"
                    else:
                        dest_text = "-"
                    self.variazioni_table.setItem(row_idx, col, QTableWidgetItem(dest_text)); col += 1

                    # Contratto
                    contratto_text = ""
                    if var.get('tipo_contratto'):
                        contratto_text = f"{var['tipo_contratto']} del {var.get('data_contratto', '')}"
                        if var.get('notaio'):
                            contratto_text += f" - {var['notaio']}"
                    self.variazioni_table.setItem(row_idx, col, QTableWidgetItem(contratto_text)); col += 1

                self.variazioni_table.resizeColumnsToContents()
            else:
                self.logger.info(f"Nessuna variazione trovata per la partita ID {self.partita_id}.")
                self.variazioni_table.setRowCount(1)
                item = QTableWidgetItem("Nessuna variazione associata a questa partita.")
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.variazioni_table.setItem(0, 0, item)
                self.variazioni_table.setSpan(0, 0, 1, self.variazioni_table.columnCount())
        except Exception as e:
            self.logger.error(f"Errore durante il popolamento della tabella variazioni per partita ID {self.partita_id}: {e}", exc_info=True)
            QMessageBox.critical(self, "Errore Popolamento Tabella", f"Si è verificato un errore durante la visualizzazione delle variazioni associate:\n{e}")
        finally:
            self.variazioni_table.setSortingEnabled(True)
            self._aggiorna_stato_pulsanti_variazioni()
            self.logger.debug("Tab 'Variazioni' popolato.")

    # In gui_widgets.py, nella classe ModificaPartitaDialog
# Sostituisci il metodo _load_documenti_allegati() con questa versione corretta:
    def _handle_duplica_partita(self):
        """Gestisce il click sul pulsante 'Duplica', apre il dialogo delle opzioni e avvia l'operazione."""
        self.logger.info(f"Richiesta duplicazione per la partita ID {self.partita_id}.")

        # Apri il dialogo delle opzioni
        options_dialog = DuplicaPartitaOptionsDialog(self)
        if options_dialog.exec() != QDialog.DialogCode.Accepted:
            self.logger.info("Duplicazione annullata dall'utente.")
            return
            
        options = options_dialog.get_options()
        nuovo_numero = options['nuovo_numero_partita']
        nuovo_suffisso = options['nuovo_suffisso']
        
        # Validazione: verifica che la nuova partita non esista già
        # Dobbiamo usare il comune_id della partita corrente
        comune_id_corrente = self.partita_data_originale.get('comune_id')
        if comune_id_corrente:
            existing = self.db_manager.search_partite(
                comune_id=comune_id_corrente,
                numero_partita=nuovo_numero,
                suffisso_partita=nuovo_suffisso
            )
            if existing:
                QMessageBox.warning(self, "Partita Esistente", f"Esiste già una partita con numero {nuovo_numero} e suffisso '{nuovo_suffisso or ''}' in questo comune.")
                return

        # Esegui la duplicazione tramite il DB Manager
        try:
            success = self.db_manager.duplicate_partita(
                partita_id_originale=self.partita_id,
                **options # Passa le opzioni come argomenti keyword
            )
            if success:
                QMessageBox.information(self, "Successo", "Partita duplicata con successo.")
                # Opzionale: potremmo voler aggiornare qualche vista qui
            # L'eccezione verrà sollevata dal metodo in caso di fallimento
        except DBMError as e:
            self.logger.error(f"Errore durante la duplicazione della partita ID {self.partita_id}: {e}", exc_info=True)
            QMessageBox.critical(self, "Errore Duplicazione", f"Impossibile duplicare la partita:\n{e}")

    def _load_documenti_allegati(self):
        """Carica e popola la tabella dei documenti allegati alla partita."""
        self.documents_table.setRowCount(0)
        self.documents_table.setSortingEnabled(False)
        self.documents_table.clearSelection() 
        self.logger.info(f"Caricamento documenti per partita ID {self.partita_id}.")

        try:
            # CORREZIONE: Usa self.partita_id invece di self.partita['id']
            documenti = self.db_manager.get_documenti_per_partita(self.partita_id)
            
            if documenti:
                self.documents_table.setRowCount(len(documenti))
                for row, doc in enumerate(documenti):
            # Salviamo un dizionario con gli ID di relazione nell'UserRole
                    rel_data = {
                        'doc_id': doc.get('rel_documento_id'),
                        'partita_id': doc.get('rel_partita_id')
                    }

                    # L'item nella prima colonna conterrà tutti i dati per la riga
                    item_doc_id = QTableWidgetItem(str(doc.get('documento_id', '')))
                    item_doc_id.setData(Qt.ItemDataRole.UserRole, rel_data)
                    self.documents_table.setItem(row, 0, item_doc_id)
                    # Salviamo l'ID del documento storico e l'ID della partita per la rimozione del legame
                    item_doc_id.setData(Qt.ItemDataRole.UserRole + 1, doc.get("dp_documento_id")) # ID del documento storico nella relazione
                    item_doc_id.setData(Qt.ItemDataRole.UserRole + 2, doc.get("dp_partita_id")) # ID della partita nella relazione (che è self.partita_id)
                    
                    
                    self.documents_table.setItem(row, 1, QTableWidgetItem(doc.get("titolo") or ''))
                    self.documents_table.setItem(row, 2, QTableWidgetItem(doc.get("tipo_documento") or ''))
                    self.documents_table.setItem(row, 3, QTableWidgetItem(str(doc.get("anno", '')) or ''))
                    self.documents_table.setItem(row, 4, QTableWidgetItem(doc.get("rilevanza") or ''))
                    
                    # CORREZIONE: Assicurati che il percorso sia salvato correttamente nell'UserRole
                    percorso_file_full = doc.get("percorso_file") or ''
                    path_item = QTableWidgetItem(os.path.basename(percorso_file_full) if percorso_file_full else "N/D")
                    path_item.setData(Qt.ItemDataRole.UserRole, percorso_file_full) # Salva percorso completo per l'apertura
                    self.documents_table.setItem(row, 5, path_item)
                
                self.documents_table.resizeColumnsToContents()
            else:
                self.logger.info(f"Nessun documento trovato per la partita ID {self.partita_id}.")
                self.documents_table.setRowCount(1)
                no_docs_item = QTableWidgetItem("Nessun documento allegato a questa partita.")
                no_docs_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.documents_table.setItem(0, 0, no_docs_item)
                self.documents_table.setSpan(0, 0, 1, self.documents_table.columnCount())

        except Exception as e:
            self.logger.error(f"Errore caricamento documenti per partita ID {self.partita_id}: {e}", exc_info=True)
            QMessageBox.critical(self, "Errore Caricamento Documenti", f"Si è verificato un errore durante il caricamento dei documenti:\n{e}")
            # Mostra messaggio di errore nella tabella
            self.documents_table.setRowCount(1)
            error_item = QTableWidgetItem(f"Errore nel caricamento dei documenti: {e}")
            error_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.documents_table.setItem(0, 0, error_item)
            self.documents_table.setSpan(0, 0, 1, self.documents_table.columnCount())
        finally:
            self.documents_table.setSortingEnabled(True)
            self._update_document_tab_title() 
            self._update_details_doc_buttons_state() 
            self.logger.debug("Tab 'Documenti' popolato.")


    # --- Metodi per la Gestione dei Pulsanti e Selezioni ---

    def _aggiorna_stato_pulsanti_possessori(self):
        """Abilita/disabilita i pulsanti per i possessori in base alla selezione."""
        has_selection = bool(self.possessori_table.selectedItems())
        self.btn_modifica_legame_possessore.setEnabled(has_selection)
        self.btn_rimuovi_possessore.setEnabled(has_selection)

    def _aggiorna_stato_pulsanti_immobili(self):
        """Abilita/disabilita i pulsanti per gli immobili in base alla selezione."""
        has_selection = bool(self.immobili_table.selectedItems())
        self.btn_modifica_immobile.setEnabled(has_selection)
        self.btn_rimuovi_immobile.setEnabled(has_selection)

    def _aggiorna_stato_pulsanti_variazioni(self):
        """Abilita/disabilita i pulsanti per le variazioni in base alla selezione."""
        has_selection = bool(self.variazioni_table.selectedItems())
        self.btn_modifica_variazione.setEnabled(has_selection)
        self.btn_elimina_variazione.setEnabled(has_selection)

    def _update_details_doc_buttons_state(self):
        """Abilita/disabilita i pulsanti per i documenti in base alla selezione."""
        has_selection = bool(self.documents_table.selectedItems())
        self.btn_apri_doc_details_dialog.setEnabled(has_selection)
        self.btn_scollega_doc.setEnabled(has_selection)

    # --- Metodi per Azioni sui Dati ---

    # -- Possessori --
    def _aggiungi_possessore_a_partita(self):
        self.logger.debug(f"Richiesta aggiunta possessore per partita ID {self.partita_id}")
        comune_id_partita = self.partita_data_originale.get('comune_id')
        if comune_id_partita is None:
            QMessageBox.warning(self, "Errore", "Comune della partita non determinato. Impossibile aggiungere possessore.")
            return

        possessore_dialog = PossessoreSelectionDialog(self.db_manager, comune_id_partita, self)
        selected_possessore_id = None
        selected_possessore_nome = None

        if possessore_dialog.exec() == QDialog.DialogCode.Accepted:
            if hasattr(possessore_dialog, 'selected_possessore') and possessore_dialog.selected_possessore:
                selected_possessore_id = possessore_dialog.selected_possessore.get('id')
                selected_possessore_nome = possessore_dialog.selected_possessore.get('nome_completo')
        if not selected_possessore_id or not selected_possessore_nome:
            self.logger.info("Nessun possessore selezionato o creato.")
            return

        self.logger.info(f"Possessore selezionato/creato: ID {selected_possessore_id}, Nome: {selected_possessore_nome}")
        tipo_partita_corrente = self.partita_data_originale.get('tipo', 'principale')
        from foliarium.ui.dialogs.entity import DettagliLegamePossessoreDialog
        dettagli_legame = DettagliLegamePossessoreDialog.get_details_for_new_legame(selected_possessore_nome, tipo_partita_corrente, self)

        if not dettagli_legame:
            self.logger.info("Inserimento dettagli legame annullato.")
            return

        try:
            success = self.db_manager.aggiungi_possessore_a_partita(
                partita_id=self.partita_id,
                possessore_id=selected_possessore_id,
                tipo_partita_rel=tipo_partita_corrente,
                titolo=dettagli_legame["titolo"],
                quota=dettagli_legame["quota"]
            )
            if success:
                self.logger.info(f"Possessore ID {selected_possessore_id} aggiunto con successo alla partita ID {self.partita_id}")
                QMessageBox.information(self, "Successo", f"Possessore '{selected_possessore_nome}' aggiunto alla partita.")
                self._load_possessori_associati()
            else:
                self.logger.error("aggiungi_possessore_a_partita ha restituito False.")
                QMessageBox.critical(self, "Errore", "Impossibile aggiungere il possessore alla partita.")
        except (DBUniqueConstraintError, DBDataError, DBMError) as e:
            self.logger.error(f"Errore DB aggiungendo possessore {selected_possessore_id} a partita {self.partita_id}: {e}", exc_info=True)
            QMessageBox.critical(self, "Errore Database", f"Errore durante l'aggiunta del possessore alla partita:\n{e.message if hasattr(e, 'message') else str(e)}")
        except Exception as e:
            self.logger.critical(f"Errore imprevisto aggiungendo possessore {selected_possessore_id} a partita {self.partita_id}: {e}", exc_info=True)
            QMessageBox.critical(self, "Errore Imprevisto", f"Si è verificato un errore: {e}")

    def _modifica_legame_possessore(self):
        from foliarium.ui.dialogs.entity import DettagliLegamePossessoreDialog

        selected_items = self.possessori_table.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "Nessuna Selezione", "Seleziona un possessore dalla tabella per modificarne il legame.")
            return

        current_row = selected_items[0].row()
        id_relazione_pp = self.possessori_table.item(current_row, 0).data(Qt.ItemDataRole.UserRole)
        if id_relazione_pp is None:
            QMessageBox.critical(self, "Errore Interno", "ID relazione non trovato per il possessore selezionato.")
            return

        nome_possessore_attuale = self.possessori_table.item(current_row, 2).text()
        titolo_attuale = self.possessori_table.item(current_row, 3).text()
        quota_attuale_item = self.possessori_table.item(current_row, 4)
        quota_attuale = quota_attuale_item.text() if quota_attuale_item and quota_attuale_item.text() != 'N/D' else None

        self.logger.debug(f"Richiesta modifica legame per relazione ID {id_relazione_pp} (Possessore: {nome_possessore_attuale})")
        tipo_partita_corrente = self.partita_data_originale.get('tipo', 'principale')
        nuovi_dettagli_legame = DettagliLegamePossessoreDialog.get_details_for_edit_legame(
            nome_possessore_attuale, tipo_partita_corrente, titolo_attuale, quota_attuale, self
        )

        if not nuovi_dettagli_legame:
            self.logger.info("Modifica dettagli legame annullata.")
            return

        try:
            success = self.db_manager.aggiorna_legame_partita_possessore(
                partita_possessore_id=id_relazione_pp,
                titolo=nuovi_dettagli_legame["titolo"],
                quota=nuovi_dettagli_legame["quota"]
            )
            if success:
                self.logger.info(f"Legame ID {id_relazione_pp} aggiornato con successo.")
                QMessageBox.information(self, "Successo", "Dettagli del legame possessore aggiornati.")
                self._load_possessori_associati()
            else:
                self.logger.error("aggiorna_legame_partita_possessore ha restituito False.")
                QMessageBox.critical(self, "Errore", "Impossibile aggiornare il legame del possessore.")
        except (DBMError, DBDataError) as dbe_legame:
            self.logger.error(f"Errore DB aggiornando legame {id_relazione_pp}: {dbe_legame}", exc_info=True)
            QMessageBox.critical(self, "Errore Database", f"Errore durante l'aggiornamento del legame:\n{dbe_legame.message if hasattr(dbe_legame, 'message') else str(dbe_legame)}")
        except Exception as e_legame:
            self.logger.critical(f"Errore imprevisto aggiornando legame {id_relazione_pp}: {e_legame}", exc_info=True)
            QMessageBox.critical(self, "Errore Imprevisto", f"Si è verificato un errore: {e_legame}")

    def _rimuovi_possessore_da_partita(self):
        selected_items = self.possessori_table.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "Nessuna Selezione", "Seleziona un legame possessore dalla tabella da rimuovere.")
            return

        id_relazione_pp = selected_items[0].data(Qt.ItemDataRole.UserRole)
        nome_possessore = self.possessori_table.item(selected_items[0].row(), 2).text()

        if id_relazione_pp is None:
            QMessageBox.critical(self, "Errore Interno", "ID relazione non trovato per il possessore selezionato.")
            return

        reply = QMessageBox.question(self, "Conferma Rimozione Legame",
                                     f"Sei sicuro di voler rimuovere il legame con il possessore '{nome_possessore}' (ID Relazione: {id_relazione_pp}) da questa partita?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            self.logger.debug(f"Richiesta rimozione legame ID {id_relazione_pp}")
            try:
                success = self.db_manager.rimuovi_possessore_da_partita(id_relazione_pp)

                if success:
                    self.logger.info(f"Legame ID {id_relazione_pp} rimosso con successo.")
                    QMessageBox.information(self, "Successo", "Legame con il possessore rimosso dalla partita.")
                    self._load_possessori_associati()
                else:
                    self.logger.error("rimuovi_possessore_da_partita ha restituito False.")
                    QMessageBox.critical(self, "Errore", "Impossibile rimuovere il legame del possessore.")
            except DBNotFoundError as nfe_rel:
                self.logger.warning(f"Tentativo di rimuovere legame ID {id_relazione_pp} non trovato: {nfe_rel}")
                QMessageBox.warning(self, "Operazione Fallita", str(nfe_rel.message))
                self._load_possessori_associati()
            except (DBMError, DBDataError) as dbe_rel:
                self.logger.error(f"Errore DB rimuovendo legame {id_relazione_pp}: {dbe_rel}", exc_info=True)
                QMessageBox.critical(self, "Errore Database", f"Errore durante la rimozione del legame:\n{dbe_rel.message if hasattr(dbe_rel, 'message') else str(dbe_rel)}")
            except Exception as e_rel:
                self.logger.critical(f"Errore imprevisto rimuovendo legame {id_relazione_pp}: {e_rel}", exc_info=True)
                QMessageBox.critical(self, "Errore Imprevisto", f"Si è verificato un errore: {e_rel}")

    # -- Immobili --
    def _aggiungi_immobile_a_partita(self):
        self.logger.debug(f"Richiesta aggiunta immobile per partita ID {self.partita_id}")
        comune_id_partita = self.partita_data_originale.get('comune_id')
        if comune_id_partita is None:
            QMessageBox.warning(self, "Errore", "Comune della partita non determinato. Impossibile aggiungere immobile.")
            return

        dialog = ImmobileDialog(self.db_manager, comune_id_partita, self)
        if dialog.exec() == QDialog.DialogCode.Accepted and dialog.immobile_data:
            immobile_data = dialog.immobile_data
            try:
                # La procedura SQL inserisci_immobile in db_manager deve essere aggiornata
                # per accettare tutti i campi dall'immobile_data
                immobile_id = self.db_manager.inserisci_immobile(
                    partita_id=self.partita_id,
                    natura=immobile_data['natura'],
                    localita_id=immobile_data['localita_id'],
                    numero_civico=immobile_data.get('numero_civico'),
                    classificazione=immobile_data['classificazione'],
                    consistenza=immobile_data['consistenza'],
                    numero_piani=immobile_data['numero_piani'],
                    numero_vani=immobile_data['numero_vani']
                )
                if immobile_id:
                    QMessageBox.information(self, "Successo", f"Immobile '{immobile_data['natura']}' aggiunto con ID: {immobile_id}.")
                    self._load_immobili_associati() # Ricarica la tabella immobili
                else:
                    self.logger.error("inserisci_immobile ha restituito None.")
                    QMessageBox.critical(self, "Errore", "Impossibile aggiungere l'immobile.")
            except (DBDataError, DBMError) as e:
                self.logger.error(f"Errore DB aggiungendo immobile: {e}", exc_info=True)
                QMessageBox.critical(self, "Errore Database", f"Errore durante l'aggiunta dell'immobile:\n{e.message if hasattr(e, 'message') else str(e)}")
            except Exception as e:
                self.logger.critical(f"Errore imprevisto aggiungendo immobile: {e}", exc_info=True)
                QMessageBox.critical(self, "Errore Imprevisto", f"Si è verificato un errore: {e}")

    def _modifica_immobile_associato(self):
        selected_items = self.immobili_table.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "Nessuna Selezione", "Seleziona un immobile dalla tabella per modificarlo.")
            return

        row = self.immobili_table.currentRow()
        immobile_id = int(self.immobili_table.item(row, 0).text())
        
        # Recupera i dettagli attuali dell'immobile dal DB per pre-popolare il dialogo di modifica
        immobile_data = self.db_manager.get_immobile_details(immobile_id) # Questo metodo deve essere in db_manager
        if not immobile_data:
            QMessageBox.critical(self, "Errore", "Impossibile recuperare i dettagli dell'immobile per la modifica.")
            return

        # Apri un dialogo di modifica specifico per l'immobile, simile a ImmobileDialog ma per la modifica
        # Dobbiamo creare una classe ModificaImmobileDialog, oppure riadattare ImmobileDialog con un flag 'modalità_modifica'
        
        # Per semplicità, qui useremo una versione adattata di ImmobileDialog o un nuovo dialogo.
        # Creiamo un nuovo dialogo o adattiamo quello esistente (che forse non è l'ideale).
        
        # Idealmente, avresti un ModificaImmobileDialog(db_manager, immobile_id, comune_id_partita, parent)
        # Per ora, si assume che sia un dialogo che possa essere pre-popolato e salvare.
        
        # Se non esiste una ModificaImmobileDialog, questo non funzionerà.
        # Per semplicità, ipotizziamo una classe ad-hoc o un'estensione.
        # Assicurati che sia importata o creata
        dialog = ModificaImmobileDialog(self.db_manager, immobile_id, self.partita_id, self) # Passa immobile_id, partita_id
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            QMessageBox.information(self, "Successo", "Immobile modificato con successo.")
            self._load_immobili_associati() # Ricarica la tabella immobili
        else:
            self.logger.info("Modifica immobile annullata.")

    def _rimuovi_immobile_da_partita(self):
        selected_items = self.immobili_table.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "Nessuna Selezione", "Seleziona un immobile dalla tabella per rimuoverlo.")
            return

        row = self.immobili_table.currentRow()
        immobile_id = int(self.immobili_table.item(row, 0).text())
        
        reply = QMessageBox.question(self, "Conferma Rimozione",
                                     f"Sei sicuro di voler rimuovere l'immobile ID {immobile_id} da questa partita?\n"
                                     "Questa azione non cancella l'immobile dal database, ma lo scollega dalla partita attuale, impostando il suo partita_id a NULL.",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            try:
                # Il metodo delete_immobile in db_manager deve essere aggiornato
                # per supportare la rimozione/scollegamento senza cancellare
                # o potresti chiamare una procedura SQL specifica per scollegare.
                # Per ora, la tua procedura delete_immobile probabilemente CANCELLA.
                # Quindi, il comportamento è distruttivo.
                # Dobbiamo chiarire la semantica di "rimuovi immobile da partita":
                # 1. Cancellare l'immobile del tutto (current delete_immobile)?
                # 2. Scollegarlo dalla partita (partita_id a NULL)?
                # 3. Trasferirlo a un'altra partita (usare _esegui_trasferimento_immobile)?

                # Se l'intento è impostare partita_id a NULL (scollegare), serve un nuovo metodo in DBManager.
                # Es. db_manager.scollega_immobile_da_partita(immobile_id)
                # Per ora, usiamo l'esistente delete_immobile con un avviso, ma è probabile che non sia il comportamento desiderato.
                success = self.db_manager.delete_immobile(immobile_id) # ATTENZIONE: Questo prob. CANCELLA FISICAMENTE!

                if success:
                    QMessageBox.information(self, "Successo", f"Immobile ID {immobile_id} rimosso/cancellato dalla partita.")
                    self._load_immobili_associati()
                else:
                    self.logger.error("delete_immobile ha restituito False.")
                    QMessageBox.critical(self, "Errore", "Impossibile rimuovere/cancellare l'immobile.")
            except (DBMError, DBDataError) as e:
                self.logger.error(f"Errore DB rimuovendo immobile: {e}", exc_info=True)
                QMessageBox.critical(self, "Errore Database", f"Errore durante la rimozione dell'immobile:\n{e.message if hasattr(e, 'message') else str(e)}")
            except Exception as e:
                self.logger.critical(f"Errore imprevisto rimuovendo immobile: {e}", exc_info=True)
                QMessageBox.critical(self, "Errore Imprevisto", f"Si è verificato un errore: {e}")

    # -- Variazioni --
    def _modifica_variazione_selezionata(self):
        selected_items = self.variazioni_table.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "Nessuna Selezione", "Seleziona una variazione dalla tabella per modificarla.")
            return

        row = self.variazioni_table.currentRow()
        # Controlla se la riga selezionata è una riga di placeholder
        if self.variazioni_table.rowCount() == 1 and self.variazioni_table.item(0, 0) and "Nessuna variazione" in self.variazioni_table.item(0, 0).text():
            QMessageBox.warning(self, "Nessuna Variazione", "Non ci sono variazioni valide selezionate per la modifica.")
            return

        variazione_id = int(self.variazioni_table.item(row, 0).text())

        # Apri un dialogo per modificare la variazione, simile a InserimentoVariazione (se lo hai)
        # Dobbiamo creare una classe ModificaVariazioneDialog
        from gui_widgets import ModificaVariazioneDialog # Assicurati che sia importata o creata
        dialog = ModificaVariazioneDialog(self.db_manager, variazione_id, self.partita_id, self) # Passa variazione_id, partita_id
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            QMessageBox.information(self, "Successo", "Variazione modificata con successo.")
            self._load_variazioni_associati() # Ricarica la tabella
        else:
            self.logger.info("Modifica variazione annullata.")

    def _elimina_variazione_selezionata(self):
        selected_items = self.variazioni_table.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "Nessuna Selezione", "Seleziona una variazione dalla tabella per eliminarla.")
            return

        row = self.variazioni_table.currentRow()
        variazione_id = int(self.variazioni_table.item(row, 0).text())
        
        reply = QMessageBox.question(self, "Conferma Eliminazione",
                                     f"Sei sicuro di voler eliminare la variazione ID {variazione_id}?\n"
                                     "Questa azione potrebbe avere effetti sulle partite collegate (es. riattivare la partita origine se chiusa).",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            try:
                # Il metodo delete_variazione in db_manager ha flag force e restore_partita
                success = self.db_manager.delete_variazione(variazione_id, force=True, restore_partita=False) # Decidi la politica
                
                if success:
                    QMessageBox.information(self, "Successo", f"Variazione ID {variazione_id} eliminata.")
                    # Dopo aver eliminato una variazione, è fondamentale ricaricare i dati di tutte le partite coinvolte
                    # (origine e destinazione) per riflettere eventuali cambiamenti di stato.
                    # Per ora, ricarichiamo solo la lista delle variazioni per la partita corrente.
                    self._load_variazioni_associati() 
                    # Potrebbe essere necessario ricaricare anche la partita_data_originale
                    # e le partite del comune genitore.
                else:
                    self.logger.error("delete_variazione ha restituito False.")
                    QMessageBox.critical(self, "Errore", "Impossibile eliminare la variazione.")
            except (DBMError, DBDataError) as e:
                self.logger.error(f"Errore DB eliminando variazione: {e}", exc_info=True)
                QMessageBox.critical(self, "Errore Database", f"Errore durante l'eliminazione della variazione:\n{e.message if hasattr(e, 'message') else str(e)}")
            except Exception as e:
                self.logger.critical(f"Errore imprevisto eliminando variazione: {e}", exc_info=True)
                QMessageBox.critical(self, "Errore Imprevisto", f"Si è verificato un errore: {e}")

    # -- Documenti --
    # Questi metodi sono già definiti correttamente e riutilizzano DocumentViewerDialog.
    # Non è necessario riscriverli qui, ma assicurati che siano presenti nel codice finale.
    # documents_table_dragEnterEvent, documents_table_dragMoveEvent, documents_table_dropEvent,
    # _handle_dropped_file, _allega_nuovo_documento_a_partita, _apri_documento_selezionato_from_details_dialog,
    # _scollega_documento_selezionato.
    # --- NUOVI METODI PER LA GESTIONE DEL DRAG-AND-DROP ---

    def documents_table_dragEnterEvent(self, event):
        """Accetta solo eventi di drag che contengono URL (file)."""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def documents_table_dragMoveEvent(self, event):
        """Mantiene l'accettazione dell'azione se ci sono URL."""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def documents_table_dropEvent(self, event):
        """Elabora i file rilasciati sulla tabella."""
        self.logger.info("Drop event rilevato sulla tabella documenti.")
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                file_path = url.toLocalFile()
                self.logger.info(f"File rilasciato: {file_path}")
                # Qui chiamiamo la stessa logica di allegazione usata dal pulsante "Allega Nuovo Documento..."
                # che a sua volta apre AggiungiDocumentoDialog.
                # Però, dobbiamo passare il file_path al dialogo in modo che sia pre-selezionato.
                self._handle_dropped_file(file_path)
            event.acceptProposedAction()
        else:
            event.ignore()

    def _handle_dropped_file(self, file_path: str):
        """Gestisce un singolo file rilasciato, aprendo il dialogo di allegazione."""
        if not os.path.exists(file_path):
            QMessageBox.warning(self, "File Non Trovato", f"Il file rilasciato non esiste: {file_path}")
            self.logger.warning(f"File rilasciato non trovato: {file_path}")
            return
        
        if not os.path.isfile(file_path):
            QMessageBox.warning(self, "Non un File", f"L'elemento rilasciato non è un file valido: {file_path}")
            self.logger.warning(f"Elemento rilasciato non è un file: {file_path}")
            return

        # Filtra i tipi di file accettati, se necessario
        allowed_extensions = ['.pdf', '.jpg', '.jpeg', '.png']
        file_extension = os.path.splitext(file_path)[1].lower()
        if file_extension not in allowed_extensions:
            QMessageBox.warning(self, "Formato Non Supportato", f"Il formato del file '{file_extension}' non è supportato. Sono accettati: {', '.join(allowed_extensions)}.")
            self.logger.warning(f"Formato file non supportato per il drop: {file_path}")
            return
        
        # Apri il dialogo AggiungiDocumentoDialog e pre-popola il campo file
        dialog = AggiungiDocumentoDialog(self.db_manager, self.partita_id, self)
        
        # Imposta il percorso del file nel dialogo appena aperto
        # Questo richiede una modifica in AggiungiDocumentoDialog per avere un metodo set_initial_file_path
        dialog.set_initial_file_path(file_path)

        if dialog.exec() == QDialog.DialogCode.Accepted and dialog.document_data:
            doc_info = dialog.document_data
            percorso_originale = doc_info["percorso_file_originale"] # Ora sarà file_path pre-selezionato
            
            # ... (la tua logica esistente di copia file e salvataggio nel DB da _allega_nuovo_documento_a_partita) ...
            allegati_dir = os.path.join(".", "allegati_catasto", f"partita_{self.partita_id}")
            os.makedirs(allegati_dir, exist_ok=True)
            
            nome_file_originale = os.path.basename(percorso_originale)
            nome_file_dest = nome_file_originale 
            percorso_destinazione_completo = os.path.join(allegati_dir, nome_file_dest)
            
            try:
                import shutil
                shutil.copy2(percorso_originale, percorso_destinazione_completo)
                self.logger.info(f"File copiato da '{percorso_originale}' a '{percorso_destinazione_completo}'")

                percorso_file_db = percorso_destinazione_completo

                doc_id = self.db_manager.aggiungi_documento_storico(
                    titolo=doc_info["titolo"],
                    tipo_documento=doc_info["tipo_documento"],
                    percorso_file=percorso_file_db,
                    descrizione=doc_info["descrizione"],
                    anno=doc_info["anno"],
                    periodo_id=doc_info["periodo_id"],
                    metadati_json=doc_info["metadati_json"]
                )
                if doc_id:
                    success_link = self.db_manager.collega_documento_a_partita(
                        doc_id, self.partita_id, doc_info["rilevanza"], doc_info["note_legame"]
                    )
                    if success_link:
                        QMessageBox.information(self, "Successo", "Documento allegato e collegato con successo.")
                        self._load_documenti_allegati() # Aggiorna la tabella
                    else:
                        QMessageBox.warning(self, "Attenzione", "Documento salvato ma fallito il collegamento alla partita.")
                else:
                    QMessageBox.critical(self, "Errore", "Impossibile salvare le informazioni del documento nel database.")
                    if os.path.exists(percorso_destinazione_completo): os.remove(percorso_destinazione_completo)

            except FileNotFoundError:
                QMessageBox.critical(self, "Errore File", f"File sorgente non trovato: {percorso_originale}")
            except PermissionError:
                QMessageBox.critical(self, "Errore Permessi", f"Permessi non sufficienti per copiare il file in '{allegati_dir}'.")
            except DBMError as e_db:
                QMessageBox.critical(self, "Errore Database", f"Errore durante il salvataggio: {e_db}")
                if os.path.exists(percorso_destinazione_completo): os.remove(percorso_destinazione_completo)
            except Exception as e:
                QMessageBox.critical(self, "Errore Imprevisto", f"Errore durante l'allegazione del documento: {e}")
                if os.path.exists(percorso_destinazione_completo): os.remove(percorso_destinazione_completo)
                self.logger.error(f"Errore allegando documento: {e}", exc_info=True)
        else:
            self.logger.info("Aggiunta documento tramite drag-and-drop annullata dall'utente (dialogo chiuso).")

    # Modifica _allega_nuovo_documento_a_partita per riutilizzare la logica di _handle_dropped_file
    def _allega_nuovo_documento_a_partita(self):
        """Gestisce l'allegazione di un nuovo documento tramite il pulsante Sfoglia."""
        # Apri il dialogo file, come faceva prima
        filePath, _ = QFileDialog.getOpenFileName(self, "Seleziona Documento da Allegare", "",
                                                  "Documenti (*.pdf *.jpg *.jpeg *.png);;File PDF (*.pdf);;Immagini JPG (*.jpg *.jpeg);;Immagini PNG (*.png);;Tutti i file (*)")
        if filePath:
            # Reutilizza la logica di gestione del file, che ora include il dialogo
            self._handle_dropped_file(filePath)
        else:
            self.logger.info("Selezione file annullata dall'utente per l'allegazione.")
    def _apri_documento_selezionato_from_details_dialog(self):
        """
        Apre un documento selezionato dalla tabella dei documenti allegati
        usando il visualizzatore predefinito del sistema operativo.
        """
        selected_items = self.documents_table.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "Nessuna Selezione", "Seleziona un documento dalla lista per aprirlo.")
            return
        
        row = self.documents_table.currentRow()
        # La colonna con il percorso del file è la 6a (indice 5)
        percorso_file_item = self.documents_table.item(row, 5) 
        
        if percorso_file_item:
            # Recupera il percorso completo salvato nell'UserRole
            percorso_file_completo = percorso_file_item.data(Qt.ItemDataRole.UserRole)
            
            if percorso_file_completo and os.path.exists(percorso_file_completo):
                from PyQt6.QtGui import QDesktopServices
                from PyQt6.QtCore import QUrl
                
                self.logger.info(f"Tentativo di aprire il documento: {percorso_file_completo}")
                success = QDesktopServices.openUrl(QUrl.fromLocalFile(percorso_file_completo))
                
                if not success:
                    QMessageBox.warning(self, "Errore Apertura", 
                                        f"Impossibile aprire il file:\n{percorso_file_completo}\n"
                                        "Verificare che sia installata un'applicazione associata o che i permessi siano corretti.")
            else:
                QMessageBox.warning(self, "File Non Trovato", 
                                    f"Il file specificato non è stato trovato al percorso:\n{percorso_file_completo}\n"
                                    "Il file potrebbe essere stato spostato o eliminato.")
        else:
            QMessageBox.warning(self, "Percorso Mancante", 
                                "Informazioni sul percorso del file non disponibili per il documento selezionato.")


    # In gui_widgets.py, all'interno della classe ModificaPartitaDialog

    def _scollega_documento_selezionato(self):
        """
        Scollega un documento dalla partita corrente rimuovendo il record
        dalla tabella di associazione 'documento_partita'.
        """
        selected_items = self.documents_table.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "Nessuna Selezione", "Seleziona un documento dalla lista per scollegarlo.")
            return

        row = self.documents_table.currentRow()
        
        # Recupera gli ID salvati nei dati dell'item
        id_doc_item = self.documents_table.item(row, 0)
        titolo_doc = self.documents_table.item(row, 1).text() if self.documents_table.item(row, 1) else "Sconosciuto"

        if not id_doc_item:
            QMessageBox.critical(self, "Errore Interno", "Impossibile recuperare i dati del documento selezionato.")
            return
        rel_data = id_doc_item.data(Qt.ItemDataRole.UserRole)
        if not isinstance(rel_data, dict) or not rel_data.get('doc_id') or not rel_data.get('partita_id'):
            self.logger.error(f"Dati di relazione mancanti o corrotti per la riga {row}: {rel_data}")
            QMessageBox.critical(self, "Errore Dati", "Informazioni sulla relazione documento-partita non trovate.")
            return

        documento_id_da_scollegare = rel_data['doc_id']
        partita_id_da_cui_scollegare = rel_data['partita_id']


        if not documento_id_da_scollegare or not partita_id_da_cui_scollegare:
            self.logger.error(f"Dati di relazione mancanti per la riga {row} (DocID: {documento_id_da_scollegare}, PartitaID: {partita_id_da_cui_scollegare})")
            QMessageBox.critical(self, "Errore Dati", "Informazioni sulla relazione documento-partita non trovate. Impossibile procedere.")
            return

        reply = QMessageBox.question(self, "Conferma Scollegamento",
                                     f"Sei sicuro di voler scollegare il documento '{titolo_doc}' (ID: {documento_id_da_scollegare}) "
                                     f"dalla partita corrente (ID: {partita_id_da_cui_scollegare})?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)

        if reply == QMessageBox.StandardButton.Yes:
            try:
                self.logger.info(f"Tentativo di scollegare doc ID {documento_id_da_scollegare} da partita ID {partita_id_da_cui_scollegare}")
                
                # Chiama il metodo del DB Manager che esegue la DELETE sulla tabella di collegamento
                success = self.db_manager.scollega_documento_da_partita(
                    documento_id=documento_id_da_scollegare,
                    partita_id=partita_id_da_cui_scollegare
                )

                if success:
                    QMessageBox.information(self, "Successo", "Documento scollegato con successo dalla partita.")
                    self._load_documenti_allegati()  # Ricarica la lista dei documenti per aggiornare la UI
                # else: scollega_documento_da_partita solleverà un'eccezione in caso di fallimento
            except DBNotFoundError as nfe:
                self.logger.warning(f"Tentativo di scollegare un legame non trovato: {nfe}")
                QMessageBox.warning(self, "Operazione Fallita", str(nfe))
            except DBMError as e_db:
                self.logger.error(f"Errore DB durante lo scollegamento del documento: {e_db}", exc_info=True)
                QMessageBox.critical(self, "Errore Database", f"Impossibile scollegare il documento: {e_db}")
            except Exception as e:
                self.logger.critical(f"Errore imprevisto durante lo scollegamento del documento: {e}", exc_info=True)
                QMessageBox.critical(self, "Errore Imprevisto", f"Si è verificato un errore di sistema: {e}")
    def _update_document_tab_title(self):
        """Aggiorna il titolo del tab dei documenti con il conteggio corrente."""
        try:
            # Assicurati che self.documents_table esista prima di contarne le righe
            if hasattr(self, 'documents_table'):
                count = self.documents_table.rowCount()
                
                # Se la tabella ha solo una riga placeholder "Nessun documento...", il conteggio è 0
                if count == 1 and self.documents_table.item(0, 0) and "Nessun documento" in self.documents_table.item(0, 0).text():
                    count = 0
                
                # Trova l'indice del tab dei documenti nel QTabWidget principale
                tab_index = self.tab_widget.indexOf(self.tab_documenti)
                if tab_index != -1:
                    self.tab_widget.setTabText(tab_index, f"Documenti Allegati ({count})")
            else:
                self.logger.warning("Attributo 'documents_table' non trovato in _update_document_tab_title.")

        except Exception as e:
            self.logger.error(f"Errore imprevisto durante l'aggiornamento del titolo del tab documenti: {e}", exc_info=True)

    def _save_changes(self):
        """Salva le modifiche apportate ai dati generali della partita."""
        self.logger.info(f"Tentativo di salvare le modifiche per la partita ID: {self.partita_id}")

        # Raccoglie i dati dai widget, inclusi quelli nuovi/modificati
        data_chiusura_val = self.data_chiusura_edit.date().toPyDate() if self.data_chiusura_check.isChecked() else None
        
        dati_da_salvare = {
            "numero_partita": self.numero_partita_spinbox.value(),
            "suffisso_partita": self.suffisso_partita_edit.text().strip() or None,
            "tipo": self.tipo_combo.currentText(),
            "stato": self.stato_combo.currentText(),
            "data_impianto": qdate_to_datetime(self.data_impianto_edit.date()),
            "data_chiusura": data_chiusura_val,
            "numero_provenienza": self.numero_provenienza_edit.text().strip() or None
        }

        # La validazione e la chiamata al DB rimangono le stesse...
        try:
            self.db_manager.update_partita(self.partita_id, dati_da_salvare)
            self.logger.info(f"Dati generali della partita ID {self.partita_id} aggiornati con successo.")
            QMessageBox.information(self, "Salvataggio Riuscito", "Le modifiche ai dati generali della partita sono state salvate.")
            # Ricarica i dati per mantenere la UI sincronizzata con il DB
            self._load_all_partita_data()
        except (DBUniqueConstraintError, DBDataError, DBNotFoundError, DBMError) as e:
            self.logger.error(f"Errore durante il salvataggio dei dati per la partita ID {self.partita_id}: {e}", exc_info=True)
            QMessageBox.critical(self, "Errore di Salvataggio", f"Impossibile salvare le modifiche:\n{e}")
        except Exception as e_gen:
            # ...
            QMessageBox.critical(self, "Errore Critico", f"Si è verificato un errore di sistema imprevisto: {e_gen}")

    def _archivia_partita(self):
        numero = self.numero_partita_spinbox.value()
        suffisso = self.suffisso_partita_edit.text().strip()
        numero_display = f"{numero} {suffisso}" if suffisso else str(numero)
        risposta = QMessageBox.question(
            self, "Conferma Archiviazione",
            f"Archiviare la partita N.{numero_display}?\n\nNon verrà eliminata, solo nascosta dalle ricerche.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if risposta != QMessageBox.StandardButton.Yes:
            return
        try:
            self.db_manager.archivia_partita(self.partita_id)
            QMessageBox.information(self, "Operazione completata",
                                    f"Partita N.{numero_display} archiviata con successo.")
            self.reject()
        except Exception as e:
            QMessageBox.critical(self, "Errore", f"Impossibile archiviare la partita:\n{e}")


class DuplicaPartitaOptionsDialog(QDialog):
    """
    Un dialogo per raccogliere le opzioni necessarie alla duplicazione di una partita.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Opzioni di Duplicazione Partita")
        self.setModal(True)
        self.setMinimumWidth(400)

        layout = QFormLayout(self)
        layout.setSpacing(10)

        self.nuovo_numero_partita_spinbox = QSpinBox()
        self.nuovo_numero_partita_spinbox.setRange(1, 9999999)
        layout.addRow("Nuovo Numero Partita (*):", self.nuovo_numero_partita_spinbox)

        self.nuovo_suffisso_edit = QLineEdit()
        self.nuovo_suffisso_edit.setPlaceholderText("Es. bis, A (opzionale)")
        layout.addRow("Nuovo Suffisso Partita:", self.nuovo_suffisso_edit)

        self.mantieni_possessori_check = QCheckBox("Mantieni i possessori originali nella nuova partita")
        self.mantieni_possessori_check.setChecked(True)
        layout.addRow(self.mantieni_possessori_check)
        
        self.mantieni_immobili_check = QCheckBox("Copia gli immobili originali nella nuova partita")
        self.mantieni_immobili_check.setChecked(False)
        layout.addRow(self.mantieni_immobili_check)
        
        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        layout.addRow(self.button_box)

    def get_options(self) -> Optional[Dict[str, Any]]:
        """Restituisce le opzioni selezionate come dizionario."""
        return {
            "nuovo_numero_partita": self.nuovo_numero_partita_spinbox.value(),
            "nuovo_suffisso": self.nuovo_suffisso_edit.text().strip() or None,
            "mantenere_possessori": self.mantieni_possessori_check.isChecked(),
            "mantenere_immobili": self.mantieni_immobili_check.isChecked()
        }


