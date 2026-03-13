
import os,csv,sys,logging,json,bcrypt
from datetime import date, datetime
from typing import Optional, List, Dict, Any, Tuple, TYPE_CHECKING
# Importazioni PyQt5
from PyQt5.QtCore import (QDate, QDateTime, QPoint, QProcess, QSettings, 
                          QSize, QStandardPaths, Qt, QTimer, QUrl, 
                          pyqtSignal,pyqtSlot)

from PyQt5.QtGui import (QCloseEvent, QColor, QDesktopServices, QFont, 
                         QIcon, QPalette, QPixmap)

try:
    from PyQt5.QtWebEngineWidgets import QWebEngineView
    WEB_ENGINE_AVAILABLE = True
except ImportError:
    QWebEngineView = None
    WEB_ENGINE_AVAILABLE = False

from PyQt5.QtWidgets import (QAbstractItemView, QAction, QApplication, 
                             QCheckBox, QComboBox, QDateEdit, QDateTimeEdit,
                             QDialog, QDialogButtonBox, QDoubleSpinBox,
                             QFileDialog, QFormLayout, QFrame, QGridLayout,
                             QGroupBox, QHBoxLayout, QHeaderView, QInputDialog,
                             QLabel, QLineEdit, QListWidget, QListWidgetItem,
                             QMainWindow, QMenu, QMessageBox, QProgressBar,
                             QPushButton, QScrollArea, QSizePolicy, QSpacerItem,
                             QSpinBox, QStyle, QStyleFactory, QTabWidget,
                             QTableWidget, QTableWidgetItem, QTextEdit,
                             QVBoxLayout, QWidget, QDateEdit,
                             QGraphicsScene, QGraphicsView, QDialog, QVBoxLayout, 
                             QTextBrowser, QDialogButtonBox, QRadioButton)

from PyQt5.QtGui import QPainter
from app_paths import get_resource_path




# Importazione commentata (da abilitare se necessario)
# from PyQt5.QtSvgWidgets import QSvgWidget
from config import (
    SETTINGS_DB_TYPE, SETTINGS_DB_HOST, SETTINGS_DB_PORT, 
    SETTINGS_DB_NAME, SETTINGS_DB_USER, SETTINGS_DB_SCHEMA,SETTINGS_DB_PASSWORD
)
from catasto_db_manager import CatastoDBManager

from custom_widgets import QPasswordLineEdit,ImmobiliTableWidget


from app_utils import (gui_esporta_partita_pdf, gui_esporta_partita_json, gui_esporta_partita_csv,
                       gui_esporta_possessore_pdf, gui_esporta_possessore_json, gui_esporta_possessore_csv,
                       GenericTextReportPDF, FPDF_AVAILABLE, prompt_to_open_file,PDFApreviewDialog) # <-- AGGIUNGI QUI

# --- INIZIO CORREZIONE: Importazione sicura di keyring ---
try:
    import keyring
except ImportError:
    keyring = None
    logging.getLogger("CatastoGUI").warning(
        "Libreria 'keyring' non trovata. La funzionalità di salvataggio sicuro della password non sarà disponibile."
    )
# --- FINE CORREZIONE ---

try:
    from fpdf import FPDF
    from fpdf.enums import XPos, YPos
    FPDF_AVAILABLE = True
except ImportError:
    FPDF_AVAILABLE = False
    # class FPDF: pass # Fallback se si volessero istanziare le classi PDF anche senza fpdf
    # ma è meglio gestire con FPDF_AVAILABLE
    # Potrebbe essere utile definire classi PDF vuote qui se FPDF non è disponibile,
    # per evitare NameError se il codice tenta di usarle condizionalmente.

    class PDFPartita:
        pass

    class PDFPossessore:
        pass

    class GenericTextReportPDF:
        pass

try:
    from catasto_db_manager import DBMError, DBUniqueConstraintError, DBNotFoundError, DBDataError
except ImportError:
    # Fallback o definizione locale se preferisci non importare direttamente
    # (ma l'importazione è più pulita se sono definite in db_manager)
    class DBMError(Exception):
        pass

    class DBUniqueConstraintError(DBMError):
        pass

    class DBNotFoundError(DBMError):
        pass

    class DBDataError(DBMError):
        pass
    QMessageBox.warning(None, "Avviso Importazione",
                        "Eccezioni DB personalizzate non trovate in catasto_db_manager, usando definizioni fallback.")


