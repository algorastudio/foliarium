"""
tests/unit/test_new_modules.py
==============================
Unit test per i nuovi moduli introdotti nel sistema foliarium:
  - validators.py
  - utils/error_handlers.py
  - utils/logger_config.py
  - utils/config_manager.py
  - core/session_manager.py
"""

import pytest
import sys
import os

# Assicura che la root del progetto sia nel path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))


# ===========================================================================
# validators.py
# ===========================================================================

@pytest.mark.unit
class TestFieldValidatorRequiredText:
    def test_valid_text(self):
        from validators import FieldValidator
        r = FieldValidator.required_text("  Savona  ", "Nome")
        assert r.is_valid
        assert r.value == "Savona"

    def test_empty_string(self):
        from validators import FieldValidator
        r = FieldValidator.required_text("", "Nome")
        assert not r.is_valid
        assert "obbligatorio" in r.error_message

    def test_whitespace_only(self):
        from validators import FieldValidator
        r = FieldValidator.required_text("   ", "Campo")
        assert not r.is_valid

    def test_max_len_exceeded(self):
        from validators import FieldValidator
        r = FieldValidator.required_text("A" * 101, "Nome", max_len=100)
        assert not r.is_valid
        assert "100" in r.error_message

    def test_max_len_ok(self):
        from validators import FieldValidator
        r = FieldValidator.required_text("A" * 100, "Nome", max_len=100)
        assert r.is_valid


@pytest.mark.unit
class TestFieldValidatorIntegerPositive:
    def test_valid_positive(self):
        from validators import FieldValidator
        r = FieldValidator.integer_positive("42", "N")
        assert r.is_valid
        assert r.value == 42

    def test_zero_not_allowed(self):
        from validators import FieldValidator
        r = FieldValidator.integer_positive("0", "N")
        assert not r.is_valid

    def test_zero_allowed(self):
        from validators import FieldValidator
        r = FieldValidator.integer_positive("0", "N", allow_zero=True)
        assert r.is_valid

    def test_non_numeric(self):
        from validators import FieldValidator
        r = FieldValidator.integer_positive("abc", "N")
        assert not r.is_valid

    def test_negative(self):
        from validators import FieldValidator
        r = FieldValidator.integer_positive("-1", "N")
        assert not r.is_valid


@pytest.mark.unit
class TestFieldValidatorDate:
    def test_valid_date(self):
        from validators import FieldValidator
        from datetime import date
        r = FieldValidator.date_format("2024-03-15", "Data")
        assert r.is_valid
        assert r.value == date(2024, 3, 15)

    def test_invalid_format(self):
        from validators import FieldValidator
        r = FieldValidator.date_format("15/03/2024", "Data")
        assert not r.is_valid

    def test_empty_required(self):
        from validators import FieldValidator
        r = FieldValidator.date_format("", "Data")
        assert not r.is_valid

    def test_optional_date_empty(self):
        from validators import FieldValidator
        r = FieldValidator.optional_date("")
        assert r.is_valid
        assert r.value is None

    def test_date_range_valid(self):
        from validators import FieldValidator
        r = FieldValidator.date_range("2020-01-01", "2024-12-31")
        assert r.is_valid

    def test_date_range_inverted(self):
        from validators import FieldValidator
        r = FieldValidator.date_range("2024-12-31", "2020-01-01")
        assert not r.is_valid


@pytest.mark.unit
class TestFieldValidatorProvincia:
    def test_valid_uppercase(self):
        from validators import FieldValidator
        r = FieldValidator.provincia_italiana("SV")
        assert r.is_valid
        assert r.value == "SV"

    def test_valid_lowercase(self):
        from validators import FieldValidator
        r = FieldValidator.provincia_italiana("sv")
        assert r.is_valid
        assert r.value == "SV"

    def test_invalid(self):
        from validators import FieldValidator
        r = FieldValidator.provincia_italiana("XX")
        assert not r.is_valid

    def test_empty(self):
        from validators import FieldValidator
        r = FieldValidator.provincia_italiana("")
        assert not r.is_valid


@pytest.mark.unit
class TestFieldValidatorCodiceCatastale:
    def test_valid(self):
        from validators import FieldValidator
        r = FieldValidator.codice_catastale("I480")
        assert r.is_valid
        assert r.value == "I480"

    def test_lowercase_normalized(self):
        from validators import FieldValidator
        r = FieldValidator.codice_catastale("i480")
        assert r.is_valid
        assert r.value == "I480"

    def test_invalid_format(self):
        from validators import FieldValidator
        r = FieldValidator.codice_catastale("1234")
        assert not r.is_valid

    def test_empty_ok(self):
        from validators import FieldValidator
        r = FieldValidator.codice_catastale("")
        assert r.is_valid
        assert r.value is None


