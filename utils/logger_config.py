"""
utils/logger_config.py — Configurazione logging uniforme per Foliarium.

Permette di ottenere logger con configurazione consistente in qualsiasi
modulo senza dipendere da config.py (che importa PyQt6).

Utilizzo:
    from utils.logger_config import get_logger

    logger = get_logger(__name__)
    logger.info("Modulo inizializzato")

Per configurare logging all'avvio dell'applicazione:
    from utils.logger_config import configure_logging
    configure_logging(level="INFO", log_file="/path/to/app.log")
"""

from __future__ import annotations

import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional, Union


# ---------------------------------------------------------------------------
# Formato log
# ---------------------------------------------------------------------------

_DEFAULT_FORMAT = (
    "%(asctime)s | %(levelname)-8s | %(name)-30s | %(message)s"
)
_SHORT_FORMAT = "%(levelname)-8s | %(name)s | %(message)s"

_ROOT_LOGGER_NAME = "foliarium"
_configured = False


# ---------------------------------------------------------------------------
# API pubblica
# ---------------------------------------------------------------------------

def get_logger(name: str) -> logging.Logger:
    """
    Restituisce un logger gerarchicamente sotto 'foliarium'.

    Se `name` è già prefissato con 'foliarium.' viene usato direttamente.
    Altrimenti viene prefissato automaticamente per mantenere la gerarchia.
    """
    if not name.startswith(_ROOT_LOGGER_NAME):
        full_name = f"{_ROOT_LOGGER_NAME}.{name}"
    else:
        full_name = name
    return logging.getLogger(full_name)


def configure_logging(
    level: Union[str, int] = "INFO",
    log_file: Optional[Union[str, Path]] = None,
    max_bytes: int = 5 * 1024 * 1024,   # 5 MB
    backup_count: int = 5,
    console: bool = True,
    fmt: str = _DEFAULT_FORMAT,
) -> None:
    """
    Configura il logger radice 'foliarium'.

    Da chiamare una sola volta all'avvio dell'applicazione.
    Chiamate successive aggiungono ulteriori handler solo se non già
    configurati (idempotente).

    Args:
        level:        Livello di log (stringa o costante logging.*).
        log_file:     Percorso file di log. Se None non viene creato file.
        max_bytes:    Dimensione massima prima di ruotare il file.
        backup_count: Numero di backup da conservare.
        console:      Se True aggiunge StreamHandler su stderr.
        fmt:          Formato dei messaggi.
    """
    global _configured

    root_logger = logging.getLogger(_ROOT_LOGGER_NAME)

    # Risolvi livello
    if isinstance(level, str):
        numeric_level = getattr(logging, level.upper(), logging.INFO)
    else:
        numeric_level = level

    root_logger.setLevel(numeric_level)

    # Evita doppia configurazione
    if _configured:
        return

    formatter = logging.Formatter(fmt, datefmt="%Y-%m-%d %H:%M:%S")

    # --- Console handler ---
    if console and not _has_handler(root_logger, logging.StreamHandler):
        ch = logging.StreamHandler()
        ch.setLevel(numeric_level)
        ch.setFormatter(formatter)
        root_logger.addHandler(ch)

    # --- File handler ---
    if log_file and not _has_handler(root_logger, RotatingFileHandler):
        log_path = Path(log_file)
        try:
            log_path.parent.mkdir(parents=True, exist_ok=True)
            fh = RotatingFileHandler(
                log_path,
                maxBytes=max_bytes,
                backupCount=backup_count,
                encoding="utf-8",
            )
            fh.setLevel(numeric_level)
            fh.setFormatter(formatter)
            root_logger.addHandler(fh)
        except OSError as e:
            root_logger.warning("Impossibile aprire file di log '%s': %s", log_file, e)

    _configured = True


def configure_logging_from_env() -> None:
    """
    Configura logging leggendo variabili d'ambiente:
      FOLIARIUM_LOG_LEVEL  (default: INFO)
      FOLIARIUM_LOG_FILE   (default: nessun file)
    """
    level = os.environ.get("FOLIARIUM_LOG_LEVEL", "INFO")
    log_file = os.environ.get("FOLIARIUM_LOG_FILE", None)
    configure_logging(level=level, log_file=log_file)


def reset_logging() -> None:
    """
    Rimuove tutti gli handler dal root logger 'foliarium'.
    Utile nei test per evitare contaminazione tra test suite.
    """
    global _configured
    root_logger = logging.getLogger(_ROOT_LOGGER_NAME)
    for handler in list(root_logger.handlers):
        handler.close()
        root_logger.removeHandler(handler)
    _configured = False


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _has_handler(logger_: logging.Logger, handler_type: type) -> bool:
    """Controlla se il logger ha già un handler del tipo specificato."""
    return any(isinstance(h, handler_type) for h in logger_.handlers)