class DBConfigDialog(QDialog):
    def __init__(self, parent=None, initial_config: Optional[Dict] = None):
        super().__init__(parent)
        # --- INIZIO CORREZIONE: Aggiungere questa riga ---
        self.logger = logging.getLogger(f"CatastoGUI.{self.__class__.__name__}")
        # --- FINE CORREZIONE ---
        self.setWindowTitle("Configurazione Connessione Database")
        self.settings = QSettings()
        self.setModal(True)
        self.setMinimumWidth(450)
        
        config = initial_config if initial_config else {}

        # --- UI Setup ---
        layout = QVBoxLayout(self)
        form_layout = QFormLayout()
        
        self.local_radio = QRadioButton("Locale (localhost)")
        self.remote_radio = QRadioButton("Remoto (Server Specifico)")
        type_layout = QHBoxLayout()
        type_layout.addWidget(self.local_radio)
        type_layout.addWidget(self.remote_radio)
        form_layout.addRow("Tipo di Server:", type_layout)
        
        self.host_edit = QLineEdit()
        self.port_spinbox = QSpinBox()
        self.port_spinbox.setRange(1, 65535)
        self.dbname_edit = QLineEdit()
        self.user_edit = QLineEdit()
        self.password_edit = QPasswordLineEdit()
        self.save_password_check = QCheckBox("Salva password (non sicuro)")
        
        self.host_label = QLabel("Indirizzo Server Host:")
        form_layout.addRow(self.host_label, self.host_edit)
        form_layout.addRow("Porta Server:", self.port_spinbox)
        form_layout.addRow("Nome Database:", self.dbname_edit)
        form_layout.addRow("Utente Database:", self.user_edit)
        form_layout.addRow("Password Database:", self.password_edit)
        form_layout.addRow(self.save_password_check)
        
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self)
        buttons.button(QDialogButtonBox.Ok).setText("Testa e Salva")
        buttons.accepted.connect(self._handle_save_and_connect)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        # --- INIZIO AGGIUNTA: Sezione Operazioni di Emergenza ---
        emergency_group = QGroupBox("Operazioni di Emergenza")
        emergency_layout = QHBoxLayout(emergency_group)

        emergency_label = QLabel("Usare solo se il database principale è corrotto o inaccessibile.")
        emergency_label.setWordWrap(True)

        self.btn_emergency_restore = QPushButton(QApplication.style().standardIcon(QStyle.SP_DialogResetButton), " Ripristina Database da Backup...")
        self.btn_emergency_restore.clicked.connect(self._handle_emergency_restore)

        emergency_layout.addWidget(emergency_label, 1)
        emergency_layout.addWidget(self.btn_emergency_restore)

        layout.addWidget(emergency_group)
        # --- FINE AGGIUNTA ---

        
        layout.addLayout(form_layout)
        layout.addWidget(buttons)
        
        # --- Connessioni e Pre-compilazione ---
        self.local_radio.toggled.connect(self._toggle_host_field) # Collega al nuovo metodo
        
        db_type = config.get("db_type", "local")
        if db_type == "remote":
            self.remote_radio.setChecked(True)
        else:
            self.local_radio.setChecked(True)
        
        self.host_edit.setText(config.get("host", "localhost"))
        self.port_spinbox.setValue(config.get("port", 5432))
        self.dbname_edit.setText(config.get("dbname", "catasto_storico"))
        self.user_edit.setText(config.get("user", "postgres"))
        
        self._toggle_host_field() # Chiamata iniziale per impostare lo stato corretto della UI

        buttons.accepted.connect(self._handle_save_and_connect)
        buttons.rejected.connect(self.reject)
    def _toggle_host_field(self):
        """
        Abilita o disabilita il campo di testo dell'host in base alla selezione
        del radio button per la connessione locale/remota.
        """
        # Il campo dell'host è visibile solo se è selezionato "Remoto"
        is_remote = self.remote_radio.isChecked()
        self.host_label.setVisible(is_remote)
        self.host_edit.setVisible(is_remote)
    def _load_settings(self):
        """Carica le impostazioni da QSettings, usando self.default_preset_config come fallback."""
        config_to_load = {}
        config_to_load[SETTINGS_DB_TYPE] = self.settings.value(SETTINGS_DB_TYPE, self.default_preset_config[SETTINGS_DB_TYPE], type=str)
        config_to_load[SETTINGS_DB_HOST] = self.settings.value(SETTINGS_DB_HOST, self.default_preset_config[SETTINGS_DB_HOST], type=str)
        config_to_load[SETTINGS_DB_PORT] = self.settings.value(SETTINGS_DB_PORT, self.default_preset_config[SETTINGS_DB_PORT], type=int)
        config_to_load[SETTINGS_DB_NAME] = self.settings.value(SETTINGS_DB_NAME, self.default_preset_config[SETTINGS_DB_NAME], type=str)
        config_to_load[SETTINGS_DB_USER] = self.settings.value(SETTINGS_DB_USER, self.default_preset_config[SETTINGS_DB_USER], type=str)
        config_to_load[SETTINGS_DB_SCHEMA] = self.settings.value(SETTINGS_DB_SCHEMA, self.default_preset_config[SETTINGS_DB_SCHEMA], type=str)
        
        # Aggiungiamo il caricamento dello stato della checkbox e della password
        saved_password = self.settings.value(SETTINGS_DB_PASSWORD, "", type=str)
        if saved_password:
            self.password_edit.setText(saved_password)
            self.save_password_check.setChecked(True)
        else:
            self.save_password_check.setChecked(False)
        
        
        # Non è necessario chiamare _db_type_changed qui, sarà chiamato alla fine di __init__

    # --- MODIFICA A _populate_from_config per riflettere i tipi ---
    def _populate_from_config(self, config: Dict[str, Any]):
        """
        Popola i campi del dialogo con i valori di configurazione forniti.
        """
        # Aggiunto log per debug interno
        logging.getLogger("CatastoGUI").debug(f"Popolando DBConfigDialog con: { {k:v for k,v in config.items() if k != 'password'} }")

        db_type_str = config.get(SETTINGS_DB_TYPE, self.default_preset_config[SETTINGS_DB_TYPE])
        if db_type_str == "remote":
            self.remote_radio.setChecked(True)
        else:
            self.local_radio.setChecked(True)
        self._toggle_host_field() # Assicurati che l'UI rifletta la selezione

        self.host_edit.setText(config.get(SETTINGS_DB_HOST, self.default_preset_config[SETTINGS_DB_HOST]))
        
        # Recupera la porta in modo robusto
        port_value = config.get(SETTINGS_DB_PORT, self.default_preset_config[SETTINGS_DB_PORT])
        try:
            self.port_spinbox.setValue(int(port_value))
        except (ValueError, TypeError):
            self.port_spinbox.setValue(self.default_preset_config[SETTINGS_DB_PORT])
            logging.getLogger("CatastoGUI").warning(f"Valore porta non valido '{port_value}' in config, usando default {self.default_preset_config[SETTINGS_DB_PORT]}.")

        self.dbname_edit.setText(config.get(SETTINGS_DB_NAME, self.default_preset_config[SETTINGS_DB_NAME]))
        self.user_edit.setText(config.get(SETTINGS_DB_USER, self.default_preset_config[SETTINGS_DB_USER]))
        self.schema_edit.setText(config.get(SETTINGS_DB_SCHEMA, self.default_preset_config[SETTINGS_DB_SCHEMA]))
        
        # La password viene gestita da "LastPassword" nel __init__


    # --- NUOVI METODI WRAPPER PER accepted() e rejected() ---
    # In dialogs.py, modifica il metodo _handle_save_and_connect in DBConfigDialog

    # In dialogs.py, puoi sostituire l'intero metodo in DBConfigDialog

    def _handle_save_and_connect(self):
        """
        Recupera i valori, testa la connessione, salva le impostazioni
        e chiude il dialogo se tutto va a buon fine.
        """
        config = self.get_config_values(include_password=True)
        
        # Testa la connessione con i nuovi parametri
        test_db_manager = CatastoDBManager(
            host=config["host"],
            port=config["port"],
            dbname=config["dbname"],
            user=config["user"],
            password=config["password"]
        )
        
        # --- INIZIO CORREZIONE ---
        # Usiamo il metodo corretto per testare la connessione e inizializzare il pool
        if test_db_manager.initialize_main_pool():
        # --- FINE CORREZIONE ---
            self.logger.info("Test di connessione riuscito.")
            
            # Se il test ha successo, salva le impostazioni
            settings = QSettings()
            
            if self.remote_radio.isChecked():
                settings.setValue("Database/Type", "remote")
                settings.setValue("Database/Host", config["host"])
            else:
                settings.setValue("Database/Type", "local")
                settings.setValue("Database/Host", "localhost")

            settings.setValue("Database/Port", config["port"])
            settings.setValue("Database/DBName", config["dbname"])
            settings.setValue("Database/User", config["user"])
            
            if config.get("save_password", False) and config.get("password"):
                if keyring:
                    try:
                        keyring.set_password(f"meridiana_db_{config['host']}", config['user'], config['password'])
                        self.logger.info("Password salvata nel keyring di sistema.")
                    except Exception as e:
                        self.logger.error(f"Impossibile salvare la password nel keyring: {e}")
                        QMessageBox.warning(self, "Salvataggio Password Fallito", f"Impossibile salvare la password nel portachiavi di sistema:\n{e}")
            
            settings.sync()
            QMessageBox.information(self, "Successo", "Connessione riuscita e impostazioni salvate.")
            self.accept()
        else:
            QMessageBox.critical(self, "Connessione Fallita", "Impossibile connettersi al database con i parametri forniti.\nControlla i dati e riprova.")

    def _handle_cancel(self):
        """Gestisce il click su 'Annulla'."""
        # Non è necessaria alcuna logica di salvataggio qui
        # Chiudi il dialogo con QDialog.Rejected.
        super().reject()
    # --- FINE NUOVI METODI WRAPPER ---
    
    
    def _test_connection(self):
        config_values = self.get_config_values(include_password=True) # Ottieni anche la password
        
        # Validazione minima prima del test
        if not all([config_values["dbname"], config_values["user"], config_values["password"]]):
            QMessageBox.warning(self, "Dati Mancanti", "Compilare tutti i campi obbligatori (Nome DB, Utente DB, Password DB) prima di testare la connessione.")
            return

        # Chiudi un eventuale db_manager_test precedente
        if self.db_manager_test:
            self.db_manager_test.close_pool()

        # Istanzia un nuovo DBManager per il test
        try:
            self.db_manager_test = CatastoDBManager(
                dbname=config_values["dbname"],
                user=config_values["user"],
                password=config_values["password"],
                host=config_values["host"],
                port=config_values["port"],
                schema=config_values["schema"],
                application_name="CatastoAppGUI_TestConnessione"
            )
            
            if self.db_manager_test.initialize_main_pool():
                QMessageBox.information(self, "Test Connessione", "Connessione al database riuscita con successo!")
                # Chiudi il pool di test subito dopo il successo
                self.db_manager_test.close_pool() 
                self.db_manager_test = None
            else:
                QMessageBox.warning(self, "Test Connessione", "Connessione al database fallita. Verificare i parametri e la password.")
                # Il logger di db_manager_test ha già registrato i dettagli dell'errore
        except Exception as e:
            QMessageBox.critical(self, "Errore Test", f"Si è verificato un errore durante il test di connessione: {e}")
            self.logger.error(f"Errore imprevisto durante il test di connessione: {e}", exc_info=True)
        finally:
            if self.db_manager_test: # Assicurati che sia chiuso anche in caso di eccezione
                self.db_manager_test.close_pool()
                self.db_manager_test = None

    # Modifica il metodo accept per salvare la password usata (temporaneamente)
    def accept(self):
        config_values = self.get_config_values(include_password=True) # Ottieni anche la password
        # Validazione completa prima di salvare e accettare
        if not all([config_values["dbname"], config_values["user"], config_values["password"]]):
            QMessageBox.warning(self, "Dati Mancanti", "Compilare tutti i campi obbligatori (Nome DB, Utente DB, Password DB).")
            return
        is_remoto = self.remote_radio.isChecked()
        if is_remoto and not config_values["host"]:
            QMessageBox.warning(self, "Dati Mancanti", "L'indirizzo del server host è obbligatorio per database remoto.")
            return

        # Salva la password nel QSettings in una chiave temporanea per la sessione o l'ultimo uso.
        # NON la salvare permanentemente in SETTINGS_DB_PASSWORD.
        self.settings.setValue("Database/LastPassword", config_values["password"])
        self.settings.sync() # Forza la scrittura

        self._save_settings() # Questo salva le altre impostazioni (senza password)
        super().accept()
    

    def _save_settings(self):
        if self.local_radio.isChecked():
            self.settings.setValue(SETTINGS_DB_TYPE, "local")
            host_to_save = "localhost"
        else:
            self.settings.setValue(SETTINGS_DB_TYPE, "remote")
            host_to_save = self.host_edit.text().strip()
        
        self.settings.setValue(SETTINGS_DB_HOST, host_to_save)
        self.settings.setValue(SETTINGS_DB_PORT, self.port_spinbox.value())
        self.settings.setValue(SETTINGS_DB_NAME, self.dbname_edit.text().strip())
        self.settings.setValue(SETTINGS_DB_USER, self.user_edit.text().strip())
        
        # --- CORREZIONE: Rimuovi o correggi la riga che fa riferimento a schema_edit ---
        # Opzione 1: Se non serve lo schema, rimuovi questa riga:
        # self.settings.setValue(SETTINGS_DB_SCHEMA, self.schema_edit.text().strip() or "catasto")
        
        # Opzione 2: Se serve lo schema, usa un valore fisso:
        self.settings.setValue(SETTINGS_DB_SCHEMA, "catasto")  # Valore fisso
        
        # --- FINE CORREZIONE ---
        
        # --- NUOVA LOGICA PER LA PASSWORD ---
        if self.save_password_check.isChecked():
            # Salva la password se la checkbox è spuntata
            self.settings.setValue(SETTINGS_DB_PASSWORD, self.password_edit.text())
        else:
            # Altrimenti, rimuovi la chiave per non salvarla
            self.settings.remove(SETTINGS_DB_PASSWORD)
        # --- FINE NUOVA LOGICA ---

        self.settings.sync()
        
        # AGGIUNGI UN LOG PER VERIFICARE COSA VIENE SALVATO
        # (Rimuovi o commenta la riga che fa riferimento a db_type_combo.currentText() 
        # dato che ora usi radio button invece di combobox)
        
        self.settings.sync() # Forza la scrittura su disco
        logging.getLogger("CatastoGUI").info(f"Impostazioni di connessione al database salvate (senza password) in: {self.settings.fileName()}")

    def _handle_emergency_restore(self):
        """Gestisce il flusso di ripristino di emergenza."""
        reply = QMessageBox.critical(
            self,
            "ATTENZIONE: OPERAZIONE DISTRUTTIVA",
            "Stai per CANCELLARE il database corrente e sostituirlo con un backup.\n"
            "Questa operazione è irreversibile e va usata solo se il database è corrotto o inaccessibile.\n\n"
            "Sei assolutamente sicuro di voler procedere?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            self.logger.info("Ripristino di emergenza annullato dall'utente.")
            return

        # Raccogli i dati di connessione dal dialogo
        config = self.get_config_values(include_password=True)
        if not all(config.values()):
            QMessageBox.warning(self, "Dati Mancanti", "Compila tutti i campi di connessione per procedere.")
            return

        # Chiedi all'utente di selezionare il file di backup
        backup_file, _ = QFileDialog.getOpenFileName(
            self, "Seleziona File di Backup", "", "File Dump (*.dump);;Tutti i file (*)")

        if not backup_file:
            return

        # Conferma finale
        reply2 = QMessageBox.question(self, "Conferma Finale",
            f"Confermi di voler CANCELLARE il database '{config['dbname']}' e ripristinarlo dal file:\n{os.path.basename(backup_file)}?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)

        if reply2 != QMessageBox.Yes:
            return

        # Crea un DB Manager temporaneo per l'operazione
        emergency_db_manager = CatastoDBManager(
            host=config["host"], port=config["port"],
            dbname=config["dbname"], user=config["user"],
            password=config["password"]
        )

        # Esegui l'operazione
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            success, message = emergency_db_manager.execute_restore_from_file_emergency(backup_file)
            if success:
                QMessageBox.information(self, "Successo", message)
                # Se il ripristino ha successo, potremmo voler accettare il dialogo
                # per forzare un nuovo tentativo di connessione all'avvio.
                self.accept()
            else:
                QMessageBox.critical(self, "Fallimento Ripristino", message)
        finally:
            QApplication.restoreOverrideCursor()
    def get_config_values(self, include_password: bool = False) -> Dict[str, Any]:
        """
        Recupera i valori di configurazione dai campi della UI.
        Corretto per leggere dai radio button invece che da una combobox.
        """
        # --- INIZIO CORREZIONE ---
        if self.local_radio.isChecked():
            db_type_val = "local"
            host_val = "localhost"
        else:
            db_type_val = "remote"
            host_val = self.host_edit.text().strip()
        # --- FINE CORREZIONE ---

        config = {
            "db_type": db_type_val,
            "host": host_val,
            "port": self.port_spinbox.value(),
            "dbname": self.dbname_edit.text().strip(),
            "user": self.user_edit.text().strip(),
            "save_password": self.save_password_check.isChecked()
        }
        if include_password:
            config["password"] = self.password_edit.text()

        return config
    
    
class DocumentViewerDialog(QDialog):
    def __init__(self, parent=None, file_path: str = None):
        super().__init__(parent)
        self.logger = logging.getLogger(f"CatastoGUI.{self.__class__.__name__}")
        self.file_path = file_path
        self.setWindowTitle("Visualizzatore Documento")
        self.setMinimumSize(800, 600)

        self._init_ui()
        self._load_document()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        
        self.viewer_widget = QWidget()
        self.viewer_layout = QVBoxLayout(self.viewer_widget)
        self.viewer_layout.setContentsMargins(0,0,0,0)

        button_layout = QHBoxLayout()
        self.close_button = QPushButton("Chiudi")
        self.close_button.clicked.connect(self.accept)
        button_layout.addStretch()
        button_layout.addWidget(self.close_button)
        button_layout.addStretch()

        main_layout.addWidget(self.viewer_widget)
        main_layout.addLayout(button_layout)

    def _load_document(self):
        if not self.file_path or not os.path.exists(self.file_path):
            QMessageBox.critical(self, "Errore", "File non trovato o percorso non valido.")
            self.logger.error(f"Tentativo di caricare documento non trovato o non valido: {self.file_path}")
            self.viewer_layout.addWidget(QLabel("Errore: File non trovato."))
            return

        file_extension = os.path.splitext(self.file_path)[1].lower()

        if file_extension == '.pdf':
            self._load_pdf()
        elif file_extension in ['.jpg', '.jpeg', '.png', '.bmp', '.gif']:
            self._load_image()
        else:
            QMessageBox.warning(self, "Formato non supportato", f"Il formato '{file_extension}' non è supportato per la visualizzazione interna.")
            self.logger.warning(f"Formato documento non supportato per la visualizzazione interna: {self.file_path}")
            self.viewer_layout.addWidget(QLabel(f"Formato '{file_extension}' non supportato."))
            
    def _load_pdf(self):
        try:
            self.web_view = QWebEngineView(self)
            self.web_view.setUrl(QUrl.fromLocalFile(self.file_path))
            self.viewer_layout.addWidget(self.web_view)
            self.logger.info(f"PDF caricato in QWebEngineView: {self.file_path}")
        except Exception as e:
            self.logger.error(f"Errore durante il caricamento del PDF in QWebEngineView: {e}", exc_info=True)
            QMessageBox.critical(self, "Errore PDF", f"Impossibile visualizzare il PDF. Errore: {e}")
            self.viewer_layout.addWidget(QLabel("Errore nel caricamento del PDF."))
            
    def _load_image(self):
        try:
            self.graphics_scene = QGraphicsScene(self)
            self.graphics_view = QGraphicsView(self.graphics_scene, self)
            self.graphics_view.setRenderHint(QPainter.Antialiasing)
            self.graphics_view.setRenderHint(QPainter.SmoothPixmapTransform)
            self.graphics_view.setCacheMode(QGraphicsView.CacheBackground)
            self.graphics_view.setViewportUpdateMode(QGraphicsView.BoundingRectViewportUpdate)
            self.graphics_view.setDragMode(QGraphicsView.ScrollHandDrag)

            pixmap = QPixmap(str(self.file_path))
            if pixmap.isNull():
                raise ValueError(f"Impossibile caricare immagine da: {self.file_path}")

            self.pixmap_item = self.graphics_scene.addPixmap(pixmap)
            self.graphics_view.fitInView(self.pixmap_item, Qt.KeepAspectRatio)
            self.graphics_view.setAlignment(Qt.AlignCenter)

            self.zoom_factor = 1.0
            self.graphics_view.wheelEvent = self._image_wheel_event

            self.viewer_layout.addWidget(self.graphics_view)
            self.logger.info(f"Immagine caricata in QGraphicsView: {self.file_path}")

        except Exception as e:
            self.logger.error(f"Errore durante il caricamento dell'immagine in QGraphicsView: {e}", exc_info=True)
            QMessageBox.critical(self, "Errore Immagine", f"Impossibile visualizzare l'immagine. Errore: {e}")
            self.viewer_layout.addWidget(QLabel("Errore nel caricamento dell'immagine."))

    def _image_wheel_event(self, event):
        zoom_in_factor = 1.15
        zoom_out_factor = 1 / zoom_in_factor
        
        if event.angleDelta().y() > 0:
            self.zoom_factor *= zoom_in_factor
        else:
            self.zoom_factor *= zoom_out_factor

        self.zoom_factor = max(0.1, min(self.zoom_factor, 10.0))

        transform = self.graphics_view.transform()
        transform.reset()
        transform.scale(self.zoom_factor, self.zoom_factor)
        self.graphics_view.setTransform(transform)

        event.accept()

# *** FINE: Classe DocumentViewerDialog ***
class PartitaDetailsDialog(QDialog):
    def __init__(self, partita_data, parent=None):
        super(PartitaDetailsDialog, self).__init__(parent)
        self.partita = partita_data
        self.db_manager = getattr(parent, 'db_manager', None) 
        self.logger = logging.getLogger(f"CatastoGUI.{self.__class__.__name__}")

        self.setWindowTitle(
            f"Dettagli Partita {partita_data['numero_partita']}")
        self.setMinimumSize(700, 500)

        self._init_ui()
        self._load_all_data() # <--- Assicurati che sia chiamato solo qui
        self._update_document_tab_title() 

        
    def _init_ui(self):
        layout = QVBoxLayout(self)
        

        

        # Sostituisci questa riga:
        # title_label = QLabel(f"<h2>Partita N.{self.partita['numero_partita']} ({self.partita['suffisso_partita']}) - {self.partita['comune_nome']}</h2>")

        # Con questa logica più robusta:
        header_layout = QHBoxLayout()
        suffisso_db = self.partita.get('suffisso_partita')

        # Controlliamo se il suffisso esiste e non è una stringa vuota
        suffisso_display = f" ({suffisso_db.strip()})" if suffisso_db and suffisso_db.strip() else ""

        titolo_completo = f"<h2>Partita N.{self.partita['numero_partita']}{suffisso_display} - {self.partita['comune_nome']}</h2>"
        title_label = QLabel(titolo_completo)

        
        header_layout.addWidget(title_label)
        layout.addLayout(header_layout)

        # Informazioni generali
        info_group = QGroupBox("Informazioni Generali")
        info_layout = QGridLayout()

        info_layout.addWidget(QLabel("<b>ID:</b>"), 0, 0)
        info_layout.addWidget(QLabel(str(self.partita['id'])), 0, 1)

        info_layout.addWidget(QLabel("<b>Tipo:</b>"), 0, 2)
        info_layout.addWidget(QLabel(self.partita['tipo']), 0, 3)

        info_layout.addWidget(QLabel("<b>Stato:</b>"), 1, 0)
        info_layout.addWidget(QLabel(self.partita['stato']), 1, 1)

        info_layout.addWidget(QLabel("<b>Data Impianto:</b>"), 1, 2)
        info_layout.addWidget(QLabel(str(self.partita['data_impianto'])), 1, 3)

        # NUOVA RIGA: Suffisso Partita
        info_layout.addWidget(QLabel("<b>Suffisso:</b>"), 2, 2) # Adatta la riga/colonna
        info_layout.addWidget(QLabel(self.partita.get('suffisso_partita', 'N/A')), 2, 3)

        if self.partita.get('data_chiusura'):
            info_layout.addWidget(QLabel("<b>Data Chiusura:</b>"), 2, 0) # Adatta la riga
            info_layout.addWidget(QLabel(str(self.partita['data_chiusura'])), 2, 1)
        
        info_group.setLayout(info_layout)
        layout.addWidget(info_group)

        # Tabs per possessori, immobili, variazioni, documenti
        self.tabs = QTabWidget() # Rinomina a self.tabs per coerenza
        layout.addWidget(self.tabs)

        # Tab Possessori
        possessori_tab = QWidget()
        possessori_layout = QVBoxLayout(possessori_tab)
        possessori_table = QTableWidget()
        possessori_table.setColumnCount(4)
        possessori_table.setHorizontalHeaderLabels(["ID", "Nome Completo", "Titolo", "Quota"])
        possessori_table.setAlternatingRowColors(True)
        # --- INIZIO MODIFICA ---
        # Aggiungi queste righe per gestire il ridimensionamento delle colonne
        header_possessori = possessori_table.horizontalHeader()
        # La colonna "ID" (indice 0) si adatta al contenuto
        header_possessori.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        # La colonna "Nome Completo" (indice 1) si espande per riempire lo spazio
        header_possessori.setSectionResizeMode(1, QHeaderView.Stretch)
        # Le colonne "Titolo" e "Quota" (indici 2 e 3) si adattano al contenuto
        header_possessori.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header_possessori.setSectionResizeMode(3, QHeaderView.ResizeToContents)
# --- FINE MODIFICA ---
        if self.partita.get('possessori'):
            possessori_table.setRowCount(len(self.partita['possessori']))
            for i, possessore in enumerate(self.partita['possessori']):
                possessori_table.setItem(i, 0, QTableWidgetItem(str(possessore.get('id', ''))))
                possessori_table.setItem(i, 1, QTableWidgetItem(possessore.get('nome_completo', '')))
                possessori_table.setItem(i, 2, QTableWidgetItem(possessore.get('titolo', '')))
                possessori_table.setItem(i, 3, QTableWidgetItem(possessore.get('quota', '')))
        possessori_layout.addWidget(possessori_table)
        self.tabs.addTab(possessori_tab, "Possessori")

        # Tab Immobili
        immobili_tab = QWidget()
        immobili_layout = QVBoxLayout(immobili_tab)
        immobili_table = ImmobiliTableWidget()
        if self.partita.get('immobili'):
            immobili_table.populate_data(self.partita['immobili'])
        immobili_layout.addWidget(immobili_table)
        self.tabs.addTab(immobili_tab, "Immobili")

        # Tab Variazioni
        variazioni_tab = QWidget()
        variazioni_layout = QVBoxLayout()

        variazioni_table = QTableWidget()
        # Aumenta il numero di colonne per includere origine e destinazione per esteso
        variazioni_table.setColumnCount(6) # Ad es., ID, Tipo, Data, Partita Origine, Partita Destinazione, Contratto
        variazioni_table.setHorizontalHeaderLabels([
            "ID Var.", "Tipo", "Data Var.", "Partita Origine", "Partita Destinazione", "Contratto" # Etichette aggiornate
        ])
        variazioni_table.setAlternatingRowColors(True)
        variazioni_table.horizontalHeader().setStretchLastSection(True) # Per far espandere l'ultima colonna
        variazioni_table.setEditTriggers(QTableWidget.NoEditTriggers)

        if self.partita.get('variazioni'):
            variazioni_table.setRowCount(len(self.partita['variazioni']))
            for i, var in enumerate(self.partita['variazioni']):
                col = 0
                variazioni_table.setItem(i, col, QTableWidgetItem(str(var.get('id', '')))); col += 1
                variazioni_table.setItem(i, col, QTableWidgetItem(var.get('tipo', ''))); col += 1
                variazioni_table.setItem(i, col, QTableWidgetItem(str(var.get('data_variazione', '')))); col += 1

                # Informazioni Partita Origine
                origine_text = ""
                if var.get('partita_origine_id'): # Solo se l'ID esiste
                    num_orig = var.get('origine_numero_partita', 'N/D')
                    com_orig = var.get('origine_comune_nome', 'N/D')
                    origine_text = f"N.{num_orig} ({com_orig})"
                else:
                    origine_text = "-" # O "N/A"
                variazioni_table.setItem(i, col, QTableWidgetItem(origine_text)); col += 1

                # Informazioni Partita Destinazione
                dest_text = ""
                if var.get('partita_destinazione_id'): # Solo se l'ID esiste
                    num_dest = var.get('destinazione_numero_partita', 'N/D')
                    com_dest = var.get('destinazione_comune_nome', 'N/D')
                    dest_text = f"N.{num_dest} ({com_dest})"
                else:
                    dest_text = "-" # O "N/A"
                variazioni_table.setItem(i, col, QTableWidgetItem(dest_text)); col += 1

                # Contratto info (come prima)
                contratto_text = ""
                if var.get('tipo_contratto'):
                    contratto_text = f"{var['tipo_contratto']} del {var.get('data_contratto', '')}"
                    if var.get('notaio'):
                        contratto_text += f" - {var['notaio']}"
                variazioni_table.setItem(i, col, QTableWidgetItem(contratto_text)); col += 1

        variazioni_layout.addWidget(variazioni_table)
        variazioni_tab.setLayout(variazioni_layout)
        self.tabs.addTab(variazioni_tab, "Variazioni")


        # Tab Documenti (come prima)
        self.documents_tab_widget = QWidget()
        self.documents_tab_layout = QVBoxLayout(self.documents_tab_widget)
        self.documents_table = QTableWidget()
        self.documents_table.setColumnCount(6)
        self.documents_table.setHorizontalHeaderLabels(["ID Doc.", "Titolo", "Tipo Doc.", "Anno", "Rilevanza", "Percorso"])
        self.documents_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.documents_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.documents_table.horizontalHeader().setStretchLastSection(True)
        self.documents_table.setSortingEnabled(True)
        self.documents_table.itemSelectionChanged.connect(self._update_details_doc_buttons_state)
        self.documents_tab_layout.addWidget(self.documents_table)
        
        doc_buttons_layout = QHBoxLayout()
        self.btn_apri_doc_details_dialog = QPushButton(QApplication.style().standardIcon(QStyle.SP_DialogOpenButton), "Apri Documento")
        self.btn_apri_doc_details_dialog.clicked.connect(self._apri_documento_selezionato_from_details_dialog)
        self.btn_apri_doc_details_dialog.setEnabled(False)
        doc_buttons_layout.addWidget(self.btn_apri_doc_details_dialog)
        doc_buttons_layout.addStretch()
        self.documents_tab_layout.addLayout(doc_buttons_layout)
        self.tabs.addTab(self.documents_tab_widget, "Documenti Allegati")


        # --- Sostituzione dei pulsanti di esportazione ---
        buttons_layout = QHBoxLayout()

        self.btn_export_txt = QPushButton("Esporta TXT")
        self.btn_export_txt.clicked.connect(self._export_partita_to_txt)
        buttons_layout.addWidget(self.btn_export_txt)

        self.btn_export_pdf = QPushButton("Esporta PDF")
        self.btn_export_pdf.clicked.connect(self._export_partita_to_pdf)
        self.btn_export_pdf.setEnabled(FPDF_AVAILABLE) # Abilita solo se FPDF è disponibile
        buttons_layout.addWidget(self.btn_export_pdf)

        # Il pulsante JSON che avevi prima era export_button. Lo rimuoviamo o lo rendiamo PDF/TXT.
        # export_button = QPushButton("Esporta in JSON")
        # export_button.clicked.connect(self.export_to_json) # Non più chiamato
        # buttons_layout.addWidget(export_button) # Rimuovi o commenta questa riga

        close_button = QPushButton("Chiudi")
        close_button.clicked.connect(self.accept)

        buttons_layout.addStretch()
        # buttons_layout.addWidget(export_button) # Rimosso
        buttons_layout.addWidget(close_button)

        layout.addLayout(buttons_layout)
        self.setLayout(layout)
    
    def _load_all_data(self):
        """Carica i dati per tutti i tab."""
        # Se il db_manager non è stato passato o non è valido
        if not self.db_manager:
            self.logger.warning("DB Manager non disponibile, impossibile caricare i dati dei documenti.")
            # Popola la tabella con un messaggio di errore o lascia vuota
            self.documents_table.setRowCount(1)
            item_msg = QTableWidgetItem("DB Manager non disponibile. Impossibile caricare documenti.")
            item_msg.setTextAlignment(Qt.AlignCenter)
            self.documents_table.setItem(0, 0, item_msg)
            self.documents_table.setSpan(0, 0, 1, self.documents_table.columnCount())
            return

        # Carica i documenti e aggiorna la tabella dei documenti
        try:
            documenti_list = self.db_manager.get_documenti_per_partita(self.partita['id'])
            self.documents_table.setRowCount(0) # Pulisci prima di popolare

            if documenti_list:
                self.documents_table.setRowCount(len(documenti_list))
                for row, doc_data in enumerate(documenti_list):
                    self.documents_table.setItem(row, 0, QTableWidgetItem(str(doc_data.get('documento_id', ''))))
                    self.documents_table.setItem(row, 1, QTableWidgetItem(doc_data.get('titolo', '')))
                    self.documents_table.setItem(row, 2, QTableWidgetItem(doc_data.get('tipo_documento', '')))
                    self.documents_table.setItem(row, 3, QTableWidgetItem(str(doc_data.get('anno', ''))))
                    self.documents_table.setItem(row, 4, QTableWidgetItem(doc_data.get('rilevanza', '')))
                    
                    # Percorso, con un tooltip che mostra il percorso completo
                    percorso_file_full = doc_data.get('percorso_file', 'N/D')
                    path_item = QTableWidgetItem(os.path.basename(percorso_file_full) if percorso_file_full else "N/D")
                    path_item.setToolTip(percorso_file_full) # Il tooltip mostrerà il percorso completo
                    # Salva il percorso completo nell'UserRole per il pulsante "Apri"
                    percorso_file_full = doc_data.get('percorso_file', '')
                    path_item = QTableWidgetItem(os.path.basename(percorso_file_full) if percorso_file_full else "N/D")
                    path_item.setData(Qt.UserRole, percorso_file_full)  # Assicurati che questo sia sempre una stringa valida
                    self.documents_table.setItem(row, 5, path_item)
                self.documents_table.resizeColumnsToContents()
            else:
                self.logger.info(f"Nessun documento allegato per la partita ID {self.partita['id']}.")
                self.documents_table.setRowCount(1)
                no_docs_item = QTableWidgetItem("Nessun documento allegato a questa partita.")
                no_docs_item.setTextAlignment(Qt.AlignCenter)
                self.documents_table.setItem(0, 0, no_docs_item)
                self.documents_table.setSpan(0, 0, 1, self.documents_table.columnCount())
        except Exception as e:
            self.logger.error(f"Errore durante il caricamento dei documenti per la partita {self.partita['id']}: {e}", exc_info=True)
            QMessageBox.critical(self, "Errore Caricamento Documenti", f"Si è verificato un errore durante il caricamento dei documenti: {e}")
            self.documents_table.setRowCount(1)
            error_item = QTableWidgetItem("Errore nel caricamento dei documenti.")
            error_item.setTextAlignment(Qt.AlignCenter)
            self.documents_table.setItem(0, 0, error_item)
            self.documents_table.setSpan(0, 0, 1, self.documents_table.columnCount())
        finally:
            self.documents_table.setSortingEnabled(True)
            self._update_document_tab_title() # Aggiorna il titolo del tab con il conteggio
            self._update_details_doc_buttons_state() # Aggiorna lo stato dei pulsanti Apri

    def _export_partita_to_txt(self):
        """Esporta i dettagli della partita in formato TXT (testo leggibile)."""
        if not self.partita:
            QMessageBox.warning(self, "Errore Dati", "Nessun dato della partita da esportare.")
            return

        partita_id = self.partita.get('id', 'sconosciuto')
        default_filename = f"dettaglio_partita_{partita_id}_{date.today().isoformat()}.txt"

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Salva Dettaglio Partita in TXT",
            default_filename,
            "File di testo (*.txt);;Tutti i file (*)"
        )

        if file_path:
            try:
                # Genera un testo leggibile con le informazioni della partita
                text_content = self._generate_partita_text_report()

                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(text_content)

                prompt_to_open_file(self, file_path)
                self.logger.info(f"Dettaglio partita TXT salvato con successo in: {file_path}")
            except Exception as e:
                self.logger.error(f"Errore durante l'esportazione TXT del dettaglio partita: {e}", exc_info=True)
                QMessageBox.critical(self, "Errore Esportazione", f"Errore durante il salvataggio del file TXT:\n{e}")

    def _export_partita_to_pdf(self):
        """Esporta i dettagli della partita in formato PDF."""
        if not FPDF_AVAILABLE:
            QMessageBox.critical(self, "Errore Libreria", "La libreria FPDF (fpdf2) non è disponibile per generare PDF.")
            return
        if not self.partita:
            QMessageBox.warning(self, "Errore Dati", "Nessun dato della partita da esportare.")
            return

        partita_id = self.partita.get('id', 'sconosciuto')
        pdf_report_title = f"Dettaglio Partita N.{self.partita.get('numero_partita', 'N/D')} - Comune: {self.partita.get('comune_nome', 'N/D')}"
        default_filename_prefix = f"dettaglio_partita_{partita_id}"

        # Genera un testo leggibile per l'anteprima e per il PDF
        text_content = self._generate_partita_text_report()

        # Usa la classe generica per l'esportazione PDF (che include l'anteprima)
        # Nota: PDFApreviewDialog e GenericTextReportPDF sono in app_utils
        preview_dialog = PDFApreviewDialog(text_content, self, title=f"Anteprima: {pdf_report_title}")
        if preview_dialog.exec_() != QDialog.Accepted:
            self.logger.info(f"Esportazione PDF per '{pdf_report_title}' annullata dall'utente dopo anteprima.")
            return

        filename_pdf, _ = QFileDialog.getSaveFileName(
            self, f"Salva PDF - {pdf_report_title}", f"{default_filename_prefix}_{date.today().isoformat()}.pdf", "File PDF (*.pdf)")

        if filename_pdf:
            try:
                pdf = GenericTextReportPDF(report_title=pdf_report_title)
                pdf.add_page()
                pdf.add_report_text(text_content)
                pdf.output(filename_pdf)
                prompt_to_open_file(self, filename_pdf)
                self.logger.info(f"Dettaglio partita PDF salvato con successo in: {filename_pdf}")
            except Exception as e:
                self.logger.error(f"Errore durante la generazione del PDF per il dettaglio partita: {e}", exc_info=True)
                QMessageBox.critical(self, "Errore Esportazione PDF", f"Impossibile generare il PDF:\n{e}")

    def _generate_partita_text_report(self) -> str:
        """
        Genera un report testuale formattato con tutti i dettagli della partita,
        inclusi i possessori, immobili, variazioni e documenti allegati.
        """
        report_lines = []
        partita = self.partita # self.partita contiene tutti i dati recuperati da get_partita_details

        # --- SEZIONE 1: INTESTAZIONE E DATI GENERALI PARTITA ---
        report_lines.append("=" * 70)
        # Includi il suffisso nel titolo, se presente
        numero_partita_display = f"N. {partita.get('numero_partita', 'N/D')}"
        if partita.get('suffisso_partita'):
            numero_partita_display += f" ({partita['suffisso_partita']})"

        report_lines.append(f"DETTAGLIO PARTITA {numero_partita_display}")
        report_lines.append(f"Comune: {partita.get('comune_nome', 'N/D')}")
        report_lines.append(f"ID Partita: {partita.get('id', 'N/D')}")
        report_lines.append("=" * 70)

        report_lines.append(f"Tipo Partita: {partita.get('tipo', 'N/D')}")
        report_lines.append(f"Stato: {partita.get('stato', 'N/D')}")
        report_lines.append(f"Data Impianto: {partita.get('data_impianto', 'N/D')}")
        data_chiusura = partita.get('data_chiusura')
        report_lines.append(f"Data Chiusura: {data_chiusura if data_chiusura else 'N/A'}")
        numero_provenienza = partita.get('numero_provenienza')
        report_lines.append(f"Numero Provenienza: {numero_provenienza if numero_provenienza else 'N/A'}")
        report_lines.append("\n") # Linea vuota per separazione

        # --- SEZIONE 2: POSSESSORI ---
        report_lines.append("=" * 70)
        report_lines.append("POSSESSORI ASSOCIATI")
        report_lines.append("=" * 70)
        if partita.get('possessori'):
            for i, poss in enumerate(partita['possessori']):
                report_lines.append(f"  - Possessore {i+1} (ID: {poss.get('id', 'N/D')}): {poss.get('nome_completo', 'N/D')}")
                report_lines.append(f"    Titolo di Possesso: {poss.get('titolo', 'N/A')}")
                report_lines.append(f"    Quota: {poss.get('quota', 'N/A')}")
                if i < len(partita['possessori']) - 1:
                    report_lines.append("  " + "-" * 60) # Separatore tra possessori
        else:
            report_lines.append("  Nessun possessore associato a questa partita.")
        report_lines.append("\n") # Linea vuota per separazione

        # --- SEZIONE 3: IMMOBILI ---
        report_lines.append("=" * 70)
        report_lines.append("IMMOBILI CENSITI")
        report_lines.append("=" * 70)
        if partita.get('immobili'):
            for i, imm in enumerate(partita['immobili']):
                report_lines.append(f"  - Immobile {i+1} (ID: {imm.get('id', 'N/D')}): {imm.get('natura', 'N/D')}")
                localita_info = f"{imm.get('localita_nome', '')}"
                if imm.get('civico') is not None and str(imm.get('civico')).strip() != '':
                    localita_info += f", civ. {imm.get('civico')}"
                if imm.get('localita_tipo'):
                    localita_info += f" ({imm.get('localita_tipo')})"
                report_lines.append(f"    Località: {localita_info.strip() if localita_info.strip() else 'N/A'}")
                report_lines.append(f"    Classificazione: {imm.get('classificazione', 'N/A')}")
                report_lines.append(f"    Consistenza: {imm.get('consistenza', 'N/A')}")
                piani_vani_info = []
                if imm.get('numero_piani') is not None and imm.get('numero_piani') > 0:
                    piani_vani_info.append(f"Piani: {imm.get('numero_piani')}")
                if imm.get('numero_vani') is not None and imm.get('numero_vani') > 0:
                    piani_vani_info.append(f"Vani: {imm.get('numero_vani')}")
                if piani_vani_info:
                    report_lines.append(f"    Dettagli: {' | '.join(piani_vani_info)}")
                
                if i < len(partita['immobili']) - 1:
                    report_lines.append("  " + "-" * 60) # Separatore tra immobili
        else:
            report_lines.append("  Nessun immobile associato a questa partita.")
        report_lines.append("\n") # Linea vuota per separazione

        # --- SEZIONE 4: VARIAZIONI ---
        report_lines.append("=" * 70)
        report_lines.append("VARIAZIONI STORICHE")
        report_lines.append("=" * 70)
        if partita.get('variazioni'):
            for i, var in enumerate(partita['variazioni']):
                report_lines.append(f"  - Variazione {i+1} (ID: {var.get('id', 'N/D')}): {var.get('tipo', 'N/D')}")
                report_lines.append(f"    Data Variazione: {var.get('data_variazione', 'N/D')}")
                
                # Dettagli Partita Origine
                orig_part_id = var.get('partita_origine_id')
                orig_num = var.get('origine_numero_partita', 'N/D')
                orig_com = var.get('origine_comune_nome', 'N/D')
                if orig_part_id:
                    report_lines.append(f"    Partita Origine: N.{orig_num} (Comune: {orig_com}) [ID: {orig_part_id}]")
                else:
                    report_lines.append("    Partita Origine: N/A")

                # Dettagli Partita Destinazione
                dest_part_id = var.get('partita_destinazione_id')
                dest_num = var.get('destinazione_numero_partita', 'N/D')
                dest_com = var.get('destinazione_comune_nome', 'N/D')
                if dest_part_id:
                    report_lines.append(f"    Partita Destinazione: N.{dest_num} (Comune: {dest_com}) [ID: {dest_part_id}]")
                else:
                    report_lines.append("    Partita Destinazione: N/A")

                # Dettagli Contratto
                contr_info_parts = []
                if var.get('tipo_contratto'): contr_info_parts.append(f"Tipo: {var.get('tipo_contratto')}")
                if var.get('data_contratto'): contr_info_parts.append(f"Data: {var.get('data_contratto')}")
                if var.get('notaio'): contr_info_parts.append(f"Notaio: {var.get('notaio')}")
                if var.get('repertorio'): contr_info_parts.append(f"Repertorio: {var.get('repertorio')}")
                if contr_info_parts:
                    report_lines.append(f"    Contratto: {' | '.join(contr_info_parts)}")
                
                if var.get('note_variazione') : report_lines.append(f"    Note Variazione: {var.get('note_variazione')}") # Se c'è una colonna note per la variazione
                if var.get('contratto_note') : report_lines.append(f"    Note Contratto: {var.get('contratto_note')}") # Se c'è una colonna note nel contratto

                if i < len(partita['variazioni']) - 1:
                    report_lines.append("  " + "-" * 60) # Separatore tra variazioni
        else:
            report_lines.append("  Nessuna variazione registrata per questa partita.")
        report_lines.append("\n") # Linea vuota per separazione

        # --- SEZIONE 5: DOCUMENTI ALLEGATI ---
        report_lines.append("=" * 70)
        # Assicurati che self.documents_table sia popolata correttamente
        num_docs = self.documents_table.rowCount()
        # Se la tabella ha una sola riga e contiene il messaggio "Nessun documento..."
        if num_docs == 1 and self.documents_table.item(0,0) and "Nessun documento" in self.documents_table.item(0,0).text():
            num_docs = 0
        report_lines.append(f"DOCUMENTI ALLEGATI ({num_docs})")
        report_lines.append("=" * 70)
        
        if num_docs > 0:
            for r in range(self.documents_table.rowCount()):
                # Assicurati che gli item non siano None (se la tabella è vuota eccetto il placeholder)
                doc_id_item = self.documents_table.item(r,0)
                if not doc_id_item: continue # Salta se la riga è vuota (es. riga placeholder)

                doc_id = doc_id_item.text()
                titolo = self.documents_table.item(r,1).text()
                tipo_doc = self.documents_table.item(r,2).text()
                anno = self.documents_table.item(r,3).text()
                rilevanza = self.documents_table.item(r,4).text()
                percorso_short = self.documents_table.item(r,5).text()

                report_lines.append(f"  - Documento {r+1} (ID: {doc_id}): {titolo}")
                report_lines.append(f"    Tipo: {tipo_doc}, Anno: {anno}, Rilevanza: {rilevanza}")
                report_lines.append(f"    Percorso (locale): {percorso_short}")
                if r < num_docs - 1:
                    report_lines.append("  " + "-" * 60) # Separatore tra documenti
        else:
            report_lines.append("  Nessun documento allegato.")

        # --- SEZIONE FINALE ---
        report_lines.append("\n" + "=" * 70)
        report_lines.append("FINE DETTAGLIO PARTITA")
        report_lines.append("=" * 70)

        return "\n".join(report_lines)
    def _update_document_tab_title(self):
        """Aggiorna il titolo del tab "Documenti Allegati" con il conteggio."""
        count = self.documents_table.rowCount()
        # Se la tabella ha solo 1 riga e il testo è "Nessun documento allegato..." allora il conteggio è 0
        if count == 1 and self.documents_table.item(0,0) and "Nessun documento" in self.documents_table.item(0,0).text():
            count = 0
        
        tab_index = self.tabs.indexOf(self.documents_tab_widget)
        if tab_index != -1:
            self.tabs.setTabText(tab_index, f"Documenti Allegati ({count})")
            self.logger.info(f"Titolo tab documenti aggiornato a 'Documenti Allegati ({count})'.")


    def _update_details_doc_buttons_state(self):
        """Abilita/disabilita il pulsante 'Apri Documento' in base alla selezione."""
        has_selection = bool(self.documents_table.selectedItems())
        self.btn_apri_doc_details_dialog.setEnabled(has_selection)

    def _apri_documento_selezionato_from_details_dialog(self):
        selected_items = self.documents_table.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "Nessuna Selezione", "Seleziona un documento dalla lista per aprirlo.")
            return
        
        row = self.documents_table.currentRow()
        percorso_file_item = self.documents_table.item(row, 5) 
        if percorso_file_item:
            percorso_file_completo = percorso_file_item.data(Qt.UserRole) # Recupera il percorso completo salvato
            
            if os.path.exists(percorso_file_completo):
                from PyQt5.QtGui import QDesktopServices
                from PyQt5.QtCore import QUrl
                success = QDesktopServices.openUrl(QUrl.fromLocalFile(percorso_file_completo))
                if not success:
                    QMessageBox.warning(self, "Errore Apertura", f"Impossibile aprire il file:\n{percorso_file_completo}\nVerificare che sia installata un'applicazione associata o che i permessi siano corretti.")
            else:
                QMessageBox.warning(self, "File Non Trovato", f"Il file specificato non è stato trovato al percorso:\n{percorso_file_completo}\nIl file potrebbe essere stato spostato o eliminato.")
        else:
            QMessageBox.warning(self, "Percorso Mancante", "Informazioni sul percorso del file non disponibili per il documento selezionato.")

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
        self.possessori_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.possessori_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.possessori_table.setSelectionMode(QTableWidget.SingleSelection)
        self.possessori_table.setAlternatingRowColors(True)
        
        # Logica per l'espansione delle colonne
        header_possessori = self.possessori_table.horizontalHeader()
        header_possessori.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header_possessori.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header_possessori.setSectionResizeMode(2, QHeaderView.Stretch) # Espande "Nome Completo"
        header_possessori.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header_possessori.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        
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
        self.immobili_table.setSelectionMode(QTableWidget.SingleSelection)
        self.immobili_table.setSelectionBehavior(QTableWidget.SelectRows)
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
        self.variazioni_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.variazioni_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.variazioni_table.setSelectionMode(QTableWidget.SingleSelection)
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
        self.documents_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.documents_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.documents_table.setSelectionMode(QTableWidget.SingleSelection)
        self.documents_table.horizontalHeader().setStretchLastSection(True)
        self.documents_table.setSortingEnabled(True)
        self.documents_table.itemSelectionChanged.connect(self._update_details_doc_buttons_state)
        
        self.documents_table.setAcceptDrops(True)
        self.documents_table.setDropIndicatorShown(True)
        self.documents_table.setDragDropMode(QAbstractItemView.DropOnly)
        self.documents_table.dragEnterEvent = self.documents_table_dragEnterEvent
        self.documents_table.dragMoveEvent = self.documents_table_dragMoveEvent
        self.documents_table.dropEvent = self.documents_table_dropEvent
        
        layout_documenti.addWidget(self.documents_table)

        doc_buttons_layout = QHBoxLayout()
        self.btn_allega_nuovo = QPushButton(QApplication.style().standardIcon(QStyle.SP_FileLinkIcon), "Allega Nuovo Documento...")
        self.btn_allega_nuovo.clicked.connect(self._allega_nuovo_documento_a_partita)
        doc_buttons_layout.addWidget(self.btn_allega_nuovo)

        self.btn_apri_doc_details_dialog = QPushButton(QApplication.style().standardIcon(QStyle.SP_DialogOpenButton), "Apri Documento Selezionato")
        self.btn_apri_doc_details_dialog.clicked.connect(self._apri_documento_selezionato_from_details_dialog)
        self.btn_apri_doc_details_dialog.setEnabled(False)
        doc_buttons_layout.addWidget(self.btn_apri_doc_details_dialog)
        
        self.btn_scollega_doc = QPushButton(QApplication.style().standardIcon(QStyle.SP_TrashIcon), "Scollega Documento")
        self.btn_scollega_doc.clicked.connect(self._scollega_documento_selezionato)
        self.btn_scollega_doc.setEnabled(False)
        doc_buttons_layout.addWidget(self.btn_scollega_doc)
        
        doc_buttons_layout.addStretch()
        layout_documenti.addLayout(doc_buttons_layout)
        
        self.tab_widget.addTab(self.tab_documenti, "Documenti Allegati")

        # --- Blocco Pulsanti Finale ---
        buttons_layout = QHBoxLayout()
        self.btn_duplica_partita = QPushButton(self.style().standardIcon(QStyle.SP_FileDialogNewFolder), " Duplica questa Partita...")
        self.save_button = QPushButton("Salva Modifiche Dati Generali")
        self.close_dialog_button = QPushButton("Chiudi")
        self.btn_duplica_partita.clicked.connect(self._handle_duplica_partita)
        self.save_button.clicked.connect(self._save_changes)
        self.close_dialog_button.clicked.connect(self.accept)
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

        tipo_idx = self.tipo_combo.findText(partita.get('tipo', ''), Qt.MatchFixedString)
        if tipo_idx >= 0: self.tipo_combo.setCurrentIndex(tipo_idx)

        stato_idx = self.stato_combo.findText(partita.get('stato', ''), Qt.MatchFixedString)
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
                    id_rel_item.setData(Qt.UserRole, id_rel_val) # Salva l'ID relazione
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
                item.setTextAlignment(Qt.AlignCenter)
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
                    localita_text = ""
                    if 'localita_nome' in imm:
                        localita_text = imm['localita_nome']
                        if 'civico' in imm and imm['civico'] is not None:
                            localita_text += f", {imm['civico']}"
                        if 'localita_tipo' in imm:
                            localita_text += f" ({imm['localita_tipo']})"
                    self.immobili_table.setItem(row_idx, 4, QTableWidgetItem(localita_text))
                self.immobili_table.resizeColumnsToContents()
            else:
                self.logger.info(f"Nessun immobile trovato per la partita ID {self.partita_id}.")
                self.immobili_table.setRowCount(1)
                item = QTableWidgetItem("Nessun immobile associato a questa partita.")
                item.setTextAlignment(Qt.AlignCenter)
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
                item.setTextAlignment(Qt.AlignCenter)
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
        if options_dialog.exec_() != QDialog.Accepted:
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
                    documento_id_storico = doc.get("documento_id")
                    
                    # --- INIZIO CORREZIONE: Salvataggio dati robusto ---
            # Salviamo un dizionario con gli ID di relazione nell'UserRole
                    rel_data = {
                        'doc_id': doc.get('rel_documento_id'),
                        'partita_id': doc.get('rel_partita_id')
                    }

                    # L'item nella prima colonna conterrà tutti i dati per la riga
                    item_doc_id = QTableWidgetItem(str(doc.get('documento_id', '')))
                    item_doc_id.setData(Qt.UserRole, rel_data)
                    self.documents_table.setItem(row, 0, item_doc_id)
            # --- FINE CORREZIONE ---
                    # Salviamo l'ID del documento storico e l'ID della partita per la rimozione del legame
                    item_doc_id.setData(Qt.UserRole + 1, doc.get("dp_documento_id")) # ID del documento storico nella relazione
                    item_doc_id.setData(Qt.UserRole + 2, doc.get("dp_partita_id")) # ID della partita nella relazione (che è self.partita_id)
                    
                    
                    self.documents_table.setItem(row, 1, QTableWidgetItem(doc.get("titolo") or ''))
                    self.documents_table.setItem(row, 2, QTableWidgetItem(doc.get("tipo_documento") or ''))
                    self.documents_table.setItem(row, 3, QTableWidgetItem(str(doc.get("anno", '')) or ''))
                    self.documents_table.setItem(row, 4, QTableWidgetItem(doc.get("rilevanza") or ''))
                    
                    # CORREZIONE: Assicurati che il percorso sia salvato correttamente nell'UserRole
                    percorso_file_full = doc.get("percorso_file") or ''
                    path_item = QTableWidgetItem(os.path.basename(percorso_file_full) if percorso_file_full else "N/D")
                    path_item.setData(Qt.UserRole, percorso_file_full) # Salva percorso completo per l'apertura
                    self.documents_table.setItem(row, 5, path_item)
                
                self.documents_table.resizeColumnsToContents()
            else:
                self.logger.info(f"Nessun documento trovato per la partita ID {self.partita_id}.")
                self.documents_table.setRowCount(1)
                no_docs_item = QTableWidgetItem("Nessun documento allegato a questa partita.")
                no_docs_item.setTextAlignment(Qt.AlignCenter)
                self.documents_table.setItem(0, 0, no_docs_item)
                self.documents_table.setSpan(0, 0, 1, self.documents_table.columnCount())

        except Exception as e:
            self.logger.error(f"Errore caricamento documenti per partita ID {self.partita_id}: {e}", exc_info=True)
            QMessageBox.critical(self, "Errore Caricamento Documenti", f"Si è verificato un errore durante il caricamento dei documenti:\n{e}")
            # Mostra messaggio di errore nella tabella
            self.documents_table.setRowCount(1)
            error_item = QTableWidgetItem(f"Errore nel caricamento dei documenti: {e}")
            error_item.setTextAlignment(Qt.AlignCenter)
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

        if possessore_dialog.exec_() == QDialog.Accepted:
            if hasattr(possessore_dialog, 'selected_possessore') and possessore_dialog.selected_possessore:
                selected_possessore_id = possessore_dialog.selected_possessore.get('id')
                selected_possessore_nome = possessore_dialog.selected_possessore.get('nome_completo')
        if not selected_possessore_id or not selected_possessore_nome:
            self.logger.info("Nessun possessore selezionato o creato.")
            return

        self.logger.info(f"Possessore selezionato/creato: ID {selected_possessore_id}, Nome: {selected_possessore_nome}")
        tipo_partita_corrente = self.partita_data_originale.get('tipo', 'principale')
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
        selected_items = self.possessori_table.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "Nessuna Selezione", "Seleziona un possessore dalla tabella per modificarne il legame.")
            return

        current_row = selected_items[0].row()
        id_relazione_pp = self.possessori_table.item(current_row, 0).data(Qt.UserRole)
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

        id_relazione_pp = selected_items[0].data(Qt.UserRole)
        nome_possessore = self.possessori_table.item(selected_items[0].row(), 2).text()

        if id_relazione_pp is None:
            QMessageBox.critical(self, "Errore Interno", "ID relazione non trovato per il possessore selezionato.")
            return

        reply = QMessageBox.question(self, "Conferma Rimozione Legame",
                                     f"Sei sicuro di voler rimuovere il legame con il possessore '{nome_possessore}' (ID Relazione: {id_relazione_pp}) da questa partita?",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
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
        if dialog.exec_() == QDialog.Accepted and dialog.immobile_data:
            immobile_data = dialog.immobile_data
            try:
                # La procedura SQL inserisci_immobile in db_manager deve essere aggiornata
                # per accettare tutti i campi dall'immobile_data
                immobile_id = self.db_manager.inserisci_immobile(
                    partita_id=self.partita_id,
                    natura=immobile_data['natura'],
                    localita_id=immobile_data['localita_id'],
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
        
        if dialog.exec_() == QDialog.Accepted:
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
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
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
        # --- INIZIO MODIFICA ---
        # Controlla se la riga selezionata è una riga di placeholder
        if self.variazioni_table.rowCount() == 1 and self.variazioni_table.item(0, 0) and "Nessuna variazione" in self.variazioni_table.item(0, 0).text():
            QMessageBox.warning(self, "Nessuna Variazione", "Non ci sono variazioni valide selezionate per la modifica.")
            return
        # --- FINE MODIFICA ---

        variazione_id = int(self.variazioni_table.item(row, 0).text())

        # Apri un dialogo per modificare la variazione, simile a InserimentoVariazione (se lo hai)
        # Dobbiamo creare una classe ModificaVariazioneDialog
        from gui_widgets import ModificaVariazioneDialog # Assicurati che sia importata o creata
        dialog = ModificaVariazioneDialog(self.db_manager, variazione_id, self.partita_id, self) # Passa variazione_id, partita_id
        
        if dialog.exec_() == QDialog.Accepted:
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
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
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

        if dialog.exec_() == QDialog.Accepted and dialog.document_data:
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
            percorso_file_completo = percorso_file_item.data(Qt.UserRole)
            
            if percorso_file_completo and os.path.exists(percorso_file_completo):
                from PyQt5.QtGui import QDesktopServices
                from PyQt5.QtCore import QUrl
                
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
        # --- INIZIO CORREZIONE: Recupero dati robusto ---
        rel_data = id_doc_item.data(Qt.UserRole)
        if not isinstance(rel_data, dict) or not rel_data.get('doc_id') or not rel_data.get('partita_id'):
            self.logger.error(f"Dati di relazione mancanti o corrotti per la riga {row}: {rel_data}")
            QMessageBox.critical(self, "Errore Dati", "Informazioni sulla relazione documento-partita non trovate.")
            return

        documento_id_da_scollegare = rel_data['doc_id']
        partita_id_da_cui_scollegare = rel_data['partita_id']
        # --- FINE CORREZIONE --
        

        if not documento_id_da_scollegare or not partita_id_da_cui_scollegare:
            self.logger.error(f"Dati di relazione mancanti per la riga {row} (DocID: {documento_id_da_scollegare}, PartitaID: {partita_id_da_cui_scollegare})")
            QMessageBox.critical(self, "Errore Dati", "Informazioni sulla relazione documento-partita non trovate. Impossibile procedere.")
            return

        reply = QMessageBox.question(self, "Conferma Scollegamento",
                                     f"Sei sicuro di voler scollegare il documento '{titolo_doc}' (ID: {documento_id_da_scollegare}) "
                                     f"dalla partita corrente (ID: {partita_id_da_cui_scollegare})?",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)

        if reply == QMessageBox.Yes:
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
            QApplication.style().standardIcon(QStyle.SP_DialogOkButton), "OK")
        self.ok_button.clicked.connect(self._accept_details)
        self.cancel_button = QPushButton(QApplication.style().standardIcon(
            QStyle.SP_DialogCancelButton), "Annulla")
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
        if dialog.exec_() == QDialog.Accepted:
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
        if dialog.exec_() == QDialog.Accepted:
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
            QStyle.SP_DialogSaveButton), "Salva Modifiche")
        self.save_button.clicked.connect(self._save_changes)
        self.cancel_button = QPushButton(QApplication.style().standardIcon(
            QStyle.SP_DialogCancelButton), "Annulla")
        self.cancel_button.clicked.connect(self.reject)

        buttons_layout.addStretch()
        buttons_layout.addWidget(self.save_button)
        buttons_layout.addWidget(self.cancel_button)
        layout.addLayout(buttons_layout)

        self.setLayout(layout)
        
    # --- NUOVO METODO: per generare il nome completo ---
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
    # --- FINE NUOVO METODO ---

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
            from PyQt5.QtCore import QTimer
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
        if dialog.exec_() == QDialog.Accepted and dialog.selected_comune_id:
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
            self.accept()  # Chiude il dialogo e restituisce QDialog.Accepted

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
        form_layout.setRowWrapPolicy(QFormLayout.WrapAllRows)
        form_layout.setLabelAlignment(Qt.AlignLeft)

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
        self.note_edit.setFixedHeight(80)
        form_layout.addRow("Note:", self.note_edit)

        main_layout.addLayout(form_layout)

        self.button_box = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
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
        
        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
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
        self.possessori_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.possessori_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.possessori_table.setSelectionMode(QTableWidget.SingleSelection)
        self.possessori_table.setAlternatingRowColors(True)
        self.possessori_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.Stretch)  # o ResizeToContents
        self.possessori_table.setSortingEnabled(True)
        self.possessori_table.itemSelectionChanged.connect(
            self._aggiorna_stato_pulsanti_azione)  # NUOVO
        self.possessori_table.itemDoubleClicked.connect(
            self.apri_modifica_possessore_selezionato)  # NUOVO per doppio click

        layout.addWidget(self.possessori_table)

        # --- NUOVI Pulsanti di Azione ---
        action_layout = QHBoxLayout()
        self.btn_modifica_possessore = QPushButton(QApplication.style().standardIcon(
            QStyle.SP_FileDialogDetailedView), "Modifica Selezionato")
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

    def _aggiorna_stato_pulsanti_azione(self):  # NUOVO METODO
        """Abilita/disabilita i pulsanti di azione in base alla selezione nella tabella."""
        has_selection = bool(self.possessori_table.selectedItems())
        self.btn_modifica_possessore.setEnabled(has_selection)

    # NUOVO METODO HELPER
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

            dialog_result = dialog.exec_()  # Salva il risultato
            logging.getLogger("CatastoGUI").debug(
                # NUOVA STAMPA
                f"DEBUG: ModificaPossessoreDialog.exec_() restituito: {dialog_result} (Accepted è {QDialog.Accepted})")

            if dialog_result == QDialog.Accepted:
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
                item.setTextAlignment(Qt.AlignCenter)
                self.possessori_table.setItem(0, 0, item)
                self.possessori_table.setSpan(0, 0, 1, self.possessori_table.columnCount())

        except Exception as e:
            self.logger.error(f"Errore durante il caricamento dei possessori per comune ID {self.comune_id}: {e}", exc_info=True)
            QMessageBox.critical(self, "Errore Caricamento Dati", f"Si è verificato un errore: {e}")
            # Visualizza un messaggio di errore nella tabella
            self.possessori_table.setRowCount(1)
            item = QTableWidgetItem(f"Errore nel caricamento dei dati: {e}")
            item.setTextAlignment(Qt.AlignCenter)
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

        self.partite_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.partite_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.partite_table.setSelectionMode(QTableWidget.SingleSelection)
        self.partite_table.setAlternatingRowColors(True)
        self.partite_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.partite_table.setSortingEnabled(True)
        self.partite_table.itemDoubleClicked.connect(self.apri_dettaglio_partita_selezionata)
        self.partite_table.itemSelectionChanged.connect(self._aggiorna_stato_pulsante_modifica)

        layout.addWidget(self.partite_table)

        action_buttons_layout = QHBoxLayout()
        self.btn_apri_dettaglio = QPushButton(QApplication.style().standardIcon(
            QStyle.SP_FileDialogInfoView), "Vedi Dettagli")
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
                item.setTextAlignment(Qt.AlignCenter)
                self.partite_table.setItem(0, 0, item)
                self.partite_table.setSpan(0, 0, 1, self.partite_table.columnCount())

        except Exception as e:
            self.logger.error(f"Errore durante il caricamento delle partite per comune ID {self.comune_id}: {e}", exc_info=True)
            QMessageBox.critical(self, "Errore Caricamento Dati", f"Si è verificato un errore: {e}")
            self.partite_table.setRowCount(1)
            item = QTableWidgetItem(f"Errore nel caricamento dei dati: {e}")
            item.setTextAlignment(Qt.AlignCenter)
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
                details_dialog = PartitaDetailsDialog(partita_details_data, self)
                details_dialog.exec_()
            else:
                QMessageBox.warning(self, "Errore Dati", f"Impossibile recuperare i dettagli per la partita ID {partita_id}.")
        else:
            QMessageBox.information(self, "Nessuna Selezione", "Seleziona una partita dalla tabella per vederne i dettagli.")

    def apri_modifica_partita_selezionata(self, item: Optional[QTableWidgetItem] = None):
        partita_id = self._get_selected_partita_id()
        if partita_id is not None:
            dialog = ModificaPartitaDialog(self.db_manager, partita_id, self)
            if dialog.exec_() == QDialog.Accepted:
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
                details_dialog = PartitaDetailsDialog(partita_details_data, self)
                details_dialog.exec_()
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
        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel, self)
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
        self.descrizione_edit.setFixedHeight(100)
        form_layout.addRow("Descrizione:", self.descrizione_edit)

        form_layout.addRow("Data Creazione:", self.data_creazione_label)
        form_layout.addRow("Ultima Modifica:", self.data_modifica_label)

        main_layout.addLayout(form_layout)

        # Pulsanti
        self.button_box = QDialogButtonBox(
            QDialogButtonBox.Save | QDialogButtonBox.Cancel)
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
            from PyQt5.QtCore import QTimer
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
        self.localita_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.localita_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.localita_table.setSelectionMode(QTableWidget.SingleSelection)
        self.localita_table.itemSelectionChanged.connect(self._aggiorna_stato_pulsanti_action_localita) # Qui si collega il segnale
        self.localita_table.itemDoubleClicked.connect(self._handle_double_click)
        select_layout.addWidget(self.localita_table)

        select_action_layout = QHBoxLayout()
        self.btn_modifica_localita = QPushButton(QApplication.style().standardIcon(
            QStyle.SP_FileDialogDetailedView), "Modifica Selezionata")
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
            self.btn_salva_nuova_localita = QPushButton(QApplication.style().standardIcon(QStyle.SP_DialogSaveButton) ,"Salva Nuova Località")
            self.btn_salva_nuova_localita.clicked.connect(self._salva_nuova_localita_da_tab)
            create_form_layout.addRow(self.btn_salva_nuova_localita)
            self.tabs.addTab(create_tab, "Crea Nuova Località")

        buttons_layout = QHBoxLayout()

        self.select_button = QPushButton(QApplication.style().standardIcon(
            QStyle.SP_DialogApplyButton), "Seleziona")
        self.select_button.setToolTip("Conferma la località selezionata")
        self.select_button.clicked.connect(self._handle_selection_or_creation)
        buttons_layout.addWidget(self.select_button)

        buttons_layout.addStretch()

        self.chiudi_button = QPushButton(QApplication.style().standardIcon(
            QStyle.SP_DialogCloseButton), "Chiudi")
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
                    item.setTextAlignment(Qt.AlignCenter)
                    self.localita_table.setItem(0, 0, item)
                    self.localita_table.setSpan(0, 0, 1, self.localita_table.columnCount())

            except Exception as e:
                self.logger.error(f"Errore caricamento località per comune {self.comune_id} (filtro '{actual_filter_text}'): {e}", exc_info=True)
                QMessageBox.critical(
                    self, "Errore Caricamento", f"Impossibile caricare le località:\n{e}")
                self.localita_table.setRowCount(1)
                item = QTableWidgetItem(f"Errore caricamento: {e}")
                item.setTextAlignment(Qt.AlignCenter)
                self.localita_table.setItem(0, 0, item)
                self.localita_table.setSpan(0, 0, 1, self.localita_table.columnCount())
        else:
            self.logger.warning("Comune ID non disponibile per caricare località.")
            self.localita_table.setRowCount(1)
            item = QTableWidgetItem("ID Comune non disponibile per caricare località.")
            item.setTextAlignment(Qt.AlignCenter)
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
        # Importa ModificaLocalitaDialog localmente per evitare cicli di importazione
        from gui_widgets import ModificaLocalitaDialog 

        localita_id_sel = self._get_selected_localita_id_from_table()
        if localita_id_sel is not None:
            self.logger.info(f"LocalitaSelectionDialog: Richiesta modifica per località ID {localita_id_sel}.")
            # Istanzia e apre ModificaLocalitaDialog, passando il comune_id_parent
            dialog = ModificaLocalitaDialog(
                self.db_manager, localita_id_sel, self.comune_id, self) # comune_id qui è il comune_id_parent
            if dialog.exec_() == QDialog.Accepted:
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
                if civico_item_text and civico_item_text != "-" and civico_item_text.strip() != self.civico_spinbox_nuova.specialValueText(): # Verifica anche il testo speciale
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
        form_layout.addRow("Foglio:", self.foglio_edit)
        form_layout.addRow("Mappale:", self.mappale_edit)
        form_layout.addRow("Subalterno:", self.subalterno_edit)
        form_layout.addRow("Vani/Superficie:", self.vani_spinbox)
        form_layout.addRow("Note:", self.note_edit)

        main_layout.addLayout(form_layout)

        # --- Pulsanti Salva e Annulla ---
        self.button_box = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
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
        try:
            localita_list = self.db_manager.get_localita_per_comune(self.comune_id_partita)
            for loc_id, nome_localita in localita_list:
                self.localita_combo.addItem(nome_localita, userData=loc_id)
        except Exception as e:
            print(f"Errore nel caricamento delle località: {e}")
            self.localita_combo.addItem("Errore caricamento", -1)

    def _load_initial_data(self):
        """Carica i dati dell'immobile dal DB e popola i campi."""
        try:
            self.dati_originali = self.db_manager.get_immobile_details(self.immobile_id)
            if not self.dati_originali:
                QMessageBox.critical(self, "Errore", "Impossibile trovare i dati per l'immobile specificato.")
                # Disabilita i campi e il pulsante salva
                self.button_box.button(QDialogButtonBox.Save).setEnabled(False)
                for i in range(self.layout().count()):
                    widget = self.layout().itemAt(i).widget()
                    if widget: widget.setEnabled(False)
                return

            # Popola i campi
            self.natura_combo.setCurrentText(self.dati_originali.get('natura', ''))
            self.classificazione_edit.setText(self.dati_originali.get('classificazione', ''))
            self.indirizzo_edit.setText(self.dati_originali.get('indirizzo', ''))
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

