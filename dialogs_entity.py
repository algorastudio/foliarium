"""
dialogs_entity.py — Dialog per la gestione di possessori, comuni, localita e periodi storici.

Classi estratte da dialogs.py:
  DettagliLegamePossessoreDialog, ModificaPossessoreDialog, ModificaComuneDialog,
  PossessoriComuneDialog, PartiteComuneDialog, ModificaLocalitaDialog,
  PeriodoStoricoDetailsDialog, ComuneSelectionDialog, PartitaSearchDialog,
  CreatePossessoreDialog, LocalitaSelectionDialog, PeriodoStoricoEditDialog
"""
from __future__ import annotations

import logging
import os
from datetime import date, datetime
from typing import Optional, List, Dict, Any, Tuple

from PyQt6.QtCore import (QDate, QDateTime, QPoint, QSettings,
                          QSize, Qt, QUrl, pyqtSignal)
from PyQt6.QtGui import (QBrush, QColor, QDesktopServices, QFont,
                         QIcon, QPalette, QAction)
from PyQt6.QtWidgets import (QAbstractItemView, QApplication,
                             QCheckBox, QComboBox, QDateEdit,
                             QDialog, QDialogButtonBox, QDoubleSpinBox,
                             QFileDialog, QFormLayout, QFrame, QGridLayout,
                             QGroupBox, QHBoxLayout, QHeaderView, QInputDialog,
                             QLabel, QLineEdit, QListWidget, QListWidgetItem,
                             QMenu, QMessageBox,
                             QPushButton, QScrollArea, QSizePolicy, QSpacerItem,
                             QSpinBox, QStyle, QTabWidget,
                             QSplitter, QTableWidget, QTableWidgetItem, QTextEdit,
                             QTreeWidget, QTreeWidgetItem,
                             QVBoxLayout, QWidget,
                             QTextBrowser, QDialogButtonBox)

from catasto_db_manager import CatastoDBManager
from custom_widgets import ImmobiliTableWidget

try:
    from catasto_db_manager import DBMError, DBUniqueConstraintError, DBNotFoundError, DBDataError
except ImportError:
    class DBMError(Exception): pass
    class DBUniqueConstraintError(DBMError): pass
    class DBNotFoundError(DBMError): pass
    class DBDataError(DBMError): pass

class DettagliLegamePossessoreDialog(QDialog):
    def __init__(self, nome_possessore_selezionato: str, partita_tipo: str,
                 titolo_attuale: Optional[str] = None,  # Nuovo
                 quota_attuale: Optional[str] = None,   # Nuovo
                 parent=None):
        super().__init__(parent)
        self.setWindowTitle(
            f"Dettagli Legame per {nome_possessore_selezionato}")
        self.setMinimumWidth(400)

        self.titolo: Optional[str] = None
        self.quota: Optional[str] = None
        # self.tipo_partita_rel: str = partita_tipo

        layout = QFormLayout(self)

        self.titolo_edit = QLineEdit()
        self.titolo_edit.setPlaceholderText(
            "Es. proprietà esclusiva, usufrutto")
        self.titolo_edit.setText(
            titolo_attuale if titolo_attuale is not None else "proprietà esclusiva")  # Pre-compila
        layout.addRow("Titolo di Possesso (*):", self.titolo_edit)

        self.quota_edit = QLineEdit()
        self.quota_edit.setPlaceholderText(
            "Es. 1/1, 1/2 (lasciare vuoto se non applicabile)")
        self.quota_edit.setText(
            quota_attuale if quota_attuale is not None else "")  # Pre-compila
        layout.addRow("Quota (opzionale):", self.quota_edit)

        # ... (pulsanti OK/Annulla e metodo _accept_details come prima) ...
        buttons_layout = QHBoxLayout()
        self.ok_button = QPushButton(
            QApplication.style().standardIcon(QStyle.StandardPixmap.SP_DialogOkButton), "OK")
        self.ok_button.clicked.connect(self._accept_details)
        self.cancel_button = QPushButton(QApplication.style().standardIcon(
            QStyle.StandardPixmap.SP_DialogCancelButton), "Annulla")
        self.cancel_button.clicked.connect(self.reject)
        buttons_layout.addStretch()
        buttons_layout.addWidget(self.ok_button)
        buttons_layout.addWidget(self.cancel_button)
        layout.addRow(buttons_layout)
        self.setLayout(layout)
        self.titolo_edit.setFocus()

    def _accept_details(self):
        # ... (come prima) ...
        titolo_val = self.titolo_edit.text().strip()
        if not titolo_val:
            QMessageBox.warning(self, "Dato Mancante",
                                "Il titolo di possesso è obbligatorio.")
            self.titolo_edit.setFocus()
            return
        self.titolo = titolo_val
        self.quota = self.quota_edit.text().strip() or None
        self.accept()

    # Metodo statico per l'inserimento (come prima)

    @staticmethod
    def get_details_for_new_legame(nome_possessore: str, tipo_partita_attuale: str, parent=None) -> Optional[Dict[str, Any]]:
        # Chiamiamo il costruttore senza titolo_attuale e quota_attuale,
        # così userà i default (None) e quindi il testo placeholder o il default "proprietà esclusiva"
        dialog = DettagliLegamePossessoreDialog(
            nome_possessore_selezionato=nome_possessore,
            partita_tipo=tipo_partita_attuale,
            # titolo_attuale e quota_attuale non vengono passati,
            # quindi __init__ userà i loro valori di default (None)
            parent=parent
        )
        if dialog.exec() == QDialog.DialogCode.Accepted:
            return {
                "titolo": dialog.titolo,
                "quota": dialog.quota,
                # "tipo_partita_rel": dialog.tipo_partita_rel # Se lo gestisci
            }
        return None

    # NUOVO Metodo statico per la modifica
    @staticmethod
    def get_details_for_edit_legame(nome_possessore: str, tipo_partita_attuale: str,
                                    titolo_init: str, quota_init: Optional[str],
                                    parent=None) -> Optional[Dict[str, Any]]:
        dialog = DettagliLegamePossessoreDialog(nome_possessore, tipo_partita_attuale,
                                                titolo_attuale=titolo_init,
                                                quota_attuale=quota_init,
                                                parent=parent)
        # Titolo specifico per modifica
        dialog.setWindowTitle(f"Modifica Legame per {nome_possessore}")
        if dialog.exec() == QDialog.DialogCode.Accepted:
            return {
                "titolo": dialog.titolo,
                "quota": dialog.quota,
            }
        return None