@pytest.mark.unit
class TestFieldValidatorPassword:
    def test_strong_password(self):
        from validators import FieldValidator
        r = FieldValidator.password_strength("Sicura123")
        assert r.is_valid

    def test_too_short(self):
        from validators import FieldValidator
        r = FieldValidator.password_strength("abc1")
        assert not r.is_valid
        assert "8" in r.error_message

    def test_no_digit(self):
        from validators import FieldValidator
        r = FieldValidator.password_strength("SenzaCifre")
        assert not r.is_valid
        assert "cifra" in r.error_message

    def test_empty(self):
        from validators import FieldValidator
        r = FieldValidator.password_strength("")
        assert not r.is_valid


@pytest.mark.unit
class TestFormValidationResult:
    def test_all_valid(self):
        from validators import FieldValidator
        result = FieldValidator.validate_form({
            "nome": FieldValidator.required_text("Savona", "Nome"),
            "provincia": FieldValidator.provincia_italiana("SV"),
        })
        assert result.is_valid
        assert result.errors == {}
        assert result.values["nome"] == "Savona"
        assert result.values["provincia"] == "SV"

    def test_partial_errors(self):
        from validators import FieldValidator
        result = FieldValidator.validate_form({
            "nome": FieldValidator.required_text("", "Nome"),
            "provincia": FieldValidator.provincia_italiana("SV"),
        })
        assert not result.is_valid
        assert "nome" in result.errors
        assert "provincia" not in result.errors

    def test_first_error(self):
        from validators import FieldValidator
        result = FieldValidator.validate_form({
            "nome": FieldValidator.required_text("", "Nome"),
        })
        assert result.first_error() != ""

    def test_first_error_empty_when_valid(self):
        from validators import FieldValidator
        result = FieldValidator.validate_form({
            "nome": FieldValidator.required_text("Savona", "Nome"),
        })
        assert result.first_error() == ""


# ===========================================================================
# utils/error_handlers.py
# ===========================================================================

@pytest.mark.unit
class TestCatastoExceptions:
    def test_hierarchy(self):
        from utils.error_handlers import (
            CatastoError, DatabaseError, AuthenticationError,
            ValidationError, NotFoundError, DuplicateError,
        )
        assert issubclass(DatabaseError, CatastoError)
        assert issubclass(AuthenticationError, CatastoError)
        assert issubclass(ValidationError, CatastoError)
        assert issubclass(NotFoundError, CatastoError)
        assert issubclass(DuplicateError, CatastoError)

    def test_validation_error_has_field(self):
        from utils.error_handlers import ValidationError
        e = ValidationError("Campo richiesto", field_name="nome")
        assert e.field_name == "nome"
        assert str(e) == "Campo richiesto"

    def test_duplicate_error_has_constraint(self):
        from utils.error_handlers import DuplicateError
        e = DuplicateError("Duplicato", constraint="unique_nome")
        assert e.constraint == "unique_nome"


@pytest.mark.unit
class TestHandleDbErrors:
    def test_reraises_catasto_error_unchanged(self):
        from utils.error_handlers import handle_db_errors, DatabaseError, NotFoundError

        @handle_db_errors("Test op")
        def raises_not_found():
            raise NotFoundError("non trovato")

        with pytest.raises(NotFoundError):
            raises_not_found()

    def test_wraps_generic_exception(self):
        from utils.error_handlers import handle_db_errors, DatabaseError

        @handle_db_errors("Test op")
        def raises_generic():
            raise RuntimeError("errore generico")

        with pytest.raises(DatabaseError) as exc_info:
            raises_generic()
        assert "Test op" in str(exc_info.value)

    def test_returns_value_on_success(self):
        from utils.error_handlers import handle_db_errors

        @handle_db_errors("Test")
        def returns_42():
            return 42

        assert returns_42() == 42

    def test_custom_reraise_type(self):
        from utils.error_handlers import handle_db_errors, AuthenticationError

        @handle_db_errors("Auth", reraise_as=AuthenticationError)
        def raises():
            raise ValueError("bad value")

        with pytest.raises(AuthenticationError):
            raises()


@pytest.mark.unit
class TestHandleUiErrors:
    def test_catches_exception_no_dialog(self):
        from utils.error_handlers import handle_ui_errors

        @handle_ui_errors("Test op", show_dialog=False)
        def fails():
            raise RuntimeError("UI error")

        # Non dovrebbe propagare l'eccezione
        result = fails()
        assert result is None

    def test_returns_value_on_success(self):
        from utils.error_handlers import handle_ui_errors

        @handle_ui_errors("Test", show_dialog=False)
        def ok():
            return "ciao"

        assert ok() == "ciao"


