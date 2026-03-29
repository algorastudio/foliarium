#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Foliarium — Archivio Catastale Storico
=======================================
Autore: Marco Santoro
Data: 18/05/2025
"""
import sys,bcrypt
from gui_widgets import UnifiedFuzzySearchWidget
import os
import logging
from datetime import datetime
from typing import Optional, Dict
# Importazioni PyQt6
from PyQt6.QtCore import (QSettings,
                          QStandardPaths, Qt, QTimer, QUrl,
                          pyqtSlot, pyqtSignal, QCoreApplication,
                          QPropertyAnimation, QEasingCurve)

from PyQt6.QtGui import (QCloseEvent, QDesktopServices, QAction, QActionGroup, QGuiApplication,
                         QKeySequence, QShortcut)
from PyQt6.QtCore import QSize
from PyQt6.QtWidgets import QGraphicsOpacityEffect

from PyQt6.QtWidgets import (QApplication,
                             QDialog, QFileDialog, QFrame, QGridLayout,
                             QHBoxLayout, QInputDialog,
                             QLabel, QLineEdit, QMainWindow, QMessageBox, QPushButton,
                             QScrollArea, QSizePolicy, QSplashScreen, QStackedWidget,
                             QStyle, QStyleFactory, QTabWidget,
                             QVBoxLayout, QWidget)
# --- FINE MODIFICA ---



from catasto_db_manager import CatastoDBManager
from app_utils import get_local_ip_address, get_password_from_keyring 
import pandas as pd # Importa pandas
from app_paths import get_available_styles, load_stylesheet, get_logo_svg_path, get_resource_path
from dialogs import (CSVImportResultDialog, EulaDialog, BackupReminderSettingsDialog,
                     ImportComuniDialog, ImportLocalitaDialog)


# Dai nuovi moduli che creeremo:
from gui_widgets import (
    DashboardWidget, ElencoComuniWidget, RicercaPartiteWidget,
    RicercaAvanzataImmobiliWidget, InserimentoComuneWidget,
    InserimentoPossessoreWidget, InserimentoLocalitaWidget, RegistrazioneProprietaWidget,
    OperazioniPartitaWidget, EsportazioniWidget, ReportisticaWidget, StatisticheWidget,
    GestioneUtentiWidget, AuditLogViewerWidget, BackupWidget,
    RegistraConsultazioneWidget, WelcomeScreen, GestionePeriodiStoriciWidget,
    GestioneTipiLocalitaWidget,
    DBConfigDialog, InserimentoPartitaWidget, RicercaDocumentiWidget)

from custom_widgets import QPasswordLineEdit
import update_checker


from config import (
    APP_VERSION, APP_NAME, APP_SUBTITLE,
    SETTINGS_DB_TYPE, SETTINGS_DB_HOST, SETTINGS_DB_PORT,
    SETTINGS_DB_NAME, SETTINGS_DB_USER, SETTINGS_DB_SCHEMA, SETTINGS_DB_PASSWORD,
    SETTINGS_UI_CURRENT_STYLE, SETTINGS_UI_AUTO_THEME, SETTINGS_UI_WIN11_STYLE,
    AUTO_THEME_DARK, AUTO_THEME_LIGHT,
    IS_TEST_ENV, SETTINGS_SESSION_TIMEOUT,
    EULA_VERSION, SETTINGS_EULA_ACCEPTED)
from app_paths import get_icon_path
from core.session_manager import SessionManager

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

# ---------------------------------------------------------------------------
# Splash screen Foliarium
# ---------------------------------------------------------------------------

def _build_foliarium_splash_pixmap():
    """Genera il pixmap di fallback per la splash screen (usato se il PNG non esiste)."""
    from PyQt6.QtGui import QPixmap, QPainter, QColor, QFont, QPen
    from PyQt6.QtCore import QRect

    W, H = 700, 394
    pixmap = QPixmap(W, H)
    pixmap.fill(QColor("#f5f0e8"))

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    # Bordo oro
    pen = QPen(QColor("#b8960c"), 4)
    painter.setPen(pen)
    painter.drawRect(8, 8, W - 16, H - 16)
    # Linea separatrice
    painter.drawLine(40, H // 2 + 30, W - 40, H // 2 + 30)

    # Titolo
    font_title = QFont("Georgia", 64, QFont.Weight.Bold)
    painter.setFont(font_title)
    painter.setPen(QColor("#1a3c2b"))
    painter.drawText(QRect(0, 50, W, 140), Qt.AlignmentFlag.AlignCenter, "FOLIARIUM")

    # Sottotitolo
    font_sub = QFont("Georgia", 16)
    painter.setFont(font_sub)
    painter.drawText(QRect(0, 210, W, 40), Qt.AlignmentFlag.AlignCenter, "GESTIONE DIGITALE")
    painter.drawText(QRect(0, 245, W, 40), Qt.AlignmentFlag.AlignCenter, "ARCHIVI CATASTALI STORICI")

    # Versione
    font_ver = QFont("Georgia", 10)
    painter.setFont(font_ver)
    painter.setPen(QColor("#7a6a50"))
    painter.drawText(QRect(0, H - 45, W - 20, 30),
                     Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignBottom,
                     f"v{APP_VERSION}")

    painter.end()
    return pixmap


class FoliariumSplashScreen(QSplashScreen):
    """Splash screen mostrata all'avvio prima del login."""

    def __init__(self):
        logo_path = str(get_resource_path("Logo_foliarium_1.png"))
        if os.path.exists(logo_path):
            from PyQt6.QtGui import QPixmap
            pixmap = QPixmap(logo_path).scaled(
                700, 394,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        else:
            pixmap = _build_foliarium_splash_pixmap()
        super().__init__(pixmap)
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint)


# ---------------------------------------------------------------------------


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

        self.setWindowTitle("Login - Foliarium")
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
    logging.warning("[INIT] Ricerca fuzzy non disponibile")
    FUZZY_SEARCH_AVAILABLE = False


# ---------------------------------------------------------------------------
# TopBarWidget — barra superiore fissa con logo, info utente e logout
# ---------------------------------------------------------------------------

class TopBarWidget(QFrame):
    logout_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("topBar")
        self.setFixedHeight(48)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 0, 12, 0)
        layout.setSpacing(8)

        # Logo + titolo
        try:
            from PyQt6.QtSvgWidgets import QSvgWidget
            logo_path = get_logo_svg_path(dark=False)
            if logo_path:
                logo = QSvgWidget(logo_path)
                logo.setFixedSize(28, 28)
                layout.addWidget(logo)
        except Exception:
            pass

        title_label = QLabel("Foliarium")
        title_label.setObjectName("appTitle")
        layout.addWidget(title_label)

        layout.addStretch()

        # Indicatore DB
        self._db_indicator = QLabel("● DB: —")
        self._db_indicator.setObjectName("dbIndicator")
        layout.addWidget(self._db_indicator)

        layout.addSpacing(16)

        # Nome utente
        self._user_label = QLabel("—")
        self._user_label.setObjectName("userLabel")
        layout.addWidget(self._user_label)

        # Chip ruolo
        self._role_chip = QLabel("")
        self._role_chip.setObjectName("roleChip")
        layout.addWidget(self._role_chip)

        layout.addSpacing(8)

        # Pulsante Logout
        self._logout_btn = QPushButton("Logout")
        self._logout_btn.setObjectName("logoutButton")
        self._logout_btn.setEnabled(False)
        self._logout_btn.clicked.connect(self.logout_requested)
        layout.addWidget(self._logout_btn)

    def update_user_info(self, nome: str, ruolo: str, db_connected: bool, db_name: str = ""):
        """Aggiorna label utente, ruolo e stato DB."""
        if db_connected:
            db_text = f"● DB: {db_name}" if db_name else "● DB: connesso"
            self._db_indicator.setStyleSheet("color: #2E7D32; font-size: 11px;")
        else:
            db_text = "● DB: offline"
            self._db_indicator.setStyleSheet("color: #B71C1C; font-size: 11px;")
        self._db_indicator.setText(db_text)

        if nome:
            self._user_label.setText(nome)
            self._role_chip.setText(ruolo or "")
            self._role_chip.setProperty("role", (ruolo or "").lower())
            # Forza il restyle del chip
            self._role_chip.style().unpolish(self._role_chip)
            self._role_chip.style().polish(self._role_chip)
            self._logout_btn.setEnabled(True)
        else:
            self._user_label.setText("—")
            self._role_chip.setText("")
            self._logout_btn.setEnabled(False)

    def set_logout_enabled(self, enabled: bool):
        self._logout_btn.setEnabled(enabled)


