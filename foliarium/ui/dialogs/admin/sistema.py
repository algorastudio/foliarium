"""Dialog di sistema: backup reminder, EULA, SMTP."""
from __future__ import annotations

import logging
import os
import sys

from PyQt6.QtCore import (QSettings)
from PyQt6.QtWidgets import (QCheckBox, QDialog,
                             QFormLayout, QGroupBox,
                             QHBoxLayout, QLabel, QLineEdit,
                             QPushButton, QSpinBox, QVBoxLayout,
                             QTextBrowser, QDialogButtonBox)
from app_paths import get_resource_path, get_resource_path as resource_path, get_doc_path  # noqa: F401
from config import (
    SETTINGS_SMTP_ENABLED, SETTINGS_SMTP_HOST, SETTINGS_SMTP_PORT,
    SETTINGS_SMTP_USER, SETTINGS_SMTP_USE_TLS, SETTINGS_SMTP_FROM_ADDR,
    SETTINGS_EMAIL_ON_CREATE, SETTINGS_EMAIL_ON_PASSWD,
    SETTINGS_EMAIL_ON_ROLE, SETTINGS_EMAIL_ON_LOGIN,
)
from catasto_exceptions import DBMError, DBUniqueConstraintError, DBNotFoundError, DBDataError  # noqa: F401
from foliarium.ui.widgets.custom import QPasswordLineEdit, show_status_message as _show_status_message

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
            except Exception:
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




