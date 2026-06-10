"""Dialog di configurazione connessione al database."""
from __future__ import annotations

import logging
import os
from typing import Optional, Dict, Any

from PyQt6.QtCore import (QSettings, Qt)
from PyQt6.QtWidgets import (QApplication,
                             QCheckBox, QDialog,
                             QFileDialog, QFormLayout, QGroupBox,
                             QHBoxLayout, QLabel, QLineEdit,
                             QMessageBox, QPushButton, QSpinBox, QStyle,
                             QVBoxLayout,
                             QDialogButtonBox,
                             QRadioButton)
from app_paths import get_resource_path, get_resource_path as resource_path, get_doc_path  # noqa: F401
from config import (
    SETTINGS_DB_TYPE, SETTINGS_DB_HOST, SETTINGS_DB_PORT,
    SETTINGS_DB_NAME, SETTINGS_DB_USER, SETTINGS_DB_SCHEMA, SETTINGS_DB_PASSWORD,
)
from catasto_db_manager import CatastoDBManager
from catasto_exceptions import DBMError, DBUniqueConstraintError, DBNotFoundError, DBDataError  # noqa: F401
from foliarium.ui.widgets.custom import QPasswordLineEdit

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
    
    


