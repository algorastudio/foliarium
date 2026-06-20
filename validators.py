"""
validators.py — Sistema di validazione centralizzato per Foliarium.

Fornisce dataclass e metodi statici per validare input utente in modo
uniforme sia nei form PyQt6 che nella logica di business.

Utilizzo:
    from validators import FieldValidator, ValidationResult

    result = FieldValidator.required_text(value, "Nome comune")
    if not result.is_valid:
        show_error(result.error_message)
    else:
        save(result.value)
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, List, Optional


# ---------------------------------------------------------------------------
# Policy password
# ---------------------------------------------------------------------------

#: Lunghezza minima della password.
MIN_PASSWORD_LENGTH = 10

#: Password comuni/banali rifiutate a prescindere dalla composizione.
#: Confronto case-insensitive sull'intera stringa.
COMMON_WEAK_PASSWORDS = frozenset({
    "password", "password1", "password12", "password123", "passw0rd1",
    "12345678", "123456789", "1234567890", "qwertyuiop", "qwerty1234",
    "admin12345", "administrator", "amministratore", "foliarium1", "foliarium12",
    "letmein123", "welcome123", "iloveyou12", "changeme123", "benvenuto1",
})


# ---------------------------------------------------------------------------
# Risultato di validazione
# ---------------------------------------------------------------------------

@dataclass
class ValidationResult:
    """Risultato di una singola operazione di validazione."""
    is_valid: bool
    value: Optional[Any] = None
    error_message: str = ""

    @classmethod
    def ok(cls, value: Any) -> "ValidationResult":
        return cls(is_valid=True, value=value)

    @classmethod
    def fail(cls, message: str) -> "ValidationResult":
        return cls(is_valid=False, error_message=message)


# ---------------------------------------------------------------------------
# Province italiane (107 sigle ufficiali)
# ---------------------------------------------------------------------------

PROVINCE_ITALIANE: List[str] = [
    "AG", "AL", "AN", "AO", "AR", "AP", "AT", "AV",
    "BA", "BT", "BL", "BN", "BG", "BI", "BO", "BZ",
    "BS", "BR", "CA", "CL", "CB", "CI", "CE", "CT",
    "CZ", "CH", "CO", "CS", "CR", "KR", "CN", "EN",
    "FM", "FE", "FI", "FG", "FC", "FR", "GE", "GO",
    "GR", "IM", "IS", "SP", "LT", "LE", "LC", "LI",
    "LO", "LU", "MC", "MN", "MS", "MT", "ME", "MI",
    "MO", "MB", "NA", "NO", "NU", "OG", "OT", "OR",
    "PD", "PA", "PR", "PV", "PG", "PU", "PE", "PC",
    "PI", "PT", "PN", "PZ", "PO", "RG", "RA", "RC",
    "RE", "RI", "RN", "RO", "RM", "SA", "SS", "SV",
    "SI", "SR", "SO", "TA", "TE", "TR", "TO", "OT",
    "TP", "TN", "TV", "TS", "UD", "VA", "VE", "VB",
    "VC", "VR", "VV", "VI", "VT",
]

_PROVINCE_SET = set(PROVINCE_ITALIANE)

# Regioni italiane
REGIONI_ITALIANE: List[str] = [
    "Abruzzo", "Basilicata", "Calabria", "Campania", "Emilia-Romagna",
    "Friuli-Venezia Giulia", "Lazio", "Liguria", "Lombardia", "Marche",
    "Molise", "Piemonte", "Puglia", "Sardegna", "Sicilia", "Toscana",
    "Trentino-Alto Adige", "Umbria", "Valle d'Aosta", "Veneto",
]


# ---------------------------------------------------------------------------
# Validatori statici
# ---------------------------------------------------------------------------

class FieldValidator:
    """
    Raccolta di metodi di validazione statici riutilizzabili.

    Ogni metodo riceve il valore grezzo (tipicamente stringa dal widget)
    e restituisce un ValidationResult.  Sul successo .value contiene il
    valore già convertito/normalizzato (es. int, date, str.strip()).
    """

    # --- Testo ---

    @staticmethod
    def required_text(value: str, field_name: str = "Campo",
                      max_len: int = 0) -> ValidationResult:
        """Testo non vuoto; opzionalmente controlla la lunghezza massima."""
        if not isinstance(value, str) or not value.strip():
            return ValidationResult.fail(f"{field_name} è obbligatorio.")
        stripped = value.strip()
        if max_len and len(stripped) > max_len:
            return ValidationResult.fail(
                f"{field_name} non può superare {max_len} caratteri "
                f"(inseriti {len(stripped)})."
            )
        return ValidationResult.ok(stripped)

    @staticmethod
    def optional_text(value: str, max_len: int = 0) -> ValidationResult:
        """Testo opzionale; restituisce None se vuoto."""
        if not isinstance(value, str) or not value.strip():
            return ValidationResult.ok(None)
        stripped = value.strip()
        if max_len and len(stripped) > max_len:
            return ValidationResult.fail(
                f"Il valore non può superare {max_len} caratteri."
            )
        return ValidationResult.ok(stripped)

    # --- Numeri ---

    @staticmethod
    def integer_positive(value: str, field_name: str = "Campo",
                         allow_zero: bool = False) -> ValidationResult:
        """Intero positivo (> 0 per default, >= 0 se allow_zero=True)."""
        if not isinstance(value, str) or not value.strip():
            return ValidationResult.fail(f"{field_name} è obbligatorio.")
        try:
            n = int(value.strip())
        except ValueError:
            return ValidationResult.fail(
                f"{field_name} deve essere un numero intero."
            )
        if not allow_zero and n <= 0:
            return ValidationResult.fail(
                f"{field_name} deve essere maggiore di zero."
            )
        if allow_zero and n < 0:
            return ValidationResult.fail(
                f"{field_name} non può essere negativo."
            )
        return ValidationResult.ok(n)

    @staticmethod
    def optional_integer(value: str, field_name: str = "Campo",
                         min_val: Optional[int] = None,
                         max_val: Optional[int] = None) -> ValidationResult:
        """Intero opzionale con range facoltativo."""
        if not isinstance(value, str) or not value.strip():
            return ValidationResult.ok(None)
        try:
            n = int(value.strip())
        except ValueError:
            return ValidationResult.fail(
                f"{field_name} deve essere un numero intero."
            )
        if min_val is not None and n < min_val:
            return ValidationResult.fail(
                f"{field_name} deve essere almeno {min_val}."
            )
        if max_val is not None and n > max_val:
            return ValidationResult.fail(
                f"{field_name} non può superare {max_val}."
            )
        return ValidationResult.ok(n)

    # --- Date ---

    @staticmethod
    def date_format(value: str, field_name: str = "Data",
                    fmt: str = "%Y-%m-%d") -> ValidationResult:
        """Data nel formato specificato (default YYYY-MM-DD)."""
        if not isinstance(value, str) or not value.strip():
            return ValidationResult.fail(f"{field_name} è obbligatoria.")
        try:
            d = datetime.strptime(value.strip(), fmt).date()
        except ValueError:
            display_fmt = fmt.replace("%Y", "AAAA").replace("%m", "MM").replace("%d", "GG")
            return ValidationResult.fail(
                f"{field_name} deve essere nel formato {display_fmt}."
            )
        return ValidationResult.ok(d)

    @staticmethod
    def optional_date(value: str, field_name: str = "Data",
                      fmt: str = "%Y-%m-%d") -> ValidationResult:
        """Data opzionale; restituisce None se vuoto."""
        if not isinstance(value, str) or not value.strip():
            return ValidationResult.ok(None)
        return FieldValidator.date_format(value, field_name, fmt)

    @staticmethod
    def date_range(start_value: str, end_value: str,
                   start_name: str = "Data inizio",
                   end_name: str = "Data fine",
                   fmt: str = "%Y-%m-%d") -> ValidationResult:
        """Verifica che end >= start per due date opzionali."""
        r_start = FieldValidator.optional_date(start_value, start_name, fmt)
        if not r_start.is_valid:
            return r_start
        r_end = FieldValidator.optional_date(end_value, end_name, fmt)
        if not r_end.is_valid:
            return r_end
        if r_start.value and r_end.value and r_end.value < r_start.value:
            return ValidationResult.fail(
                f"{end_name} non può precedere {start_name}."
            )
        return ValidationResult.ok((r_start.value, r_end.value))

    # --- Geografici ---

    @staticmethod
    def provincia_italiana(value: str) -> ValidationResult:
        """Sigla provincia italiana valida (case-insensitive)."""
        if not isinstance(value, str) or not value.strip():
            return ValidationResult.fail("La provincia è obbligatoria.")
        upper = value.strip().upper()
        if upper not in _PROVINCE_SET:
            return ValidationResult.fail(
                f"'{upper}' non è una sigla di provincia italiana valida."
            )
        return ValidationResult.ok(upper)

    @staticmethod
    def regione_italiana(value: str) -> ValidationResult:
        """Nome regione italiana valido (case-insensitive)."""
        if not isinstance(value, str) or not value.strip():
            return ValidationResult.fail("La regione è obbligatoria.")
        stripped = value.strip()
        match = next(
            (r for r in REGIONI_ITALIANE
             if r.lower() == stripped.lower()),
            None
        )
        if match is None:
            return ValidationResult.fail(
                f"'{stripped}' non è una regione italiana valida."
            )
        return ValidationResult.ok(match)

    # --- Codici catastali ---

    @staticmethod
    def codice_catastale(value: str) -> ValidationResult:
        """
        Codice catastale ISTAT: una lettera seguita da 3 cifre (es. A001).
        Restituisce None se vuoto (campo opzionale).
        """
        if not isinstance(value, str) or not value.strip():
            return ValidationResult.ok(None)
        upper = value.strip().upper()
        if not re.fullmatch(r"[A-Z]\d{3}", upper):
            return ValidationResult.fail(
                f"'{upper}' non è un codice catastale valido (es. A001)."
            )
        return ValidationResult.ok(upper)

    # --- Sicurezza / Utenti ---

    @staticmethod
    def password_strength(value: str) -> ValidationResult:
        """
        Policy password Foliarium:
        - minimo 10 caratteri
        - almeno 1 lettera minuscola
        - almeno 1 lettera maiuscola
        - almeno 1 cifra
        - non deve essere una password comune/banale
        """
        if not value:
            return ValidationResult.fail("La password è obbligatoria.")
        if len(value) < MIN_PASSWORD_LENGTH:
            return ValidationResult.fail(
                f"La password deve contenere almeno {MIN_PASSWORD_LENGTH} caratteri."
            )
        if not any(c.islower() for c in value):
            return ValidationResult.fail(
                "La password deve contenere almeno una lettera minuscola."
            )
        if not any(c.isupper() for c in value):
            return ValidationResult.fail(
                "La password deve contenere almeno una lettera maiuscola."
            )
        if not any(c.isdigit() for c in value):
            return ValidationResult.fail(
                "La password deve contenere almeno una cifra."
            )
        if value.lower() in COMMON_WEAK_PASSWORDS:
            return ValidationResult.fail(
                "La password è troppo comune: sceglierne una meno prevedibile."
            )
        return ValidationResult.ok(value)

    @staticmethod
    def username(value: str) -> ValidationResult:
        """Username: 3-64 caratteri alfanumerici, underscore, trattino."""
        if not isinstance(value, str) or not value.strip():
            return ValidationResult.fail("Il nome utente è obbligatorio.")
        stripped = value.strip()
        if len(stripped) < 3:
            return ValidationResult.fail(
                "Il nome utente deve contenere almeno 3 caratteri."
            )
        if len(stripped) > 64:
            return ValidationResult.fail(
                "Il nome utente non può superare 64 caratteri."
            )
        if not re.fullmatch(r"[\w\-]+", stripped):
            return ValidationResult.fail(
                "Il nome utente può contenere solo lettere, cifre, _ e -."
            )
        return ValidationResult.ok(stripped)

    @staticmethod
    def email(value: str) -> ValidationResult:
        """Indirizzo email in formato base (opzionale)."""
        if not isinstance(value, str) or not value.strip():
            return ValidationResult.ok(None)
        stripped = value.strip()
        if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", stripped):
            return ValidationResult.fail(
                f"'{stripped}' non è un indirizzo email valido."
            )
        return ValidationResult.ok(stripped)

    # --- Compositi ---

    @staticmethod
    def run_all(checks: List[ValidationResult]) -> ValidationResult:
        """
        Esegue una sequenza di ValidationResult già calcolati.
        Restituisce il primo errore, oppure ok con lista di valori.
        """
        values = []
        for r in checks:
            if not r.is_valid:
                return r
            values.append(r.value)
        return ValidationResult.ok(values)

    @staticmethod
    def validate_form(fields: dict) -> "FormValidationResult":
        """
        Valida un dizionario {nome_campo: ValidationResult}.
        Restituisce un FormValidationResult con errori per campo.
        """
        return FormValidationResult(fields)


# ---------------------------------------------------------------------------
# Risultato validazione form multi-campo
# ---------------------------------------------------------------------------

@dataclass
class FormValidationResult:
    """
    Raccoglie i risultati di più campi di un form.

    Utilizzo:
        result = FieldValidator.validate_form({
            "nome": FieldValidator.required_text(nome_edit.text(), "Nome"),
            "provincia": FieldValidator.provincia_italiana(prov_edit.text()),
        })
        if not result.is_valid:
            for field, msg in result.errors.items():
                set_field_error(widgets[field])
    """
    _results: dict = field(default_factory=dict)

    def __init__(self, results: dict):
        self._results = results

    @property
    def is_valid(self) -> bool:
        return all(r.is_valid for r in self._results.values())

    @property
    def errors(self) -> dict:
        """Dizionario {nome_campo: messaggio_errore} per i campi non validi."""
        return {
            name: r.error_message
            for name, r in self._results.items()
            if not r.is_valid
        }

    @property
    def values(self) -> dict:
        """Dizionario {nome_campo: valore_validato} per i campi validi."""
        return {
            name: r.value
            for name, r in self._results.items()
            if r.is_valid
        }

    def first_error(self) -> str:
        """Primo messaggio di errore, stringa vuota se tutto ok."""
        for r in self._results.values():
            if not r.is_valid:
                return r.error_message
        return ""
