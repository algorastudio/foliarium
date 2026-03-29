
import os,csv,sys,logging,json
from datetime import date, datetime
from typing import Optional, List, Dict, Any, Tuple, TYPE_CHECKING
from app_utils import BulkReportPDF, FPDF_AVAILABLE, _get_default_export_path, prompt_to_open_file
import pandas as pd # Importa pandas

# Importazioni PyQt6
from PyQt6.QtCore import (QDate, QDateTime, QPoint, QProcess, QSettings, 
                          QSize, QStandardPaths, Qt, QTimer, QUrl, 
                          pyqtSignal,QModelIndex,QProcessEnvironment,Qt, QSettings, 
                          pyqtSlot,pyqtSignal ,QThread)

from PyQt6.QtGui import (QCloseEvent, QColor, QDesktopServices, QFont, 
                         QIcon, QPalette, QPixmap, QAction)

# QWebEngineView: opzionale, riservato a future funzionalità web
try:
    from PyQt6.QtWebEngineWidgets import QWebEngineView
    WEB_ENGINE_AVAILABLE = True
except ImportError:
    QWebEngineView = None
    WEB_ENGINE_AVAILABLE = False

from PyQt6.QtWidgets import (QAbstractItemView, QApplication, 
                             QCheckBox, QComboBox, QDateEdit, QDateTimeEdit,
                             QDialog, QDialogButtonBox, QDoubleSpinBox,
                             QFileDialog, QFormLayout, QFrame, QGridLayout,
                             QGroupBox, QHBoxLayout, QHeaderView, QInputDialog,
                             QLabel, QLineEdit, QListWidget, QListWidgetItem,
                             QMainWindow, QMenu, QMessageBox, QProgressBar,
                             QPushButton, QScrollArea, QSizePolicy, QSpacerItem,
                             QSpinBox, QStyle, QStyleFactory, QTabWidget,
                             QTableWidget, QTableWidgetItem, QTextEdit,
                             QVBoxLayout, QWidget,QProgressDialog,QTextBrowser,QSlider, QCompleter,QSplitter)

from config import (
    APP_VERSION,
    SETTINGS_DB_TYPE, SETTINGS_DB_HOST, SETTINGS_DB_PORT,
    SETTINGS_DB_NAME, SETTINGS_DB_USER, SETTINGS_DB_SCHEMA,
    COLONNE_POSSESSORI_DETTAGLI_NUM ,COLONNE_POSSESSORI_DETTAGLI_LABELS,COLONNE_VISUALIZZAZIONE_POSSESSORI_NUM,
    COLONNE_VISUALIZZAZIONE_POSSESSORI_LABELS, COLONNE_INSERIMENTO_POSSESSORI_NUM, COLONNE_INSERIMENTO_POSSESSORI_LABELS,
    NUOVE_ETICHETTE_POSSESSORI)
from dialogs import ( ModificaPossessoreDialog, PartiteComuneDialog, ModificaImmobileDialog,
                     PossessoriComuneDialog, LocalitaSelectionDialog, ModificaComuneDialog,
                     PartitaDetailsDialog, CreateUserDialog, ModificaLocalitaDialog, PeriodoStoricoEditDialog,
                     CreatePossessoreDialog, AlberoGeneralogicoDialog, ConfrontoPartiteDialog)
from custom_widgets import LazyLoadedWidget

# Ottieni un logger specifico per questo modulo.
logger = logging.getLogger("CatastoGUI.gui_widgets")
# In gui_main.py, dopo le importazioni PyQt e standard:
# E le sue eccezioni se servono qui
if TYPE_CHECKING:
    # Questa importazione avviene solo per i type checker (es. MyPy), 
    # non a runtime, quindi non crea il ciclo.
    from gui_main import CatastoMainWindow 
    from catasto_db_manager import CatastoDBManager # Se serve anche per type hint

# In gui_widgets.py, dopo le importazioni PyQt e standard:
from custom_widgets import QPasswordLineEdit, LazyLoadedWidget, StatCard
from dialogs import (DBConfigDialog,DocumentViewerDialog, ModificaPossessoreDialog, PartiteComuneDialog, ModificaImmobileDialog,
                    PossessoriComuneDialog, LocalitaSelectionDialog, ModificaComuneDialog,PeriodoStoricoDetailsDialog,
                    PartitaDetailsDialog,CreateUserDialog)
from dialogs import (ComuneSelectionDialog, PartitaSearchDialog, PossessoreSelectionDialog, ImmobileDialog,LocalitaSelectionDialog, 
                    DettagliLegamePossessoreDialog, UserSelectionDialog,qdate_to_datetime, datetime_to_qdate,_hash_password,_verify_password)

from app_utils import (gui_esporta_partita_pdf, gui_esporta_partita_json, gui_esporta_partita_csv,
                       gui_esporta_possessore_pdf, gui_esporta_possessore_json, gui_esporta_possessore_csv,
                       GenericTextReportPDF,FPDF_AVAILABLE, is_file_locked,get_alternative_filename)
# È possibile che alcune utility (es. hashing) siano usate da dialoghi che ora sono in gui_main.py
# In tal caso, gui_main.py importerà _hash_password da app_utils.py.



# Importazione del gestore DB e eccezioni
try:
    from catasto_db_manager import CatastoDBManager, DBMError, DBUniqueConstraintError, DBNotFoundError, DBDataError
except ImportError:
    # Fallback o gestione errore
    class DBMError(Exception):
        pass  # ... definizioni fallback come nel file originale
    logger.warning("ATTENZIONE: catasto_db_manager non trovato, usando eccezioni DB fallback in gui_widgets.py")
# ---------------------------------------------------------------------------
# Costanti e helper globali UI/UX
# ---------------------------------------------------------------------------
_PROVINCE_ITALIANE = [
    "AG","AL","AN","AO","AP","AQ","AR","AT","AV","BA","BG","BI","BL","BN","BO",
    "BR","BS","BT","BZ","CA","CB","CE","CH","CL","CN","CO","CR","CS","CT","CZ",
    "EN","FC","FE","FG","FI","FM","FR","GE","GO","GR","IM","IS","KR","LC","LE",
    "LI","LO","LT","LU","MB","MC","ME","MI","MN","MO","MS","MT","NA","NO","NU",
    "OG","OR","OT","PA","PC","PD","PE","PG","PI","PN","PO","PR","PT","PU","PV",
    "PZ","RA","RC","RE","RG","RI","RM","RN","RO","SA","SI","SO","SP","SR","SS",
    "SU","SV","TA","TE","TN","TO","TP","TR","TS","TV","UD","VA","VB","VC","VE",
    "VI","VR","VT","VV",
]

_FIELD_ERROR_STYLE = (
    "border: 2px solid #e74c3c; border-radius: 3px; background-color: #fff5f5;"
)


def _set_field_error(widget, has_error: bool) -> None:
    """Applica o rimuove il bordo rosso di errore da un widget di input."""
    widget.setStyleSheet(_FIELD_ERROR_STYLE if has_error else "")


def _show_status_message(message: str, timeout_ms: int = 4000) -> None:
    """Mostra un messaggio nella status bar della finestra principale (non bloccante)."""
    win = QApplication.activeWindow()
    if win and hasattr(win, "statusBar"):
        win.statusBar().showMessage(message, timeout_ms)


# ---------------------------------------------------------------------------

class ElencoComuniWidget(LazyLoadedWidget):
    def __init__(self, db_manager: 'CatastoDBManager', parent=None):
        super().__init__(parent)
        self.logger.debug("Inizializzazione di ElencoComuniWidget")
        if db_manager:
            self.db_manager = db_manager
            self.logger.info(f"Widget inizializzato CORRETTAMENTE con DBManager (ID Oggetto: {id(self.db_manager)})")
        else:
            self.db_manager = None
            self.logger.error("ERRORE CRITICO: ElencoComuniWidget inizializzato SENZA un DBManager valido!")
            QMessageBox.critical(self, "Errore Widget", "Il widget dei comuni non ha ricevuto il gestore del database.")
            return

        layout = QVBoxLayout(self)

        comuni_group = QGroupBox("Elenco Comuni Registrati")
        comuni_layout = QVBoxLayout(comuni_group)

        self.filter_comuni_edit = QLineEdit()
        self.filter_comuni_edit.setPlaceholderText("Filtra per nome, provincia...")
        self.filter_comuni_edit.textChanged.connect(self.apply_filter)
        comuni_layout.addWidget(self.filter_comuni_edit)

        self.comuni_table = QTableWidget()
        self.comuni_table.setColumnCount(7) # ID, Nome, Cod. Cat., Prov., Data Ist., Data Sopp., Note
        self.comuni_table.setHorizontalHeaderLabels([
            "ID", "Nome Comune", "Cod. Catastale", "Provincia",
            "Data Istituzione", "Data Soppressione", "Note"
        ])
        self.comuni_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.comuni_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.comuni_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection) # Importante per menu contestuale su una riga
        self.comuni_table.setAlternatingRowColors(True)
        self.comuni_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.comuni_table.setSortingEnabled(True)
        # self.comuni_table.itemDoubleClicked.connect(self.mostra_partite_del_comune) # Il doppio click può rimanere

        # Imposta la policy per il menu contestuale sulla tabella
        self.comuni_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.comuni_table.customContextMenuRequested.connect(self.apri_menu_contestuale_comune)
        # --- INIZIO MODIFICA ---
        # Collega il segnale di cambio selezione a una funzione che abilita/disabilita i pulsanti
        self.comuni_table.itemSelectionChanged.connect(self._update_action_buttons_state)
        # --- FINE MODIFICA ---

        comuni_layout.addWidget(self.comuni_table)

        action_buttons_layout = QHBoxLayout()
        
        # --- INIZIO MODIFICA: Creazione del nuovo pulsante ---
        self.btn_modifica_comune = QPushButton("Modifica Comune Selezionato")
        self.btn_modifica_comune.clicked.connect(self.azione_modifica_comune)
        self.btn_modifica_comune.setEnabled(False) # Inizia disabilitato
        action_buttons_layout.addWidget(self.btn_modifica_comune)
        # --- FINE MODIFICA ---
        self.btn_mostra_partite = QPushButton("Mostra Partite del Comune Selezionato")
        self.btn_mostra_partite.clicked.connect(self.azione_mostra_partite)
        action_buttons_layout.addWidget(self.btn_mostra_partite)

        self.btn_mostra_possessori = QPushButton("Mostra Possessori del Comune Selezionato")
        self.btn_mostra_possessori.clicked.connect(self.azione_mostra_possessori)
        action_buttons_layout.addWidget(self.btn_mostra_possessori)

        self.btn_mostra_localita = QPushButton("Mostra Località del Comune Selezionato")
        self.btn_mostra_localita.clicked.connect(self.azione_mostra_localita)
        action_buttons_layout.addWidget(self.btn_mostra_localita)
        
        action_buttons_layout.addStretch()
        comuni_layout.addLayout(action_buttons_layout)
        layout.addWidget(comuni_group)
        self.setLayout(layout)

         # Chiamata esplicita per caricare i dati
        self.logger.info("Chiamata a load_comuni_data() da __init__.")
        
    def load_data(self):
        """
        Metodo pubblico per caricare o ricaricare i dati dei comuni nella tabella.
        Questo metodo contiene la logica principale di popolamento.
        """
        self.logger.info(">>> ESECUZIONE DI load_data in ElencoComuniWidget...")
        # Il resto del suo codice da _load_data_on_first_show rimane identico qui...
        self.comuni_table.setSortingEnabled(False)
        self.comuni_table.setRowCount(0)

        try:
            if not self.db_manager:
                self.logger.error("load_data chiamato ma self.db_manager è None!")
                return

            self.logger.info(">>> Chiamata a db_manager.get_all_comuni_details() in corso...")
            comuni_list = self.db_manager.get_all_comuni_details()
            
            self.logger.info(f"--- RISULTATO RICEVUTO da db_manager: Tipo={type(comuni_list)}, Lunghezza={len(comuni_list) if comuni_list is not None else 'None'} ---")

            if not comuni_list:
                self.logger.warning("Nessun comune restituito dal DB manager per la visualizzazione.")
                self.comuni_table.setRowCount(1)
                item = QTableWidgetItem("Nessun comune trovato nel database.")
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.comuni_table.setItem(0, 0, item)
                self.comuni_table.setSpan(0, 0, 1, self.comuni_table.columnCount())
                return
                
            self.logger.info(f">>> Inizio ciclo FOR per popolare la tabella con {len(comuni_list)} elementi.")
            self.comuni_table.setRowCount(len(comuni_list))
            for row_idx, comune in enumerate(comuni_list):
                self.comuni_table.setItem(row_idx, 0, QTableWidgetItem(str(comune.get('id', ''))))
                self.comuni_table.setItem(row_idx, 1, QTableWidgetItem(comune.get('nome_comune', '')))
                self.comuni_table.setItem(row_idx, 2, QTableWidgetItem(comune.get('codice_catastale', '')))
                self.comuni_table.setItem(row_idx, 3, QTableWidgetItem(comune.get('provincia', '')))
                data_ist = comune.get('data_istituzione')
                self.comuni_table.setItem(row_idx, 4, QTableWidgetItem(str(data_ist) if data_ist else ''))
                data_soppr = comune.get('data_soppressione')
                self.comuni_table.setItem(row_idx, 5, QTableWidgetItem(str(data_soppr) if data_soppr else ''))
                self.comuni_table.setItem(row_idx, 6, QTableWidgetItem(comune.get('note', '')))
            
            self.comuni_table.resizeColumnsToContents()
            self.logger.info(">>> Fine ciclo FOR.")

        except Exception as e:
            self.logger.error(f"Errore imprevisto durante il popolamento della tabella comuni: {e}", exc_info=True)
            QMessageBox.critical(self, "Errore Caricamento Dati", f"Si è verificato un errore imprevisto: {e}")
        finally:
            self.comuni_table.setSortingEnabled(True)
            self.logger.info(">>> load_data terminato.")

    def _load_data_on_first_show(self):
        """
        Metodo per il lazy loading. Soddisfa il contratto della classe base
        e chiama il nostro nuovo metodo di caricamento pubblico.
        """
        self.load_data()
    def _slot_modifica_dati_comune(self, comune_id: int):
        """
        Slot per il menu di modifica. Ora chiama il metodo corretto 'load_data'.
        """
        self.logger.info(f"Menu contestuale: richiesta modifica per comune ID {comune_id}")
        dialog = ModificaComuneDialog(self.db_manager, comune_id, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.logger.info(f"Dati del comune ID {comune_id} modificati. Aggiornamento lista comuni.")
            self.load_data()  # <-- CORRETTO
        else:
            self.logger.info(f"Modifica del comune ID {comune_id} annullata dall'utente.")

    def azione_modifica_comune(self):
        """Azione eseguita dal pulsante 'Modifica Comune Selezionato'."""
        selected_info = self._get_selected_comune_info_from_table()
        if selected_info:
            comune_id, _ = selected_info
            self._slot_modifica_dati_comune(comune_id)
        else:
            QMessageBox.information(self, "Nessuna Selezione", "Seleziona un comune dalla tabella per modificarlo.")

    def apply_filter(self):
        """Filtra le righe della tabella in base al testo inserito."""
        filter_text = self.filter_comuni_edit.text().strip().lower()
        for row in range(self.comuni_table.rowCount()):
            row_visible = False
            if not filter_text:  # Se il filtro è vuoto, mostra tutte le righe
                row_visible = True
            else:
                for col in range(self.comuni_table.columnCount()):
                    item = self.comuni_table.item(row, col)
                    if item and filter_text in item.text().lower():
                        row_visible = True
                        break
            self.comuni_table.setRowHidden(row, not row_visible)
        
        filter_text = self.filter_comuni_edit.text().strip().lower()
        for row in range(self.comuni_table.rowCount()):
            row_visible = False
            if not filter_text:
                row_visible = True
            else:
                for col in range(self.comuni_table.columnCount()):
                    item = self.comuni_table.item(row, col)
                    if item and filter_text in item.text().lower():
                        row_visible = True
                        break
            self.comuni_table.setRowHidden(row, not row_visible)
    
    def _get_comune_info_from_row(self, row: int) -> Optional[Tuple[int, str]]:
        """Helper per ottenere ID e nome del comune da una specifica riga."""
        try:
            comune_id_item = self.comuni_table.item(row, 0) # Colonna ID
            nome_comune_item = self.comuni_table.item(row, 1) # Colonna Nome Comune
            if comune_id_item and nome_comune_item and comune_id_item.text().isdigit():
                return int(comune_id_item.text()), nome_comune_item.text()
        except Exception as e:
            self.logger.error(f"Errore nel recuperare info comune dalla riga {row}: {e}")
        return None

    def _get_selected_comune_info_from_table(self) -> Optional[Tuple[int, str]]:
        """Helper per ottenere ID e nome del comune attualmente selezionato nella tabella."""
        current_row = self.comuni_table.currentRow()
        if current_row < 0:
            # Nessuna riga selezionata, ma il menu contestuale potrebbe essere stato attivato su una riga specifica
            # Questo metodo è più per i pulsanti che dipendono da una selezione esplicita.
            return None 
        return self._get_comune_info_from_row(current_row)
    
    

    def _get_selected_comune_info(self) -> Optional[Tuple[int, str]]:
        """Helper per ottenere ID e nome del comune correntemente selezionato nella tabella."""
        selected_items = self.comuni_table.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "Nessuna Selezione",
                                "Seleziona un comune dalla tabella.")
            return None

        # selectedItems può dare più item se la selezione non è per riga
        row = self.comuni_table.currentRow()
        # currentRow è più sicuro per single row selection
        if row < 0:  # Nessuna riga effettivamente selezionata
            QMessageBox.warning(self, "Nessuna Selezione",
                                "Seleziona un comune dalla tabella.")
            return None

        try:
            comune_id_item = self.comuni_table.item(row, 0)  # Colonna ID
            nome_comune_item = self.comuni_table.item(
                row, 1)  # Colonna Nome Comune

            if comune_id_item and nome_comune_item:
                comune_id = int(comune_id_item.text())
                nome_comune = nome_comune_item.text()
                return comune_id, nome_comune
            else:
                QMessageBox.warning(
                    self, "Errore Selezione", "Impossibile recuperare ID o nome del comune dalla riga.")
                return None
        except ValueError:
            QMessageBox.warning(self, "Errore Dati",
                                "L'ID del comune non è un numero valido.")
            return None
        except Exception as e:
            logging.getLogger("CatastoGUI").error(
                f"Errore in _get_selected_comune_info: {e}", exc_info=True)
            QMessageBox.critical(
                self, "Errore", f"Si è verificato un errore imprevisto: {e}")
            return None

    # Questo è per il doppio click
    def mostra_partite_del_comune(self, item: QTableWidgetItem):
        """Apre un dialogo con le partite del comune selezionato tramite doppio click."""
        # Questa funzione ora può usare l'helper se item è valido,
        # o mantenere la sua logica se item è il modo primario per ottenere la riga.
        if not item:
            return
        row = item.row()
        # ... (resto della logica di mostra_partite_del_comune come prima, usando 'row' per prendere ID e nome)
        try:
            comune_id_item = self.comuni_table.item(row, 0)
            nome_comune_item = self.comuni_table.item(row, 1)
            if comune_id_item and nome_comune_item:
                comune_id = int(comune_id_item.text())
                nome_comune = nome_comune_item.text()
                dialog = PartiteComuneDialog(
                    self.db_manager, comune_id, nome_comune, self)
                dialog.exec()
        except ValueError:
            QMessageBox.warning(self, "Errore Dati",
                                "L'ID del comune non è un numero valido.")
        except Exception as e:
            logging.getLogger("CatastoGUI").error(
                f"Errore in mostra_partite_del_comune: {e}", exc_info=True)
            QMessageBox.critical(self, "Errore", f"Errore: {e}")
    def apri_menu_contestuale_comune(self, position: QPoint):
        index = self.comuni_table.indexAt(position)
        if not index.isValid(): return
        row = index.row()
        comune_info = self._get_comune_info_from_row(row)
        if not comune_info: return
        comune_id_selezionato, nome_comune_selezionato = comune_info
        
        menu = QMenu(self.comuni_table)
        
       # ... (azioni esistenti per Visualizza Partite, Possessori, Località) ...
        action_vedi_partite = menu.addAction(QApplication.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogContentsView), "Visualizza Partite")
        action_vedi_partite.triggered.connect(lambda: self._slot_vedi_partite_comune(comune_id_selezionato, nome_comune_selezionato))
        
        action_vedi_possessori = menu.addAction(QApplication.style().standardIcon(QStyle.StandardPixmap.SP_DirLinkIcon), "Visualizza Possessori")
        action_vedi_possessori.triggered.connect(lambda: self._slot_vedi_possessori_comune(comune_id_selezionato, nome_comune_selezionato))

        action_vedi_localita = menu.addAction(QApplication.style().standardIcon(QStyle.StandardPixmap.SP_DirHomeIcon), "Visualizza Località")
        action_vedi_localita.triggered.connect(lambda: self._slot_vedi_localita_comune(comune_id_selezionato, nome_comune_selezionato))
        
        menu.addSeparator()

        # --- NUOVA AZIONE PER MODIFICA COMUNE ---
         # Azione 4: Modifica Dati Comune (senza icona)
        action_modifica_comune = menu.addAction("Modifica Dati Comune")
        action_modifica_comune.triggered.connect(
            lambda: self._slot_modifica_dati_comune(comune_id_selezionato)
        )
        
        menu.exec_(self.comuni_table.viewport().mapToGlobal(position))

   
    def _slot_vedi_partite_comune(self, comune_id: int, nome_comune: str):
        self.logger.info(f"Azione: Visualizza partite per comune ID {comune_id} ('{nome_comune}')")
        dialog = PartiteComuneDialog(self.db_manager, comune_id, nome_comune, self)
        dialog.exec()

    def _slot_vedi_possessori_comune(self, comune_id: int, nome_comune: str):
        self.logger.info(f"Azione: Visualizza possessori per comune ID {comune_id} ('{nome_comune}')")
        dialog = PossessoriComuneDialog(self.db_manager, comune_id, nome_comune, self)
        dialog.exec()

    def _slot_vedi_localita_comune(self, comune_id: int, nome_comune: str):
        self.logger.info(f"Azione: Visualizza località per comune ID {comune_id} ('{nome_comune}')")
        dialog = LocalitaSelectionDialog(self.db_manager, comune_id, self, selection_mode=False)
        dialog.setWindowTitle(f"Località del Comune di {nome_comune}")
        dialog.exec()

     # Metodi per i pulsanti esterni (possono riutilizzare gli slot)
    def azione_mostra_partite(self):
        selected_info = self._get_selected_comune_info_from_table()
        if selected_info:
            self._slot_vedi_partite_comune(selected_info[0], selected_info[1])
        else:
            QMessageBox.information(self, "Nessuna Selezione", "Seleziona un comune dalla tabella.")

    def azione_mostra_possessori(self):
        selected_info = self._get_selected_comune_info_from_table()
        if selected_info:
            self._slot_vedi_possessori_comune(selected_info[0], selected_info[1])
        else:
            QMessageBox.information(self, "Nessuna Selezione", "Seleziona un comune dalla tabella.")
            
    def azione_mostra_localita(self):
        selected_info = self._get_selected_comune_info_from_table()
        if selected_info:
            self._slot_vedi_localita_comune(selected_info[0], selected_info[1])
        else:
            QMessageBox.information(self, "Nessuna Selezione", "Seleziona un comune dalla tabella.")
            
    def _update_action_buttons_state(self):
        """Abilita o disabilita i pulsanti di azione in base alla selezione nella tabella."""
        has_selection = bool(self.comuni_table.selectedItems())
        self.btn_modifica_comune.setEnabled(has_selection)
        self.btn_mostra_partite.setEnabled(has_selection)
        self.btn_mostra_possessori.setEnabled(has_selection)
        self.btn_mostra_localita.setEnabled(has_selection)