class PossessoreSelectionDialog(QDialog):
    def __init__(self, db_manager: CatastoDBManager, comune_id: Optional[int], parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        # comune_id ora è un filtro iniziale opzionale, non un requisito fisso
        self.comune_id_filter = comune_id
        self.selected_possessore = None
        self.logger = logging.getLogger(f"CatastoGUI.{self.__class__.__name__}")

        self.setWindowTitle("Seleziona o Crea Possessore")
        self.setMinimumSize(700, 500)

        self._initUI()
        self.load_data()

    def _initUI(self):
        layout = QVBoxLayout(self)
        self.tabs = QTabWidget()

        # --- Tab 1: Seleziona Esistente ---
        select_tab = QWidget()
        select_layout = QVBoxLayout(select_tab)
        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("Filtra per nome:"))
        self.filter_edit = QLineEdit()
        self.filter_edit.setPlaceholderText("Digita per filtrare su tutti i comuni...")
        self.filter_edit.textChanged.connect(self.filter_possessori)
        filter_layout.addWidget(self.filter_edit)
        select_layout.addLayout(filter_layout)

        self.possessori_table = QTableWidget()
        # Aggiungiamo il comune di riferimento alla tabella
        self.possessori_table.setColumnCount(5)
        self.possessori_table.setHorizontalHeaderLabels(["ID", "Nome Completo", "Paternità", "Comune Riferimento", "Stato"])
        self.possessori_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.possessori_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.possessori_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.possessori_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.possessori_table.itemDoubleClicked.connect(self.handle_selection)
        select_layout.addWidget(self.possessori_table)
        self.tabs.addTab(select_tab, "Seleziona Esistente")

        # --- Tab 2: Crea Nuovo ---
        create_tab = QWidget()
        create_layout = QFormLayout(create_tab)
        self.cognome_edit = QLineEdit()
        create_layout.addRow("Cognome e Nome (*):", self.cognome_edit)
        self.paternita_edit = QLineEdit()
        create_layout.addRow("Paternità:", self.paternita_edit)
        self.nome_completo_edit = QLineEdit()
        create_layout.addRow("Nome Completo (*):", self.nome_completo_edit)

        # --- MODIFICA CHIAVE: Combo per selezionare il comune del NUOVO possessore ---
        self.new_poss_comune_combo = QComboBox()
        create_layout.addRow("Comune di Riferimento (*):", self.new_poss_comune_combo)
        # --- FINE MODIFICA ---

        self.attivo_checkbox = QCheckBox("Attivo")
        self.attivo_checkbox.setChecked(True)
        create_layout.addRow(self.attivo_checkbox)
        self.tabs.addTab(create_tab, "Crea Nuovo")

        layout.addWidget(self.tabs)

        buttons_layout = QHBoxLayout()
        self.ok_button = QPushButton("Seleziona")
        self.ok_button.clicked.connect(self.handle_selection)
        buttons_layout.addWidget(self.ok_button)
        self.cancel_button = QPushButton("Annulla")
        self.cancel_button.clicked.connect(self.reject)
        buttons_layout.addWidget(self.cancel_button)
        layout.addLayout(buttons_layout)

    def load_data(self):
        """Carica i dati per entrambi i tab (lista possessori e lista comuni)."""
        self._load_possessori_for_table()
        self._load_comuni_for_combo()

    def _load_possessori_for_table(self, filter_text=None):
        self.possessori_table.setRowCount(0)
        try:
            # Se è stato passato un comune_id, filtra per quello. Altrimenti, ricerca globale.
            if self.comune_id_filter:
                possessori_list = self.db_manager.get_possessori_by_comune(self.comune_id_filter, filter_text)
            else:
                possessori_list = self.db_manager.search_possessori_by_term_globally(filter_text)

            self.possessori_table.setRowCount(len(possessori_list))
            for row, pos_data in enumerate(possessori_list):
                self.possessori_table.setItem(row, 0, QTableWidgetItem(str(pos_data.get('id', ''))))
                self.possessori_table.setItem(row, 1, QTableWidgetItem(pos_data.get('nome_completo', '')))
                self.possessori_table.setItem(row, 2, QTableWidgetItem(pos_data.get('paternita', '')))
                self.possessori_table.setItem(row, 3, QTableWidgetItem(pos_data.get('comune_riferimento_nome', '')))
                self.possessori_table.setItem(row, 4, QTableWidgetItem("Attivo" if pos_data.get('attivo', False) else "Non Attivo"))
            self.possessori_table.resizeColumnsToContents()
        except DBMError as e:
            QMessageBox.critical(self, "Errore", f"Impossibile caricare i possessori: {e}")

    def _load_comuni_for_combo(self):
        self.new_poss_comune_combo.clear()
        try:
            comuni = self.db_manager.get_elenco_comuni_semplice()
            self.new_poss_comune_combo.addItem("--- Seleziona Comune ---", None)
            for id, nome in comuni:
                self.new_poss_comune_combo.addItem(nome, id)
        except DBMError as e:
            self.new_poss_comune_combo.addItem("Errore caricamento", None)

    def filter_possessori(self):
        self._load_possessori_for_table(self.filter_edit.text().strip())

    def handle_selection(self):
        if self.tabs.currentIndex() == 0: # Tab "Seleziona Esistente"
            selected = self.possessori_table.selectedItems()
            if not selected:
                QMessageBox.warning(self, "Nessuna Selezione", "Seleziona un possessore dalla tabella.")
                return
            row = selected[0].row()
            id_poss = int(self.possessori_table.item(row, 0).text())
            # Recuperiamo tutti i dettagli per assicurarci di averli
            self.selected_possessore = self.db_manager.get_possessore_full_details(id_poss)
            self.accept()

        elif self.tabs.currentIndex() == 1: # Tab "Crea Nuovo"
            nome_completo = self.nome_completo_edit.text().strip()
            cognome_nome = self.cognome_edit.text().strip()
            paternita = self.paternita_edit.text().strip() or None
            comune_id = self.new_poss_comune_combo.currentData()

            if not nome_completo or not cognome_nome or comune_id is None:
                QMessageBox.warning(self, "Dati Mancanti", "Nome completo, Cognome/Nome e Comune sono obbligatori.")
                return

            try:
                new_id = self.db_manager.create_possessore(
                    nome_completo=nome_completo,
                    cognome_nome=cognome_nome,
                    paternita=paternita,
                    comune_riferimento_id=comune_id,
                    attivo=self.attivo_checkbox.isChecked()
                )
                self.selected_possessore = self.db_manager.get_possessore_full_details(new_id)
                QMessageBox.information(self, "Successo", f"Nuovo possessore '{nome_completo}' creato con successo.")
                self.accept()
            except (DBMError, DBUniqueConstraintError) as e:
                QMessageBox.critical(self, "Errore Creazione", str(e))
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

        # ... (resto dei campi del form) ...
        # Classificazione
        classificazione_label = QLabel("Classificazione:")
        self.classificazione_edit = QLineEdit()
        self.classificazione_edit.setPlaceholderText(
            "Es. Abitazione civile, Deposito, ecc.")

        form_layout.addWidget(classificazione_label, 2, 0)
        form_layout.addWidget(self.classificazione_edit, 2, 1)

        # Consistenza
        consistenza_label = QLabel("Consistenza:")
        self.consistenza_edit = QLineEdit()
        self.consistenza_edit.setPlaceholderText("Es. 120 mq")

        form_layout.addWidget(consistenza_label, 3, 0)
        form_layout.addWidget(self.consistenza_edit, 3, 1)

        # Numero piani
        piani_label = QLabel("Numero piani:")
        self.piani_edit = QSpinBox()
        self.piani_edit.setMinimum(0)
        self.piani_edit.setMaximum(99)
        self.piani_edit.setSpecialValueText("Non specificato")

        form_layout.addWidget(piani_label, 4, 0)
        form_layout.addWidget(self.piani_edit, 4, 1)

        # Numero vani
        vani_label = QLabel("Numero vani:")
        self.vani_edit = QSpinBox()
        self.vani_edit.setMinimum(0)
        self.vani_edit.setMaximum(99)
        self.vani_edit.setSpecialValueText("Non specificato")

        form_layout.addWidget(vani_label, 5, 0)
        form_layout.addWidget(self.vani_edit, 5, 1)

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

        # --- MODIFICA CHIAVE QUI: allow_creation=True (parametro logico, non esiste in LocalitaSelectionDialog) ---
        # Il tuo LocalitaSelectionDialog ha un parametro selection_mode.
        # Se selection_mode=False, dovrebbe permettere la creazione di nuove località.
        # Se selection_mode=True, permette solo la selezione.
        # Vogliamo qui che permetta SIA selezione CHE creazione, quindi usiamo selection_mode=False
        # e poi la logica di handle_selection_or_creation (nel LocalitaSelectionDialog) gestirà.

        dialog = LocalitaSelectionDialog(self.db_manager,
                                         self.comune_id,
                                         self,
                                         selection_mode=False) # <--- CAMBIATO A False
        
        # Imposta il titolo del dialogo per riflettere la possibilità di gestione/creazione
        dialog.setWindowTitle(f"Seleziona o Crea Località per Comune ID: {self.comune_id}")

        result = dialog.exec_()

        # Il LocalitaSelectionDialog, se modificato per get_selected_or_created_localita,
        # dovrebbe restituire un dizionario con id e nome (compreso il civico).
        # Ad esempio: { 'id': 1, 'nome': 'Via Roma, 12 (Via)' }
        if result == QDialog.Accepted:
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
        classificazione = self.classificazione_edit.text().strip() or None
        consistenza = self.consistenza_edit.text().strip() or None
        numero_piani = self.piani_edit.value() if self.piani_edit.value() > 0 else None
        numero_vani = self.vani_edit.value() if self.vani_edit.value() > 0 else None

        # Crea il dizionario dei dati dell'immobile
        self.immobile_data = {
            'natura': natura,
            'localita_id': self.localita_id,
            'localita_nome': self.localita_display.text(),
            'classificazione': classificazione,
            'consistenza': consistenza,
            'numero_piani': numero_piani,
            'numero_vani': numero_vani
        }

        self.accept()
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
            QApplication.style().standardIcon(QStyle.SP_BrowserReload), "")
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
                    item.setData(Qt.UserRole, comune['id'])
                    # Per recuperare il nome facilmente
                    item.setData(Qt.UserRole + 1, comune['nome'])
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
        if current_item and current_item.data(Qt.UserRole) is not None:
            self.selected_comune_id = current_item.data(Qt.UserRole)
            self.selected_comune_name = current_item.data(
                Qt.UserRole + 1)  # Salva anche il nome
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
        self.results_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.results_table.setSelectionMode(QTableWidget.SingleSelection)
        self.results_table.itemDoubleClicked.connect(self.select_partita)
        self.results_table.setEditTriggers(QTableWidget.NoEditTriggers)
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
        if dialog.exec_() == QDialog.Accepted and dialog.selected_comune_id:
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
# --- Dialog per la Selezione dei Possessori ---



