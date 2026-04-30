"""
tests/unit/test_validators.py
==============================
Unit test per validators.py — ValidationResult, FieldValidator, FormValidationResult.
Marker: unit
"""
from __future__ import annotations

import pytest
from datetime import date


# ---------------------------------------------------------------------------
# Import
# ---------------------------------------------------------------------------

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from validators import (
    ValidationResult,
    FieldValidator,
    FormValidationResult,
    PROVINCE_ITALIANE,
    REGIONI_ITALIANE,
)


# ===========================================================================
# ValidationResult
# ===========================================================================

@pytest.mark.unit
class TestValidationResult:

    def test_ok_is_valid(self):
        r = ValidationResult.ok("valore")
        assert r.is_valid is True
        assert r.value == "valore"
        assert r.error_message == ""

    def test_ok_with_none_value(self):
        r = ValidationResult.ok(None)
        assert r.is_valid is True
        assert r.value is None

    def test_ok_with_int(self):
        r = ValidationResult.ok(42)
        assert r.value == 42

    def test_fail_is_not_valid(self):
        r = ValidationResult.fail("Errore!")
        assert r.is_valid is False
        assert r.error_message == "Errore!"
        assert r.value is None

    def test_fail_empty_message(self):
        r = ValidationResult.fail("")
        assert r.is_valid is False
        assert r.error_message == ""

    def test_direct_instantiation(self):
        r = ValidationResult(is_valid=True, value=5, error_message="")
        assert r.is_valid is True
        assert r.value == 5


# ===========================================================================
# FieldValidator.required_text
# ===========================================================================

@pytest.mark.unit
class TestRequiredText:

    def test_valid_string(self):
        r = FieldValidator.required_text("Savona", "Nome")
        assert r.is_valid is True
        assert r.value == "Savona"

    def test_strips_whitespace(self):
        r = FieldValidator.required_text("  Savona  ", "Nome")
        assert r.value == "Savona"

    def test_empty_string_fails(self):
        r = FieldValidator.required_text("", "Nome")
        assert r.is_valid is False
        assert "obbligatorio" in r.error_message

    def test_whitespace_only_fails(self):
        r = FieldValidator.required_text("   ", "Campo")
        assert r.is_valid is False

    def test_non_string_fails(self):
        r = FieldValidator.required_text(None, "Nome")  # type: ignore
        assert r.is_valid is False

    def test_max_len_ok(self):
        r = FieldValidator.required_text("abc", "Campo", max_len=10)
        assert r.is_valid is True

    def test_max_len_exceeded(self):
        r = FieldValidator.required_text("abcdefghijk", "Campo", max_len=5)
        assert r.is_valid is False
        assert "5" in r.error_message


# ===========================================================================
# FieldValidator.optional_text
# ===========================================================================

@pytest.mark.unit
class TestOptionalText:

    def test_empty_returns_none(self):
        r = FieldValidator.optional_text("")
        assert r.is_valid is True
        assert r.value is None

    def test_whitespace_returns_none(self):
        r = FieldValidator.optional_text("   ")
        assert r.is_valid is True
        assert r.value is None

    def test_valid_returns_stripped(self):
        r = FieldValidator.optional_text("  testo  ")
        assert r.value == "testo"

    def test_max_len_exceeded(self):
        r = FieldValidator.optional_text("troppo lungo", max_len=5)
        assert r.is_valid is False

    def test_none_input_returns_none(self):
        r = FieldValidator.optional_text(None)  # type: ignore
        assert r.is_valid is True
        assert r.value is None


# ===========================================================================
# FieldValidator.integer_positive
# ===========================================================================

@pytest.mark.unit
class TestIntegerPositive:

    def test_valid_integer(self):
        r = FieldValidator.integer_positive("5", "Numero")
        assert r.is_valid is True
        assert r.value == 5

    def test_zero_fails_by_default(self):
        r = FieldValidator.integer_positive("0", "Numero")
        assert r.is_valid is False

    def test_zero_ok_with_allow_zero(self):
        r = FieldValidator.integer_positive("0", "Numero", allow_zero=True)
        assert r.is_valid is True
        assert r.value == 0

    def test_negative_fails(self):
        r = FieldValidator.integer_positive("-3", "Numero")
        assert r.is_valid is False

    def test_negative_fails_with_allow_zero(self):
        r = FieldValidator.integer_positive("-1", "Numero", allow_zero=True)
        assert r.is_valid is False

    def test_non_numeric_fails(self):
        r = FieldValidator.integer_positive("abc", "Numero")
        assert r.is_valid is False

    def test_empty_fails(self):
        r = FieldValidator.integer_positive("", "Numero")
        assert r.is_valid is False

    def test_none_fails(self):
        r = FieldValidator.integer_positive(None, "Numero")  # type: ignore
        assert r.is_valid is False