class RicercaPartiteWidget(QWidget):
    def __init__(self, db_manager, parent=None):
        super(RicercaPartiteWidget, self).__init__(parent)
        self.db_manager = db_manager

        layout = QVBoxLayout()

        # Criteri di ricerca
        criteria_group = QGroupBox("Criteri di Ricerca")
        criteria_layout = QGridLayout()

        # Comune
        comune_label = QLabel("Comune:")
        self.comune_button = QPushButton("Seleziona Comune...")
        self.comune_button.clicked.connect(self.select_comune)
        self.comune_id = None
        self.comune_display = QLabel("Nessun comune selezionato")
        self.clear_comune_button = QPushButton("Cancella")
        self.clear_comune_button.clicked.connect(self.clear_comune)

        criteria_layout.addWidget(comune_label, 0, 0)
        criteria_layout.addWidget(self.comune_button, 0, 1)
        criteria_layout.addWidget(self.comune_display, 0, 2)
        criteria_layout.addWidget(self.clear_comune_button, 0, 3)

        # Numero partita
        numero_label = QLabel("Numero Partita:")
        self.numero_edit = QSpinBox()
        self.numero_edit.setMinimum(0)
        self.numero_edit.setMaximum(9999)
        self.numero_edit.setSpecialValueText("Qualsiasi")

        criteria_layout.addWidget(numero_label, 1, 0)
        criteria_layout.addWidget(self.numero_edit, 1, 1)

        # Possessore
        possessore_label = QLabel("Nome Possessore:")
        self.possessore_edit = QLineEdit()
        self.possessore_edit.setPlaceholderText("Qualsiasi possessore")

        criteria_layout.addWidget(possessore_label, 2, 0)
        criteria_layout.addWidget(self.possessore_edit, 2, 1, 1, 3)

        # Natura immobile
        natura_label = QLabel("Natura Immobile:")
        self.natura_edit = QLineEdit()
        self.natura_edit.setPlaceholderText("Qualsiasi natura immobile")

        criteria_layout.addWidget(natura_label, 3, 0)
        criteria_layout.addWidget(self.natura_edit, 3, 1, 1, 3)

        criteria_group.setLayout(criteria_layout)
        layout.addWidget(criteria_group)

        # Pulsante Ricerca
        search_button = QPushButton("Cerca Partite")
        search_button.clicked.connect(self.do_search)
        layout.addWidget(search_button)

        # Risultati
        results_group = QGroupBox("Risultati")
        results_layout = QVBoxLayout()

        self.results_table = QTableWidget()
        self.results_table.setColumnCount(5)
        self.results_table.setHorizontalHeaderLabels(
            ["ID", "Comune", "Numero", "Tipo", "Stato"])
        self.results_table.setAlternatingRowColors(True)
        self.results_table.horizontalHeader().setStretchLastSection(True)
        self.results_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.results_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.results_table.setSortingEnabled(True)
        self.results_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.results_table.customContextMenuRequested.connect(self._apri_menu_contestuale_partita)

        self.result_count_label = QLabel("Nessuna ricerca eseguita.")
        self.result_count_label.setStyleSheet("color: #555; font-style: italic; padding: 2px 0;")
        results_layout.addWidget(self.result_count_label)
        results_layout.addWidget(self.results_table)

        # Dettagli partita selezionata
        self.detail_button = QPushButton("Mostra Dettagli Partita")
        self.detail_button.clicked.connect(self.show_details)
        results_layout.addWidget(self.detail_button)

        results_group.setLayout(results_layout)
        layout.addWidget(results_group)

        self.setLayout(layout)

    def select_comune(self):
        """Apre il selettore di comuni."""
        dialog = ComuneSelectionDialog(self.db_manager, self)
        result = dialog.exec()

        if result == QDialog.DialogCode.Accepted and dialog.selected_comune_id:
            self.comune_id = dialog.selected_comune_id
            self.comune_display.setText(dialog.selected_comune_name)

    def clear_comune(self):
        """Cancella il comune selezionato."""
        self.comune_id = None
        self.comune_display.setText("Nessun comune selezionato")

    def do_search(self):
        """Esegue la ricerca partite in base ai criteri."""
        comune_id = self.comune_id
        numero_partita_val = self.numero_edit.value()
        numero_partita = numero_partita_val if numero_partita_val > 0 and self.numero_edit.text(
        ) != self.numero_edit.specialValueText() else None

        possessore = self.possessore_edit.text().strip() or None
        natura = self.natura_edit.text().strip() or None

        # --- Stampa di DEBUG dei parametri inviati ---
        logging.getLogger("CatastoGUI").debug(
            f"RicercaPartiteWidget.do_search - Parametri inviati al DBManager:")
        logging.getLogger("CatastoGUI").debug(
            f"  comune_id: {comune_id} (tipo: {type(comune_id)})")
        logging.getLogger("CatastoGUI").debug(
            f"  numero_partita: {numero_partita} (tipo: {type(numero_partita)})")
        logging.getLogger("CatastoGUI").debug(
            f"  possessore: '{possessore}' (tipo: {type(possessore)})")
        logging.getLogger("CatastoGUI").debug(
            f"  immobile_natura: '{natura}' (tipo: {type(natura)})")
        # --- Fine Stampa di DEBUG ---

        try:
            partite = self.db_manager.search_partite(
                comune_id=comune_id,
                numero_partita=numero_partita,
                possessore=possessore,
                immobile_natura=natura
            )

            # --- Stampa di DEBUG dei risultati ricevuti ---
            logging.getLogger("CatastoGUI").debug(
                f"RicercaPartiteWidget.do_search - Risultati ricevuti dal DBManager (tipo: {type(partite)}):")
            if partite is not None:  # Controlla se partite è None prima di len()
                logging.getLogger("CatastoGUI").debug(
                    f"  Numero di partite ricevute: {len(partite)}")
                # Se vuoi vedere i primi risultati per debug (attenzione con dati sensibili):
                # for i, p_item in enumerate(partite[:3]): # Logga al massimo i primi 3
                #    logging.getLogger("CatastoGUI").debug(f"    Partita {i}: {p_item}")
            else:
                logging.getLogger("CatastoGUI").debug(
                    "  Nessun risultato (variabile 'partite' è None).")
            # --- Fine Stampa di DEBUG ---

            # Pulisce la tabella prima di popolarla
            self.results_table.setSortingEnabled(False)
            self.results_table.setRowCount(0)

            if partite:  # Verifica se la lista 'partite' non è vuota
                self.results_table.setRowCount(len(partite))
                # Usa nomi variabili chiari
                for row_idx, partita_data in enumerate(partite):
                    # Popolamento tabella come da suo codice esistente
                    self.results_table.setItem(
                        row_idx, 0, QTableWidgetItem(str(partita_data.get('id', ''))))
                    self.results_table.setItem(row_idx, 1, QTableWidgetItem(
                        partita_data.get('comune_nome', '')))
                    self.results_table.setItem(row_idx, 2, QTableWidgetItem(
                        str(partita_data.get('numero_partita', ''))))
                    self.results_table.setItem(
                        row_idx, 3, QTableWidgetItem(partita_data.get('tipo', '')))
                    self.results_table.setItem(
                        row_idx, 4, QTableWidgetItem(partita_data.get('stato', '')))
                self.results_table.resizeColumnsToContents()  # Adatta le colonne al contenuto
                self.results_table.setSortingEnabled(True)
                self.result_count_label.setText(f"{len(partite)} partite trovate.")
                _show_status_message(f"Ricerca completata: {len(partite)} partite trovate.", 4000)
            else:
                self.results_table.setSortingEnabled(True)
                logging.getLogger("CatastoGUI").info(
                    "RicercaPartiteWidget.do_search - Nessuna partita trovata o la lista risultati è vuota.")
                self.result_count_label.setText("Nessuna partita trovata con i criteri specificati.")

        except Exception as e:
            logging.getLogger("CatastoGUI").error(
                f"Errore imprevisto durante RicercaPartiteWidget.do_search: {e}", exc_info=True)
            QMessageBox.critical(
                self, "Errore di Ricerca", f"Si è verificato un errore imprevisto durante la ricerca: {e}")

    def show_details(self):
        """Mostra i dettagli della partita selezionata."""
        # Ottiene l'ID della partita selezionata
        selected_items = self.results_table.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "Attenzione",
                                "Seleziona una partita dalla lista.")
            return

        # Ottiene l'ID dalla prima colonna della riga selezionata
        row = selected_items[0].row()
        partita_id_item = self.results_table.item(row, 0)

        if partita_id_item and partita_id_item.text().isdigit():
            partita_id = int(partita_id_item.text())

            # Ottiene i dettagli della partita
            partita = self.db_manager.get_partita_details(partita_id)

            if partita:
                # Crea e mostra una finestra di dialogo per i dettagli
                details_dialog = PartitaDetailsDialog(partita, self)
                details_dialog.exec()
            else:
                QMessageBox.warning(
                    self, "Errore", f"Non è stato possibile recuperare i dettagli della partita ID {partita_id}.")
        else:
            QMessageBox.warning(self, "Errore", "ID partita non valido.")

    def _apri_menu_contestuale_partita(self, position: QPoint):
        """Context menu sul risultato di ricerca partite."""
        index = self.results_table.indexAt(position)
        if not index.isValid():
            return
        row = index.row()
        id_item = self.results_table.item(row, 0)
        numero_item = self.results_table.item(row, 2)
        partita_id_text = id_item.text() if id_item else ""
        numero_text = numero_item.text() if numero_item else ""

        menu = QMenu(self.results_table)
        menu.addAction(
            QApplication.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogContentsView),
            "Apri Dettagli"
        ).triggered.connect(self.show_details)
        menu.addSeparator()
        menu.addAction(f"Copia Numero Partita ({numero_text})").triggered.connect(
            lambda: QApplication.clipboard().setText(numero_text))
        menu.addAction(f"Copia ID ({partita_id_text})").triggered.connect(
            lambda: QApplication.clipboard().setText(partita_id_text))
        menu.exec(self.results_table.viewport().mapToGlobal(position))

    # ======================================================================
    # ECCO LO SLOT CHE STAI CERCANDO DI POSIZIONARE
    # È un metodo della stessa classe che contiene il pulsante e la tabella.
    # ======================================================================
    @pyqtSlot()
    def apri_dialog_modifica_immobile(self):
        """
        Slot che viene eseguito quando si clicca il pulsante "Modifica".
        Apre il dialogo di modifica per l'immobile selezionato.
        """
        selected_rows = self.tabella_immobili.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "Nessuna Selezione", "Per favore, seleziona un immobile dalla tabella da modificare.")
            return

        # Prendi la riga selezionata (anche se sono multiple, consideriamo solo la prima)
        riga_selezionata = selected_rows[0].row()
        
        # Recupera l'ID dell'immobile che abbiamo salvato in precedenza
        primo_item_nella_riga = self.tabella_immobili.item(riga_selezionata, 0)
        if not primo_item_nella_riga:
            QMessageBox.critical(self, "Errore", "Impossibile recuperare i dati dalla riga selezionata.")
            return
            
        immobile_id = primo_item_nella_riga.data(Qt.ItemDataRole.UserRole)

        # Crea e lancia il dialogo, passando tutti i parametri necessari
        dialog = ModificaImmobileDialog(
            db_manager=self.db_manager,
            immobile_id=immobile_id,
            comune_id_partita=self.comune_id_attuale, # Usa l'ID del comune di questo widget
            parent=self  # Il parent è questo widget stesso
        )

        # Esegui il dialogo. Il codice si ferma qui finché il dialogo non viene chiuso.
        # Usiamo exec_() per compatibilità con tutti i nomi
        if dialog.exec() == QDialog.DialogCode.Accepted:
            # Se l'utente ha premuto "Salva" e le modifiche sono state salvate,
            # aggiorna la tabella per mostrare i nuovi dati.
            self.logger.debug("Modifiche salvate. Aggiornamento della vista in corso...")
            self.carica_dati_immobili()
        else:
            self.logger.debug("Operazione di modifica annullata dall'utente.")