# ===========================================================================
# utils/logger_config.py
# ===========================================================================

@pytest.mark.unit
class TestLoggerConfig:
    def setup_method(self):
        from utils.logger_config import reset_logging
        reset_logging()

    def test_get_logger_prefixes_name(self):
        from utils.logger_config import get_logger
        import logging
        log = get_logger("mymodule")
        assert log.name == "foliarium.mymodule"

    def test_get_logger_already_prefixed(self):
        from utils.logger_config import get_logger
        log = get_logger("foliarium.mymodule")
        assert log.name == "foliarium.mymodule"

    def test_configure_sets_level(self):
        from utils.logger_config import configure_logging, get_logger
        import logging
        configure_logging(level="DEBUG", console=False)
        root = logging.getLogger("foliarium")
        assert root.level == logging.DEBUG

    def test_configure_idempotent(self):
        from utils.logger_config import configure_logging, reset_logging
        import logging
        configure_logging(level="INFO", console=True)
        root = logging.getLogger("foliarium")
        handler_count = len(root.handlers)
        # Seconda chiamata non deve aggiungere handler
        configure_logging(level="INFO", console=True)
        assert len(root.handlers) == handler_count

    def teardown_method(self):
        from utils.logger_config import reset_logging
        reset_logging()


# ===========================================================================
# utils/config_manager.py
# ===========================================================================

@pytest.mark.unit
class TestDatabaseConfig:
    def test_defaults(self):
        from utils.config_manager import DatabaseConfig
        cfg = DatabaseConfig()
        assert cfg.host == "localhost"
        assert cfg.port == 5432
        assert cfg.dbname == "catasto_storico"

    def test_invalid_port(self):
        from utils.config_manager import DatabaseConfig
        with pytest.raises(ValueError):
            DatabaseConfig(port=0)

    def test_invalid_pool(self):
        from utils.config_manager import DatabaseConfig
        with pytest.raises(ValueError):
            DatabaseConfig(min_conn=10, max_conn=5)

    def test_safe_repr_hides_password(self):
        from utils.config_manager import DatabaseConfig
        cfg = DatabaseConfig(password="segreto")
        assert "segreto" not in cfg.safe_repr()

    def test_as_psycopg2_kwargs(self):
        from utils.config_manager import DatabaseConfig
        cfg = DatabaseConfig(host="db.example.com", port=5433)
        kwargs = cfg.as_psycopg2_kwargs()
        assert kwargs["host"] == "db.example.com"
        assert kwargs["port"] == 5433
        assert "password" in kwargs

    def test_from_env(self, monkeypatch):
        from utils.config_manager import DatabaseConfig
        monkeypatch.setenv("DB_HOST", "myhost")
        monkeypatch.setenv("DB_NAME", "mydb")
        monkeypatch.setenv("DB_USER", "myuser")
        monkeypatch.setenv("DB_PASS", "mypass")
        monkeypatch.setenv("DB_PORT", "5433")
        cfg = DatabaseConfig.from_env()
        assert cfg.host == "myhost"
        assert cfg.dbname == "mydb"
        assert cfg.user == "myuser"
        assert cfg.password == "mypass"
        assert cfg.port == 5433

    def test_with_password(self):
        from utils.config_manager import DatabaseConfig
        cfg = DatabaseConfig()
        cfg2 = cfg.with_password("nuova")
        assert cfg2.password == "nuova"
        assert cfg.password == ""  # immutabile


@pytest.mark.unit
class TestAppConfig:
    def test_defaults(self):
        from utils.config_manager import AppConfig
        cfg = AppConfig()
        assert cfg.log_level == "INFO"
        assert cfg.session_timeout_minutes == 15

    def test_invalid_log_level(self):
        from utils.config_manager import AppConfig
        with pytest.raises(ValueError):
            AppConfig(log_level="INVALID")

    def test_negative_timeout(self):
        from utils.config_manager import AppConfig
        with pytest.raises(ValueError):
            AppConfig(session_timeout_minutes=-1)

    def test_export_path(self):
        from utils.config_manager import AppConfig
        from pathlib import Path
        cfg = AppConfig(export_directory="./esportazioni")
        assert isinstance(cfg.export_path, Path)


# ===========================================================================
# core/session_manager.py
# ===========================================================================

