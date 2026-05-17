"""
dialogs_admin.py — Dialog di amministrazione e configurazione sistema.

Classi estratte da dialogs.py:
  DBConfigDialog, DocumentViewerDialog, CreateUserDialog, UserSelectionDialog,
  BackupReminderSettingsDialog, EulaDialog, SMTPSettingsDialog, HelpViewerDialog,
  LicenseDialog
"""
from __future__ import annotations

import logging
import os
import sys
from datetime import date
from typing import Optional, Dict, Any

from PyQt6.QtCore import (QDate, QSettings, Qt)
from PyQt6.QtGui import (QDesktopServices, QFont, QPixmap)
from PyQt6.QtPdf import QPdfDocument
from PyQt6.QtPdfWidgets import QPdfView
from PyQt6.QtWidgets import (QAbstractItemView, QApplication,
                             QCheckBox, QComboBox, QDialog,
                             QFileDialog, QFormLayout, QFrame, QGridLayout, QGroupBox,
                             QHBoxLayout, QHeaderView, QLabel, QLineEdit,
                             QMessageBox, QPushButton, QSpinBox, QStyle,
                             QSplitter, QTableWidget, QTableWidgetItem,
                             QTreeWidget, QTreeWidgetItem, QVBoxLayout,
                             QWidget, QTextBrowser, QDialogButtonBox,
                             QRadioButton, QGraphicsScene, QGraphicsView)
from PyQt6.QtGui import QPainter
from app_paths import get_resource_path, get_resource_path as resource_path, get_doc_path  # noqa: F401
from config import (
    SETTINGS_DB_TYPE, SETTINGS_DB_HOST, SETTINGS_DB_PORT,
    SETTINGS_DB_NAME, SETTINGS_DB_USER, SETTINGS_DB_SCHEMA, SETTINGS_DB_PASSWORD,
    SETTINGS_SMTP_ENABLED, SETTINGS_SMTP_HOST, SETTINGS_SMTP_PORT,
    SETTINGS_SMTP_USER, SETTINGS_SMTP_USE_TLS, SETTINGS_SMTP_FROM_ADDR,
    SETTINGS_EMAIL_ON_CREATE, SETTINGS_EMAIL_ON_PASSWD,
    SETTINGS_EMAIL_ON_ROLE, SETTINGS_EMAIL_ON_LOGIN,
    SETTINGS_LICENSE_FILE_PATH, SETTINGS_LICENSE_NETWORK_SHARE,
)
from catasto_db_manager import CatastoDBManager
from catasto_exceptions import DBMError, DBUniqueConstraintError, DBNotFoundError, DBDataError  # noqa: F401
from foliarium.ui.widgets.custom import QPasswordLineEdit, show_status_message as _show_status_message
from core.auth_manager import AuthManager as _AuthManager

def _verify_password(stored_hash: str, provided_password: str) -> bool:
    return _AuthManager._verify_password(stored_hash, provided_password)

try:
    import keyring
except ImportError:
    keyring = None

try:
    import markdown
except ImportError:
    markdown = None

try:
    import yaml
except ImportError:
    yaml = None