class RicercaAvanzataImmobiliWidget(QWidget):
    def __init__(self, db_manager: CatastoDBManager, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.logger = logging.getLogger(f"CatastoGUI.{self.__class__.__name__}")
        self.selected_comune_id: Optional[int] = None
        self.selected_localita_id: Optional[int] = None

        main_layout = QVBoxLayout(self)

        criteria_group = QGroupBox("Criteri di Ricerca Avanzata Immobili")
        criteria_layout = QGridLayout(criteria_group)

        # Riga 0: Comune
        criteria_layout.addWidget(QLabel("Comune:"), 0, 0)
        self.comune_display_label = QLabel("Qualsiasi comune")
        criteria_layout.addWidget(self.comune_display_label, 0, 1)
        self.btn_seleziona_comune = QPushButton("Seleziona...")
        self.btn_seleziona_comune.clicked.connect(
            self._seleziona_comune_per_ricerca)
        criteria_layout.addWidget(self.btn_seleziona_comune, 0, 2)
        self.btn_reset_comune = QPushButton("Reset")
        self.btn_reset_comune.clicked.connect(self._reset_comune_ricerca)
        criteria_layout.addWidget(self.btn_reset_comune, 0, 3)

        # Riga 1: Località
        criteria_layout.addWidget(QLabel("Località:"), 1, 0)
        self.localita_display_label = QLabel("Qualsiasi località")
        criteria_layout.addWidget(self.localita_display_label, 1, 1)
        self.btn_seleziona_localita = QPushButton("Seleziona...")
        self.btn_seleziona_localita.clicked.connect(
            self._seleziona_localita_per_ricerca)
        self.btn_seleziona_localita.setEnabled(False)
        criteria_layout.addWidget(self.btn_seleziona_localita, 1, 2)
        self.btn_reset_localita = QPushButton("Reset")
        self.btn_reset_localita.clicked.connect(self._reset_localita_ricerca)
        criteria_layout.addWidget(self.btn_reset_localita, 1, 3)

        # Riga 2: Natura e Classificazione
        criteria_layout.addWidget(QLabel("Natura Immobile:"), 2, 0)
        self.natura_edit = QLineEdit()
        self.natura_edit.setPlaceholderText(
            "Es. Casa, Terreno (lascia vuoto per qualsiasi)")
        criteria_layout.addWidget(self.natura_edit, 2, 1, 1, 3)

        criteria_layout.addWidget(QLabel("Classificazione:"), 3, 0)
        self.classificazione_edit = QLineEdit()
        self.classificazione_edit.setPlaceholderText(
            "Es. Abitazione civile, Oliveto (lascia vuoto per qualsiasi)")
        criteria_layout.addWidget(self.classificazione_edit, 3, 1, 1, 3)

        # Riga 4: Consistenza (come testo per ricerca parziale)
        criteria_layout.addWidget(QLabel("Testo Consistenza:"), 4, 0)
        self.consistenza_search_edit = QLineEdit()
        self.consistenza_search_edit.setPlaceholderText(
            "Es. 120, are, vani (ricerca parziale)")
        criteria_layout.addWidget(self.consistenza_search_edit, 4, 1, 1, 3)

        # Riga 5: Numero Piani
        criteria_layout.addWidget(QLabel("Piani Min:"), 5, 0)
        self.piani_min_spinbox = QSpinBox()
        self.piani_min_spinbox.setMinimum(0)
        self.piani_min_spinbox.setValue(0)
        criteria_layout.addWidget(self.piani_min_spinbox, 5, 1)
        criteria_layout.addWidget(QLabel("Piani Max:"), 5, 2)
        self.piani_max_spinbox = QSpinBox()
        self.piani_max_spinbox.setMinimum(0)
        self.piani_max_spinbox.setMaximum(99)
        self.piani_max_spinbox.setValue(0)
        self.piani_max_spinbox.setSpecialValueText("Qualsiasi")
        criteria_layout.addWidget(self.piani_max_spinbox, 5, 3)

        # Riga 6: Numero Vani
        criteria_layout.addWidget(QLabel("Vani Min:"), 6, 0)
        self.vani_min_spinbox = QSpinBox()
        self.vani_min_spinbox.setMinimum(0)
        self.vani_min_spinbox.setValue(0)
        criteria_layout.addWidget(self.vani_min_spinbox, 6, 1)
        criteria_layout.addWidget(QLabel("Vani Max:"), 6, 2)
        self.vani_max_spinbox = QSpinBox()
        self.vani_max_spinbox.setMinimum(0)
        self.vani_max_spinbox.setMaximum(999)
        self.vani_max_spinbox.setValue(0)
        self.vani_max_spinbox.setSpecialValueText("Qualsiasi")
        criteria_layout.addWidget(self.vani_max_spinbox, 6, 3)

        # Riga 7: Nome Possessore (NUOVO CAMPO)
        criteria_layout.addWidget(QLabel("Nome Possessore:"), 7, 0)
        self.nome_possessore_edit = QLineEdit()
        self.nome_possessore_edit.setPlaceholderText(
            "Ricerca parziale nome possessore (lascia vuoto per qualsiasi)")
        criteria_layout.addWidget(self.nome_possessore_edit, 7, 1, 1, 3)

        main_layout.addWidget(criteria_group)

        self.btn_esegui_ricerca_immobili = QPushButton(
            "Esegui Ricerca Immobili")
        self.btn_esegui_ricerca_immobili.setIcon(
            QApplication.style().standardIcon(QStyle.StandardPixmap.SP_DialogApplyButton))
        self.btn_esegui_ricerca_immobili.clicked.connect(
            self._esegui_ricerca_effettiva)
        main_layout.addWidget(self.btn_esegui_ricerca_immobili)

        results_group = QGroupBox("Risultati Ricerca")
        results_layout = QVBoxLayout(results_group)
        self.risultati_immobili_table = QTableWidget()
        # Colonne basate sulla funzione SQL cerca_immobili_avanzato
        self.risultati_immobili_table.setColumnCount(10)
        self.risultati_immobili_table.setHorizontalHeaderLabels([
            "ID Imm.", "Part. N.", "Comune", "Località", "Natura",
            "Class.", "Consist.", "Piani", "Vani", "Possessori"
        ])
        self.risultati_immobili_table.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers)
        self.risultati_immobili_table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows)
        self.risultati_immobili_table.setAlternatingRowColors(True)
        self.risultati_immobili_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.ResizeToContents)  # ResizeToContents
        self.risultati_immobili_table.horizontalHeader(
        ).setStretchLastSection(True)  # Ultima colonna stretch
        self.risultati_immobili_table.setSortingEnabled(True)
        self.risultati_immobili_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.risultati_immobili_table.customContextMenuRequested.connect(self._apri_menu_immobile)
        self.result_count_label = QLabel("Nessuna ricerca eseguita.")
        self.result_count_label.setStyleSheet("color: #555; font-style: italic; padding: 2px 0;")
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

            self.risultati_immobili_table.setSortingEnabled(False)
            self.risultati_immobili_table.setRowCount(0)
            if immobili_trovati:
                self.risultati_immobili_table.setRowCount(
                    len(immobili_trovati))
                for row_idx, immobile in enumerate(immobili_trovati):
                    col = 0
                    self.risultati_immobili_table.setItem(
                        row_idx, col, QTableWidgetItem(str(immobile.get('id_immobile', ''))))
                    col += 1
                    self.risultati_immobili_table.setItem(
                        row_idx, col, QTableWidgetItem(str(immobile.get('numero_partita', ''))))
                    col += 1
                    self.risultati_immobili_table.setItem(
                        row_idx, col, QTableWidgetItem(immobile.get('comune_nome', '')))
                    col += 1
                    localita_display = f"{immobile.get('localita_nome', '')}"
                    if immobile.get('civico'):
                        localita_display += f", {immobile.get('civico')}"
                    if immobile.get('localita_tipo'):
                        localita_display += f" ({immobile.get('localita_tipo')})"
                    self.risultati_immobili_table.setItem(
                        row_idx, col, QTableWidgetItem(localita_display.strip()))
                    col += 1
                    self.risultati_immobili_table.setItem(
                        row_idx, col, QTableWidgetItem(immobile.get('natura', '')))
                    col += 1
                    self.risultati_immobili_table.setItem(
                        row_idx, col, QTableWidgetItem(immobile.get('classificazione', '')))
                    col += 1
                    self.risultati_immobili_table.setItem(
                        row_idx, col, QTableWidgetItem(immobile.get('consistenza', '')))
                    col += 1
                    self.risultati_immobili_table.setItem(row_idx, col, QTableWidgetItem(str(
                        immobile.get('numero_piani', '')) if immobile.get('numero_piani') is not None else ''))
                    col += 1
                    self.risultati_immobili_table.setItem(row_idx, col, QTableWidgetItem(str(
                        immobile.get('numero_vani', '')) if immobile.get('numero_vani') is not None else ''))
                    col += 1
                    self.risultati_immobili_table.setItem(
                        row_idx, col, QTableWidgetItem(immobile.get('possessori_attuali', '')))
                    col += 1  # Campo dalla funzione SQL

                self.risultati_immobili_table.setSortingEnabled(True)
                self.result_count_label.setText(f"{len(immobili_trovati)} immobili trovati.")
                _show_status_message(f"Ricerca completata: {len(immobili_trovati)} immobili trovati.", 4000)
            else:
                self.risultati_immobili_table.setSortingEnabled(True)
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
        row = index.row()
        def _cell(col):
            item = self.risultati_immobili_table.item(row, col)
            return item.text() if item else ""
        id_imm, numero, comune, _, natura = _cell(0), _cell(1), _cell(2), _cell(3), _cell(4)
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

# In gui_widgets.py, SOSTITUISCI l'intera classe InserimentoComuneWidget con questa:

class InserimentoComuneWidget(LazyLoadedWidget): # Eredita da LazyLoadedWidget
    comune_appena_inserito = pyqtSignal(int)
    import_csv_requested = pyqtSignal()
    scarica_csv_requested = pyqtSignal()

    def __init__(self, db_manager: 'CatastoDBManager', utente_attuale_info: Optional[Dict[str, Any]], parent=None):
        super().__init__(parent) # Chiama il costruttore della classe base
        self.db_manager = db_manager
        self.utente_attuale_info = utente_attuale_info
        # self.logger e self._data_loaded sono gestiti dalla classe base

        self._initUI()

    def _initUI(self):
        # ... (tutta la definizione della UI rimane la stessa)
        main_layout = QVBoxLayout(self)
        form_group = QGroupBox("Dati del Nuovo Comune")
        form_layout = QFormLayout(form_group)
        form_layout.setSpacing(10)
        self.nome_comune_edit = QLineEdit()
        _lbl_nome = QLabel('Nome Comune <span style="color:#e74c3c;font-weight:bold;">*</span>:')
        form_layout.addRow(_lbl_nome, self.nome_comune_edit)
        self.provincia_edit = QLineEdit("SV")
        self.provincia_edit.setMaxLength(100)
        _prov_completer = QCompleter(_PROVINCE_ITALIANE, self)
        _prov_completer.setCompletionMode(QCompleter.CompletionMode.InlineCompletion)
        _prov_completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.provincia_edit.setCompleter(_prov_completer)
        _lbl_prov = QLabel('Provincia <span style="color:#e74c3c;font-weight:bold;">*</span>:')
        form_layout.addRow(_lbl_prov, self.provincia_edit)
        self.regione_edit = QLineEdit()
        self.regione_edit.setMaxLength(100)
        _lbl_reg = QLabel('Regione <span style="color:#e74c3c;font-weight:bold;">*</span>:')
        form_layout.addRow(_lbl_reg, self.regione_edit)
        # Reset errore al primo carattere digitato
        self.nome_comune_edit.textChanged.connect(lambda: _set_field_error(self.nome_comune_edit, False))
        self.provincia_edit.textChanged.connect(lambda: _set_field_error(self.provincia_edit, False))
        self.regione_edit.textChanged.connect(lambda: _set_field_error(self.regione_edit, False))
        self.codice_catastale_edit = QLineEdit()
        self.codice_catastale_edit.setPlaceholderText("Es. A123 (opzionale)")
        self.codice_catastale_edit.returnPressed.connect(self.inserisci_comune)
        form_layout.addRow("Codice Catastale:", self.codice_catastale_edit)
        self.data_istituzione_check = QCheckBox("Imposta data istituzione")
        self.data_istituzione_edit = QDateEdit(calendarPopup=True)
        self.data_istituzione_edit.setDisplayFormat("yyyy-MM-dd")
        self.data_istituzione_edit.setEnabled(False)
        self.data_istituzione_check.toggled.connect(self.data_istituzione_edit.setEnabled)
        data_istituzione_layout = QHBoxLayout(); data_istituzione_layout.addWidget(self.data_istituzione_check); data_istituzione_layout.addWidget(self.data_istituzione_edit)
        form_layout.addRow("Data Istituzione:", data_istituzione_layout)
        self.data_soppressione_check = QCheckBox("Imposta data soppressione")
        self.data_soppressione_edit = QDateEdit(calendarPopup=True)
        self.data_soppressione_edit.setDisplayFormat("yyyy-MM-dd")
        self.data_soppressione_edit.setEnabled(False)
        self.data_soppressione_check.toggled.connect(self.data_soppressione_edit.setEnabled)
        data_soppressione_layout = QHBoxLayout(); data_soppressione_layout.addWidget(self.data_soppressione_check); data_soppressione_layout.addWidget(self.data_soppressione_edit)
        form_layout.addRow("Data Soppressione:", data_soppressione_layout)
        self.note_edit = QTextEdit()
        self.note_edit.setMinimumHeight(60)
        form_layout.addRow("Note:", self.note_edit)
        self.periodo_combo = QComboBox()
        form_layout.addRow("Periodo Storico:", self.periodo_combo)
        main_layout.addWidget(form_group)
        button_layout = QHBoxLayout()
        self.submit_button = QPushButton("Inserisci Comune")
        self.submit_button.clicked.connect(self.inserisci_comune)
        self.submit_button.setToolTip("Salva il comune nel database (Invio)")
        self.clear_button = QPushButton("Pulisci Campi")
        self.clear_button.clicked.connect(self.pulisci_campi)
        self.clear_button.setToolTip("Azzera tutti i campi del form")
        btn_import = QPushButton("Importa CSV")
        btn_import.clicked.connect(self.import_csv_requested.emit)
        btn_import.setToolTip("Importa più comuni da un file CSV")
        btn_scarica = QPushButton("Scarica CSV")
        btn_scarica.clicked.connect(self.scarica_csv_requested.emit)
        btn_scarica.setToolTip("Scarica i comuni esistenti come file CSV")
        btn_template = QPushButton("Scarica template")
        btn_template.clicked.connect(self._scarica_template_csv)
        btn_template.setToolTip("Scarica un file CSV di esempio con le colonne corrette")
        button_layout.addStretch()
        button_layout.addWidget(self.submit_button)
        button_layout.addWidget(self.clear_button)
        button_layout.addWidget(btn_import)
        button_layout.addWidget(btn_scarica)
        button_layout.addWidget(btn_template)
        main_layout.addLayout(button_layout)
        main_layout.addStretch(1)

    def _load_data_on_first_show(self):
        """Metodo per il lazy loading, chiamato la prima volta."""
        self.logger.info("InserimentoComuneWidget: Esecuzione lazy loading dei periodi storici...")
        self._carica_elenco_periodi()

    def _carica_elenco_periodi(self):
        self.periodo_combo.clear()
        self.periodo_combo.addItem("--- Nessuno ---", None)
        try:
            periodi = self.db_manager.get_historical_periods()
            if periodi:
                for periodo in periodi:
                    display_text = f"{periodo.get('nome')} ({periodo.get('anno_inizio')} - {periodo.get('anno_fine', 'oggi')})"
                    self.periodo_combo.addItem(display_text, periodo.get('id'))
        except DBMError as e:
            QMessageBox.critical(self, "Errore Caricamento", f"Impossibile caricare l'elenco dei periodi storici:\n{e}")


    def _scarica_template_csv(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Salva template CSV comuni", "template_comuni.csv", "File CSV (*.csv)"
        )
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8-sig") as f:
                f.write("nome;provincia;regione;codice_catastale;data_istituzione;data_soppressione;note\n")
                f.write("Savona;SV;Liguria;I480;1861-01-01;;\n")
            QMessageBox.information(self, "Template salvato", f"Template salvato in:\n{path}")
        except Exception as e:
            QMessageBox.critical(self, "Errore", str(e))

    def pulisci_campi(self):
        self.nome_comune_edit.clear(); self.provincia_edit.setText("SV"); self.regione_edit.clear()
        self.codice_catastale_edit.clear(); self.note_edit.clear()
        
        # --- MODIFICA QUI: Resetta anche le checkbox ---
        self.data_istituzione_check.setChecked(False)
        self.data_soppressione_check.setChecked(False)
        # Il segnale 'toggled' disabiliterà automaticamente i QDateEdit
        
        self.periodo_combo.setCurrentIndex(0)
        for w in (self.nome_comune_edit, self.provincia_edit, self.regione_edit):
            _set_field_error(w, False)
        self.nome_comune_edit.setFocus()

    def inserisci_comune(self):
        # Raccoglie i dati da tutti i campi
        nome_comune = self.nome_comune_edit.text().strip()
        provincia = self.provincia_edit.text().strip()
        regione = self.regione_edit.text().strip()
        codice_catastale = self.codice_catastale_edit.text().strip() or None
        note = self.note_edit.toPlainText().strip() or None
        periodo_id_val = self.periodo_combo.currentData()
        
        # --- MODIFICA QUI: Legge le date solo se le checkbox sono spuntate ---
        data_ist = self.data_istituzione_edit.date().toPyDate() if self.data_istituzione_check.isChecked() else None
        data_sopp = self.data_soppressione_edit.date().toPyDate() if self.data_soppressione_check.isChecked() else None

        _set_field_error(self.nome_comune_edit, not nome_comune)
        _set_field_error(self.provincia_edit, not provincia)
        _set_field_error(self.regione_edit, not regione)
        if not all([nome_comune, provincia, regione]):
            return

        username_per_log = self.utente_attuale_info.get('username', 'utente_sconosciuto') if self.utente_attuale_info else 'utente_sconosciuto'
        
        try:
            comune_id = self.db_manager.aggiungi_comune(
                nome_comune=nome_comune, provincia=provincia, regione=regione,
                periodo_id=periodo_id_val, codice_catastale=codice_catastale,
                data_istituzione=data_ist, data_soppressione=data_sopp, # Passa i valori corretti (o None)
                note=note, utente=username_per_log
            )
            _show_status_message(f"Comune '{nome_comune}' inserito con successo (ID: {comune_id}).", 5000)
            self.pulisci_campi()
            self.comune_appena_inserito.emit(comune_id)
        except (DBUniqueConstraintError, DBDataError, DBMError) as e:
            QMessageBox.critical(self, "Errore Inserimento", str(e))

# In gui_widgets.py, aggiungi questa nuova classe

