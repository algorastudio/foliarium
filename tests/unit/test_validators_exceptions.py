"""
tests/unit/test_validators_exceptions.py
=========================================
Unit tests per validators.py, catasto_exceptions.py, e app_paths.py.
Questi moduli sono principalmente indipendenti dal DB e testabili con unit test puri.
"""

import pytest
from datetime import date, datetime
from pathlib import Path
import os
import sys

from validators import (
    ValidationResult, FieldValidator, FormValidationResult,
    PROVINCE_ITALIANE, REGIONI_ITALIANE
)
from catasto_exceptions import (
    DBMError, DBUniqueConstraintError, DBNotFoundError, DBDataError
)
from app_paths import get_logo_svg_path, get_doc_path, APP_DATA_DIR, LOG_DIR


# ===========================================================================
# Test ValidationResult
# ===========================================================================

@pytest.mark.unit
class TestValidationResult:

    def test_ok_crea_risultato_valido(self):
        """ValidationResult.ok() deve creare un risultato positivo."""
        result = ValidationResult.ok("test_value")
        assert result.is_valid is True
        assert result.value == "test_value"
        assert result.error_message == ""

    def test_fail_crea_risultato_invalido(self):
        """ValidationResult.fail() deve creare un risultato negativo."""
        result = ValidationResult.fail("Errore di test")
        assert result.is_valid is False
        assert result.value is None
        assert result.error_message == "Errore di test"

    def test_costruttore_diretto(self):
        """Costruttore diretto deve funzionare."""
        result = ValidationResult(is_valid=True, value=42, error_message="")
        assert result.is_valid is True
        assert result.value == 42


# ===========================================================================
# Test FieldValidator - Testo
# ===========================================================================

@pytest.mark.unit
class TestFieldValidatorTesto:

    def test_required_text_valido(self):
        """required_text con testo valido deve restituire ok."""
        result = FieldValidator.required_text("  hello  ", "Nome")
        assert result.is_valid is True
        assert result.value == "hello"

    def test_required_text_vuoto(self):
        """required_text con testo vuoto deve fallire."""
        result = FieldValidator.required_text("", "Nome")
        assert result.is_valid is False
        assert "obbligatorio" in result.error_message.lower()

    def test_required_text_con_max_len(self):
        """required_text deve rispettare max_len."""
        result = FieldValidator.required_text("hello", "Nome", max_len=3)
        assert result.is_valid is False
        assert "non può superare" in result.error_message.lower()

    def test_optional_text_valido(self):
        """optional_text con testo valido deve restituire il valore."""
        result = FieldValidator.optional_text("  hello  ")
        assert result.is_valid is True
        assert result.value == "hello"

    def test_optional_text_vuoto(self):
        """optional_text con testo vuoto deve restituire None."""
        result = FieldValidator.optional_text("")
        assert result.is_valid is True
        assert result.value is None


# ===========================================================================
# Test FieldValidator - Numeri
# ===========================================================================

@pytest.mark.unit
class TestFieldValidatorNumeri:

    def test_integer_positive_valido(self):
        """integer_positive con numero positivo valido."""
        result = FieldValidator.integer_positive("42", "ID")
        assert result.is_valid is True
        assert result.value == 42

    def test_integer_positive_zero_non_permesso(self):
        """integer_positive deve rifiutare zero per default."""
        result = FieldValidator.integer_positive("0", "ID")
        assert result.is_valid is False

    def test_integer_positive_zero_permesso(self):
        """integer_positive con allow_zero=True deve accettare zero."""
        result = FieldValidator.integer_positive("0", "ID", allow_zero=True)
        assert result.is_valid is True
        assert result.value == 0

    def test_integer_positive_negativo(self):
        """integer_positive deve rifiutare numeri negativi."""
        result = FieldValidator.integer_positive("-5", "ID")
        assert result.is_valid is False

    def test_integer_positive_non_numerico(self):
        """integer_positive deve rifiutare stringhe non numeriche."""
        result = FieldValidator.integer_positive("abc", "ID")
        assert result.is_valid is False
        assert "intero" in result.error_message.lower()

    def test_optional_integer_valido(self):
        """optional_integer con numero valido."""
        result = FieldValidator.optional_integer("42", "ID")
        assert result.is_valid is True
        assert result.value == 42

    def test_optional_integer_vuoto(self):
        """optional_integer con stringa vuota deve restituire None."""
        result = FieldValidator.optional_integer("", "ID")
        assert result.is_valid is True
        assert result.value is None

    def test_optional_integer_con_range(self):
        """optional_integer deve rispettare min_val e max_val."""
        result = FieldValidator.optional_integer("50", "Valore", min_val=10, max_val=100)
        assert result.is_valid is True

        result = FieldValidator.optional_integer("5", "Valore", min_val=10)
        assert result.is_valid is False