class DBConfigDialog(QDialog):
    def __init__(self, parent=None, initial_config: Optional[Dict] = None):
        super().__init__(parent)
        self.logger = logging.getLogger(f"CatastoGUI.{self.__class__.__name__}")
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
        
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel, self)
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Testa e Salva")
        buttons.accepted.connect(self._handle_save_and_connect)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        emergency_group = QGroupBox("Operazioni di Emergenza")
        emergency_layout = QHBoxLayout(emergency_group)

        emergency_label = QLabel("Usare solo se il database principale è corrotto o inaccessibile.")
        emergency_label.setWordWrap(True)

        self.btn_emergency_restore = QPushButton(QApplication.style().standardIcon(QStyle.StandardPixmap.SP_DialogResetButton), " Ripristina Database da Backup...")
        self.btn_emergency_restore.clicked.connect(self._handle_emergency_restore)

        emergency_layout.addWidget(emergency_label, 1)
        emergency_layout.addWidget(self.btn_emergency_restore)

        layout.addWidget(emergency_group)

        
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
        
        # Usiamo il metodo corretto per testare la connessione e inizializzare il pool
        if test_db_manager.initialize_main_pool():
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
                        keyring.set_password(f"foliarium_db_{config['host']}", config['user'], config['password'])
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
        # Chiudi il dialogo con QDialog.DialogCode.Rejected.
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
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply != QMessageBox.StandardButton.Yes:
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
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)

        if reply2 != QMessageBox.StandardButton.Yes:
            return

        # Crea un DB Manager temporaneo per l'operazione
        emergency_db_manager = CatastoDBManager(
            host=config["host"], port=config["port"],
            dbname=config["dbname"], user=config["user"],
            password=config["password"]
        )

        # Esegui l'operazione
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
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
        if self.local_radio.isChecked():
            db_type_val = "local"
            host_val = "localhost"
        else:
            db_type_val = "remote"
            host_val = self.host_edit.text().strip()

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

        # Toolbar zoom PDF (visibile solo quando si carica un PDF)
        self.pdf_toolbar = QWidget()
        toolbar_layout = QHBoxLayout(self.pdf_toolbar)
        toolbar_layout.setContentsMargins(4, 4, 4, 4)
        self.btn_zoom_out = QPushButton("−")
        self.btn_zoom_out.setToolTip("Riduci zoom")
        self.zoom_label = QLabel("100%")
        self.zoom_label.setMinimumWidth(50)
        self.zoom_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.btn_zoom_in = QPushButton("+")
        self.btn_zoom_in.setToolTip("Aumenta zoom")
        self.btn_fit = QPushButton("Adatta")
        self.btn_fit.setToolTip("Adatta alla larghezza della finestra")
        toolbar_layout.addWidget(self.btn_zoom_out)
        toolbar_layout.addWidget(self.zoom_label)
        toolbar_layout.addWidget(self.btn_zoom_in)
        toolbar_layout.addWidget(self.btn_fit)
        toolbar_layout.addStretch()
        self.pdf_toolbar.setVisible(False)

        self.viewer_widget = QWidget()
        self.viewer_layout = QVBoxLayout(self.viewer_widget)
        self.viewer_layout.setContentsMargins(0, 0, 0, 0)

        button_layout = QHBoxLayout()
        self.close_button = QPushButton("Chiudi")
        self.close_button.clicked.connect(self.accept)
        button_layout.addStretch()
        button_layout.addWidget(self.close_button)
        button_layout.addStretch()

        main_layout.addWidget(self.pdf_toolbar)
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
            self.pdf_document = QPdfDocument(self)
            status = self.pdf_document.load(self.file_path)
            if status != QPdfDocument.Status.Ready:
                raise RuntimeError(f"Errore caricamento documento: {status.name}")

            self.pdf_view = QPdfView(self)
            self.pdf_view.setDocument(self.pdf_document)
            self.pdf_view.setPageMode(QPdfView.PageMode.MultiPage)
            self.pdf_view.setZoomMode(QPdfView.ZoomMode.FitInView)
            self._pdf_zoom = 1.0
            self.viewer_layout.addWidget(self.pdf_view)

            # Attiva toolbar zoom
            self.pdf_toolbar.setVisible(True)
            self.btn_zoom_in.clicked.connect(self._pdf_zoom_in)
            self.btn_zoom_out.clicked.connect(self._pdf_zoom_out)
            self.btn_fit.clicked.connect(self._pdf_zoom_fit)
            self._update_zoom_label()

            self.logger.info(f"PDF caricato con QPdfDocument ({self.pdf_document.pageCount()} pagine): {self.file_path}")
        except Exception as e:
            self.logger.error(f"Errore durante il caricamento del PDF: {e}", exc_info=True)
            QMessageBox.critical(self, "Errore PDF", f"Impossibile visualizzare il PDF.\n{e}")
            self.viewer_layout.addWidget(QLabel("Errore nel caricamento del PDF."))

    def _pdf_zoom_in(self):
        self._pdf_zoom = min(self._pdf_zoom * 1.25, 5.0)
        self.pdf_view.setZoomMode(QPdfView.ZoomMode.Custom)
        self.pdf_view.setZoomFactor(self._pdf_zoom)
        self._update_zoom_label()

    def _pdf_zoom_out(self):
        self._pdf_zoom = max(self._pdf_zoom / 1.25, 0.1)
        self.pdf_view.setZoomMode(QPdfView.ZoomMode.Custom)
        self.pdf_view.setZoomFactor(self._pdf_zoom)
        self._update_zoom_label()

    def _pdf_zoom_fit(self):
        self.pdf_view.setZoomMode(QPdfView.ZoomMode.FitInView)
        self._pdf_zoom = self.pdf_view.zoomFactor()
        self._update_zoom_label()

    def _update_zoom_label(self):
        self.zoom_label.setText(f"{int(self._pdf_zoom * 100)}%")
            
    def _load_image(self):
        try:
            self.graphics_scene = QGraphicsScene(self)
            self.graphics_view = QGraphicsView(self.graphics_scene, self)
            self.graphics_view.setRenderHint(QPainter.RenderHint.Antialiasing)
            self.graphics_view.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
            self.graphics_view.setCacheMode(QGraphicsView.CacheModeFlag.CacheBackground)
            self.graphics_view.setViewportUpdateMode(QGraphicsView.ViewportUpdateMode.BoundingRectViewportUpdate)
            self.graphics_view.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)

            pixmap = QPixmap(str(self.file_path))
            if pixmap.isNull():
                raise ValueError(f"Impossibile caricare immagine da: {self.file_path}")

            self.pixmap_item = self.graphics_scene.addPixmap(pixmap)
            self.graphics_view.fitInView(self.pixmap_item, Qt.AspectRatioMode.KeepAspectRatio)
            self.graphics_view.setAlignment(Qt.AlignmentFlag.AlignCenter)

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
        frame_form.setFrameShape(QFrame.Shape.StyledPanel)
        layout.addWidget(frame_form)

        buttons_layout = QHBoxLayout()
        self.create_button = QPushButton(QApplication.style().standardIcon(
            QStyle.StandardPixmap.SP_DialogSaveButton), "Crea Utente")
        self.create_button.clicked.connect(self.handle_create_user)
        self.create_button.setDefault(True)

        self.cancel_button = QPushButton(QApplication.style().standardIcon(
            QStyle.StandardPixmap.SP_DialogCancelButton), "Annulla")
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
        pwd_ok, pwd_err = _validate_password_strength(password)
        if not pwd_ok:
            QMessageBox.warning(self, "Errore di Validazione", pwd_err)
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
        self.user_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.user_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.user_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.user_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
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
        info_label.setObjectName("hintLabel")
        layout.addRow(info_label)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
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
        _show_status_message("Impostazioni promemoria backup salvate.", 4000)
        super().accept()

class EulaDialog(QDialog):
    """Dialogo per la visualizzazione e l'accettazione dell'EULA."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Contratto di Licenza (EULA) - Foliarium")
        self.setMinimumSize(600, 500)
        self.setModal(True)

        layout = QVBoxLayout(self)

        self.text_browser = QTextBrowser()
        self.text_browser.setReadOnly(True)
        self.text_browser.setOpenExternalLinks(True)
        layout.addWidget(self.text_browser)

        # Usiamo i pulsanti standard 'Ok' e 'Cancel'
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)

        # E poi ne personalizziamo il testo
        button_box.button(QDialogButtonBox.StandardButton.Ok).setText("Accetto i Termini")
        button_box.button(QDialogButtonBox.StandardButton.Cancel).setText("Rifiuto ed Esci")

        # Le connessioni ai segnali 'accepted' e 'rejected' funzionano correttamente
        # perché si basano sul "ruolo" del pulsante (AcceptRole, RejectRole), non sul testo.
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)

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
def _validate_password_strength(password: str) -> tuple:
    """Verifica i requisiti minimi della password.
    Restituisce (True, '') se valida, oppure (False, messaggio_errore).
    Requisiti: almeno 8 caratteri, almeno 1 cifra.
    """
    if len(password) < 8:
        return False, "La password deve essere di almeno 8 caratteri."
    if not any(c.isdigit() for c in password):
        return False, "La password deve contenere almeno un numero."
    return True, ""


# Hash/verifica password: logica centralizzata in core.auth_manager (_AuthManager importato a riga 44)
def _hash_password(password: str) -> str:
    """Genera un hash sicuro per la password usando bcrypt."""
    return _AuthManager._hash_password(password)

def _verify_password(stored_hash: str, provided_password: str) -> bool:
    """Verifica se la password fornita corrisponde all'hash memorizzato."""
    return _AuthManager._verify_password(stored_hash, provided_password)


