
import os,csv,sys,logging,json
from datetime import date, datetime
from typing import Optional, List, Dict, Any, Tuple, TYPE_CHECKING
from app_utils import BulkReportPDF, FPDF_AVAILABLE, _get_default_export_path, prompt_to_open_file
from app_paths import get_icon_path
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
                             QVBoxLayout, QWidget,QProgressDialog,QTextBrowser,QSlider, QCompleter,QSplitter,QStackedWidget)

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
        _hdr = self.comuni_table.horizontalHeader()
        _hdr.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        _hdr.setStretchLastSection(True)
        self.comuni_table.setColumnWidth(0, 45)   # ID
        self.comuni_table.setColumnWidth(1, 200)  # Nome Comune
        self.comuni_table.setColumnWidth(2, 110)  # Cod. Catastale
        self.comuni_table.setColumnWidth(3, 80)   # Provincia
        self.comuni_table.setColumnWidth(4, 120)  # Data Istituzione
        self.comuni_table.setColumnWidth(5, 120)  # Data Soppressione
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

        self.btn_archivia_comune = QPushButton("Archivia Comune")
        self.btn_archivia_comune.setObjectName("dangerButton")
        self.btn_archivia_comune.setEnabled(False)
        self.btn_archivia_comune.setToolTip("Archivia il comune selezionato (non viene eliminato, solo nascosto)")
        self.btn_archivia_comune.clicked.connect(self._azione_archivia_comune)
        action_buttons_layout.addWidget(self.btn_archivia_comune)
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

        action_modifica_comune = menu.addAction("Modifica Dati Comune")
        action_modifica_comune.triggered.connect(
            lambda: self._slot_modifica_dati_comune(comune_id_selezionato)
        )

        menu.addSeparator()

        action_archivia = menu.addAction(
            QApplication.style().standardIcon(QStyle.StandardPixmap.SP_TrashIcon),
            f"Archivia '{nome_comune_selezionato}'"
        )
        action_archivia.triggered.connect(
            lambda: self._slot_archivia_comune(comune_id_selezionato, nome_comune_selezionato)
        )

        menu.exec(self.comuni_table.viewport().mapToGlobal(position))

    def _slot_archivia_comune(self, comune_id: int, nome: str):
        from PyQt6.QtWidgets import QMessageBox
        risposta = QMessageBox.question(
            self, "Archivia Comune",
            f"Archiviare il comune '{nome}'?\n\n"
            "Il comune non verrà eliminato ma nascosto dalle liste.\n"
            "Le partite e i possessori collegati resteranno visibili.\n"
            "Puoi ripristinarlo in qualsiasi momento dal pannello Archivio.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if risposta != QMessageBox.StandardButton.Yes:
            return
        try:
            self.db_manager.archivia_comune(comune_id)
            self.load_data()
            from app_utils import show_status_message
        except Exception as e:
            QMessageBox.critical(self, "Errore", f"Impossibile archiviare il comune:\n{e}")

   
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
        self.btn_archivia_comune.setEnabled(has_selection)

    def _azione_archivia_comune(self):
        """Archivia il comune selezionato tramite pulsante."""
        row = self.comuni_table.currentRow()
        if row < 0:
            return
        comune_id = int(self.comuni_table.item(row, 0).text())
        nome = self.comuni_table.item(row, 1).text() if self.comuni_table.item(row, 1) else "?"
        self._slot_archivia_comune(comune_id, nome)



class _PartiteSearchWorker(QThread):
    """Esegue search_partite in background per non bloccare la UI."""
    results_ready = pyqtSignal(list)
    error_occurred = pyqtSignal(str)

    def __init__(self, db_manager, comune_id, numero, possessore, natura, parent=None):
        super().__init__(parent)
        self._db = db_manager
        self._comune_id = comune_id
        self._numero = numero
        self._possessore = possessore
        self._natura = natura

    def run(self):
        try:
            partite = self._db.search_partite(
                comune_id=self._comune_id,
                numero_partita=self._numero,
                possessore=self._possessore,
                immobile_natura=self._natura,
            )
            self.results_ready.emit(partite or [])
        except Exception as e:
            self.error_occurred.emit(str(e))


class PartitaResultCard(QFrame):
    """Card cliccabile per un risultato di ricerca partite."""
    card_clicked = pyqtSignal(int)
    context_menu_requested = pyqtSignal(int, QPoint)

    _STATO_STYLE: dict[str, tuple[str, str]] = {
        "attiva":   ("#E8F5E9", "#1B5E20"),
        "inattiva": ("#F5F5F5", "#616161"),
        "aperta":   ("#E3F2FD", "#0D47A1"),
        "chiusa":   ("#FFF3E0", "#BF360C"),
    }

    def __init__(self, partita_data: dict, parent=None):
        super().__init__(parent)
        self._partita_id: int = partita_data.get('id', -1)
        self._partita_data = partita_data
        self.setObjectName("resultCard")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setFrameShadow(QFrame.Shadow.Raised)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(
            lambda pos: self.context_menu_requested.emit(
                self._partita_id, self.mapToGlobal(pos)))

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(3)

        # Top row: numero partita + chip stato
        row1 = QHBoxLayout()
        row1.setSpacing(8)

        numero = partita_data.get('numero_partita', '—')
        suffisso = (partita_data.get('suffisso_partita') or '').strip()
        suf_display = f"/{suffisso}" if suffisso else ""
        numero_lbl = QLabel(f"<b>N. {numero}{suf_display}</b>")
        numero_lbl.setObjectName("cardTitle")
        row1.addWidget(numero_lbl)
        row1.addStretch()

        stato = (partita_data.get('stato') or '').strip()
        bg, fg = self._STATO_STYLE.get(stato.lower(), ("#F5F5F5", "#424242"))
        stato_lbl = QLabel(stato or "—")
        stato_lbl.setStyleSheet(
            f"background:{bg}; color:{fg}; border-radius:9px; "
            f"padding:1px 9px; font-size:9pt; font-weight:600;"
        )
        row1.addWidget(stato_lbl)
        layout.addLayout(row1)

        # Comune
        comune = partita_data.get('comune_nome', '')
        if comune:
            comune_lbl = QLabel(comune)
            comune_lbl.setObjectName("cardSubtitle")
            layout.addWidget(comune_lbl)

        # Tipo
        tipo = partita_data.get('tipo', '')
        if tipo:
            tipo_lbl = QLabel(tipo)
            tipo_lbl.setObjectName("cardMeta")
            layout.addWidget(tipo_lbl)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.card_clicked.emit(self._partita_id)
        super().mousePressEvent(event)

    def set_selected(self, selected: bool):
        self.setProperty("selected", "true" if selected else "false")
        self.style().unpolish(self)
        self.style().polish(self)


class RicercaPartiteWidget(QWidget):
    def __init__(self, db_manager, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self._selected_partita_id: Optional[int] = None
        self._all_partite: list[dict] = []
        self._comune_id: Optional[int] = None
        self._search_worker: Optional[_PartiteSearchWorker] = None

        main_layout = QVBoxLayout(self)

        group = QGroupBox("Ricerca Partite")
        group_layout = QVBoxLayout(group)

        # ─────────────────────────────────────────────────────────
        # Barra ricerca: Comune, N°, Possessore, Natura, Cerca, Pulisci
        # ─────────────────────────────────────────────────────────
        search_layout = QHBoxLayout()
        search_layout.setContentsMargins(0, 0, 0, 0)
        search_layout.setSpacing(6)

        self._comune_btn = QPushButton("Comune...")
        self._comune_btn.setObjectName("secondaryButton")
        self._comune_btn.setMaximumWidth(110)
        self._comune_btn.clicked.connect(self._select_comune)
        search_layout.addWidget(self._comune_btn)

        self._numero_edit = QSpinBox()
        self._numero_edit.setMinimum(0)
        self._numero_edit.setMaximum(99999)
        self._numero_edit.setSpecialValueText("N°...")
        self._numero_edit.setMaximumWidth(80)
        search_layout.addWidget(self._numero_edit)

        self._possessore_edit = QLineEdit()
        self._possessore_edit.setPlaceholderText("Possessore...")
        self._possessore_edit.returnPressed.connect(self.do_search)
        search_layout.addWidget(self._possessore_edit, 1)

        self._natura_edit = QLineEdit()
        self._natura_edit.setPlaceholderText("Natura immobile...")
        self._natura_edit.returnPressed.connect(self.do_search)
        search_layout.addWidget(self._natura_edit, 1)

        self._search_btn = QPushButton("Cerca")
        self._search_btn.clicked.connect(self.do_search)
        search_layout.addWidget(self._search_btn)

        clear_btn = QPushButton("Pulisci")
        clear_btn.setObjectName("secondaryButton")
        clear_btn.clicked.connect(self._clear_search)
        search_layout.addWidget(clear_btn)

        group_layout.addLayout(search_layout)

        # Loading progress bar (hidden by default)
        self._loading_bar = QProgressBar()
        self._loading_bar.setRange(0, 0)
        self._loading_bar.setFixedHeight(3)
        self._loading_bar.setVisible(False)
        self._loading_bar.setTextVisible(False)
        group_layout.addWidget(self._loading_bar)

        # ─────────────────────────────────────────────────────────
        # Filtri stato + conteggio risultati
        # ─────────────────────────────────────────────────────────
        filter_layout = QHBoxLayout()
        filter_layout.setContentsMargins(0, 0, 0, 0)
        filter_layout.setSpacing(6)

        filter_layout.addWidget(QLabel("Stato:"))
        self._stato_combo = QComboBox()
        self._stato_combo.addItems(["Tutte", "Attiva", "Inattiva", "Aperta", "Chiusa"])
        self._stato_combo.currentTextChanged.connect(self._on_stato_combo_changed)
        filter_layout.addWidget(self._stato_combo)

        filter_layout.addStretch()

        self._count_label = QLabel("Nessuna ricerca eseguita.")
        self._count_label.setStyleSheet("color:#757575; font-style:italic; font-size:9pt;")
        filter_layout.addWidget(self._count_label)

        group_layout.addLayout(filter_layout)

        # ─────────────────────────────────────────────────────────
        # Tabella risultati (full-width)
        # ─────────────────────────────────────────────────────────
        self._table = QTableWidget()
        self._table.setColumnCount(5)
        self._table.setHorizontalHeaderLabels(["N° Partita", "Comune", "Stato", "Tipo", "Data Impianto"])
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._table.setAlternatingRowColors(True)
        self._table.setSortingEnabled(True)
        self._table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._table.verticalHeader().setVisible(False)
        hh = self._table.horizontalHeader()
        hh.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        hh.setStretchLastSection(True)
        self._table.setColumnWidth(0, 90)
        self._table.setColumnWidth(1, 160)
        self._table.setColumnWidth(2, 80)
        self._table.setColumnWidth(3, 100)
        self._table.cellClicked.connect(lambda row, col: self._on_row_selected(row))
        self._table.doubleClicked.connect(lambda: self.show_details())
        self._table.customContextMenuRequested.connect(self._on_context_menu)
        group_layout.addWidget(self._table, 1)

        # ─────────────────────────────────────────────────────────
        # Bottoni azione (come ElencoComuniWidget)
        # ─────────────────────────────────────────────────────────
        action_layout = QHBoxLayout()
        action_layout.setContentsMargins(0, 0, 0, 0)
        action_layout.setSpacing(8)

        self._btn_open_full = QPushButton("Apri Dettagli Completi")
        self._btn_open_full.setEnabled(False)
        self._btn_open_full.clicked.connect(self.show_details)
        action_layout.addWidget(self._btn_open_full)

        self._btn_albero = QPushButton("Albero Genealogico")
        self._btn_albero.setObjectName("secondaryButton")
        self._btn_albero.setEnabled(False)
        self._btn_albero.clicked.connect(self._apri_albero)
        action_layout.addWidget(self._btn_albero)

        action_layout.addStretch()

        self._btn_copy_id = QPushButton("Copia ID")
        self._btn_copy_id.setObjectName("secondaryButton")
        self._btn_copy_id.setEnabled(False)
        self._btn_copy_id.clicked.connect(lambda: QApplication.clipboard().setText(
            str(self._selected_partita_id or "")))
        action_layout.addWidget(self._btn_copy_id)

        self._btn_archivia = QPushButton("Archivia Partita")
        self._btn_archivia.setObjectName("dangerButton")
        self._btn_archivia.setEnabled(False)
        self._btn_archivia.setToolTip("Archivia la partita selezionata (non viene eliminata, solo nascosta)")
        self._btn_archivia.clicked.connect(self._azione_archivia_partita)
        action_layout.addWidget(self._btn_archivia)

        group_layout.addLayout(action_layout)

        main_layout.addWidget(group)


    def _select_comune(self):
        dialog = ComuneSelectionDialog(self.db_manager, self)
        if dialog.exec() == QDialog.DialogCode.Accepted and dialog.selected_comune_id:
            self._comune_id = dialog.selected_comune_id
            self._comune_btn.setText(dialog.selected_comune_name or "Comune...")

    def _clear_search(self):
        if self._search_worker and self._search_worker.isRunning():
            self._search_worker.quit()
            self._search_worker.wait(500)
        self._loading_bar.setVisible(False)
        self._search_btn.setEnabled(True)
        self._comune_id = None
        self._comune_btn.setText("Comune...")
        self._numero_edit.setValue(0)
        self._possessore_edit.clear()
        self._natura_edit.clear()
        self._stato_combo.setCurrentText("Tutte")
        self._table.setSortingEnabled(False)
        self._table.setRowCount(0)
        self._table.setSortingEnabled(True)
        self._all_partite.clear()
        self._selected_partita_id = None
        self._count_label.setText("Nessuna ricerca eseguita.")
        for btn in (self._btn_open_full, self._btn_albero, self._btn_copy_id, self._btn_archivia):
            btn.setEnabled(False)

    def _on_stato_combo_changed(self, text: str):
        """Quando il combo filtro stato cambia, aggiorna la visibilità righe."""
        self._update_row_visibility()

    def _update_row_visibility(self):
        """Filtra la tabella in base al valore del combo stato."""
        stato_filtro = self._stato_combo.currentText()
        if stato_filtro == "Tutte":
            stato_filtro = ""

        visible = 0
        for row in range(self._table.rowCount()):
            stato_item = self._table.item(row, 2)
            partita_stato = (stato_item.text() if stato_item else "").strip()
            show = (not stato_filtro or
                    partita_stato.lower() == stato_filtro.lower())
            self._table.setRowHidden(row, not show)
            if show:
                visible += 1

        total = len(self._all_partite)
        if stato_filtro:
            self._count_label.setText(f"{visible} di {total} partite mostrate.")
        else:
            self._count_label.setText(f"{total} partite trovate.")

    def do_search(self):
        # Cancel any running search
        if self._search_worker and self._search_worker.isRunning():
            self._search_worker.quit()
            self._search_worker.wait(500)

        numero_val = self._numero_edit.value()
        numero = numero_val if numero_val > 0 else None
        possessore = self._possessore_edit.text().strip() or None
        natura = self._natura_edit.text().strip() or None

        self._search_btn.setEnabled(False)
        self._loading_bar.setVisible(True)
        self._count_label.setText("Ricerca in corso…")

        self._search_worker = _PartiteSearchWorker(
            self.db_manager, self._comune_id, numero, possessore, natura, self
        )
        self._search_worker.results_ready.connect(self._on_search_results)
        self._search_worker.error_occurred.connect(self._on_search_error)
        self._search_worker.start()

    def _on_search_results(self, partite: list):
        self._loading_bar.setVisible(False)
        self._search_btn.setEnabled(True)

        self._all_partite = partite
        truncated = bool(self._all_partite and self._all_partite[-1].get('_truncated'))

        self._table.setSortingEnabled(False)
        self._table.setRowCount(0)
        for p in self._all_partite:
            row = self._table.rowCount()
            self._table.insertRow(row)
            suf = (p.get('suffisso_partita') or '').strip()
            num_text = f"{p.get('numero_partita')}{f'/{suf}' if suf else ''}"
            data_imp = str(p.get('data_impianto') or '—')
            for col, val in enumerate([
                num_text,
                p.get('comune_nome', ''),
                p.get('stato', ''),
                p.get('tipo', ''),
                data_imp,
            ]):
                item = QTableWidgetItem(str(val))
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                if col == 0:
                    item.setData(Qt.ItemDataRole.UserRole, p.get('id'))
                self._table.setItem(row, col, item)
        self._table.setSortingEnabled(True)

        self._selected_partita_id = None
        for btn in (self._btn_open_full, self._btn_albero, self._btn_copy_id, self._btn_archivia):
            btn.setEnabled(False)

        self._update_row_visibility()

        if truncated:
            self._count_label.setText(
                f"Visualizzate le prime {len(self._all_partite)} partite. "
                f"Affina la ricerca per risultati più precisi.")

    def _on_search_error(self, error_msg: str):
        self._loading_bar.setVisible(False)
        self._search_btn.setEnabled(True)
        self._count_label.setText("Errore durante la ricerca.")
        logging.getLogger("CatastoGUI").error(f"Errore ricerca partite: {error_msg}")
        QMessageBox.critical(self, "Errore di Ricerca",
                             f"Si è verificato un errore durante la ricerca:\n\n{error_msg}"
                             "\n\nSe l'errore riguarda la colonna 'archiviato', eseguire "
                             "la migrazione del database: sql_scripts/07_soft_delete_archiviazione.sql")

    def _on_row_selected(self, current_row: int):
        if current_row < 0:
            self._selected_partita_id = None
            for btn in (self._btn_open_full, self._btn_albero, self._btn_copy_id, self._btn_archivia):
                btn.setEnabled(False)
            return

        id_item = self._table.item(current_row, 0)
        if id_item is None:
            return
        partita_id = id_item.data(Qt.ItemDataRole.UserRole)
        if not partita_id:
            return

        self._selected_partita_id = partita_id
        for btn in (self._btn_open_full, self._btn_albero, self._btn_copy_id, self._btn_archivia):
            btn.setEnabled(True)

    def show_details(self):
        if not self._selected_partita_id:
            QMessageBox.warning(self, "Attenzione", "Seleziona una partita dalla lista.")
            return
        try:
            partita = self.db_manager.get_partita_details(self._selected_partita_id)
            if partita:
                from dialogs_partita import PartitaDetailsDialog
                dlg = PartitaDetailsDialog(partita, self)
                dlg.exec()
        except Exception as e:
            QMessageBox.critical(self, "Errore", f"Impossibile caricare i dettagli: {e}")

    def _apri_albero(self):
        if not self._selected_partita_id:
            return
        try:
            from dialogs_partita import AlberoGeneralogicoDialog
            dlg = AlberoGeneralogicoDialog(self.db_manager, self._selected_partita_id, self)
            dlg.exec()
        except Exception as e:
            QMessageBox.critical(self, "Errore", str(e))

    def _on_context_menu(self, pos: QPoint):
        row = self._table.rowAt(pos.y())
        if row < 0:
            return
        id_item = self._table.item(row, 0)
        if id_item is None:
            return
        partita_id = id_item.data(Qt.ItemDataRole.UserRole)
        numero_text = id_item.text()

        self._table.selectRow(row)

        menu = QMenu(self)
        menu.addAction(
            QApplication.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogContentsView),
            "Apri Dettagli Completi"
        ).triggered.connect(self.show_details)
        menu.addSeparator()
        menu.addAction(f"Copia Numero Partita ({numero_text})").triggered.connect(
            lambda: QApplication.clipboard().setText(numero_text))
        menu.addAction(f"Copia ID ({partita_id})").triggered.connect(
            lambda: QApplication.clipboard().setText(str(partita_id)))
        menu.addSeparator()
        menu.addAction(
            QApplication.style().standardIcon(QStyle.StandardPixmap.SP_TrashIcon),
            f"Archivia Partita N. {numero_text}"
        ).triggered.connect(lambda: self._archivia_partita(partita_id, numero_text))
        menu.exec(self._table.viewport().mapToGlobal(pos))

    def _archivia_partita(self, partita_id: int, numero_text: str):
        risposta = QMessageBox.question(
            self, "Archivia Partita",
            f"Archiviare la partita N. {numero_text}?\n\n"
            "La partita non verrà eliminata ma nascosta dalle ricerche.\n"
            "Puoi ripristinarla in qualsiasi momento dal pannello Archivio.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if risposta != QMessageBox.StandardButton.Yes:
            return
        try:
            self.db_manager.archivia_partita(partita_id)
            self.do_search()
        except Exception as e:
            QMessageBox.critical(self, "Errore", f"Impossibile archiviare la partita:\n{e}")

    def _azione_archivia_partita(self):
        """Archivia la partita selezionata tramite pulsante."""
        if not self._selected_partita_id:
            return
        row = self._table.currentRow()
        numero_text = self._table.item(row, 0).text() if row >= 0 and self._table.item(row, 0) else str(self._selected_partita_id)
        self._archivia_partita(self._selected_partita_id, numero_text)


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
            QHeaderView.ResizeMode.Interactive)
        self.risultati_immobili_table.horizontalHeader().setStretchLastSection(True)
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

# Estratto in insertion_widgets.py — backward compat re-export
from insertion_widgets import (
    InserimentoComuneWidget, InserimentoPossessoreWidget,
    InserimentoLocalitaWidget, InserimentoPartitaWidget,
)
from admin_widgets import GestioneTipiLocalitaWidget, GestionePeriodiStoriciWidget


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

            QMessageBox.information(self, "Successo", f"Partita N.{numero} registrata (ID: {partita_id}).")
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
        self.main_tabs.addTab(stats_container_widget, QIcon(str(get_icon_path("bar-chart"))), "Statistiche")
        self.main_tabs.addTab(maintenance_tab, QIcon(str(get_icon_path("settings"))), "Manutenzione Database")
        
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
        self.stats_comune_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.stats_comune_table.horizontalHeader().setStretchLastSection(True)
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
        self.immobili_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.immobili_table.horizontalHeader().setStretchLastSection(True)
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

from admin_widgets import GestioneUtentiWidget, AuditLogViewerWidget, BackupWidget, ArchivioWidget

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
        _lbl_search = QLabel()
        _lbl_search.setPixmap(QIcon(str(get_icon_path("search"))).pixmap(QSize(16, 16)))
        search_row.addWidget(_lbl_search)
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Cerca in possessori, località, immobili, variazioni, contratti, partite...")
        search_row.addWidget(self.search_edit, 1)
        self.search_btn = QPushButton("Cerca")
        search_row.addWidget(self.search_btn)
        self.clear_btn = QPushButton()
        self.clear_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_LineEditClearButton))
        self.clear_btn.setToolTip("Pulisci ricerca")
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
        self.search_possessori_cb = QCheckBox("Possessori"); self.search_possessori_cb.setIcon(QIcon(str(get_icon_path("users")))); self.search_possessori_cb.setChecked(True); types_group_layout.addWidget(self.search_possessori_cb)
        self.search_localita_cb = QCheckBox("Località"); self.search_localita_cb.setIcon(QIcon(str(get_icon_path("map-pin")))); self.search_localita_cb.setChecked(True); types_group_layout.addWidget(self.search_localita_cb)
        self.search_immobili_cb = QCheckBox("Immobili"); self.search_immobili_cb.setIcon(QIcon(str(get_icon_path("building")))); self.search_immobili_cb.setChecked(True); types_group_layout.addWidget(self.search_immobili_cb)
        self.search_variazioni_cb = QCheckBox("Variazioni"); self.search_variazioni_cb.setIcon(QIcon(str(get_icon_path("report")))); self.search_variazioni_cb.setChecked(True); types_group_layout.addWidget(self.search_variazioni_cb)
        self.search_contratti_cb = QCheckBox("Contratti"); self.search_contratti_cb.setIcon(QIcon(str(get_icon_path("file-text")))); self.search_contratti_cb.setChecked(True); types_group_layout.addWidget(self.search_contratti_cb)
        self.search_partite_cb = QCheckBox("Partite"); self.search_partite_cb.setIcon(QIcon(str(get_icon_path("bar-chart")))); self.search_partite_cb.setChecked(True); types_group_layout.addWidget(self.search_partite_cb)
        types_layout.addWidget(types_group)

        content_layout.addLayout(types_layout) # AGGIUNTO AL CONTENT_LAYOUT

        # === AREA RISULTATI (da aggiungere al content_layout) ===
        self.results_tabs = QTabWidget()
        self.results_tabs.setMinimumHeight(400)
        # ... (tutta la creazione delle tabelle e l'aggiunta a results_tabs rimane identica) ...
        self.unified_table = self._create_table_widget(["Tipo", "Nome/Descrizione", "Dettagli", "Similarità", "Campo"], [1, 2], 3); self.results_tabs.addTab(self.unified_table, QIcon(str(get_icon_path("search"))), "Tutti")
        self.possessori_table = self._create_table_widget(["Nome Completo", "Comune", "Partite", "Similitud."], [0], 3); self.results_tabs.addTab(self.possessori_table, QIcon(str(get_icon_path("users"))), "Possessori")
        self.localita_table = self._create_table_widget(["Nome", "Tipo", "Civico", "Comune", "Immobili", "Similitud."], [0, 3], 5); self.results_tabs.addTab(self.localita_table, QIcon(str(get_icon_path("map-pin"))), "Località")
        self.immobili_table = self._create_table_widget(["Natura", "Classificazione", "Partita", "Suffisso", "Comune", "Similitud."], [1, 4], 5); self.results_tabs.addTab(self.immobili_table, QIcon(str(get_icon_path("building"))), "Immobili")
        self.variazioni_table = self._create_table_widget(["Tipo", "Data", "Rif. e Partita Origine", "Similitud."], [2], 3)
        self.results_tabs.addTab(self.variazioni_table, QIcon(str(get_icon_path("report"))), "Variazioni")
        self.contratti_table = self._create_table_widget(["Tipo", "Data", "Partita", "Similitud."], [0], 3); self.results_tabs.addTab(self.contratti_table, QIcon(str(get_icon_path("file-text"))), "Contratti")
        # --- MODIFICA QUESTA RIGA ---
        self.partite_table = self._create_table_widget(
            ["Numero", "Suffisso", "Possessori", "Tipo", "Stato", "Data Impianto", "Comune", "Similitud."],
            [2, 6],  # Indici delle colonne da espandere (Possessori e Comune)
            7        # L'indice della colonna 'Similitud.' ora è 7
        )
        # --- FINE MODIFICA --- 
        self.results_tabs.addTab(self.partite_table, QIcon(str(get_icon_path("bar-chart"))), "Partite")

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
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        header.setStretchLastSection(True)
        
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
            self.indices_status_label.setText("Ricerca non disponibile")
            return
        try:
            result = self.gin_search.verify_gin_indices()
            if result.get('status') == 'OK' and result.get('gin_indices', 0) > 0:
                self.indices_status_label.setText(f"Indici GIN attivi ({result['gin_indices']})")
            else:
                self.indices_status_label.setText("Indici GIN mancanti o non validi")
        except Exception as e:
            self.indices_status_label.setText("Errore verifica indici")
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
        _type_icon_names = {
            'possessore': 'users', 'localita': 'map-pin', 'immobile': 'building',
            'variazione': 'report', 'contratto': 'file-text', 'partita': 'bar-chart'
        }
        _type_labels = {
            'possessore': 'Possessore', 'localita': 'Località', 'immobile': 'Immobile',
            'variazione': 'Variazione', 'contratto': 'Contratto', 'partita': 'Partita'
        }
        for entity_type, entities in results_by_type.items():
            for entity in entities:
                self.unified_table.insertRow(row)
                _icon_name = _type_icon_names.get(entity_type, 'file-text')
                _tipo_item = QTableWidgetItem(_type_labels.get(entity_type, entity_type.title()))
                _tipo_item.setIcon(QIcon(str(get_icon_path(_icon_name))))

                # ["Tipo", "Nome/Descrizione", "Dettagli", "Similarità", "Campo"]
                self.unified_table.setItem(row, 0, _tipo_item)
                self.unified_table.item(row, 0).setData(Qt.ItemDataRole.UserRole, {'type': entity_type, 'data': entity}) # Salva dati per doppio click
                
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
        self.results_tabs.setTabText(0, f"Tutti ({sum(len(v) for v in results_by_type.values())})")
        self.results_tabs.setTabText(1, f"Possessori ({len(results_by_type.get('possessore', []))})")
        self.results_tabs.setTabText(2, f"Località ({len(results_by_type.get('localita', []))})")
        self.results_tabs.setTabText(3, f"Immobili ({len(results_by_type.get('immobile', []))})")
        self.results_tabs.setTabText(4, f"Variazioni ({len(results_by_type.get('variazione', []))})")
        self.results_tabs.setTabText(5, f"Contratti ({len(results_by_type.get('contratto', []))})")
        self.results_tabs.setTabText(6, f"Partite ({len(results_by_type.get('partita', []))})")

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
        self.stats_label.setText("Errore ricerca")
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
        self.tab_possessori_recenti.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.tab_possessori_recenti.horizontalHeader().setStretchLastSection(True)
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
        self.audit_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.audit_table.horizontalHeader().setStretchLastSection(True)
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
                        color, testo = "#E74C3C", f"Backup: {days_ago} giorni fa — consigliato!"
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