# ===========================================================================
# Test FieldValidator - Date
# ===========================================================================

@pytest.mark.unit
class TestFieldValidatorDate:

    def test_date_format_valido(self):
        """date_format con data valida nel formato YYYY-MM-DD."""
        result = FieldValidator.date_format("2025-12-31", "Data")
        assert result.is_valid is True
        assert result.value == date(2025, 12, 31)

    def test_date_format_formato_diverso(self):
        """date_format deve supportare formati diversi."""
        result = FieldValidator.date_format("31/12/2025", "Data", fmt="%d/%m/%Y")
        assert result.is_valid is True
        assert result.value == date(2025, 12, 31)

    def test_date_format_invalido(self):
        """date_format con data non valida deve fallire."""
        result = FieldValidator.date_format("2025-13-01", "Data")
        assert result.is_valid is False

    def test_optional_date_vuoto(self):
        """optional_date con stringa vuota deve restituire None."""
        result = FieldValidator.optional_date("", "Data")
        assert result.is_valid is True
        assert result.value is None

    def test_date_range_valido(self):
        """date_range con range valido."""
        result = FieldValidator.date_range("2025-01-01", "2025-12-31", fmt="%Y-%m-%d")
        assert result.is_valid is True
        assert result.value == (date(2025, 1, 1), date(2025, 12, 31))

    def test_date_range_invertito(self):
        """date_range con end < start deve fallire."""
        result = FieldValidator.date_range("2025-12-31", "2025-01-01", fmt="%Y-%m-%d")
        assert result.is_valid is False
        assert "non può precedere" in result.error_message.lower()


# ===========================================================================
# Test FieldValidator - Geografici
# ===========================================================================

@pytest.mark.unit
class TestFieldValidatorGeografici:

    def test_provincia_italiana_valida(self):
        """provincia_italiana con sigla valida."""
        result = FieldValidator.provincia_italiana("RM")
        assert result.is_valid is True
        assert result.value == "RM"

    def test_provincia_italiana_minuscola(self):
        """provincia_italiana deve essere case-insensitive."""
        result = FieldValidator.provincia_italiana("rm")
        assert result.is_valid is True
        assert result.value == "RM"

    def test_provincia_italiana_invalida(self):
        """provincia_italiana con sigla non valida."""
        result = FieldValidator.provincia_italiana("XX")
        assert result.is_valid is False

    def test_regione_italiana_valida(self):
        """regione_italiana con nome valido."""
        result = FieldValidator.regione_italiana("Lazio")
        assert result.is_valid is True
        assert result.value == "Lazio"

    def test_regione_italiana_case_insensitive(self):
        """regione_italiana deve essere case-insensitive."""
        result = FieldValidator.regione_italiana("lazio")
        assert result.is_valid is True
        assert result.value == "Lazio"

    def test_regione_italiana_invalida(self):
        """regione_italiana con nome non valido."""
        result = FieldValidator.regione_italiana("InvalidRegion")
        assert result.is_valid is False


# ===========================================================================
# Test FieldValidator - Codici Catastali
# ===========================================================================

