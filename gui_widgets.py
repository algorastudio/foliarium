
import os,csv,sys,logging,json
from datetime import date, datetime
from typing import Optional, List, Dict, Any, Tuple, TYPE_CHECKING
from app_utils import BulkReportPDF, FPDF_AVAILABLE, _get_default_export_path, prompt_to_open_file
from app_paths import get_icon_path
import pandas as pd # Importa pandas

# Importazioni PyQt6
from PyQt6.QtCore import (QDate, QDateTime, QPoint, QProcess, QSize, QStandardPaths, QTimer, QUrl, 
                          QModelIndex,QProcessEnvironment,Qt, QSettings, 
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
from foliarium.ui.widgets.custom import LazyLoadedWidget

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
from foliarium.ui.widgets.custom import QPasswordLineEdit, StatCard
from dialogs import (DBConfigDialog,DocumentViewerDialog, PeriodoStoricoDetailsDialog)
from dialogs import (ComuneSelectionDialog, PartitaSearchDialog, PossessoreSelectionDialog, ImmobileDialog,DettagliLegamePossessoreDialog, UserSelectionDialog,qdate_to_datetime, datetime_to_qdate,_hash_password,_verify_password)

from app_utils import (gui_esporta_partita_pdf, gui_esporta_partita_json, gui_esporta_partita_csv,
                       gui_esporta_possessore_pdf, gui_esporta_possessore_json, gui_esporta_possessore_csv,
                       GenericTextReportPDF,is_file_locked,get_alternative_filename)
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


from foliarium.ui.widgets.custom import show_status_message as _show_status_message


# ---------------------------------------------------------------------------

class _ComuniLoaderWorker(QThread):
    """Carica l'elenco comuni dal DB in background per non bloccare la UI."""
    results_ready = pyqtSignal(list)
    error_occurred = pyqtSignal(str)

    def __init__(self, db_manager, parent=None):
        super().__init__(parent)
        self._db = db_manager

    def run(self):
        try:
            result = self._db.get_all_comuni_details()
            self.results_ready.emit(result or [])
        except Exception as e:
            self.error_occurred.emit(str(e))


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
        # Collega il segnale di cambio selezione a una funzione che abilita/disabilita i pulsanti
        self.comuni_table.itemSelectionChanged.connect(self._update_action_buttons_state)

        comuni_layout.addWidget(self.comuni_table)

        action_buttons_layout = QHBoxLayout()
        
        self.btn_modifica_comune = QPushButton("Modifica Comune Selezionato")
        self.btn_modifica_comune.clicked.connect(self.azione_modifica_comune)
        self.btn_modifica_comune.setEnabled(False) # Inizia disabilitato
        action_buttons_layout.addWidget(self.btn_modifica_comune)
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
        """Avvia il caricamento dell'elenco comuni in background (non blocca la UI)."""
        if not self.db_manager:
            self.logger.error("load_data chiamato ma self.db_manager è None!")
            return
        if hasattr(self, '_loader') and self._loader.isRunning():
            return  # caricamento già in corso

        self.comuni_table.setSortingEnabled(False)
        self.comuni_table.setRowCount(1)
        loading_item = QTableWidgetItem("Caricamento in corso…")
        loading_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self.comuni_table.setItem(0, 0, loading_item)
        self.comuni_table.setSpan(0, 0, 1, self.comuni_table.columnCount())

        self._loader = _ComuniLoaderWorker(self.db_manager, self)
        self._loader.results_ready.connect(self._on_comuni_loaded)
        self._loader.error_occurred.connect(self._on_comuni_error)
        self._loader.start()
        self.logger.debug("_ComuniLoaderWorker avviato.")

    def _on_comuni_loaded(self, comuni_list: list):
        self.comuni_table.setSortingEnabled(False)
        self.comuni_table.clearSpans()
        self.comuni_table.setRowCount(0)
        if not comuni_list:
            self.logger.warning("Nessun comune restituito dal DB.")
            self.comuni_table.setRowCount(1)
            item = QTableWidgetItem("Nessun comune trovato nel database.")
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.comuni_table.setItem(0, 0, item)
            self.comuni_table.setSpan(0, 0, 1, self.comuni_table.columnCount())
        else:
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
        self.comuni_table.setSortingEnabled(True)
        self.logger.debug("Tabella comuni popolata con %d righe.", len(comuni_list))

    def _on_comuni_error(self, error_msg: str):
        self.comuni_table.setSortingEnabled(True)
        self.comuni_table.clearSpans()
        self.comuni_table.setRowCount(0)
        self.logger.error("Errore caricamento comuni: %s", error_msg)
        QMessageBox.critical(self, "Errore Caricamento Dati",
                             f"Impossibile caricare l'elenco dei comuni:\n{error_msg}")

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
            _show_status_message(f"Comune '{nome}' archiviato con successo.", 4000)
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


# Estratto in search_widgets.py — backward compat re-export
from search_widgets import (
    _PartiteSearchWorker, PartitaResultCard,
    RicercaPartiteWidget, RicercaAvanzataImmobiliWidget,
    UnifiedFuzzySearchThread, UnifiedFuzzySearchWidget,
)

# Estratto in insertion_widgets.py — backward compat re-export
from foliarium.ui.widgets.insertion import (
    InserimentoComuneWidget, InserimentoPossessoreWidget,
    InserimentoLocalitaWidget, InserimentoPartitaWidget,
)
from foliarium.ui.widgets.admin import GestioneTipiLocalitaWidget, GestionePeriodiStoriciWidget


# Estratto in partita_workflow_widgets.py — backward compat re-export
from partita_workflow_widgets import (
    RegistrazioneProprietaWidget,
    NuovaPartitaWizardWidget,
    OperazioniPartitaWidget,
)

# Estratto in admin_widgets.py — backward compat re-export
# Estratto in reporting_widgets.py — backward compat re-export
from foliarium.ui.widgets.reporting import (
    RicercaDocumentiWidget, EsportazioniWidget, ReportisticaWidget,
    StatisticheWidget, RegistraConsultazioneWidget,
)

from foliarium.ui.widgets.admin import GestioneUtentiWidget, AuditLogViewerWidget, BackupWidget, ArchivioWidget, TipiPossessoWidget

class _DashboardLoaderWorker(QThread):
    """Esegue le tre query della dashboard in background per non bloccare la UI."""
    stats_ready = pyqtSignal(dict)
    sessions_ready = pyqtSignal(list)
    ultimi_ready = pyqtSignal(dict)
    error_occurred = pyqtSignal(str)

    def __init__(self, db_manager, parent=None):
        super().__init__(parent)
        self._db = db_manager

    def run(self):
        try:
            self.stats_ready.emit(self._db.get_dashboard_stats() or {})
            self.sessions_ready.emit(self._db.get_recent_session_logs(limit=5) or [])
            self.ultimi_ready.emit(self._db.get_ultimi_inserimenti_dashboard(limit=3) or {})
        except Exception as e:
            self.error_occurred.emit(str(e))


class DashboardWidget(QWidget):
    # Segnali per navigare ad altri tab (manteniamo la logica)
    go_to_tab_signal = pyqtSignal(str, str) # Segnale emetterà (nome_tab_principale, nome_sotto_tab)
    # Definiamo il nuovo segnale che trasporterà una stringa (il testo della ricerca)
    ricerca_globale_richiesta = pyqtSignal(str)

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
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(18)

        # 1. Intestazione — titolo + sottotitolo con ruolo/data
        nome_utente = self.current_user_info.get('nome_completo', 'Utente') if self.current_user_info else 'Utente'
        ruolo_utente = self.current_user_info.get('ruolo', '') if self.current_user_info else ''
        from datetime import datetime as _dt
        # Usa locale italiano se possibile, fallback su date semplice
        try:
            import locale
            try:
                locale.setlocale(locale.LC_TIME, "it_IT.UTF-8")
            except locale.Error:
                pass
            data_str = _dt.now().strftime("%A %d %B %Y, %H:%M")
        except Exception:
            data_str = _dt.now().strftime("%d/%m/%Y, %H:%M")

        header_label = QLabel(f"Benvenuto, {nome_utente}")
        header_label.setObjectName("pageTitle")
        main_layout.addWidget(header_label)

        sub_label = QLabel(f"Ruolo: <b>{ruolo_utente}</b>  ·  {data_str}  ·  v{APP_VERSION}")
        sub_label.setObjectName("pageSubtitle")
        sub_label.setTextFormat(Qt.TextFormat.RichText)
        main_layout.addWidget(sub_label)

        # 2. Ricerca Globale
        search_group = QGroupBox("Ricerca Rapida")
        search_layout = QHBoxLayout(search_group)
        search_layout.setSpacing(10)
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Cerca qualsiasi cosa nel catasto — comune, possessore, partita, immobile…")
        self.search_edit.setMinimumHeight(36)
        self.search_button = QPushButton("Cerca")
        self.search_button.setMinimumWidth(110)
        self.search_button.clicked.connect(self._avvia_ricerca_globale)
        self.search_edit.returnPressed.connect(self._avvia_ricerca_globale)
        search_layout.addWidget(self.search_edit, 1)
        search_layout.addWidget(self.search_button)
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
        
        # Cambiamo le colonne per mostrare le informazioni della sessione
        self.audit_table.setColumnCount(5)
        self.audit_table.setHorizontalHeaderLabels(["Data/Ora", "Utente", "Azione", "Esito", "Indirizzo IP"])

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
        if self.is_admin:
            actions_layout.addSpacing(15)

            # Creiamo un pulsante specifico per il backup
            btn_backup = QPushButton(QApplication.style().standardIcon(QStyle.StandardPixmap.SP_DialogSaveButton), " Esegui Backup")
            #btn_backup.setStyleSheet("background-color: #ffeeba; border: 1px solid #ffc107;")

            # Collega il segnale per andare al tab "Sistema" e al sotto-tab "Backup/Ripristino DB"
            btn_backup.clicked.connect(lambda: self.go_to_tab_signal.emit("Sistema", "Backup/Ripristino DB"))

            actions_layout.addWidget(btn_backup)
        
        actions_layout.addWidget(btn_new_prop); actions_layout.addWidget(btn_new_partita); actions_layout.addWidget(btn_new_consult) ; actions_layout.addWidget(btn_reports)
        actions_layout.addStretch()

        # Mini-card stato backup — stilizzata via #backupStatusCard nel QSS
        self.backup_status_label = QLabel("Backup: nessun dato")
        self.backup_status_label.setObjectName("backupStatusCard")
        self.backup_status_label.setWordWrap(True)
        actions_layout.addWidget(self.backup_status_label)

        bottom_layout.addWidget(actions_group, 1)

        main_layout.addLayout(bottom_layout, 1) # Stretch factor per la parte inferiore
        

    # In gui_widgets.py, nel metodo DashboardWidget.load_initial_data

    def load_initial_data(self):
        """Avvia il caricamento dei dati dashboard in background (non blocca la UI)."""
        self.logger.info("Avvio caricamento asincrono dati Dashboard...")
        if hasattr(self, '_dash_loader') and self._dash_loader.isRunning():
            return

        self._dash_loader = _DashboardLoaderWorker(self.db_manager, self)
        self._dash_loader.stats_ready.connect(self._on_stats_ready)
        self._dash_loader.sessions_ready.connect(self._on_sessions_ready)
        self._dash_loader.ultimi_ready.connect(self._on_ultimi_ready)
        self._dash_loader.error_occurred.connect(
            lambda msg: self.logger.warning("Errore caricamento dashboard: %s", msg)
        )
        self._dash_loader.start()

    def _on_stats_ready(self, stats: dict):
        self.stat_comuni_card.setValue(stats.get('total_comuni', 0))
        self.stat_partite_card.setValue(stats.get('total_partite', 0))
        self.stat_possessori_card.setValue(stats.get('total_possessori', 0))
        self.stat_immobili_card.setValue(stats.get('total_immobili', 0))

    def _on_sessions_ready(self, session_logs: list):
        self.audit_table.setRowCount(len(session_logs))
        for row, log in enumerate(session_logs):
            ts = log.get('data_login')
            ts_str = ts.strftime("%d/%m/%y %H:%M") if ts else "N/D"
            user_display = log.get('nome_completo') or log.get('username', 'N/D')
            action_display = log.get('azione', 'N/D').replace('_', ' ').title()
            esito_display = "Successo" if log.get('esito') else "Fallito"
            self.audit_table.setItem(row, 0, QTableWidgetItem(ts_str))
            self.audit_table.setItem(row, 1, QTableWidgetItem(user_display))
            self.audit_table.setItem(row, 2, QTableWidgetItem(action_display))
            self.audit_table.setItem(row, 3, QTableWidgetItem(esito_display))
            self.audit_table.setItem(row, 4, QTableWidgetItem(log.get('indirizzo_ip', 'N/D')))
        self.audit_table.resizeColumnsToContents()

    def _on_ultimi_ready(self, ultimi: dict):
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
                        status, testo = "ok", f"Backup: oggi ({backup_dt.strftime('%H:%M')})"
                    elif days_ago <= 7:
                        status, testo = "warn", f"Backup: {days_ago} giorni fa"
                    else:
                        status, testo = "alert", f"Backup: {days_ago} giorni fa — consigliato!"
                    self.backup_status_label.setText(testo)
                    self.backup_status_label.setProperty("status", status)
                    self.backup_status_label.style().unpolish(self.backup_status_label)
                    self.backup_status_label.style().polish(self.backup_status_label)
                except Exception as _e:
                    logger.debug("Impossibile aggiornare stato backup dalla data '%s': %s", last_backup, _e)
        except Exception as _e:
            logger.debug("Impossibile leggere stato backup da QSettings: %s", _e)

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
        left.setObjectName("welcomeBranding")
        left.setFixedWidth(320)
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
                left_layout.addWidget(lbl)

        left_layout.addSpacing(16)

        app_lbl = QLabel(APP_NAME)
        app_lbl.setObjectName("welcomeAppTitle")
        app_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        left_layout.addWidget(app_lbl)

        sub_lbl = QLabel(APP_SUBTITLE)
        sub_lbl.setObjectName("welcomeAppSubtitle")
        sub_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sub_lbl.setWordWrap(True)
        left_layout.addWidget(sub_lbl)

        left_layout.addStretch(1)

        separator = QFrame()
        separator.setObjectName("welcomeSeparator")
        separator.setFrameShape(QFrame.Shape.HLine)
        left_layout.addWidget(separator)

        algora_lbl = QLabel("Algora Studio")
        algora_lbl.setObjectName("welcomeStudio")
        algora_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        left_layout.addWidget(algora_lbl)

        copy_lbl = QLabel(f"© 2025 Algora Studio\nVersione {APP_VERSION}")
        copy_lbl.setObjectName("welcomeCopyright")
        copy_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        left_layout.addWidget(copy_lbl)

        root.addWidget(left)

        # ── Pannello destro (EULA) ──────────────────────────────────────────
        right = QFrame()
        right.setObjectName("welcomeBody")
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(32, 32, 32, 24)
        right_layout.setSpacing(14)

        title_lbl = QLabel("Contratto di Licenza")
        title_lbl.setObjectName("welcomeTitle")
        right_layout.addWidget(title_lbl)

        info_lbl = QLabel(
            "Leggi attentamente il contratto di licenza prima di utilizzare Foliarium.\n"
            "Devi accettare i termini per continuare."
        )
        info_lbl.setObjectName("welcomeInfo")
        info_lbl.setWordWrap(True)
        right_layout.addWidget(info_lbl)

        # Testo EULA
        self.eula_browser = QTextBrowser()
        self.eula_browser.setObjectName("eulaBrowser")
        self.eula_browser.setReadOnly(True)
        self.eula_browser.setFont(QFont("Consolas", 9))
        eula_path = get_resource_path("EULA.txt")
        try:
            with open(str(eula_path), "r", encoding="utf-8") as f:
                self.eula_browser.setPlainText(f.read())
        except Exception as _e:
            logger.warning("Impossibile caricare EULA da '%s': %s", eula_path, _e)
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
        self.continue_btn.setDefault(True)
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
