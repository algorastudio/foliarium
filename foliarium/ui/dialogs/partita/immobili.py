"""Dialog relativi agli immobili di una partita."""

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


class ModificaImmobileDialog(QDialog):
    """
    Dialogo per la modifica dei dettagli di un singolo immobile.
    """
    def __init__(self, db_manager, immobile_id: int, comune_id_partita: int, parent=None):
        super().__init__(parent)
        
        # --- Parametri e stato interno ---
        self.db_manager = db_manager
        self.immobile_id = immobile_id
        self.comune_id_partita = comune_id_partita
        self.dati_originali = None # Conterrà i dati caricati dal DB

        # --- Setup UI ---
        self.setWindowTitle(f"Modifica Immobile ID: {self.immobile_id}")
        self.setMinimumWidth(500)
        
        self._setup_ui()
        self._load_initial_data()

    def _setup_ui(self):
        """Crea e assembla i widget dell'interfaccia."""
        main_layout = QVBoxLayout(self)
        form_layout = QFormLayout()

        # --- Creazione dei campi del modulo ---
        self.natura_combo = QComboBox()
        self.classificazione_edit = QLineEdit()
        self.indirizzo_edit = QLineEdit()
        self.localita_combo = QComboBox()
        self.civico_edit = QLineEdit()
        self.civico_edit.setMaxLength(20)
        self.civico_edit.setPlaceholderText("Es. 17, 17/A, s.n.c.")
        self.foglio_edit = QLineEdit()
        self.mappale_edit = QLineEdit()
        self.subalterno_edit = QLineEdit()
        self.vani_spinbox = QDoubleSpinBox()
        self.vani_spinbox.setDecimals(2)
        self.vani_spinbox.setRange(0, 9999.99)
        self.note_edit = QTextEdit()
        self.note_edit.setMaximumHeight(80)

        # Popola i ComboBox
        self._populate_combos()

        # Aggiungi i widget al form layout
        form_layout.addRow("Natura:", self.natura_combo)
        form_layout.addRow("Classificazione:", self.classificazione_edit)
        form_layout.addRow("Indirizzo:", self.indirizzo_edit)
        form_layout.addRow("Località:", self.localita_combo)
        form_layout.addRow("Civico:", self.civico_edit)
        form_layout.addRow("Foglio:", self.foglio_edit)
        form_layout.addRow("Mappale:", self.mappale_edit)
        form_layout.addRow("Subalterno:", self.subalterno_edit)
        form_layout.addRow("Vani/Superficie:", self.vani_spinbox)
        form_layout.addRow("Note:", self.note_edit)

        main_layout.addLayout(form_layout)

        # --- Pulsanti Salva e Annulla ---
        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        
        main_layout.addWidget(self.button_box)

    def _populate_combos(self):
        """Popola i QComboBox con dati dal database o valori fissi."""
        # Esempio con valori fissi per 'Natura'
        # Potresti caricarli anche da una tabella del DB
        self.natura_combo.addItems([
            "Fabbricato", "Terreno", "Area Urbana", "Lastrico Solare", "Altro"
        ])

        # Carica le località per il comune specifico
        # (get_localita_by_comune ritorna List[Dict] con chiavi id, nome, tipologia_stradale)
        try:
            localita_list = self.db_manager.get_localita_by_comune(self.comune_id_partita)
            for loc in localita_list:
                self.localita_combo.addItem(loc["nome"], userData=loc["id"])
        except Exception as e:
            self.logger.error(f"Errore nel caricamento delle località: {e}")
            self.localita_combo.addItem("Errore caricamento", -1)

    def _load_initial_data(self):
        """Carica i dati dell'immobile dal DB e popola i campi."""
        try:
            self.dati_originali = self.db_manager.get_immobile_details(self.immobile_id)
            if not self.dati_originali:
                QMessageBox.critical(self, "Errore", "Impossibile trovare i dati per l'immobile specificato.")
                # Disabilita i campi e il pulsante salva
                self.button_box.button(QDialogButtonBox.StandardButton.Save).setEnabled(False)
                for i in range(self.layout().count()):
                    widget = self.layout().itemAt(i).widget()
                    if widget: widget.setEnabled(False)
                return

            # Popola i campi
            self.natura_combo.setCurrentText(self.dati_originali.get('natura', ''))
            self.classificazione_edit.setText(self.dati_originali.get('classificazione', ''))
            self.indirizzo_edit.setText(self.dati_originali.get('indirizzo', ''))
            self.civico_edit.setText(self.dati_originali.get('numero_civico') or '')
            self.foglio_edit.setText(str(self.dati_originali.get('foglio', '')))
            self.mappale_edit.setText(str(self.dati_originali.get('mappale', '')))
            self.subalterno_edit.setText(str(self.dati_originali.get('subalterno', '')))
            self.vani_spinbox.setValue(float(self.dati_originali.get('vani_o_superficie', 0.0)))
            self.note_edit.setPlainText(self.dati_originali.get('note', ''))
            
            # Seleziona la località corretta nel ComboBox
            id_localita_originale = self.dati_originali.get('id_localita')
            if id_localita_originale:
                index = self.localita_combo.findData(id_localita_originale)
                if index != -1:
                    self.localita_combo.setCurrentIndex(index)

        except Exception as e:
            QMessageBox.critical(self, "Errore di Caricamento", f"Impossibile caricare i dati dell'immobile:\n{e}")
            self.reject() # Chiude il dialogo in caso di errore critico

    def _save_changes(self):
        """Raccoglie i dati, li valida e li salva nel database."""
        # 1. Raccogli i dati aggiornati dai widget
        dati_aggiornati = {
            'natura': self.natura_combo.currentText(),
            'classificazione': self.classificazione_edit.text().strip(),
            'indirizzo': self.indirizzo_edit.text().strip(),
            'id_localita': self.localita_combo.currentData(),
            'numero_civico': self.civico_edit.text().strip() or None,
            'foglio': self.foglio_edit.text().strip(),
            'mappale': self.mappale_edit.text().strip(),
            'subalterno': self.subalterno_edit.text().strip(),
            'vani_o_superficie': self.vani_spinbox.value(),
            'note': self.note_edit.toPlainText().strip()
        }

        # 2. Validazione (esempio base)
        if not all([dati_aggiornati['natura'], dati_aggiornati['foglio'], dati_aggiornati['mappale']]):
            QMessageBox.warning(self, "Dati Mancanti", "I campi 'Natura', 'Foglio' e 'Mappale' sono obbligatori.")
            return

        # 3. Chiamata al DB Manager per l'aggiornamento
        try:
            successo = self.db_manager.update_immobile(self.immobile_id, dati_aggiornati)
            if successo:
                QMessageBox.information(self, "Successo", "Immobile aggiornato con successo.")
                return True # L'operazione è andata a buon fine
            else:
                QMessageBox.critical(self, "Errore Database", "L'aggiornamento nel database è fallito per un motivo sconosciuto.")
                return False
        except Exception as e:
            QMessageBox.critical(self, "Errore Critico", f"Si è verificato un errore durante il salvataggio:\n{e}")
            return False

    # Override del metodo accept per includere la logica di salvataggio
    def accept(self):
        """Eseguito quando si preme 'Salva'."""
        if self._save_changes():
            super().accept() # Chiude il dialogo con stato 'Accepted' solo se il salvataggio ha successo