# Estratto in admin_widgets.py — backward compat re-export
from admin_widgets import GestioneTipiLocalitaWidget, GestionePeriodiStoriciWidget
class InserimentoPossessoreWidget(LazyLoadedWidget):
    import_csv_requested = pyqtSignal()
    scarica_csv_requested = pyqtSignal()

    def __init__(self, db_manager: 'CatastoDBManager', parent=None):
        super().__init__(parent)  # Chiama il costruttore della classe base
        self.db_manager = db_manager
        self.comuni_list_data: List[Dict[str, Any]] = []
        # Il logger e il flag _data_loaded sono gestiti dalla classe base

        self._initUI()

    def _initUI(self):
        main_layout = QVBoxLayout(self)
        form_group = QGroupBox("Dati del Nuovo Possessore")
        form_layout = QGridLayout(form_group)
        form_layout.setColumnStretch(1, 1)

        form_layout.addWidget(QLabel('Cognome e Nome <span style="color:#e74c3c;font-weight:bold;">*</span>:'), 0, 0)
        self.cognome_nome_edit = QLineEdit()
        self.cognome_nome_edit.setPlaceholderText("Es. Rossi Mario, Bianchi Giovanni")
        form_layout.addWidget(self.cognome_nome_edit, 0, 1)

        form_layout.addWidget(QLabel("Paternità (es. fu Carlo):"), 1, 0)
        self.paternita_edit = QLineEdit()
        form_layout.addWidget(self.paternita_edit, 1, 1)

        self.btn_genera_nome_completo = QPushButton("Genera Nome Completo")
        self.btn_genera_nome_completo.clicked.connect(self._genera_e_imposta_nome_completo)
        form_layout.addWidget(self.btn_genera_nome_completo, 2, 1, Qt.AlignmentFlag.AlignLeft)

        form_layout.addWidget(QLabel('Nome Completo (generato) <span style="color:#e74c3c;font-weight:bold;">*</span>:'), 3, 0)
        self.nome_completo_edit = QLineEdit()
        self.nome_completo_edit.setPlaceholderText("Verrà generato o inserire manualmente")
        self.nome_completo_edit.returnPressed.connect(self._salva_possessore)
        form_layout.addWidget(self.nome_completo_edit, 3, 1)

        form_layout.addWidget(QLabel('Comune di Riferimento <span style="color:#e74c3c;font-weight:bold;">*</span>:'), 4, 0)
        self.comune_combo = QComboBox()
        self.comune_combo.addItem("Caricamento comuni...", None)
        self.comune_combo.setEnabled(False)
        form_layout.addWidget(self.comune_combo, 4, 1)

        self.attivo_checkbox = QCheckBox("Attivo")
        self.attivo_checkbox.setChecked(True)
        form_layout.addWidget(self.attivo_checkbox, 5, 1)

        # Reset errore al primo carattere digitato
        self.cognome_nome_edit.textChanged.connect(lambda: _set_field_error(self.cognome_nome_edit, False))
        self.nome_completo_edit.textChanged.connect(lambda: _set_field_error(self.nome_completo_edit, False))
        self.comune_combo.currentIndexChanged.connect(lambda: _set_field_error(self.comune_combo, False))

        main_layout.addWidget(form_group)

        button_layout = QHBoxLayout()
        self.save_button = QPushButton("Salva Nuovo Possessore")
        self.save_button.clicked.connect(self._salva_possessore)
        self.save_button.setToolTip("Salva il possessore nel database (Invio)")
        self.clear_button = QPushButton("Pulisci Campi")
        self.clear_button.clicked.connect(self._pulisci_campi_possessore)
        self.clear_button.setToolTip("Azzera tutti i campi del form")
        btn_import = QPushButton("Importa CSV")
        btn_import.clicked.connect(self.import_csv_requested.emit)
        btn_import.setToolTip("Importa più possessori da un file CSV")
        btn_scarica = QPushButton("Scarica CSV")
        btn_scarica.clicked.connect(self.scarica_csv_requested.emit)
        btn_scarica.setToolTip("Scarica i possessori esistenti come file CSV")
        btn_template = QPushButton("Scarica template")
        btn_template.clicked.connect(self._scarica_template_csv)
        btn_template.setToolTip("Scarica un file CSV di esempio con le colonne corrette")
        button_layout.addStretch()
        button_layout.addWidget(self.save_button)
        button_layout.addWidget(self.clear_button)
        button_layout.addWidget(btn_import)
        button_layout.addWidget(btn_scarica)
        button_layout.addWidget(btn_template)
        main_layout.addLayout(button_layout)

        main_layout.addStretch(1)
        self.setLayout(main_layout)

    def _load_data_on_first_show(self):
        """Metodo per il lazy loading: carica i comuni la prima volta che il tab viene visualizzato."""
        self.logger.info("InserimentoPossessoreWidget: Esecuzione lazy loading dei comuni...")
        self._load_comuni_for_combo()

    def _load_comuni_for_combo(self):
        """Carica e popola il QComboBox con l'elenco dei comuni."""
        self.comune_combo.clear()
        try:
            comuni = self.db_manager.get_elenco_comuni_semplice()
            if comuni:
                self.comune_combo.setEnabled(True)
                self.comune_combo.addItem("--- Seleziona un comune ---", None)
                for comune_id, nome in comuni:
                    self.comune_combo.addItem(nome, userData=comune_id)
            else:
                self.comune_combo.addItem("Nessun comune registrato", None)
                self.comune_combo.setEnabled(False)
        except DBMError as e:
            self.logger.error(f"Errore caricamento comuni: {e}")
            self.comune_combo.addItem("Errore caricamento", None)
            self.comune_combo.setEnabled(False)
    def _mostra_info_formato_csv(self):
        """Mostra un dialogo con le informazioni sul formato CSV per i possessori."""
        info_text = """
        <h3>Formato CSV per Importazione Possessori</h3>
        <p>Il file CSV deve rispettare le seguenti regole:</p>
        <ul>
            <li>Utilizzare il punto e virgola (<b>;</b>) come delimitatore.</li>
            <li>La prima riga deve contenere le intestazioni delle colonne.</li>
            <li>Le virgolette doppie (") sono gestite correttamente.</li>
        </ul>
        <p><b>Colonne Richieste:</b></p>
        <ul>
            <li><b>cognome_nome</b>: Il cognome e nome separati da spazio (es. Rossi Mario).</li>
            <li><b>nome_completo</b>: Il nome completo come deve apparire, includendo la paternità.</li>
        </ul>
        <p><b>Colonne Opzionali:</b></p>
        <ul>
            <li><b>paternita</b>: La paternità (es. fu Carlo).</li>
        </ul>
        <hr>
        <p><b>Esempio di contenuto del file:</b></p>
        <pre style="background-color:#f0f0f0; padding:5px;"><code>cognome_nome;paternita;nome_completo
        Rossi Mario;fu Giovanni;Rossi Mario fu Giovanni
        Bianchi Giuseppe;;Bianchi Giuseppe</code></pre>
        """
        QMessageBox.information(self, "Guida Formato CSV - Possessori", info_text)

    def _genera_e_imposta_nome_completo(self):
        """
        Genera il nome completo concatenando "Cognome Nome" e "Paternità"
        e lo imposta nel campo nome_completo_edit.
        """
        cognome_nome = self.cognome_nome_edit.text().strip()
        paternita = self.paternita_edit.text().strip()
        nome_completo_generato = cognome_nome # Inizia con cognome e nome

        if cognome_nome and paternita: # Aggiungi paternità solo se entrambi sono presenti
            nome_completo_generato += f" {paternita}" # Es. "Rossi Mario fu Giovanni"
        elif cognome_nome and not paternita: # Solo cognome e nome
            pass # nome_completo_generato è già corretto
        elif not cognome_nome and paternita: # Solo paternità (improbabile ma gestito)
            nome_completo_generato = paternita 
        else: # Entrambi vuoti
            nome_completo_generato = ""
            
        self.nome_completo_edit.setText(nome_completo_generato.strip())

    def _scarica_template_csv(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Salva template CSV possessori", "template_possessori.csv", "File CSV (*.csv)"
        )
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8-sig") as f:
                f.write("cognome_nome;nome_completo;paternita\n")
                f.write("Rossi Mario;Mario Rossi;fu Giovanni\n")
            QMessageBox.information(self, "Template salvato", f"Template salvato in:\n{path}")
        except Exception as e:
            QMessageBox.critical(self, "Errore", str(e))

    def _pulisci_campi_possessore(self):
        """Pulisce i campi del form possessore."""
        self.cognome_nome_edit.clear()
        self.paternita_edit.clear()
        self.nome_completo_edit.clear()
        if self.comune_combo.count() > 0:
            self.comune_combo.setCurrentIndex(0) # O -1 per nessuna selezione se preferito
        self.attivo_checkbox.setChecked(True)
        for w in (self.cognome_nome_edit, self.nome_completo_edit, self.comune_combo):
            _set_field_error(w, False)
        self.cognome_nome_edit.setFocus()

    def _salva_possessore(self):
        # Ora 'cognome_nome' è l'input primario per nome/cognome
        # 'nome_completo' è quello generato o corretto dall'utente
        cognome_nome_input = self.cognome_nome_edit.text().strip() # Usato per DB e per generare nome completo se serve
        paternita_input = self.paternita_edit.text().strip()
        nome_completo_input = self.nome_completo_edit.text().strip() # Questo è il valore da salvare

        idx_comune = self.comune_combo.currentIndex()
        comune_id_selezionato_data = self.comune_combo.itemData(idx_comune)
        comune_id_selezionato: Optional[int] = None
        if comune_id_selezionato_data is not None:
            try:
                comune_id_selezionato = int(comune_id_selezionato_data)
            except ValueError:
                QMessageBox.warning(self, "Errore Interno", "ID comune selezionato non valido.")
                return

        attivo = self.attivo_checkbox.isChecked()

        _set_field_error(self.nome_completo_edit, not nome_completo_input)
        _set_field_error(self.cognome_nome_edit, not cognome_nome_input)
        _set_field_error(self.comune_combo, comune_id_selezionato is None)
        if not nome_completo_input or not cognome_nome_input or comune_id_selezionato is None:
            if not nome_completo_input:
                self.nome_completo_edit.setFocus()
            elif not cognome_nome_input:
                self.cognome_nome_edit.setFocus()
            else:
                self.comune_combo.setFocus()
            return

        try:
            new_possessore_id = self.db_manager.create_possessore(
                nome_completo=nome_completo_input,
                paternita=paternita_input if paternita_input else None,
                comune_riferimento_id=comune_id_selezionato,
                attivo=attivo,
                cognome_nome=cognome_nome_input # Passa il campo cognome_nome al DB manager
            )

            if new_possessore_id is not None:
                _show_status_message(f"Possessore '{nome_completo_input}' inserito con successo (ID: {new_possessore_id}).", 5000)
                self._pulisci_campi_possessore()
                # Qui potresti emettere un segnale se altri widget devono essere aggiornati
            # else: create_possessore solleva eccezioni
        # ... (stessa gestione eccezioni di prima per _salva_possessore) ...
        except DBUniqueConstraintError as uve:
            logging.getLogger("CatastoGUI").warning(f"Errore di unicità salvando possessore '{nome_completo_input}': {uve.message}")
            QMessageBox.critical(self, "Errore di Unicità", f"Impossibile creare il possessore:\n{uve.message}")
        except DBDataError as dde:
            logging.getLogger("CatastoGUI").warning(f"Errore dati per possessore '{nome_completo_input}': {dde.message}")
            QMessageBox.warning(self, "Dati Non Validi", f"Impossibile creare il possessore:\n{dde.message}")
        except DBMError as dbe:
            logging.getLogger("CatastoGUI").error(f"Errore database salvando possessore '{nome_completo_input}': {dbe.message}", exc_info=True)
            QMessageBox.critical(self, "Errore Database", f"Si è verificato un errore durante la creazione del possessore:\n{dbe.message}")
        except Exception as e:
            logging.getLogger("CatastoGUI").critical(f"Errore critico imprevisto salvando possessore '{nome_completo_input}': {e}", exc_info=True)
            QMessageBox.critical(self, "Errore Critico Imprevisto", f"Errore di sistema imprevisto:\n{type(e).__name__}: {e}")



# --- Scheda per Localita ---
class InserimentoLocalitaWidget(QWidget):
    import_csv_requested = pyqtSignal()
    scarica_csv_requested = pyqtSignal()

    def __init__(self, db_manager, parent=None):
        super(InserimentoLocalitaWidget, self).__init__(parent)
        self.db_manager = db_manager
        self.comune_id = None
        self._initUI()
        # Non carichiamo i tipi qui, ma quando un comune viene selezionato

    def _initUI(self):
        # ... (la UI rimane quasi identica)
        layout = QVBoxLayout(self)
        form_group = QGroupBox("Inserimento Nuova Località")
        form_layout = QGridLayout(form_group)
        comune_label = QLabel('Comune <span style="color:#e74c3c;font-weight:bold;">*</span>:')
        self.comune_button = QPushButton("Seleziona Comune...")
        self.comune_button.clicked.connect(self.select_comune)
        self.comune_display = QLabel("Nessun comune selezionato")
        form_layout.addWidget(comune_label, 0, 0)
        form_layout.addWidget(self.comune_button, 0, 1)
        form_layout.addWidget(self.comune_display, 0, 2)
        nome_label = QLabel('Nome località <span style="color:#e74c3c;font-weight:bold;">*</span>:')
        self.nome_edit = QLineEdit()
        self.nome_edit.textChanged.connect(lambda: _set_field_error(self.nome_edit, False))
        self.nome_edit.returnPressed.connect(self.insert_localita)
        form_layout.addWidget(nome_label, 1, 0)
        form_layout.addWidget(self.nome_edit, 1, 1, 1, 2)
        tipo_label = QLabel('Tipo <span style="color:#e74c3c;font-weight:bold;">*</span>:')
        self.tipo_combo = QComboBox()
        self.tipo_combo.addItem("Seleziona prima un comune...", None)
        self.tipo_combo.setEnabled(False)
        self.tipo_combo.currentIndexChanged.connect(lambda: _set_field_error(self.tipo_combo, False))
        form_layout.addWidget(tipo_label, 2, 0)
        form_layout.addWidget(self.tipo_combo, 2, 1)
        civico_label = QLabel("Civico (opzionale):")
        self.civico_edit = QSpinBox()
        self.civico_edit.setMinimum(0)
        self.civico_edit.setMaximum(9999)
        self.civico_edit.setSpecialValueText("Nessuno")
        form_layout.addWidget(civico_label, 3, 0)
        form_layout.addWidget(self.civico_edit, 3, 1)
        form_group.setLayout(form_layout)
        layout.addWidget(form_group)
        button_layout = QHBoxLayout()
        btn_inserisci = QPushButton("Inserisci Località")
        btn_inserisci.clicked.connect(self.insert_localita)
        btn_inserisci.setToolTip("Salva la località nel database (Invio)")
        self._btn_inserisci_localita = btn_inserisci
        btn_pulisci = QPushButton("Pulisci Campi")
        btn_pulisci.clicked.connect(self._pulisci_campi)
        btn_pulisci.setToolTip("Azzera tutti i campi del form")
        btn_import = QPushButton("Importa CSV")
        btn_import.clicked.connect(self.import_csv_requested.emit)
        btn_import.setToolTip("Importa più località da un file CSV")
        btn_scarica = QPushButton("Scarica CSV")
        btn_scarica.clicked.connect(self.scarica_csv_requested.emit)
        btn_scarica.setToolTip("Scarica le località esistenti come file CSV")
        btn_template = QPushButton("Scarica template")
        btn_template.clicked.connect(self._scarica_template_csv)
        btn_template.setToolTip("Scarica un file CSV di esempio con le colonne corrette")
        button_layout.addStretch()
        button_layout.addWidget(btn_inserisci)
        button_layout.addWidget(btn_pulisci)
        button_layout.addWidget(btn_import)
        button_layout.addWidget(btn_scarica)
        button_layout.addWidget(btn_template)
        layout.addLayout(button_layout)
        summary_group = QGroupBox("Località nel Comune Selezionato")
        summary_layout = QVBoxLayout(summary_group)
        self.refresh_button = QPushButton("Aggiorna Lista")
        self.refresh_button.clicked.connect(self.refresh_localita)
        self.localita_table = QTableWidget()
        self.localita_table.setColumnCount(4)
        self.localita_table.setHorizontalHeaderLabels(["ID", "Nome", "Tipo", "Civico"])
        self.localita_table.setAlternatingRowColors(True)
        self.localita_table.horizontalHeader().setStretchLastSection(True)
        summary_layout.addWidget(self.refresh_button)
        summary_layout.addWidget(self.localita_table)
        layout.addWidget(summary_group)
        self.setLayout(layout)

    def _pulisci_campi(self):
        self.nome_edit.clear()
        self.civico_edit.setValue(0)
        for w in (self.nome_edit, self.tipo_combo):
            _set_field_error(w, False)
        self.nome_edit.setFocus()

    def _scarica_template_csv(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Salva template CSV località", "template_localita.csv", "File CSV (*.csv)"
        )
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8-sig") as f:
                f.write("nome;tipo;civico\n")
                f.write("Via Roma;Via;10\n")
                f.write("Borgata Pianello;Borgata;\n")
            QMessageBox.information(self, "Template salvato", f"Template salvato in:\n{path}")
        except Exception as e:
            QMessageBox.critical(self, "Errore", str(e))

    def _load_tipi_localita(self):
        """Carica dinamicamente le tipologie di località nel ComboBox."""
        self.tipo_combo.clear()
        try:
            tipi = self.db_manager.get_tipi_localita()
            if tipi:
                self.tipo_combo.addItem("--- Seleziona Tipo ---", None)
                for tipo in tipi:
                    self.tipo_combo.addItem(tipo['nome'], tipo['id'])
                self.tipo_combo.setEnabled(True)
            else:
                self.tipo_combo.addItem("Nessuna tipologia definita", None)
                self.tipo_combo.setEnabled(False)
        except DBMError as e:
            self.tipo_combo.addItem("Errore caricamento", None)
            self.tipo_combo.setEnabled(False)
            QMessageBox.critical(self, "Errore", f"Impossibile caricare le tipologie di località:\n{e}")

    def select_comune(self):
        # ... (invariato)
        dialog = ComuneSelectionDialog(self.db_manager, self)
        if dialog.exec() == QDialog.DialogCode.Accepted and dialog.selected_comune_id:
            self.comune_id = dialog.selected_comune_id
            self.comune_display.setText(dialog.selected_comune_name)
            self._load_tipi_localita() # Carica i tipi dopo aver selezionato il comune
            self.refresh_localita()

    def insert_localita(self):
        nome = self.nome_edit.text().strip()
        tipo_id = self.tipo_combo.currentData()
        civico = self.civico_edit.value() if self.civico_edit.value() > 0 else None

        _set_field_error(self.nome_edit, not nome)
        _set_field_error(self.tipo_combo, tipo_id is None)
        if not self.comune_id or not nome or tipo_id is None:
            return

        try:
            localita_id = self.db_manager.insert_localita(self.comune_id, nome, tipo_id, civico)
            _show_status_message(f"Località '{nome}' inserita con successo (ID: {localita_id}).", 5000)
            self.nome_edit.clear()
            self.civico_edit.setValue(0)
            self.refresh_localita()
        except (DBMError, DBDataError, DBUniqueConstraintError) as e:
            QMessageBox.critical(self, "Errore Inserimento", str(e))

    def refresh_localita(self):
        # ... (questo metodo rimane quasi identico, ma deve recuperare il nome del tipo)
        self.localita_table.setRowCount(0)
        if not self.comune_id: return

        try:
            # get_localita_by_comune ora deve fare un JOIN per prendere il nome del tipo
            localita_list = self.db_manager.get_localita_by_comune(self.comune_id)
            # ... (popola la tabella, assicurati che la query restituisca il nome del tipo, non l'id)
            # Se la query db non è stata modificata, la colonna "tipo" conterrà l'ID.
            # Per ora, la lasciamo così, ma l'ideale sarebbe aggiornare la query.
        except Exception as e:
            # ...
            pass