# ---------------------------------------------------------------------------
# SidebarWidget — navigazione verticale stile VS Code
# ---------------------------------------------------------------------------

class SidebarWidget(QWidget):
    page_requested = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("sidebar")
        self.setFixedWidth(220)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        self._container = QWidget()
        self._nav_layout = QVBoxLayout(self._container)
        self._nav_layout.setContentsMargins(0, 8, 0, 8)
        self._nav_layout.setSpacing(0)
        self._nav_layout.addStretch()

        scroll.setWidget(self._container)
        outer.addWidget(scroll)

        # Dict page_name -> QPushButton
        self._buttons: dict[str, QPushButton] = {}

    def build_nav(self, is_admin: bool, fuzzy_available: bool = False):
        """Costruisce i bottoni di navigazione in base al ruolo."""
        # Rimuove widget esistenti (tranne lo stretch finale)
        while self._nav_layout.count() > 1:
            item = self._nav_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._buttons.clear()

        layout = self._nav_layout
        stretch = layout.takeAt(0)  # rimuovi stretch temporaneamente

        def insert(lbl, page, icon=""):
            self._add_nav_button(layout, lbl, page, icon)

        # Home
        insert("Home", "home", "home")

        # ARCHIVIO
        self._add_section(layout, "ARCHIVIO")
        insert("Comuni", "comuni", "building")
        insert("Ricerca Partite", "partite", "search")
        insert("Ricerca Immobili", "immobili", "search")
        insert("Ricerca Documenti", "documenti", "file-text")
        if fuzzy_available:
            insert("Ricerca Globale", "fuzzy", "globe")

        # INSERIMENTO
        self._add_section(layout, "INSERIMENTO")
        insert("Comune", "ins_comune", "building")
        insert("Possessore", "ins_possessore", "user")
        insert("Partita", "ins_partita", "file-text")
        insert("Località", "ins_localita", "map-pin")
        insert("Reg. Proprietà", "reg_proprieta", "key")
        insert("Operazioni", "operazioni", "settings")
        insert("Reg. Consultazione", "reg_consult", "book")
        if is_admin:
            insert("Tipi Località", "tipi_localita", "map-pin")
            insert("Periodi Storici", "periodi", "clock")

        # ANALISI
        self._add_section(layout, "ANALISI")
        insert("Esportazioni", "esportazioni", "download")
        insert("Report", "report", "report")
        insert("Statistiche", "statistiche", "bar-chart")

        # SISTEMA (admin only)
        if is_admin:
            self._add_section(layout, "SISTEMA")
            insert("Utenti", "utenti", "users")
            insert("Audit Log", "audit", "shield")
            insert("Backup", "backup", "database")

        layout.addStretch()

    def _add_section(self, layout: QVBoxLayout, label: str):
        lbl = QLabel(label)
        lbl.setObjectName("sectionLabel")
        lbl.setEnabled(False)
        layout.addWidget(lbl)

    def _add_nav_button(self, layout: QVBoxLayout, label: str, page_name: str,
                        icon_name: str = ""):
        btn = QPushButton(label)
        btn.setObjectName("navButton")
        btn.setFlat(True)
        btn.setCheckable(False)
        btn.setProperty("active", "false")
        btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        btn.setMinimumHeight(36)
        if icon_name:
            icon_path = get_icon_path(icon_name)
            if icon_path.exists():
                from PyQt6.QtGui import QIcon
                btn.setIcon(QIcon(str(icon_path)))
                btn.setIconSize(QSize(18, 18))
        btn.clicked.connect(lambda _, p=page_name: self.page_requested.emit(p))
        self._buttons[page_name] = btn
        layout.addWidget(btn)

    def set_active(self, page_name: str):
        """Imposta il bottone attivo e rimuove lo stile dagli altri."""
        for name, btn in self._buttons.items():
            active = (name == page_name)
            btn.setProperty("active", "true" if active else "false")
            btn.style().unpolish(btn)
            btn.style().polish(btn)

    def set_button_visible(self, page_name: str, visible: bool):
        if page_name in self._buttons:
            self._buttons[page_name].setVisible(visible)

    def get_page_names(self) -> list:
        """Restituisce la lista ordinata dei nomi pagina (per shortcut Ctrl+N)."""
        return list(self._buttons.keys())