@pytest.mark.unit
class TestFieldValidatorCodiciCatastali:

    def test_codice_catastale_valido(self):
        """codice_catastale con formato valido (A001)."""
        result = FieldValidator.codice_catastale("H501")
        assert result.is_valid is True
        assert result.value == "H501"

    def test_codice_catastale_minuscolo(self):
        """codice_catastale deve normalizzare a maiuscolo."""
        result = FieldValidator.codice_catastale("a001")
        assert result.is_valid is True
        assert result.value == "A001"

    def test_codice_catastale_vuoto(self):
        """codice_catastale vuoto deve restituire None (opzionale)."""
        result = FieldValidator.codice_catastale("")
        assert result.is_valid is True
        assert result.value is None

    def test_codice_catastale_invalido(self):
        """codice_catastale con formato non valido."""
        result = FieldValidator.codice_catastale("1234")  # Deve essere L+3cifre
        assert result.is_valid is False


# ===========================================================================
# Test FieldValidator - Sicurezza/Utenti
# ===========================================================================

@pytest.mark.unit
class TestFieldValidatorSicurezza:

    def test_password_strength_valida(self):
        """password_strength con password valida (8+ chars, almeno 1 digit)."""
        result = FieldValidator.password_strength("MyPass123")
        assert result.is_valid is True

    def test_password_strength_troppo_corta(self):
        """password_strength deve rifiutare password < 8 caratteri."""
        result = FieldValidator.password_strength("Pass1")
        assert result.is_valid is False
        assert "8 caratteri" in result.error_message.lower()

    def test_password_strength_senza_cifra(self):
        """password_strength deve rifiutare password senza cifra."""
        result = FieldValidator.password_strength("MyPassword")
        assert result.is_valid is False
        assert "cifra" in result.error_message.lower()

    def test_username_valido(self):
        """username con nome valido (3+ chars, alfanumerico/dash/underscore)."""
        result = FieldValidator.username("user_123")
        assert result.is_valid is True
        assert result.value == "user_123"

    def test_username_troppo_corto(self):
        """username deve rifiutare username < 3 caratteri."""
        result = FieldValidator.username("ab")
        assert result.is_valid is False

    def test_username_troppo_lungo(self):
        """username deve rifiutare username > 64 caratteri."""
        long_name = "a" * 65
        result = FieldValidator.username(long_name)
        assert result.is_valid is False

    def test_email_valido(self):
        """email con indirizzo valido."""
        result = FieldValidator.email("user@example.com")
        assert result.is_valid is True
        assert result.value == "user@example.com"

    def test_email_vuoto(self):
        """email vuoto deve restituire None (opzionale)."""
        result = FieldValidator.email("")
        assert result.is_valid is True
        assert result.value is None

    def test_email_invalido(self):
        """email con formato non valido."""
        result = FieldValidator.email("notanemail")
        assert result.is_valid is False


# ===========================================================================
# Test FieldValidator - Compositi
# ===========================================================================

@pytest.mark.unit
class TestFieldValidatorCompositi:

    def test_run_all_tutti_validi(self):
        """run_all con tutti i risultati validi."""
        checks = [
            ValidationResult.ok("value1"),
            ValidationResult.ok("value2"),
            ValidationResult.ok(42),
        ]
        result = FieldValidator.run_all(checks)
        assert result.is_valid is True
        assert result.value == ["value1", "value2", 42]

    def test_run_all_primo_invalido(self):
        """run_all deve restituire il primo errore."""
        checks = [
            ValidationResult.ok("value1"),
            ValidationResult.fail("Errore 1"),
            ValidationResult.fail("Errore 2"),
        ]
        result = FieldValidator.run_all(checks)
        assert result.is_valid is False
        assert result.error_message == "Errore 1"

    def test_validate_form_valido(self):
        """validate_form con tutti i campi validi."""
        form_result = FieldValidator.validate_form({
            "nome": ValidationResult.ok("Mario"),
            "provincia": ValidationResult.ok("RM"),
        })
        assert form_result.is_valid is True
        assert form_result.values == {"nome": "Mario", "provincia": "RM"}

    def test_validate_form_con_errori(self):
        """validate_form con alcuni campi non validi."""
        form_result = FieldValidator.validate_form({
            "nome": ValidationResult.ok("Mario"),
            "provincia": ValidationResult.fail("Provincia non valida"),
        })
        assert form_result.is_valid is False
        assert "provincia" in form_result.errors
        assert "Provincia non valida" in form_result.errors["provincia"]


