"""Dialog di login utente."""
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
from foliarium.ui.dialogs.admin.helpers import _verify_password


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
            logo_path = get_logo_svg_path(dark=True)
            if logo_path and os.path.exists(logo_path):
                logo_widget = None
                if str(logo_path).lower().endswith(".svg"):
                    from PyQt6.QtSvgWidgets import QSvgWidget
                    svg = QSvgWidget(str(logo_path))
                    # QSvgWidget non renderizza file raster: se il file ha
                    # estensione .svg ma e' in realta' un PNG/JPEG, ricade sotto.
                    if not svg.renderer().isValid():
                        svg.deleteLater()
                    else:
                        svg.setFixedSize(48, 48)
                        logo_widget = svg
                if logo_widget is None:
                    pix = QPixmap(str(logo_path))
                    if not pix.isNull():
                        lbl = QLabel()
                        lbl.setFixedSize(48, 48)
                        lbl.setScaledContents(False)
                        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
                        lbl.setPixmap(pix.scaled(
                            48, 48,
                            Qt.AspectRatioMode.KeepAspectRatio,
                            Qt.TransformationMode.SmoothTransformation))
                        logo_widget = lbl
                if logo_widget is not None:
                    logo_row = QHBoxLayout()
                    logo_row.addStretch()
                    logo_row.addWidget(logo_widget)
                    logo_row.addStretch()
                    banner_layout.addLayout(logo_row)
        except Exception:
            logging.getLogger(__name__).debug(
                "Logo login non caricato", exc_info=True)

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