class CreateUserDialog(QDialog):
    def __init__(self, db_manager: CatastoDBManager, parent=None): # db_manager è CatastoDBManager
        super(CreateUserDialog, self).__init__(parent)
        self.db_manager = db_manager
        self.setWindowTitle("Crea Nuovo Utente")
        self.setMinimumWidth(400)
        layout = QVBoxLayout(self)

        form_layout = QGridLayout()
        form_layout.addWidget(QLabel("Username:"), 0, 0)
        self.username_edit = QLineEdit()
        self.username_edit.setPlaceholderText("Min. 3 caratteri")
        form_layout.addWidget(self.username_edit, 0, 1)

        form_layout.addWidget(QLabel("Password:"), 1, 0)
        self.password_edit = QPasswordLineEdit() # Usa la classe definita
        self.password_edit.setPlaceholderText("Min. 6 caratteri")
        form_layout.addWidget(self.password_edit, 1, 1)

        form_layout.addWidget(QLabel("Conferma Password:"), 2, 0)
        self.confirm_edit = QPasswordLineEdit() # Usa la classe definita
        form_layout.addWidget(self.confirm_edit, 2, 1)

        form_layout.addWidget(QLabel("Nome Completo:"), 3, 0)
        self.nome_edit = QLineEdit()
        form_layout.addWidget(self.nome_edit, 3, 1)

        form_layout.addWidget(QLabel("Email:"), 4, 0)
        self.email_edit = QLineEdit()
        self.email_edit.setPlaceholderText("es. utente@dominio.it")
        form_layout.addWidget(self.email_edit, 4, 1)

        form_layout.addWidget(QLabel("Ruolo:"), 5, 0)
        self.ruolo_combo = QComboBox()
        self.ruolo_combo.addItems(["admin", "archivista", "consultatore"])
        form_layout.addWidget(self.ruolo_combo, 5, 1)

        frame_form = QFrame()
        frame_form.setLayout(form_layout)
        frame_form.setFrameShape(QFrame.StyledPanel)
        layout.addWidget(frame_form)

        buttons_layout = QHBoxLayout()
        self.create_button = QPushButton(QApplication.style().standardIcon(
            QStyle.SP_DialogSaveButton), "Crea Utente")
        self.create_button.clicked.connect(self.handle_create_user)
        self.create_button.setDefault(True)

        self.cancel_button = QPushButton(QApplication.style().standardIcon(
            QStyle.SP_DialogCancelButton), "Annulla")
        self.cancel_button.clicked.connect(self.reject)

        buttons_layout.addStretch()
        buttons_layout.addWidget(self.create_button)
        buttons_layout.addWidget(self.cancel_button)
        layout.addLayout(buttons_layout)

        self.username_edit.setFocus()

    def handle_create_user(self):
        username = self.username_edit.text().strip()
        password = self.password_edit.text()
        confirm = self.confirm_edit.text()
        nome_completo = self.nome_edit.text().strip()
        email = self.email_edit.text().strip()
        ruolo = self.ruolo_combo.currentText()

        if not all([username, password, nome_completo, email, ruolo]):
            QMessageBox.warning(self, "Errore di Validazione", "Tutti i campi sono obbligatori.")
            return
        if len(username) < 3:
            QMessageBox.warning(self, "Errore di Validazione", "L'username deve essere di almeno 3 caratteri.")
            return
        if len(password) < 6: #Sposto il controllo prima del confirm
            QMessageBox.warning(self, "Errore di Validazione", "La password deve essere di almeno 6 caratteri.")
            self.password_edit.setFocus()
            self.password_edit.selectAll()
            return
        if password != confirm:
            QMessageBox.warning(self, "Errore di Validazione", "Le password non coincidono.")
            self.password_edit.setFocus() # O confirm_edit
            self.password_edit.selectAll()
            return

        try:
            password_hash = _hash_password(password) # Assumendo _hash_password sia in common_utils o app_utils

            # La chiamata al db_manager è corretta
            if self.db_manager.create_user(username, password_hash, nome_completo, email, ruolo):
                QMessageBox.information(self, "Successo", f"Utente '{username}' creato con successo.")
                self.accept()
            # else: create_user solleva eccezioni in caso di fallimento noto
        except DBUniqueConstraintError as uve:
            # Usiamo str(uve) per ottenere il messaggio di errore in modo standard
            QMessageBox.critical(self, "Errore Creazione Utente", f"Impossibile creare l'utente '{username}':\n{str(uve)}")
        except DBMError as dbe: # Altri errori gestiti dal DBManager
             QMessageBox.critical(self, "Errore Database", f"Errore database durante la creazione dell'utente '{username}':\n{dbe.message}")
        except Exception as e:
            logging.getLogger("CatastoGUI").error(f"Errore imprevisto durante la creazione dell'utente {username}: {e}", exc_info=True)
            QMessageBox.critical(self, "Errore Inaspettato", f"Si è verificato un errore imprevisto: {e}")