# ---------------------------------------------------------------------------
# Import comuni e località da CSV / ISTAT
# ---------------------------------------------------------------------------


# Estratto in import_dialogs.py — backward compat re-export


# ---------------------------------------------------------------------------
# SMTPSettingsDialog — Impostazioni notifiche email
# ---------------------------------------------------------------------------

class SMTPSettingsDialog(QDialog):
    """
    Finestra di configurazione SMTP per le notifiche email.
    Accessibile da Impostazioni → Notifiche Email...

    La password SMTP viene salvata in keyring (non in QSettings).
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Impostazioni Notifiche Email")
        self.setMinimumWidth(440)
        self._settings = QSettings()
        self._email_worker = None
        self._initUI()
        self._load_settings()

    def _initUI(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # --- Abilita notifiche ---
        self.enabled_check = QCheckBox("Abilita notifiche email")
        layout.addWidget(self.enabled_check)

        # --- Server SMTP ---
        smtp_group = QGroupBox("Server SMTP")
        smtp_form = QFormLayout(smtp_group)
        smtp_form.setSpacing(8)

        self.host_edit = QLineEdit()
        self.host_edit.setPlaceholderText("es. smtp.gmail.com")
        smtp_form.addRow("Host:", self.host_edit)

        porta_layout = QHBoxLayout()
        self.port_spin = QSpinBox()
        self.port_spin.setRange(1, 65535)
        self.port_spin.setValue(587)
        self.port_spin.setMinimumWidth(80)
        self.tls_check = QCheckBox("Usa TLS (STARTTLS)")
        self.tls_check.setChecked(True)
        porta_layout.addWidget(self.port_spin)
        porta_layout.addWidget(self.tls_check)
        porta_layout.addStretch()
        smtp_form.addRow("Porta:", porta_layout)

        self.user_edit = QLineEdit()
        self.user_edit.setPlaceholderText("es. noreply@archivio.it")
        smtp_form.addRow("Utente:", self.user_edit)

        self.password_edit = QPasswordLineEdit()
        self.password_edit.setPlaceholderText("Password account SMTP")
        smtp_form.addRow("Password:", self.password_edit)

        self.from_edit = QLineEdit()
        self.from_edit.setPlaceholderText("es. Foliarium <noreply@archivio.it>")
        smtp_form.addRow("Indirizzo mittente:", self.from_edit)

        layout.addWidget(smtp_group)

        # --- Notifiche attive ---
        notify_group = QGroupBox("Invia notifica quando...")
        notify_layout = QVBoxLayout(notify_group)
        self.chk_create = QCheckBox("Creazione account")
        self.chk_passwd = QCheckBox("Cambio password")
        self.chk_role   = QCheckBox("Cambio ruolo")
        self.chk_login  = QCheckBox("Accesso (login)")
        for chk in (self.chk_create, self.chk_passwd, self.chk_role, self.chk_login):
            chk.setChecked(True)
            notify_layout.addWidget(chk)
        layout.addWidget(notify_group)

        # --- Test + label esito ---
        test_layout = QHBoxLayout()
        self.btn_test = QPushButton("Test connessione")
        self.btn_test.clicked.connect(self._test_connection)
        self.test_label = QLabel("")
        test_layout.addWidget(self.btn_test)
        test_layout.addWidget(self.test_label)
        test_layout.addStretch()
        layout.addLayout(test_layout)

        # --- OK / Annulla ---
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._save_and_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    # ------------------------------------------------------------------

    def _load_settings(self):
        s = self._settings
        self.enabled_check.setChecked(s.value(SETTINGS_SMTP_ENABLED, False, type=bool))
        self.host_edit.setText(s.value(SETTINGS_SMTP_HOST, "", type=str))
        self.port_spin.setValue(s.value(SETTINGS_SMTP_PORT, 587, type=int))
        self.user_edit.setText(s.value(SETTINGS_SMTP_USER, "", type=str))
        self.tls_check.setChecked(s.value(SETTINGS_SMTP_USE_TLS, True, type=bool))
        self.from_edit.setText(s.value(SETTINGS_SMTP_FROM_ADDR, "", type=str))
        self.chk_create.setChecked(s.value(SETTINGS_EMAIL_ON_CREATE, True, type=bool))
        self.chk_passwd.setChecked(s.value(SETTINGS_EMAIL_ON_PASSWD, True, type=bool))
        self.chk_role.setChecked(s.value(SETTINGS_EMAIL_ON_ROLE, True, type=bool))
        self.chk_login.setChecked(s.value(SETTINGS_EMAIL_ON_LOGIN, True, type=bool))
        # Password da keyring
        user = self.user_edit.text()
        if user and keyring:
            pwd = keyring.get_password("Foliarium_SMTP", user) or ""
            self.password_edit.setText(pwd)

    def _save_and_accept(self):
        s = self._settings
        s.setValue(SETTINGS_SMTP_ENABLED, self.enabled_check.isChecked())
        s.setValue(SETTINGS_SMTP_HOST, self.host_edit.text().strip())
        s.setValue(SETTINGS_SMTP_PORT, self.port_spin.value())
        s.setValue(SETTINGS_SMTP_USER, self.user_edit.text().strip())
        s.setValue(SETTINGS_SMTP_USE_TLS, self.tls_check.isChecked())
        s.setValue(SETTINGS_SMTP_FROM_ADDR, self.from_edit.text().strip())
        s.setValue(SETTINGS_EMAIL_ON_CREATE, self.chk_create.isChecked())
        s.setValue(SETTINGS_EMAIL_ON_PASSWD, self.chk_passwd.isChecked())
        s.setValue(SETTINGS_EMAIL_ON_ROLE,   self.chk_role.isChecked())
        s.setValue(SETTINGS_EMAIL_ON_LOGIN,  self.chk_login.isChecked())
        # Salva password in keyring
        user = self.user_edit.text().strip()
        pwd  = self.password_edit.text()
        if keyring and user:
            try:
                keyring.set_password("Foliarium_SMTP", user, pwd)
            except Exception as e:
                logging.getLogger("CatastoGUI").warning(f"Keyring SMTP: {e}")
        self.accept()

    def _test_connection(self):
        """Salva temporaneamente i valori e invia un'email di test al mittente."""
        from foliarium.core.services.email import EmailService, EmailWorker
        # Costruisce un service "live" con i valori attuali del form
        s = QSettings()
        s.setValue(SETTINGS_SMTP_ENABLED, True)
        s.setValue(SETTINGS_SMTP_HOST, self.host_edit.text().strip())
        s.setValue(SETTINGS_SMTP_PORT, self.port_spin.value())
        s.setValue(SETTINGS_SMTP_USER, self.user_edit.text().strip())
        s.setValue(SETTINGS_SMTP_USE_TLS, self.tls_check.isChecked())
        s.setValue(SETTINGS_SMTP_FROM_ADDR, self.from_edit.text().strip())

        svc = EmailService(s)
        # Inietta la password dal campo senza passare per keyring
        svc.password = self.password_edit.text()

        to = self.from_edit.text().strip() or self.user_edit.text().strip()
        if not to:
            self.test_label.setText("⚠ Inserisci l'indirizzo mittente.")
            self._set_test_label_status("warning")
            return

        self.btn_test.setEnabled(False)
        self.test_label.setText("Invio in corso…")
        self._set_test_label_status("pending")

        self._email_worker = EmailWorker(
            svc, to,
            "[Foliarium] Test connessione SMTP",
            "Connessione SMTP configurata correttamente.\n\n-- Sistema Foliarium"
        )
        self._email_worker.result.connect(self._on_test_result)
        self._email_worker.start()

    def _set_test_label_status(self, status: str) -> None:
        self.test_label.setProperty("status", status)
        self.test_label.style().unpolish(self.test_label)
        self.test_label.style().polish(self.test_label)

    def _on_test_result(self, ok: bool, err: str):
        self.btn_test.setEnabled(True)
        if ok:
            self.test_label.setText("✓ Email di test inviata con successo.")
            self._set_test_label_status("success")
        else:
            self.test_label.setText(f"✗ {err}")
            self._set_test_label_status("error")


