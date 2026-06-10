"""Dialog di selezione/ricerca: comune, partita, localita."""
from __future__ import annotations

import logging
from typing import Optional

from PyQt6.QtCore import (Qt)
from PyQt6.QtWidgets import (QAbstractItemView, QApplication,
                             QDialog, QFormLayout,
                             QGridLayout, QGroupBox, QHBoxLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem,
                             QMessageBox, QPushButton, QSpinBox, QStyle,
                             QTabWidget, QTableWidget,
                             QTableWidgetItem, QVBoxLayout, QWidget)

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

from foliarium.ui.dialogs.entity.localita import ModificaLocalitaDialog


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
        self.localita_table.setColumnCount(3)
        self.localita_table.setHorizontalHeaderLabels(["ID", "Nome", "Tipologia"])
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
            self.nome_edit_nuova.setPlaceholderText("Es. Repubblica")
            self.tipologia_edit_nuova = QLineEdit()
            self.tipologia_edit_nuova.setPlaceholderText("Es. Via, Piazza, Borgata")
            create_form_layout.addRow(QLabel("Nome località (*):"), self.nome_edit_nuova)
            create_form_layout.addRow(QLabel("Tipologia Stradale (*):"), self.tipologia_edit_nuova)
            self.btn_salva_nuova_localita = QPushButton(QApplication.style().standardIcon(QStyle.StandardPixmap.SP_DialogSaveButton), "Salva Nuova Località")
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
                        tipologia = loc.get('tipologia_stradale') or 'N/D'
                        self.localita_table.setItem(
                            i, 2, QTableWidgetItem(tipologia))
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

    def _handle_double_click(self, item: QTableWidgetItem):
        """Gestisce il doppio click sulla tabella."""
        if self.selection_mode and self.tabs.currentIndex() == 0:
            # Se in modalità selezione e nel tab di visualizzazione, il doppio click seleziona
            self._handle_selection_or_creation() # Chiama il metodo unificato per la selezione
        elif not self.selection_mode and self.tabs.currentIndex() == 0:
            # Se non in modalità selezione (ovvero gestione) e nel tab di visualizzazione,
            # il doppio click apre la modifica (se l'utente ha i permessi e una riga è selezionata).
            self.apri_modifica_localita_selezionata()
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
                _show_status_message("Modifiche alla località salvate.", 4000)
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
                tipologia = self.localita_table.item(current_row, 2).text()

                self.selected_localita_name = nome
                if tipologia and tipologia != 'N/D':
                    self.selected_localita_name += f" ({tipologia})"

                self.logger.info(f"LocalitaSelectionDialog: Località esistente selezionata - ID: {self.selected_localita_id}, Nome: '{self.selected_localita_name}'")
                self.accept() # Accetta il dialogo con la selezione fatta

            except ValueError:
                QMessageBox.critical(self, "Errore Dati", "ID località non valido nella tabella.")
            except Exception as e:
                self.logger.error(f"Errore in _handle_selection_or_creation (selezione esistente): {e}", exc_info=True)
                QMessageBox.critical(self, "Errore Imprevisto", f"Errore durante la conferma della selezione: {e}")

        elif current_tab_index == 1 and not self.selection_mode: # Tab "Crea Nuova Località"
            nome = self.nome_edit_nuova.text().strip()
            tipologia_stradale = self.tipologia_edit_nuova.text().strip()

            if not nome:
                QMessageBox.warning(self, "Dati Mancanti", "Il nome della località è obbligatorio.")
                self.nome_edit_nuova.setFocus()
                return
            if not tipologia_stradale:
                QMessageBox.warning(self, "Dati Mancanti", "La tipologia stradale è obbligatoria (es. Via, Piazza, Borgata).")
                self.tipologia_edit_nuova.setFocus()
                return

            if self.comune_id is None:
                QMessageBox.critical(self, "Errore Interno", "ID Comune non specificato. Impossibile creare località.")
                return

            try:
                localita_id_creata = self.db_manager.insert_localita(
                    self.comune_id, nome, tipologia_stradale
                )

                if localita_id_creata is not None:
                    self.selected_localita_id = localita_id_creata
                    self.selected_localita_name = format_indirizzo(tipologia_stradale, nome)

                    _show_status_message(f"Località '{self.selected_localita_name}' registrata (ID: {self.selected_localita_id}).", 5000)
                    self._pulisci_campi_creazione_localita()
                    self.load_localita()
                    self.tabs.setCurrentIndex(0)
                    self.accept()

                else:
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

    def _salva_nuova_localita_da_tab(self):
        """Salva una nuova località dal tab "Crea Nuova Località"."""
        nome = self.nome_edit_nuova.text().strip()
        tipologia_stradale = self.tipologia_edit_nuova.text().strip()

        if not nome:
            QMessageBox.warning(self, "Dati Mancanti", "Il nome della località è obbligatorio.")
            self.nome_edit_nuova.setFocus()
            return
        if not tipologia_stradale:
            QMessageBox.warning(self, "Dati Mancanti", "La tipologia stradale è obbligatoria (es. Via, Piazza, Borgata).")
            self.tipologia_edit_nuova.setFocus()
            return

        if self.comune_id is None:
            QMessageBox.critical(self, "Errore Interno", "ID Comune non specificato. Impossibile creare località.")
            return

        try:
            localita_id_creata = self.db_manager.insert_localita(
                self.comune_id, nome, tipologia_stradale
            )

            if localita_id_creata is not None:
                _show_status_message(f"Località '{nome}' registrata (ID: {localita_id_creata}).", 5000)
                self.logger.info(f"Nuova località creata tramite tab 'Crea Nuova': ID {localita_id_creata}, Nome: '{nome}'")

                self._pulisci_campi_creazione_localita()
                self.load_localita()
                self.tabs.setCurrentIndex(0)
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
        """Ripulisce i campi di creazione nuova località."""
        self.nome_edit_nuova.clear()
        self.tipologia_edit_nuova.clear()