@pytest.mark.unit
class TestSessionManager:
    def test_initial_state(self):
        from core.session_manager import SessionManager
        s = SessionManager()
        assert not s.is_authenticated
        assert s.user_id is None
        assert s.role is None
        assert s.display_name == ""

    def test_login(self):
        from core.session_manager import SessionManager
        s = SessionManager()
        s.login(
            user_id=42,
            user_info={"nome": "Mario Rossi", "ruolo": "archivista"},
        )
        assert s.is_authenticated
        assert s.user_id == 42
        assert s.display_name == "Mario Rossi"
        assert s.role == "archivista"

    def test_logout(self):
        from core.session_manager import SessionManager
        s = SessionManager()
        s.login(1, {"nome": "Test", "ruolo": "admin"})
        s.logout()
        assert not s.is_authenticated
        assert s.user_id is None

    def test_has_permission_admin(self):
        from core.session_manager import SessionManager
        s = SessionManager()
        s.login(1, {"nome": "Admin", "ruolo": "admin"})
        assert s.has_permission("manage_users")
        assert s.has_permission("delete")
        assert s.has_permission("configure")

    def test_has_permission_archivista(self):
        from core.session_manager import SessionManager
        s = SessionManager()
        s.login(2, {"nome": "Arch", "ruolo": "archivista"})
        assert s.has_permission("insert")
        assert not s.has_permission("manage_users")

    def test_has_permission_visualizzatore(self):
        from core.session_manager import SessionManager
        s = SessionManager()
        s.login(3, {"nome": "View", "ruolo": "visualizzatore"})
        assert s.has_permission("view")
        assert not s.has_permission("insert")
        assert not s.has_permission("delete")

    def test_no_permission_when_logged_out(self):
        from core.session_manager import SessionManager
        s = SessionManager()
        assert not s.has_permission("view")

    def test_is_admin(self):
        from core.session_manager import SessionManager
        s = SessionManager()
        s.login(1, {"nome": "A", "ruolo": "admin"})
        assert s.is_admin()

    def test_is_not_admin(self):
        from core.session_manager import SessionManager
        s = SessionManager()
        s.login(2, {"nome": "B", "ruolo": "archivista"})
        assert not s.is_admin()

    def test_can_all(self):
        from core.session_manager import SessionManager
        s = SessionManager()
        s.login(1, {"nome": "A", "ruolo": "admin"})
        assert s.can("view", "insert", "delete")

    def test_can_any(self):
        from core.session_manager import SessionManager
        s = SessionManager()
        s.login(3, {"nome": "V", "ruolo": "visualizzatore"})
        assert s.can_any("view", "delete")
        assert not s.can_any("insert", "delete")

    def test_session_id_generated(self):
        from core.session_manager import SessionManager
        s = SessionManager()
        s.login(1, {"nome": "A", "ruolo": "admin"})
        assert s.session_id is not None
        assert len(s.session_id) > 8

    def test_custom_session_id(self):
        from core.session_manager import SessionManager
        s = SessionManager()
        s.login(1, {"nome": "A", "ruolo": "admin"}, session_id="my-session-id")
        assert s.session_id == "my-session-id"

    def test_is_timed_out_false_when_zero(self):
        from core.session_manager import SessionManager
        s = SessionManager()
        s.login(1, {"nome": "A", "ruolo": "admin"})
        assert not s.is_timed_out(0)

    def test_is_timed_out_not_authenticated(self):
        from core.session_manager import SessionManager
        s = SessionManager()
        assert not s.is_timed_out(15)

    def test_audit_context(self):
        from core.session_manager import SessionManager
        s = SessionManager()
        s.login(7, {"nome": "A", "ruolo": "admin"},
                session_id="sess-123", client_ip="192.168.1.1")
        ctx = s.get_audit_context()
        assert ctx["user_id"] == 7
        assert ctx["session_id"] == "sess-123"
        assert ctx["client_ip"] == "192.168.1.1"

    def test_repr_authenticated(self):
        from core.session_manager import SessionManager
        s = SessionManager()
        s.login(1, {"nome": "Mario", "ruolo": "admin"})
        assert "Mario" in repr(s)

    def test_repr_not_authenticated(self):
        from core.session_manager import SessionManager
        s = SessionManager()
        assert "non autenticato" in repr(s)


@pytest.mark.unit
class TestValidationResult:
    def test_ok_factory(self):
        from validators import ValidationResult
        r = ValidationResult.ok(42)
        assert r.is_valid
        assert r.value == 42
        assert r.error_message == ""

    def test_fail_factory(self):
        from validators import ValidationResult
        r = ValidationResult.fail("Errore")
        assert not r.is_valid
        assert r.value is None
        assert r.error_message == "Errore"