# In dialogs.py, SOSTITUISCI l'intera classe PossessoreSelectionDialog




class ImmobileDialog(QDialog):
    def __init__(self, db_manager, comune_id, parent=None):
        super(ImmobileDialog, self).__init__(parent)
        self.db_manager = db_manager
        self.comune_id = comune_id
        self.immobile_data = None
        self.logger = logging.getLogger(f"CatastoGUI.{self.__class__.__name__}") # Inizializza il logger

        self.setWindowTitle("Inserisci Immobile")
        self.setMinimumSize(500, 400)

        layout = QVBoxLayout()

        form_layout = QGridLayout()

        # Natura
        natura_label = QLabel("Natura:")
        self.natura_edit = QLineEdit()
        self.natura_edit.setPlaceholderText("Es. Casa, Terreno, Garage, ecc.")

        form_layout.addWidget(natura_label, 0, 0)
        form_layout.addWidget(self.natura_edit, 0, 1)

        # Località
        localita_label = QLabel("Località:")
        self.localita_button = QPushButton("Seleziona/Gestisci Località...") # Modificato testo del pulsante
        self.localita_button.clicked.connect(self.select_localita)
        self.localita_id = None
        self.localita_display = QLabel("Nessuna località selezionata")

        form_layout.addWidget(localita_label, 1, 0)
        form_layout.addWidget(self.localita_button, 1, 1)
        form_layout.addWidget(self.localita_display, 1, 2)

        # Civico (alfanumerico: "17", "17/A", "s.n.c.")
        civico_label = QLabel("Civico:")
        self.civico_edit = QLineEdit()
        self.civico_edit.setMaxLength(20)
        self.civico_edit.setPlaceholderText("Es. 17, 17/A, s.n.c.")
        form_layout.addWidget(civico_label, 2, 0)
        form_layout.addWidget(self.civico_edit, 2, 1)

        # Classificazione
        classificazione_label = QLabel("Classificazione:")
        self.classificazione_edit = QLineEdit()
        self.classificazione_edit.setPlaceholderText(
            "Es. Abitazione civile, Deposito, ecc.")

        form_layout.addWidget(classificazione_label, 3, 0)
        form_layout.addWidget(self.classificazione_edit, 3, 1)

        # Consistenza
        consistenza_label = QLabel("Consistenza:")
        self.consistenza_edit = QLineEdit()
        self.consistenza_edit.setPlaceholderText("Es. 120 mq")

        form_layout.addWidget(consistenza_label, 4, 0)
        form_layout.addWidget(self.consistenza_edit, 4, 1)

        # Numero piani
        piani_label = QLabel("Numero piani:")
        self.piani_edit = QSpinBox()
        self.piani_edit.setMinimum(0)
        self.piani_edit.setMaximum(99)
        self.piani_edit.setSpecialValueText("Non specificato")

        form_layout.addWidget(piani_label, 5, 0)
        form_layout.addWidget(self.piani_edit, 5, 1)

        # Numero vani
        vani_label = QLabel("Numero vani:")
        self.vani_edit = QSpinBox()
        self.vani_edit.setMinimum(0)
        self.vani_edit.setMaximum(99)
        self.vani_edit.setSpecialValueText("Non specificato")

        form_layout.addWidget(vani_label, 6, 0)
        form_layout.addWidget(self.vani_edit, 6, 1)

        layout.addLayout(form_layout)

        # Pulsanti
        buttons_layout = QHBoxLayout()

        self.ok_button = QPushButton("Inserisci")
        self.ok_button.clicked.connect(self.handle_insert)

        self.cancel_button = QPushButton("Annulla")
        self.cancel_button.clicked.connect(self.reject)

        buttons_layout.addWidget(self.ok_button)
        buttons_layout.addWidget(self.cancel_button)

        layout.addLayout(buttons_layout)

        self.setLayout(layout)

    def select_localita(self):
        """
        Apre un dialogo per selezionare o gestire la località.
        Permetterà anche la creazione di nuove località.
        """
        if self.comune_id is None:
            QMessageBox.warning(self, "Comune Mancante",
                                "Selezionare un comune per la partita prima di scegliere una località per l'immobile.")
            return

        # Lazy import per evitare dipendenza circolare con dialogs_entity
        from foliarium.ui.dialogs.entity import LocalitaSelectionDialog

        dialog = LocalitaSelectionDialog(self.db_manager,
                                         self.comune_id,
                                         self,
                                         selection_mode=False) # <--- CAMBIATO A False
        
        # Imposta il titolo del dialogo per riflettere la possibilità di gestione/creazione
        dialog.setWindowTitle(f"Seleziona o Crea Località per Comune ID: {self.comune_id}")

        result = dialog.exec()

        # Il LocalitaSelectionDialog, se modificato per get_selected_or_created_localita,
        # dovrebbe restituire un dizionario con id e nome (compreso il civico).
        # Ad esempio: { 'id': 1, 'nome': 'Via Roma, 12 (Via)' }
        if result == QDialog.DialogCode.Accepted:
            if dialog.selected_localita_id is not None and dialog.selected_localita_name is not None:
                self.localita_id = dialog.selected_localita_id
                self.localita_display.setText(dialog.selected_localita_name)
                self.logger.info(
                    f"ImmobileDialog: Località selezionata/creata ID: {self.localita_id}, Nome: '{self.localita_display.text()}'")
            else:
                self.logger.warning(
                    "ImmobileDialog: LocalitaSelectionDialog accettato ma ID/nome località non validi (probabilmente selezione annullata dopo creazione).")
                # Se l'utente crea una località ma poi non la seleziona prima di chiudere,
                # oppure se annulla la selezione, qui potremmo voler pulire.
                self.localita_id = None
                self.localita_display.setText("Nessuna località selezionata")
        else:
            self.logger.info("Selezione/Creazione località annullata dall'utente in ImmobileDialog.")
            # Non fare nulla se l'utente annulla, la selezione precedente (o nessuna) rimane.

    def handle_insert(self):
        """Gestisce l'inserimento dell'immobile."""
        # Validazione input
        natura = self.natura_edit.text().strip()
        if not natura:
            QMessageBox.warning(
                self, "Errore", "La natura dell'immobile è obbligatoria.")
            return

        if not self.localita_id:
            QMessageBox.warning(self, "Errore", "Seleziona una località.")
            return

        # Raccoglie i dati
        numero_civico = self.civico_edit.text().strip() or None
        classificazione = self.classificazione_edit.text().strip() or None
        consistenza = self.consistenza_edit.text().strip() or None
        numero_piani = self.piani_edit.value() if self.piani_edit.value() > 0 else None
        numero_vani = self.vani_edit.value() if self.vani_edit.value() > 0 else None

        # Crea il dizionario dei dati dell'immobile
        self.immobile_data = {
            'natura': natura,
            'localita_id': self.localita_id,
            'localita_nome': self.localita_display.text(),
            'numero_civico': numero_civico,
            'classificazione': classificazione,
            'consistenza': consistenza,
            'numero_piani': numero_piani,
            'numero_vani': numero_vani
        }

        self.accept()