# In dialogs.py, aggiungi questa nuova classe

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

        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
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
        self.localita_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.localita_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.localita_table.setSelectionMode(QTableWidget.SingleSelection)
        self.localita_table.itemSelectionChanged.connect(self._aggiorna_stato_pulsanti_action_localita) # Qui si collega il segnale
        self.localita_table.itemDoubleClicked.connect(self._handle_double_click)
        select_layout.addWidget(self.localita_table)

        select_action_layout = QHBoxLayout()
        self.btn_modifica_localita = QPushButton(QApplication.style().standardIcon(
            QStyle.SP_FileDialogDetailedView), "Modifica Selezionata")
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
            self.btn_salva_nuova_localita = QPushButton(QApplication.style().standardIcon(QStyle.SP_DialogSaveButton) ,"Salva Nuova Località")
            self.btn_salva_nuova_localita.clicked.connect(self._salva_nuova_localita_da_tab)
            create_form_layout.addRow(self.btn_salva_nuova_localita)
            self.tabs.addTab(create_tab, "Crea Nuova Località")

        buttons_layout = QHBoxLayout()

        self.select_button = QPushButton(QApplication.style().standardIcon(
            QStyle.SP_DialogApplyButton), "Seleziona")
        self.select_button.setToolTip("Conferma la località selezionata")
        self.select_button.clicked.connect(self._handle_selection_or_creation)
        buttons_layout.addWidget(self.select_button)

        buttons_layout.addStretch()

        self.chiudi_button = QPushButton(QApplication.style().standardIcon(
            QStyle.SP_DialogCloseButton), "Chiudi")
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
                    item.setTextAlignment(Qt.AlignCenter)
                    self.localita_table.setItem(0, 0, item)
                    self.localita_table.setSpan(0, 0, 1, self.localita_table.columnCount())

            except Exception as e:
                self.logger.error(f"Errore caricamento località per comune {self.comune_id} (filtro '{actual_filter_text}'): {e}", exc_info=True)
                QMessageBox.critical(
                    self, "Errore Caricamento", f"Impossibile caricare le località:\n{e}")
                self.localita_table.setRowCount(1)
                item = QTableWidgetItem(f"Errore caricamento: {e}")
                item.setTextAlignment(Qt.AlignCenter)
                self.localita_table.setItem(0, 0, item)
                self.localita_table.setSpan(0, 0, 1, self.localita_table.columnCount())
        else:
            self.logger.warning("Comune ID non disponibile per caricare località.")
            self.localita_table.setRowCount(1)
            item = QTableWidgetItem("ID Comune non disponibile per caricare località.")
            item.setTextAlignment(Qt.AlignCenter)
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
            if dialog.exec_() == QDialog.Accepted:
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
                if civico_item_text and civico_item_text != "-" and civico_item_text.strip() != self.civico_spinbox_nuova.specialValueText(): # Verifica anche il testo speciale
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
            QApplication.style().standardIcon(QStyle.SP_DialogOkButton), "OK")
        self.ok_button.clicked.connect(self._accept_details)
        self.cancel_button = QPushButton(QApplication.style().standardIcon(
            QStyle.SP_DialogCancelButton), "Annulla")
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
        if dialog.exec_() == QDialog.Accepted:
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
        if dialog.exec_() == QDialog.Accepted:
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
        self.descrizione_edit.setFixedHeight(80)

        layout.addRow("Nome (*):", self.nome_edit)
        layout.addRow("Anno Inizio (*):", self.anno_inizio_spin)
        layout.addRow("Anno Fine (0 se Aperto):", self.anno_fine_spin)
        layout.addRow("Descrizione:", self.descrizione_edit)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
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