class InserimentoPartitaWidget(QWidget):
    import_csv_requested = pyqtSignal()
    scarica_csv_requested = pyqtSignal()

    def __init__(self, db_manager: 'CatastoDBManager', parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.logger = logging.getLogger(f"CatastoGUI.{self.__class__.__name__}")
        self._initUI()
        self.load_initial_data() # Carichiamo i dati necessari come i comuni

    def _initUI(self):
        main_layout = QVBoxLayout(self)
        form_group = QGroupBox("Dati Nuova Partita")
        form_layout = QFormLayout(form_group)
        form_layout.setSpacing(10)
        
        # --- CAMPI DEL FORM AGGIORNATI SECONDO LO SCHEMA ---
        self.comune_combo = QComboBox()
        self.comune_combo.currentIndexChanged.connect(lambda: _set_field_error(self.comune_combo, False))
        _lbl_comune_p = QLabel('Comune <span style="color:#e74c3c;font-weight:bold;">*</span>:')
        form_layout.addRow(_lbl_comune_p, self.comune_combo)

        self.numero_partita_spin = QSpinBox()
        self.numero_partita_spin.setRange(1, 999999)
        form_layout.addRow("Numero Partita (*):", self.numero_partita_spin)

        self.suffisso_edit = QLineEdit()
        self.suffisso_edit.setPlaceholderText("Es. bis, A (opzionale)")
        self.suffisso_edit.setMaxLength(20)
        self.suffisso_edit.returnPressed.connect(self._salva_partita)
        form_layout.addRow("Suffisso Partita:", self.suffisso_edit)

        self.data_impianto_edit = QDateEdit(calendarPopup=True)
        self.data_impianto_edit.setDisplayFormat("yyyy-MM-dd")
        self.data_impianto_edit.setDate(QDate.currentDate())
        form_layout.addRow("Data Impianto (*):", self.data_impianto_edit)

        # NUOVO: Campo per data_chiusura (opzionale)
        self.data_chiusura_check = QCheckBox("Imposta data chiusura")
        self.data_chiusura_check.toggled.connect(self._toggle_data_chiusura)
        self.data_chiusura_edit = QDateEdit(calendarPopup=True)
        self.data_chiusura_edit.setDisplayFormat("yyyy-MM-dd")
        self.data_chiusura_edit.setEnabled(False) # Inizia disabilitato
        data_chiusura_layout = QHBoxLayout()
        data_chiusura_layout.addWidget(self.data_chiusura_check)
        data_chiusura_layout.addWidget(self.data_chiusura_edit)
        form_layout.addRow("Data Chiusura:", data_chiusura_layout)
        
        # CORRETTO: Campo per numero_provenienza (testuale)
        self.numero_provenienza_edit = QLineEdit()
        self.numero_provenienza_edit.setPlaceholderText("Numero o testo di riferimento (opzionale)")
        self.numero_provenienza_edit.setMaxLength(50)
        form_layout.addRow("Numero Provenienza:", self.numero_provenienza_edit)

        self.tipo_combo = QComboBox()
        self.tipo_combo.addItems(["principale", "secondaria"])
        form_layout.addRow("Tipo (*):", self.tipo_combo)

        self.stato_combo = QComboBox()
        self.stato_combo.addItems(["attiva", "inattiva"])
        form_layout.addRow("Stato (*):", self.stato_combo)

        main_layout.addWidget(form_group)

        button_layout = QHBoxLayout()
        btn_salva = QPushButton("Salva Nuova Partita")
        btn_salva.clicked.connect(self._salva_partita)
        btn_salva.setToolTip("Salva la partita nel database (Invio)")
        self._btn_salva_partita = btn_salva
        btn_pulisci = QPushButton("Pulisci Campi")
        btn_pulisci.clicked.connect(self._pulisci_campi)
        btn_pulisci.setToolTip("Azzera tutti i campi del form")
        btn_import = QPushButton("Importa CSV")
        btn_import.clicked.connect(self.import_csv_requested.emit)
        btn_import.setToolTip("Importa più partite da un file CSV o Excel")
        btn_scarica = QPushButton("Scarica CSV")
        btn_scarica.clicked.connect(self.scarica_csv_requested.emit)
        btn_scarica.setToolTip("Scarica le partite esistenti come file CSV")
        btn_template = QPushButton("Scarica template")
        btn_template.clicked.connect(self._scarica_template_csv)
        btn_template.setToolTip("Scarica un file CSV di esempio con le colonne corrette")
        button_layout.addStretch()
        button_layout.addWidget(btn_salva)
        button_layout.addWidget(btn_pulisci)
        button_layout.addWidget(btn_import)
        button_layout.addWidget(btn_scarica)
        button_layout.addWidget(btn_template)
        main_layout.addLayout(button_layout)

        main_layout.addStretch()
        self.setLayout(main_layout)
        
    def _mostra_info_formato_csv(self):
        """Mostra un dialogo con le informazioni sul formato CSV per le partite."""
        info_text = """
        <h3>Formato CSV per Importazione Partite</h3>
        <p>Il file CSV deve rispettare le seguenti regole:</p>
        <ul>
            <li>Utilizzare il punto e virgola (<b>;</b>) come delimitatore.</li>
            <li>La prima riga deve contenere le intestazioni delle colonne.</li>
        </ul>
        <p><b>Colonne Richieste (*):</b></p>
        <ul>
            <li><b>numero_partita</b> (*): Numero intero della partita.</li>
            <li><b>data_impianto</b> (*): Data in formato YYYY-MM-DD.</li>
            <li><b>stato</b> (*): Testo, 'attiva' o 'inattiva'.</li>
            <li><b>tipo</b> (*): Testo, 'principale' o 'secondaria'.</li>
        </ul>
        <p><b>Colonne Opzionali:</b></p>
        <ul>
            <li><b>suffisso_partita</b>: Suffisso testuale (es. A, bis).</li>
            <li><b>data_chiusura</b>: Data in formato YYYY-MM-DD.</li>
            <li><b>numero_provenienza</b>: Testo o numero di riferimento.</li>
        </ul>
        <hr>
        <p><b>Esempio di contenuto del file:</b></p>
        <pre style="background-color:#f0f0f0; padding:5px;"><code>numero_partita;suffisso_partita;data_impianto;stato;tipo
        1005;A;1980-05-20;attiva;principale
        1006;;1975-11-10;inattiva;principale</code></pre>
        """
        QMessageBox.information(self, "Guida Formato CSV - Partite", info_text)

    def load_initial_data(self):
        """Metodo per caricare i dati necessari, come la lista dei comuni."""
        try:
            comuni = self.db_manager.get_elenco_comuni_semplice()
            self.comune_combo.clear()
            self.comune_combo.addItem("--- Seleziona un comune ---", None)
            for id_comune, nome in comuni:
                self.comune_combo.addItem(nome, id_comune)
        except DBMError as e:
            QMessageBox.critical(self, "Errore Caricamento", f"Impossibile caricare l'elenco dei comuni:\n{e}")
    
    def _toggle_data_chiusura(self, checked):
        """Abilita o disabilita il QDateEdit per la data di chiusura."""
        self.data_chiusura_edit.setEnabled(checked)
        if checked:
            self.data_chiusura_edit.setDate(QDate.currentDate())
        else:
            self.data_chiusura_edit.setDate(QDate()) # Data nulla

    def _pulisci_campi(self):
        self.comune_combo.setCurrentIndex(0)
        self.numero_partita_spin.setValue(1)
        self.suffisso_edit.clear()
        self.data_impianto_edit.setDate(QDate.currentDate())
        self.data_chiusura_check.setChecked(False)
        self.numero_provenienza_edit.clear()
        self.tipo_combo.setCurrentIndex(0)
        self.stato_combo.setCurrentIndex(0)
        _set_field_error(self.comune_combo, False)

    def _scarica_template_csv(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Salva template CSV partite", "template_partite.csv", "File CSV (*.csv)"
        )
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8-sig") as f:
                f.write("comune_nome;numero_partita;suffisso_partita;data_impianto;tipo_partita;numero_provenienza;stato\n")
                f.write("Savona;1;;1900-01-01;principale;;attiva\n")
            QMessageBox.information(self, "Template salvato", f"Template salvato in:\n{path}")
        except Exception as e:
            QMessageBox.critical(self, "Errore", str(e))

    def _salva_partita(self):
        comune_id = self.comune_combo.currentData()
        _set_field_error(self.comune_combo, not comune_id)
        if not comune_id:
            return

        # Recupera i dati dai campi, inclusi i nuovi
        data_chiusura = self.data_chiusura_edit.date().toPyDate() if self.data_chiusura_check.isChecked() else None
        numero_provenienza = self.numero_provenienza_edit.text().strip() or None

        try:
            new_id = self.db_manager.create_partita(
                comune_id=comune_id,
                numero_partita=self.numero_partita_spin.value(),
                tipo=self.tipo_combo.currentText(),
                stato=self.stato_combo.currentText(),
                data_impianto=self.data_impianto_edit.date().toPyDate(),
                suffisso_partita=self.suffisso_edit.text().strip() or None,
                data_chiusura=data_chiusura, # Passa il nuovo valore
                numero_provenienza=numero_provenienza # Passa il nuovo valore
            )
            _show_status_message(f"Partita creata con successo (ID: {new_id}).", 5000)
            self._pulisci_campi()
        except (DBMError, DBUniqueConstraintError, DBDataError) as e:
            QMessageBox.critical(self, "Errore Salvataggio", f"Impossibile salvare la partita:\n{e}")


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
        self.possessori_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch); self.possessori_table.setMinimumHeight(120)
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
        self.immobili_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch); self.immobili_table.setMinimumHeight(120)
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
                QMessageBox.information(self, "Successo",
                                        f"Partita ID {self.selected_partita_id_source} duplicata con successo "
                                        f"in una nuova partita N. {nuovo_numero}{suffisso_display}.")
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
                QMessageBox.information(self, "Successo",
                                        f"Immobile ID {self.selected_immobile_id_transfer} trasferito "
                                        f"alla partita ID {id_partita_dest} con successo.")
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
            table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)  # Natura
            table.horizontalHeader().setSectionResizeMode(
                3, QHeaderView.ResizeMode.Stretch)  # Località
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
                QMessageBox.information(
                    self, "Successo", "Passaggio di proprietà registrato con successo. La nuova partita è stata creata e gli immobili trasferiti.")
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


class StatisticheWidget(LazyLoadedWidget):
    def __init__(self, db_manager, parent=None):
        super().__init__(parent)  # Chiama il costruttore della classe base
        self.db_manager = db_manager
        self.comune_filter_id = None
        # Il self.logger e self._data_loaded sono già gestiti da LazyLoadedWidget

        self._initUI()

    def _initUI(self):
        """Crea l'interfaccia utente, riorganizzata per maggiore chiarezza."""
        main_layout = QVBoxLayout(self)
        
        # Tab principale per separare Statistiche da Manutenzione
        self.main_tabs = QTabWidget()
        main_layout.addWidget(self.main_tabs)

        # --- Contenitore per il tab Statistiche ---
        stats_container_widget = QWidget()
        stats_container_layout = QVBoxLayout(stats_container_widget)
        
        # Sotto-tab per i diversi tipi di statistiche
        stats_sub_tabs = QTabWidget()
        stats_container_layout.addWidget(stats_sub_tabs)
        
        # --- Aggiunta dei tab statistici al sotto-tab ---
        stats_comune_tab = self._create_stats_comune_tab()
        stats_sub_tabs.addTab(stats_comune_tab, "Statistiche per Comune")
        
        immobili_tab = self._create_immobili_tipologia_tab()
        stats_sub_tabs.addTab(immobili_tab, "Immobili per Tipologia")

        grafici_tab = self._create_grafici_tab()
        stats_sub_tabs.addTab(grafici_tab, "Grafici")

        # --- Contenitore per il tab Manutenzione ---
        maintenance_tab = self._create_maintenance_tab()

        # Aggiunta dei tab principali
        self.main_tabs.addTab(stats_container_widget, "📊 Statistiche")
        self.main_tabs.addTab(maintenance_tab, "🔧 Manutenzione Database")
        
    def _create_stats_comune_tab(self):
        """Crea il widget per il tab 'Statistiche per Comune'."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        refresh_button = QPushButton("Aggiorna Statistiche Comuni")
        refresh_button.clicked.connect(self.refresh_stats_comune)
        self.stats_comune_table = QTableWidget()
        self.stats_comune_table.setColumnCount(7)
        self.stats_comune_table.setHorizontalHeaderLabels(["Comune", "Provincia", "Totale Partite", "Partite Attive", "Partite Inattive", "Totale Possessori", "Totale Immobili"])
        self.stats_comune_table.setAlternatingRowColors(True)
        self.stats_comune_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.stats_comune_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.stats_comune_table.customContextMenuRequested.connect(self._apri_menu_stats_comune)
        layout.addWidget(refresh_button)
        layout.addWidget(self.stats_comune_table)
        return widget

    def _create_immobili_tipologia_tab(self):
        """Crea il widget per il tab 'Immobili per Tipologia'."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        filter_layout = QHBoxLayout()
        self.comune_filter_button = QPushButton("Filtra per Comune...")
        self.comune_filter_button.clicked.connect(self.filter_immobili_per_comune)
        self.comune_filter_display = QLabel("Visualizzando tutti i comuni")
        self.clear_filter_button = QPushButton("Rimuovi Filtro")
        self.clear_filter_button.clicked.connect(self.clear_immobili_filter)
        filter_layout.addWidget(self.comune_filter_button)
        filter_layout.addWidget(self.comune_filter_display)
        filter_layout.addWidget(self.clear_filter_button)
        layout.addLayout(filter_layout)
        refresh_button = QPushButton("Aggiorna Statistiche Immobili")
        refresh_button.clicked.connect(self.refresh_immobili_tipologia)
        layout.addWidget(refresh_button)
        self.immobili_table = QTableWidget()
        self.immobili_table.setColumnCount(6)
        self.immobili_table.setHorizontalHeaderLabels(["Comune", "Classificazione", "Numero Immobili", "Totale Piani", "Totale Vani", "Media Vani/Immobile"])
        self.immobili_table.setAlternatingRowColors(True)
        self.immobili_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.immobili_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.immobili_table.customContextMenuRequested.connect(self._apri_menu_immobili_stats)
        layout.addWidget(self.immobili_table)
        return widget

    def _create_grafici_tab(self):
        """Crea il tab con grafici statistici via matplotlib."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        try:
            from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
            from matplotlib.figure import Figure
            import matplotlib
            matplotlib.use('QtAgg')

            btn_aggiorna = QPushButton("Aggiorna Grafici")
            btn_aggiorna.clicked.connect(self._aggiorna_grafici)
            layout.addWidget(btn_aggiorna)

            # Figura matplotlib con 3 assi
            self._fig = Figure(figsize=(10, 8), tight_layout=True)
            self._ax_partite = self._fig.add_subplot(2, 2, 1)
            self._ax_stato   = self._fig.add_subplot(2, 2, 2)
            self._ax_variaz  = self._fig.add_subplot(2, 1, 2)
            self._canvas = FigureCanvas(self._fig)
            layout.addWidget(self._canvas, 1)
            self._matplotlib_ok = True
        except Exception as e:
            self._matplotlib_ok = False
            lbl = QLabel(f"Grafici non disponibili: {e}\n\nInstalla matplotlib: pip install matplotlib")
            lbl.setWordWrap(True)
            layout.addWidget(lbl)

        return widget

    def _aggiorna_grafici(self):
        if not getattr(self, '_matplotlib_ok', False):
            return
        try:
            stats = self.db_manager.get_statistiche_comune() or []

            # --- Grafico 1: Partite per comune (bar orizzontale, top 10) ---
            ax = self._ax_partite
            ax.clear()
            dati = sorted(stats, key=lambda r: r.get('totale_partite', 0), reverse=True)[:10]
            comuni = [r.get('comune', '') for r in dati]
            totali = [r.get('totale_partite', 0) for r in dati]
            ax.barh(comuni[::-1], totali[::-1], color='steelblue')
            ax.set_title('Partite per comune (top 10)')
            ax.set_xlabel('Totale partite')

            # --- Grafico 2: Stato partite (torta attive/inattive) ---
            ax2 = self._ax_stato
            ax2.clear()
            tot_attive  = sum(r.get('partite_attive', 0)   for r in stats)
            tot_inattive = sum(r.get('partite_inattive', 0) for r in stats)
            if tot_attive + tot_inattive > 0:
                ax2.pie([tot_attive, tot_inattive],
                        labels=['Attive', 'Inattive'],
                        colors=['#4CAF50', '#F44336'],
                        autopct='%1.1f%%', startangle=90)
            ax2.set_title('Stato partite (totale)')

            # --- Grafico 3: Variazioni per anno ---
            ax3 = self._ax_variaz
            ax3.clear()
            try:
                variaz = self.db_manager.get_elenco_variazioni_per_esportazione(None) or []
                anni: dict = {}
                for v in variaz:
                    data = v.get('data_variazione') or ''
                    anno = str(data)[:4]
                    if anno.isdigit():
                        anni[anno] = anni.get(anno, 0) + 1
                if anni:
                    anni_ord = sorted(anni.keys())
                    ax3.bar(anni_ord, [anni[a] for a in anni_ord], color='darkorange')
                    ax3.set_title('Variazioni per anno')
                    ax3.set_xlabel('Anno')
                    ax3.set_ylabel('N. variazioni')
                    ax3.tick_params(axis='x', rotation=45)
            except Exception:
                ax3.set_title('Variazioni per anno (dati non disponibili)')

            self._canvas.draw()
        except Exception as e:
            self.logger.error(f"Errore aggiornamento grafici: {e}", exc_info=True)

    def _create_maintenance_tab(self):
        """Crea il widget per il tab 'Manutenzione'."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        group = QGroupBox("Operazioni di Manutenzione")
        group_layout = QVBoxLayout(group)
        
        # Sezione Viste
        viste_label = QLabel("Le viste materializzate migliorano le performance delle statistiche. Aggiornale periodicamente.")
        viste_label.setWordWrap(True)
        self.update_views_button = QPushButton("Aggiorna Tutte le Viste Materializzate")
        self.update_views_button.clicked.connect(self.update_all_views)
        group_layout.addWidget(viste_label)
        group_layout.addWidget(self.update_views_button)
        
        group_layout.addWidget(QFrame(self, frameShape=QFrame.Shape.HLine))

        
        layout.addWidget(group)

        self.status_text = QTextEdit()
        self.status_text.setReadOnly(True)
        self.status_text.setPlaceholderText("L'esito delle operazioni di manutenzione apparirà qui...")
        layout.addWidget(self.status_text, 1) # Dà più spazio al log
        return widget

    def _load_data_on_first_show(self):
        """Carica i dati iniziali la prima volta che il tab viene mostrato."""
        self.logger.info("StatisticheWidget: Esecuzione lazy loading...")
        self.refresh_stats_comune()
        self.refresh_immobili_tipologia()
        self._aggiorna_grafici()

    def refresh_stats_comune(self):
        self.logger.info("Aggiornamento statistiche comuni...")
        self.stats_comune_table.setRowCount(0)
        try:
            stats = self.db_manager.get_statistiche_comune()
            if stats:
                self.stats_comune_table.setRowCount(len(stats))
                for i, s in enumerate(stats):
                    self.stats_comune_table.setItem(i, 0, QTableWidgetItem(s.get('comune', '')))
                    self.stats_comune_table.setItem(i, 1, QTableWidgetItem(s.get('provincia', '')))
                    self.stats_comune_table.setItem(i, 2, QTableWidgetItem(str(s.get('totale_partite', 0))))
                    self.stats_comune_table.setItem(i, 3, QTableWidgetItem(str(s.get('partite_attive', 0))))
                    self.stats_comune_table.setItem(i, 4, QTableWidgetItem(str(s.get('partite_inattive', 0))))
                    self.stats_comune_table.setItem(i, 5, QTableWidgetItem(str(s.get('totale_possessori', 0))))
                    self.stats_comune_table.setItem(i, 6, QTableWidgetItem(str(s.get('totale_immobili', 0))))
                self.stats_comune_table.resizeColumnsToContents()
            self.log_status("Statistiche comuni aggiornate con successo.")
        except DBMError as e:
            self.log_status(f"Errore DB durante l'aggiornamento delle statistiche comuni: {e}", error=True)
            QMessageBox.critical(self, "Errore", f"Impossibile caricare le statistiche:\n{e}")

    def filter_immobili_per_comune(self):
        dialog = ComuneSelectionDialog(self.db_manager, self)
        if dialog.exec() == QDialog.DialogCode.Accepted and dialog.selected_comune_id:
            self.comune_filter_id = dialog.selected_comune_id
            self.comune_filter_display.setText(f"Comune: {dialog.selected_comune_name}")
            self.refresh_immobili_tipologia()

    def clear_immobili_filter(self):
        self.comune_filter_id = None
        self.comune_filter_display.setText("Visualizzando tutti i comuni")
        self.refresh_immobili_tipologia()

    def refresh_immobili_tipologia(self):
        self.logger.info("Aggiornamento statistiche immobili per tipologia...")
        self.immobili_table.setRowCount(0)
        try:
            stats = self.db_manager.get_immobili_per_tipologia(self.comune_filter_id)
            if stats:
                self.immobili_table.setRowCount(len(stats))
                for i, s in enumerate(stats):
                    self.immobili_table.setItem(i, 0, QTableWidgetItem(s.get('comune_nome', '')))
                    self.immobili_table.setItem(i, 1, QTableWidgetItem(s.get('classificazione', 'N/D')))
                    num_immobili = s.get('numero_immobili', 0)
                    self.immobili_table.setItem(i, 2, QTableWidgetItem(str(num_immobili)))
                    self.immobili_table.setItem(i, 3, QTableWidgetItem(str(s.get('totale_piani', 0))))
                    totale_vani = s.get('totale_vani', 0)
                    self.immobili_table.setItem(i, 4, QTableWidgetItem(str(totale_vani)))
                    media_vani = round(totale_vani / num_immobili, 2) if num_immobili > 0 else 0
                    self.immobili_table.setItem(i, 5, QTableWidgetItem(str(media_vani)))
                self.immobili_table.resizeColumnsToContents()
            status_text = "Statistiche immobili aggiornate"
            if self.comune_filter_id:
                status_text += f" (filtrate per {self.comune_filter_display.text()})"
            self.log_status(status_text + ".")
        except DBMError as e:
            self.log_status(f"Errore DB durante l'aggiornamento delle statistiche immobili: {e}", error=True)
            QMessageBox.critical(self, "Errore", f"Impossibile caricare le statistiche:\n{e}")

    def update_all_views(self):
        self.log_status("Avvio aggiornamento di tutte le viste materializzate...")
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            if self.db_manager.refresh_materialized_views():
                self.log_status("Aggiornamento viste completato con successo.")
                self.refresh_stats_comune()
                self.refresh_immobili_tipologia()
            else:
                self.log_status("ERRORE: Aggiornamento viste non riuscito. Controllare i log.", error=True)
        finally:
            QApplication.restoreOverrideCursor()

    

    def log_status(self, message, error=False):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        formatted_message = f"[{timestamp}] {message}"
        if error:
            self.status_text.append(f"<font color='red'>{formatted_message}</font>")
        else:
            self.status_text.append(formatted_message)
        self.status_text.verticalScrollBar().setValue(self.status_text.verticalScrollBar().maximum())
        QApplication.processEvents()

    def _apri_menu_stats_comune(self, position: QPoint):
        """Context menu sulla tabella statistiche per comune."""
        index = self.stats_comune_table.indexAt(position)
        if not index.isValid():
            return
        row = index.row()
        comune_item = self.stats_comune_table.item(row, 0)
        prov_item = self.stats_comune_table.item(row, 1)
        comune = comune_item.text() if comune_item else ""
        prov = prov_item.text() if prov_item else ""

        menu = QMenu(self.stats_comune_table)
        if comune:
            menu.addAction(f"Copia comune  ({comune})").triggered.connect(
                lambda: QApplication.clipboard().setText(comune))
        if prov:
            menu.addAction(f"Copia provincia  ({prov})").triggered.connect(
                lambda: QApplication.clipboard().setText(prov))
        menu.addSeparator()
        def _copia_riga():
            parts = []
            for col in range(self.stats_comune_table.columnCount()):
                item = self.stats_comune_table.item(row, col)
                parts.append(item.text() if item else "")
            QApplication.clipboard().setText("\t".join(parts))
        menu.addAction("Copia riga intera").triggered.connect(_copia_riga)
        menu.exec(self.stats_comune_table.viewport().mapToGlobal(position))

    def _apri_menu_immobili_stats(self, position: QPoint):
        """Context menu sulla tabella statistiche immobili per tipologia."""
        index = self.immobili_table.indexAt(position)
        if not index.isValid():
            return
        row = index.row()
        comune_item = self.immobili_table.item(row, 0)
        class_item = self.immobili_table.item(row, 1)
        comune = comune_item.text() if comune_item else ""
        classificazione = class_item.text() if class_item else ""

        menu = QMenu(self.immobili_table)
        if comune:
            menu.addAction(f"Copia comune  ({comune})").triggered.connect(
                lambda: QApplication.clipboard().setText(comune))
        if classificazione:
            menu.addAction(f"Copia classificazione  ({classificazione})").triggered.connect(
                lambda: QApplication.clipboard().setText(classificazione))
        menu.addSeparator()
        def _copia_riga():
            parts = []
            for col in range(self.immobili_table.columnCount()):
                item = self.immobili_table.item(row, col)
                parts.append(item.text() if item else "")
            QApplication.clipboard().setText("\t".join(parts))
        menu.addAction("Copia riga intera").triggered.connect(_copia_riga)
        menu.exec(self.immobili_table.viewport().mapToGlobal(position))

