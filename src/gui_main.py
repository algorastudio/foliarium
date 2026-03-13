
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Interfaccia Grafica per Gestionale Catasto Storico
=================================================
Autore: Marco Santoro
Data: 18/05/2025
Versione: 1.2 (con integrazione menu esportazioni)
"""
import sys,bcrypt
from gui_widgets import UnifiedFuzzySearchWidget
import os
import logging
from datetime import datetime
from typing import Optional, Dict
# Importazioni PyQt5
from PyQt5.QtCore import (QSettings,
                          QStandardPaths, Qt, QUrl,
                          pyqtSlot,QCoreApplication)

from PyQt5.QtGui import (QCloseEvent, QDesktopServices)


from PyQt5.QtWidgets import (QAction, QActionGroup, QApplication, # <-- AGGIUNTO QActionGroup
                             QDialog, QFileDialog, QFrame, QGridLayout,
                             QHBoxLayout, QInputDialog,
                             QLabel, QLineEdit, QMainWindow, QMessageBox, QPushButton, QStyle, QTabWidget,
                             QVBoxLayout, QWidget)
# --- FINE MODIFICA ---



from catasto_db_manager import CatastoDBManager
from app_utils import get_local_ip_address, get_password_from_keyring 
import pandas as pd # Importa pandas
from app_paths import get_available_styles, load_stylesheet, get_logo_path, get_resource_path
from dialogs import CSVImportResultDialog, EulaDialog,BackupReminderSettingsDialog


# Dai nuovi moduli che creeremo:
from gui_widgets import (
    DashboardWidget, ElencoComuniWidget, RicercaPartiteWidget,
    RicercaAvanzataImmobiliWidget, InserimentoComuneWidget,
    InserimentoPossessoreWidget, InserimentoLocalitaWidget, RegistrazioneProprietaWidget,
    OperazioniPartitaWidget, EsportazioniWidget, ReportisticaWidget, StatisticheWidget,
    GestioneUtentiWidget, AuditLogViewerWidget, BackupWidget, 
    RegistraConsultazioneWidget, WelcomeScreen  , RicercaPartiteWidget,GestionePeriodiStoriciWidget ,
    GestioneTipiLocalitaWidget , 
    DBConfigDialog,InserimentoPartitaWidget)
from dialogs import CSVImportResultDialog,EulaDialog

from custom_widgets import QPasswordLineEdit


from config import (
    SETTINGS_DB_TYPE, SETTINGS_DB_HOST, SETTINGS_DB_PORT, 
    SETTINGS_DB_NAME, SETTINGS_DB_USER, SETTINGS_DB_SCHEMA,SETTINGS_DB_PASSWORD)

try:
    from fpdf import FPDF
    from fpdf.enums import XPos, YPos
    FPDF_AVAILABLE = True
except ImportError:
    FPDF_AVAILABLE = False
    # QMessageBox.warning(None, "Avviso Dipendenza", "La libreria FPDF non è installata. L'esportazione in PDF non sarà disponibile.")
    # Non mostrare il messaggio qui, ma gestire la disabilitazione dei pulsanti PDF.

# Importazione del gestore DB (il percorso potrebbe necessitare aggiustamenti)
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
# Importazione del gestore DB, con gestione dell'errore di importazione
try:
    from catasto_db_manager import CatastoDBManager
except ImportError:
    sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
    try:
        from catasto_db_manager import CatastoDBManager
    except ImportError:
        QMessageBox.critical(None, "Errore Importazione",
                             "Non è possibile importare CatastoDBManager. "
                             "Assicurati che catasto_db_manager.py sia accessibile.")
        sys.exit(1)
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

class LoginDialog(QDialog):
    # --- INIZIO MODIFICA 1 ---
    # Aggiungiamo 'client_ip' come parametro all'init
    def __init__(self, db_manager: CatastoDBManager, client_ip: str, parent=None):
        super(LoginDialog, self).__init__(parent)
        self.db_manager = db_manager
        self.client_ip = client_ip # Salviamo l'IP come attributo dell'istanza
        self.logged_in_user_id: Optional[int] = None
    # --- FINE MODIFICA 1 ---
        self.logged_in_user_info: Optional[Dict] = None
        # NUOVO attributo per conservare l'UUID
        self.current_session_id_from_dialog: Optional[str] = None

        self.setWindowTitle("Login - Meridiana 1.2")
        self.setMinimumWidth(350)
        self.setModal(True)

        layout = QVBoxLayout(self)

        form_layout = QGridLayout()
        form_layout.addWidget(QLabel("Username:"), 0, 0)
        self.username_edit = QLineEdit()
        self.username_edit.setPlaceholderText("Inserisci username")
        form_layout.addWidget(self.username_edit, 0, 1)

        form_layout.addWidget(QLabel("Password:"), 1, 0)
        self.password_edit = QPasswordLineEdit()
        form_layout.addWidget(self.password_edit, 1, 1)

        layout.addLayout(form_layout)

        buttons_layout = QHBoxLayout()
        self.login_button = QPushButton("Login")
        self.login_button.setDefault(True)
        self.login_button.clicked.connect(self.handle_login)

        self.cancel_button = QPushButton("Esci")
        self.cancel_button.clicked.connect(self.reject)

        buttons_layout.addStretch()
        buttons_layout.addWidget(self.login_button)
        buttons_layout.addWidget(self.cancel_button)
        layout.addLayout(buttons_layout)

        self.username_edit.setFocus()

    def handle_login(self):
        username = self.username_edit.text().strip()
        password = self.password_edit.text()

        if not username or not password:
            QMessageBox.warning(self, "Login Fallito",
                                "Username e password sono obbligatori.")
            return

        credentials = self.db_manager.get_user_credentials(
            username)  # Presumiamo restituisca anche 'id' utente app
        login_success = False
        user_id_app = None  # ID utente dell'applicazione

        if credentials:
            # ID dell'utente dalla tabella 'utente'
            user_id_app = credentials.get('id')
            stored_hash = credentials.get('password_hash')
            is_active = credentials.get('attivo', False)

            if not is_active:
                QMessageBox.warning(self, "Login Fallito",
                                    "Utente non attivo.")
                logging.getLogger("CatastoGUI").warning(
                    f"Login GUI fallito (utente '{username}' non attivo).")
                return  # Non procedere oltre se l'utente non è attivo

            # Usa la tua funzione di verifica
            if stored_hash and _verify_password(stored_hash, password):
                login_success = True
                logging.getLogger("CatastoGUI").info(
                    f"Verifica password GUI OK per utente '{username}' (ID App: {user_id_app})")
            else:
                QMessageBox.warning(self, "Login Fallito",
                                    "Username o Password errati.")
                logging.getLogger("CatastoGUI").warning(
                    f"Login GUI fallito (pwd errata) per utente '{username}'.")
                self.password_edit.selectAll()
                self.password_edit.setFocus()
                return
        else:
            # Messaggio generico
            QMessageBox.warning(self, "Login Fallito",
                                "Username o Password errati.")
            logging.getLogger("CatastoGUI").warning(
                f"Login GUI fallito (utente '{username}' non trovato).")
            self.username_edit.selectAll()
            self.username_edit.setFocus()
            return

        if login_success and user_id_app is not None:
            try:
                 # --- INIZIO MODIFICA 2 ---
                # Usiamo self.client_ip invece della variabile globale non definita
                session_uuid_returned = self.db_manager.register_access(
                    user_id=user_id_app,
                    action='login',
                    esito=True,
                    indirizzo_ip=self.client_ip, # <-- USA L'ATTRIBUTO DI ISTANZA
                    application_name='CatastoAppGUI'
                )
                # --- FINE MODIFICA 2 ---

                if session_uuid_returned:
                    self.logged_in_user_id = user_id_app
                    # Contiene tutti i dati dell'utente, incluso 'id'
                    self.logged_in_user_info = credentials
                    self.current_session_id_from_dialog = session_uuid_returned  # Salva l'UUID

                    # Imposta le variabili di sessione PostgreSQL per l'audit
                    # user_id_app è l'ID dell'utente da 'utente.id'
                    # session_uuid_returned è l'UUID dalla tabella 'sessioni_accesso.id_sessione'
                    if not self.db_manager.set_audit_session_variables(user_id_app, session_uuid_returned):
                        QMessageBox.critical(
                            self, "Errore Audit", "Impossibile impostare le informazioni di sessione per l'audit. Il login non può procedere.")
                        # Considera di non fare self.accept() qui se questo è un errore bloccante
                        return

                    QMessageBox.information(self, "Login Riuscito",
                                            f"Benvenuto {self.logged_in_user_info.get('nome_completo', username)}!")
                    self.accept()  # Chiude il dialogo e segnala successo
                else:
                    # register_access ha fallito nel restituire un session_id
                    QMessageBox.critical(
                        self, "Login Fallito", "Errore critico: Impossibile registrare la sessione di accesso nel database.")
                    logging.getLogger("CatastoGUI").error(
                        f"Login GUI OK per utente '{username}' ma fallita registrazione della sessione (nessun UUID sessione restituito).")

            except DBMError as e_dbm:  # Cattura DBMError da register_access o set_audit_session_variables
                QMessageBox.critical(
                    self, "Errore di Login (DB)", f"Errore durante il processo di login:\n{str(e_dbm)}")
                logging.getLogger("CatastoGUI").error(
                    f"DBMError durante il login per {username}: {str(e_dbm)}")
            except Exception as e_gen:  # Altri errori imprevisti
                QMessageBox.critical(
                    self, "Errore Imprevisto", f"Errore di sistema durante il login:\n{str(e_gen)}")
                logging.getLogger("CatastoGUI").error(
                    f"Errore imprevisto durante il login per {username}: {str(e_gen)}", exc_info=True)


try:
    from gui_widgets import UnifiedFuzzySearchWidget,UnifiedFuzzySearchThread
    FUZZY_SEARCH_AVAILABLE = True
except ImportError as e:
    print(f"[INIT] Ricerca fuzzy non disponibile")
    FUZZY_SEARCH_AVAILABLE = False

class CatastoMainWindow(QMainWindow):
    
    def __init__(self, client_ip_address_gui: str):
        super(CatastoMainWindow, self).__init__()
        self.logger = logging.getLogger("CatastoGUI")
        self.db_manager: Optional[CatastoDBManager] = None
        self.logged_in_user_id: Optional[int] = None
        self.logged_in_user_info: Optional[Dict] = None
        self.current_session_id: Optional[str] = None
        self.client_ip_address_gui = client_ip_address_gui

        # --- INIZIO CORREZIONE DEFINITIVA: Aggiungi questa riga ---
        self.pool_initialized_successful: bool = False
        # --- FINE CORREZIONE DEFINITIVA ---

        self.initUI()
        
    def initUI(self):
        # Inizializzazione dei QTabWidget per i sotto-tab se si usa questa organizzazione
        self.consultazione_sub_tabs = QTabWidget()
        self.inserimento_sub_tabs = QTabWidget()
        self.sistema_sub_tabs = QTabWidget()  # Deve essere inizializzato qui

        # Riferimenti ai widget specifici, inizializzati a None
        
        self.elenco_comuni_widget_ref: Optional[ElencoComuniWidget] = None
        self.ricerca_partite_widget_ref: Optional[RicercaPartiteWidget] = None
        
        self.ricerca_avanzata_immobili_widget_ref: Optional[RicercaAvanzataImmobiliWidget] = None
        self.inserimento_comune_widget_ref: Optional[InserimentoComuneWidget] = None
        self.inserimento_possessore_widget_ref: Optional[InserimentoPossessoreWidget] = None
        self.inserimento_localita_widget_ref: Optional[InserimentoLocalitaWidget] = None
        self.registrazione_proprieta_widget_ref: Optional[RegistrazioneProprietaWidget] = None
        self.operazioni_partita_widget_ref: Optional[OperazioniPartitaWidget] = None
        self.registra_consultazione_widget_ref: Optional[RegistraConsultazioneWidget] = None
        self.esportazioni_widget_ref: Optional[EsportazioniWidget] = None
        self.reportistica_widget_ref: Optional[ReportisticaWidget] = None
        self.statistiche_widget_ref: Optional[StatisticheWidget] = None
        self.gestione_utenti_widget_ref: Optional[GestioneUtentiWidget] = None
        self.audit_viewer_widget_ref: Optional[AuditLogViewerWidget] = None
        self.backup_restore_widget_ref: Optional[BackupWidget] = None
        self.gestione_periodi_storici_widget_ref: Optional[GestionePeriodiStoriciWidget] = None
        self.gestione_tipi_localita_widget_ref: Optional[GestioneTipiLocalitaWidget] = None
        
        self.setWindowTitle("Meridiana 1.2 - Gestionale Catasto Storico")
        self.setMinimumSize(1280, 720)
        self.central_widget = QWidget()
        self.main_layout = QVBoxLayout(self.central_widget)
        
        self.stale_data_bar = QFrame()
        self.stale_data_bar.setObjectName("staleDataBar") # Per lo stile CSS
        self.stale_data_bar.setStyleSheet("#staleDataBar { background-color: #FFF3CD; border: 1px solid #FFEEBA; border-radius: 4px; }")
        stale_data_layout = QHBoxLayout(self.stale_data_bar)
        stale_data_layout.setContentsMargins(10, 5, 10, 5)
        
        self.stale_data_label = QLabel("I dati delle statistiche potrebbero non essere aggiornati.")
        self.stale_data_label.setStyleSheet("color: #664D03;")
        
        self.stale_data_refresh_btn = QPushButton("Aggiorna Ora")
        self.stale_data_refresh_btn.setFixedWidth(100)
        self.stale_data_refresh_btn.clicked.connect(self._handle_stale_data_refresh_click)
        
        stale_data_layout.addWidget(self.stale_data_label)
        stale_data_layout.addStretch()
        stale_data_layout.addWidget(self.stale_data_refresh_btn)
        
        self.main_layout.addWidget(self.stale_data_bar)
        self.stale_data_bar.hide() # Nascondi la barra di default
       

        self.create_status_bar_content()
        self.create_menu_bar()

        self.tabs = QTabWidget()
        self.tabs.currentChanged.connect(self.handle_tab_changed) # <-- Modifica qui
        
        
        self.main_layout.addWidget(self.tabs)
        self.setCentralWidget(self.central_widget)

        self.statusBar().showMessage("Pronto.")

    def avvia_ricerca_globale_da_dashboard(self, testo: str):
        # 1. Trova l'indice del tab "Ricerca Globale"
        idx_ricerca = -1
        for i in range(self.tabs.count()):
            if "Ricerca Globale" in self.tabs.tabText(i):
                idx_ricerca = i
                break
        
        # 2. Se trovato, attivalo e imposta il testo della ricerca
        if idx_ricerca != -1 and hasattr(self, 'fuzzy_search_widget'):
            self.tabs.setCurrentIndex(idx_ricerca)
            self.fuzzy_search_widget.search_edit.setText(testo)
            self.fuzzy_search_widget._perform_search() # Avvia la ricerca
        else:
            self.logger.warning("Tentativo di avviare ricerca da dashboard ma il tab/widget non è stato trovato.")
    def perform_initial_setup(self, db_manager: CatastoDBManager,
                              # ID utente dell'applicazione
                              user_id: Optional[int],
                              user_info: Optional[Dict],   # Dettagli utente
                              session_id: Optional[str]):  # UUID della sessione
        logging.getLogger("CatastoGUI").info(
            ">>> CatastoMainWindow: Inizio perform_initial_setup")
        self.db_manager = db_manager
        self.logged_in_user_id = user_id
        self.logged_in_user_info = user_info
        self.current_session_id = session_id  # Memorizza l'UUID della sessione

        # --- Aggiornamento etichetta stato DB ---
        db_name_configured = "N/Config"  # Default
        db_name_configured = "N/Config"
        if self.db_manager:
            db_name_configured = self.db_manager.get_current_dbname() or "N/Config(None)"

        connection_status_text = ""
        if hasattr(self, 'pool_initialized_successful'):  # Corretto il nome dell'attributo
            if self.pool_initialized_successful:
                connection_status_text = f"Database: Connesso ({db_name_configured})"
            else:
                connection_status_text = f"Database: Non Pronto/Inesistente ({db_name_configured})"
        else:
            connection_status_text = f"Database: Stato Sconosciuto ({db_name_configured})"
        self.db_status_label.setText(connection_status_text)

        if self.logged_in_user_info:  # Se l'utente è loggato
            user_display = self.logged_in_user_info.get(
                'nome_completo') or self.logged_in_user_info.get('username', 'N/D')
            ruolo_display = self.logged_in_user_info.get('ruolo', 'N/D')
            # L'ID utente è già in self.logged_in_user_id
            self.user_status_label.setText(
                f"Utente: {user_display} (ID: {self.logged_in_user_id}, Ruolo: {ruolo_display}, Sessione: {str(self.current_session_id)[:8]}...)")
            self.logout_button.setEnabled(True)
            self.statusBar().showMessage(
                f"Login come {user_display} effettuato con successo.")
        else:  # Modalità setup DB (admin_offline) o nessun login
            ruolo_fittizio = self.logged_in_user_info.get(
                'ruolo') if self.logged_in_user_info else None
            if ruolo_fittizio == 'admin_offline':
                self.user_status_label.setText(
                    f"Utente: Admin Setup (Sessione: {str(self.current_session_id)[:8]}...)")
                # L'admin_offline può fare "logout" per chiudere l'app
                self.logout_button.setEnabled(True)
                self.statusBar().showMessage("Modalità configurazione database.")
            # Nessun login valido, ma il pool potrebbe essere attivo (improbabile con flusso attuale)
            else:
                self.user_status_label.setText("Utente: Non Autenticato")
                self.logout_button.setEnabled(False)
                self.statusBar().showMessage("Pronto.")

        logging.getLogger("CatastoGUI").info(
            ">>> CatastoMainWindow: Chiamata a setup_tabs")
        self.setup_tabs()
        
        logging.getLogger("CatastoGUI").info(
            ">>> CatastoMainWindow: Chiamata a update_ui_based_on_role")
        self.update_ui_based_on_role()

        logging.getLogger("CatastoGUI").info(
            ">>> CatastoMainWindow: Chiamata a self.show()")
        self.show()
        logging.getLogger("CatastoGUI").info(
            ">>> CatastoMainWindow: self.show() completato. Fine perform_initial_setup")
         # --- AGGIUNGERE QUESTA CHIAMATA ALLA FINE ---
        self.check_mv_refresh_status()
        # --- FINE AGGIUNTA ---
# In gui_main.py, SOSTITUISCI il metodo _check_backup_reminder

    def _check_backup_reminder(self):
        settings = QSettings()
        reminder_days = settings.value("Backup/ReminderDays", 0, type=int)

        # Se il promemoria è disattivato, esci subito
        if reminder_days == 0:
            return

        last_backup_str = settings.value("Backup/LastBackupTimestamp", "")
        reason = ""
        show_reminder = False

        if not last_backup_str:
            show_reminder = True
            reason = "Non risulta essere mai stato eseguito un backup tramite il programma."
        else:
            try:
                last_backup_date = datetime.fromisoformat(last_backup_str)
                days_since_backup = (datetime.now() - last_backup_date).days
                if days_since_backup >= reminder_days:
                    show_reminder = True
                    reason = f"Sono passati {days_since_backup} giorni dall'ultimo backup (limite impostato: {reminder_days})."
            except ValueError:
                self.logger.warning("Timestamp dell'ultimo backup non valido.")
                show_reminder = True # In dubbio, meglio mostrare l'avviso
                reason = "Impossibile determinare la data dell'ultimo backup."

        if show_reminder:
            reply = QMessageBox.question(self, "Promemoria Backup",
                                        f"{reason}\nÈ fortemente consigliato eseguire un backup dei dati.\n\nVuoi andare alla sezione di backup ora?",
                                        QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)
            if reply == QMessageBox.Yes:
                self.activate_tab_and_sub_tab("Sistema", "Backup/Ripristino DB")

    def create_menu_bar(self):
        menu_bar = self.menuBar()

        file_menu = menu_bar.addMenu("&File")
        settings_menu = menu_bar.addMenu("&Impostazioni")
        help_menu = menu_bar.addMenu("&Help")
        
            # --- INIZIO AGGIUNTA ---
        settings_menu.addSeparator()
        backup_reminder_action = QAction("Promemoria Backup...", self)
        backup_reminder_action.triggered.connect(self._show_backup_settings_dialog)
        settings_menu.addAction(backup_reminder_action)
        # --- FINE AGGIUNTA ---
        
        # --- Azioni per il menu File ---
        import_possessori_action = QAction("Importa Possessori da CSV...", self)
        import_possessori_action.triggered.connect(self._import_possessori_csv)
        import_partite_action = QAction("Importa Partite da CSV...", self)
        import_partite_action.triggered.connect(self._import_partite_csv)
        exit_action = QAction(self.style().standardIcon(QStyle.SP_DialogCloseButton), "&Esci", self)
        exit_action.triggered.connect(self.close)
        
        file_menu.addAction(import_possessori_action)
        file_menu.addAction(import_partite_action)
        file_menu.addSeparator()
        file_menu.addAction(exit_action)
        
        # --- Azioni per il menu Impostazioni ---
        config_db_action = QAction(self.style().standardIcon(QStyle.SP_ComputerIcon), "Configurazione &Database...", self)
        config_db_action.triggered.connect(self._apri_dialogo_configurazione_db)
        
        config_refresh_action = QAction("Impostazioni di Aggiornamento Dati...", self)
        config_refresh_action.triggered.connect(self._apri_dialogo_impostazioni_aggiornamento)
        
        settings_menu.addAction(config_db_action)
        settings_menu.addAction(config_refresh_action)
        settings_menu.addSeparator()

        # --- NUOVA SEZIONE: Menu dinamico per i temi ---
        style_menu = settings_menu.addMenu("Cambia Tema Grafico")
        
        self.style_action_group = QActionGroup(self) # Garantisce che solo un'opzione sia selezionata
        self.style_action_group.setExclusive(True)

        available_styles = get_available_styles()
        settings = QSettings()
        current_style = settings.value("UI/CurrentStyle", "meridiana_style.qss", type=str)

        for style_file in available_styles:
            style_name = style_file.replace('_', ' ').replace('.qss', '').title()
            action = QAction(style_name, self, checkable=True)
            action.triggered.connect(lambda checked, file=style_file: self._change_stylesheet(file))
            
            if style_file == current_style:
                action.setChecked(True) # Seleziona il tema attualmente in uso

            style_menu.addAction(action)
            self.style_action_group.addAction(action)
        # --- FINE NUOVA SEZIONE ---

        # --- Azione per il menu Help ---
        show_manual_action = QAction("Visualizza Manuale Utente...", self)
        show_manual_action.triggered.connect(self._apri_manuale_utente)
        help_menu.addAction(show_manual_action)
            # --- INIZIO MODIFICA ---
        help_menu.addSeparator()

        show_eula_action = QAction("Informazioni su Meridiana / EULA...", self)
        show_eula_action.triggered.connect(self._show_about_eula_dialog)
        help_menu.addAction(show_eula_action)
        # --- FINE MODIFICA ---

    def _change_stylesheet(self, filename: str):
        """Carica, applica e salva il nuovo stylesheet selezionato."""
        self.logger.info(f"Cambio tema grafico richiesto: {filename}")
        
        # 'load_stylesheet' è già definita in gui_main.py
        new_stylesheet = load_stylesheet(filename)
        
        if new_stylesheet:
            # Applica lo stile all'intera applicazione
            QApplication.instance().setStyleSheet(new_stylesheet)
            
            # Salva la scelta nelle impostazioni per caricarla al prossimo avvio
            settings = QSettings()
            settings.setValue("UI/CurrentStyle", filename)
            
            QMessageBox.information(self, "Cambio Tema", f"Tema '{filename.replace('.qss', '').title()}' applicato con successo.")
        else:
            QMessageBox.warning(self, "Errore Tema", f"Impossibile caricare il file di stile '{filename}'.")
            
    def _show_about_eula_dialog(self):
        """Apre la finestra di dialogo con le informazioni su versione e licenza (EULA)."""
        dialog = EulaDialog(self)
        dialog.exec_()

    # --- FINE AGGIUNTA METODO MANCANTE -
    def create_status_bar_content(self):
        status_frame = QFrame()
        status_frame.setFrameShape(QFrame.StyledPanel)
        status_frame.setFrameShadow(QFrame.Sunken)
        status_layout = QHBoxLayout(status_frame)

        self.db_status_label = QLabel("Database: Non connesso")
        self.user_status_label = QLabel("Utente: Nessuno")

        self.logout_button = QPushButton(QApplication.style(
        ).standardIcon(QStyle.SP_DialogCloseButton), "Logout")
        self.logout_button.setToolTip(
            "Effettua il logout dell'utente corrente")
        self.logout_button.clicked.connect(self.handle_logout)
        self.logout_button.setEnabled(False)

        status_layout.addWidget(self.db_status_label)
        status_layout.addSpacing(20)
        status_layout.addWidget(self.user_status_label)
        status_layout.addStretch()
        status_layout.addWidget(self.logout_button)
        self.main_layout.addWidget(status_frame)

    
    # In gui_main.py, SOSTITUISCI l'intero metodo setup_tabs con questo:

    def setup_tabs(self):
        if not self.db_manager:
            self.logger.error("Tentativo di configurare i tab senza un db_manager.")
            return

        self.tabs.clear()

        # Inizializza i contenitori per i sotto-tab
        self.consultazione_sub_tabs = QTabWidget()
        self.inserimento_sub_tabs = QTabWidget()
        self.sistema_sub_tabs = QTabWidget()
        
        # Collega anche i sotto-tab al gestore di eventi universale
        self.consultazione_sub_tabs.currentChanged.connect(self.handle_tab_changed)
        self.inserimento_sub_tabs.currentChanged.connect(self.handle_tab_changed)
        self.sistema_sub_tabs.currentChanged.connect(self.handle_tab_changed)

        # 1. Tab Dashboard
        self.dashboard_widget = DashboardWidget(self.db_manager, self.logged_in_user_info, self.tabs)
        self.tabs.addTab(self.dashboard_widget, "🏠 Home")
        self.dashboard_widget.go_to_tab_signal.connect(self.activate_tab_and_sub_tab)
        self.dashboard_widget.ricerca_globale_richiesta.connect(self.avvia_ricerca_globale_da_dashboard)

        # 2. Tab Consultazione e Modifica
        consultazione_contenitore = QWidget()
        layout_consultazione = QVBoxLayout(consultazione_contenitore)
        self.elenco_comuni_widget_ref = ElencoComuniWidget(self.db_manager, self.consultazione_sub_tabs)
        self.consultazione_sub_tabs.addTab(self.elenco_comuni_widget_ref, "Principale")
        self.ricerca_partite_widget_ref = RicercaPartiteWidget(self.db_manager, self.consultazione_sub_tabs)
        self.consultazione_sub_tabs.addTab(self.ricerca_partite_widget_ref, "Ricerca Partite")
        self.ricerca_avanzata_immobili_widget_ref = RicercaAvanzataImmobiliWidget(self.db_manager, self.consultazione_sub_tabs)
        self.consultazione_sub_tabs.addTab(self.ricerca_avanzata_immobili_widget_ref, "Ricerca Immobili")
        
        # Tooltip per i sotto-tab di consultazione
        self.consultazione_sub_tabs.setTabToolTip(0, "Visualizza l'elenco principale dei comuni registrati")
        self.consultazione_sub_tabs.setTabToolTip(1, "Ricerca partite per comune, numero, possessore o natura immobile")
        self.consultazione_sub_tabs.setTabToolTip(2, "Ricerca avanzata immobili con filtri multipli")
        
        layout_consultazione.addWidget(self.consultazione_sub_tabs)
        self.tabs.addTab(consultazione_contenitore, "Consultazione")

        # 3. Tab Ricerca Globale
        if FUZZY_SEARCH_AVAILABLE:
            self.fuzzy_search_widget = UnifiedFuzzySearchWidget(self.db_manager, parent=self.tabs)
            self.tabs.addTab(self.fuzzy_search_widget, "🔍 Ricerca")

        # 4. Tab Inserimento
        inserimento_contenitore = QWidget()
        layout_inserimento = QVBoxLayout(inserimento_contenitore)
        utente_per_inserimenti = self.logged_in_user_info if self.logged_in_user_info else {}

        # Aggiunta dei widget esistenti per l'inserimento
        self.inserimento_comune_widget_ref = InserimentoComuneWidget(
            db_manager=self.db_manager,
            utente_attuale_info=utente_per_inserimenti,
            parent=self.inserimento_sub_tabs
        )
        self.inserimento_sub_tabs.addTab(self.inserimento_comune_widget_ref, "Comune")

        self.inserimento_possessore_widget_ref = InserimentoPossessoreWidget(self.db_manager)
        self.inserimento_sub_tabs.addTab(self.inserimento_possessore_widget_ref, "Possessore")
        self.inserimento_possessore_widget_ref.import_csv_requested.connect(self._import_possessori_csv)
        
        self.inserimento_partite_widget_ref = InserimentoPartitaWidget(self.db_manager, self.inserimento_sub_tabs)
        self.inserimento_sub_tabs.addTab(self.inserimento_partite_widget_ref, "Partita")
        self.inserimento_partite_widget_ref.import_csv_requested.connect(self._import_partite_csv)
    
        self.inserimento_localita_widget_ref = InserimentoLocalitaWidget(self.db_manager, self.inserimento_sub_tabs)
        self.inserimento_sub_tabs.addTab(self.inserimento_localita_widget_ref, "Località")

        self.registrazione_proprieta_widget_ref = RegistrazioneProprietaWidget(self.db_manager)
        self.inserimento_sub_tabs.addTab(self.registrazione_proprieta_widget_ref, "Reg. Proprietà")

        self.operazioni_partita_widget_ref = OperazioniPartitaWidget(self.db_manager)
        self.inserimento_sub_tabs.addTab(self.operazioni_partita_widget_ref, "Operazioni")

        self.registra_consultazione_widget_ref = RegistraConsultazioneWidget(self.db_manager, self.logged_in_user_info)
        self.inserimento_sub_tabs.addTab(self.registra_consultazione_widget_ref, "Reg. Consultazione")

        # Widget di gestione (solo per admin)
        if self.logged_in_user_info and self.logged_in_user_info.get('ruolo') == 'admin':
            self.gestione_tipi_localita_widget = GestioneTipiLocalitaWidget(self.db_manager)
            self.inserimento_sub_tabs.addTab(self.gestione_tipi_localita_widget, "Tipi Località")

            self.gestione_periodi_widget = GestionePeriodiStoriciWidget(self.db_manager)
            self.inserimento_sub_tabs.addTab(self.gestione_periodi_widget, "Periodi")

        # Tooltip per i sotto-tab di inserimento
        tab_idx = 0
        self.inserimento_sub_tabs.setTabToolTip(tab_idx, "Inserisci Nuovo Comune\nRegistra un nuovo comune nel database"); tab_idx += 1
        self.inserimento_sub_tabs.setTabToolTip(tab_idx, "Inserisci Nuovo Possessore\nAggiungi un nuovo possessore al database"); tab_idx += 1
        self.inserimento_sub_tabs.setTabToolTip(tab_idx, "Inserisci Nuova Partita\nCrea una nuova partita catastale"); tab_idx += 1
        self.inserimento_sub_tabs.setTabToolTip(tab_idx, "Inserisci Nuova Località\nAggiungi vie, piazze, borgate, ecc."); tab_idx += 1
        self.inserimento_sub_tabs.setTabToolTip(tab_idx, "Registrazione Proprietà\nRegistra una nuova proprietà completa con possessori e immobili"); tab_idx += 1
        self.inserimento_sub_tabs.setTabToolTip(tab_idx, "Operazioni Partita\nDuplica partite, trasferisci immobili, passaggio proprietà (voltura)"); tab_idx += 1
        self.inserimento_sub_tabs.setTabToolTip(tab_idx, "Registra Consultazione\nRegistra gli accessi all'archivio per tracciabilità"); tab_idx += 1
        
        if self.logged_in_user_info and self.logged_in_user_info.get('ruolo') == 'admin':
            self.inserimento_sub_tabs.setTabToolTip(tab_idx, "Gestione Tipi Località\nGestisci le tipologie di località (Via, Piazza, ecc.)"); tab_idx += 1
            self.inserimento_sub_tabs.setTabToolTip(tab_idx, "Gestione Periodi Storici\nDefinisci i periodi storici di riferimento")

        layout_inserimento.addWidget(self.inserimento_sub_tabs)
        self.tabs.addTab(inserimento_contenitore, "Inserimento")

        # 5. Altri Tab
        self.esportazioni_widget_ref = EsportazioniWidget(self.db_manager)
        self.tabs.addTab(self.esportazioni_widget_ref, "📤 Esportazioni")

        self.reportistica_widget_ref = ReportisticaWidget(self.db_manager)
        self.tabs.addTab(self.reportistica_widget_ref, "Report")

        self.statistiche_widget_ref = StatisticheWidget(self.db_manager)
        self.tabs.addTab(self.statistiche_widget_ref, "Statistiche")

        # Conta i tab per i tooltip (utile per i tab condizionali)
        main_tab_idx = 0
        self.tabs.setTabToolTip(main_tab_idx, "Home / Dashboard\nPannello principale con statistiche e accesso rapido"); main_tab_idx += 1
        self.tabs.setTabToolTip(main_tab_idx, "Consultazione e Modifica\nVisualizza e modifica comuni, partite e possessori"); main_tab_idx += 1
        
        if FUZZY_SEARCH_AVAILABLE:
            self.tabs.setTabToolTip(main_tab_idx, "Ricerca Globale\nRicerca fuzzy avanzata in tutto il database"); main_tab_idx += 1
        
        self.tabs.setTabToolTip(main_tab_idx, "Inserimento e Gestione\nInserisci nuovi dati e gestisci le proprietà"); main_tab_idx += 1
        self.tabs.setTabToolTip(main_tab_idx, "Esportazioni Massive\nEsporta dati in CSV, Excel e PDF"); main_tab_idx += 1
        self.tabs.setTabToolTip(main_tab_idx, "Reportistica\nGenera report dettagliati e certificati"); main_tab_idx += 1
        self.tabs.setTabToolTip(main_tab_idx, "Statistiche e Viste\nVisualizza statistiche e gestisci le viste materializzate"); main_tab_idx += 1

        # 6. Tab Admin
        if self.logged_in_user_info and self.logged_in_user_info.get('ruolo') == 'admin':
            self.gestione_utenti_widget_ref = GestioneUtentiWidget(self.db_manager, self.logged_in_user_info)
            self.tabs.addTab(self.gestione_utenti_widget_ref, "Utenti")
            self.tabs.setTabToolTip(main_tab_idx, "Gestione Utenti\nGestisci utenti, ruoli e permessi"); main_tab_idx += 1

            sistema_contenitore = QWidget()
            layout_sistema = QVBoxLayout(sistema_contenitore)

            self.audit_viewer_widget_ref = AuditLogViewerWidget(self.db_manager)
            self.sistema_sub_tabs.addTab(self.audit_viewer_widget_ref, "Log Audit")

            self.backup_restore_widget_ref = BackupWidget(self.db_manager)
            self.sistema_sub_tabs.addTab(self.backup_restore_widget_ref, "Backup/Ripristino")

            # Tooltip per i sotto-tab di sistema
            self.sistema_sub_tabs.setTabToolTip(0, "Log di Audit\nVisualizza tutte le operazioni effettuate nel sistema")
            self.sistema_sub_tabs.setTabToolTip(1, "Backup/Ripristino DB\nEsegui backup del database o ripristina da backup esistente")

            layout_sistema.addWidget(self.sistema_sub_tabs)
            self.tabs.addTab(sistema_contenitore, "Sistema")
            self.tabs.setTabToolTip(main_tab_idx, "Sistema\nConfigurazione, backup, log di audit")

        self.tabs.setCurrentIndex(0)
        self.logger.info("Setup dei tab completato con nomi abbreviati e tooltip.")
    def activate_tab_and_sub_tab(self, main_tab_name: str, sub_tab_name: str, activate_report_sub_tab: bool = False):
        self.logger.info(
            f"Richiesta attivazione: Tab Principale='{main_tab_name}', Sotto-Tab='{sub_tab_name}'")

        main_tab_index = -1
        for i in range(self.tabs.count()):
            if self.tabs.tabText(i) == main_tab_name:
                main_tab_index = i
                break

        if main_tab_index != -1:
            self.tabs.setCurrentIndex(main_tab_index)
            # Ora gestisci il sotto-tab
            main_tab_widget = self.tabs.widget(main_tab_index)
            # Se il tab principale contiene altri tab
            if isinstance(main_tab_widget, QTabWidget):
                sub_tab_index = -1
                for i in range(main_tab_widget.count()):
                    if main_tab_widget.tabText(i) == sub_tab_name:
                        sub_tab_index = i
                        break
                if sub_tab_index != -1:
                    main_tab_widget.setCurrentIndex(sub_tab_index)

                    # Logica specifica se si attiva un sotto-tab della Reportistica
                    if activate_report_sub_tab and main_tab_name == "Reportistica":
                        if hasattr(self, 'reportistica_widget_ref') and self.reportistica_widget_ref:
                            # Il widget ReportisticaWidget stesso è un QTabWidget
                            report_tabs = self.reportistica_widget_ref.findChild(
                                QTabWidget)  # Cerca il QTabWidget interno
                            if report_tabs:
                                target_report_tab_index = -1
                                for i in range(report_tabs.count()):
                                    # sub_tab_name qui è il nome del report specifico
                                    if report_tabs.tabText(i) == sub_tab_name:
                                        target_report_tab_index = i
                                        break
                                if target_report_tab_index != -1:
                                    report_tabs.setCurrentIndex(
                                        target_report_tab_index)
                                    self.logger.info(
                                        f"Attivato sotto-tab '{sub_tab_name}' in Reportistica.")
                                else:
                                    self.logger.warning(
                                        f"Sotto-tab report '{sub_tab_name}' non trovato in Reportistica.")
                            else:
                                self.logger.warning(
                                    "QTabWidget interno non trovato in ReportisticaWidget per attivare sotto-tab.")
                else:
                    self.logger.warning(
                        f"Sotto-tab '{sub_tab_name}' non trovato nel tab principale '{main_tab_name}'.")
            elif main_tab_widget is not None:  # Il tab principale è un widget diretto, non un QTabWidget
                self.logger.info(
                    f"Tab principale '{main_tab_name}' attivato (è un widget diretto).")
            else:
                self.logger.error(
                    f"Widget per il tab principale '{main_tab_name}' non trovato (None).")
        else:
            self.logger.error(f"Tab principale '{main_tab_name}' non trovato.")

    @pyqtSlot(int)
    def handle_comune_appena_inserito(self, nuovo_comune_id: int):
        self.logger.info(
            f"SLOT handle_comune_appena_inserito ESEGUITO per nuovo comune ID: {nuovo_comune_id}")
        if hasattr(self, 'elenco_comuni_widget_ref') and self.elenco_comuni_widget_ref:
            self.logger.info(
                f"Riferimento a ElencoComuniWidget ({id(self.elenco_comuni_widget_ref)}) valido. Chiamata a load_data().")
            self.elenco_comuni_widget_ref.load_data() # <-- CORRETTO
        else:
            self.logger.warning(
                "Riferimento a ElencoComuniWidget è None o non esiste! Impossibile aggiornare la lista dei comuni.")


    def _handle_partita_creata_per_operazioni(self, nuova_partita_id: int, comune_id_partita: int,
                                              target_operazioni_widget: OperazioniPartitaWidget):
        """
        Slot per gestire la creazione di una nuova partita e il passaggio al tab
        delle operazioni collegate, pre-compilando l'ID.
        """
        logging.getLogger("CatastoGUI").info(
            f"Nuova Partita ID {nuova_partita_id} (Comune ID {comune_id_partita}) creata. Passaggio al tab Operazioni.")

        # Trova l'indice del tab principale "Inserimento"
        idx_tab_inserimento = -1
        for i in range(self.tabs.count()):
            if self.tabs.tabText(i) == "Inserimento":
                idx_tab_inserimento = i
                break

        if idx_tab_inserimento != -1:
            # Vai al tab principale "Inserimento"
            self.tabs.setCurrentIndex(idx_tab_inserimento)

            # Ora, all'interno di questo tab, trova il sotto-tab "Operazioni su Partita"
            # e imposta il suo indice corrente.
            # Assumiamo che self.inserimento_sub_tabs sia l'attributo corretto che contiene OperazioniPartitaWidget.
            if hasattr(self, 'inserimento_sub_tabs'):
                idx_sotto_tab_operazioni = -1
                for i in range(self.inserimento_sub_tabs.count()):
                    # Controlla se il widget del sotto-tab è l'istanza che ci interessa
                    if self.inserimento_sub_tabs.widget(i) == target_operazioni_widget:
                        idx_sotto_tab_operazioni = i
                        break

                if idx_sotto_tab_operazioni != -1:
                    self.inserimento_sub_tabs.setCurrentIndex(
                        idx_sotto_tab_operazioni)
                    # Chiama il metodo su OperazioniPartitaWidget per impostare l'ID
                    target_operazioni_widget.seleziona_e_carica_partita_sorgente(
                        nuova_partita_id)
                else:
                    logging.getLogger("CatastoGUI").error(
                        "Impossibile trovare il sotto-tab 'Operazioni su Partita' per il cambio automatico.")
            else:
                logging.getLogger("CatastoGUI").error(
                    "'self.inserimento_sub_tabs' non trovato in CatastoMainWindow.")
        else:
            logging.getLogger("CatastoGUI").error(
                "Impossibile trovare il tab principale 'Inserimento'.")
    @pyqtSlot(int)
    def handle_sub_tab_changed(self, index: int):
        """
        Gestisce il cambio di tab per i QTabWidget nidificati (sotto-tab).
        Carica i dati per il widget appena visualizzato.
        """
        # self.sender() ci restituisce l'oggetto che ha emesso il segnale (il QTabWidget interno)
        sender_tab_widget = self.sender()
        if not isinstance(sender_tab_widget, QTabWidget):
            self.logger.warning("handle_sub_tab_changed chiamato da un oggetto non QTabWidget.")
            return

        widget_to_load = sender_tab_widget.widget(index)

        if widget_to_load and hasattr(widget_to_load, 'load_initial_data'):
            try:
                # Chiamiamo il metodo per caricare i suoi dati (verrà eseguito solo la prima volta)
                self.logger.info(f"Sub-tab cambiato: avvio lazy loading per {widget_to_load.__class__.__name__}.")
                widget_to_load.load_initial_data()
            except Exception as e:
                self.logger.error(f"Errore durante il lazy loading del sotto-widget '{widget_to_load.__class__.__name__}': {e}", exc_info=True)
                QMessageBox.critical(self, "Errore Caricamento Widget", f"Impossibile caricare i dati per la sezione selezionata:\n{e}")

    # In gui_main.py, SOSTITUISCI il vecchio handle_main_tab_changed con questo:

    def handle_tab_changed(self, index: int):
        """
        Gestore universale per il cambio di tab (principali o sotto-tab).
        Implementa il lazy loading per il widget appena visualizzato.
        """
        if not self.db_manager or not self.db_manager.pool:
            return

        # self.sender() ci dice quale QTabWidget ha emesso il segnale
        tab_widget = self.sender()
        if not isinstance(tab_widget, QTabWidget):
            self.logger.warning("handle_tab_changed chiamato da un oggetto non QTabWidget.")
            return

        widget_to_load = tab_widget.widget(index)

        # Se il widget appena attivato è un contenitore per altri sotto-tab,
        # dobbiamo caricare il primo dei suoi figli.
        if widget_to_load:
            sub_tabs = widget_to_load.findChildren(QTabWidget)
            if sub_tabs:
                widget_to_load = sub_tabs[0].currentWidget()

        # Infine, se abbiamo un widget valido, chiamiamo il suo metodo di lazy loading.
        if hasattr(widget_to_load, 'load_initial_data'):
            try:
                widget_to_load.load_initial_data()
            except Exception as e:
                self.logger.error(f"Errore durante il lazy loading del widget '{widget_to_load.__class__.__name__}': {e}", exc_info=True)
                QMessageBox.critical(self, "Errore Caricamento Widget", f"Impossibile caricare i dati per la sezione selezionata:\n{e}")

    def update_ui_based_on_role(self):
        self.logger.info(
            ">>> CatastoMainWindow: Chiamata a update_ui_based_on_role")
        ruolo = None
        is_admin_offline_mode = False

        # Determina se siamo in modalità offline o se un utente è loggato
        # La pool_initialized_successful è un attributo di CatastoMainWindow.
        # logged_in_user_info è un dizionario con i dettagli dell'utente.

        # Scenario 1: Modalità Admin Offline (DB non connesso in modo normale)
        # Questo si verifica quando self.pool_initialized_successful è False.
        if not self.pool_initialized_successful:
            if self.logged_in_user_info and self.logged_in_user_info.get('ruolo') == 'admin_offline':
                is_admin_offline_mode = True
                ruolo = 'admin_offline'  # Ruolo fittizio per la gestione UI in questa modalità
            else:
                # Se pool_initialized_successful è False ma non siamo admin_offline,
                # significa che la connessione è fallita e l'utente non ha scelto admin_offline.
                # In questo caso, nessun ruolo "normale" è valido per abilitare i tab.
                ruolo = None  # Nessun ruolo normale per abilitare i tab
        else:
            # Scenario 2: Database connesso normalmente
            if self.logged_in_user_info:
                ruolo = self.logged_in_user_info.get('ruolo')
            else:
                # Questo caso non dovrebbe succedere con il flusso attuale (dopo login, user_info non è None)
                # Ma per sicurezza, se non c'è user_info, il ruolo è None.
                ruolo = None

        is_admin = (ruolo == 'admin')
        is_archivista = (ruolo == 'archivista')
        is_consultatore = (ruolo == 'consultatore')

        self.logger.debug(
            f"update_ui_based_on_role: Ruolo effettivo considerato: {ruolo}, is_admin_offline: {is_admin_offline_mode}")

        # La logica di abilitazione dei tab principali si basa sul ruolo e sullo stato della connessione.
        # db_ready_for_normal_ops è True solo se il pool è inizializzato con successo E NON siamo in modalità admin_offline.
        db_ready_for_normal_ops = self.pool_initialized_successful and not is_admin_offline_mode

        # Determina lo stato di abilitazione per ciascun tipo di funzionalità
        # Consultazione e Modifica (Principale, Ricerca Partite, Ricerca Possessori, Ricerca Immobili Avanzata)
        consultazione_enabled = db_ready_for_normal_ops

        # Inserimento (Nuovo Comune, Nuovo Possessore, Nuova Località, Registrazione Proprietà, Operazioni Partita, Registra Consultazione)
        inserimento_enabled = db_ready_for_normal_ops and (
            is_admin or is_archivista)

        # Esportazioni (Partita, Possessore)
        esportazioni_enabled = db_ready_for_normal_ops and (
            is_admin or is_archivista or is_consultatore)  # Tutti gli utenti normali

        # Reportistica (Report Proprietà, Genealogico, Possessore, Consultazioni)
        reportistica_enabled = db_ready_for_normal_ops and (
            is_admin or is_archivista or is_consultatore)  # Tutti gli utenti normali

        # Statistiche e Viste (Statistiche per Comune, Immobili per Tipologia, Manutenzione Database)
        statistiche_enabled = db_ready_for_normal_ops and (
            is_admin or is_archivista)  # Generalmente per ruoli più gestionali

        # Gestione Utenti (Solo per admin connessi normalmente)
        gestione_utenti_enabled = db_ready_for_normal_ops and is_admin

        # Sistema (Log di Audit, Backup/Ripristino DB, Amministrazione DB)
        # Accessibile per admin normali O per admin_offline (per setup DB iniziale)
        sistema_enabled = is_admin or is_admin_offline_mode

        # Applica lo stato di abilitazione ai tab
        tab_indices = {self.tabs.tabText(
            i): i for i in range(self.tabs.count())}

        if "Consultazione e Modifica" in tab_indices:
            self.tabs.setTabEnabled(
                tab_indices["Consultazione e Modifica"], consultazione_enabled)
            self.logger.debug(
                f"Tab 'Consultazione e Modifica' abilitato: {consultazione_enabled}")

        if "Inserimento" in tab_indices:
            self.tabs.setTabEnabled(
                tab_indices["Inserimento"], inserimento_enabled)
            self.logger.debug(
                f"Tab 'Inserimento' abilitato: {inserimento_enabled}")

        if "Esportazioni" in tab_indices:
            self.tabs.setTabEnabled(
                tab_indices["Esportazioni"], esportazioni_enabled)
            self.logger.debug(
                f"Tab 'Esportazioni' abilitato: {esportazioni_enabled}")

        if "Reportistica" in tab_indices:
            self.tabs.setTabEnabled(
                tab_indices["Reportistica"], reportistica_enabled)
            self.logger.debug(
                f"Tab 'Reportistica' abilitato: {reportistica_enabled}")

        if "Statistiche e Viste" in tab_indices:
            self.tabs.setTabEnabled(
                tab_indices["Statistiche e Viste"], statistiche_enabled)
            self.logger.debug(
                f"Tab 'Statistiche e Viste' abilitato: {statistiche_enabled}")

        # Il tab "Gestione Utenti" è un tab diretto, non un sotto-tab. Se è stato aggiunto come tale.
        # Se invece è un sotto-tab di "Sistema", allora il controllo è sul sotto-tab specifico.
        # Data la tua struttura: self.tabs.addTab(self.gestione_utenti_widget_ref, "Gestione Utenti")
        if "Gestione Utenti" in tab_indices:
            self.tabs.setTabEnabled(
                tab_indices["Gestione Utenti"], gestione_utenti_enabled)
            self.logger.debug(
                f"Tab 'Gestione Utenti' abilitato: {gestione_utenti_enabled}")

        if "Sistema" in tab_indices:
            self.tabs.setTabEnabled(tab_indices["Sistema"], sistema_enabled)
            self.logger.debug(f"Tab 'Sistema' abilitato: {sistema_enabled}")

            # Se siamo in modalità admin_offline, forza la selezione del tab "Sistema" -> "Amministrazione DB"
            if sistema_enabled and is_admin_offline_mode:
                self.tabs.setCurrentIndex(tab_indices["Sistema"])
                if hasattr(self, 'sistema_sub_tabs'):
                    admin_db_ops_tab_index = -1
                    # Cerca il sotto-tab "Amministrazione DB" all'interno del QTabWidget self.sistema_sub_tabs
                    for i in range(self.sistema_sub_tabs.count()):
                        if self.sistema_sub_tabs.tabText(i) == "Amministrazione DB":
                            admin_db_ops_tab_index = i
                            break
                    if admin_db_ops_tab_index != -1:
                        self.sistema_sub_tabs.setCurrentIndex(
                            admin_db_ops_tab_index)
                        self.logger.debug(
                            "Tab 'Sistema' -> 'Amministrazione DB' selezionato per modalità offline.")
                    else:
                        self.logger.warning(
                            "Sotto-tab 'Amministrazione DB' non trovato nel tab 'Sistema'.")
                else:
                    self.logger.warning(
                        "self.sistema_sub_tabs non è un QTabWidget o non è stato inizializzato.")

        # Abilitazione/Disabilitazione del pulsante Logout
        if hasattr(self, 'logout_button'):
            self.logout_button.setEnabled(
                not is_admin_offline_mode and bool(self.logged_in_user_id))

        self.logger.info("update_ui_based_on_role completato.")

    def apri_dialog_inserimento_comune(self):  # Metodo integrato nella classe
        if not self.db_manager:
            QMessageBox.critical(
                self, "Errore", "Manager Database non inizializzato.")
            return
        if not self.logged_in_user_info:
            QMessageBox.warning(self, "Login Richiesto",
                                "Effettuare il login per procedere.")
            return

        ruolo_utente = self.logged_in_user_info.get('ruolo')
        if ruolo_utente not in ['admin', 'archivista']:
            QMessageBox.warning(self, "Accesso Negato",
                                "Non si dispone delle autorizzazioni necessarie per aggiungere un comune.")
            return

        utente_login_username = self.logged_in_user_info.get(
            'username', 'log_utente_sconosciuto')

        dialog = InserimentoComuneWidget(
            self.db_manager, utente_login_username, self)  # Passa 'self' come parent
        if dialog.exec_() == QDialog.Accepted:
            logging.getLogger("CatastoGUI").info(
                f"Dialogo inserimento comune chiuso con successo da utente '{utente_login_username}'.")
            QMessageBox.information(
                self, "Comune Aggiunto", "Il nuovo comune è stato registrato con successo.")
            # Aggiorna la vista dell'elenco comuni se presente nel tab consultazione
            # Questo ciclo cerca il widget ElencoComuniWidget tra i sotto-tab di consultazione
            if hasattr(self, 'consultazione_sub_tabs'):
                for i in range(self.consultazione_sub_tabs.count()):
                    widget = self.consultazione_sub_tabs.widget(i)
                    if isinstance(widget, ElencoComuniWidget):
                        widget.load_comuni_data()  # Assumendo che ElencoComuniWidget abbia questo metodo
                        logging.getLogger("CatastoGUI").info(
                            "Principale nel tab consultazione aggiornato.")
                        break
        else:
            logging.getLogger("CatastoGUI").info(
                f"Dialogo inserimento comune annullato da utente '{utente_login_username}'.")

    def _apri_dialogo_configurazione_db(self):
        """Apre il dialogo di configurazione DB, pre-compilandolo con i valori correnti."""
        self.logger.info("Apertura dialogo configurazione DB dal menu.")
        settings = QSettings()

        # Raccoglie la configurazione attuale da QSettings
        current_config = {
            "db_type": settings.value("Database/Type", "local", type=str),
            "host": settings.value("Database/Host", "localhost", type=str),
            "port": settings.value("Database/Port", 5432, type=int),
            "dbname": settings.value("Database/DBName", "catasto_storico", type=str),
            "user": settings.value("Database/User", "postgres", type=str)
        }

        # Passa il dizionario di configurazione usando il nome corretto del parametro
        config_dialog = DBConfigDialog(self, initial_config=current_config)

        if config_dialog.exec_() == QDialog.Accepted:
            QMessageBox.information(
                self, "Riavvio Necessario",
                "Le nuove impostazioni del database sono state salvate.\n"
                "È necessario riavviare l'applicazione per applicarle."
            )
            # Potremmo anche chiudere l'applicazione qui per forzare il riavvio
            # self.close()
    def handle_logout(self):
        if self.logged_in_user_id is not None and self.current_session_id and self.db_manager:
            # Chiama il logout_user del db_manager passando l'ID utente e l'ID sessione correnti
            if self.db_manager.logout_user(self.logged_in_user_id, self.current_session_id, self.client_ip_address_gui):
                QMessageBox.information(
                    self, "Logout", "Logout effettuato con successo.")
                logging.getLogger("CatastoGUI").info(
                    f"Logout utente ID {self.logged_in_user_id}, sessione {self.current_session_id[:8]}... registrato nel DB.")
            else:
                # Anche se la registrazione DB fallisce, procedi con il logout lato client
                QMessageBox.warning(
                    self, "Logout", "Logout effettuato. Errore durante la registrazione remota del logout.")
                logging.getLogger("CatastoGUI").warning(
                    f"Logout utente ID {self.logged_in_user_id}, sessione {self.current_session_id[:8]}... Errore registrazione DB.")

            # Resetta le informazioni utente e sessione nella GUI
            self.logged_in_user_id = None
            self.logged_in_user_info = None
            self.current_session_id = None  # IMPORTANTE: Resetta l'ID sessione

            # Aggiorna l'interfaccia utente
            self.user_status_label.setText("Utente: Nessuno")
            # Potresti voler cambiare lo stato del DB qui, ma di solito rimane "Connesso"
            # self.db_status_label.setText("Database: Connesso (Logout effettuato)")
            self.logout_button.setEnabled(False)

            self.tabs.clear()  # Rimuove tutti i tab
            # Potresti voler re-inizializzare i tab in uno stato "non loggato" o semplicemente chiudere.
            # Per ora, chiudiamo l'applicazione dopo il logout per semplicità.
            self.statusBar().showMessage("Logout effettuato. L'applicazione verrà chiusa.")

            # Chiude l'applicazione dopo un breve ritardo per permettere all'utente di leggere il messaggio
            from PyQt5.QtCore import QTimer
            QTimer.singleShot(1500, self.close)  # Chiude dopo 1.5 secondi

        else:
            logging.getLogger("CatastoGUI").warning(
                "Tentativo di logout senza una sessione utente valida o db_manager.")

    def closeEvent(self, event: QCloseEvent):
        logging.getLogger("CatastoGUI").info(
            "Evento closeEvent intercettato in CatastoMainWindow.")

        if hasattr(self, 'db_manager') and self.db_manager:
            pool_era_attivo = self.db_manager.pool is not None

            if pool_era_attivo:
                # Se un utente è loggato con una sessione attiva, esegui il logout
                if self.logged_in_user_id is not None and self.current_session_id:
                    logging.getLogger("CatastoGUI").info(
                        f"Chiusura applicazione: logout di sicurezza per utente ID {self.logged_in_user_id}, sessione {self.current_session_id[:8]}...")
                    self.db_manager.logout_user(
                        self.logged_in_user_id, self.current_session_id, self.client_ip_address_gui)
                else:
                    # Se non c'è un utente loggato, ma il pool è attivo, logga un messaggio informativo
                    logging.getLogger("CatastoGUI").info(
                        "Chiusura applicazione: nessun utente loggato, ma il pool di connessioni era attivo.")
                    self.logger.info(
                        "Nessun utente/sessione attiva da loggare out esplicitamente, ma il pool era attivo.")
                   

            # Chiudi sempre il pool se esiste
            self.db_manager.close_pool()
            logging.getLogger("CatastoGUI").info(
                "Tentativo di chiusura del pool di connessioni al database completato durante closeEvent.")
        else:
            logging.getLogger("CatastoGUI").warning(
                "DB Manager non disponibile durante closeEvent o pool già None.")

        logging.getLogger("CatastoGUI").info(
            "Applicazione GUI Catasto Storico terminata via closeEvent.")
        event.accept()
   
    def _import_possessori_csv(self):
        """
        Gestisce il flusso di importazione dei possessori da CSV, chiamando la logica
        di importazione nel DB manager e visualizzando i risultati dettagliati.
        """
        try:
            # --- PASSO 1: Selezione del comune (invariato) ---
            comuni = self.db_manager.get_elenco_comuni_semplice()
            if not comuni:
                QMessageBox.warning(self, "Nessun Comune", "Nessun comune trovato nel database. Impossibile importare.")
                return

            nomi_comuni = [c[1] for c in comuni]
            nome_comune_selezionato, ok = QInputDialog.getItem(
                self, "Selezione Comune", "A quale comune vuoi associare i nuovi possessori?",
                nomi_comuni, 0, False
            )
            
            if not ok or not nome_comune_selezionato:
                return

            comune_id_selezionato = None
            for comun_id, comun_nome in comuni:
                if comun_nome == nome_comune_selezionato:
                    comune_id_selezionato = comun_id
                    break
            
            if comune_id_selezionato is None:
                QMessageBox.critical(self, "Errore", "Impossibile trovare l'ID del comune selezionato.")
                return

            # --- PASSO 2: Selezione del file CSV (invariato) ---
            file_path, _ = QFileDialog.getOpenFileName(
                self, "Seleziona il file CSV con i possessori", "",
                "File CSV (*.csv);;Tutti i file (*)"
            )

            if not file_path:
                return

            # --- PASSO 3: Avvia l'importazione e mostra il nuovo dialogo di riepilogo ---
            QApplication.setOverrideCursor(Qt.WaitCursor)
            
            # --- MODIFICA CHIAVE QUI ---
            # Chiamiamo il metodo del db_manager che ora restituisce un dizionario dettagliato.
            # Passiamo anche il nome del comune per poterlo visualizzare nel report di successo.
            import_results = self.db_manager.import_possessori_from_csv(
                file_path, comune_id_selezionato, nome_comune_selezionato
            )

            # Invece di una semplice QMessageBox, creiamo e mostriamo il nostro nuovo dialogo.
            result_dialog = CSVImportResultDialog(
                import_results.get('success', []),
                import_results.get('errors', []),
                self
            )
            result_dialog.exec_()
            # --- FINE MODIFICA ---

            # Dopo l'importazione, aggiorniamo la vista dei comuni per riflettere eventuali
            # cambiamenti (se ad esempio la vista mostrasse il numero di possessori).
            if self.elenco_comuni_widget_ref:
                self.elenco_comuni_widget_ref.load_data() # <-- CORRETTO

        except DBMError as e:
            self.logger.error(f"Errore DB durante il processo di importazione CSV: {e}", exc_info=True)
            QMessageBox.critical(self, "Errore Database", f"Si è verificato un errore di database:\n\n{e}")
        except Exception as e:
            self.logger.error(f"Errore imprevisto durante l'importazione CSV: {e}", exc_info=True)
            QMessageBox.critical(self, "Errore durante l'importazione", f"Si è verificato un errore imprevisto:\n\n{e}")
        finally:
            QApplication.restoreOverrideCursor()
    
    def _import_partite_csv(self):
        """
        Gestisce l'importazione di partite da un file CSV e mostra i risultati.
        """
        try:
            comuni = self.db_manager.get_elenco_comuni_semplice()
            if not comuni:
                QMessageBox.warning(self, "Nessun Comune", "Nessun comune trovato nel database. Impossibile importare.")
                return

            nomi_comuni = [c[1] for c in comuni]
            nome_comune_selezionato, ok = QInputDialog.getItem(
                self, "Selezione Comune", "A quale comune vuoi associare le nuove partite?", nomi_comuni, 0, False
            )
            if not ok or not nome_comune_selezionato:
                return

            comune_id_selezionato = next((cid for cid, cnome in comuni if cnome == nome_comune_selezionato), None)
            if comune_id_selezionato is None:
                QMessageBox.critical(self, "Errore", "Impossibile trovare l'ID del comune selezionato.")
                return

            file_path, _ = QFileDialog.getOpenFileName(
                self, "Seleziona il file CSV con le partite", "", "File CSV (*.csv);;Tutti i file (*)"
            )
            if not file_path:
                return

            QApplication.setOverrideCursor(Qt.WaitCursor)
            
            import_results = self.db_manager.import_partite_from_csv(file_path, comune_id_selezionato, nome_comune_selezionato)
            
            # Crea una versione dei dati di successo adatta al dialogo generico
            success_display_data = []
            for row in import_results.get('success', []):
                success_display_data.append({
                    'id': row.get('id'),
                    'nome_completo': f"Partita N.{row.get('numero_partita')} {row.get('suffisso_partita') or ''}".strip(),
                    'comune_nome': row.get('comune_nome')
                })

            result_dialog = CSVImportResultDialog(
                success_display_data,
                import_results.get('errors', []),
                self
            )
            result_dialog.setWindowTitle("Riepilogo Importazione Partite")
            result_dialog.exec_()
            
            if self.elenco_comuni_widget_ref:
                self.elenco_comuni_widget_ref.load_data() 

        except Exception as e:
            self.logger.error(f"Errore imprevisto durante l'importazione CSV delle partite: {e}", exc_info=True)
            QMessageBox.critical(self, "Errore Importazione", f"Si è verificato un errore non gestito: {e}")
        finally:
            QApplication.restoreOverrideCursor()
    def check_mv_refresh_status(self):
        """
        Controlla il timestamp dell'ultimo aggiornamento e mostra la barra di notifica se i dati sono obsoleti.
        """
        from datetime import timedelta, timezone
        if not self.db_manager or not self.db_manager.pool: return
        # --- MODIFICA QUI: Leggiamo il valore da QSettings ---
        settings = QSettings()
        threshold_hours = settings.value("General/StaleDataThresholdHours", 24, type=int)
        # ----------------------------------------------------

        last_refresh = self.db_manager.get_last_mv_refresh_timestamp()
        if last_refresh is None:
            # Se non c'è mai stato un refresh, consideriamo i dati obsoleti
            self.stale_data_label.setText("I dati delle statistiche non sono mai stati aggiornati.")
            self.stale_data_bar.show()
            return
        
        # Usiamo la soglia personalizzata
        staleness_threshold = timedelta(hours=threshold_hours)
        time_since_refresh = datetime.now(timezone.utc) - last_refresh

        if time_since_refresh > staleness_threshold:
            hours_ago = int(time_since_refresh.total_seconds() / 3600)
            # Mostriamo la soglia impostata nel messaggio
            self.stale_data_label.setText(f"I dati delle statistiche non sono aggiornati da circa {hours_ago} ore (soglia: {threshold_hours} ore).")
            self.stale_data_bar.show()
        else:
            self.stale_data_bar.hide()
    def _apri_dialogo_impostazioni_aggiornamento(self):
        """
        Apre un dialogo per permettere all'utente di impostare la soglia (in ore)
        per considerare i dati delle viste materializzate come obsoleti.
        """
        settings = QSettings()
        
        # Legge il valore corrente per mostrarlo come default (default a 24 se non esiste)
        current_threshold = settings.value("General/StaleDataThresholdHours", 24, type=int)
        
        # Apre un dialogo per l'inserimento di un numero intero
        new_threshold, ok = QInputDialog.getInt(
            self,
            "Soglia Aggiornamento Dati",
            "Dopo quante ore i dati delle statistiche devono essere considerati obsoleti?",
            value=current_threshold, # Valore di partenza
            min=1,                 # Minimo 1 ora
            max=720,               # Massimo 30 giorni (720 ore)
            step=1                 # Incremento di 1
        )
        
        # Se l'utente preme "OK" e il valore è valido
        if ok:
            # Salva il nuovo valore nelle impostazioni dell'applicazione
            settings.setValue("General/StaleDataThresholdHours", new_threshold)
            QMessageBox.information(self, "Impostazione Salvata",
                                    f"La nuova soglia di {new_threshold} ore è stata salvata.\n"
                                    "La modifica sarà effettiva al prossimo riavvio dell'applicazione.")


    def _handle_stale_data_refresh_click(self):
        """Gestisce il click sul pulsante 'Aggiorna Ora' della barra di notifica."""
        # Nascondiamo subito la barra per dare un feedback immediato
        self.stale_data_bar.hide()
        
        # Chiamiamo la funzione di refresh esistente, mostrando il messaggio di successo
        self.db_manager.refresh_materialized_views(show_success_message=True)
    def _apri_manuale_utente(self):
        """
        Apre il file PDF del manuale utente situato nella cartella 'resources'.
        """
        try:
            # Lista di percorsi possibili per il manuale
            possible_paths = []
            
            # Percorso 1: Usando get_resource_path (originale)
            try:
                manual_path_1 = get_resource_path(os.path.join("resources", "manuale_utente.pdf"))
                possible_paths.append(manual_path_1)
            except:
                pass
            
            # Percorso 2: Relativo all'eseguibile
            if getattr(sys, 'frozen', False):
                # Applicazione compilata
                exe_dir = os.path.dirname(sys.executable)
                manual_path_2 = os.path.join(exe_dir, "resources", "manuale_utente.pdf")
                possible_paths.append(manual_path_2)
                
                # Percorso 3: Nella cartella _internal (PyInstaller)
                manual_path_3 = os.path.join(exe_dir, "_internal", "resources", "manuale_utente.pdf")
                possible_paths.append(manual_path_3)
            
            # Percorso 4: Relativo allo script principale
            base_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
            manual_path_4 = os.path.join(base_dir, "resources", "manuale_utente.pdf")
            possible_paths.append(manual_path_4)
            
            # Percorso 5: Directory corrente
            manual_path_5 = os.path.join(os.getcwd(), "resources", "manuale_utente.pdf")
            possible_paths.append(manual_path_5)
            
            # Cerca il primo percorso valido
            found_path = None
            for path in possible_paths:
                if os.path.exists(path):
                    found_path = path
                    break
            
            if found_path:
                self.logger.info(f"Manuale trovato al percorso: {found_path}")
                QDesktopServices.openUrl(QUrl.fromLocalFile(found_path))
            else:
                # Log di debug per vedere tutti i percorsi tentati
                self.logger.error(f"Manuale non trovato. Percorsi tentati:")
                for i, path in enumerate(possible_paths, 1):
                    self.logger.error(f"  {i}. {path}")
                
                QMessageBox.warning(self, "Manuale Non Trovato",
                                f"Il file del manuale utente non è stato trovato.\n\n"
                                f"Percorsi verificati:\n" + 
                                "\n".join([f"• {path}" for path in possible_paths[:3]]))
                                
        except Exception as e:
            self.logger.error(f"Errore imprevisto durante l'apertura del manuale: {e}", exc_info=True)
            QMessageBox.critical(self, "Errore", f"Impossibile aprire il manuale:\n{e}")
            
    def _show_backup_settings_dialog(self):
        dialog = BackupReminderSettingsDialog(self)
        dialog.exec_()



def setup_logging():
    """Configura il logging per scrivere nella cartella AppData dell'utente."""
    # Imposta i metadati dell'applicazione per creare un percorso univoco
    QCoreApplication.setOrganizationName("ArchivioDiStatoSavona")
    QCoreApplication.setApplicationName("Meridiana")

    # Trova la cartella standard e scrivibile per i dati dell'applicazione
    app_data_path = QStandardPaths.writableLocation(QStandardPaths.AppLocalDataLocation)

    # Assicurati che la cartella esista
    os.makedirs(app_data_path, exist_ok=True)

    # Percorso completo del file di log
    log_file_path = os.path.join(app_data_path, "meridiana_session.log")

    # Configura il logger principale (root logger)
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s'
    logging.basicConfig(level=logging.INFO,
                        format=log_format,
                        handlers=[
                            logging.FileHandler(log_file_path, mode='a', encoding='utf-8'),
                            logging.StreamHandler(sys.stdout)
                        ])

    logging.info(f"Logging configurato. I log verranno salvati in: {log_file_path}")
    
