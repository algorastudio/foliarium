"""
tests/unit/test_email_service.py
=================================
Unit test per email_service.py — template email, servizio SMTP, worker.

Tutti i test mockano SMTP e keyring per essere eseguibili senza
connessione di rete e senza Qt event loop completo.
"""

import os
import sys
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))


# ===========================================================================
# Helper: crea un EmailService senza leggere QSettings / keyring reali
# ===========================================================================

def _make_service(enabled=True, host="smtp.test.com", port=587, user="user@test.com",
                  use_tls=True, from_addr="noreply@test.com", password="secret"):
    """Costruisce un EmailService con attributi iniettati (senza QSettings/keyring)."""
    from foliarium.core.services.email import EmailService
    svc = EmailService.__new__(EmailService)
    svc.enabled = enabled
    svc.host = host
    svc.port = port
    svc.user = user
    svc.use_tls = use_tls
    svc.from_addr = from_addr
    svc.password = password
    return svc


# ===========================================================================
# EmailService.is_configured
# ===========================================================================


@pytest.mark.unit
class TestEmailServiceIsConfigured:
    def test_fully_configured(self):
        svc = _make_service()
        assert svc.is_configured()

    def test_not_enabled(self):
        svc = _make_service(enabled=False)
        assert not svc.is_configured()

    def test_missing_host(self):
        svc = _make_service(host="")
        assert not svc.is_configured()

    def test_missing_user(self):
        svc = _make_service(user="")
        assert not svc.is_configured()

    def test_missing_from_addr(self):
        svc = _make_service(from_addr="")
        assert not svc.is_configured()


# ===========================================================================
# EmailService.send (con mock SMTP)
# ===========================================================================


@pytest.mark.unit
class TestEmailServiceSend:
    def test_not_configured_returns_error(self):
        svc = _make_service(enabled=False)
        ok, err = svc.send("to@test.com", "Subj", "Body")
        assert not ok
        assert "non configurato" in err.lower()

    @patch("foliarium.core.services.email.smtplib.SMTP")
    def test_send_tls_success(self, mock_smtp_cls):
        mock_server = MagicMock()
        mock_smtp_cls.return_value = mock_server

        svc = _make_service(use_tls=True)
        ok, err = svc.send("to@test.com", "Test Subject", "Body text")

        assert ok
        assert err == ""
        mock_smtp_cls.assert_called_once_with("smtp.test.com", 587, timeout=10)
        mock_server.starttls.assert_called_once()
        mock_server.login.assert_called_once_with("user@test.com", "secret")
        mock_server.sendmail.assert_called_once()
        mock_server.quit.assert_called_once()

    @patch("foliarium.core.services.email.smtplib.SMTP_SSL")
    def test_send_ssl_success(self, mock_smtp_ssl_cls):
        mock_server = MagicMock()
        mock_smtp_ssl_cls.return_value = mock_server

        svc = _make_service(use_tls=False)
        ok, err = svc.send("to@test.com", "Test", "Body")

        assert ok
        mock_smtp_ssl_cls.assert_called_once_with("smtp.test.com", 587, timeout=10)
        mock_server.starttls.assert_not_called()

    @patch("foliarium.core.services.email.smtplib.SMTP")
    def test_send_no_password(self, mock_smtp_cls):
        mock_server = MagicMock()
        mock_smtp_cls.return_value = mock_server

        svc = _make_service(password="")
        ok, _ = svc.send("to@test.com", "Test", "Body")

        assert ok
        mock_server.login.assert_not_called()

    @patch("foliarium.core.services.email.smtplib.SMTP")
    def test_auth_error(self, mock_smtp_cls):
        import smtplib
        mock_server = MagicMock()
        mock_server.login.side_effect = smtplib.SMTPAuthenticationError(535, b"Bad credentials")
        mock_smtp_cls.return_value = mock_server

        svc = _make_service()
        ok, err = svc.send("to@test.com", "Test", "Body")

        assert not ok
        assert "autenticazione" in err.lower()

    @patch("foliarium.core.services.email.smtplib.SMTP")
    def test_connect_error(self, mock_smtp_cls):
        import smtplib
        mock_smtp_cls.side_effect = smtplib.SMTPConnectError(421, b"Service unavailable")

        svc = _make_service()
        ok, err = svc.send("to@test.com", "Test", "Body")

        assert not ok
        assert "connettersi" in err.lower()

    @patch("foliarium.core.services.email.smtplib.SMTP")
    def test_network_error(self, mock_smtp_cls):
        mock_smtp_cls.side_effect = OSError("Network unreachable")

        svc = _make_service()
        ok, err = svc.send("to@test.com", "Test", "Body")

        assert not ok
        assert "rete" in err.lower()


# ===========================================================================
# Template email
# ===========================================================================


@pytest.mark.unit
class TestEmailTemplates:
    def setup_method(self):
        self.svc = _make_service()

    def test_notify_account_created(self):
        to, subject, body = self.svc.notify_account_created(
            "mario@test.com", "mario.rossi", "Mario Rossi", "archivista"
        )
        assert to == "mario@test.com"
        assert "Foliarium" in subject
        assert "account" in subject.lower() or "creato" in subject.lower()
        assert "Mario Rossi" in body
        assert "mario.rossi" in body
        assert "archivista" in body

    def test_notify_password_changed(self):
        to, subject, body = self.svc.notify_password_changed(
            "mario@test.com", "mario.rossi", "Mario Rossi"
        )
        assert to == "mario@test.com"
        assert "password" in subject.lower()
        assert "mario.rossi" in body
        assert "amministratore" in body.lower()

    def test_notify_role_changed(self):
        to, subject, body = self.svc.notify_role_changed(
            "mario@test.com", "mario.rossi", "Mario Rossi",
            "visualizzatore", "archivista"
        )
        assert to == "mario@test.com"
        assert "ruolo" in subject.lower()
        assert "visualizzatore" in body
        assert "archivista" in body

    def test_notify_login(self):
        to, subject, body = self.svc.notify_login(
            "mario@test.com", "mario.rossi", "Mario Rossi"
        )
        assert to == "mario@test.com"
        assert "accesso" in subject.lower()
        assert "mario.rossi" in body

    def test_all_templates_have_footer(self):
        templates = [
            self.svc.notify_account_created("a@b.com", "u", "N", "r"),
            self.svc.notify_password_changed("a@b.com", "u", "N"),
            self.svc.notify_role_changed("a@b.com", "u", "N", "old", "new"),
            self.svc.notify_login("a@b.com", "u", "N"),
        ]
        for _, _, body in templates:
            assert "Foliarium" in body
            assert "--" in body