# ===========================================================================
# Test Eccezioni Personalizzate
# ===========================================================================

@pytest.mark.unit
class TestCastoExceptions:

    def test_dbm_error_eredita_exception(self):
        """DBMError deve essere una Exception."""
        exc = DBMError("Test error")
        assert isinstance(exc, Exception)
        assert str(exc) == "Test error"

    def test_db_unique_constraint_error(self):
        """DBUniqueConstraintError deve memorizzare constraint_name e details."""
        exc = DBUniqueConstraintError(
            "Violazione vincolo",
            constraint_name="pk_comune",
            details={"campo": "nome"}
        )
        assert exc.constraint_name == "pk_comune"
        assert exc.details == {"campo": "nome"}
        assert isinstance(exc, DBMError)

    def test_db_not_found_error(self):
        """DBNotFoundError deve essere un DBMError."""
        exc = DBNotFoundError("Record non trovato")
        assert isinstance(exc, DBMError)
        assert str(exc) == "Record non trovato"

    def test_db_data_error(self):
        """DBDataError deve essere un DBMError."""
        exc = DBDataError("Dati non validi")
        assert isinstance(exc, DBMError)


# ===========================================================================
# Test app_paths
# ===========================================================================

@pytest.mark.unit
class TestAppPaths:

    def test_app_data_dir_esiste(self):
        """APP_DATA_DIR deve essere un Path valido."""
        assert isinstance(APP_DATA_DIR, Path)
        # Non necessariamente deve esistere, ma deve essere un Path

    def test_log_dir_esiste(self):
        """LOG_DIR deve essere un Path valido."""
        assert isinstance(LOG_DIR, Path)

    def test_get_logo_svg_path_dark(self):
        """get_logo_svg_path(dark=True) ritorna un Path SVG; se la variante
        dark non e' presente cade su get_logo_path() (PNG)."""
        path = get_logo_svg_path(dark=True)
        assert isinstance(path, Path)
        assert str(path).lower().endswith((".svg", ".png"))

    def test_get_logo_svg_path_light(self):
        """get_logo_svg_path(dark=False) ritorna un Path SVG; PNG come fallback."""
        path = get_logo_svg_path(dark=False)
        assert isinstance(path, Path)
        assert str(path).lower().endswith((".svg", ".png"))

    def test_get_doc_path(self):
        """get_doc_path deve restituire un Path valido."""
        path = get_doc_path("index.md")
        assert isinstance(path, Path)
        assert "index.md" in str(path)

    def test_get_doc_path_nested(self):
        """get_doc_path deve supportare percorsi annidati."""
        path = get_doc_path("primo-avvio/login.md")
        assert isinstance(path, Path)
        assert "primo-avvio" in str(path)


# ===========================================================================
# Test PROVINCE_ITALIANE e REGIONI_ITALIANE
# ===========================================================================

@pytest.mark.unit
class TestCostantiGeografiche:

    def test_province_italiane_contiene_sigle_note(self):
        """PROVINCE_ITALIANE deve contenere le sigle principali."""
        assert "RM" in PROVINCE_ITALIANE  # Roma
        assert "MI" in PROVINCE_ITALIANE  # Milano
        assert "NA" in PROVINCE_ITALIANE  # Napoli
        assert "FI" in PROVINCE_ITALIANE  # Firenze

    def test_province_italiane_lunghezza(self):
        """PROVINCE_ITALIANE deve contenere almeno 107 sigle."""
        assert len(PROVINCE_ITALIANE) >= 107

    def test_regioni_italiane_contiene_regioni_note(self):
        """REGIONI_ITALIANE deve contenere le regioni principali."""
        assert "Lazio" in REGIONI_ITALIANE
        assert "Lombardia" in REGIONI_ITALIANE
        assert "Campania" in REGIONI_ITALIANE
        assert "Toscana" in REGIONI_ITALIANE

    def test_regioni_italiane_lunghezza(self):
        """REGIONI_ITALIANE deve contenere 20 regioni."""
        assert len(REGIONI_ITALIANE) == 20