# ---------------------------------------------------------------------------
# HelpViewerDialog — Manuale utente integrato (Markdown → QTextBrowser)
# ---------------------------------------------------------------------------

_HELP_CSS = """
<style>
body {
    font-family: Segoe UI, Arial, sans-serif;
    font-size: 13px;
    line-height: 1.65;
    color: #212121;
    max-width: 860px;
    margin: 0 auto;
    padding: 16px 24px;
}
h1 { font-size: 1.7em; color: #1a237e; border-bottom: 2px solid #3949ab; padding-bottom: 6px; margin-top: 0; }
h2 { font-size: 1.35em; color: #283593; border-bottom: 1px solid #c5cae9; padding-bottom: 4px; margin-top: 1.4em; }
h3 { font-size: 1.1em; color: #303f9f; margin-top: 1.2em; }
h4 { font-size: 1em; color: #3949ab; }
a  { color: #1565c0; text-decoration: none; }
a:hover { text-decoration: underline; }
code {
    background: #f0f0f0;
    border-radius: 3px;
    padding: 1px 5px;
    font-family: Consolas, monospace;
    font-size: 0.88em;
    color: #c62828;
}
pre {
    background: #f5f5f5;
    border-left: 4px solid #3949ab;
    border-radius: 3px;
    padding: 10px 14px;
    overflow-x: auto;
    font-family: Consolas, monospace;
    font-size: 0.85em;
    line-height: 1.5;
}
pre code { background: none; padding: 0; color: inherit; }
blockquote {
    background: #e8eaf6;
    border-left: 4px solid #3949ab;
    margin: 10px 0;
    padding: 8px 14px;
    border-radius: 0 4px 4px 0;
    color: #37474f;
}
table { border-collapse: collapse; width: 100%; margin: 12px 0; font-size: 0.92em; }
th { background: #3949ab; color: #fff; padding: 7px 12px; text-align: left; }
td { padding: 6px 12px; border-bottom: 1px solid #e0e0e0; }
tr:nth-child(even) td { background: #f5f5f5; }
ul, ol { padding-left: 1.5em; margin: 6px 0; }
li { margin: 3px 0; }
hr { border: none; border-top: 1px solid #e0e0e0; margin: 16px 0; }
</style>
"""

_MKDOCS_YML = "mkdocs.yml"


# ---------------------------------------------------------------------------
# HelpViewerDialog — Manuale utente integrato (Markdown → QTextBrowser)
# ---------------------------------------------------------------------------

_HELP_CSS = """
<style>
body {
    font-family: Segoe UI, Arial, sans-serif;
    font-size: 13px;
    line-height: 1.65;
    color: #212121;
    max-width: 860px;
    margin: 0 auto;
    padding: 16px 24px;
}
h1 { font-size: 1.7em; color: #1a237e; border-bottom: 2px solid #3949ab; padding-bottom: 6px; margin-top: 0; }
h2 { font-size: 1.35em; color: #283593; border-bottom: 1px solid #c5cae9; padding-bottom: 4px; margin-top: 1.4em; }
h3 { font-size: 1.1em; color: #303f9f; margin-top: 1.2em; }
h4 { font-size: 1em; color: #3949ab; }
a  { color: #1565c0; text-decoration: none; }
a:hover { text-decoration: underline; }
code {
    background: #f0f0f0;
    border-radius: 3px;
    padding: 1px 5px;
    font-family: Consolas, monospace;
    font-size: 0.88em;
    color: #c62828;
}
pre {
    background: #f5f5f5;
    border-left: 4px solid #3949ab;
    border-radius: 3px;
    padding: 10px 14px;
    overflow-x: auto;
    font-family: Consolas, monospace;
    font-size: 0.85em;
    line-height: 1.5;
}
pre code { background: none; padding: 0; color: inherit; }
blockquote {
    background: #e8eaf6;
    border-left: 4px solid #3949ab;
    margin: 10px 0;
    padding: 8px 14px;
    border-radius: 0 4px 4px 0;
    color: #37474f;
}
table { border-collapse: collapse; width: 100%; margin: 12px 0; font-size: 0.92em; }
th { background: #3949ab; color: #fff; padding: 7px 12px; text-align: left; }
td { padding: 6px 12px; border-bottom: 1px solid #e0e0e0; }
tr:nth-child(even) td { background: #f5f5f5; }
ul, ol { padding-left: 1.5em; margin: 6px 0; }
li { margin: 3px 0; }
hr { border: none; border-top: 1px solid #e0e0e0; margin: 16px 0; }
</style>
"""