class ModificaPossessoreDialog(QDialog):
    def __init__(self, db_manager: CatastoDBManager, possessore_id: int, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.possessore_id = possessore_id
        self.possessore_data_originale = None
        self.logger = logging.getLogger(f"CatastoGUI.{self.__class__.__name__}")
        # Per l'audit, se vuoi confrontare i dati vecchi e nuovi
        # self.current_user_info = getattr(QApplication.instance().main_window, 'logged_in_user_info', None) # Modo per prendere utente
        # se main_window è accessibile

        self.setWindowTitle(
            f"Modifica Dati Possessore ID: {self.possessore_id}")
        self.setMinimumWidth(450)

        self._init_ui()
        self._load_possessore_data()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        form_layout = QFormLayout()

        self.id_label = QLabel(str(self.possessore_id))
        form_layout.addRow("ID Possessore:", self.id_label)

        self.nome_completo_edit = QLineEdit()
        form_layout.addRow("Nome Completo (*):", self.nome_completo_edit)

        # Campo che avevi nello schema per ricerca/ordinamento
        self.cognome_nome_edit = QLineEdit()
        form_layout.addRow("Cognome e Nome (per ricerca):",
                           self.cognome_nome_edit)

        self.paternita_edit = QLineEdit()
        form_layout.addRow("Paternità:", self.paternita_edit)
        
        # --- INIZIO NUOVA AGGIUNTA: Pulsante Genera Nome Completo ---
        self.btn_genera_nome_completo = QPushButton("Genera Nome Completo")
        # Collega il pulsante al nuovo metodo _genera_nome_completo
        self.btn_genera_nome_completo.clicked.connect(self._genera_nome_completo)
        # Aggiungi il pulsante al layout (es. sotto Paternità o tra i campi)
        form_layout.addRow(self.btn_genera_nome_completo) 
        # --- FINE NUOVA AGGIUNTA ---

        self.attivo_checkbox = QCheckBox("Possessore Attivo")
        form_layout.addRow(self.attivo_checkbox)

        # Comune di Riferimento
        comune_ref_layout = QHBoxLayout()
        self.comune_ref_label = QLabel(
            "Comune non specificato")  # Verrà popolato
        self.btn_cambia_comune_ref = QPushButton("Cambia...")
        self.btn_cambia_comune_ref.clicked.connect(
            self._cambia_comune_riferimento)
        comune_ref_layout.addWidget(self.comune_ref_label)
        comune_ref_layout.addStretch()
        comune_ref_layout.addWidget(self.btn_cambia_comune_ref)
        form_layout.addRow("Comune di Riferimento:", comune_ref_layout)

        # ID del comune di riferimento (nascosto, ma utile da tenere)
        self.selected_comune_ref_id: Optional[int] = None

        layout.addLayout(form_layout)

        # Pulsanti
        buttons_layout = QHBoxLayout()
        self.save_button = QPushButton(QApplication.style().standardIcon(
            QStyle.StandardPixmap.SP_DialogSaveButton), "Salva Modifiche")
        self.save_button.clicked.connect(self._save_changes)
        self.cancel_button = QPushButton(QApplication.style().standardIcon(
            QStyle.StandardPixmap.SP_DialogCancelButton), "Annulla")
        self.cancel_button.clicked.connect(self.reject)

        buttons_layout.addStretch()
        buttons_layout.addWidget(self.save_button)
        buttons_layout.addWidget(self.cancel_button)
        layout.addLayout(buttons_layout)

        self.setLayout(layout)
        
    def _genera_nome_completo(self):
        """
        Genera il campo 'Nome Completo' dalla concatenazione di 'Cognome e Nome' e 'Paternità'.
        """
        cognome_nome = self.cognome_nome_edit.text().strip()
        paternita = self.paternita_edit.text().strip()

        if cognome_nome and paternita:
            full_name = f"{cognome_nome} di {paternita}"
        elif cognome_nome:
            full_name = cognome_nome
        else:
            full_name = "" # O "N/D" a seconda delle preferenze

        self.nome_completo_edit.setText(full_name)
        self.logger.debug(f"Nome completo generato: '{full_name}'")

    def _load_possessore_data(self):
        # Metodo da creare in CatastoDBManager: get_possessore_details(possessore_id)
        # Dovrebbe restituire un dizionario con tutti i campi di possessore,
        # incluso comune_id e il nome del comune (comune_riferimento_nome).
        self.possessore_data_originale = self.db_manager.get_possessore_full_details(
            self.possessore_id)  # Rinominato per chiarezza

        if not self.possessore_data_originale:
            QMessageBox.critical(self, "Errore Caricamento",
                                 f"Impossibile caricare i dati per il possessore ID: {self.possessore_id}.\n"
                                 "Il dialogo verrà chiuso.")
            from PyQt6.QtCore import QTimer
            # Chiudi dopo che il messaggio è stato processato
            QTimer.singleShot(0, self.reject)
            return

        self.nome_completo_edit.setText(
            self.possessore_data_originale.get('nome_completo', ''))
        self.cognome_nome_edit.setText(self.possessore_data_originale.get(
            'cognome_nome', ''))
        self.paternita_edit.setText(
            self.possessore_data_originale.get('paternita', ''))
        self.attivo_checkbox.setChecked(
            self.possessore_data_originale.get('attivo', True))

        self.selected_comune_ref_id = self.possessore_data_originale.get(
            'comune_riferimento_id')  # Salva l'ID
        nome_comune_ref = self.possessore_data_originale.get(
            'comune_riferimento_nome', "Nessun comune assegnato")
        self.comune_ref_label.setText(
            f"{nome_comune_ref} (ID: {self.selected_comune_ref_id or 'N/A'})")

    def _cambia_comune_riferimento(self):
        # Usa ComuneSelectionDialog per cambiare il comune di riferimento
        dialog = ComuneSelectionDialog(
            self.db_manager, self, title="Seleziona Nuovo Comune di Riferimento")
        if dialog.exec() == QDialog.DialogCode.Accepted and dialog.selected_comune_id:
            self.selected_comune_ref_id = dialog.selected_comune_id
            self.comune_ref_label.setText(
                f"{dialog.selected_comune_name} (ID: {self.selected_comune_ref_id})")
            logging.getLogger("CatastoGUI").info(
                f"Nuovo comune di riferimento selezionato per possessore (non ancora salvato): ID {self.selected_comune_ref_id}, Nome: {dialog.selected_comune_name}")

    def _save_changes(self):
        logging.getLogger("CatastoGUI").info(
            # NUOVA STAMPA
            f"DEBUG: _save_changes chiamato per possessore ID {self.possessore_id}")
        dati_modificati = {
            "nome_completo": self.nome_completo_edit.text().strip(),
            "cognome_nome": self.cognome_nome_edit.text().strip() or None,  # Può essere nullo
            "paternita": self.paternita_edit.text().strip() or None,    # Può essere nullo
            "attivo": self.attivo_checkbox.isChecked(),
            "comune_riferimento_id": self.selected_comune_ref_id,  # L'ID del comune selezionato
        }
        logging.getLogger("CatastoGUI").info(
            f"DEBUG: Dati dalla UI: {dati_modificati}")  # NUOVA STAMPA

        if not dati_modificati["nome_completo"]:
            QMessageBox.warning(
                self, "Dati Mancanti", "Il 'Nome Completo' del possessore è obbligatorio.")
            self.nome_completo_edit.setFocus()
            return

        if dati_modificati["comune_riferimento_id"] is None:
            QMessageBox.warning(self, "Dati Mancanti",
                                "Il 'Comune di Riferimento' è obbligatorio.")
            # Non c'è un campo input diretto per il focus, ma l'utente deve usare il pulsante
            self.btn_cambia_comune_ref.setFocus()
            return

        try:
            logging.getLogger("CatastoGUI").info(
                # NUOVA STAMPA
                f"DEBUG: Chiamata a db_manager.update_possessore per ID {self.possessore_id}")
            logging.getLogger("CatastoGUI").info(
                f"Tentativo di aggiornare il possessore ID {self.possessore_id} con i dati: {dati_modificati}")
            # Metodo da creare in CatastoDBManager: update_possessore(possessore_id, dati_modificati)
            self.db_manager.update_possessore(
                self.possessore_id, dati_modificati)

            logging.getLogger("CatastoGUI").info(
                f"Possessore ID {self.possessore_id} aggiornato con successo.")
            logging.getLogger("CatastoGUI").info(
                # NUOVA STAMPA
                f"DEBUG: db_manager.update_possessore completato per ID {self.possessore_id}")
            self.accept()  # Chiude il dialogo e restituisce QDialog.DialogCode.Accepted

        # Gestione eccezioni simile a quella di update_partita (DBUniqueConstraintError, DBDataError, DBMError, etc.)
        # Ad esempio, se nome_completo + comune_id deve essere univoco, o altri vincoli.
        # Per ora, un gestore generico per errori DB e altri errori.
        except (DBMError, DBDataError) as dbe_poss:  # Usa le tue eccezioni personalizzate
            logging.getLogger("CatastoGUI").error(
                f"Errore DB durante aggiornamento possessore ID {self.possessore_id}: {dbe_poss}", exc_info=True)
            QMessageBox.critical(self, "Errore Database",
                                 f"Errore durante il salvataggio delle modifiche al possessore:\n{dbe_poss.message if hasattr(dbe_poss, 'message') else str(dbe_poss)}")
        except AttributeError as ae:
            logging.getLogger("CatastoGUI").critical(
                f"Metodo 'update_possessore' non trovato o altro AttributeError: {ae}", exc_info=True)
            QMessageBox.critical(self, "Errore Implementazione",
                                 "Funzionalità per aggiornare possessore non completamente implementata o errore interno.")
        except Exception as e_poss:
            logging.getLogger("CatastoGUI").critical(
                f"Errore critico imprevisto durante il salvataggio del possessore ID {self.possessore_id}: {e_poss}", exc_info=True)
            QMessageBox.critical(self, "Errore Critico Imprevisto",
                                 f"Si è verificato un errore di sistema imprevisto:\n{type(e_poss).__name__}: {e_poss}")
# In dialogs.py, SOSTITUISCI l'intera classe ModificaComuneDialog con questa:


class ModificaComuneDialog(QDialog):
    def __init__(self, db_manager: 'CatastoDBManager', comune_id: int, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.comune_id = comune_id
        self.comune_data_originale: Optional[Dict[str, Any]] = None
        self.logger = logging.getLogger(f"CatastoGUI.{self.__class__.__name__}")

        self.setWindowTitle(f"Modifica Dati Comune ID: {self.comune_id}")
        self.setMinimumWidth(450)
        self.setModal(True)

        self._initUI()
        self._load_comune_data()

    def _initUI(self):
        main_layout = QVBoxLayout(self)
        form_layout = QFormLayout()
        form_layout.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapAllRows)
        form_layout.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)

        self.id_label = QLabel(str(self.comune_id))
        form_layout.addRow("ID Comune:", self.id_label)

        self.nome_edit = QLineEdit()
        form_layout.addRow("Nome Comune (*):", self.nome_edit)

        self.provincia_edit = QLineEdit()
        self.provincia_edit.setMaxLength(100)
        form_layout.addRow("Provincia (*):", self.provincia_edit)

        self.regione_edit = QLineEdit()
        form_layout.addRow("Regione (*):", self.regione_edit)

        # Il codice per questi campi non era presente nella tua classe,
        # ma lo aggiungo per coerenza con lo schema della tabella 'comune'
        # Se non esistono nel tuo DB, puoi rimuovere le righe corrispondenti.
        self.codice_catastale_edit = QLineEdit()
        self.codice_catastale_edit.setPlaceholderText("Es. A123 (opzionale)")
        form_layout.addRow("Codice Catastale:", self.codice_catastale_edit)

        # --- MODIFICA CHIAVE: Sostituzione SpinBox con ComboBox ---
        self.periodo_combo = QComboBox()
        form_layout.addRow("Periodo Storico:", self.periodo_combo)
        # --- FINE MODIFICA ---

        self.data_istituzione_edit = QDateEdit(calendarPopup=True)
        self.data_istituzione_edit.setDisplayFormat("yyyy-MM-dd")
        self.data_istituzione_edit.setSpecialValueText(" ")
        self.data_istituzione_edit.setDate(QDate())
        form_layout.addRow("Data Istituzione:", self.data_istituzione_edit)
        
        self.data_soppressione_edit = QDateEdit(calendarPopup=True)
        self.data_soppressione_edit.setDisplayFormat("yyyy-MM-dd")
        self.data_soppressione_edit.setSpecialValueText(" ")
        self.data_soppressione_edit.setDate(QDate())
        form_layout.addRow("Data Soppressione:", self.data_soppressione_edit)

        self.note_edit = QTextEdit()
        self.note_edit.setMinimumHeight(80)
        form_layout.addRow("Note:", self.note_edit)

        main_layout.addLayout(form_layout)

        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        self.button_box.accepted.connect(self._save_changes)
        self.button_box.rejected.connect(self.reject)
        main_layout.addWidget(self.button_box)

        self.setLayout(main_layout)

    def _load_comune_data(self):
        # Per prima cosa, carichiamo tutti i periodi disponibili nel ComboBox
        try:
            periodi = self.db_manager.get_historical_periods()
            self.periodo_combo.clear()
            self.periodo_combo.addItem("--- Nessuno ---", None)
            for p in periodi:
                display_text = f"{p.get('nome')} ({p.get('anno_inizio')} - {p.get('anno_fine', 'oggi')})"
                self.periodo_combo.addItem(display_text, p.get('id'))
        except DBMError as e:
            self.logger.error(f"Impossibile caricare i periodi storici nel dialogo di modifica: {e}")
            self.periodo_combo.addItem("Errore caricamento periodi", None)

        # Ora carichiamo i dati specifici del comune da modificare
        all_comuni = self.db_manager.get_all_comuni_details()
        found_comune = next((c for c in all_comuni if c.get('id') == self.comune_id), None)
        
        if not found_comune:
            QMessageBox.critical(self, "Errore Caricamento", f"Impossibile caricare dati per Comune ID: {self.comune_id}.")
            QTimer.singleShot(0, self.reject)
            return
        
        self.comune_data_originale = found_comune
        
        # Popoliamo i campi della UI con i dati caricati
        self.nome_edit.setText(self.comune_data_originale.get('nome_comune', ''))
        self.provincia_edit.setText(self.comune_data_originale.get('provincia', ''))
        self.regione_edit.setText(self.comune_data_originale.get('regione', ''))
        self.codice_catastale_edit.setText(self.comune_data_originale.get('codice_catastale', ''))
        self.note_edit.setText(self.comune_data_originale.get('note', ''))

        # --- MODIFICA CHIAVE: Selezioniamo il periodo corretto nel ComboBox ---
        periodo_id_attuale = self.comune_data_originale.get('periodo_id')
        if periodo_id_attuale is not None:
            index = self.periodo_combo.findData(periodo_id_attuale)
            if index != -1:
                self.periodo_combo.setCurrentIndex(index)
        else:
            self.periodo_combo.setCurrentIndex(0) # Seleziona "--- Nessuno ---"
        # --- FINE MODIFICA ---

        # Gestione date
        di_str = self.comune_data_originale.get('data_istituzione'); self.data_istituzione_edit.setDate(QDate.fromString(str(di_str), "yyyy-MM-dd") if di_str else QDate())
        ds_str = self.comune_data_originale.get('data_soppressione'); self.data_soppressione_edit.setDate(QDate.fromString(str(ds_str), "yyyy-MM-dd") if ds_str else QDate())

    def _save_changes(self):
        # --- MODIFICA CHIAVE: Lettura dati dal ComboBox ---
        periodo_id_selezionato = self.periodo_combo.currentData()
        # --- FINE MODIFICA ---

        dati_modificati = {
            "nome": self.nome_edit.text().strip(),
            "provincia": self.provincia_edit.text().strip().upper(),
            "regione": self.regione_edit.text().strip(),
            "codice_catastale": self.codice_catastale_edit.text().strip() or None,
            "periodo_id": periodo_id_selezionato, # Usa il valore dal ComboBox
            "data_istituzione": self.data_istituzione_edit.date().toPyDate() if self.data_istituzione_edit.date().isValid() and self.data_istituzione_edit.text().strip() else None,
            "data_soppressione": self.data_soppressione_edit.date().toPyDate() if self.data_soppressione_edit.date().isValid() and self.data_soppressione_edit.text().strip() else None,
            "note": self.note_edit.toPlainText().strip() or None,
        }

        # La logica di validazione e salvataggio rimane la stessa
        try:
            success = self.db_manager.update_comune(self.comune_id, dati_modificati)
            if success:
                QMessageBox.information(self, "Successo", "Dati del comune aggiornati con successo.")
                self.accept()
        except (DBNotFoundError, DBUniqueConstraintError, DBDataError, DBMError) as e:
            QMessageBox.critical(self, "Errore Salvataggio", str(e))
        except Exception as e_gen:
            QMessageBox.critical(self, "Errore Imprevisto", f"Si è verificato un errore: {str(e_gen)}")


