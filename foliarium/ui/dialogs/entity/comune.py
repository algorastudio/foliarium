"""Dialog relativi ai comuni."""
from __future__ import annotations

import logging
from typing import Optional, Dict, Any

from PyQt6.QtCore import (QDate, Qt, QTimer)
from PyQt6.QtWidgets import (QAbstractItemView, QApplication,
                             QCheckBox, QComboBox, QDateEdit,
                             QDialog, QFormLayout,
                             QGridLayout, QGroupBox, QHBoxLayout, QHeaderView,
                             QLabel, QLineEdit, QListWidget, QListWidgetItem,
                             QMessageBox, QPushButton, QSpinBox, QStyle,
                             QTabWidget, QTableWidget,
                             QTableWidgetItem, QTextEdit, QVBoxLayout, QWidget,
                             QDialogButtonBox)

from catasto_db_manager import CatastoDBManager
from app_utils import format_indirizzo
from foliarium.ui.widgets.custom import show_status_message as _show_status_message

try:
    from catasto_db_manager import DBMError, DBUniqueConstraintError, DBNotFoundError, DBDataError
except ImportError:
    class DBMError(Exception): pass
    class DBUniqueConstraintError(DBMError): pass
    class DBNotFoundError(DBMError): pass
    class DBDataError(DBMError): pass

from foliarium.ui.dialogs.entity.possessore import ModificaPossessoreDialog


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

        buttons_layout = QHBoxLayout()
        self.btn_archivia = QPushButton("Archivia Comune")
        self.btn_archivia.setObjectName("dangerButton")
        self.btn_archivia.setToolTip("Archivia questo comune (non viene eliminato, solo nascosto)")
        self.btn_archivia.clicked.connect(self._archivia_comune)
        buttons_layout.addWidget(self.btn_archivia)
        buttons_layout.addStretch()

        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        self.button_box.accepted.connect(self._save_changes)
        self.button_box.rejected.connect(self.reject)
        buttons_layout.addWidget(self.button_box)

        main_layout.addLayout(buttons_layout)

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

        # Gestione date
        di_str = self.comune_data_originale.get('data_istituzione'); self.data_istituzione_edit.setDate(QDate.fromString(str(di_str), "yyyy-MM-dd") if di_str else QDate())
        ds_str = self.comune_data_originale.get('data_soppressione'); self.data_soppressione_edit.setDate(QDate.fromString(str(ds_str), "yyyy-MM-dd") if ds_str else QDate())

    def _save_changes(self):
        # --- MODIFICA CHIAVE: Lettura dati dal ComboBox ---
        periodo_id_selezionato = self.periodo_combo.currentData()

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
                _show_status_message("Dati del comune aggiornati con successo.", 4000)
                self.accept()
        except (DBNotFoundError, DBUniqueConstraintError, DBDataError, DBMError) as e:
            QMessageBox.critical(self, "Errore Salvataggio", str(e))
        except Exception as e_gen:
            QMessageBox.critical(self, "Errore Imprevisto", f"Si è verificato un errore: {str(e_gen)}")

    def _archivia_comune(self):
        nome = self.nome_edit.text()
        risposta = QMessageBox.question(
            self, "Conferma Archiviazione",
            f"Archiviare il comune '{nome}'?\n\nNon verrà eliminato, solo nascosto dalle ricerche.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if risposta != QMessageBox.StandardButton.Yes:
            return
        try:
            self.db_manager.archivia_comune(self.comune_id)
            _show_status_message(f"Comune '{nome}' archiviato.", 4000)
            self.reject()  # Chiude il dialog
        except Exception as e:
            QMessageBox.critical(self, "Errore", f"Impossibile archiviare il comune:\n{e}")




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
                _show_status_message("Modifiche al possessore salvate.", 4000)
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
                from foliarium.ui.dialogs.partita import PartitaDetailsDialog
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
            from foliarium.ui.dialogs.partita import ModificaPartitaDialog
            dialog = ModificaPartitaDialog(self.db_manager, partita_id, self)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                self.load_partite_data()
                _show_status_message("Modifiche alla partita salvate.", 4000)
        else:
            QMessageBox.warning(self, "Nessuna Selezione", "Per favore, seleziona una partita da modificare.")
    
    def apri_dettaglio_partita_selezionata(self, item: QTableWidgetItem):
        if not item:
            return
        partita_id = self._get_selected_partita_id()
        if partita_id is not None:
            partita_details_data = self.db_manager.get_partita_details(partita_id)
            if partita_details_data:
                from foliarium.ui.dialogs.partita import PartitaDetailsDialog
                details_dialog = PartitaDetailsDialog(partita_details_data, self)
                details_dialog.exec()
            else:
                QMessageBox.warning(self, "Errore Dati", f"Impossibile recuperare i dettagli per la partita ID {partita_id}.")