# Inserisci questa funzione in gui_main.py

def setup_global_logging():
    """
    Configura il logging in modo centralizzato e sicuro, scrivendo i file
    nella cartella AppData dell'utente, che e' sempre scrivibile.
    """
    # Imposta i metadati necessari a PyQt per trovare il percorso corretto
    QCoreApplication.setOrganizationName("ArchivioDiStatoSavona")
    QCoreApplication.setApplicationName("Meridiana")
    
    # Ottieni il percorso standard e scrivibile per i dati dell'applicazione
    app_data_path = QStandardPaths.writableLocation(QStandardPaths.AppLocalDataLocation)
    
    # Assicurati che la cartella esista
    os.makedirs(app_data_path, exist_ok=True)
    
    # Percorso completo del file di log
    log_file_path = os.path.join(app_data_path, "meridiana_session.log")
    
    # Configura il logger usando basicConfig, che pulisce ogni handler precedente.
    # 'force=True' (per Python 3.8+) assicura che questa configurazione sovrascriva tutto.
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s',
        handlers=[
            logging.FileHandler(log_file_path, mode='a', encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ],
        force=True 
    )
    
    logging.info(f"Logging configurato. I log verranno salvati in: {log_file_path}")

def run_gui_app():
    try:
        app = QApplication(sys.argv)
        # --- INIZIO MODIFICA ---
        # Imposta i metadati dell'applicazione.
        # Questo è FONDAMENTALE affinché QStandardPaths possa generare
        # percorsi di dati scrivibili e univoci per l'app.
        QCoreApplication.setOrganizationName("Marco Santoro")
        QCoreApplication.setApplicationName("Meridiana")
        # --- FINE MODIFICA ---

        # --- CHIAMATA ALLA NUOVA FUNZIONE QUI ---
        # Questo imposta il logging per l'intera applicazione prima che qualsiasi
        # altra cosa venga importata o eseguita.
        setup_global_logging()
        # --- FINE CHIAMATA ---

        # Ora puoi ottenere il logger già configurato
        gui_logger = logging.getLogger("CatastoGUI")

        # Il resto della funzione rimane identico...
        client_ip_address_gui = get_local_ip_address()
        gui_logger.info(f"Indirizzo IP locale identificato: {client_ip_address_gui}")

        settings = QSettings()
        current_style_file = settings.value("UI/CurrentStyle", "meridiana_style.qss", type=str)
        stylesheet = load_stylesheet(current_style_file)
        if stylesheet:
            app.setStyleSheet(stylesheet)
        # --- FINE MODIFICA ---
        # --- INIZIO BLOCCO CONTROLLO EULA ---
        settings = QSettings()
        eula_accepted = settings.value("EULA/accepted", False, type=bool)

        if not eula_accepted:
            eula_dialog = EulaDialog()
            if eula_dialog.exec_() == QDialog.Accepted:
                # L'utente ha accettato, salva l'impostazione e procedi
                settings.setValue("EULA/accepted", True)
                settings.sync()
            else:
                # L'utente ha rifiutato, esci dall'applicazione
                sys.exit(0)
        # --- FINE BLOCCO CONTROLLO EULA ---
        
        gui_logger.info("Avvio dell'applicazione GUI Catasto Storico...")
        db_manager_gui: Optional[CatastoDBManager] = None
        main_window_instance = CatastoMainWindow(client_ip_address_gui)

        # --- NUOVO FLUSSO DI AVVIO ---

         # 1. TENTATIVO DI CONNESSIONE AUTOMATICA
        gui_logger.info("Tentativo di connessione automatica con le impostazioni salvate...")
        
        # --- CORREZIONE: Gestisci la password in modo più robusto ---
        saved_password = settings.value(SETTINGS_DB_PASSWORD, "", type=str)
        
        # Se non c'è password salvata, prova a prenderla dal keyring
        if not saved_password:
            db_host = settings.value(SETTINGS_DB_HOST, "localhost", type=str)
            db_user = settings.value(SETTINGS_DB_USER, "postgres", type=str)
            saved_password = get_password_from_keyring(db_host, db_user)
        
        saved_config = {
            "host": settings.value(SETTINGS_DB_HOST, "localhost", type=str),
            "port": settings.value(SETTINGS_DB_PORT, 5432, type=int),
            "dbname": settings.value(SETTINGS_DB_NAME, "catasto_storico", type=str),
            "user": settings.value(SETTINGS_DB_USER, "postgres", type=str),
            "password": saved_password or ""  # Assicurati che ci sia sempre una password (anche vuota)
        }
        
        # Prova a connettere solo se sono presenti i dati essenziali E la password
        if saved_config["dbname"] and saved_config["user"] and saved_config["password"]:
            try:
                db_manager_gui = CatastoDBManager(**saved_config)
                if db_manager_gui.initialize_main_pool():
                    main_window_instance.db_manager = db_manager_gui
                    main_window_instance.pool_initialized_successful = True
                    gui_logger.info("Connessione automatica riuscita.")
                else:
                    db_manager_gui = None # Resetta se fallisce
            except Exception as e:
                gui_logger.warning(f"Errore durante la creazione di CatastoDBManager: {e}")
                db_manager_gui = None
        else:
            gui_logger.info("Dati di connessione incompleti (manca password o altri parametri essenziali). Skip connessione automatica.")
            db_manager_gui = None
        # --- FINE CORREZIONE ---
        
        # 2. FALLBACK A CONFIGURAZIONE MANUALE se la connessione automatica è fallita
        if not db_manager_gui or not db_manager_gui.pool:
            gui_logger.warning("Connessione automatica fallita. Apertura dialogo di configurazione manuale.")
            QMessageBox.information(None, "Configurazione Database", "Impossibile connettersi con le impostazioni salvate. Apriamo la configurazione.")

            while True: # Loop per riprovare la configurazione manuale
                config_dialog = DBConfigDialog(parent=None)
                # --- INIZIO MODIFICA: Leggiamo le impostazioni AD OGNI ciclo ---
                db_type = settings.value("Database/Type", "local", type=str)
                db_host = settings.value("Database/Host", "localhost", type=str)
                db_port = settings.value("Database/Port", 5432, type=int)
                db_name = settings.value("Database/DBName", "catasto_storico", type=str)
                db_user = settings.value("Database/User", "postgres", type=str)
                db_password = get_password_from_keyring(db_host, db_user)
                # --- FINE MODIFICA ---
                
                if config_dialog.exec_() != QDialog.Accepted:
                    gui_logger.info("Configurazione manuale annullata. Uscita.")
                    sys.exit(0)

                current_config = config_dialog.get_config_values(include_password=True)
                
                # --- CORREZIONE: Filtra solo i parametri supportati da CatastoDBManager ---
                db_manager_params = {
                    'host': current_config.get('host'),
                    'port': current_config.get('port'), 
                    'dbname': current_config.get('dbname'),
                    'user': current_config.get('user'),
                    'password': current_config.get('password', '')  # Assicurati che ci sia sempre una password
                }
                
                # Rimuovi eventuali chiavi con valore None (ma mantieni password vuota se necessario)
                db_manager_params = {k: v for k, v in db_manager_params.items() if v is not None}
                
                # Assicurati che password sia sempre presente
                if 'password' not in db_manager_params:
                    db_manager_params['password'] = ''
                
                try:
                    db_manager_gui = CatastoDBManager(**db_manager_params)
                except Exception as e:
                    gui_logger.error(f"Errore creazione CatastoDBManager: {e}")
                    QMessageBox.critical(None, "Errore Configurazione", f"Errore nella configurazione del database: {e}")
                    continue  # Riprova il loop di configurazione
                # --- FINE CORREZIONE ---
                
                if db_manager_gui.initialize_main_pool():
                    main_window_instance.db_manager = db_manager_gui
                    main_window_instance.pool_initialized_successful = True
                    gui_logger.info("Connessione manuale riuscita.")
                    break # Esce dal loop di configurazione
                else:
                    # Mostra l'errore specifico e il loop continuerà, riaprendo il dialogo
                    error_details = db_manager_gui.get_last_connect_error_details() or {}
                    pgcode = error_details.get('pgcode')
                    pgerror_msg = error_details.get('pgerror')
                    
                    if pgcode == '28P01': 
                        QMessageBox.critical(None, "Errore Autenticazione", "Password o utente errati.")
                    else: 
                        QMessageBox.critical(None, "Errore Connessione", f"Impossibile connettersi.\n{pgerror_msg}")

        # 3. SE LA CONNESSIONE (auto o manuale) è OK, PROCEDI CON IL LOGIN UTENTE
        # --- INIZIO MODIFICA ---
        # Passiamo la variabile 'client_ip_address_gui' al costruttore del LoginDialog
        login_dialog = LoginDialog(db_manager_gui, client_ip_address_gui, parent=main_window_instance)
        # --- FINE MODIFICA ---
        if login_dialog.exec_() != QDialog.Accepted:
            gui_logger.info("Login utente annullato. Uscita.")
            sys.exit(0)

        # 4. LOGIN UTENTE OK, MOSTRA WELCOME SCREEN E AVVIA L'APP
        base_dir_app = os.path.dirname(os.path.abspath(sys.argv[0]))
        logo_path = get_logo_path()
        manuale_path = None
        if getattr(sys, 'frozen', False):
            exe_dir = os.path.dirname(sys.executable)
            possible_manual_paths = [
                os.path.join(exe_dir, "resources", "manuale_utente.pdf"),
                os.path.join(exe_dir, "_internal", "resources", "manuale_utente.pdf")
            ]
        else:
            base_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
            possible_manual_paths = [
                os.path.join(base_dir, "resources", "manuale_utente.pdf")
            ]

        welcome_screen = WelcomeScreen(parent=None, logo_path=logo_path, help_url=manuale_path)
        if welcome_screen.exec_() != QDialog.Accepted:
            gui_logger.info("Welcome screen chiusa. Uscita.")
            sys.exit(0)
            
        main_window_instance.perform_initial_setup(
            db_manager_gui,
            login_dialog.logged_in_user_id,
            login_dialog.logged_in_user_info,
            login_dialog.current_session_id_from_dialog
        )
        
        gui_logger.info("Setup completato. Avvio loop eventi.")
        sys.exit(app.exec_())

    except Exception as e:
        # Blocco di gestione crash (invariato)
        logging.basicConfig(filename='crash_report.log', level=logging.DEBUG)
        logging.exception("CRASH IMPREVISTO ALL'AVVIO:")
        QMessageBox.critical(None, "Errore Critico", f"Errore fatale: {e}\nControlla crash_report.log.")
        sys.exit(1)


if __name__ == "__main__":
    
    
    
    # Importa qui per evitare importazioni circolari (se necessario)
    import traceback
    
    try:
        run_gui_app()
    except Exception as e:
        # Log dell'errore critico
        logging.getLogger("CatastoGUI").critical(f"Errore critico all'avvio dell'applicazione: {e}", exc_info=True)
        traceback.print_exc()
        
        # Mostra messaggio di errore all'utente
        try:
            from PyQt5.QtWidgets import QApplication, QMessageBox
            if not QApplication.instance():
                app = QApplication(sys.argv)
            QMessageBox.critical(None, "Errore Critico", 
                               f"Si è verificato un errore critico:\n\n{str(e)}\n\n"
                               "Controlla il file catasto_gui.log per maggiori dettagli.")
        except:
            print(f"ERRORE CRITICO: {e}")
            print("Controlla il file catasto_gui.log per maggiori dettagli.")
        
        sys.exit(1)