class PossessoriComuneDialog(QDialog):
    def __init__(self, db_manager: CatastoDBManager, comune_id: int, nome_comune: str, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.comune_id = comune_id
        self.nome_comune = nome_comune
        self.logger = logging.getLogger(f"CatastoGUI.{self.__class__.__name__}")

        self.setWindowTitle(
            f"Possessori del Comune di {self.nome_comune} (ID: {self.comune_id})")
        self.setMinimumSize(800, 500)

        layout = QVBoxLayout(self)
        # --- SEZIONE FILTRO (NUOVA) ---
        filter_layout = QHBoxLayout()
        filter_label = QLabel("Filtra possessori:")
        self.filter_edit = QLineEdit()
        self.filter_edit.setPlaceholderText("Digita per filtrare (nome completo, cognome, paternità)...")
        
        self.filter_button = QPushButton("Applica Filtro")
        self.filter_button.clicked.connect(self.load_possessori_data) # Ricarica i dati con il filtro
        
        filter_layout.addWidget(filter_label)
        filter_layout.addWidget(self.filter_edit)
        filter_layout.addWidget(self.filter_button)
        layout.addLayout(filter_layout)
        # --- FINE SEZIONE FILTRO ---
        # Tabella Possessori (come prima)
        self.possessori_table = QTableWidget()
        self.possessori_table.setColumnCount(5)
        self.possessori_table.setHorizontalHeaderLabels([
            "ID Poss.", "Nome Completo", "Cognome Nome", "Paternità", "Stato"
        ])
        self.possessori_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.possessori_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.possessori_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.possessori_table.setAlternatingRowColors(True)
        self.possessori_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch)  # o ResizeToContents
        self.possessori_table.setSortingEnabled(True)
        self.possessori_table.itemSelectionChanged.connect(
            self._aggiorna_stato_pulsanti_azione)  # NUOVO
        self.possessori_table.itemDoubleClicked.connect(
            self.apri_modifica_possessore_selezionato)  # NUOVO per doppio click

        layout.addWidget(self.possessori_table)

        # --- NUOVI Pulsanti di Azione ---
        action_layout = QHBoxLayout()
        self.btn_modifica_possessore = QPushButton(QApplication.style().standardIcon(
            QStyle.StandardPixmap.SP_FileDialogDetailedView), "Modifica Selezionato")
        self.btn_modifica_possessore.setToolTip(
            "Modifica i dati del possessore selezionato")
        self.btn_modifica_possessore.clicked.connect(
            self.apri_modifica_possessore_selezionato)
        self.btn_modifica_possessore.setEnabled(
            False)  # Inizialmente disabilitato
        action_layout.addWidget(self.btn_modifica_possessore)

        action_layout.addStretch()  # Spazio

        self.close_button = QPushButton("Chiudi")  # Pulsante Chiudi esistente
        self.close_button.clicked.connect(self.accept)
        action_layout.addWidget(self.close_button)

        layout.addLayout(action_layout)
        # --- FINE NUOVI Pulsanti di Azione ---

        self.setLayout(layout)
        self.load_possessori_data()

    def _aggiorna_stato_pulsanti_azione(self):
        """Abilita/disabilita i pulsanti di azione in base alla selezione nella tabella."""
        has_selection = bool(self.possessori_table.selectedItems())
        self.btn_modifica_possessore.setEnabled(has_selection)

    def _get_selected_possessore_id(self) -> Optional[int]:
        """Restituisce l'ID del possessore attualmente selezionato nella tabella."""
        selected_items = self.possessori_table.selectedItems()
        if not selected_items:
            return None

        current_row = self.possessori_table.currentRow()
        if current_row < 0:
            return None

        # Colonna ID Poss.
        id_item = self.possessori_table.item(current_row, 0)
        if id_item and id_item.text().isdigit():
            return int(id_item.text())
        return None

    def apri_modifica_possessore_selezionato(self):
        logging.getLogger("CatastoGUI").debug(
            "DEBUG: apri_modifica_possessore_selezionato chiamato.")  # NUOVA STAMPA
        possessore_id = self._get_selected_possessore_id()
        if possessore_id is not None:
            logging.getLogger("CatastoGUI").debug(
                # NUOVA STAMPA
                f"DEBUG: ID Possessore selezionato: {possessore_id}")
            dialog = ModificaPossessoreDialog(
                self.db_manager, possessore_id, self)

            dialog_result = dialog.exec()  # Salva il risultato
            logging.getLogger("CatastoGUI").debug(
                # NUOVA STAMPA
                f"DEBUG: ModificaPossessoreDialog.exec() restituito: {dialog_result} (Accepted è {QDialog.DialogCode.Accepted})")

            if dialog_result == QDialog.DialogCode.Accepted:
                logging.getLogger("CatastoGUI").info(
                    "DEBUG: ModificaPossessoreDialog accettato. Ricaricamento dati possessori...")  # NUOVA STAMPA
                QMessageBox.information(self, "Modifica Possessore",
                                        "Modifiche al possessore salvate con successo.")
                self.load_possessori_data()
            else:
                logging.getLogger("CatastoGUI").info(
                    # NUOVA STAMPA
                    "DEBUG: ModificaPossessoreDialog non accettato (probabilmente Annulla o errore nel salvataggio).")
        else:
            logging.getLogger("CatastoGUI").warning(
                "DEBUG: Tentativo di modificare possessore, ma nessun ID selezionato.")  # NUOVA STAMPA
            QMessageBox.warning(self, "Nessuna Selezione",
                                "Per favore, seleziona un possessore dalla tabella da modificare.")

    def load_possessori_data(self):
        """Carica i possessori per il comune specificato, applicando il filtro."""
        self.possessori_table.setRowCount(0)
        self.possessori_table.setSortingEnabled(False)
        
        filter_text = self.filter_edit.text().strip() # Ottieni il testo del filtro

        try:
            # Modifica il db_manager.get_possessori_by_comune per accettare un filtro testuale.
            # Se non hai ancora modificato get_possessori_by_comune, vedi la nota sotto.
            possessori_list = self.db_manager.get_possessori_by_comune(
                self.comune_id, filter_text=filter_text if filter_text else None
            )
            
            if possessori_list:
                self.possessori_table.setRowCount(len(possessori_list))
                for row_idx, possessore in enumerate(possessori_list):
                    col = 0
                    self.possessori_table.setItem(
                        row_idx, col, QTableWidgetItem(str(possessore.get('id', ''))))
                    col += 1
                    self.possessori_table.setItem(row_idx, col, QTableWidgetItem(
                        possessore.get('nome_completo', '')))
                    col += 1
                    self.possessori_table.setItem(
                        row_idx, col, QTableWidgetItem(possessore.get('cognome_nome', '')))
                    col += 1
                    self.possessori_table.setItem(
                        row_idx, col, QTableWidgetItem(possessore.get('paternita', '')))
                    col += 1
                    stato_str = "Attivo" if possessore.get('attivo', False) else "Non Attivo"
                    self.possessori_table.setItem(
                        row_idx, col, QTableWidgetItem(stato_str))
                    col += 1
                self.possessori_table.resizeColumnsToContents()
            else:
                self.logger.info(f"Nessun possessore trovato per il comune ID: {self.comune_id} con filtro '{filter_text}'.")
                # Visualizza un messaggio nella tabella se nessun risultato
                self.possessori_table.setRowCount(1)
                item = QTableWidgetItem("Nessun possessore trovato con i criteri specificati.")
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.possessori_table.setItem(0, 0, item)
                self.possessori_table.setSpan(0, 0, 1, self.possessori_table.columnCount())

        except Exception as e:
            self.logger.error(f"Errore durante il caricamento dei possessori per comune ID {self.comune_id}: {e}", exc_info=True)
            QMessageBox.critical(self, "Errore Caricamento Dati", f"Si è verificato un errore: {e}")
            # Visualizza un messaggio di errore nella tabella
            self.possessori_table.setRowCount(1)
            item = QTableWidgetItem(f"Errore nel caricamento dei dati: {e}")
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.possessori_table.setItem(0, 0, item)
            self.possessori_table.setSpan(0, 0, 1, self.possessori_table.columnCount())
        finally:
            self.possessori_table.setSortingEnabled(True)
            self._aggiorna_stato_pulsanti_azione()