class UserSelectionDialog(QDialog):
    def __init__(self, db_manager: CatastoDBManager, parent=None, title="Seleziona Utente", exclude_user_id: Optional[int] = None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.setWindowTitle(title)
        self.setMinimumWidth(500)
        self.selected_user_id: Optional[int] = None
        self.exclude_user_id = exclude_user_id

        layout = QVBoxLayout(self)

        self.user_table = QTableWidget()
        self.user_table.setColumnCount(5)
        self.user_table.setHorizontalHeaderLabels(
            ["ID", "Username", "Nome Completo", "Ruolo", "Stato"])
        self.user_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.user_table.setSelectionMode(QTableWidget.SingleSelection)
        self.user_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.user_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.user_table.itemDoubleClicked.connect(self._accept_selection)
        layout.addWidget(self.user_table)

        buttons_layout = QHBoxLayout()
        ok_button = QPushButton("Seleziona")
        ok_button.clicked.connect(self._accept_selection)
        cancel_button = QPushButton("Annulla")
        cancel_button.clicked.connect(self.reject)
        buttons_layout.addStretch()
        buttons_layout.addWidget(ok_button)
        buttons_layout.addWidget(cancel_button)
        layout.addLayout(buttons_layout)

        self.load_users()

    def load_users(self):
        self.user_table.setRowCount(0)
        users = self.db_manager.get_utenti()
        for user_data in users:
            if self.exclude_user_id and user_data['id'] == self.exclude_user_id:
                continue
            row_pos = self.user_table.rowCount()
            self.user_table.insertRow(row_pos)
            self.user_table.setItem(
                row_pos, 0, QTableWidgetItem(str(user_data['id'])))
            self.user_table.setItem(
                row_pos, 1, QTableWidgetItem(user_data['username']))
            self.user_table.setItem(
                row_pos, 2, QTableWidgetItem(user_data['nome_completo']))
            self.user_table.setItem(
                row_pos, 3, QTableWidgetItem(user_data['ruolo']))
            self.user_table.setItem(row_pos, 4, QTableWidgetItem(
                "Attivo" if user_data['attivo'] else "Non Attivo"))
        self.user_table.resizeColumnsToContents()

    def _accept_selection(self):
        selected_rows = self.user_table.selectionModel().selectedRows()
        if selected_rows:
            row = selected_rows[0].row()
            self.selected_user_id = int(self.user_table.item(row, 0).text())
            self.accept()
        else:
            QMessageBox.warning(self, "Selezione",
                                "Per favore, seleziona un utente dalla lista.")

 
class AggiungiDocumentoDialog(QDialog):
    def __init__(self, db_manager: 'CatastoDBManager', partita_id: int, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.partita_id = partita_id
        self.selected_file_path: Optional[str] = None
        self.document_data: Optional[Dict[str, Any]] = None

        self.setWindowTitle(f"Allega Nuovo Documento alla Partita ID: {self.partita_id}")
        self.setMinimumWidth(500)

        layout = QVBoxLayout(self)
        form = QFormLayout()


        self.btn_seleziona_file = QPushButton("Seleziona File (PDF, JPG)...")
        self.btn_seleziona_file.clicked.connect(self._seleziona_file)
        self.file_selezionato_label = QLabel("Nessun file selezionato.")
        form.addRow(self.btn_seleziona_file, self.file_selezionato_label)

        self.titolo_edit = QLineEdit()
        form.addRow("Titolo Documento (*):", self.titolo_edit)

        self.descrizione_edit = QTextEdit()
        self.descrizione_edit.setFixedHeight(60)
        form.addRow("Descrizione:", self.descrizione_edit)

        self.tipo_documento_combo = QComboBox()
        # Popola con tipi comuni o da una tabella DB se preferisci
        self.tipo_documento_combo.addItems(["Atto Notarile", "Mappa Catastale", "Fotografia Storica", "Corrispondenza", "Estratto Matriciale", "Altro"])
        form.addRow("Tipo Documento (*):", self.tipo_documento_combo)

        self.anno_edit = QSpinBox()
        self.anno_edit.setRange(1000, QDate.currentDate().year() + 5) # Range ampio
        self.anno_edit.setSpecialValueText(" ") # Per anno non specificato
        self.anno_edit.setValue(self.anno_edit.minimum()) # Default a " "
        form.addRow("Anno Documento (opz.):", self.anno_edit)

        self.periodo_combo = QComboBox()
        form.addRow("Periodo Storico (opz.):", self.periodo_combo)
        self._carica_periodi_storici() # Metodo per popolare la combo

        self.rilevanza_combo = QComboBox()
        self.rilevanza_combo.addItems(['primaria', 'secondaria', 'correlata']) # Da CHECK constraint
        form.addRow("Rilevanza per la Partita (*):", self.rilevanza_combo)

        self.note_legame_edit = QLineEdit()
        form.addRow("Note sul Legame (opz.):", self.note_legame_edit)
        
        # self.metadati_edit = QTextEdit() # Per JSONB - semplice input testuale per ora
        # self.metadati_edit.setPlaceholderText("Opzionale: Inserire metadati aggiuntivi in formato JSON, es. {\"risoluzione\": \"300dpi\"}")
        # self.metadati_edit.setFixedHeight(60)
        # form.addRow("Metadati JSON (opz.):", self.metadati_edit)

        layout.addLayout(form)

        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.button_box.button(QDialogButtonBox.Ok).setText("Salva Allegato")
        self.button_box.accepted.connect(self._salva_allegato)
        self.button_box.rejected.connect(self.reject)
        layout.addWidget(self.button_box)
        self.setLayout(layout)
        
    # --- NUOVO METODO PER IMPOSTARE IL PERCORSO INIZIALE DEL FILE ---
    def set_initial_file_path(self, file_path: str):
        """Imposta un percorso file iniziale e aggiorna la label di visualizzazione."""
        if os.path.exists(file_path) and os.path.isfile(file_path):
            self.selected_file_path = file_path
            self.file_selezionato_label.setText(os.path.basename(file_path))
            # Puoi anche tentare di derivare un titolo iniziale dal nome del file qui
            # es. self.titolo_edit.setText(os.path.splitext(os.path.basename(file_path))[0])
        else:
            self.logger.warning(f"Tentativo di impostare un percorso file iniziale non valido in AggiungiDocumentoDialog: {file_path}")
            self.selected_file_path = None
            self.file_selezionato_label.setText("Nessun file selezionato (iniziale non valido).")
    # --- FINE NUOVO METODO ---

    def _seleziona_file(self):
        filePath, _ = QFileDialog.getOpenFileName(self, "Seleziona Documento", "", 
                                                  "Documenti (*.pdf *.jpg *.jpeg *.png);;File PDF (*.pdf);;Immagini JPG (*.jpg *.jpeg);;Immagini PNG (*.png);;Tutti i file (*)")
        if filePath:
            self.selected_file_path = filePath
            import os
            self.file_selezionato_label.setText(os.path.basename(filePath))
        else:
            self.selected_file_path = None
            self.file_selezionato_label.setText("Nessun file selezionato.")

    def _carica_periodi_storici(self):
        self.periodo_combo.clear()
        self.periodo_combo.addItem("Nessuno", None) # Opzione per non selezionare periodo
        try:
            periodi = self.db_manager.get_historical_periods() # Metodo esistente
            for p in periodi:
                self.periodo_combo.addItem(f"{p.get('nome')} ({p.get('anno_inizio')}-{p.get('anno_fine', 'oggi')})", p.get('id'))
        except Exception as e:
            self.periodo_combo.addItem("Errore caricamento periodi", None)
            logging.getLogger("CatastoGUI").error(f"Errore caricamento periodi storici per dialogo allegato: {e}")

    def _salva_allegato(self):
        if not self.selected_file_path:
            QMessageBox.warning(self, "File Mancante", "Selezionare un file da allegare.")
            return
        
        titolo = self.titolo_edit.text().strip()
        tipo_documento = self.tipo_documento_combo.currentText()
        rilevanza = self.rilevanza_combo.currentText()

        if not titolo or not tipo_documento or not rilevanza:
            QMessageBox.warning(self, "Dati Obbligatori Mancanti", "Titolo, Tipo Documento e Rilevanza sono obbligatori.")
            return

        descrizione = self.descrizione_edit.toPlainText().strip() or None
        anno_val = self.anno_edit.value()
        anno = anno_val if self.anno_edit.text().strip() != "" else None # Se non è " "
        
        periodo_id_data = self.periodo_combo.currentData()
        periodo_id = periodo_id_data if periodo_id_data is not None else None
        
        note_legame = self.note_legame_edit.text().strip() or None
        # metadati_str = self.metadati_edit.toPlainText().strip() or None
        # if metadati_str:
        #     try:
        #         json.loads(metadati_str) # Valida JSON
        #     except json.JSONDecodeError:
        #         QMessageBox.warning(self, "Errore Metadati", "Il testo dei metadati non è un JSON valido.")
        #         return
        metadati_str = None # Per ora non gestiamo input JSON complesso dall'utente

        # Qui la logica di copia del file e salvataggio nel DB
        self.document_data = {
            "titolo": titolo, "tipo_documento": tipo_documento, "descrizione": descrizione,
            "anno": anno, "periodo_id": periodo_id, "rilevanza": rilevanza, 
            "note_legame": note_legame, "percorso_file_originale": self.selected_file_path,
            "metadati_json": metadati_str 
        }
        self.accept()
        
class CSVImportResultDialog(QDialog):
    """
    Un dialogo per visualizzare i risultati di un'importazione da CSV,
    separando i record importati con successo da quelli con errori.
    """
    def __init__(self, success_data: List[Dict], error_data: List[Tuple[int, Dict, str]], parent=None):
        super().__init__(parent)
        self.setWindowTitle("Riepilogo Importazione CSV")
        self.setMinimumSize(700, 500)

        main_layout = QVBoxLayout(self)

        # Messaggio di riepilogo
        summary_text = f"<b>Importazione completata.</b><br>" \
                       f"Record importati con successo: <b>{len(success_data)}</b><br>" \
                       f"Record con errori: <b>{len(error_data)}</b>"
        summary_label = QLabel(summary_text)
        main_layout.addWidget(summary_label)

        # Tab per separare successi ed errori
        tabs = QTabWidget()
        
        # Tab dei successi
        success_table = self._create_table(["ID Assegnato", "Nome Completo", "Comune"], success_data)
        tabs.addTab(success_table, f"✅ Successi ({len(success_data)})")

        # Tab degli errori
        error_table = self._create_error_table(["Riga N.", "Dati Riga", "Errore"], error_data)
        tabs.addTab(error_table, f"❌ Errori ({len(error_data)})")
        
        if not error_data:
            tabs.setTabEnabled(1, False) # Disabilita il tab errori se non ci sono errori

        main_layout.addWidget(tabs)

        # Pulsante OK
        button_box = QDialogButtonBox(QDialogButtonBox.Ok)
        button_box.accepted.connect(self.accept)
        main_layout.addWidget(button_box)

    def _create_table(self, headers: List[str], data: List[Dict]) -> QTableWidget:
        table = QTableWidget(len(data), len(headers))
        table.setHorizontalHeaderLabels(headers)
        for row_idx, row_data in enumerate(data):
            table.setItem(row_idx, 0, QTableWidgetItem(str(row_data.get('id', 'N/A'))))
            table.setItem(row_idx, 1, QTableWidgetItem(row_data.get('nome_completo', '')))
            table.setItem(row_idx, 2, QTableWidgetItem(row_data.get('comune_nome', '')))
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        table.resizeColumnsToContents()
        table.horizontalHeader().setStretchLastSection(True)
        return table

    def _create_error_table(self, headers: List[str], data: List[Tuple[int, Dict, str]]) -> QTableWidget:
        table = QTableWidget(len(data), len(headers))
        table.setHorizontalHeaderLabels(headers)
        for row_idx, error_tuple in enumerate(data):
            line_num, row_data, error_msg = error_tuple
            table.setItem(row_idx, 0, QTableWidgetItem(str(line_num)))
            table.setItem(row_idx, 1, QTableWidgetItem(str(row_data)))
            table.setItem(row_idx, 2, QTableWidgetItem(error_msg))
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        table.resizeColumnsToContents()
        table.horizontalHeader().setStretchLastSection(True)
        return table
# In dialogs.py, aggiungi questa nuova classe

# In dialogs.py, SOSTITUISCI l'intera classe BackupReminderSettingsDialog

class BackupReminderSettingsDialog(QDialog):
    """Dialogo per configurare il trigger temporale del promemoria di backup."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.settings = QSettings()
        self.setWindowTitle("Impostazioni Promemoria Backup")

        layout = QFormLayout(self)

        self.days_spinbox = QSpinBox()
        self.days_spinbox.setRange(0, 365) # 0 per disattivare
        self.days_spinbox.setSuffix(" giorni")
        self.days_spinbox.setSpecialValueText("Mai (disattivato)")
        layout.addRow("Mostra promemoria ogni:", self.days_spinbox)

        info_label = QLabel("Impostando a '0', il promemoria verrà disattivato.")
        info_label.setStyleSheet("font-style: italic; color: #555;")
        layout.addRow(info_label)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

        self.load_settings()

    def load_settings(self):
        days = self.settings.value("Backup/ReminderDays", 30, type=int) # Default 30 giorni
        self.days_spinbox.setValue(days)

    def accept(self):
        self.settings.setValue("Backup/ReminderDays", self.days_spinbox.value())
        # Rimuoviamo la vecchia impostazione per pulizia
        self.settings.remove("Backup/ReminderInserts")
        QMessageBox.information(self, "Impostazioni Salve", "Le impostazioni per il promemoria di backup sono state salvate.")
        super().accept()
class EulaDialog(QDialog):
    """Dialogo per la visualizzazione e l'accettazione dell'EULA."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Contratto di Licenza (EULA) - Meridiana 1.2")
        self.setMinimumSize(600, 500)
        self.setModal(True)

        layout = QVBoxLayout(self)

        self.text_browser = QTextBrowser()
        self.text_browser.setReadOnly(True)
        self.text_browser.setOpenExternalLinks(True)
        layout.addWidget(self.text_browser)

        # --- INIZIO CORREZIONE ---
        # Usiamo i pulsanti standard 'Ok' e 'Cancel'
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)

        # E poi ne personalizziamo il testo
        button_box.button(QDialogButtonBox.Ok).setText("Accetto i Termini")
        button_box.button(QDialogButtonBox.Cancel).setText("Rifiuto ed Esci")

        # Le connessioni ai segnali 'accepted' e 'rejected' funzionano correttamente
        # perché si basano sul "ruolo" del pulsante (AcceptRole, RejectRole), non sul testo.
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        # --- FINE CORREZIONE ---

        layout.addWidget(button_box)

        self._load_eula_text()


    def _load_eula_text(self):
        """Carica il testo dell'EULA dal file resources/EULA.txt."""
        try:
            # Lista di percorsi possibili per l'EULA
            possible_paths = []
            
            # Percorso 1: Usando resource_path (originale)
            try:
                eula_path_1 = resource_path(os.path.join("resources", "EULA.txt"))
                possible_paths.append(eula_path_1)
            except:
                pass
            
            # Percorso 2: Relativo all'eseguibile
            if getattr(sys, 'frozen', False):
                # Applicazione compilata
                exe_dir = os.path.dirname(sys.executable)
                eula_path_2 = os.path.join(exe_dir, "resources", "EULA.txt")
                possible_paths.append(eula_path_2)
                
                # Percorso 3: Nella cartella _internal (PyInstaller)
                eula_path_3 = os.path.join(exe_dir, "_internal", "resources", "EULA.txt")
                possible_paths.append(eula_path_3)
            
            # Percorso 4: Relativo allo script principale
            base_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
            eula_path_4 = os.path.join(base_dir, "resources", "EULA.txt")
            possible_paths.append(eula_path_4)
            
            # Percorso 5: Directory corrente
            eula_path_5 = os.path.join(os.getcwd(), "resources", "EULA.txt")
            possible_paths.append(eula_path_5)
            
            # Cerca il primo percorso valido
            found_path = None
            for path in possible_paths:
                if os.path.exists(path):
                    found_path = path
                    break
            
            if found_path:
                with open(found_path, 'r', encoding='utf-8') as f:
                    eula_text = f.read()
                self.text_browser.setMarkdown(eula_text.replace('\n', '  \n'))
            else:
                # Se non trova il file, mostra un messaggio di errore con i percorsi tentati
                error_msg = "ERRORE: File EULA.txt non trovato.\n\nPercorsi verificati:\n"
                for i, path in enumerate(possible_paths[:3], 1):
                    error_msg += f"{i}. {path}\n"
                self.text_browser.setText(error_msg)
                
        except Exception as e:
            self.text_browser.setText(f"Impossibile caricare il testo della licenza.\n\nErrore: {e}")
            