# ===========================================================================
# FieldValidator.optional_integer
# ===========================================================================

@pytest.mark.unit
class TestOptionalInteger:

    def test_empty_returns_none(self):
        r = FieldValidator.optional_integer("")
        assert r.is_valid is True
        assert r.value is None

    def test_valid_integer(self):
        r = FieldValidator.optional_integer("10")
        assert r.value == 10

    def test_non_numeric_fails(self):
        r = FieldValidator.optional_integer("abc")
        assert r.is_valid is False

    def test_min_val_ok(self):
        r = FieldValidator.optional_integer("5", min_val=1)
        assert r.is_valid is True

    def test_min_val_fail(self):
        r = FieldValidator.optional_integer("0", min_val=1)
        assert r.is_valid is False

    def test_max_val_ok(self):
        r = FieldValidator.optional_integer("5", max_val=10)
        assert r.is_valid is True

    def test_max_val_fail(self):
        r = FieldValidator.optional_integer("11", max_val=10)
        assert r.is_valid is False

    def test_min_max_range_ok(self):
        r = FieldValidator.optional_integer("5", min_val=1, max_val=10)
        assert r.is_valid is True


# ===========================================================================
# FieldValidator.date_format
# ===========================================================================

@pytest.mark.unit
class TestDateFormat:

    def test_valid_date(self):
        r = FieldValidator.date_format("1900-01-15", "Data")
        assert r.is_valid is True
        assert r.value == date(1900, 1, 15)

    def test_empty_fails(self):
        r = FieldValidator.date_format("", "Data")
        assert r.is_valid is False

    def test_wrong_format_fails(self):
        r = FieldValidator.date_format("15/01/1900", "Data")
        assert r.is_valid is False

    def test_invalid_date_fails(self):
        r = FieldValidator.date_format("1900-13-01", "Data")
        assert r.is_valid is False

    def test_custom_format(self):
        r = FieldValidator.date_format("15/01/1900", "Data", fmt="%d/%m/%Y")
        assert r.is_valid is True
        assert r.value == date(1900, 1, 15)

    def test_none_fails(self):
        r = FieldValidator.date_format(None, "Data")  # type: ignore
        assert r.is_valid is False


# ===========================================================================
# FieldValidator.optional_date
# ===========================================================================

@pytest.mark.unit
class TestOptionalDate:

    def test_empty_returns_none(self):
        r = FieldValidator.optional_date("")
        assert r.is_valid is True
        assert r.value is None

    def test_whitespace_returns_none(self):
        r = FieldValidator.optional_date("   ")
        assert r.is_valid is True
        assert r.value is None

    def test_valid_date_parsed(self):
        r = FieldValidator.optional_date("1900-06-01")
        assert r.value == date(1900, 6, 1)

    def test_invalid_date_fails(self):
        r = FieldValidator.optional_date("not-a-date")
        assert r.is_valid is False


# ===========================================================================
# FieldValidator.date_range
# ===========================================================================

@pytest.mark.unit
class TestDateRange:

    def test_valid_range(self):
        r = FieldValidator.date_range("1900-01-01", "1910-12-31")
        assert r.is_valid is True
        assert r.value == (date(1900, 1, 1), date(1910, 12, 31))

    def test_same_date_is_ok(self):
        r = FieldValidator.date_range("1900-01-01", "1900-01-01")
        assert r.is_valid is True

    def test_end_before_start_fails(self):
        r = FieldValidator.date_range("1910-01-01", "1900-01-01")
        assert r.is_valid is False
        assert "non può precedere" in r.error_message

    def test_both_empty_ok(self):
        r = FieldValidator.date_range("", "")
        assert r.is_valid is True
        assert r.value == (None, None)

    def test_only_start(self):
        r = FieldValidator.date_range("1900-01-01", "")
        assert r.is_valid is True

    def test_invalid_start_fails(self):
        r = FieldValidator.date_range("bad-date", "1910-01-01")
        assert r.is_valid is False