_MKDOCS_YML = "mkdocs.yml"


class HelpViewerDialog(QDialog):
    """Visualizzatore del manuale utente integrato.
    Legge i file .md dalla cartella docs/, li converte in HTML e li mostra
    in un QTextBrowser con navigazione ad albero sul lato sinistro.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Manuale Utente \u2014 Foliarium")
        self.setMinimumSize(900, 620)
        self.resize(1100, 720)
        self.setWindowFlags(
            self.windowFlags() | Qt.WindowType.WindowMaximizeButtonHint)

        self._docs_dir = get_doc_path()
        self._history = []
        self._history_pos = -1

        self._build_ui()
        self._populate_nav()

        # Apri la prima pagina disponibile
        root = self.nav_tree.invisibleRootItem()
        if root.childCount():
            first = root.child(0)
            if first.childCount():
                first = first.child(0)
            self.nav_tree.setCurrentItem(first)

    # ------------------------------------------------------------------
    # Costruzione UI
    # ------------------------------------------------------------------

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        # Toolbar navigazione
        toolbar = QHBoxLayout()
        self.btn_back = QPushButton("\u25c4 Indietro")
        self.btn_back.setEnabled(False)
        self.btn_back.clicked.connect(self._go_back)
        self.btn_forward = QPushButton("Avanti \u25ba")
        self.btn_forward.setEnabled(False)
        self.btn_forward.clicked.connect(self._go_forward)
        self.lbl_title = QLabel()
        title_font = self.lbl_title.font()
        title_font.setBold(True)
        self.lbl_title.setFont(title_font)
        toolbar.addWidget(self.btn_back)
        toolbar.addWidget(self.btn_forward)
        toolbar.addSpacing(12)
        toolbar.addWidget(self.lbl_title)
        toolbar.addStretch()
        layout.addLayout(toolbar)

        # Splitter: albero a sinistra, contenuto a destra
        splitter = QSplitter(Qt.Orientation.Horizontal)

        self.nav_tree = QTreeWidget()
        self.nav_tree.setHeaderHidden(True)
        self.nav_tree.setMinimumWidth(180)
        self.nav_tree.setMaximumWidth(280)
        self.nav_tree.setAnimated(True)
        self.nav_tree.currentItemChanged.connect(self._on_nav_changed)

        self.content = QTextBrowser()
        self.content.setOpenLinks(False)
        self.content.anchorClicked.connect(self._on_link_clicked)
        self.content.setFont(QFont("Segoe UI", 10))

        splitter.addWidget(self.nav_tree)
        splitter.addWidget(self.content)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 4)
        layout.addWidget(splitter, stretch=1)

        # Pulsante chiudi
        btn_bar = QHBoxLayout()
        btn_bar.addStretch()
        btn_close = QPushButton("Chiudi")
        btn_close.setDefault(True)
        btn_close.clicked.connect(self.accept)
        btn_bar.addWidget(btn_close)
        layout.addLayout(btn_bar)

    # ------------------------------------------------------------------
    # Navigazione ad albero da mkdocs.yml
    # ------------------------------------------------------------------

    def _populate_nav(self):
        """Legge mkdocs.yml e costruisce il QTreeWidget di navigazione."""
        nav = self._parse_mkdocs_nav()
        self.nav_tree.clear()
        if nav:
            self._add_nav_items(self.nav_tree.invisibleRootItem(), nav)
        else:
            self._add_nav_fallback()
        self.nav_tree.expandAll()

    def _parse_mkdocs_nav(self):
        """Tenta di leggere la sezione nav da mkdocs.yml."""
        yml_path = self._docs_dir.parent / _MKDOCS_YML
        if not yml_path.exists():
            return []
        try:
            import yaml
            with open(yml_path, encoding="utf-8") as f:
                cfg = yaml.safe_load(f)
            return cfg.get("nav", []) or []
        except Exception:
            return []

    def _add_nav_items(self, parent, nav_list):
        """Ricorsivo: costruisce QTreeWidgetItem dalla struttura nav di mkdocs."""
        for entry in nav_list:
            if isinstance(entry, dict):
                for label, value in entry.items():
                    if isinstance(value, str):
                        item = QTreeWidgetItem(parent, [label])
                        item.setData(0, Qt.ItemDataRole.UserRole, value)
                        item.setToolTip(0, label)
                    elif isinstance(value, list):
                        cat = QTreeWidgetItem(parent, [label])
                        cat.setData(0, Qt.ItemDataRole.UserRole, None)
                        cat_font = cat.font(0)
                        cat_font.setBold(True)
                        cat.setFont(0, cat_font)
                        self._add_nav_items(cat, value)
            elif isinstance(entry, str):
                item = QTreeWidgetItem(parent, [entry])
                item.setData(0, Qt.ItemDataRole.UserRole, entry)

    def _add_nav_fallback(self):
        """Fallback: scansiona docs/ e aggiunge tutti i .md trovati."""
        for md_file in sorted(self._docs_dir.rglob("*.md")):
            rel = md_file.relative_to(self._docs_dir).as_posix()
            label = md_file.stem.replace("-", " ").replace("_", " ").title()
            item = QTreeWidgetItem(self.nav_tree, [label])
            item.setData(0, Qt.ItemDataRole.UserRole, rel)

    # ------------------------------------------------------------------
    # Caricamento e rendering pagina
    # ------------------------------------------------------------------

    def _load_page(self, rel_path, push_history=True):
        """Carica un file .md, lo converte in HTML e lo visualizza."""
        anchor = ""
        if "#" in rel_path:
            rel_path, anchor = rel_path.split("#", 1)
        rel_path = rel_path.replace("\\", "/")

        md_file = self._docs_dir / rel_path
        if not md_file.exists():
            self.content.setHtml(
                f"<p><i>Pagina non trovata: <code>{rel_path}</code></i></p>")
            return

        try:
            import markdown as _md
            text = md_file.read_text(encoding="utf-8")
            body = _md.markdown(
                text,
                extensions=["tables", "fenced_code", "toc", "admonition", "nl2br"],
            )
            html = (
                "<!DOCTYPE html><html><head>"
                + _HELP_CSS
                + "</head><body>"
                + body
                + "</body></html>"
            )
            self.content.setHtml(html)
        except Exception as e:
            self.content.setPlainText(f"Errore rendering: {e}")
            return

        title = md_file.stem.replace("-", " ").replace("_", " ").title()
        self.lbl_title.setText(title)

        if anchor:
            self.content.scrollToAnchor(anchor)

        if push_history:
            self._history = self._history[:self._history_pos + 1]
            self._history.append(rel_path)
            self._history_pos = len(self._history) - 1

        self._update_nav_buttons()
        self._sync_tree(rel_path)

    def _sync_tree(self, rel_path):
        """Seleziona nel tree il nodo corrispondente alla pagina corrente."""
        def _find(item):
            data = item.data(0, Qt.ItemDataRole.UserRole)
            if data and data.replace("\\", "/") == rel_path:
                self.nav_tree.blockSignals(True)
                self.nav_tree.setCurrentItem(item)
                self.nav_tree.blockSignals(False)
                return True
            for i in range(item.childCount()):
                if _find(item.child(i)):
                    return True
            return False

        root = self.nav_tree.invisibleRootItem()
        for i in range(root.childCount()):
            if _find(root.child(i)):
                break

    # ------------------------------------------------------------------
    # Slot
    # ------------------------------------------------------------------

    def _on_nav_changed(self, current, _previous):
        if current is None:
            return
        path = current.data(0, Qt.ItemDataRole.UserRole)
        if path:
            self._load_page(path)

    def _on_link_clicked(self, url):
        href = url.toString()
        if href.startswith("http://") or href.startswith("https://"):
            QDesktopServices.openUrl(url)
            return
        if self._history_pos >= 0:
            from pathlib import PurePosixPath
            current_rel = self._history[self._history_pos]
            base = PurePosixPath(current_rel).parent
            resolved = str(base / href).lstrip("/")
        else:
            resolved = href
        self._load_page(resolved)

    def _go_back(self):
        if self._history_pos > 0:
            self._history_pos -= 1
            self._load_page(self._history[self._history_pos], push_history=False)

    def _go_forward(self):
        if self._history_pos < len(self._history) - 1:
            self._history_pos += 1
            self._load_page(self._history[self._history_pos], push_history=False)

    def _update_nav_buttons(self):
        self.btn_back.setEnabled(self._history_pos > 0)
        self.btn_forward.setEnabled(self._history_pos < len(self._history) - 1)


# ===========================================================================
# LicenseDialog — gestione e visualizzazione della licenza
# ===========================================================================


class LicenseDialog(QDialog):
    """
    Dialog per visualizzare lo stato della licenza, configurare il percorso
    del file .license e la cartella condivisa per il conteggio dei seat di rete.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Gestione Licenza — Foliarium")
        self.setMinimumWidth(540)
        self.setMinimumHeight(420)
        self._build_ui()
        self._load_settings()
        self._refresh_status()

    # ------------------------------------------------------------------
    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # --- Gruppo: stato licenza ---
        grp_status = QGroupBox("Stato licenza attuale")
        grp_layout = QFormLayout(grp_status)

        self._lbl_valid    = QLabel("—")
        self._lbl_owner    = QLabel("—")
        self._lbl_type     = QLabel("—")
        self._lbl_seats    = QLabel("—")
        self._lbl_expiry   = QLabel("—")
        self._lbl_hw       = QLabel("—")
        self._lbl_fp       = QLabel("—")

        grp_layout.addRow("Stato:",          self._lbl_valid)
        grp_layout.addRow("Intestata a:",    self._lbl_owner)
        grp_layout.addRow("Tipo:",           self._lbl_type)
        grp_layout.addRow("Seat (max):",     self._lbl_seats)
        grp_layout.addRow("Scadenza:",       self._lbl_expiry)
        grp_layout.addRow("Hardware ID:",    self._lbl_hw)
        grp_layout.addRow("ID computer:",    self._lbl_fp)
        layout.addWidget(grp_status)

        # --- Gruppo: percorso file licenza ---
        grp_file = QGroupBox("File di licenza")
        file_layout = QHBoxLayout(grp_file)
        self._edit_license_path = QLineEdit()
        self._edit_license_path.setPlaceholderText("Percorso file foliarium.license …")
        btn_browse = QPushButton("Sfoglia…")
        btn_browse.clicked.connect(self._browse_license_file)
        file_layout.addWidget(self._edit_license_path)
        file_layout.addWidget(btn_browse)
        layout.addWidget(grp_file)

        # --- Gruppo: cartella condivisa per seat di rete ---
        grp_share = QGroupBox("Cartella condivisa (controllo seat di rete)")
        share_layout = QVBoxLayout(grp_share)
        lbl_help = QLabel(
            "Inserisci il percorso UNC di una cartella condivisa accessibile da tutti i PC\n"
            "dove è installato Foliarium (es. \\\\server\\Condivisa\\foliarium_seats).\n"
            "Lascia vuoto per non limitare le istanze simultanee."
        )
        lbl_help.setWordWrap(True)
        lbl_help.setProperty("muted", "true")
        share_layout.addWidget(lbl_help)
        share_row = QHBoxLayout()
        self._edit_share = QLineEdit()
        self._edit_share.setPlaceholderText("\\\\server\\condivisa\\foliarium_seats")
        btn_browse_share = QPushButton("Sfoglia…")
        btn_browse_share.clicked.connect(self._browse_share_folder)
        share_row.addWidget(self._edit_share)
        share_row.addWidget(btn_browse_share)
        share_layout.addLayout(share_row)
        layout.addWidget(grp_share)

        # --- Bottoni ---
        btn_row = QHBoxLayout()
        btn_refresh = QPushButton("Ricontrolla licenza")
        btn_refresh.clicked.connect(self._refresh_status)
        btn_generate = QPushButton("Copia ID hardware…")
        btn_generate.setToolTip("Copia negli appunti il fingerprint di questo computer da inviare per generare la licenza")
        btn_generate.clicked.connect(self._copy_hardware_id)
        btn_save = QPushButton("Salva impostazioni")
        btn_save.setDefault(True)
        btn_save.clicked.connect(self._save_and_close)
        btn_close = QPushButton("Chiudi")
        btn_close.clicked.connect(self.reject)

        btn_row.addWidget(btn_refresh)
        btn_row.addWidget(btn_generate)
        btn_row.addStretch()
        btn_row.addWidget(btn_save)
        btn_row.addWidget(btn_close)
        layout.addLayout(btn_row)

    # ------------------------------------------------------------------
    def _load_settings(self):
        from PyQt6.QtCore import QSettings
        s = QSettings()
        self._edit_license_path.setText(s.value(SETTINGS_LICENSE_FILE_PATH, "", type=str))
        self._edit_share.setText(s.value(SETTINGS_LICENSE_NETWORK_SHARE, "", type=str))

    def _refresh_status(self):
        from foliarium.core.services.license import LicenseManager, get_hardware_fingerprint
        # Aggiorna il percorso nell'oggetto manager prima di validare
        lm = LicenseManager.__new__(LicenseManager)
        lm.license_path  = self._edit_license_path.text().strip() or lm.__class__.__init__.__code__.co_filename
        # Usa direttamente la funzione di validazione
        from foliarium.core.services.license import _validate_file
        from config import IS_DEMO_MODE
        if IS_DEMO_MODE:
            from datetime import date
            from foliarium.core.services.license import LicenseInfo
            info = LicenseInfo("Versione Demo", "demo", 1, None, None, date.today(), True)
        else:
            path = self._edit_license_path.text().strip()
            if not path:
                from app_paths import BASE_DIR
                from config import LICENSE_DEFAULT_FILENAME
                from pathlib import Path
                path = str(Path(BASE_DIR) / LICENSE_DEFAULT_FILENAME)
            info = _validate_file(path)

        fp = get_hardware_fingerprint()
        self._lbl_fp.setText(fp)

        if info.is_valid:
            self._lbl_valid.setText("<b style='color:green'>✔ Valida</b>")
        else:
            self._lbl_valid.setText(f"<b style='color:red'>✘ {info.error_message}</b>")

        self._lbl_owner.setText(info.licensed_to or "—")
        type_labels = {"demo": "Demo", "standard": "Standard", "enterprise": "Enterprise"}
        self._lbl_type.setText(type_labels.get(info.license_type, info.license_type))
        self._lbl_seats.setText(str(info.max_seats))
        if info.expiry_date:
            days = info.days_to_expiry()
            self._lbl_expiry.setText(
                f"{info.expiry_date.strftime('%d/%m/%Y')}  "
                f"({'scaduta' if days < 0 else f'tra {days} giorni'})"
            )
        else:
            self._lbl_expiry.setText("Perpetua")
        self._lbl_hw.setText(info.hardware_id or "Qualsiasi")

    def _browse_license_file(self):
        from PyQt6.QtWidgets import QFileDialog
        path, _ = QFileDialog.getOpenFileName(
            self, "Seleziona file licenza",
            self._edit_license_path.text() or "",
            "File licenza (*.license *.json);;Tutti i file (*)"
        )
        if path:
            self._edit_license_path.setText(path)
            self._refresh_status()

    def _browse_share_folder(self):
        from PyQt6.QtWidgets import QFileDialog
        folder = QFileDialog.getExistingDirectory(
            self, "Seleziona cartella condivisa", self._edit_share.text() or ""
        )
        if folder:
            self._edit_share.setText(folder)

    def _copy_hardware_id(self):
        from foliarium.core.services.license import get_hardware_fingerprint
        from PyQt6.QtWidgets import QApplication
        fp = get_hardware_fingerprint()
        QApplication.clipboard().setText(fp)
        QMessageBox.information(
            self, "ID copiato",
            f"ID hardware copiato negli appunti:\n\n{fp}\n\n"
            "Invia questo codice all'amministratore per generare il file di licenza."
        )

    def _save_and_close(self):
        from PyQt6.QtCore import QSettings
        s = QSettings()
        s.setValue(SETTINGS_LICENSE_FILE_PATH, self._edit_license_path.text().strip())
        s.setValue(SETTINGS_LICENSE_NETWORK_SHARE, self._edit_share.text().strip())
        s.sync()
        QMessageBox.information(self, "Salvato",
                                "Impostazioni di licenza salvate.\n"
                                "Riavvia l'applicazione per applicarle.")
        self.accept()