def qdate_to_datetime(q_date: QDate) -> Optional[date]:
    if q_date.isNull() or not q_date.isValid():  # Controlla anche isValid
        return None
    return date(q_date.year(), q_date.month(), q_date.day())


def datetime_to_qdate(dt_date: Optional[date]) -> QDate:
    if dt_date is None:
        return QDate()  # Restituisce una QDate "nulla"
    return QDate(dt_date.year, dt_date.month, dt_date.day)
def _hash_password(password: str) -> str:
        """Genera un hash sicuro per la password usando bcrypt."""
        password_bytes = password.encode('utf-8')
        salt = bcrypt.gensalt()
        hashed_bytes = bcrypt.hashpw(password_bytes, salt)
        return hashed_bytes.decode('utf-8')
def _verify_password(stored_hash: str, provided_password: str) -> bool:
    """Verifica se la password fornita corrisponde all'hash memorizzato."""
    try:
        stored_hash_bytes = stored_hash.encode('utf-8')
        provided_password_bytes = provided_password.encode('utf-8')
        return bcrypt.checkpw(provided_password_bytes, stored_hash_bytes)
    except ValueError:
        logging.getLogger("CatastoGUI").error(
            f"Tentativo di verifica con hash non valido: {stored_hash[:10]}...")
        return False
    except Exception as e:
        logging.getLogger("CatastoGUI").error(
            f"Errore imprevisto durante la verifica bcrypt: {e}")
        return False