class CatastoMainWindow(QMainWindow):
    
    def __init__(self, client_ip_address_gui: str):
        super(CatastoMainWindow, self).__init__()
        self.logger = logging.getLogger("CatastoGUI")
        self.db_manager: Optional[CatastoDBManager] = None
        self.logged_in_user_id: Optional[int] = None
        self.logged_in_user_info: Optional[Dict] = None
        self.current_session_id: Optional[str] = None
        self.client_ip_address_gui = client_ip_address_gui

        # Gestione sessione centralizzata (nuovo sistema modulare)
        self.session = SessionManager()

        # --- INIZIO CORREZIONE DEFINITIVA: Aggiungi questa riga ---
        self.pool_initialized_successful: bool = False
        # --- FINE CORREZIONE DEFINITIVA ---

        # --- Session timeout (inattività) ---
        from PyQt6.QtCore import QTimer, QEvent
        self._inactivity_timer = QTimer(self)
        self._inactivity_timer.setSingleShot(True)
        self._inactivity_timer.timeout.connect(self._on_inactivity_timeout)
        QApplication.instance().installEventFilter(self)

        self.initUI()
        
    def initUI(self):
        # Riferimenti ai widget, inizializzati a None
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

        # Indice pagine sidebar: page_name -> QStackedWidget index
        self._page_index: dict = {}

        self.setWindowTitle("Foliarium — Archivio Catastale Storico")
        self.setMinimumSize(1280, 720)
        self.central_widget = QWidget()
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        # --- Top bar ---
        self.top_bar = TopBarWidget(self)
        self.top_bar.logout_requested.connect(self.handle_logout)
        self.main_layout.addWidget(self.top_bar)

        # --- Area centrale: sidebar + stack ---
        content_widget = QWidget()
        content_layout = QHBoxLayout(content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        self.sidebar = SidebarWidget(self)
        self.sidebar.page_requested.connect(self.navigate_to)
        content_layout.addWidget(self.sidebar)

        self.stack = QStackedWidget(self)
        self.stack.currentChanged.connect(self._on_stack_changed)
        content_layout.addWidget(self.stack)

        self.main_layout.addWidget(content_widget, 1)

        # --- Barra dati obsoleti ---
        self.stale_data_bar = QFrame()
        self.stale_data_bar.setObjectName("staleDataBar")
        self.stale_data_bar.setStyleSheet("#staleDataBar { background-color: #FFF3CD; border: 1px solid #FFEEBA; border-radius: 4px; }")
        stale_data_layout = QHBoxLayout(self.stale_data_bar)
        stale_data_layout.setContentsMargins(10, 5, 10, 5)
        self.stale_data_label = QLabel("I dati delle statistiche potrebbero non essere aggiornati.")
        self.stale_data_label.setStyleSheet("color: #664D03;")
        self.stale_data_refresh_btn = QPushButton("Aggiorna Ora")
        self.stale_data_refresh_btn.clicked.connect(self._handle_stale_data_refresh_click)
        stale_data_layout.addWidget(self.stale_data_label)
        stale_data_layout.addStretch()
        stale_data_layout.addWidget(self.stale_data_refresh_btn)
        self.main_layout.addWidget(self.stale_data_bar)
        self.stale_data_bar.hide()

        # --- Barra modalità offline ---
        self.offline_bar = QFrame()
        self.offline_bar.setObjectName("offlineBar")
        self.offline_bar.setStyleSheet("#offlineBar { background-color: #FFCDD2; border: 1px solid #EF9A9A; border-radius: 4px; }")
        offline_layout = QHBoxLayout(self.offline_bar)
        offline_layout.setContentsMargins(10, 5, 10, 5)
        self.offline_label = QLabel("⚠️  Modalità offline — database non raggiungibile. Dati mostrati dalla cache locale.")
        self.offline_label.setStyleSheet("color: #B71C1C; font-weight: bold;")
        self.offline_timestamp_label = QLabel("")
        self.offline_timestamp_label.setStyleSheet("color: #B71C1C;")
        offline_layout.addWidget(self.offline_label)
        offline_layout.addWidget(self.offline_timestamp_label)
        offline_layout.addStretch()
        self.main_layout.addWidget(self.offline_bar)
        self.offline_bar.hide()

        self.create_menu_bar()
        self.setCentralWidget(self.central_widget)
        self.statusBar().showMessage("Pronto.")

    def avvia_ricerca_globale_da_dashboard(self, testo: str):
        if hasattr(self, 'fuzzy_search_widget') and 'fuzzy' in self._page_index:
            self.navigate_to('fuzzy')
            self.fuzzy_search_widget.search_edit.setText(testo)
            self.fuzzy_search_widget._perform_search()
        else:
            self.logger.warning("Ricerca globale non disponibile.")
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

        # Sincronizza il SessionManager centralizzato
        if user_id is not None and user_info:
            self.session.login(
                user_id=user_id,
                user_info={
                    "nome": user_info.get("nome_completo") or user_info.get("username", ""),
                    "ruolo": user_info.get("ruolo", ""),
                    "email": user_info.get("email"),
                    "username": user_info.get("username", ""),
                },
                session_id=session_id,
                client_ip=self.client_ip_address_gui,
            )

        # --- Aggiornamento etichetta stato DB ---
        db_name_configured = "N/Config"  # Default
        db_name_configured = "N/Config"
        if self.db_manager:
            db_name_configured = self.db_manager.get_current_dbname() or "N/Config(None)"

        db_connected = bool(self.pool_initialized_successful)

        if self.logged_in_user_info:  # Se l'utente è loggato
            user_display = self.logged_in_user_info.get(
                'nome_completo') or self.logged_in_user_info.get('username', 'N/D')
            ruolo_display = self.logged_in_user_info.get('ruolo', 'N/D')
            self.top_bar.update_user_info(user_display, ruolo_display, db_connected, db_name_configured)
            self.statusBar().showMessage(
                f"Login come {user_display} effettuato con successo.")
            self._start_inactivity_timer()
            # --- Notifica email login ---
            try:
                from email_service import EmailService, EmailWorker
                from config import SETTINGS_EMAIL_ON_LOGIN
                _svc = EmailService(QSettings())
                if _svc.is_configured() and QSettings().value(SETTINGS_EMAIL_ON_LOGIN, True, type=bool):
                    _user_email = (self.logged_in_user_info or {}).get('email')
                    if _user_email:
                        _username = (self.logged_in_user_info or {}).get('username', 'N/D')
                        _nome = (self.logged_in_user_info or {}).get('nome_completo') or _username
                        _to, _subj, _body = _svc.notify_login(_user_email, _username, _nome)
                        self._login_email_worker = EmailWorker(_svc, _to, _subj, _body)
                        self._login_email_worker.result.connect(
                            lambda ok, err: self.logger.warning(f"Email login: {err}") if not ok else None)
                        self._login_email_worker.start()
            except Exception as _e:
                self.logger.warning(f"Notifica email login non inviata: {_e}")
        else:  # Modalità setup DB (admin_offline) o nessun login
            ruolo_fittizio = self.logged_in_user_info.get(
                'ruolo') if self.logged_in_user_info else None
            if ruolo_fittizio == 'admin_offline':
                self.top_bar.update_user_info("Admin Setup", "admin", db_connected, db_name_configured)
                self.top_bar.set_logout_enabled(True)
                self.statusBar().showMessage("Modalità configurazione database.")
            else:
                self.top_bar.update_user_info("", "", db_connected, db_name_configured)
                self.statusBar().showMessage("Pronto.")

        logging.getLogger("CatastoGUI").info(
            ">>> CatastoMainWindow: Chiamata a setup_pages")
        self.setup_pages()
        
        logging.getLogger("CatastoGUI").info(
            ">>> CatastoMainWindow: Chiamata a update_ui_based_on_role")
        self.update_ui_based_on_role()

        logging.getLogger("CatastoGUI").info(
            ">>> CatastoMainWindow: Chiamata a self.show()")
        self.show()
        logging.getLogger("CatastoGUI").info(
            ">>> CatastoMainWindow: self.show() completato. Fine perform_initial_setup")

        # Connette il segnale OS dark/light mode per aggiornare il tema in tempo reale
        QGuiApplication.styleHints().colorSchemeChanged.connect(self._on_color_scheme_changed)

        self.check_mv_refresh_status()
        self._check_offline_mode()
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
                                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.Yes)
            if reply == QMessageBox.StandardButton.Yes:
                self.navigate_to("backup")

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
        import_comuni_action = QAction("Importa Comuni da CSV/ISTAT...", self)
        import_comuni_action.triggered.connect(self._import_comuni)
        scarica_comuni_action = QAction("Scarica CSV Comuni", self)
        scarica_comuni_action.triggered.connect(self._scarica_csv_comuni)

        import_localita_action = QAction("Importa Località da CSV...", self)
        import_localita_action.triggered.connect(self._import_localita)
        scarica_localita_action = QAction("Scarica CSV Località...", self)
        scarica_localita_action.triggered.connect(self._scarica_csv_localita)

        import_possessori_action = QAction("Importa Possessori da CSV...", self)
        import_possessori_action.triggered.connect(self._import_possessori_csv)
        scarica_poss_action = QAction("Scarica CSV Possessori...", self)
        scarica_poss_action.triggered.connect(self._scarica_csv_possessori)

        import_partite_action = QAction("Importa Partite da CSV/Excel...", self)
        import_partite_action.triggered.connect(self._import_partite_csv)
        scarica_partite_action = QAction("Scarica CSV Partite...", self)
        scarica_partite_action.triggered.connect(self._scarica_csv_partite)

        exit_action = QAction(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogCloseButton), "&Esci", self)
        exit_action.triggered.connect(self.close)

        file_menu.addAction(import_comuni_action)
        file_menu.addAction(scarica_comuni_action)
        file_menu.addAction(import_localita_action)
        file_menu.addAction(scarica_localita_action)
        file_menu.addSeparator()
        file_menu.addAction(import_possessori_action)
        file_menu.addAction(scarica_poss_action)
        file_menu.addAction(import_partite_action)
        file_menu.addAction(scarica_partite_action)
        file_menu.addSeparator()
        file_menu.addAction(exit_action)
        
        # --- Azioni per il menu Impostazioni ---
        config_db_action = QAction(self.style().standardIcon(QStyle.StandardPixmap.SP_ComputerIcon), "Configurazione &Database...", self)
        config_db_action.triggered.connect(self._apri_dialogo_configurazione_db)
        
        config_refresh_action = QAction("Impostazioni di Aggiornamento Dati...", self)
        config_refresh_action.triggered.connect(self._apri_dialogo_impostazioni_aggiornamento)
        
        email_action = QAction(
            self.style().standardIcon(QStyle.StandardPixmap.SP_MessageBoxInformation),
            "Notifiche &Email...", self
        )
        email_action.triggered.connect(self._apri_impostazioni_email)

        timeout_action = QAction(
            self.style().standardIcon(QStyle.StandardPixmap.SP_DialogResetButton),
            "&Timeout Sessione...", self
        )
        timeout_action.triggered.connect(self._configura_timeout_sessione)

        settings_menu.addAction(config_db_action)
        settings_menu.addAction(config_refresh_action)
        settings_menu.addAction(email_action)
        settings_menu.addAction(timeout_action)
        settings_menu.addSeparator()

        # --- Menu dinamico per i temi ---
        style_menu = settings_menu.addMenu("Cambia Tema Grafico")

        self.style_action_group = QActionGroup(self)
        self.style_action_group.setExclusive(True)

        settings = QSettings()
        auto_theme_enabled = settings.value(SETTINGS_UI_AUTO_THEME, False, type=bool)
        win11_enabled = settings.value(SETTINGS_UI_WIN11_STYLE, False, type=bool)
        current_style = settings.value(SETTINGS_UI_CURRENT_STYLE, AUTO_THEME_LIGHT, type=str)

        # Voce speciale: segue la preferenza dark/light del sistema operativo
        self.auto_theme_action = QAction("Tema Automatico (Segue Sistema)", self, checkable=True)
        self.auto_theme_action.setChecked(auto_theme_enabled)
        self.auto_theme_action.triggered.connect(self._enable_auto_theme)
        style_menu.addAction(self.auto_theme_action)
        self.style_action_group.addAction(self.auto_theme_action)

        # Voce speciale: stile nativo Windows 11 (solo se disponibile)
        self.win11_action = None
        if "windows11" in QStyleFactory.keys():
            self.win11_action = QAction("Stile Nativo Windows 11", self, checkable=True)
            self.win11_action.setChecked(win11_enabled)
            self.win11_action.triggered.connect(self._enable_win11_style)
            style_menu.addAction(self.win11_action)
            self.style_action_group.addAction(self.win11_action)

        style_menu.addSeparator()

        for style_file in get_available_styles():
            style_name = style_file.replace('_', ' ').replace('.qss', '').title()
            action = QAction(style_name, self, checkable=True)
            action.triggered.connect(lambda _, file=style_file: self._change_stylesheet(file))
            if style_file == current_style and not auto_theme_enabled and not win11_enabled:
                action.setChecked(True)
            style_menu.addAction(action)
            self.style_action_group.addAction(action)

        # --- Azione per il menu Help ---
        show_manual_action = QAction("Visualizza Manuale Utente...", self)
        show_manual_action.setShortcut(QKeySequence("F1"))
        show_manual_action.triggered.connect(self._apri_manuale_utente)
        help_menu.addAction(show_manual_action)
            # --- INIZIO MODIFICA ---
        help_menu.addSeparator()

        show_eula_action = QAction("Informazioni su Foliarium / EULA...", self)
        show_eula_action.triggered.connect(self._show_about_eula_dialog)
        help_menu.addAction(show_eula_action)
        # --- FINE MODIFICA ---

    def _change_stylesheet(self, filename: str):
        """Carica, applica e salva il nuovo stylesheet. Disabilita tema automatico e stile Win11."""
        self.logger.info(f"Cambio tema grafico richiesto: {filename}")
        new_stylesheet = load_stylesheet(filename)
        if new_stylesheet:
            self._reset_app_style()
            QApplication.instance().setStyleSheet(new_stylesheet)
            settings = QSettings()
            settings.setValue(SETTINGS_UI_CURRENT_STYLE, filename)
            settings.setValue(SETTINGS_UI_AUTO_THEME, False)
            settings.setValue(SETTINGS_UI_WIN11_STYLE, False)
            self.auto_theme_action.setChecked(False)
            if self.win11_action:
                self.win11_action.setChecked(False)
            QMessageBox.information(self, "Cambio Tema", f"Tema '{filename.replace('.qss', '').title()}' applicato con successo.")
        else:
            QMessageBox.warning(self, "Errore Tema", f"Impossibile caricare il file di stile '{filename}'.")

    def _enable_auto_theme(self):
        """Attiva il tema automatico basato sulla preferenza dark/light del sistema operativo."""
        self._reset_app_style()
        settings = QSettings()
        settings.setValue(SETTINGS_UI_AUTO_THEME, True)
        settings.setValue(SETTINGS_UI_WIN11_STYLE, False)
        if self.win11_action:
            self.win11_action.setChecked(False)
        self._apply_auto_theme()
        self.logger.info("Tema automatico attivato.")

    def _apply_auto_theme(self):
        """Applica il tema chiaro o scuro in base allo schema colori del sistema operativo."""
        scheme = QGuiApplication.styleHints().colorScheme()
        theme_file = AUTO_THEME_DARK if scheme == Qt.ColorScheme.Dark else AUTO_THEME_LIGHT
        stylesheet = load_stylesheet(theme_file)
        if stylesheet:
            QApplication.instance().setStyleSheet(stylesheet)
            self.logger.info(f"Tema automatico applicato: {theme_file} (schema OS: {scheme.name})")

    @pyqtSlot(Qt.ColorScheme)
    def _on_color_scheme_changed(self, scheme: Qt.ColorScheme):
        """Slot: aggiorna il tema quando l'utente cambia la modalità dark/light in Windows."""
        settings = QSettings()
        if settings.value(SETTINGS_UI_AUTO_THEME, False, type=bool):
            self._apply_auto_theme()
            self.logger.info(f"Schema OS cambiato a {scheme.name}, tema aggiornato automaticamente.")

    def _enable_win11_style(self):
        """Attiva lo stile nativo Windows 11, rimuovendo qualsiasi QSS personalizzato."""
        QApplication.instance().setStyle("windows11")
        QApplication.instance().setStyleSheet("")
        settings = QSettings()
        settings.setValue(SETTINGS_UI_WIN11_STYLE, True)
        settings.setValue(SETTINGS_UI_AUTO_THEME, False)
        self.auto_theme_action.setChecked(False)
        self.logger.info("Stile nativo Windows 11 attivato.")

    def _reset_app_style(self):
        """Ripristina lo stile Qt predefinito (necessario prima di applicare un QSS)."""
        QApplication.instance().setStyle(QStyleFactory.create("Fusion"))

    def _show_about_eula_dialog(self):
        """Apre la finestra di dialogo con le informazioni su versione e licenza (EULA)."""
        dialog = EulaDialog(self)
        dialog.exec()

    def setup_pages(self):
        """Popola il QStackedWidget e la sidebar con tutte le pagine."""
        if not self.db_manager:
            self.logger.error("Tentativo di configurare le pagine senza un db_manager.")
            return

        # Svuota lo stack
        while self.stack.count():
            w = self.stack.widget(0)
            self.stack.removeWidget(w)
        self._page_index.clear()

        is_admin = bool(
            self.logged_in_user_info and self.logged_in_user_info.get('ruolo') == 'admin'
        )
        utente_per_inserimenti = self.logged_in_user_info if self.logged_in_user_info else {}

        def _add_page(name: str, widget):
            idx = self.stack.addWidget(widget)
            self._page_index[name] = idx

        # Home
        self.dashboard_widget = DashboardWidget(self.db_manager, self.logged_in_user_info, self.stack)
        self.dashboard_widget.go_to_tab_signal.connect(self.activate_tab_and_sub_tab)
        self.dashboard_widget.ricerca_globale_richiesta.connect(self.avvia_ricerca_globale_da_dashboard)
        _add_page("home", self.dashboard_widget)

        # Archivio
        self.elenco_comuni_widget_ref = ElencoComuniWidget(self.db_manager, self.stack)
        _add_page("comuni", self.elenco_comuni_widget_ref)

        self.ricerca_partite_widget_ref = RicercaPartiteWidget(self.db_manager, self.stack)
        _add_page("partite", self.ricerca_partite_widget_ref)

        self.ricerca_avanzata_immobili_widget_ref = RicercaAvanzataImmobiliWidget(self.db_manager, self.stack)
        _add_page("immobili", self.ricerca_avanzata_immobili_widget_ref)

        self.ricerca_documenti_widget_ref = RicercaDocumentiWidget(self.db_manager, self.stack)
        _add_page("documenti", self.ricerca_documenti_widget_ref)

        if FUZZY_SEARCH_AVAILABLE:
            self.fuzzy_search_widget = UnifiedFuzzySearchWidget(self.db_manager, parent=self.stack)
            _add_page("fuzzy", self.fuzzy_search_widget)

        # Inserimento
        self.inserimento_comune_widget_ref = InserimentoComuneWidget(
            db_manager=self.db_manager,
            utente_attuale_info=utente_per_inserimenti,
            parent=self.stack
        )
        self.inserimento_comune_widget_ref.import_csv_requested.connect(self._import_comuni)
        self.inserimento_comune_widget_ref.scarica_csv_requested.connect(self._scarica_csv_comuni)
        _add_page("ins_comune", self.inserimento_comune_widget_ref)

        self.inserimento_possessore_widget_ref = InserimentoPossessoreWidget(self.db_manager)
        self.inserimento_possessore_widget_ref.import_csv_requested.connect(self._import_possessori_csv)
        self.inserimento_possessore_widget_ref.scarica_csv_requested.connect(self._scarica_csv_possessori)
        _add_page("ins_possessore", self.inserimento_possessore_widget_ref)

        self.inserimento_partite_widget_ref = InserimentoPartitaWidget(self.db_manager, self.stack)
        self.inserimento_partite_widget_ref.import_csv_requested.connect(self._import_partite_csv)
        self.inserimento_partite_widget_ref.scarica_csv_requested.connect(self._scarica_csv_partite)
        _add_page("ins_partita", self.inserimento_partite_widget_ref)

        self.inserimento_localita_widget_ref = InserimentoLocalitaWidget(self.db_manager, self.stack)
        self.inserimento_localita_widget_ref.import_csv_requested.connect(self._import_localita)
        self.inserimento_localita_widget_ref.scarica_csv_requested.connect(self._scarica_csv_localita)
        _add_page("ins_localita", self.inserimento_localita_widget_ref)

        self.registrazione_proprieta_widget_ref = RegistrazioneProprietaWidget(self.db_manager)
        _add_page("reg_proprieta", self.registrazione_proprieta_widget_ref)

        self.operazioni_partita_widget_ref = OperazioniPartitaWidget(self.db_manager)
        _add_page("operazioni", self.operazioni_partita_widget_ref)

        self.registra_consultazione_widget_ref = RegistraConsultazioneWidget(
            self.db_manager, self.logged_in_user_info)
        _add_page("reg_consult", self.registra_consultazione_widget_ref)

        # Admin — voci inserimento
        if is_admin:
            self.gestione_tipi_localita_widget_ref = GestioneTipiLocalitaWidget(self.db_manager)
            _add_page("tipi_localita", self.gestione_tipi_localita_widget_ref)

            self.gestione_periodi_storici_widget_ref = GestionePeriodiStoriciWidget(self.db_manager)
            _add_page("periodi", self.gestione_periodi_storici_widget_ref)

        # Analisi
        self.esportazioni_widget_ref = EsportazioniWidget(self.db_manager)
        _add_page("esportazioni", self.esportazioni_widget_ref)

        self.reportistica_widget_ref = ReportisticaWidget(self.db_manager)
        _add_page("report", self.reportistica_widget_ref)

        self.statistiche_widget_ref = StatisticheWidget(self.db_manager)
        _add_page("statistiche", self.statistiche_widget_ref)

        # Sistema (admin only)
        if is_admin:
            self.gestione_utenti_widget_ref = GestioneUtentiWidget(self.db_manager, self.logged_in_user_info)
            _add_page("utenti", self.gestione_utenti_widget_ref)

            self.audit_viewer_widget_ref = AuditLogViewerWidget(self.db_manager)
            _add_page("audit", self.audit_viewer_widget_ref)

            self.backup_restore_widget_ref = BackupWidget(self.db_manager)
            _add_page("backup", self.backup_restore_widget_ref)

        # Costruisce la sidebar
        self.sidebar.build_nav(is_admin=is_admin, fuzzy_available=FUZZY_SEARCH_AVAILABLE)

        # Shortcut Ctrl+1..N (lista flat pagine sidebar)
        for i, page_name in enumerate(self.sidebar.get_page_names()):
            if i >= 9:
                break
            sc = QShortcut(QKeySequence(f"Ctrl+{i + 1}"), self)
            sc.activated.connect(lambda p=page_name: self.navigate_to(p))

        self._f5_shortcut = QShortcut(QKeySequence("F5"), self)
        self._f5_shortcut.activated.connect(self._handle_f5_refresh)

        # Vai alla home
        self.navigate_to("home")
        self.logger.info("Setup pagine completato (layout sidebar).")

    def _handle_f5_refresh(self):
        """F5: ricarica i dati della pagina corrente."""
        target = self.stack.currentWidget()
        if target is None:
            return
        if hasattr(target, '_data_loaded'):
            target._data_loaded = False
        if hasattr(target, 'load_initial_data'):
            target.load_initial_data()
        elif hasattr(target, 'load_data'):
            target.load_data()

    def activate_tab_and_sub_tab(self, main_tab_name: str, sub_tab_name: str, activate_report_sub_tab: bool = False):
        """Wrapper di compatibilità: mappa i vecchi nomi tab/sub-tab ai nuovi page_name."""
        _MAP = {
            # (main_tab_name, sub_tab_name) -> page_name
            ("Consultazione", "Principale"):        "comuni",
            ("Consultazione", "Ricerca Partite"):   "partite",
            ("Consultazione", "Ricerca Immobili"):  "immobili",
            ("Consultazione", "Ricerca Documenti"): "documenti",
            ("Ricerca", ""):                        "fuzzy",
            ("Inserimento", "Comune"):              "ins_comune",
            ("Inserimento", "Possessore"):          "ins_possessore",
            ("Inserimento", "Partita"):             "ins_partita",
            ("Inserimento", "Località"):            "ins_localita",
            ("Inserimento", "Reg. Proprietà"):      "reg_proprieta",
            ("Inserimento", "Operazioni"):          "operazioni",
            ("Inserimento", "Reg. Consultazione"):  "reg_consult",
            ("Inserimento", "Tipi Località"):       "tipi_localita",
            ("Inserimento", "Periodi"):             "periodi",
            ("Esportazioni", ""):                   "esportazioni",
            ("Report", ""):                         "report",
            ("Statistiche", ""):                    "statistiche",
            ("Sistema", "Utenti"):                  "utenti",
            ("Sistema", "Log Audit"):               "audit",
            ("Sistema", "Backup/Ripristino"):       "backup",
            ("Sistema", "Backup/Ripristino DB"):    "backup",
        }
        page = _MAP.get((main_tab_name, sub_tab_name))
        if page is None:
            # Prova a cercare solo per main_tab_name
            page = _MAP.get((main_tab_name, ""))
        if page:
            self.navigate_to(page)
        else:
            self.logger.warning(
                f"activate_tab_and_sub_tab: mapping non trovato per '{main_tab_name}'/'{sub_tab_name}'"
            )

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
        """Naviga alla pagina Operazioni e precompila l'ID della nuova partita."""
        logging.getLogger("CatastoGUI").info(
            f"Nuova Partita ID {nuova_partita_id} creata. Passaggio a Operazioni.")
        self.navigate_to("operazioni")
        target_operazioni_widget.seleziona_e_carica_partita_sorgente(nuova_partita_id)

    @pyqtSlot(int)
    def _on_stack_changed(self, index: int):
        """Lazy loading quando il QStackedWidget cambia pagina."""
        if not self.db_manager or not self.db_manager.pool:
            return
        widget = self.stack.widget(index)
        if widget is None:
            return
        if hasattr(widget, 'load_initial_data'):
            try:
                widget.load_initial_data()
            except Exception as e:
                self.logger.error(f"Errore lazy loading '{widget.__class__.__name__}': {e}", exc_info=True)
        self._set_focus_first_field(widget)

    def _set_focus_first_field(self, widget) -> None:
        """Imposta il focus sul primo campo di input dei widget di inserimento."""
        from gui_widgets import (InserimentoComuneWidget, InserimentoPossessoreWidget,
                                 InserimentoLocalitaWidget, InserimentoPartitaWidget)
        if isinstance(widget, InserimentoComuneWidget):
            widget.nome_comune_edit.setFocus()
        elif isinstance(widget, InserimentoPossessoreWidget):
            widget.cognome_nome_edit.setFocus()
        elif isinstance(widget, InserimentoLocalitaWidget):
            widget.comune_button.setFocus()
        elif isinstance(widget, InserimentoPartitaWidget):
            widget.comune_combo.setFocus()

    def navigate_to(self, page_name: str):
        """Naviga alla pagina con transizione fade (80ms out + 100ms in)."""
        if page_name not in self._page_index:
            self.logger.warning(f"navigate_to: pagina '{page_name}' non trovata.")
            return
        new_idx = self._page_index[page_name]
        if self.stack.currentIndex() == new_idx:
            return

        self.sidebar.set_active(page_name)

        old_widget = self.stack.currentWidget()
        if old_widget is None:
            self.stack.setCurrentIndex(new_idx)
            self._on_stack_changed(new_idx)
            return

        eff_out = QGraphicsOpacityEffect(old_widget)
        old_widget.setGraphicsEffect(eff_out)

        anim_out = QPropertyAnimation(eff_out, b"opacity", self)
        anim_out.setDuration(70)
        anim_out.setStartValue(1.0)
        anim_out.setEndValue(0.0)
        anim_out.setEasingCurve(QEasingCurve.Type.OutQuad)

        def _do_switch():
            old_widget.setGraphicsEffect(None)
            self.stack.setCurrentIndex(new_idx)
            self._on_stack_changed(new_idx)
            new_widget = self.stack.currentWidget()
            if new_widget is None:
                return
            eff_in = QGraphicsOpacityEffect(new_widget)
            new_widget.setGraphicsEffect(eff_in)
            anim_in = QPropertyAnimation(eff_in, b"opacity", self)
            anim_in.setDuration(110)
            anim_in.setStartValue(0.0)
            anim_in.setEndValue(1.0)
            anim_in.setEasingCurve(QEasingCurve.Type.InQuad)
            anim_in.finished.connect(lambda: new_widget.setGraphicsEffect(None))
            anim_in.start()
            self._anim_in = anim_in

        anim_out.finished.connect(_do_switch)
        anim_out.start()
        self._anim_out = anim_out

    def update_ui_based_on_role(self):
        """Controlla la visibilità dei bottoni sidebar in base al ruolo utente."""
        self.logger.info(">>> CatastoMainWindow: update_ui_based_on_role")

        ruolo = None
        is_admin_offline_mode = False

        if not self.pool_initialized_successful:
            if self.logged_in_user_info and self.logged_in_user_info.get('ruolo') == 'admin_offline':
                is_admin_offline_mode = True
                ruolo = 'admin_offline'
        else:
            if self.logged_in_user_info:
                ruolo = self.logged_in_user_info.get('ruolo')

        is_admin = (ruolo == 'admin')
        is_archivista = (ruolo == 'archivista')
        is_consultatore = (ruolo == 'consultatore')
        db_ready = self.pool_initialized_successful and not is_admin_offline_mode

        # Visibilità bottoni sidebar per sezioni/pagine non-admin
        inserimento_ok = db_ready and (is_admin or is_archivista)
        analisi_ok = db_ready and (is_admin or is_archivista or is_consultatore)

        # I bottoni admin sono già assenti dalla sidebar se non admin (build_nav è role-aware).
        # Qui gestiamo solo la visibilità di bottoni presenti per tutti.
        for page in ("comuni", "partite", "immobili", "documenti", "fuzzy"):
            self.sidebar.set_button_visible(page, db_ready)
        for page in ("ins_comune", "ins_possessore", "ins_partita", "ins_localita",
                     "reg_proprieta", "operazioni", "reg_consult"):
            self.sidebar.set_button_visible(page, inserimento_ok)
        for page in ("esportazioni", "report", "statistiche"):
            self.sidebar.set_button_visible(page, analisi_ok)

        # Pulsante logout nella topbar
        self.top_bar.set_logout_enabled(
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
        if dialog.exec() == QDialog.DialogCode.Accepted:
            logging.getLogger("CatastoGUI").info(
                f"Dialogo inserimento comune chiuso con successo da utente '{utente_login_username}'.")
            QMessageBox.information(
                self, "Comune Aggiunto", "Il nuovo comune è stato registrato con successo.")
            if self.elenco_comuni_widget_ref:
                self.elenco_comuni_widget_ref.load_data()
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

        if config_dialog.exec() == QDialog.DialogCode.Accepted:
            QMessageBox.information(
                self, "Riavvio Necessario",
                "Le nuove impostazioni del database sono state salvate.\n"
                "È necessario riavviare l'applicazione per applicarle."
            )
            # Potremmo anche chiudere l'applicazione qui per forzare il riavvio
            # self.close()

    def _apri_impostazioni_email(self):
        """Apre il dialogo di configurazione SMTP per le notifiche email."""
        from dialogs import SMTPSettingsDialog
        SMTPSettingsDialog(self).exec()

    # ------------------------------------------------------------------
    # Scarica CSV — helper e handler per le 4 entità di inserimento
    # ------------------------------------------------------------------

    def _scarica_csv(self, data: list, fieldnames: list, default_filename: str) -> None:
        """Salva una lista di dict come CSV (delimiter ';') tramite QFileDialog."""
        if not data:
            QMessageBox.information(self, "Nessun dato", "Nessun record da scaricare.")
            return
        filename, _ = QFileDialog.getSaveFileName(
            self, "Salva CSV", default_filename, "File CSV (*.csv)"
        )
        if not filename:
            return
        try:
            import csv as _csv
            with open(filename, 'w', newline='', encoding='utf-8') as f:
                writer = _csv.DictWriter(f, fieldnames=fieldnames, delimiter=';',
                                         extrasaction='ignore')
                writer.writeheader()
                writer.writerows(data)
            QMessageBox.information(
                self, "Scaricato",
                f"{len(data)} record salvati in:\n{filename}"
            )
            # --- Audit log export ---
            if self.db_manager:
                import os as _os
                self.db_manager.log_app_event(
                    self.logged_in_user_id, self.current_session_id,
                    "export_csv",
                    {"filename": _os.path.basename(filename), "n_record": len(data),
                     "entity": default_filename.replace(".csv", "")})
        except OSError as e:
            QMessageBox.critical(self, "Errore salvataggio", str(e))

    def _seleziona_comune_per_csv(self, entita: str):
        """
        Mostra QInputDialog per selezionare un comune.
        Restituisce (comune_id, nome_slug) oppure (None, '') se l'utente annulla.
        """
        try:
            comuni = self.db_manager.get_elenco_comuni_semplice()
        except Exception:
            comuni = []
        if not comuni:
            QMessageBox.warning(self, "Nessun Comune",
                                "Nessun comune trovato nel database.")
            return None, ""
        nomi = [c[1] for c in comuni]
        nome, ok = QInputDialog.getItem(
            self, "Selezione Comune",
            f"Comune di riferimento per '{entita}':", nomi, 0, False
        )
        if not ok or not nome:
            return None, ""
        for cid, cnome in comuni:
            if cnome == nome:
                return cid, cnome.replace(' ', '_')
        return None, ""

    def _scarica_csv_comuni(self):
        """Scarica tutti i comuni in un CSV compatibile con 'Importa Comuni da CSV'."""
        try:
            data = self.db_manager.get_comuni_export_csv()
        except Exception as e:
            QMessageBox.critical(self, "Errore Database", str(e))
            return
        self._scarica_csv(
            data,
            ['nome', 'provincia', 'regione', 'codice_catastale',
             'data_istituzione', 'data_soppressione', 'note'],
            'comuni_export.csv'
        )

    def _scarica_csv_localita(self):
        """Scarica le località di un comune in CSV compatibile con 'Importa Località da CSV'."""
        comune_id, slug = self._seleziona_comune_per_csv("località")
        if not comune_id:
            return
        try:
            data = self.db_manager.get_localita_export_csv(comune_id)
        except Exception as e:
            QMessageBox.critical(self, "Errore Database", str(e))
            return
        self._scarica_csv(data, ['nome', 'tipo', 'civico'],
                          f'localita_{slug}.csv')

    def _scarica_csv_possessori(self):
        """Scarica i possessori di un comune in CSV compatibile con 'Importa Possessori da CSV'."""
        comune_id, slug = self._seleziona_comune_per_csv("possessori")
        if not comune_id:
            return
        try:
            data = self.db_manager.get_possessori_export_csv(comune_id)
        except Exception as e:
            QMessageBox.critical(self, "Errore Database", str(e))
            return
        self._scarica_csv(data, ['cognome_nome', 'nome_completo', 'paternita'],
                          f'possessori_{slug}.csv')

    def _scarica_csv_partite(self):
        """Scarica le partite di un comune in CSV compatibile con 'Importa Partite da CSV'."""
        comune_id, slug = self._seleziona_comune_per_csv("partite")
        if not comune_id:
            return
        try:
            data = self.db_manager.get_partite_export_csv(comune_id)
        except Exception as e:
            QMessageBox.critical(self, "Errore Database", str(e))
            return
        self._scarica_csv(data, ['numero_partita', 'data_impianto', 'stato', 'tipo'],
                          f'partite_{slug}.csv')

    # ------------------------------------------------------------------
    # Session timeout — inattività
    # ------------------------------------------------------------------

    def _start_inactivity_timer(self):
        """Avvia (o riavvia) il timer di inattività in base alle impostazioni."""
        minutes = QSettings().value(SETTINGS_SESSION_TIMEOUT, 15, type=int)
        if minutes > 0 and self.logged_in_user_id is not None:
            self._inactivity_timer.start(minutes * 60 * 1000)
        else:
            self._inactivity_timer.stop()

    def eventFilter(self, obj, event):
        """Resetta il timer di inattività ad ogni interazione utente."""
        from PyQt6.QtCore import QEvent
        if self.logged_in_user_id is not None and self._inactivity_timer.isActive():
            if event.type() in (QEvent.Type.MouseMove, QEvent.Type.MouseButtonPress,
                                 QEvent.Type.KeyPress, QEvent.Type.Wheel):
                self._inactivity_timer.start()  # riavvia con l'intervallo già impostato
        return super().eventFilter(obj, event)

    def _on_inactivity_timeout(self):
        """Mostra dialog di avviso con countdown; se nessuna risposta → logout."""
        if self.logged_in_user_id is None:
            return

        from PyQt6.QtCore import QTimer as _QTimer
        dlg = QDialog(self)
        dlg.setWindowTitle("Sessione in scadenza")
        dlg.setWindowFlags(dlg.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)
        layout = QVBoxLayout(dlg)

        remaining = [60]  # secondi
        lbl = QLabel()
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        font = lbl.font(); font.setPointSize(12); lbl.setFont(font)
        layout.addWidget(lbl)

        btn_row = QHBoxLayout()
        btn_continua = QPushButton("Continua sessione")
        btn_logout = QPushButton("Logout ora")
        btn_continua.setDefault(True)
        btn_row.addWidget(btn_continua)
        btn_row.addWidget(btn_logout)
        layout.addLayout(btn_row)

        def _update():
            remaining[0] -= 1
            lbl.setText(
                f"La sessione è inattiva da troppo tempo.\n\n"
                f"Logout automatico tra {remaining[0]} secondi.\n\n"
                f"Vuoi continuare?"
            )
            if remaining[0] <= 0:
                countdown.stop()
                dlg.reject()

        countdown = _QTimer(dlg)
        countdown.timeout.connect(_update)
        countdown.start(1000)
        _update()

        btn_continua.clicked.connect(lambda: (countdown.stop(), dlg.accept()))
        btn_logout.clicked.connect(lambda: (countdown.stop(), dlg.reject()))

        if dlg.exec() == QDialog.DialogCode.Accepted:
            self._start_inactivity_timer()  # riprende la sessione
        else:
            self.handle_logout()

    def _configura_timeout_sessione(self):
        """Apre QInputDialog per configurare i minuti di timeout (0 = disabilitato)."""
        current = QSettings().value(SETTINGS_SESSION_TIMEOUT, 15, type=int)
        value, ok = QInputDialog.getInt(
            self, "Timeout Sessione",
            "Minuti di inattività prima del logout automatico\n(0 = disabilitato):",
            current, 0, 480, 5)
        if ok:
            QSettings().setValue(SETTINGS_SESSION_TIMEOUT, value)
            self._start_inactivity_timer()
            msg = f"Timeout impostato a {value} minuti." if value > 0 else "Timeout sessione disabilitato."
            self.statusBar().showMessage(msg, 4000)

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

            self._inactivity_timer.stop()
            # Resetta le informazioni utente e sessione nella GUI
            self.logged_in_user_id = None
            self.logged_in_user_info = None
            self.current_session_id = None
            self.session.logout()  # Sincronizza il SessionManager centralizzato

            # Aggiorna la top bar
            self.top_bar.update_user_info("", "", False)

            # Svuota lo stack
            while self.stack.count():
                w = self.stack.widget(0)
                self.stack.removeWidget(w)
            self._page_index.clear()

            self.statusBar().showMessage("Logout effettuato. L'applicazione verrà chiusa.")

            # Chiude l'applicazione dopo un breve ritardo per permettere all'utente di leggere il messaggio
            from PyQt6.QtCore import QTimer
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
   
    def _import_comuni(self):
        """Apre il dialog per importare comuni da CSV o ISTAT."""
        dlg = ImportComuniDialog(self.db_manager, self)
        dlg.exec()
        if self.elenco_comuni_widget_ref:
            self.elenco_comuni_widget_ref.load_data()

    def _import_localita(self):
        """Apre il dialog per importare località da CSV."""
        dlg = ImportLocalitaDialog(self.db_manager, self)
        dlg.exec()

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

            # --- Conferma sovrascrittura ---
            risposta = QMessageBox.question(
                self, "Conferma importazione",
                f"Stai per importare possessori da CSV per il comune <b>{nome_comune_selezionato}</b>.<br><br>"
                "I possessori con gli stessi dati già presenti nel database potrebbero essere sovrascritti.<br><br>"
                "Procedere con l'importazione?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            if risposta != QMessageBox.StandardButton.Yes:
                return

            # --- PASSO 3: Avvia l'importazione e mostra il nuovo dialogo di riepilogo ---
            QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
            
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
            result_dialog.exec()
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
        """Gestisce l'importazione di partite da CSV o Excel e mostra i risultati."""
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
                self, "Seleziona file partite da importare", "",
                "File supportati (*.csv *.xlsx);;CSV (*.csv);;Excel (*.xlsx);;Tutti i file (*)"
            )
            if not file_path:
                return

            risposta = QMessageBox.question(
                self, "Conferma importazione",
                f"Stai per importare partite da file per il comune <b>{nome_comune_selezionato}</b>.<br><br>"
                "Le partite con gli stessi dati già presenti nel database potrebbero essere sovrascritte.<br><br>"
                "Procedere con l'importazione?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            if risposta != QMessageBox.StandardButton.Yes:
                return

            QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)

            if file_path.lower().endswith('.xlsx'):
                import_results = self.db_manager.import_partite_from_xlsx(file_path, comune_id_selezionato, nome_comune_selezionato)
            else:
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
            result_dialog.exec()
            
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

    def _check_offline_mode(self):
        """Mostra/nasconde la barra offline in base allo stato del db_manager."""
        if not self.db_manager:
            return
        if getattr(self.db_manager, 'offline_mode', False):
            ts = getattr(self.db_manager, 'offline_cache_timestamp', None)
            ts_str = f"  (cache del {ts[:19].replace('T', ' ')})" if ts else ""
            self.offline_timestamp_label.setText(ts_str)
            self.offline_bar.show()
        else:
            self.offline_bar.hide()

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
        """Apre il manuale utente integrato (Markdown → QTextBrowser)."""
        try:
            from dialogs import HelpViewerDialog
            dlg = HelpViewerDialog(self)
            dlg.exec()
        except Exception as e:
            self.logger.error(f"Errore apertura manuale: {e}", exc_info=True)
            QMessageBox.critical(self, "Errore", f"Impossibile aprire il manuale:\n{e}")
            
    def _show_backup_settings_dialog(self):
        dialog = BackupReminderSettingsDialog(self)
        dialog.exec()



def setup_logging():
    """Configura il logging per scrivere nella cartella AppData dell'utente."""
    # Imposta i metadati dell'applicazione per creare un percorso univoco
    QCoreApplication.setOrganizationName("AlgoraStudio")
    QCoreApplication.setApplicationName("Foliarium")

    # Trova la cartella standard e scrivibile per i dati dell'applicazione
    app_data_path = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppLocalDataLocation)

    # Assicurati che la cartella esista
    os.makedirs(app_data_path, exist_ok=True)

    # Percorso completo del file di log
    log_file_path = os.path.join(app_data_path, "foliarium_session.log")

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
    QCoreApplication.setOrganizationName("AlgoraStudio")
    QCoreApplication.setApplicationName("Foliarium")
    
    # Ottieni il percorso standard e scrivibile per i dati dell'applicazione
    app_data_path = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppLocalDataLocation)
    
    # Assicurati che la cartella esista
    os.makedirs(app_data_path, exist_ok=True)
    
    # Percorso completo del file di log
    log_file_path = os.path.join(app_data_path, "foliarium_session.log")

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
        QCoreApplication.setOrganizationName("AlgoraStudio")
        QCoreApplication.setApplicationName("Foliarium")
        # --- FINE MODIFICA ---

        # Splash screen (saltata in ambiente CI/test)
        _splash = None
        if not IS_TEST_ENV:
            _splash = FoliariumSplashScreen()
            _splash.show()
            # Mostra la splash per 2.5 secondi poi la chiude automaticamente
            import time
            app.processEvents()
            time.sleep(2.5)
            app.processEvents()
            _splash.close()
            _splash = None

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
        if settings.value(SETTINGS_UI_WIN11_STYLE, False, type=bool) and \
                "windows11" in QStyleFactory.keys():
            app.setStyle("windows11")
        elif settings.value(SETTINGS_UI_AUTO_THEME, False, type=bool):
            scheme = QGuiApplication.styleHints().colorScheme()
            current_style_file = AUTO_THEME_DARK if scheme == Qt.ColorScheme.Dark else AUTO_THEME_LIGHT
            stylesheet = load_stylesheet(current_style_file)
            if stylesheet:
                app.setStyleSheet(stylesheet)
        else:
            current_style_file = settings.value(SETTINGS_UI_CURRENT_STYLE, AUTO_THEME_LIGHT, type=str)
            stylesheet = load_stylesheet(current_style_file)
            if stylesheet:
                app.setStyleSheet(stylesheet)
        # --- CONTROLLO EULA / WELCOME SCREEN ---
        settings = QSettings()
        accepted_version = settings.value(SETTINGS_EULA_ACCEPTED, "", type=str)
        if accepted_version != EULA_VERSION:
            welcome = WelcomeScreen(parent=None)
            if welcome.exec() != QDialog.DialogCode.Accepted:
                gui_logger.info("EULA non accettata. Uscita.")
                sys.exit(0)
            settings.setValue(SETTINGS_EULA_ACCEPTED, EULA_VERSION)
            settings.sync()
        # --- FINE CONTROLLO EULA ---
        
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
                
                if config_dialog.exec() != QDialog.DialogCode.Accepted:
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
        if login_dialog.exec() != QDialog.DialogCode.Accepted:
            gui_logger.info("Login utente annullato. Uscita.")
            sys.exit(0)

        # 4. LOGIN UTENTE OK, AVVIA L'APP
        main_window_instance.perform_initial_setup(
            db_manager_gui,
            login_dialog.logged_in_user_id,
            login_dialog.logged_in_user_info,
            login_dialog.current_session_id_from_dialog
        )

        QTimer.singleShot(1500, lambda: update_checker.check_for_updates(main_window_instance))

        gui_logger.info("Setup completato. Avvio loop eventi.")
        sys.exit(app.exec())

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
            from PyQt6.QtWidgets import QApplication, QMessageBox
            if not QApplication.instance():
                app = QApplication(sys.argv)
            QMessageBox.critical(None, "Errore Critico", 
                               f"Si è verificato un errore critico:\n\n{str(e)}\n\n"
                               "Controlla il file catasto_gui.log per maggiori dettagli.")
        except:
            logging.critical(f"ERRORE CRITICO: {e}")
            logging.critical("Controlla il file catasto_gui.log per maggiori dettagli.")
        
        sys.exit(1)