# Estratto in admin_widgets.py — backward compat re-export
# Estratto in reporting_widgets.py — backward compat re-export
from reporting_widgets import (
    RicercaDocumentiWidget, EsportazioniWidget, ReportisticaWidget,
    StatisticheWidget, RegistraConsultazioneWidget,
)

from admin_widgets import GestioneUtentiWidget, AuditLogViewerWidget, BackupWidget

class UnifiedFuzzySearchThread(QThread):
    """Thread unificato per eseguire ricerche fuzzy in background."""
    results_ready = pyqtSignal(dict)
    error_occurred = pyqtSignal(str)
    progress_updated = pyqtSignal(int)

    def __init__(self, gin_search_manager, query_text, options):
        super().__init__()
        self.gin_search_manager = gin_search_manager
        self.query_text = query_text
        self.options = options

    def run(self):
        """Esegue la ricerca fuzzy."""
        try:
            self.progress_updated.emit(10)
            
            threshold = self.options.get('threshold', 0.3)
            max_results = self.options.get('max_results', 100)

            # --- MODIFICA: Logica di ricerca semplificata ---
            # Questo thread ora chiama un metodo unificato che a sua volta
            # orchestra le ricerche individuali.
            # Assumiamo che `gin_search_manager` abbia un metodo come `search_all_entities_fuzzy`.
            if not hasattr(self.gin_search_manager, 'search_all_entities_fuzzy'):
                self.error_occurred.emit("Il DB Manager non supporta 'search_all_entities_fuzzy'.")
                return

            self.progress_updated.emit(30)

            results_data = self.gin_search_manager.search_all_entities_fuzzy(
                query_text=self.query_text,
                search_possessori=self.options.get('search_possessori', True),
                search_localita=self.options.get('search_localita', True),
                search_immobili=self.options.get('search_immobili', True),
                search_variazioni=self.options.get('search_variazioni', True),
                search_contratti=self.options.get('search_contratti', True),
                search_partite=self.options.get('search_partite', True),
                max_results_per_type=self.options.get('max_results_per_type', 50),
                similarity_threshold=threshold
            )

            # Prepara il dizionario finale per l'emissione del segnale
            final_results = {
                'query_text': self.query_text,
                'threshold': threshold,
                'timestamp': datetime.now(),
                'total_results': sum(len(entities) for entities in results_data.values()),
                'results_by_type': results_data # Mantiene la struttura per tipo
            }

            self.progress_updated.emit(100)
            self.results_ready.emit(final_results)

        except Exception as e:
            logging.getLogger(__name__).error(f"Errore nel thread di ricerca: {e}", exc_info=True)
            self.error_occurred.emit(str(e))


# ========================================================================
# WIDGET PRINCIPALE UNIFICATO
# ========================================================================