# ===========================================================================
# FieldValidator.provincia_italiana
# ===========================================================================

@pytest.mark.unit
class TestProvinciaItaliana:

    def test_valid_province(self):
        for prov in ["SV", "GE", "RM", "MI", "NA"]:
            r = FieldValidator.provincia_italiana(prov)
            assert r.is_valid is True
            assert r.value == prov

    def test_lowercase_normalized(self):
        r = FieldValidator.provincia_italiana("sv")
        assert r.is_valid is True
        assert r.value == "SV"

    def test_invalid_province(self):
        r = FieldValidator.provincia_italiana("XX")
        assert r.is_valid is False

    def test_empty_fails(self):
        r = FieldValidator.provincia_italiana("")
        assert r.is_valid is False

    def test_none_fails(self):
        r = FieldValidator.provincia_italiana(None)  # type: ignore
        assert r.is_valid is False

    def test_all_107_provinces_valid(self):
        for prov in PROVINCE_ITALIANE:
            r = FieldValidator.provincia_italiana(prov)
            assert r.is_valid is True, f"Provincia {prov} dovrebbe essere valida"


# ===========================================================================
# FieldValidator.regione_italiana
# ===========================================================================

@pytest.mark.unit
class TestRegioneItaliana:

    def test_valid_regione(self):
        r = FieldValidator.regione_italiana("Liguria")
        assert r.is_valid is True
        assert r.value == "Liguria"

    def test_case_insensitive(self):
        r = FieldValidator.regione_italiana("liguria")
        assert r.is_valid is True
        assert r.value == "Liguria"

    def test_invalid_regione(self):
        r = FieldValidator.regione_italiana("Atlantide")
        assert r.is_valid is False

    def test_empty_fails(self):
        r = FieldValidator.regione_italiana("")
        assert r.is_valid is False

    def test_all_regions_valid(self):
        for reg in REGIONI_ITALIANE:
            r = FieldValidator.regione_italiana(reg)
            assert r.is_valid is True, f"Regione {reg} dovrebbe essere valida"


# ===========================================================================
# FieldValidator.codice_catastale
# ===========================================================================

@pytest.mark.unit
class TestCodiceCatastale:

    def test_valid_codes(self):
        for code in ["A001", "Z999", "B123"]:
            r = FieldValidator.codice_catastale(code)
            assert r.is_valid is True
            assert r.value == code

    def test_lowercase_normalized(self):
        r = FieldValidator.codice_catastale("a001")
        assert r.is_valid is True
        assert r.value == "A001"

    def test_empty_returns_none(self):
        r = FieldValidator.codice_catastale("")
        assert r.is_valid is True
        assert r.value is None

    def test_invalid_format(self):
        for bad in ["1A00", "AA01", "A0001", "A00"]:
            r = FieldValidator.codice_catastale(bad)
            assert r.is_valid is False, f"'{bad}' dovrebbe fallire"


# ===========================================================================
# FieldValidator.password_strength
# ===========================================================================

@pytest.mark.unit
class TestPasswordStrength:

    def test_valid_password(self):
        r = FieldValidator.password_strength("Password1")
        assert r.is_valid is True
        assert r.value == "Password1"

    def test_too_short(self):
        r = FieldValidator.password_strength("Pass1")
        assert r.is_valid is False
        assert "8" in r.error_message

    def test_no_digit(self):
        r = FieldValidator.password_strength("Passwordonly")
        assert r.is_valid is False
        assert "cifra" in r.error_message

    def test_empty_fails(self):
        r = FieldValidator.password_strength("")
        assert r.is_valid is False

    def test_exactly_8_chars_with_digit(self):
        r = FieldValidator.password_strength("passw0rd")
        assert r.is_valid is True

    def test_all_digits_valid_length(self):
        r = FieldValidator.password_strength("12345678")
        assert r.is_valid is True


# ===========================================================================
# FieldValidator.username
# ===========================================================================