# ---------------------------------------------------------------------------
# LoginDialog
# ---------------------------------------------------------------------------

class LoginDialog(QDialog):
    """Dialog di autenticazione utente."""

    def __init__(self, db_manager: CatastoDBManager, client_ip: str, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.client_ip = client_ip
        self.logged_in_user_id: Optional[int] = None
        self.logged_in_user_info: Optional[Dict] = None
        self.current_session_id_from_dialog: Optional[str] = None

        self.setWindowTitle("Login — Foliarium")
        self.setMinimumWidth(420)
        self.setModal(True)
        self.setObjectName("loginDialog")

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # ── Banner indigo con logo + titolo ──────────────────────────────
        from app_paths import get_logo_svg_path
        banner = QFrame()
        banner.setObjectName("loginBanner")
        banner.setMinimumHeight(120)
        banner_layout = QVBoxLayout(banner)
        banner_layout.setContentsMargins(28, 22, 28, 22)
        banner_layout.setSpacing(6)
        banner_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        try:
            from PyQt6.QtSvgWidgets import QSvgWidget
            logo_path = get_logo_svg_path(dark=True)
            if logo_path:
                logo = QSvgWidget(str(logo_path))
                logo.setFixedSize(48, 48)
                logo_row = QHBoxLayout()
                logo_row.addStretch()
                logo_row.addWidget(logo)
                logo_row.addStretch()
                banner_layout.addLayout(logo_row)
        except Exception:
            pass

        title = QLabel("Foliarium")
        title.setObjectName("loginTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        banner_layout.addWidget(title)

        subtitle = QLabel("Archivio Catastale Storico")
        subtitle.setObjectName("loginSubtitle")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        banner_layout.addWidget(subtitle)

        outer.addWidget(banner)

        # ── Form ─────────────────────────────────────────────────────────
        body = QWidget()
        body.setObjectName("loginBody")
        layout = QVBoxLayout(body)
        layout.setContentsMargins(32, 28, 32, 24)
        layout.setSpacing(14)

        prompt = QLabel("Accedi al tuo account")
        prompt.setObjectName("loginPrompt")
        layout.addWidget(prompt)

        form_layout = QGridLayout()
        form_layout.setHorizontalSpacing(10)
        form_layout.setVerticalSpacing(10)
        form_layout.setColumnStretch(1, 1)

        _lbl_user = QLabel("Username:")
        _lbl_user.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        form_layout.addWidget(_lbl_user, 0, 0)
        self.username_edit = QLineEdit()
        self.username_edit.setPlaceholderText("Il tuo username")
        self.username_edit.setMinimumHeight(34)
        form_layout.addWidget(self.username_edit, 0, 1)

        _lbl_pwd = QLabel("Password:")
        _lbl_pwd.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        form_layout.addWidget(_lbl_pwd, 1, 0)
        self.password_edit = QPasswordLineEdit()
        self.password_edit.setPlaceholderText("La tua password")
        self.password_edit.setMinimumHeight(34)
        form_layout.addWidget(self.password_edit, 1, 1)

        layout.addLayout(form_layout)
        layout.addSpacing(6)

        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(10)
        self.cancel_button = QPushButton("Esci")
        self.cancel_button.setObjectName("secondaryButton")
        self.cancel_button.setMinimumHeight(36)
        self.cancel_button.setAutoDefault(False)
        self.cancel_button.clicked.connect(self.reject)
        buttons_layout.addWidget(self.cancel_button)

        buttons_layout.addStretch()

        self.login_button = QPushButton("Accedi")
        self.login_button.setDefault(True)
        self.login_button.setAutoDefault(True)
        self.login_button.setMinimumHeight(36)
        self.login_button.setMinimumWidth(120)
        self.login_button.clicked.connect(self.handle_login)
        buttons_layout.addWidget(self.login_button)

        self.username_edit.returnPressed.connect(lambda: self.password_edit.setFocus())
        self.password_edit.returnPressed.connect(self.handle_login)

        layout.addLayout(buttons_layout)
        outer.addWidget(body, 1)

        # Ombra modale (richiede flag finestra senza titolo per essere
        # visibile; con titolo standard Qt rende comunque la finestra
        # decorata dal window manager — l'ombra resta interna al dialog).
        try:
            from foliarium.ui.effects import apply_elevated_shadow
            apply_elevated_shadow(body)
        except Exception:
            pass

        self.username_edit.setFocus()

    def handle_login(self):
        username = self.username_edit.text().strip()
        password = self.password_edit.text()

        if not username or not password:
            QMessageBox.warning(self, "Login Fallito", "Username e password sono obbligatori.")
            return

        credentials = self.db_manager.get_user_credentials(username)
        login_success = False
        user_id_app = None

        if credentials:
            user_id_app = credentials.get('id')
            stored_hash = credentials.get('password_hash')
            is_active = credentials.get('attivo', False)

            if not is_active:
                QMessageBox.warning(self, "Login Fallito", "Utente non attivo.")
                logging.getLogger("CatastoGUI").warning(
                    f"Login fallito (utente '{username}' non attivo).")
                return

            if stored_hash and _verify_password(stored_hash, password):
                login_success = True
            else:
                QMessageBox.warning(self, "Login Fallito", "Username o Password errati.")
                logging.getLogger("CatastoGUI").warning(
                    f"Login fallito (pwd errata) per '{username}'.")
                self.password_edit.selectAll()
                self.password_edit.setFocus()
                return
        else:
            QMessageBox.warning(self, "Login Fallito", "Username o Password errati.")
            logging.getLogger("CatastoGUI").warning(
                f"Login fallito (utente '{username}' non trovato).")
            self.username_edit.selectAll()
            self.username_edit.setFocus()
            return

        if login_success and user_id_app is not None:
            try:
                session_uuid = self.db_manager.register_access(
                    user_id=user_id_app,
                    action='login',
                    esito=True,
                    indirizzo_ip=self.client_ip,
                    application_name='CatastoAppGUI',
                )

                if session_uuid:
                    self.logged_in_user_id = user_id_app
                    self.logged_in_user_info = credentials
                    self.current_session_id_from_dialog = session_uuid

                    if not self.db_manager.set_audit_session_variables(user_id_app, session_uuid):
                        QMessageBox.critical(
                            self, "Errore Audit",
                            "Impossibile impostare le informazioni di sessione per l'audit. "
                            "Il login non può procedere.")
                        return

                    QMessageBox.information(
                        self, "Login Riuscito",
                        f"Benvenuto {self.logged_in_user_info.get('nome_completo', username)}!")
                    self.accept()
                else:
                    QMessageBox.critical(
                        self, "Login Fallito",
                        "Errore critico: impossibile registrare la sessione di accesso.")
                    logging.getLogger("CatastoGUI").error(
                        f"Login OK per '{username}' ma sessione non registrata.")

            except DBMError as e:
                QMessageBox.critical(self, "Errore di Login (DB)",
                                     f"Errore durante il login:\n{e}")
                logging.getLogger("CatastoGUI").error(f"DBMError login per {username}: {e}")
            except Exception as e:
                QMessageBox.critical(self, "Errore Imprevisto",
                                     f"Errore di sistema durante il login:\n{e}")
                logging.getLogger("CatastoGUI").error(
                    f"Errore imprevisto login per {username}: {e}", exc_info=True)

