"""
utils/error_handlers.py — Gestione errori centralizzata per Foliarium.

Fornisce:
  - Gerarchia eccezioni applicative (CatastoError e sottoclassi)
  - Decoratore @handle_db_errors per metodi del DB layer
  - Decoratore @handle_ui_errors per slot PyQt6 (mostra QMessageBox)
  - Funzione log_and_reraise per contesti specifici

Utilizzo decoratori:

    from utils.error_handlers import handle_db_errors, handle_ui_errors

    # Nel DB manager:
    @handle_db_errors("Inserimento comune")
    def aggiungi_comune(self, nome, ...):
        ...

    # Negli slot PyQt6:
    @handle_ui_errors("Salvataggio comune")
    def _on_salva_comune(self):
        ...
"""

from __future__ import annotations

import functools
import logging
from typing import Callable, Optional, Type

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Gerarchia eccezioni applicative
# ---------------------------------------------------------------------------

class CatastoError(Exception):
    """Eccezione base per tutti gli errori applicativi di Foliarium."""


class DatabaseError(CatastoError):
    """Errore generico del layer database."""


class AuthenticationError(CatastoError):
    """Credenziali non valide o sessione scaduta."""


class AuthorizationError(CatastoError):
    """Utente autenticato ma senza i permessi necessari."""


class ValidationError(CatastoError):
    """Dati di input non validi."""

    def __init__(self, message: str, field_name: str = ""):
        super().__init__(message)
        self.field_name = field_name


class NotFoundError(CatastoError):
    """Risorsa richiesta non trovata nel database."""


class DuplicateError(CatastoError):
    """Tentativo di creare una risorsa già esistente (constraint UNIQUE)."""

    def __init__(self, message: str, constraint: str = ""):
        super().__init__(message)
        self.constraint = constraint


class SessionError(CatastoError):
    """Errore relativo alla sessione utente."""


class ConfigError(CatastoError):
    """Errore di configurazione applicativa."""


# ---------------------------------------------------------------------------
# Decoratore per il DB layer
# ---------------------------------------------------------------------------

def handle_db_errors(
    operation_name: str = "Operazione DB",
    reraise_as: Type[Exception] = DatabaseError,
    log_level: int = logging.ERROR,
) -> Callable:
    """
    Decoratore per metodi del DB layer.

    - Logga eccezioni psycopg2 e generiche con contesto.
    - Rilancia come `reraise_as` (default: DatabaseError) se l'eccezione
      non è già una sottoclasse di CatastoError.
    - Le eccezioni CatastoError vengono rilanciate invariate (già tipizzate).

    Args:
        operation_name: Stringa descrittiva per il log (es. "Inserimento comune").
        reraise_as:     Tipo eccezione usato per il wrap (default DatabaseError).
        log_level:      Livello di log (default logging.ERROR).
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except CatastoError:
                # Eccezione già tipizzata — rilanciamo senza wrap
                raise
            except Exception as exc:
                _logger = _get_instance_logger(args) or logger
                _logger.log(
                    log_level,
                    "[%s] Errore non gestito in %s.%s: %s",
                    operation_name,
                    func.__qualname__,
                    func.__name__,
                    exc,
                    exc_info=True,
                )
                raise reraise_as(
                    f"{operation_name} fallito: {exc}"
                ) from exc
        return wrapper
    return decorator


# ---------------------------------------------------------------------------
# Decoratore per slot PyQt6
# ---------------------------------------------------------------------------

def handle_ui_errors(
    operation_name: str = "Operazione",
    show_dialog: bool = True,
    parent_attr: str = "",
) -> Callable:
    """
    Decoratore per slot/metodi PyQt6.

    - In caso di eccezione mostra un QMessageBox.critical (se show_dialog=True
      e PyQt6 disponibile).
    - Logga sempre l'errore.
    - Non rilanciata l'eccezione (gli slot non devono propagare eccezioni).

    Args:
        operation_name: Testo da mostrare nel titolo del dialog di errore.
        show_dialog:    Se True (default) mostra QMessageBox.
        parent_attr:    Nome attributo `self` da usare come parent widget.
                        Se vuoto usa None come parent.
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as exc:
                _logger = _get_instance_logger(args) or logger
                _logger.error(
                    "[UI] Errore in %s (%s): %s",
                    operation_name,
                    func.__qualname__,
                    exc,
                    exc_info=True,
                )
                if show_dialog:
                    _show_error_dialog(operation_name, exc, args, parent_attr)
                # Non ri-lanciamo: gli slot Qt non devono propagare
                return None
        return wrapper
    return decorator


# ---------------------------------------------------------------------------
# Funzione helper per contesti specifici
# ---------------------------------------------------------------------------

def log_and_reraise(
    exc: Exception,
    message: str,
    as_type: Type[Exception] = CatastoError,
    log: Optional[logging.Logger] = None,
) -> None:
    """
    Logga un'eccezione e la rilancia wrappata in `as_type`.

    Usato nei blocchi except quando si vuole aggiungere contesto:

        except psycopg2.OperationalError as e:
            log_and_reraise(e, "Connessione al DB fallita", DatabaseError)
    """
    _log = log or logger
    _log.error("%s: %s", message, exc, exc_info=True)
    raise as_type(f"{message}: {exc}") from exc


# ---------------------------------------------------------------------------
# Helpers interni
# ---------------------------------------------------------------------------

def _get_instance_logger(args: tuple) -> Optional[logging.Logger]:
    """Restituisce self.logger se il primo argomento è un'istanza con logger."""
    if args and hasattr(args[0], "logger") and isinstance(args[0].logger, logging.Logger):
        return args[0].logger
    return None


def _show_error_dialog(
    operation_name: str,
    exc: Exception,
    args: tuple,
    parent_attr: str,
) -> None:
    """Mostra QMessageBox.critical se PyQt6 disponibile."""
    try:
        from PyQt6.QtWidgets import QMessageBox
        parent = None
        if parent_attr and args and hasattr(args[0], parent_attr):
            parent = getattr(args[0], parent_attr)
        elif args and hasattr(args[0], "parent") and callable(args[0].parent):
            parent = args[0].parent()

        # Messaggio user-friendly in base al tipo eccezione
        if isinstance(exc, ValidationError):
            title = f"Dati non validi — {operation_name}"
        elif isinstance(exc, AuthenticationError):
            title = "Accesso negato"
        elif isinstance(exc, DuplicateError):
            title = f"Duplicato — {operation_name}"
        elif isinstance(exc, NotFoundError):
            title = f"Non trovato — {operation_name}"
        elif isinstance(exc, DatabaseError):
            title = f"Errore database — {operation_name}"
        else:
            title = f"Errore — {operation_name}"

        QMessageBox.critical(parent, title, str(exc))
    except ImportError:
        pass  # PyQt6 non disponibile (es. in test headless)