class UnifiedFuzzySearchWidget(QWidget):
    """Widget unificato per ricerca fuzzy con una singola interfaccia robusta."""

    # --- MODIFICA: Il costruttore non ha più il parametro 'mode' ---
    def __init__(self, db_manager, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.parent_window = parent
        self.logger = logging.getLogger(__name__)

        # Inizializza componenti GIN. Assumiamo che db_manager sia già esteso.
        self.gin_search = self.db_manager

        # Variabili di stato
        self.current_results = {}
        self.search_thread = None
        self.search_timer = QTimer()
        self.search_timer.setSingleShot(True)
        self.search_timer.timeout.connect(self._perform_search)

        # Setup UI
        self._init_ui() # --- MODIFICA: Chiamata a un singolo metodo di setup UI
        self._setup_signals()
        self._check_gin_status()

  

    def _init_ui(self):
        """Configura l'interfaccia utente unificata con un layout robusto."""
        # Layout principale dell'intero widget
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        # --- INIZIO NUOVA STRUTTURA ---
        # 1. Creiamo un widget contenitore per tutti i contenuti tranne la status bar
        content_container_widget = QWidget()
        content_layout = QVBoxLayout(content_container_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(10)
        # --- FINE NUOVA STRUTTURA ---

        # === AREA RICERCA (da aggiungere al content_layout) ===
        search_frame = QFrame()
        search_frame.setFrameStyle(QFrame.Shape.StyledPanel)
        search_frame.setMaximumHeight(120)
        search_layout = QVBoxLayout(search_frame)
        search_layout.setContentsMargins(10, 8, 10, 8)
        # ... (il codice interno di search_frame, search_row, controls_row rimane identico)
        search_row = QHBoxLayout()
        search_row.addWidget(QLabel("🔍"))
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Cerca in possessori, località, immobili, variazioni, contratti, partite...")
        search_row.addWidget(self.search_edit, 1)
        self.search_btn = QPushButton("Cerca")
        search_row.addWidget(self.search_btn)
        self.clear_btn = QPushButton("🗑️")
        self.clear_btn.setMaximumWidth(30)
        search_row.addWidget(self.clear_btn)
        search_layout.addLayout(search_row)
        # --- BLOCCO "CONTROLLI AVANZATI" DA SOSTITUIRE ---
        controls_row = QHBoxLayout()
        controls_row.addWidget(QLabel("Soglia:"))
        self.precision_slider = QSlider(Qt.Orientation.Horizontal)
        self.precision_slider.setRange(10, 90)
        self.precision_slider.setValue(30)
        self.precision_slider.setMaximumWidth(100)
        controls_row.addWidget(self.precision_slider)

        self.precision_label = QLabel("0.30")
        self.precision_label.setMinimumWidth(30)
        controls_row.addWidget(self.precision_label)

        controls_row.addWidget(QLabel("Max Risultati:"))
        self.max_results_combo = QComboBox()
        self.max_results_combo.addItems(["50", "100", "200", "500"])
        self.max_results_combo.setCurrentText("100")
        self.max_results_combo.setMaximumWidth(70)
        controls_row.addWidget(self.max_results_combo)

        controls_row.addStretch()

        # Creiamo i nuovi pulsanti specifici
        self.btn_export_csv = QPushButton("Esporta CSV")
        self.btn_export_csv.setEnabled(False)
        controls_row.addWidget(self.btn_export_csv)

        self.btn_export_pdf = QPushButton("Esporta PDF")
        self.btn_export_pdf.setEnabled(False)
        if not FPDF_AVAILABLE:
            self.btn_export_pdf.setToolTip("Libreria FPDF2 non trovata. Funzione non disponibile.")
        controls_row.addWidget(self.btn_export_pdf)
        
        # La riga errata "controls_row.addWidget(self.export_btn)" è stata rimossa.
        
        search_layout.addLayout(controls_row)
        # --- FINE BLOCCO DA SOSTITUIRE ---
        
        content_layout.addWidget(search_frame) # AGGIUNTO AL CONTENT_LAYOUT

        # === CHECKBOXES (da aggiungere al content_layout) ===
        types_layout = QHBoxLayout()
        types_group = QGroupBox("Cerca in:")
        types_group_layout = QHBoxLayout(types_group)
        # ... (tutte le checkbox vengono create e aggiunte a types_group_layout come prima) ...
        self.search_possessori_cb = QCheckBox("👥 Possessori"); self.search_possessori_cb.setChecked(True); types_group_layout.addWidget(self.search_possessori_cb)
        self.search_localita_cb = QCheckBox("🏘️ Località"); self.search_localita_cb.setChecked(True); types_group_layout.addWidget(self.search_localita_cb)
        self.search_immobili_cb = QCheckBox("🏢 Immobili"); self.search_immobili_cb.setChecked(True); types_group_layout.addWidget(self.search_immobili_cb)
        self.search_variazioni_cb = QCheckBox("📋 Variazioni"); self.search_variazioni_cb.setChecked(True); types_group_layout.addWidget(self.search_variazioni_cb)
        self.search_contratti_cb = QCheckBox("📄 Contratti"); self.search_contratti_cb.setChecked(True); types_group_layout.addWidget(self.search_contratti_cb)
        self.search_partite_cb = QCheckBox("📊 Partite"); self.search_partite_cb.setChecked(True); types_group_layout.addWidget(self.search_partite_cb)
        types_layout.addWidget(types_group)

        content_layout.addLayout(types_layout) # AGGIUNTO AL CONTENT_LAYOUT

        # === AREA RISULTATI (da aggiungere al content_layout) ===
        self.results_tabs = QTabWidget()
        self.results_tabs.setMinimumHeight(400)
        # ... (tutta la creazione delle tabelle e l'aggiunta a results_tabs rimane identica) ...
        self.unified_table = self._create_table_widget(["Tipo", "Nome/Descrizione", "Dettagli", "Similarità", "Campo"], [1, 2], 3); self.results_tabs.addTab(self.unified_table, "🔍 Tutti")
        self.possessori_table = self._create_table_widget(["Nome Completo", "Comune", "Partite", "Similitud."], [0], 3); self.results_tabs.addTab(self.possessori_table, "👥 Possessori")
        self.localita_table = self._create_table_widget(["Nome", "Tipo", "Civico", "Comune", "Immobili", "Similitud."], [0, 3], 5); self.results_tabs.addTab(self.localita_table, "📍 Località")
        self.immobili_table = self._create_table_widget(["Natura", "Classificazione", "Partita", "Suffisso", "Comune", "Similitud."], [1, 4], 5); self.results_tabs.addTab(self.immobili_table, "🏢 Immobili")
        self.variazioni_table = self._create_table_widget(["Tipo", "Data", "Rif. e Partita Origine", "Similitud."], [2], 3)
        self.results_tabs.addTab(self.variazioni_table, "📋 Variazioni")
        self.contratti_table = self._create_table_widget(["Tipo", "Data", "Partita", "Similitud."], [0], 3); self.results_tabs.addTab(self.contratti_table, "📄 Contratti")
        # --- MODIFICA QUESTA RIGA ---
        self.partite_table = self._create_table_widget(
            ["Numero", "Suffisso", "Possessori", "Tipo", "Stato", "Data Impianto", "Comune", "Similitud."],
            [2, 6],  # Indici delle colonne da espandere (Possessori e Comune)
            7        # L'indice della colonna 'Similitud.' ora è 7
        )
        # --- FINE MODIFICA --- 
        self.results_tabs.addTab(self.partite_table, "📊 Partite")

        content_layout.addWidget(self.results_tabs) # AGGIUNTO AL CONTENT_LAYOUT

        # --- AGGIUNTA DEL CONTENITORE AL LAYOUT PRINCIPALE ---
        # Diamo a tutto il blocco dei contenuti un fattore di stretch > 0
        main_layout.addWidget(content_container_widget, 1)

        # === STATUS BAR (ora separata e sicura) ===
        status_frame = QFrame()
        status_frame.setFrameShape(QFrame.Shape.StyledPanel)
        status_frame.setFrameShadow(QFrame.Shadow.Sunken)
        status_frame.setMaximumHeight(30)
        status_layout = QHBoxLayout(status_frame)
        status_layout.setContentsMargins(5, 2, 5, 2)
        self.stats_label = QLabel("Inserire almeno 3 caratteri per iniziare")
        status_layout.addWidget(self.stats_label)
        status_layout.addStretch()
        self.indices_status_label = QLabel("Verifica indici...")
        status_layout.addWidget(self.indices_status_label)
        
        # Aggiungiamo la status bar al layout principale senza stretch
        main_layout.addWidget(status_frame)

        self.search_edit.setFocus()

    def _create_table_widget(self, headers, stretch_columns, similarity_col_index):
        """Helper per creare una QTableWidget standardizzata."""
        table = QTableWidget()
        table.setColumnCount(len(headers))
        table.setHorizontalHeaderLabels(headers)
        table.setAlternatingRowColors(True)
        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        header = table.horizontalHeader()
        for i in range(len(headers)):
            if i in stretch_columns:
                header.setSectionResizeMode(i, QHeaderView.ResizeMode.Stretch)
            else:
                header.setSectionResizeMode(i, QHeaderView.ResizeMode.ResizeToContents)
        
        # Salva l'indice della colonna di similarità per usi futuri (es. colorazione)
        table.setProperty("similarity_col", similarity_col_index)
        return table

    def _setup_signals(self):
        """Configura i segnali."""
        self.search_edit.textChanged.connect(self._on_search_text_changed)
        self.search_btn.clicked.connect(self._perform_search)
        self.clear_btn.clicked.connect(self._clear_search)
        
        self.precision_slider.valueChanged.connect(lambda v: self.precision_label.setText(f"{v/100:.2f}"))
        self.precision_slider.sliderReleased.connect(self._trigger_search_if_text)

        self.max_results_combo.currentTextChanged.connect(self._trigger_search_if_text)
        # --- MODIFICA QUI: Colleghiamo i nuovi pulsanti ---
        # Rimuoviamo la vecchia riga: self.export_btn.clicked.connect(self._export_results)
        self.btn_export_csv.clicked.connect(self._handle_export_csv)
        self.btn_export_pdf.clicked.connect(self._handle_export_pdf)
        # --- FINE MODIFICA ---

        # Checkbox
        for cb in [self.search_possessori_cb, self.search_localita_cb, self.search_immobili_cb,
                   self.search_variazioni_cb, self.search_contratti_cb, self.search_partite_cb]: # AGGIUNTE NUOVE CHECKBOX
            cb.toggled.connect(self._trigger_search_if_text)

        # Double-click
        
        # --- MODIFICA QUI: Colleghiamo il doppio click per tutte le tabelle ---
        self.unified_table.doubleClicked.connect(self._on_unified_double_click)
        self.possessori_table.doubleClicked.connect(self._on_possessori_double_click)
        self.localita_table.doubleClicked.connect(self._on_localita_double_click)
        self.immobili_table.doubleClicked.connect(self._on_immobili_double_click)
        self.variazioni_table.doubleClicked.connect(self._on_variazioni_double_click)
        self.contratti_table.doubleClicked.connect(self._on_contratti_double_click)
        self.partite_table.doubleClicked.connect(self._on_partite_double_click)
        # --- FINE MODIFICA ---

    def _check_gin_status(self):
        """Verifica lo stato degli indici GIN."""
        if not self.gin_search or not hasattr(self.gin_search, 'verify_gin_indices'):
            self.indices_status_label.setText("❌ Ricerca non disponibile")
            return
        try:
            result = self.gin_search.verify_gin_indices()
            if result.get('status') == 'OK' and result.get('gin_indices', 0) > 0:
                self.indices_status_label.setText(f"✅ Indici GIN attivi ({result['gin_indices']})")
            else:
                self.indices_status_label.setText("⚠️ Indici GIN mancanti o non validi")
        except Exception as e:
            self.indices_status_label.setText("❌ Errore verifica indici")
            self.logger.error(f"Errore verifica indici GIN: {e}")

    def _on_search_text_changed(self, text):
        """Gestisce il cambiamento del testo di ricerca."""
        if len(text) >= 3:
            self.search_timer.start(800) # Delay per evitare ricerche a ogni tasto
            self.stats_label.setText("Pronto per la ricerca...")
        else:
            self.search_timer.stop()
            self._clear_results()
            self.stats_label.setText(f"Inserire almeno {3 - len(text)} caratteri in più")

    def _trigger_search_if_text(self):
        """Rilancia la ricerca se c'è abbastanza testo."""
        if len(self.search_edit.text().strip()) >= 3:
            self._perform_search()

    def _perform_search(self):
        """Esegue la ricerca vera e propria, gestendo il thread precedente."""
        query_text = self.search_edit.text().strip()
        if len(query_text) < 3:
            return

        if not self.gin_search:
            QMessageBox.warning(self, "Errore", "Sistema di ricerca fuzzy non disponibile.")
            return

        # --- MODIFICA CRUCIALE: Gestione del thread esistente ---
        if self.search_thread and self.search_thread.isRunning():
            self.logger.debug("Ricerca precedente ancora in corso. Tentativo di fermarla.")
            self.search_thread.quit()  # Chiede al thread di terminare in modo pulito
            self.search_thread.wait(500) # Attende al massimo 500ms
            if self.search_thread.isRunning():
                self.logger.warning("Il thread precedente non si è fermato in tempo, terminazione forzata.")
                self.search_thread.terminate() # Estrema ratio
                self.search_thread.wait()

        search_options = {
            'threshold': self.precision_slider.value() / 100.0,
            'max_results': int(self.max_results_combo.currentText()),
            'search_possessori': self.search_possessori_cb.isChecked(),
            'search_localita': self.search_localita_cb.isChecked(),
            'search_immobili': self.search_immobili_cb.isChecked(),
            # --- AGGIUNGERE QUESTE OPZIONI ---
            'search_variazioni': self.search_variazioni_cb.isChecked(),
            'search_contratti': self.search_contratti_cb.isChecked(),
            'search_partite': self.search_partite_cb.isChecked(),
        }

        

        self.search_btn.setEnabled(False)
        self.stats_label.setText("Ricerca in corso...")
        
        self.search_thread = UnifiedFuzzySearchThread(self.gin_search, query_text, search_options)
        self.search_thread.results_ready.connect(self._display_results)
        self.search_thread.error_occurred.connect(self._handle_search_error)
        self.search_thread.finished.connect(lambda: self.search_btn.setEnabled(True))
        self.search_thread.start()

    def _display_results(self, results):
        """Visualizza i risultati della ricerca."""
        self.current_results = results
        results_by_type = results.get('results_by_type', {})
        
        self._populate_unified_table(results_by_type)
        self._populate_individual_tables(results_by_type)
        self._update_tab_counters(results_by_type)
        
        total = results.get('total_results', 0)
        self.stats_label.setText(f"Trovati {total} risultati per '{results.get('query_text')}'")
        # --- MODIFICA QUI ---
        self.btn_export_csv.setEnabled(total > 0)
        if FPDF_AVAILABLE:
            self.btn_export_pdf.setEnabled(total > 0)
        # --- FINE MODIFICA ---
    
    def _populate_table(self, table: QTableWidget, data: List[Dict], row_mapper_func):
        """Funzione helper per popolare una QTableWidget."""
        table.setRowCount(0)
        table.setRowCount(len(data))
        similarity_col = table.property("similarity_col")

        for row_idx, item_data in enumerate(data):
            row_content = row_mapper_func(item_data)
            for col_idx, cell_text in enumerate(row_content):
                item = QTableWidgetItem(str(cell_text))
                if col_idx == 0: # Salva i dati completi nel primo item della riga
                    item.setData(Qt.ItemDataRole.UserRole, item_data)
                
                # Applica colorazione alla colonna di similarità
                if similarity_col is not None and col_idx == similarity_col:
                    try:
                        similarity = float(cell_text)
                        if similarity > 0.7: item.setBackground(QColor("#d4edda")) # Verde
                        elif similarity > 0.5: item.setBackground(QColor("#fff3cd")) # Giallo
                        else: item.setBackground(QColor("#f8d7da")) # Rosso
                    except (ValueError, TypeError):
                        pass
                
                table.setItem(row_idx, col_idx, item)

    def _populate_unified_table(self, results_by_type: Dict[str, List]):
        self.unified_table.setRowCount(0)
        row = 0
        type_icons = {
            'possessore': '👥', 'localita': '🏘️', 'immobile': '🏢', 
            'variazione': '📋', 'contratto': '📄', 'partita': '📊'
        }
        for entity_type, entities in results_by_type.items():
            for entity in entities:
                self.unified_table.insertRow(row)
                icon = type_icons.get(entity_type, '📁')
                
                # ["Tipo", "Nome/Descrizione", "Dettagli", "Similarità", "Campo"]
                self.unified_table.setItem(row, 0, QTableWidgetItem(f"{icon} {entity_type.title()}"))
                self.unified_table.item(row,0).setData(Qt.ItemDataRole.UserRole, {'type': entity_type, 'data': entity}) # Salva dati per doppio click
                
                self.unified_table.setItem(row, 1, QTableWidgetItem(entity.get('display_text', '')))
                self.unified_table.setItem(row, 2, QTableWidgetItem(entity.get('detail_text', '')))
                self.unified_table.setItem(row, 3, QTableWidgetItem(f"{entity.get('similarity_score', 0):.3f}"))
                self.unified_table.setItem(row, 4, QTableWidgetItem(entity.get('search_field', '')))
                row += 1

    def _populate_individual_tables(self, results_by_type: Dict[str, List]):
        self._populate_table(self.possessori_table, results_by_type.get('possessore', []), 
            lambda p: [p.get('nome_completo', ''), p.get('comune_nome', ''), p.get('num_partite', 0), f"{p.get('similarity_score', 0):.3f}"])
        
        # --- MODIFICA QUESTA CHIAMATA ---
        self._populate_table(self.localita_table, results_by_type.get('localita', []),
            lambda l: [
                l.get('nome', ''),
                l.get('tipo', '') or '',      # Aggiunto
                l.get('civico', '') or '',    # Aggiunto
                l.get('comune_nome', ''),
                l.get('num_immobili', 0),
                f"{l.get('similarity_score', 0):.3f}"
            ]
        )
        # --- FINE MODIFICA ---
        # --- MODIFICA QUESTA CHIAMATA ---
        self._populate_table(self.immobili_table, results_by_type.get('immobile', []), 
            lambda i: [
                i.get('natura', ''),
                i.get('classificazione', ''),
                i.get('numero_partita', ''),
                i.get('suffisso_partita', '') or '', # Aggiunto il valore per la nuova colonna
                i.get('comune_nome', ''),
                f"{i.get('similarity_score', 0):.3f}"
            ]
        )
        # --- FINE MODIFICA ---

        self._populate_table(self.variazioni_table, results_by_type.get('variazione', []),
            lambda v: [
                v.get('tipo', ''),
                v.get('data_variazione', ''),
                v.get('detail_text', ''), # Usa detail_text per la nuova colonna
                f"{v.get('similarity_score', 0):.3f}"])

        self._populate_table(self.contratti_table, results_by_type.get('contratto', []), 
            lambda c: [c.get('tipo', ''), c.get('data_contratto', ''), c.get('numero_partita', ''), f"{c.get('similarity_score', 0):.3f}"])

        self._populate_table(self.partite_table, results_by_type.get('partita', []), 
            lambda pt: [
                pt.get('numero_partita', ''),
                pt.get('suffisso_partita', '') or '',
                pt.get('possessori_concatenati', '') or '', # NUOVA COLONNA
                pt.get('tipo_partita', ''),
                pt.get('stato', ''),
                str(pt.get('data_impianto', '')) if pt.get('data_impianto') else '',
                pt.get('comune_nome', ''),
                f"{pt.get('similarity_score', 0):.3f}"
            ]
        )
    def _update_tab_counters(self, results_by_type: Dict[str, List]):
        """Aggiorna i contatori nei titoli dei tab."""
        # --- MODIFICA: La logica di base_index non è più necessaria ---
        self.results_tabs.setTabText(0, f"🔍 Tutti ({sum(len(v) for v in results_by_type.values())})")
        self.results_tabs.setTabText(1, f"👥 Possessori ({len(results_by_type.get('possessore', []))})")
        self.results_tabs.setTabText(2, f"🏘️ Località ({len(results_by_type.get('localita', []))})")
        self.results_tabs.setTabText(3, f"🏢 Immobili ({len(results_by_type.get('immobile', []))})")
        # --- AGGIUNGERE QUESTE RIGHE ---
        self.results_tabs.setTabText(4, f"📋 Variazioni ({len(results_by_type.get('variazione', []))})")
        self.results_tabs.setTabText(5, f"📄 Contratti ({len(results_by_type.get('contratto', []))})")
        self.results_tabs.setTabText(6, f"📊 Partite ({len(results_by_type.get('partita', []))})")

    def _clear_results(self):
        """Pulisce tutti i risultati e i contatori."""
        tables = [
            self.unified_table, self.possessori_table, self.localita_table, 
            self.immobili_table, self.variazioni_table, self.contratti_table, 
            self.partite_table
        ]
        for table in tables:
            table.setRowCount(0)
        
        self._update_tab_counters({})
        
        # --- MODIFICA QUI: Disabilita i nuovi pulsanti invece del vecchio ---
        self.btn_export_csv.setEnabled(False)
        self.btn_export_pdf.setEnabled(False)
        # --- FINE MODIFICA ---
        
        self.current_results = {}

    def _handle_search_error(self, error_message):
        """Gestisce gli errori di ricerca."""
        self.search_btn.setEnabled(True)
        self.stats_label.setText("❌ Errore ricerca")
        self.logger.error(f"Errore ricerca fuzzy: {error_message}")
        QMessageBox.critical(self, "Errore Ricerca", f"Si è verificato un errore:\n{error_message}")

    def _clear_search(self):
        """Pulisce il campo di ricerca e i risultati."""
        self.search_edit.clear()
        self._clear_results()
        self.stats_label.setText("Pronto")



    def _on_unified_double_click(self, index):
        """
        Gestisce il doppio click nella tabella unificata, chiamando il gestore appropriato.
        """
        if not index.isValid(): return
            
        item_con_dati = self.unified_table.item(index.row(), 0)
        if not item_con_dati: return

        full_item_data = item_con_dati.data(Qt.ItemDataRole.UserRole)
        if not isinstance(full_item_data, dict): return

        entity_type = full_item_data.get('type')

        # Simula un evento di doppio click sul tab appropriato
        if entity_type == 'partita':
            self._on_partite_double_click(index)
        elif entity_type == 'possessore':
            self._on_possessori_double_click(index)
        elif entity_type == 'localita':
            self._on_localita_double_click(index)
        elif entity_type == 'immobile':
            self._on_immobili_double_click(index)
        elif entity_type == 'variazione':
            self._on_variazioni_double_click(index)
        elif entity_type == 'contratto':
            self._on_contratti_double_click(index)
        else:
            QMessageBox.warning(self, "Tipo Sconosciuto", f"Nessuna azione di dettaglio definita per il tipo '{entity_type}'.")
    def _handle_export_csv(self):
        """Esporta i risultati correnti della ricerca unificata in un file CSV."""
        if not self.current_results or not self.current_results.get('total_results', 0) > 0:
            QMessageBox.warning(self, "Nessun Risultato", "Non ci sono risultati da esportare.")
            return

        query_text = self.current_results.get('query_text', 'ricerca')
        default_filename = f"ricerca_fuzzy_{query_text}_{date.today().isoformat()}.csv"
        filename, _ = QFileDialog.getSaveFileName(self, "Esporta Risultati in CSV", default_filename, "File CSV (*.csv)")

        if not filename:
            return

        try:
            with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
                # Usiamo le intestazioni della tabella "Tutti"
                headers = ['Tipo Entità', 'Nome/Descrizione', 'Dettagli', 'Similarità', 'Campo Trovato']
                writer = csv.writer(csvfile, delimiter=';')
                writer.writerow(headers)
                
                for entity_type, entities in self.current_results.get('results_by_type', {}).items():
                    for entity in entities:
                        writer.writerow([
                            entity_type,
                            entity.get('display_text', ''),
                            entity.get('detail_text', ''),
                            f"{entity.get('similarity_score', 0):.3f}",
                            entity.get('search_field', '')
                        ])
            prompt_to_open_file(self, filename)
        except Exception as e:
            self.logger.error(f"Errore esportazione CSV fuzzy: {e}", exc_info=True)
            QMessageBox.critical(self, "Errore Esportazione", f"Impossibile salvare il file CSV:\n{e}")

    def _handle_export_pdf(self):
        """Esporta i risultati correnti della ricerca unificata in un file PDF."""
        if not self.current_results or not self.current_results.get('total_results', 0) > 0:
            QMessageBox.warning(self, "Nessun Risultato", "Non ci sono risultati da esportare.")
            return
            
        query_text = self.current_results.get('query_text', 'ricerca')
        default_filename = f"ricerca_fuzzy_{query_text}_{date.today().isoformat()}.pdf"
        filename, _ = QFileDialog.getSaveFileName(self, "Esporta Risultati in PDF", default_filename, "File PDF (*.pdf)")

        if not filename:
            return

        try:
            pdf = BulkReportPDF(report_title=f"Risultati Ricerca Fuzzy per '{query_text}'")
            pdf.alias_nb_pages()
            pdf.set_font('Times', '', 12)
            pdf.set_auto_page_break(auto=True, margin=15)
            pdf.add_page()
            
            for entity_type, entities in self.current_results.get('results_by_type', {}).items():
                if not entities: continue
                
                pdf.set_font('Helvetica', 'B', 12)
                pdf.cell(0, 10, f"Risultati per: {entity_type.title()} ({len(entities)})", ln=1)
                
                headers = ['Nome/Descrizione', 'Dettagli', 'Similarità']
                # Adattiamo i dati per la tabella
                data_rows = [
                    (entity.get('display_text', ''), entity.get('detail_text', ''), f"{entity.get('similarity_score', 0):.3f}")
                    for entity in entities
                ]
                # La classe BulkReportPDF gestirà la creazione della tabella
                pdf.print_table(headers, data_rows)
                pdf.ln(5)

            pdf.output(filename)
            prompt_to_open_file(self, filename)
        except Exception as e:
            self.logger.error(f"Errore esportazione PDF fuzzy: {e}", exc_info=True)
            QMessageBox.critical(self, "Errore Esportazione", f"Impossibile generare il file PDF:\n{e}")
   

    def _get_entity_id_from_table(self, table: QTableWidget, index) -> Optional[int]:
        """Helper generico per estrarre l'ID dell'entità da una riga della tabella."""
        if not index.isValid():
            return None

        # I dati completi sono sempre salvati nella UserRole della prima colonna (indice 0)
        item_con_dati = table.item(index.row(), 0)
        if not item_con_dati:
            return None
            
        entity_data_wrapper = item_con_dati.data(Qt.ItemDataRole.UserRole)
        if not isinstance(entity_data_wrapper, dict):
            return None

        # Gestisce sia il tab "Tutti" (dove i dati sono annidati in 'data') 
        # sia i tab specifici (dove i dati sono al primo livello).
        if 'data' in entity_data_wrapper and isinstance(entity_data_wrapper['data'], dict):
            return entity_data_wrapper['data'].get('entity_id')
        elif 'entity_id' in entity_data_wrapper:
            return entity_data_wrapper.get('entity_id')

        return None

    def _on_possessori_double_click(self, index):
        entity_id = self._get_entity_id_from_table(self.possessori_table, index)
        if entity_id:
            dialog = ModificaPossessoreDialog(self.db_manager, entity_id, self)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                self._perform_search() # Aggiorna i risultati se ci sono state modifiche

    def _on_localita_double_click(self, index):
        entity_id = self._get_entity_id_from_table(self.localita_table, index)
        if entity_id:
            localita_details = self.db_manager.get_localita_details(entity_id)
            if localita_details and localita_details.get('comune_id'):
                dialog = ModificaLocalitaDialog(self.db_manager, entity_id, localita_details.get('comune_id'), self)
                if dialog.exec() == QDialog.DialogCode.Accepted:
                    self._perform_search()
            else:
                QMessageBox.warning(self, "Errore Dati", f"Impossibile caricare i dettagli per la località ID {entity_id}.")

    def _on_immobili_double_click(self, index):
        entity_id = self._get_entity_id_from_table(self.immobili_table, index)
        if entity_id:
            immobile_details = self.db_manager.get_immobile_details(entity_id)
            if immobile_details and immobile_details.get('partita_id'):
                partita_details = self.db_manager.get_partita_details(immobile_details.get('partita_id'))
                if partita_details and partita_details.get('comune_id'):
                    dialog = ModificaImmobileDialog(self.db_manager, entity_id, partita_details.get('comune_id'), self)
                    if dialog.exec() == QDialog.DialogCode.Accepted:
                        self._perform_search()
                else:
                    QMessageBox.warning(self, "Errore Dati", f"Impossibile determinare il comune per l'immobile ID {entity_id}.")
            else:
                 QMessageBox.warning(self, "Errore Dati", f"Impossibile caricare i dettagli per l'immobile ID {entity_id}.")

    def _on_partite_double_click(self, index):
        entity_id = self._get_entity_id_from_table(self.partite_table, index)
        if entity_id:
            full_details = self.db_manager.get_partita_details(entity_id)
            if full_details:
                dialog = PartitaDetailsDialog(full_details, self)
                dialog.exec()
            else:
                QMessageBox.warning(self, "Errore Dati", f"Impossibile caricare i dettagli per la partita ID {entity_id}.")

    def _show_generic_details_popup(self, table: QTableWidget, index: 'QModelIndex', entity_type_name: str):
        """Mostra un popup leggibile per entità senza un dialogo di dettaglio dedicato."""
        item_con_dati = table.item(index.row(), 0)
        if not item_con_dati: return
        entity_data = item_con_dati.data(Qt.ItemDataRole.UserRole)
        entity_id = entity_data.get('entity_id', 'N/A')

        testo_formattato = f"<h3>Dettagli - {entity_type_name.title()} ID: {entity_id}</h3>"
        testo_formattato += "<table border='0' cellspacing='5'>"
        for key, value in entity_data.items():
            chiave_formattata = key.replace('_', ' ').title()
            testo_formattato += f"<tr><td><b>{chiave_formattata}:</b></td><td>{value}</td></tr>"
        testo_formattato += "</table>"
        QMessageBox.information(self, f"Dettagli - {entity_type_name.title()}", testo_formattato)

    def _on_variazioni_double_click(self, index):
        self._show_generic_details_popup(self.variazioni_table, index, 'variazione')

    def _on_contratti_double_click(self, index):
        self._show_generic_details_popup(self.contratti_table, index, 'contratto')
# In gui_widgets.py

# In gui_widgets.py, puoi commentare o eliminare la vecchia classe LandingPageWidget
# e aggiungere questa nuova classe.

class DashboardWidget(QWidget):
    # Segnali per navigare ad altri tab (manteniamo la logica)
    go_to_tab_signal = pyqtSignal(str, str) # Segnale emetterà (nome_tab_principale, nome_sotto_tab)
    # --- INIZIO MODIFICA ---
    # Definiamo il nuovo segnale che trasporterà una stringa (il testo della ricerca)
    ricerca_globale_richiesta = pyqtSignal(str)
    # --- FINE MODIFICA ---

    def __init__(self, db_manager: 'CatastoDBManager', current_user_info: Optional[Dict], parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.current_user_info = current_user_info
        
        self.logger = logging.getLogger(f"CatastoGUI.{self.__class__.__name__}")
        self.is_admin = self.current_user_info.get('ruolo') == 'admin' if self.current_user_info else False
        self._initUI()
        self.load_initial_data() # Lazy loading

    def _initUI(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(25)

        # 1. Intestazione
        nome_utente = self.current_user_info.get('nome_completo', 'Utente') if self.current_user_info else 'Utente'
        ruolo_utente = self.current_user_info.get('ruolo', '') if self.current_user_info else ''
        header_label = QLabel(f"<h2>Benvenuto in Foliarium {APP_VERSION}, {nome_utente}</h2>")
        header_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(header_label)
        from datetime import datetime as _dt
        sub_label = QLabel(
            f'<span style="color:#888;font-size:12px;">'
            f'Ruolo: <b>{ruolo_utente}</b> &nbsp;·&nbsp; {_dt.now().strftime("%A %d %B %Y, %H:%M")}'
            f'</span>'
        )
        sub_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(sub_label)

        # 2. Ricerca Globale
        search_group = QGroupBox("Ricerca Rapida")
        search_layout = QHBoxLayout(search_group)
        self.search_edit = QLineEdit(); self.search_edit.setPlaceholderText("Cerca qualsiasi cosa nel catasto...")
        self.search_edit.setMinimumHeight(35)
        self.search_button = QPushButton("Cerca"); self.search_button.clicked.connect(self._avvia_ricerca_globale)
        self.search_edit.returnPressed.connect(self._avvia_ricerca_globale)
        search_layout.addWidget(self.search_edit); search_layout.addWidget(self.search_button)
        main_layout.addWidget(search_group)

        # 3. Statistiche Rapide — StatCard pittate
        stats_layout = QHBoxLayout()
        stats_layout.setSpacing(16)
        self.stat_comuni_card    = StatCard("Comuni",     "#3F51B5")
        self.stat_partite_card   = StatCard("Partite",    "#00897B")
        self.stat_possessori_card = StatCard("Possessori", "#F57C00")
        self.stat_immobili_card  = StatCard("Immobili",   "#C62828")
        for card in (self.stat_comuni_card, self.stat_partite_card,
                     self.stat_possessori_card, self.stat_immobili_card):
            stats_layout.addWidget(card)
        main_layout.addLayout(stats_layout)

        # 4. Ultimi Inserimenti
        recenti_group = QGroupBox("Ultimi Inserimenti")
        recenti_layout = QVBoxLayout(recenti_group)
        self.recenti_tabs = QTabWidget()
        self.recenti_tabs.setMaximumHeight(140)

        self.tab_comuni_recenti = QTableWidget(0, 2)
        self.tab_comuni_recenti.setHorizontalHeaderLabels(["Comune", "Provincia"])
        self.tab_comuni_recenti.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.tab_comuni_recenti.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.tab_comuni_recenti.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tab_comuni_recenti.verticalHeader().setVisible(False)
        self.recenti_tabs.addTab(self.tab_comuni_recenti, "Comuni")

        self.tab_partite_recenti = QTableWidget(0, 2)
        self.tab_partite_recenti.setHorizontalHeaderLabels(["N. Partita", "Comune"])
        self.tab_partite_recenti.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.tab_partite_recenti.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.tab_partite_recenti.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tab_partite_recenti.verticalHeader().setVisible(False)
        self.recenti_tabs.addTab(self.tab_partite_recenti, "Partite")

        self.tab_possessori_recenti = QTableWidget(0, 2)
        self.tab_possessori_recenti.setHorizontalHeaderLabels(["Cognome/Nome", "Nome Completo"])
        self.tab_possessori_recenti.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.tab_possessori_recenti.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tab_possessori_recenti.verticalHeader().setVisible(False)
        self.recenti_tabs.addTab(self.tab_possessori_recenti, "Possessori")

        recenti_layout.addWidget(self.recenti_tabs)
        main_layout.addWidget(recenti_group)

        # 5. Attività Recenti e Azioni Rapide
        bottom_layout = QHBoxLayout()
        
        recent_activity_group = QGroupBox("Attività Utenti Recenti") # Titolo più appropriato
        recent_activity_layout = QVBoxLayout(recent_activity_group)
        self.audit_table = QTableWidget()
        
        # --- INIZIO MODIFICA ---
        # Cambiamo le colonne per mostrare le informazioni della sessione
        self.audit_table.setColumnCount(5)
        self.audit_table.setHorizontalHeaderLabels(["Data/Ora", "Utente", "Azione", "Esito", "Indirizzo IP"])
        # --- FINE MODIFICA ---

        self.audit_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.audit_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.audit_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.audit_table.customContextMenuRequested.connect(self._apri_menu_audit_dashboard)
        recent_activity_layout.addWidget(self.audit_table)
        bottom_layout.addWidget(recent_activity_group, 2)

        actions_group = QGroupBox("Azioni Rapide")
        actions_layout = QVBoxLayout(actions_group)
        btn_new_prop = QPushButton("Registra Nuova Proprietà"); 
        btn_new_prop.clicked.connect(lambda: self.go_to_tab_signal.emit("Inserimento", "Reg. Proprietà"))
        btn_new_partita = QPushButton("Inserisci Nuova Partita"); 
        btn_new_partita.clicked.connect(lambda: self.go_to_tab_signal.emit("Inserimento", "Partita"))
        btn_new_consult = QPushButton("Registra Consultazione")
        btn_new_consult.clicked.connect(lambda: self.go_to_tab_signal.emit("Inserimento", "Reg. Consultazione"))
        btn_reports = QPushButton("Vai alla Reportistica"); 
        btn_reports.clicked.connect(lambda: self.go_to_tab_signal.emit("Report", ""))
        # --- INIZIO MODIFICA: Pulsante visibile solo per admin ---
        if self.is_admin:
            actions_layout.addSpacing(15)

            # Creiamo un pulsante specifico per il backup
            btn_backup = QPushButton(QApplication.style().standardIcon(QStyle.StandardPixmap.SP_DialogSaveButton), " Esegui Backup")
            #btn_backup.setStyleSheet("background-color: #ffeeba; border: 1px solid #ffc107;")

            # Collega il segnale per andare al tab "Sistema" e al sotto-tab "Backup/Ripristino DB"
            btn_backup.clicked.connect(lambda: self.go_to_tab_signal.emit("Sistema", "Backup/Ripristino DB"))

            actions_layout.addWidget(btn_backup)
        # --- FINE MODIFICA ---
        
        actions_layout.addWidget(btn_new_prop); actions_layout.addWidget(btn_new_partita); actions_layout.addWidget(btn_new_consult) ; actions_layout.addWidget(btn_reports)
        actions_layout.addStretch()

        # Mini-card stato backup
        self.backup_status_label = QLabel("Backup: nessun dato")
        self.backup_status_label.setWordWrap(True)
        self.backup_status_label.setStyleSheet(
            "QLabel { background: #F0F4F8; border: 1px solid #D0D8E4; border-radius: 6px; "
            "padding: 6px 10px; font-size: 11px; color: #555; }"
        )
        actions_layout.addWidget(self.backup_status_label)

        bottom_layout.addWidget(actions_group, 1)

        main_layout.addLayout(bottom_layout, 1) # Stretch factor per la parte inferiore
        

    # In gui_widgets.py, nel metodo DashboardWidget.load_initial_data

    def load_initial_data(self):
        """Carica tutti i dati necessari per la dashboard."""
        self.logger.info("Caricamento dati per la Dashboard...")
        # La parte delle statistiche rimane invariata
        stats = self.db_manager.get_dashboard_stats()
        self.stat_comuni_card.setValue(stats.get('total_comuni', 0))
        self.stat_partite_card.setValue(stats.get('total_partite', 0))
        self.stat_possessori_card.setValue(stats.get('total_possessori', 0))
        self.stat_immobili_card.setValue(stats.get('total_immobili', 0))

        # Carica gli ultimi log di sessione
        session_logs = self.db_manager.get_recent_session_logs(limit=5)
        
        self.audit_table.setRowCount(len(session_logs))
        for row, log in enumerate(session_logs):
            # --- INIZIO MODIFICA DEFINITIVA ---
            # Usiamo le chiavi corrette ('data_login' e 'indirizzo_ip') restituite dalla query
            ts = log.get('data_login')
            ts_str = ts.strftime("%d/%m/%y %H:%M") if ts else "N/D"

            user_display = log.get('nome_completo') or log.get('username', 'N/D')
            action_display = log.get('azione', 'N/D').replace('_', ' ').title()
            esito_display = "Successo" if log.get('esito') else "Fallito"

            self.audit_table.setItem(row, 0, QTableWidgetItem(ts_str))
            self.audit_table.setItem(row, 1, QTableWidgetItem(user_display))
            self.audit_table.setItem(row, 2, QTableWidgetItem(action_display))
            self.audit_table.setItem(row, 3, QTableWidgetItem(esito_display))
            self.audit_table.setItem(row, 4, QTableWidgetItem(log.get('indirizzo_ip', 'N/D'))) # <-- Colonna corretta
            # --- FINE MODIFICA DEFINITIVA ---
            
        self.audit_table.resizeColumnsToContents()

        # Ultimi inserimenti
        try:
            ultimi = self.db_manager.get_ultimi_inserimenti_dashboard(limit=3)
            comuni = ultimi.get("comuni", [])
            self.tab_comuni_recenti.setRowCount(len(comuni))
            for i, c in enumerate(comuni):
                self.tab_comuni_recenti.setItem(i, 0, QTableWidgetItem(c.get("nome", "")))
                self.tab_comuni_recenti.setItem(i, 1, QTableWidgetItem(c.get("provincia", "")))
            partite = ultimi.get("partite", [])
            self.tab_partite_recenti.setRowCount(len(partite))
            for i, p in enumerate(partite):
                self.tab_partite_recenti.setItem(i, 0, QTableWidgetItem(str(p.get("numero_partita", ""))))
                self.tab_partite_recenti.setItem(i, 1, QTableWidgetItem(p.get("comune", "")))
            possessori = ultimi.get("possessori", [])
            self.tab_possessori_recenti.setRowCount(len(possessori))
            for i, pos in enumerate(possessori):
                self.tab_possessori_recenti.setItem(i, 0, QTableWidgetItem(pos.get("cognome_nome", "")))
                self.tab_possessori_recenti.setItem(i, 1, QTableWidgetItem(pos.get("nome_completo", "")))
        except Exception as e:
            self.logger.warning(f"Errore caricamento ultimi inserimenti: {e}")

        # Stato backup (legge da QSettings)
        try:
            from PyQt6.QtCore import QSettings
            settings = QSettings()
            last_backup = settings.value("Backup/LastBackupDate", "")
            if last_backup:
                from datetime import datetime as _dt2, timedelta
                try:
                    backup_dt = _dt2.fromisoformat(last_backup)
                    days_ago = (_dt2.now() - backup_dt).days
                    if days_ago == 0:
                        color, testo = "#27AE60", f"Backup: oggi ({backup_dt.strftime('%H:%M')})"
                    elif days_ago <= 7:
                        color, testo = "#E67E22", f"Backup: {days_ago} giorni fa"
                    else:
                        color, testo = "#E74C3C", f"⚠ Backup: {days_ago} giorni fa — consigliato!"
                    self.backup_status_label.setText(testo)
                    self.backup_status_label.setStyleSheet(
                        f"QLabel {{ background: #F0F4F8; border: 1px solid {color}; border-radius: 6px; "
                        f"padding: 6px 10px; font-size: 11px; color: {color}; font-weight: bold; }}"
                    )
                except Exception:
                    pass
        except Exception:
            pass

    def _avvia_ricerca_globale(self):
        """Emette un segnale per passare al tab di ricerca globale e inserire il testo."""
        testo_ricerca = self.search_edit.text().strip()
        if not testo_ricerca:
            return
        self.ricerca_globale_richiesta.emit(testo_ricerca)

    def _apri_menu_audit_dashboard(self, position: QPoint):
        """Context menu sulla tabella attività recenti della dashboard."""
        index = self.audit_table.indexAt(position)
        if not index.isValid():
            return
        row = index.row()
        utente_item = self.audit_table.item(row, 1)
        azione_item = self.audit_table.item(row, 2)
        ip_item = self.audit_table.item(row, 4)
        utente = utente_item.text() if utente_item else ""
        azione = azione_item.text() if azione_item else ""
        ip = ip_item.text() if ip_item else ""

        menu = QMenu(self.audit_table)
        if utente:
            menu.addAction(f"Copia utente  ({utente})").triggered.connect(
                lambda: QApplication.clipboard().setText(utente))
        if azione:
            menu.addAction(f"Copia azione  ({azione})").triggered.connect(
                lambda: QApplication.clipboard().setText(azione))
        if ip:
            menu.addAction(f"Copia IP  ({ip})").triggered.connect(
                lambda: QApplication.clipboard().setText(ip))
        menu.exec(self.audit_table.viewport().mapToGlobal(position))


class WelcomeScreen(QDialog):
    """Splash/EULA screen mostrata all'avvio se la EULA non è ancora stata accettata.
    Layout split: pannello sinistro (branding Indigo) + pannello destro (EULA + accettazione).
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.logger = logging.getLogger(f"CatastoGUI.{self.__class__.__name__}")
        self.setWindowTitle("Benvenuto in Foliarium — Accettazione Licenza")
        self.setModal(True)
        self.setMinimumSize(900, 620)
        self.resize(1060, 680)
        self.setWindowFlags(Qt.WindowType.Dialog)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self._init_ui()

    # ── UI ──────────────────────────────────────────────────────────────────

    def _init_ui(self):
        from app_paths import get_resource_path, get_logo_path
        from config import APP_NAME, APP_SUBTITLE, EULA_VERSION

        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Pannello sinistro (branding) ────────────────────────────────────
        left = QFrame()
        left.setFixedWidth(320)
        left.setStyleSheet("background-color: #3F51B5;")
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(28, 40, 28, 28)
        left_layout.setSpacing(12)

        # Logo
        logo_path = get_logo_path()
        logo_path_str = str(logo_path)
        if os.path.exists(logo_path_str):
            if logo_path_str.lower().endswith('.svg'):
                try:
                    from PyQt6.QtSvgWidgets import QSvgWidget
                    logo_w = QSvgWidget(logo_path_str)
                    logo_w.setFixedSize(100, 100)
                    logo_w.setStyleSheet("background: transparent;")
                    logo_layout = QHBoxLayout()
                    logo_layout.addStretch()
                    logo_layout.addWidget(logo_w)
                    logo_layout.addStretch()
                    left_layout.addLayout(logo_layout)
                except ImportError:
                    pass
            else:
                lbl = QLabel()
                px = QPixmap(logo_path_str)
                lbl.setPixmap(px.scaled(100, 100, Qt.AspectRatioMode.KeepAspectRatio,
                                        Qt.TransformationMode.SmoothTransformation))
                lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
                lbl.setStyleSheet("background: transparent;")
                left_layout.addWidget(lbl)

        left_layout.addSpacing(16)

        app_lbl = QLabel(APP_NAME)
        app_lbl.setFont(QFont("Segoe UI", 26, QFont.Weight.Bold))
        app_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        app_lbl.setStyleSheet("color: #FFFFFF; background: transparent;")
        left_layout.addWidget(app_lbl)

        sub_lbl = QLabel(APP_SUBTITLE)
        sub_lbl.setFont(QFont("Segoe UI", 11))
        sub_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sub_lbl.setWordWrap(True)
        sub_lbl.setStyleSheet("color: #C5CAE9; background: transparent;")
        left_layout.addWidget(sub_lbl)

        left_layout.addStretch(1)

        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setStyleSheet("color: #5C6BC0;")
        left_layout.addWidget(separator)

        algora_lbl = QLabel("Algora Studio")
        algora_lbl.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        algora_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        algora_lbl.setStyleSheet("color: #E8EAF6; background: transparent;")
        left_layout.addWidget(algora_lbl)

        copy_lbl = QLabel(f"© 2025 Algora Studio\nVersione {APP_VERSION}")
        copy_lbl.setFont(QFont("Segoe UI", 9))
        copy_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        copy_lbl.setStyleSheet("color: #9FA8DA; background: transparent;")
        left_layout.addWidget(copy_lbl)

        root.addWidget(left)

        # ── Pannello destro (EULA) ──────────────────────────────────────────
        right = QFrame()
        right.setStyleSheet("background-color: #FFFFFF;")
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(32, 32, 32, 24)
        right_layout.setSpacing(14)

        title_lbl = QLabel("Contratto di Licenza")
        title_lbl.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        title_lbl.setStyleSheet("color: #3F51B5;")
        right_layout.addWidget(title_lbl)

        info_lbl = QLabel(
            "Leggi attentamente il contratto di licenza prima di utilizzare Foliarium.\n"
            "Devi accettare i termini per continuare."
        )
        info_lbl.setFont(QFont("Segoe UI", 9))
        info_lbl.setStyleSheet("color: #757575;")
        info_lbl.setWordWrap(True)
        right_layout.addWidget(info_lbl)

        # Testo EULA
        self.eula_browser = QTextBrowser()
        self.eula_browser.setReadOnly(True)
        self.eula_browser.setFont(QFont("Consolas", 9))
        self.eula_browser.setStyleSheet(
            "border: 1px solid #C5CAE9; border-radius: 6px; "
            "background: #F8F9FA; padding: 8px; color: #212121;"
        )
        eula_path = get_resource_path("EULA.txt")
        try:
            with open(str(eula_path), "r", encoding="utf-8") as f:
                self.eula_browser.setPlainText(f.read())
        except Exception:
            self.eula_browser.setPlainText(
                "Impossibile caricare il testo della licenza.\n"
                "Contatta Algora Studio per una copia del contratto."
            )
        right_layout.addWidget(self.eula_browser, 1)

        # Checkbox accettazione
        self.accept_cb = QCheckBox(
            "Ho letto e accetto i termini del Contratto di Licenza con l'Utente Finale (EULA)"
        )
        self.accept_cb.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        self.accept_cb.setStyleSheet("color: #212121;")
        self.accept_cb.toggled.connect(self._on_accept_toggled)
        right_layout.addWidget(self.accept_cb)

        # Pulsanti
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        self.help_btn = QPushButton("Manuale Utente")
        self.help_btn.setObjectName("secondaryButton")
        self.help_btn.setMinimumHeight(36)
        self.help_btn.setToolTip("Apri il manuale utente integrato")
        self.help_btn.clicked.connect(self._open_help)
        btn_row.addWidget(self.help_btn)

        btn_row.addStretch()

        self.cancel_btn = QPushButton("Annulla")
        self.cancel_btn.setObjectName("secondaryButton")
        self.cancel_btn.setMinimumHeight(36)
        self.cancel_btn.setMinimumWidth(90)
        self.cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(self.cancel_btn)

        self.continue_btn = QPushButton("Continua →")
        self.continue_btn.setMinimumHeight(36)
        self.continue_btn.setMinimumWidth(110)
        self.continue_btn.setEnabled(False)
        self.continue_btn.setStyleSheet(
            "QPushButton { background-color: #3F51B5; color: #FFFFFF; border: none;"
            " border-radius: 4px; padding: 6px 16px; font-weight: bold; }"
            "QPushButton:hover { background-color: #5C6BC0; }"
            "QPushButton:disabled { background-color: #C5CAE9; color: #9FA8DA; }"
        )
        self.continue_btn.clicked.connect(self._on_continue)
        btn_row.addWidget(self.continue_btn)

        right_layout.addLayout(btn_row)
        root.addWidget(right, 1)

    # ── Handlers ────────────────────────────────────────────────────────────

    def _on_accept_toggled(self, checked: bool):
        self.continue_btn.setEnabled(checked)

    def _on_continue(self):
        if self.accept_cb.isChecked():
            self.logger.info("EULA accettata dall'utente.")
            self.accept()

    def _open_help(self):
        """Apre il manuale utente integrato (HelpViewerDialog se disponibile)."""
        try:
            from dialogs import HelpViewerDialog
            dlg = HelpViewerDialog(self)
            dlg.exec()
        except Exception as e:
            self.logger.warning(f"Impossibile aprire HelpViewerDialog: {e}")
            QMessageBox.information(
                self, "Manuale",
                "Il manuale utente integrato non è disponibile in questo momento.\n"
                "Consulta la documentazione fornita con il software."
            )