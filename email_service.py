"""
email_service.py — Servizio di notifiche email per Meridiana.

Modulo autonomo (nessuna dipendenza da gui_*) che gestisce:
- Configurazione SMTP tramite QSettings + keyring per la password
- Invio email in background (EmailWorker, QThread)
- Template per i 4 tipi di notifica: creazione account, cambio password,
  cambio ruolo, accesso/login
"""

import logging
import smtplib
import socket
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import keyring
from PyQt6.QtCore import QSettings, QThread, pyqtSignal

from config import (
    SETTINGS_SMTP_ENABLED,
    SETTINGS_SMTP_HOST,
    SETTINGS_SMTP_PORT,
    SETTINGS_SMTP_USER,
    SETTINGS_SMTP_USE_TLS,
    SETTINGS_SMTP_FROM_ADDR,
)

logger = logging.getLogger("CatastoGUI.email_service")

_FOOTER = "\n\n--\nSistema Meridiana · Archivio di Stato di Savona"


class EmailService:
    """
    Wrapper SMTP per Meridiana.

    La password SMTP è custodita in keyring (SERVICE_KEYRING) e mai
    scritta su disco/QSettings in chiaro.
    """

    SERVICE_KEYRING = "Meridiana_SMTP"

    def __init__(self, settings: QSettings | None = None):
        s = settings or QSettings()
        self.enabled: bool = s.value(SETTINGS_SMTP_ENABLED, False, type=bool)
        self.host: str = s.value(SETTINGS_SMTP_HOST, "", type=str)
        self.port: int = s.value(SETTINGS_SMTP_PORT, 587, type=int)
        self.user: str = s.value(SETTINGS_SMTP_USER, "", type=str)
        self.use_tls: bool = s.value(SETTINGS_SMTP_USE_TLS, True, type=bool)
        self.from_addr: str = s.value(SETTINGS_SMTP_FROM_ADDR, "", type=str)
        self.password: str = (
            keyring.get_password(self.SERVICE_KEYRING, self.user) or ""
            if self.user
            else ""
        )

    def is_configured(self) -> bool:
        """True se SMTP è abilitato e i campi minimi sono compilati."""
        return bool(self.enabled and self.host and self.user and self.from_addr)

    def send(self, to: str, subject: str, body: str) -> tuple[bool, str]:
        """
        Invia un'email in modo sincrono.

        Returns:
            (True, "") in caso di successo
            (False, messaggio_errore) in caso di errore
        """
        if not self.is_configured():
            return False, "SMTP non configurato."
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = self.from_addr
            msg["To"] = to
            msg.attach(MIMEText(body, "plain", "utf-8"))

            if self.use_tls:
                server = smtplib.SMTP(self.host, self.port, timeout=10)
                server.starttls()
            else:
                server = smtplib.SMTP_SSL(self.host, self.port, timeout=10)

            if self.password:
                server.login(self.user, self.password)
            server.sendmail(self.from_addr, [to], msg.as_string())
            server.quit()
            logger.info(f"Email inviata a {to}: {subject}")
            return True, ""
        except smtplib.SMTPAuthenticationError as e:
            err = f"Autenticazione SMTP fallita: {e}"
        except smtplib.SMTPConnectError as e:
            err = f"Impossibile connettersi a {self.host}:{self.port}: {e}"
        except smtplib.SMTPException as e:
            err = f"Errore SMTP: {e}"
        except OSError as e:
            err = f"Errore di rete: {e}"
        logger.warning(f"Invio email fallito → {err}")
        return False, err

    # ------------------------------------------------------------------
    # Metodi template — restituiscono (to, subject, body)
    # ------------------------------------------------------------------

    def notify_account_created(
        self, to: str, username: str, nome: str, ruolo: str
    ) -> tuple[str, str, str]:
        subject = "[Meridiana] Nuovo account creato"
        body = (
            f"Gentile {nome},\n\n"
            f"è stato creato un account per il sistema Meridiana - Archivio Catastale Storico.\n\n"
            f"Username : {username}\n"
            f"Ruolo    : {ruolo}\n"
            f"Data     : {datetime.now().strftime('%d/%m/%Y %H:%M')}\n\n"
            f"Usa le credenziali fornite dall'amministratore per accedere."
            f"{_FOOTER}"
        )
        return to, subject, body

    def notify_password_changed(
        self, to: str, username: str, nome: str
    ) -> tuple[str, str, str]:
        subject = "[Meridiana] Password modificata"
        body = (
            f"Gentile {nome},\n\n"
            f"la password del tuo account ({username}) è stata modificata "
            f"il {datetime.now().strftime('%d/%m/%Y alle %H:%M')}.\n\n"
            f"Se non hai richiesto questa modifica, contatta immediatamente l'amministratore."
            f"{_FOOTER}"
        )
        return to, subject, body

    def notify_role_changed(
        self, to: str, username: str, nome: str, old_role: str, new_role: str
    ) -> tuple[str, str, str]:
        subject = "[Meridiana] Ruolo aggiornato"
        body = (
            f"Gentile {nome},\n\n"
            f"il tuo ruolo nel sistema Meridiana è stato aggiornato:\n\n"
            f"  Ruolo precedente : {old_role}\n"
            f"  Nuovo ruolo      : {new_role}\n\n"
            f"Data modifica: {datetime.now().strftime('%d/%m/%Y %H:%M')}"
            f"{_FOOTER}"
        )
        return to, subject, body

    def notify_login(
        self, to: str, username: str, nome: str
    ) -> tuple[str, str, str]:
        subject = "[Meridiana] Accesso effettuato"
        hostname = socket.gethostname()
        body = (
            f"Gentile {nome},\n\n"
            f"è stato registrato un accesso al sistema Meridiana con il tuo account ({username}).\n\n"
            f"Data e ora  : {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n"
            f"Postazione  : {hostname}\n\n"
            f"Se non sei stato tu ad effettuare questo accesso, "
            f"contatta immediatamente l'amministratore."
            f"{_FOOTER}"
        )
        return to, subject, body


class EmailWorker(QThread):
    """
    Invia un'email in un thread separato per non bloccare la UI.

    Emette result(True, "") in caso di successo,
             result(False, messaggio_errore) in caso di errore.
    """

    result = pyqtSignal(bool, str)

    def __init__(
        self,
        service: EmailService,
        to: str,
        subject: str,
        body: str,
        parent=None,
    ):
        super().__init__(parent)
        self._service = service
        self._to = to
        self._subject = subject
        self._body = body

    def run(self):
        ok, err = self._service.send(self._to, self._subject, self._body)
        self.result.emit(ok, err)