@pytest.mark.unit
class TestUsername:

    def test_valid_username(self):
        r = FieldValidator.username("mario_rossi")
        assert r.is_valid is True
        assert r.value == "mario_rossi"

    def test_with_hyphen(self):
        r = FieldValidator.username("mario-rossi")
        assert r.is_valid is True

    def test_too_short(self):
        r = FieldValidator.username("ab")
        assert r.is_valid is False

    def test_too_long(self):
        r = FieldValidator.username("a" * 65)
        assert r.is_valid is False

    def test_special_chars_fail(self):
        r = FieldValidator.username("mario rossi")
        assert r.is_valid is False

    def test_empty_fails(self):
        r = FieldValidator.username("")
        assert r.is_valid is False

    def test_strips_and_validates(self):
        r = FieldValidator.username("  mario  ")
        assert r.value == "mario"

    def test_exactly_3_chars(self):
        r = FieldValidator.username("abc")
        assert r.is_valid is True

    def test_exactly_64_chars(self):
        r = FieldValidator.username("a" * 64)
        assert r.is_valid is True


# ===========================================================================
# FieldValidator.email
# ===========================================================================

@pytest.mark.unit
class TestEmail:

    def test_valid_email(self):
        r = FieldValidator.email("test@example.com")
        assert r.is_valid is True
        assert r.value == "test@example.com"

    def test_empty_returns_none(self):
        r = FieldValidator.email("")
        assert r.is_valid is True
        assert r.value is None

    def test_whitespace_returns_none(self):
        r = FieldValidator.email("   ")
        assert r.is_valid is True
        assert r.value is None

    def test_missing_at_fails(self):
        r = FieldValidator.email("notanemail")
        assert r.is_valid is False

    def test_missing_domain_fails(self):
        r = FieldValidator.email("user@")
        assert r.is_valid is False

    def test_none_returns_none(self):
        r = FieldValidator.email(None)  # type: ignore
        assert r.is_valid is True
        assert r.value is None


# ===========================================================================
# FieldValidator.run_all
# ===========================================================================

@pytest.mark.unit
class TestRunAll:

    def test_all_valid(self):
        checks = [
            ValidationResult.ok("Savona"),
            ValidationResult.ok(5),
            ValidationResult.ok(date(1900, 1, 1)),
        ]
        r = FieldValidator.run_all(checks)
        assert r.is_valid is True
        assert r.value == ["Savona", 5, date(1900, 1, 1)]

    def test_first_error_returned(self):
        checks = [
            ValidationResult.ok("ok"),
            ValidationResult.fail("Errore sul secondo"),
            ValidationResult.fail("Errore sul terzo"),
        ]
        r = FieldValidator.run_all(checks)
        assert r.is_valid is False
        assert "secondo" in r.error_message

    def test_empty_list_ok(self):
        r = FieldValidator.run_all([])
        assert r.is_valid is True
        assert r.value == []


# ===========================================================================
# FormValidationResult
# ===========================================================================

@pytest.mark.unit
class TestFormValidationResult:

    def test_all_valid(self):
        result = FieldValidator.validate_form({
            "nome": FieldValidator.required_text("Savona", "Nome"),
            "provincia": FieldValidator.provincia_italiana("SV"),
        })
        assert result.is_valid is True
        assert result.errors == {}
        assert result.values["nome"] == "Savona"
        assert result.values["provincia"] == "SV"

    def test_one_invalid(self):
        result = FieldValidator.validate_form({
            "nome": FieldValidator.required_text("", "Nome"),
            "provincia": FieldValidator.provincia_italiana("SV"),
        })
        assert result.is_valid is False
        assert "nome" in result.errors
        assert "provincia" not in result.errors

    def test_first_error(self):
        result = FieldValidator.validate_form({
            "nome": ValidationResult.fail("Errore nome"),
            "provincia": ValidationResult.fail("Errore provincia"),
        })
        assert result.first_error() in ("Errore nome", "Errore provincia")

    def test_first_error_empty_when_valid(self):
        result = FieldValidator.validate_form({
            "nome": ValidationResult.ok("Savona"),
        })
        assert result.first_error() == ""

    def test_values_only_includes_valid_fields(self):
        result = FieldValidator.validate_form({
            "nome": ValidationResult.ok("Savona"),
            "bad": ValidationResult.fail("errore"),
        })
        assert "nome" in result.values
        assert "bad" not in result.values

    def test_empty_form_is_valid(self):
        result = FieldValidator.validate_form({})
        assert result.is_valid is True
        assert result.first_error() == ""