class PartiteComuneDialog(QDialog):
    def __init__(self, db_manager: CatastoDBManager, comune_id: int, nome_comune: str, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.comune_id = comune_id
        self.nome_comune = nome_comune
        self.logger = logging.getLogger(f"CatastoGUI.{self.__class__.__name__}")

        self.setWindowTitle(
            f"Partite del Comune di {self.nome_comune} (ID: {self.comune_id})")
        self.setMinimumSize(850, 550)

        layout = QVBoxLayout(self)

        filter_layout = QHBoxLayout()
        filter_label = QLabel("Filtra partite:")
        self.filter_edit = QLineEdit()
        self.filter_edit.setPlaceholderText("Digita per filtrare (numero, tipo, stato, suffisso)...")
        
        self.filter_button = QPushButton("Applica Filtro")
        self.filter_button.clicked.connect(self.load_partite_data)
        
        filter_layout.addWidget(filter_label)
        filter_layout.addWidget(self.filter_edit)
        filter_layout.addWidget(self.filter_button)
        layout.addLayout(filter_layout)

        self.partite_table = QTableWidget()
        
        # MODIFICA QUI: Imposta le intestazioni corrette una sola volta
        self.partite_table.setColumnCount(9) 
        self.partite_table.setHorizontalHeaderLabels([
            "ID Partita", "Numero", "Suffisso", "Tipo", "Stato", 
            "Data Impianto", "Num. Possessori", "Num. Immobili", "Num. Documenti"
        ])

        self.partite_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.partite_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.partite_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.partite_table.setAlternatingRowColors(True)
        self.partite_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.partite_table.setSortingEnabled(True)
        self.partite_table.itemDoubleClicked.connect(self.apri_dettaglio_partita_selezionata)
        self.partite_table.itemSelectionChanged.connect(self._aggiorna_stato_pulsante_modifica)

        layout.addWidget(self.partite_table)

        action_buttons_layout = QHBoxLayout()
        self.btn_apri_dettaglio = QPushButton(QApplication.style().standardIcon(
            QStyle.StandardPixmap.SP_FileDialogInfoView), "Vedi Dettagli")
        self.btn_apri_dettaglio.clicked.connect(self.apri_dettaglio_partita_selezionata_da_pulsante)
        self.btn_apri_dettaglio.setEnabled(False)
        action_buttons_layout.addWidget(self.btn_apri_dettaglio)

        self.btn_modifica_partita = QPushButton("Modifica Partita")
        self.btn_modifica_partita.setToolTip("Modifica i dati della partita selezionata")
        self.btn_modifica_partita.clicked.connect(self.apri_modifica_partita_selezionata)
        self.btn_modifica_partita.setEnabled(False)
        action_buttons_layout.addWidget(self.btn_modifica_partita)

        action_buttons_layout.addStretch()

        self.close_button = QPushButton("Chiudi")
        self.close_button.clicked.connect(self.accept)
        action_buttons_layout.addWidget(self.close_button)

        layout.addLayout(action_buttons_layout)

        self.setLayout(layout)
        self.load_partite_data()

    def load_partite_data(self):
        self.partite_table.setRowCount(0)
        self.partite_table.setSortingEnabled(False)
        
        # Le intestazioni sono già state impostate nell'__init__
        # Non è necessario reimpostarle qui.

        filter_text = self.filter_edit.text().strip()

        try:
            partite_list = self.db_manager.get_partite_by_comune(
                self.comune_id, filter_text=filter_text if filter_text else None
            )

            if partite_list:
                self.partite_table.setRowCount(len(partite_list))
                for row_idx, partita in enumerate(partite_list):
                    col = 0
                    self.partite_table.setItem(row_idx, col, QTableWidgetItem(str(partita.get('id', '')))); col += 1
                    self.partite_table.setItem(row_idx, col, QTableWidgetItem(str(partita.get('numero_partita', '')))); col += 1
                    self.partite_table.setItem(row_idx, col, QTableWidgetItem(partita.get('suffisso_partita', '') or '')); col += 1 
                    self.partite_table.setItem(row_idx, col, QTableWidgetItem(partita.get('tipo', ''))); col += 1
                    self.partite_table.setItem(row_idx, col, QTableWidgetItem(partita.get('stato', ''))); col += 1
                    data_imp = partita.get('data_impianto')
                    self.partite_table.setItem(row_idx, col, QTableWidgetItem(str(data_imp) if data_imp else '')); col += 1
                    self.partite_table.setItem(row_idx, col, QTableWidgetItem(str(partita.get('num_possessori', '0')))); col += 1
                    self.partite_table.setItem(row_idx, col, QTableWidgetItem(str(partita.get('num_immobili', '0')))); col += 1
                    
                    # --- NUOVA RIGA PER IL NUMERO DEI DOCUMENTI ---
                    self.partite_table.setItem(row_idx, col, QTableWidgetItem(str(partita.get('num_documenti_allegati', '0')))); col += 1

                self.partite_table.resizeColumnsToContents()
            else:
                self.logger.info(f"Nessuna partita trovata per il comune ID: {self.comune_id} con filtro '{filter_text}'.")
                self.partite_table.setRowCount(1)
                item = QTableWidgetItem("Nessuna partita trovata con i criteri specificati.")
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.partite_table.setItem(0, 0, item)
                self.partite_table.setSpan(0, 0, 1, self.partite_table.columnCount())

        except Exception as e:
            self.logger.error(f"Errore durante il caricamento delle partite per comune ID {self.comune_id}: {e}", exc_info=True)
            QMessageBox.critical(self, "Errore Caricamento Dati", f"Si è verificato un errore: {e}")
            self.partite_table.setRowCount(1)
            item = QTableWidgetItem(f"Errore nel caricamento dei dati: {e}")
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.partite_table.setItem(0, 0, item)
            self.partite_table.setSpan(0, 0, 1, self.partite_table.columnCount())
        finally:
            self.partite_table.setSortingEnabled(True)
            self._aggiorna_stato_pulsante_modifica()

    def _aggiorna_stato_pulsante_modifica(self):
        has_selection = bool(self.partite_table.selectedItems())
        self.btn_modifica_partita.setEnabled(has_selection)
        self.btn_apri_dettaglio.setEnabled(has_selection)

    def _get_selected_partita_id(self) -> Optional[int]:
        selected_items = self.partite_table.selectedItems()
        if not selected_items:
            return None
        row = self.partite_table.currentRow()
        if row < 0:
            return None
        partita_id_item = self.partite_table.item(row, 0)
        if partita_id_item and partita_id_item.text().isdigit():
            return int(partita_id_item.text())
        return None

    def apri_dettaglio_partita_selezionata_da_pulsante(self):
        partita_id = self._get_selected_partita_id()
        if partita_id is not None:
            partita_details_data = self.db_manager.get_partita_details(partita_id)
            if partita_details_data:
                # Lazy import per evitare dipendenza circolare con dialogs_partita
                from dialogs_partita import PartitaDetailsDialog
                details_dialog = PartitaDetailsDialog(partita_details_data, self)
                details_dialog.exec()
            else:
                QMessageBox.warning(self, "Errore Dati", f"Impossibile recuperare i dettagli per la partita ID {partita_id}.")
        else:
            QMessageBox.information(self, "Nessuna Selezione", "Seleziona una partita dalla tabella per vederne i dettagli.")

    def apri_modifica_partita_selezionata(self, item: Optional[QTableWidgetItem] = None):
        partita_id = self._get_selected_partita_id()
        if partita_id is not None:
            # Lazy import per evitare dipendenza circolare con dialogs_partita
            from dialogs_partita import ModificaPartitaDialog
            dialog = ModificaPartitaDialog(self.db_manager, partita_id, self)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                self.load_partite_data()
                QMessageBox.information(self, "Modifica Partita", "Modifiche alla partita salvate con successo.")
        else:
            QMessageBox.warning(self, "Nessuna Selezione", "Per favore, seleziona una partita da modificare.")
    
    def apri_dettaglio_partita_selezionata(self, item: QTableWidgetItem):
        if not item:
            return
        partita_id = self._get_selected_partita_id()
        if partita_id is not None:
            partita_details_data = self.db_manager.get_partita_details(partita_id)
            if partita_details_data:
                from dialogs_partita import PartitaDetailsDialog
                details_dialog = PartitaDetailsDialog(partita_details_data, self)
                details_dialog.exec()
            else:
                QMessageBox.warning(self, "Errore Dati", f"Impossibile recuperare i dettagli per la partita ID {partita_id}.")



class ModificaLocalitaDialog(QDialog):
    def __init__(self, db_manager: CatastoDBManager, localita_id: int, comune_id_parent: int, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.localita_id = localita_id
        self.comune_id_parent = comune_id_parent
        self.localita_data_originale = None
        self.logger = logging.getLogger(f"CatastoGUI.{self.__class__.__name__}")

        self.setWindowTitle(f"Modifica Dati Località ID: {self.localita_id}")
        self.setMinimumWidth(450)

        self._init_ui()
        self._load_tipi_localita() # Carica subito i tipi disponibili
        self._load_localita_data() # Poi carica i dati della località e seleziona il tipo corretto

    def _init_ui(self):
        # ... (la UI è identica a prima, con la QComboBox per il tipo)
        layout = QVBoxLayout(self)
        form_layout = QFormLayout()
        self.id_label = QLabel(str(self.localita_id))
        form_layout.addRow("ID Località:", self.id_label)
        self.comune_display_label = QLabel("Caricamento...")
        form_layout.addRow("Comune di Appartenenza:", self.comune_display_label)
        self.nome_edit = QLineEdit()
        form_layout.addRow("Nome Località (*):", self.nome_edit)
        self.tipo_combo = QComboBox()
        form_layout.addRow("Tipo (*):", self.tipo_combo)
        self.civico_spinbox = QSpinBox()
        self.civico_spinbox.setMinimum(0); self.civico_spinbox.setMaximum(99999)
        self.civico_spinbox.setSpecialValueText("Nessuno")
        form_layout.addRow("Numero Civico (0 se assente):", self.civico_spinbox)
        layout.addLayout(form_layout)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel, self)
        buttons.accepted.connect(self._save_changes)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.setLayout(layout)

    def _load_tipi_localita(self):
        """Carica dinamicamente le tipologie di località nel ComboBox."""
        self.tipo_combo.clear()
        try:
            tipi = self.db_manager.get_tipi_localita()
            for tipo in tipi:
                self.tipo_combo.addItem(tipo['nome'], tipo['id'])
        except DBMError as e:
            QMessageBox.critical(self, "Errore", f"Impossibile caricare le tipologie di località:\n{e}")

    def _load_localita_data(self):
        # get_localita_details deve ora restituire anche tipo_id e comune_nome
        self.localita_data_originale = self.db_manager.get_localita_details(self.localita_id)
        if not self.localita_data_originale:
            QMessageBox.critical(self, "Errore", "Impossibile caricare i dati della località.")
            self.reject()
            return

        self.nome_edit.setText(self.localita_data_originale.get('nome', ''))
        self.comune_display_label.setText(f"{self.localita_data_originale.get('comune_nome', 'N/D')} (ID: {self.comune_id_parent})")

        # --- MODIFICA CHIAVE QUI: Seleziona l'item nel ComboBox basandosi sull'ID ---
        tipo_id_attuale = self.localita_data_originale.get('tipo_id')
        if tipo_id_attuale is not None:
            index = self.tipo_combo.findData(tipo_id_attuale)
            if index >= 0:
                self.tipo_combo.setCurrentIndex(index)
        # --- FINE MODIFICA ---

        civico_val = self.localita_data_originale.get('civico')
        self.civico_spinbox.setValue(civico_val if civico_val is not None else 0)

    def _save_changes(self):
        # Recupera l'ID dal ComboBox invece del testo
        tipo_id_selezionato = self.tipo_combo.currentData()

        if tipo_id_selezionato is None:
            QMessageBox.warning(self, "Dati Mancanti", "Selezionare una tipologia valida.")
            return

        dati_modificati = {
            "nome": self.nome_edit.text().strip(),
            "tipo_id": tipo_id_selezionato, # <-- MODIFICA QUI
            "civico": self.civico_spinbox.value() if self.civico_spinbox.value() > 0 else None
        }
        # ... (la logica di validazione e chiamata a update_localita rimane la stessa)
        if not dati_modificati["nome"]:
             QMessageBox.warning(self, "Dati Mancanti", "Il nome della località è obbligatorio.")
             return
        try:
            self.db_manager.update_localita(self.localita_id, dati_modificati)
            self.accept()
        except (DBMError, DBDataError, DBUniqueConstraintError) as e:
            QMessageBox.critical(self, "Errore Salvataggio", str(e))



class PeriodoStoricoDetailsDialog(QDialog):
    def __init__(self, db_manager: 'CatastoDBManager', periodo_id: int, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.periodo_id = periodo_id
        self.periodo_data_originale: Optional[Dict[str, Any]] = None

        self.setWindowTitle(
            f"Dettagli/Modifica Periodo Storico ID: {self.periodo_id}")
        self.setMinimumWidth(450)
        self.setModal(True)

        self._initUI()
        self._load_data()

    def _initUI(self):
        main_layout = QVBoxLayout(self)
        form_layout = QFormLayout()
        form_layout.setSpacing(10)

        # Campi Visualizzazione (non editabili)
        self.id_label = QLabel(str(self.periodo_id))
        self.data_creazione_label = QLabel()
        self.data_modifica_label = QLabel()

        form_layout.addRow("ID Periodo:", self.id_label)

        # Campi Editabili
        self.nome_edit = QLineEdit()
        form_layout.addRow("Nome Periodo (*):", self.nome_edit)

        self.anno_inizio_spinbox = QSpinBox()
        # Adatta il range se necessario
        self.anno_inizio_spinbox.setRange(0, 3000)
        form_layout.addRow("Anno Inizio (*):", self.anno_inizio_spinbox)

        self.anno_fine_spinbox = QSpinBox()
        self.anno_fine_spinbox.setRange(0, 3000)
        # Permetti "nessun anno fine" usando un valore speciale o gestendo 0 come "non impostato"
        self.anno_fine_spinbox.setSpecialValueText(
            " ")  # Vuoto se 0 (o il minimo)
        # 0 potrebbe significare "non specificato"
        self.anno_fine_spinbox.setMinimum(0)
        form_layout.addRow("Anno Fine (0 se aperto):", self.anno_fine_spinbox)

        self.descrizione_edit = QTextEdit()
        self.descrizione_edit.setMinimumHeight(100)
        form_layout.addRow("Descrizione:", self.descrizione_edit)

        form_layout.addRow("Data Creazione:", self.data_creazione_label)
        form_layout.addRow("Ultima Modifica:", self.data_modifica_label)

        main_layout.addLayout(form_layout)

        # Pulsanti
        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        self.button_box.accepted.connect(self._save_changes)
        self.button_box.rejected.connect(self.reject)
        main_layout.addWidget(self.button_box)

        self.setLayout(main_layout)

    def _load_data(self):
        self.periodo_data_originale = self.db_manager.get_periodo_storico_details(
            self.periodo_id)

        if not self.periodo_data_originale:
            QMessageBox.critical(self, "Errore Caricamento",
                                 f"Impossibile caricare i dettagli per il periodo ID: {self.periodo_id}.")
            # Chiudi il dialogo se i dati non possono essere caricati
            # Usiamo QTimer per permettere al messaggio di essere processato prima di chiudere
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(0, self.reject)
            return

        self.nome_edit.setText(self.periodo_data_originale.get('nome', ''))
        self.anno_inizio_spinbox.setValue(
            self.periodo_data_originale.get('anno_inizio', 0))

        anno_fine_val = self.periodo_data_originale.get('anno_fine')
        if anno_fine_val is not None:
            self.anno_fine_spinbox.setValue(anno_fine_val)
        else:  # Se anno_fine è NULL nel DB
            # Mostra testo speciale (" ")
            self.anno_fine_spinbox.setValue(self.anno_fine_spinbox.minimum())

        self.descrizione_edit.setText(
            self.periodo_data_originale.get('descrizione', ''))

        dc = self.periodo_data_originale.get('data_creazione')
        self.data_creazione_label.setText(
            dc.strftime('%Y-%m-%d %H:%M:%S') if dc else 'N/D')
        dm = self.periodo_data_originale.get('data_modifica')
        self.data_modifica_label.setText(
            dm.strftime('%Y-%m-%d %H:%M:%S') if dm else 'N/D')

    def _save_changes(self):
        dati_da_salvare = {
            "nome": self.nome_edit.text().strip(),
            "anno_inizio": self.anno_inizio_spinbox.value(),
            "descrizione": self.descrizione_edit.toPlainText().strip()
        }

        anno_fine_val_ui = self.anno_fine_spinbox.value()
        if self.anno_fine_spinbox.text() == self.anno_fine_spinbox.specialValueText() or anno_fine_val_ui == self.anno_fine_spinbox.minimum():
            # Salva NULL se vuoto o valore minimo
            dati_da_salvare["anno_fine"] = None
        else:
            dati_da_salvare["anno_fine"] = anno_fine_val_ui

        # Validazione base
        if not dati_da_salvare["nome"]:
            QMessageBox.warning(self, "Dati Mancanti",
                                "Il nome del periodo è obbligatorio.")
            self.nome_edit.setFocus()
            return
        if dati_da_salvare["anno_inizio"] <= 0:  # O altra logica per anno inizio
            QMessageBox.warning(self, "Dati Non Validi",
                                "L'anno di inizio deve essere valido.")
            self.anno_inizio_spinbox.setFocus()
            return
        if dati_da_salvare["anno_fine"] is not None and dati_da_salvare["anno_fine"] < dati_da_salvare["anno_inizio"]:
            QMessageBox.warning(
                self, "Date Non Valide", "L'anno di fine non può essere precedente all'anno di inizio.")
            self.anno_fine_spinbox.setFocus()
            return

        try:
            success = self.db_manager.update_periodo_storico(
                self.periodo_id, dati_da_salvare)
            if success:
                QMessageBox.information(
                    self, "Successo", "Periodo storico aggiornato con successo.")
                self.accept()  # Chiude il dialogo e segnala successo
            # else: # update_periodo_storico solleva eccezioni per fallimenti
            # QMessageBox.critical(self, "Errore", "Impossibile aggiornare il periodo storico.")
        except (DBUniqueConstraintError, DBDataError, DBMError) as e:
            logging.getLogger("CatastoGUI").error(
                f"Errore salvataggio periodo storico ID {self.periodo_id}: {str(e)}")
            QMessageBox.critical(self, "Errore Salvataggio", str(e))
        except Exception as e_gen:
            logging.getLogger("CatastoGUI").critical(
                f"Errore imprevisto salvataggio periodo storico ID {self.periodo_id}: {str(e_gen)}", exc_info=True)
            QMessageBox.critical(self, "Errore Imprevisto",
                                 f"Si è verificato un errore: {str(e_gen)}")
            

class ComuneSelectionDialog(QDialog):
    def __init__(self, db_manager: CatastoDBManager, parent=None, title="Seleziona Comune"):
        super(ComuneSelectionDialog, self).__init__(parent)
        self.db_manager = db_manager
        self.selected_comune_id: Optional[int] = None
        self.selected_comune_name: Optional[str] = None
        self.setWindowTitle(title)
        self.setMinimumWidth(400)
        self.setMinimumHeight(300)
        layout = QVBoxLayout(self)

        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("Filtra comuni:"))
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Digita per filtrare...")
        self.search_edit.textChanged.connect(self.filter_comuni)
        search_layout.addWidget(self.search_edit)

        self.search_button = QPushButton(
            QApplication.style().standardIcon(QStyle.StandardPixmap.SP_BrowserReload), "")
        self.search_button.setToolTip("Aggiorna lista comuni")
        self.search_button.clicked.connect(
            self.filter_comuni)  # Usa self.filter_comuni
        search_layout.addWidget(self.search_button)
        layout.addLayout(search_layout)

        self.comuni_list = QListWidget()
        self.comuni_list.setAlternatingRowColors(True)
        self.comuni_list.itemDoubleClicked.connect(
            self.handle_select)  # Connessione corretta
        layout.addWidget(self.comuni_list)

        buttons_layout = QHBoxLayout()
        self.select_button = QPushButton("Seleziona")
        self.select_button.setDefault(True)
        self.select_button.clicked.connect(
            self.handle_select)  # Connessione corretta

        self.cancel_button = QPushButton("Annulla")
        self.cancel_button.clicked.connect(self.reject)

        buttons_layout.addStretch()
        buttons_layout.addWidget(self.select_button)
        buttons_layout.addWidget(self.cancel_button)
        layout.addLayout(buttons_layout)

        self.load_comuni()

    def load_comuni(self, filter_text: Optional[str] = None):
        self.comuni_list.clear()
        try:
            comuni = self.db_manager.get_comuni(filter_text)
            if comuni:
                for comune in comuni:
                    item = QListWidgetItem(
                        f"{comune['nome']} (ID: {comune['id']}, {comune['provincia']})")
                    item.setData(Qt.ItemDataRole.UserRole, comune['id'])
                    # Per recuperare il nome facilmente
                    item.setData(Qt.ItemDataRole.UserRole + 1, comune['nome'])
                    self.comuni_list.addItem(item)
            else:
                self.comuni_list.addItem("Nessun comune trovato.")
        except Exception as e:
            logging.getLogger("CatastoGUI").error(
                f"Errore caricamento comuni nel dialogo: {e}")
            self.comuni_list.addItem("Errore caricamento comuni.")

    def filter_comuni(self):
        filter_text = self.search_edit.text().strip()
        self.load_comuni(filter_text if filter_text else None)

    def handle_select(self):
        current_item = self.comuni_list.currentItem()
        if current_item and current_item.data(Qt.ItemDataRole.UserRole) is not None:
            self.selected_comune_id = current_item.data(Qt.ItemDataRole.UserRole)
            self.selected_comune_name = current_item.data(
                Qt.ItemDataRole.UserRole + 1)  # Salva anche il nome
            self.accept()
        else:
            QMessageBox.warning(self, "Attenzione",
                                "Seleziona un comune valido dalla lista.")

class PartitaSearchDialog(QDialog):
    def __init__(self, db_manager, parent=None):
        super(PartitaSearchDialog, self).__init__(parent)
        self.db_manager = db_manager
        self.selected_partita_id = None

        self.setWindowTitle("Ricerca Partita")
        self.setMinimumSize(750, 500)
        layout = QVBoxLayout(self)
        form_group = QGroupBox("Criteri di Ricerca")
        form_layout = QGridLayout(form_group)

        # Riga 0: Comune
        form_layout.addWidget(QLabel("Comune:"), 0, 0)
        self.comune_button = QPushButton("Seleziona...")
        self.comune_button.clicked.connect(self.select_comune)
        self.comune_id = None
        self.comune_display = QLabel("Tutti i comuni")
        self.clear_comune_button = QPushButton("Cancella")
        self.clear_comune_button.clicked.connect(self.clear_comune)
        form_layout.addWidget(self.comune_button, 0, 1)
        form_layout.addWidget(self.comune_display, 0, 2, 1, 2)
        form_layout.addWidget(self.clear_comune_button, 0, 4)

        # Riga 1: Numero e Suffisso partita
        form_layout.addWidget(QLabel("Numero Partita:"), 1, 0)
        self.numero_edit = QSpinBox()
        self.numero_edit.setRange(0, 999999)
        self.numero_edit.setSpecialValueText("Qualsiasi")
        form_layout.addWidget(self.numero_edit, 1, 1)

        # --- CAMPO SUFFISSO AGGIUNTO ---
        form_layout.addWidget(QLabel("Suffisso:"), 1, 2)
        self.suffisso_edit = QLineEdit()
        self.suffisso_edit.setPlaceholderText("Qualsiasi")
        form_layout.addWidget(self.suffisso_edit, 1, 3, 1, 2)

        # Riga 2 e 3: Possessore e Natura
        form_layout.addWidget(QLabel("Nome Possessore:"), 2, 0)
        self.possessore_edit = QLineEdit()
        form_layout.addWidget(self.possessore_edit, 2, 1, 1, 4)
        form_layout.addWidget(QLabel("Natura Immobile:"), 3, 0)
        self.natura_edit = QLineEdit()
        form_layout.addWidget(self.natura_edit, 3, 1, 1, 4)
        
        layout.addWidget(form_group)

        search_button = QPushButton("Cerca")
        search_button.clicked.connect(self.do_search)
        layout.addWidget(search_button)

        results_group = QGroupBox("Risultati")
        results_layout = QVBoxLayout(results_group)
        self.results_table = QTableWidget()
        
        # --- COLONNA SUFFISSO AGGIUNTA ALLA TABELLA ---
        self.results_table.setColumnCount(6)
        self.results_table.setHorizontalHeaderLabels(["ID", "Comune", "Numero", "Suffisso", "Tipo", "Stato"])
        
        self.results_table.setAlternatingRowColors(True)
        self.results_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.results_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.results_table.itemDoubleClicked.connect(self.select_partita)
        self.results_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        results_layout.addWidget(self.results_table)
        results_group.setLayout(results_layout)
        layout.addWidget(results_group)

        buttons_layout = QHBoxLayout()
        self.select_button = QPushButton("Seleziona")
        self.select_button.clicked.connect(self.select_partita)
        self.cancel_button = QPushButton("Annulla")
        self.cancel_button.clicked.connect(self.reject)
        buttons_layout.addStretch()
        buttons_layout.addWidget(self.select_button)
        buttons_layout.addWidget(self.cancel_button)
        layout.addLayout(buttons_layout)
        self.setLayout(layout)
        
    def do_search(self):
        comune_id = self.comune_id
        numero_partita = self.numero_edit.value() if self.numero_edit.value() > 0 else None
        # --- LETTURA SUFFISSO DAL NUOVO CAMPO ---
        suffisso = self.suffisso_edit.text().strip() or None
        possessore = self.possessore_edit.text().strip() or None
        natura = self.natura_edit.text().strip() or None

        partite = self.db_manager.search_partite(
            comune_id=comune_id,
            numero_partita=numero_partita,
            suffisso_partita=suffisso, # Passa il suffisso alla ricerca
            possessore=possessore,
            immobile_natura=natura
        )

        self.results_table.setRowCount(0)
        for partita in partite:
            row_pos = self.results_table.rowCount()
            self.results_table.insertRow(row_pos)
            col = 0
            self.results_table.setItem(row_pos, col, QTableWidgetItem(str(partita.get('id', '')))); col += 1
            self.results_table.setItem(row_pos, col, QTableWidgetItem(partita.get('comune_nome', ''))); col += 1
            self.results_table.setItem(row_pos, col, QTableWidgetItem(str(partita.get('numero_partita', '')))); col += 1
            # --- POPOLAMENTO COLONNA SUFFISSO ---
            self.results_table.setItem(row_pos, col, QTableWidgetItem(partita.get('suffisso_partita', ''))); col += 1
            self.results_table.setItem(row_pos, col, QTableWidgetItem(partita.get('tipo', ''))); col += 1
            self.results_table.setItem(row_pos, col, QTableWidgetItem(partita.get('stato', ''))); col += 1
        self.results_table.resizeColumnsToContents()

    def select_comune(self):
        dialog = ComuneSelectionDialog(self.db_manager, self)
        if dialog.exec() == QDialog.DialogCode.Accepted and dialog.selected_comune_id:
            self.comune_id = dialog.selected_comune_id
            self.comune_display.setText(dialog.selected_comune_name)

    def clear_comune(self):
        self.comune_id = None
        self.comune_display.setText("Tutti i comuni")

    def select_partita(self):
        selected_rows = self.results_table.selectedIndexes()
        if not selected_rows:
            QMessageBox.warning(self, "Attenzione", "Seleziona una partita dalla tabella.")
            return
        row = selected_rows[0].row()
        partita_id_item = self.results_table.item(row, 0)
        if partita_id_item and partita_id_item.text().isdigit():
            self.selected_partita_id = int(partita_id_item.text())
            self.accept()
        else:
            QMessageBox.warning(self, "Errore", "ID partita non valido.")

class CreatePossessoreDialog(QDialog):
    """Dialogo semplificato per la creazione di un nuovo possessore."""
    def __init__(self, db_manager: 'CatastoDBManager', parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.nuovo_possessore_id = None
        self.nuovo_possessore_dati = None
        self.setWindowTitle("Crea Nuovo Possessore")
        self.setMinimumWidth(450)
        self.setModal(True)

        # UI
        layout = QFormLayout(self)
        self.cognome_nome_edit = QLineEdit()
        self.paternita_edit = QLineEdit()
        self.nome_completo_edit = QLineEdit()
        self.btn_genera_nome = QPushButton("Genera da campi precedenti")
        self.comune_combo = QComboBox()
        self.attivo_check = QCheckBox("Attivo"); self.attivo_check.setChecked(True)

        layout.addRow("Cognome e Nome (*):", self.cognome_nome_edit)
        layout.addRow("Paternità:", self.paternita_edit)
        layout.addRow(self.btn_genera_nome)
        layout.addRow("Nome Completo (*):", self.nome_completo_edit)
        layout.addRow("Comune di Riferimento (*):", self.comune_combo)
        layout.addRow(self.attivo_check)

        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        layout.addRow(self.button_box)

        # Connessioni e caricamento dati
        self.btn_genera_nome.clicked.connect(self._genera_nome)
        self.button_box.accepted.connect(self._salva_e_accetta)
        self.button_box.rejected.connect(self.reject)

        self._carica_comuni()

    def _carica_comuni(self):
        self.comune_combo.addItem("--- Seleziona ---", None)
        try:
            comuni = self.db_manager.get_elenco_comuni_semplice()
            for cid, nome in comuni:
                self.comune_combo.addItem(nome, cid)
        except DBMError as e:
            QMessageBox.critical(self, "Errore", f"Impossibile caricare i comuni: {e}")

    def _genera_nome(self):
        nome = self.cognome_nome_edit.text().strip()
        paternita = self.paternita_edit.text().strip()
        self.nome_completo_edit.setText(f"{nome} {paternita}".strip())

    def _salva_e_accetta(self):
        nome_completo = self.nome_completo_edit.text().strip()
        cognome_nome = self.cognome_nome_edit.text().strip()
        comune_id = self.comune_combo.currentData()

        if not nome_completo or not cognome_nome or comune_id is None:
            QMessageBox.warning(self, "Dati Mancanti", "Cognome/Nome, Nome Completo e Comune sono obbligatori.")
            return

        try:
            self.nuovo_possessore_id = self.db_manager.create_possessore(
                nome_completo=nome_completo,
                cognome_nome=cognome_nome,
                paternita=self.paternita_edit.text().strip() or None,
                comune_riferimento_id=comune_id,
                attivo=self.attivo_check.isChecked()
            )
            self.nuovo_possessore_dati = self.db_manager.get_possessore_full_details(self.nuovo_possessore_id)
            self.accept()
        except (DBMError, DBUniqueConstraintError) as e:
            QMessageBox.critical(self, "Errore Creazione", str(e))


class LocalitaSelectionDialog(QDialog):
    def __init__(self, db_manager: CatastoDBManager, comune_id: int, parent=None,
                 selection_mode: bool = False):
        super(LocalitaSelectionDialog, self).__init__(parent)
        self.db_manager = db_manager
        self.comune_id = comune_id
        self.selection_mode = selection_mode
        self.logger = logging.getLogger(f"CatastoGUI.{self.__class__.__name__}")

        self.selected_localita_id: Optional[int] = None
        self.selected_localita_name: Optional[str] = None

        if self.selection_mode:
            self.setWindowTitle(f"Seleziona Località per Comune ID: {self.comune_id}")
        else:
            self.setWindowTitle(f"Gestisci Località per Comune ID: {self.comune_id}")

        self.setMinimumSize(650, 450)

        layout = QVBoxLayout(self)

        self.tabs = QTabWidget(self)
        layout.addWidget(self.tabs)

        # --- Tab 1: Visualizza/Modifica Esistente ---
        select_tab = QWidget()
        select_layout = QVBoxLayout(select_tab)

        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("Filtra per nome:"))
        self.filter_edit = QLineEdit()
        self.filter_edit.setPlaceholderText("Digita per filtrare...")
        self.filter_edit.textChanged.connect(
            lambda: (self.load_localita(self.filter_edit.text().strip()),
                     self._aggiorna_stato_pulsanti_action_localita())
        )
        filter_layout.addWidget(self.filter_edit)
        select_layout.addLayout(filter_layout)

        self.localita_table = QTableWidget()
        self.localita_table.setColumnCount(4)
        self.localita_table.setHorizontalHeaderLabels(["ID", "Nome", "Tipo", "Civico"])
        self.localita_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.localita_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.localita_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.localita_table.itemSelectionChanged.connect(self._aggiorna_stato_pulsanti_action_localita) # Qui si collega il segnale
        self.localita_table.itemDoubleClicked.connect(self._handle_double_click)
        select_layout.addWidget(self.localita_table)

        select_action_layout = QHBoxLayout()
        self.btn_modifica_localita = QPushButton(QApplication.style().standardIcon(
            QStyle.StandardPixmap.SP_FileDialogDetailedView), "Modifica Selezionata")
        self.btn_modifica_localita.setToolTip("Modifica i dati della località selezionata")
        self.btn_modifica_localita.clicked.connect(self.apri_modifica_localita_selezionata)
        if self.selection_mode:
            self.btn_modifica_localita.setVisible(False)
        select_action_layout.addWidget(self.btn_modifica_localita)
        select_action_layout.addStretch()
        select_layout.addLayout(select_action_layout)
        self.tabs.addTab(select_tab, "Visualizza Località")

        if not self.selection_mode:
            create_tab = QWidget()
            create_form_layout = QFormLayout(create_tab)
            self.nome_edit_nuova = QLineEdit() 
            self.tipo_combo_nuova = QComboBox() 
            self.tipo_combo_nuova.addItems(["Regione", "Via", "Borgata", "Altro"])
            self.civico_spinbox_nuova = QSpinBox() 
            self.civico_spinbox_nuova.setMinimum(0)
            self.civico_spinbox_nuova.setMaximum(99999)
            self.civico_spinbox_nuova.setSpecialValueText("Nessuno") 
            create_form_layout.addRow(QLabel("Nome località (*):"), self.nome_edit_nuova)
            create_form_layout.addRow(QLabel("Tipo (*):"), self.tipo_combo_nuova)
            create_form_layout.addRow(QLabel("Numero Civico (0 se assente):"), self.civico_spinbox_nuova)
            self.btn_salva_nuova_localita = QPushButton(QApplication.style().standardIcon(QStyle.StandardPixmap.SP_DialogSaveButton) ,"Salva Nuova Località")
            self.btn_salva_nuova_localita.clicked.connect(self._salva_nuova_localita_da_tab)
            create_form_layout.addRow(self.btn_salva_nuova_localita)
            self.tabs.addTab(create_tab, "Crea Nuova Località")

        buttons_layout = QHBoxLayout()

        self.select_button = QPushButton(QApplication.style().standardIcon(
            QStyle.StandardPixmap.SP_DialogApplyButton), "Seleziona")
        self.select_button.setToolTip("Conferma la località selezionata")
        self.select_button.clicked.connect(self._handle_selection_or_creation)
        buttons_layout.addWidget(self.select_button)

        buttons_layout.addStretch()

        self.chiudi_button = QPushButton(QApplication.style().standardIcon(
            QStyle.StandardPixmap.SP_DialogCloseButton), "Chiudi")
        self.chiudi_button.clicked.connect(self.reject)
        buttons_layout.addWidget(self.chiudi_button)

        layout.addLayout(buttons_layout)
        self.setLayout(layout)

        self.tabs.currentChanged.connect(self._tab_changed) 

        self.load_localita()
        self._tab_changed(self.tabs.currentIndex()) # Imposta lo stato iniziale del pulsante
     # --- INIZIO METODO MANCANTE/DA RIPRISTINARE ---
    def load_localita(self, filter_text: Optional[str] = None):
        """
        Carica le località per il comune_id corrente, applicando un filtro testuale opzionale.
        """
        self.localita_table.setRowCount(0)
        self.localita_table.setSortingEnabled(False)

        # Se il filtro non è fornito, usa il testo attuale dal QLineEdit del filtro
        # Questo assicura che il filtro venga mantenuto anche se load_localita è chiamato senza parametri
        actual_filter_text = filter_text if filter_text is not None else self.filter_edit.text().strip()
        if not actual_filter_text: # Se il filtro è vuoto, imposta a None per la query DB
            actual_filter_text = None

        if self.comune_id:
            try:
                localita_results = self.db_manager.get_localita_by_comune(
                    self.comune_id, actual_filter_text)
                
                if localita_results:
                    self.localita_table.setRowCount(len(localita_results))
                    for i, loc in enumerate(localita_results):
                        self.localita_table.setItem(
                            i, 0, QTableWidgetItem(str(loc.get('id', ''))))
                        self.localita_table.setItem(
                            i, 1, QTableWidgetItem(loc.get('nome', '')))
                        self.localita_table.setItem(
                            i, 2, QTableWidgetItem(loc.get('tipo', '')))
                        civico_text = str(loc.get('civico', '')) if loc.get(
                            'civico') is not None else "-"
                        self.localita_table.setItem(
                            i, 3, QTableWidgetItem(civico_text))
                    self.localita_table.resizeColumnsToContents()
                else:
                    self.logger.info(f"Nessuna località trovata per comune ID {self.comune_id} con filtro '{actual_filter_text}'.")
                    # Mostra un messaggio nella tabella se nessun risultato
                    self.localita_table.setRowCount(1)
                    item = QTableWidgetItem("Nessuna località trovata con i criteri specificati.")
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    self.localita_table.setItem(0, 0, item)
                    self.localita_table.setSpan(0, 0, 1, self.localita_table.columnCount())

            except Exception as e:
                self.logger.error(f"Errore caricamento località per comune {self.comune_id} (filtro '{actual_filter_text}'): {e}", exc_info=True)
                QMessageBox.critical(
                    self, "Errore Caricamento", f"Impossibile caricare le località:\n{e}")
                self.localita_table.setRowCount(1)
                item = QTableWidgetItem(f"Errore caricamento: {e}")
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.localita_table.setItem(0, 0, item)
                self.localita_table.setSpan(0, 0, 1, self.localita_table.columnCount())
        else:
            self.logger.warning("Comune ID non disponibile per caricare località.")
            self.localita_table.setRowCount(1)
            item = QTableWidgetItem("ID Comune non disponibile per caricare località.")
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.localita_table.setItem(0, 0, item)
            self.localita_table.setSpan(0, 0, 1, self.localita_table.columnCount())


        self.localita_table.setSortingEnabled(True)
        self._aggiorna_stato_pulsanti_action_localita() # Aggiorna stato pulsanti
    # --- FINE METODO MANCANTE/DA RIPRISTINARE ---

    # --- INIZIO METODO MANCANTE/DA RIPRISTINARE ---
    def _handle_double_click(self, item: QTableWidgetItem):
        """Gestisce il doppio click sulla tabella."""
        if self.selection_mode and self.tabs.currentIndex() == 0:
            # Se in modalità selezione e nel tab di visualizzazione, il doppio click seleziona
            self._handle_selection_or_creation() # Chiama il metodo unificato per la selezione
        elif not self.selection_mode and self.tabs.currentIndex() == 0:
            # Se non in modalità selezione (ovvero gestione) e nel tab di visualizzazione,
            # il doppio click apre la modifica (se l'utente ha i permessi e una riga è selezionata).
            self.apri_modifica_localita_selezionata()
    # --- FINE METODO MANCANTE/DA RIPRISTINARE ---
    def _aggiorna_stato_pulsanti_action_localita(self):
        """Abilita/disabilita i pulsanti di azione (Modifica, Seleziona) in base alla selezione nella tabella."""
        is_select_tab_active = (self.tabs.currentIndex() == 0)
        has_selection_in_table = bool(self.localita_table.selectedItems())

        # Pulsante Modifica (visibile e attivo solo se non in selection_mode e nel tab corretto)
        self.btn_modifica_localita.setEnabled(
            is_select_tab_active and has_selection_in_table and not self.selection_mode
        )

        # Pulsante Seleziona (visibile e attivo solo se nel tab corretto e c'è selezione)
        # La visibilità del pulsante "Seleziona" è gestita in _tab_changed e _init_ui
        self.select_button.setEnabled(is_select_tab_active and has_selection_in_table)
    # --- FINE METODO MANCANTE/DA RIPRISTINARE ---


    def _tab_changed(self, index):
        """Gestisce il cambio di tab e aggiorna il testo del pulsante OK."""
        if self.selection_mode: # Se è in modalità solo selezione, il pulsante è sempre "Seleziona"
            self.select_button.setText("Seleziona Località")
            self.select_button.setToolTip("Conferma la località selezionata dalla tabella.")
            self.select_button.setVisible(True) # In modalità selezione, il pulsante è sempre visibile
        else: # Modalità gestione/creazione
            if index == 0:  # Tab "Visualizza Località"
                self.select_button.setText("Seleziona Località")
                self.select_button.setToolTip("Conferma la località selezionata dalla tabella.")
                self.select_button.setVisible(True)
            elif index == 1: # Tab "Crea Nuova Località"
                self.select_button.setText("Crea e Seleziona")
                self.select_button.setToolTip("Crea la nuova località e la seleziona automaticamente.")
                # Assicurati che questo pulsante sia visibile solo quando il tab è attivo e non in modalità solo selezione
                self.select_button.setVisible(True) 
            
        self._aggiorna_stato_pulsanti_action_localita() # Aggiorna abilitazione

    # --- MODIFICA CRUCIALE: Unifica la gestione di selezione ed creazione ---
    # --- INIZIO METODO MANCANTE/DA RIPRISTINARE ---
    def apri_modifica_localita_selezionata(self):
        """
        Apre un dialogo per modificare la località selezionata dalla tabella.
        """
        localita_id_sel = self._get_selected_localita_id_from_table()
        if localita_id_sel is not None:
            self.logger.info(f"LocalitaSelectionDialog: Richiesta modifica per località ID {localita_id_sel}.")
            # Istanzia e apre ModificaLocalitaDialog, passando il comune_id_parent
            dialog = ModificaLocalitaDialog(
                self.db_manager, localita_id_sel, self.comune_id, self) # comune_id qui è il comune_id_parent
            if dialog.exec() == QDialog.DialogCode.Accepted:
                self.logger.info(f"Modifiche a località ID {localita_id_sel} salvate. Ricarico l'elenco.")
                self.load_localita(self.filter_edit.text().strip() or None) # Ricarica con il filtro corrente
                QMessageBox.information(self, "Modifica Località", "Modifiche alla località salvate con successo.")
            else:
                self.logger.info(f"Modifica località ID {localita_id_sel} annullata dall'utente.")
        else:
            QMessageBox.warning(
                self, "Nessuna Selezione", "Seleziona una località dalla tabella per modificarla.")

    def _get_selected_localita_id_from_table(self) -> Optional[int]:
        """Helper per ottenere l'ID della località selezionata nella tabella."""
        selected_items = self.localita_table.selectedItems()
        if not selected_items:
            return None
        current_row = self.localita_table.currentRow()
        if current_row < 0:
            return None
        id_item = self.localita_table.item(current_row, 0)
        if id_item and id_item.text().isdigit():
            return int(id_item.text())
        return None
    # --- FINE METODO MANCANTE/DA RIPRISTINARE ---
    def _handle_selection_or_creation(self):
        """
        Gestisce la selezione di una località esistente o la creazione/selezione di una nuova.
        Questo metodo imposta self.selected_localita_id e self.selected_localita_name
        e poi chiama self.accept().
        """
        current_tab_index = self.tabs.currentIndex()

        if current_tab_index == 0:  # Tab "Visualizza Località" (selezione di un esistente)
            selected_items = self.localita_table.selectedItems()
            if not selected_items:
                QMessageBox.warning(self, "Nessuna Selezione", "Seleziona una località dalla tabella.")
                return

            current_row = self.localita_table.currentRow()
            if current_row < 0: # Controllo aggiuntivo
                QMessageBox.warning(self, "Errore Selezione", "Nessuna riga selezionata validamente.")
                return

            try:
                self.selected_localita_id = int(self.localita_table.item(current_row, 0).text())
                nome = self.localita_table.item(current_row, 1).text()
                tipo = self.localita_table.item(current_row, 2).text()
                civico_item_text = self.localita_table.item(current_row, 3).text()

                self.selected_localita_name = nome
                if civico_item_text and civico_item_text.strip() not in ("", "-", "0"):
                    self.selected_localita_name += f", civ. {civico_item_text}"
                if tipo:
                    self.selected_localita_name += f" ({tipo})"
                
                self.logger.info(f"LocalitaSelectionDialog: Località esistente selezionata - ID: {self.selected_localita_id}, Nome: '{self.selected_localita_name}'")
                self.accept() # Accetta il dialogo con la selezione fatta

            except ValueError:
                QMessageBox.critical(self, "Errore Dati", "ID località non valido nella tabella.")
            except Exception as e:
                self.logger.error(f"Errore in _handle_selection_or_creation (selezione esistente): {e}", exc_info=True)
                QMessageBox.critical(self, "Errore Imprevisto", f"Errore durante la conferma della selezione: {e}")

        elif current_tab_index == 1 and not self.selection_mode: # Tab "Crea Nuova Località" (solo se in modalità gestione)
            nome = self.nome_edit_nuova.text().strip()
            tipo = self.tipo_combo_nuova.currentText()
            civico_val = self.civico_spinbox_nuova.value()
            
            # Determina il valore finale del civico (NULL se 0 o testo speciale)
            civico = None
            if self.civico_spinbox_nuova.text().strip() != self.civico_spinbox_nuova.specialValueText() and civico_val != 0:
                civico = civico_val

            if not nome:
                QMessageBox.warning(self, "Dati Mancanti", "Il nome della località è obbligatorio.")
                self.nome_edit_nuova.setFocus()
                return
            if not tipo or tipo.strip() == "Seleziona Tipo...": # Se avevi aggiunto un placeholder
                QMessageBox.warning(self, "Dati Mancanti", "Il tipo di località è obbligatorio.")
                self.tipo_combo_nuova.setFocus()
                return
            if self.comune_id is None:
                QMessageBox.critical(self, "Errore Interno", "ID Comune non specificato. Impossibile creare località.")
                return

            try:
                localita_id_creata = self.db_manager.insert_localita(
                    self.comune_id, nome, tipo, civico
                )

                if localita_id_creata is not None:
                    # Imposta gli attributi selected_localita_id e selected_localita_name
                    # che verranno letti dal chiamante (ImmobileDialog).
                    self.selected_localita_id = localita_id_creata
                    self.selected_localita_name = nome
                    if civico is not None:
                        self.selected_localita_name += f", civ. {civico}"
                    self.selected_localita_name += f" ({tipo})"

                    QMessageBox.information(self, "Località Creata", f"Località '{self.selected_localita_name}' registrata con ID: {self.selected_localita_id}.")
                    self._pulisci_campi_creazione_localita() # Pulisce i campi del tab "Crea Nuova"
                    self.load_localita() # Ricarica l'elenco delle località nel tab "Visualizza"
                    self.tabs.setCurrentIndex(0) # Torna al tab di visualizzazione/selezione

                    self.accept() # Accetta il dialogo con la nuova località creata e selezionata

                else: # Fallimento nella creazione senza eccezione esplicita dal DBManager
                    self.logger.error("Creazione località fallita: ID non restituito da DBManager.")
                    QMessageBox.critical(self, "Errore Creazione", "Impossibile creare la località (ID non restituito).")

            except (DBUniqueConstraintError, DBDataError, DBMError) as dbe:
                self.logger.error(f"Errore DB creazione località: {dbe}", exc_info=True)
                QMessageBox.critical(self, "Errore Database", f"Impossibile creare località:\n{dbe.message if hasattr(dbe, 'message') else str(dbe)}")
            except Exception as e:
                self.logger.critical(f"Errore imprevisto creazione località: {e}", exc_info=True)
                QMessageBox.critical(self, "Errore Imprevisto", f"Si è verificato un errore:\n{e}")
        
        else: # Se si tenta di creare in selection_mode=True, blocca
             if current_tab_index == 1 and self.selection_mode:
                QMessageBox.warning(self, "Azione Non Disponibile", "La creazione di nuove località non è consentita in questa modalità di selezione.")
             else:
                QMessageBox.warning(self, "Azione Non Valida", "Azione non riconosciuta per il tab corrente.")

    # Aggiungi questo metodo per pulire i campi del tab "Crea Nuova Località"
    def _pulisci_campi_creazione_localita(self):
        self.nome_edit_nuova.clear()
        self.tipo_combo_nuova.setCurrentIndex(0)
        self.civico_spinbox_nuova.setValue(self.civico_spinbox_nuova.minimum()) # Resetta al "Nessuno"
    # --- INIZIO METODO MANCANTE/DA RIPRISTINARE ---
    def _salva_nuova_localita_da_tab(self):
        """
        Salva una nuova località dal tab "Crea Nuova Località".
        """
        nome = self.nome_edit_nuova.text().strip()
        tipo = self.tipo_combo_nuova.currentText()
        civico_val = self.civico_spinbox_nuova.value()

        civico = None
        if self.civico_spinbox_nuova.text().strip() != self.civico_spinbox_nuova.specialValueText() and civico_val != 0:
            civico = civico_val

        if not nome:
            QMessageBox.warning(self, "Dati Mancanti", "Il nome della località è obbligatorio.")
            self.nome_edit_nuova.setFocus()
            return
        if not tipo or tipo.strip() == "Seleziona Tipo...": # Se avevi aggiunto un placeholder
            QMessageBox.warning(self, "Dati Mancanti", "Il tipo di località è obbligatorio.")
            self.tipo_combo_nuova.setFocus()
            return
        if self.comune_id is None:
            QMessageBox.critical(self, "Errore Interno", "ID Comune non specificato. Impossibile creare località.")
            return

        try:
            localita_id_creata = self.db_manager.insert_localita(
                self.comune_id, nome, tipo, civico
            )

            if localita_id_creata is not None:
                QMessageBox.information(self, "Località Creata", f"Località '{nome}' registrata con ID: {localita_id_creata}")
                self.logger.info(f"Nuova località creata tramite tab 'Crea Nuova': ID {localita_id_creata}, Nome: '{nome}'")
                
                self._pulisci_campi_creazione_localita() # Pulisce i campi del tab "Crea Nuova"
                self.load_localita() # Ricarica l'elenco delle località nel tab "Visualizza"
                self.tabs.setCurrentIndex(0) # Torna al tab di visualizzazione/selezione
            else:
                self.logger.error("Creazione località fallita: ID non restituito da DBManager.")
                QMessageBox.critical(self, "Errore Creazione", "Impossibile creare la località (ID non restituito).")

        except (DBUniqueConstraintError, DBDataError, DBMError) as dbe:
            self.logger.error(f"Errore DB creazione località: {dbe}", exc_info=True)
            QMessageBox.critical(self, "Errore Database", f"Impossibile creare località:\n{dbe.message if hasattr(dbe, 'message') else str(dbe)}")
        except Exception as e:
            self.logger.critical(f"Errore imprevisto creazione località: {e}", exc_info=True)
            QMessageBox.critical(self, "Errore Imprevisto", f"Si è verificato un errore:\n{e}")

    def _pulisci_campi_creazione_localita(self):
        self.nome_edit_nuova.clear()
        self.tipo_combo_nuova.setCurrentIndex(0)
        self.civico_spinbox_nuova.setValue(self.civico_spinbox_nuova.minimum()) # Resetta al "Nessuno"
    # --- FINE METODO MANCANTE/DA RIPRISTINARE ---
        


class DettagliLegamePossessoreDialog(QDialog):
    def __init__(self, nome_possessore_selezionato: str, partita_tipo: str,
                 titolo_attuale: Optional[str] = None,  # Nuovo
                 quota_attuale: Optional[str] = None,   # Nuovo
                 parent=None):
        super().__init__(parent)
        self.setWindowTitle(
            f"Dettagli Legame per {nome_possessore_selezionato}")
        self.setMinimumWidth(400)

        self.titolo: Optional[str] = None
        self.quota: Optional[str] = None
        # self.tipo_partita_rel: str = partita_tipo

        layout = QFormLayout(self)

        self.titolo_edit = QLineEdit()
        self.titolo_edit.setPlaceholderText(
            "Es. proprietà esclusiva, usufrutto")
        self.titolo_edit.setText(
            titolo_attuale if titolo_attuale is not None else "proprietà esclusiva")  # Pre-compila
        layout.addRow("Titolo di Possesso (*):", self.titolo_edit)

        self.quota_edit = QLineEdit()
        self.quota_edit.setPlaceholderText(
            "Es. 1/1, 1/2 (lasciare vuoto se non applicabile)")
        self.quota_edit.setText(
            quota_attuale if quota_attuale is not None else "")  # Pre-compila
        layout.addRow("Quota (opzionale):", self.quota_edit)

        # ... (pulsanti OK/Annulla e metodo _accept_details come prima) ...
        buttons_layout = QHBoxLayout()
        self.ok_button = QPushButton(
            QApplication.style().standardIcon(QStyle.StandardPixmap.SP_DialogOkButton), "OK")
        self.ok_button.clicked.connect(self._accept_details)
        self.cancel_button = QPushButton(QApplication.style().standardIcon(
            QStyle.StandardPixmap.SP_DialogCancelButton), "Annulla")
        self.cancel_button.clicked.connect(self.reject)
        buttons_layout.addStretch()
        buttons_layout.addWidget(self.ok_button)
        buttons_layout.addWidget(self.cancel_button)
        layout.addRow(buttons_layout)
        self.setLayout(layout)
        self.titolo_edit.setFocus()

    def _accept_details(self):
        # ... (come prima) ...
        titolo_val = self.titolo_edit.text().strip()
        if not titolo_val:
            QMessageBox.warning(self, "Dato Mancante",
                                "Il titolo di possesso è obbligatorio.")
            self.titolo_edit.setFocus()
            return
        self.titolo = titolo_val
        self.quota = self.quota_edit.text().strip() or None
        self.accept()

    # Metodo statico per l'inserimento (come prima)

    @staticmethod
    def get_details_for_new_legame(nome_possessore: str, tipo_partita_attuale: str, parent=None) -> Optional[Dict[str, Any]]:
        # Chiamiamo il costruttore senza titolo_attuale e quota_attuale,
        # così userà i default (None) e quindi il testo placeholder o il default "proprietà esclusiva"
        dialog = DettagliLegamePossessoreDialog(
            nome_possessore_selezionato=nome_possessore,
            partita_tipo=tipo_partita_attuale,
            # titolo_attuale e quota_attuale non vengono passati,
            # quindi __init__ userà i loro valori di default (None)
            parent=parent
        )
        if dialog.exec() == QDialog.DialogCode.Accepted:
            return {
                "titolo": dialog.titolo,
                "quota": dialog.quota,
                # "tipo_partita_rel": dialog.tipo_partita_rel # Se lo gestisci
            }
        return None

    # NUOVO Metodo statico per la modifica
    @staticmethod
    def get_details_for_edit_legame(nome_possessore: str, tipo_partita_attuale: str,
                                    titolo_init: str, quota_init: Optional[str],
                                    parent=None) -> Optional[Dict[str, Any]]:
        dialog = DettagliLegamePossessoreDialog(nome_possessore, tipo_partita_attuale,
                                                titolo_attuale=titolo_init,
                                                quota_attuale=quota_init,
                                                parent=parent)
        # Titolo specifico per modifica
        dialog.setWindowTitle(f"Modifica Legame per {nome_possessore}")
        if dialog.exec() == QDialog.DialogCode.Accepted:
            return {
                "titolo": dialog.titolo,
                "quota": dialog.quota,
            }
        return None
# In dialogs.py, aggiungi questa nuova classe


class PeriodoStoricoEditDialog(QDialog):
    def __init__(self, db_manager, periodo_data: Optional[Dict] = None, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.periodo_data = periodo_data
        self.periodo_id = self.periodo_data.get('id') if self.periodo_data else None

        if self.periodo_id:
            self.setWindowTitle(f"Modifica Periodo Storico ID: {self.periodo_id}")
        else:
            self.setWindowTitle("Crea Nuovo Periodo Storico")

        self.setMinimumWidth(400)
        self._initUI()

    def _initUI(self):
        layout = QFormLayout(self)

        # --- INIZIO CORREZIONE: Gestione del caso in cui periodo_data è None ---
        nome_default = self.periodo_data.get('nome', '') if self.periodo_data else ''
        anno_inizio_default = self.periodo_data.get('anno_inizio', 1900) if self.periodo_data else 1900
        anno_fine_default = self.periodo_data.get('anno_fine') if self.periodo_data and self.periodo_data.get('anno_fine') is not None else 0
        descrizione_default = self.periodo_data.get('descrizione', '') if self.periodo_data else ''
        # --- FINE CORREZIONE ---

        self.nome_edit = QLineEdit(nome_default)
        self.anno_inizio_spin = QSpinBox()
        self.anno_inizio_spin.setRange(1000, 3000)
        self.anno_inizio_spin.setValue(anno_inizio_default)
        self.anno_fine_spin = QSpinBox()
        self.anno_fine_spin.setRange(0, 3000)
        self.anno_fine_spin.setSpecialValueText("Aperto")
        self.anno_fine_spin.setValue(anno_fine_default)
        self.descrizione_edit = QTextEdit(descrizione_default)
        self.descrizione_edit.setMinimumHeight(80)

        layout.addRow("Nome (*):", self.nome_edit)
        layout.addRow("Anno Inizio (*):", self.anno_inizio_spin)
        layout.addRow("Anno Fine (0 se Aperto):", self.anno_fine_spin)
        layout.addRow("Descrizione:", self.descrizione_edit)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.save_and_accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def save_and_accept(self):
        nome = self.nome_edit.text().strip()
        anno_inizio = self.anno_inizio_spin.value()
        anno_fine = self.anno_fine_spin.value() if self.anno_fine_spin.value() > 0 else None
        descrizione = self.descrizione_edit.toPlainText().strip()

        if not nome:
            QMessageBox.warning(self, "Dati Mancanti", "Il nome del periodo è obbligatorio.")
            return

        try:
            # --- CORREZIONE LOGICA: Chiama il metodo giusto per modifica o creazione ---
            if self.periodo_id:
                # Modalità Modifica
                dati_modificati = {
                    "nome": nome, "anno_inizio": anno_inizio, 
                    "anno_fine": anno_fine, "descrizione": descrizione
                }
                self.db_manager.update_periodo_storico(self.periodo_id, dati_modificati)
            else:
                # Modalità Creazione
                self.db_manager.aggiungi_periodo_storico(nome, anno_inizio, anno_fine, descrizione)

            self.accept() # Chiude il dialogo solo se il salvataggio ha successo
        except (DBMError, DBDataError, DBUniqueConstraintError) as e:
            QMessageBox.critical(self, "Errore di Salvataggio", str(e))

