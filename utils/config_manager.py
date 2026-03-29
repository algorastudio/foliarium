"""
utils/config_manager.py — Gestione configurazione tipizzata per Foliarium.

Fornisce dataclass immutabili per configurazione database e applicazione,
con costruzione da variabili d'ambiente, QSettings, o valori espliciti.

Utilizzo:
    from utils.config_manager import ConfigManager

    cfg = ConfigManager.from_env()
    db_cfg = cfg.database
    print(db_cfg.host, db_cfg.port, db_cfg.dbname)
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Optional


# ---------------------------------------------------------------------------
# DatabaseConfig
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class DatabaseConfig:
    """Parametri di connessione al database PostgreSQL."""

    dbname: str = "catasto_storico"
    user: str = "postgres"
    password: str = ""
    host: str = "localhost"
    port: int = 5432
    schema: str = "catasto"
    min_conn: int = 2
    max_conn: int = 20
    application_name: str = "Foliarium"

    def __post_init__(self) -> None:
        if not 1 <= self.port <= 65535:
            raise ValueError(f"Porta DB non valida: {self.port}")
        if self.min_conn < 1:
            raise ValueError("min_conn deve essere >= 1")
        if self.max_conn < self.min_conn:
            raise ValueError("max_conn deve essere >= min_conn")

    def as_psycopg2_kwargs(self) -> dict:
        """Dizionario pronto per psycopg2.connect(**kwargs)."""
        return {
            "dbname": self.dbname,
            "user": self.user,
            "password": self.password,
            "host": self.host,
            "port": self.port,
        }

    def safe_repr(self) -> str:
        """Rappresentazione senza password per logging."""
        return (
            f"postgresql://{self.user}@{self.host}:{self.port}"
            f"/{self.dbname} (schema={self.schema})"
        )

    @classmethod
    def from_env(cls) -> "DatabaseConfig":
        """Costruisce da variabili d'ambiente DB_HOST, DB_USER, ecc."""
        return cls(
            host=os.environ.get("DB_HOST", "localhost"),
            dbname=os.environ.get("DB_NAME", "catasto_storico"),
            user=os.environ.get("DB_USER", "postgres"),
            password=os.environ.get("DB_PASS", ""),
            port=int(os.environ.get("DB_PORT", "5432")),
            schema=os.environ.get("DB_SCHEMA", "catasto"),
        )

    @classmethod
    def from_qsettings(cls, settings) -> "DatabaseConfig":
        """
        Costruisce da QSettings.

        Args:
            settings: istanza QSettings già aperta.
        """
        # Importiamo qui per non rendere PyQt6 dipendenza obbligatoria
        from config import (
            SETTINGS_DB_HOST, SETTINGS_DB_PORT, SETTINGS_DB_NAME,
            SETTINGS_DB_USER, SETTINGS_DB_SCHEMA,
            ENV_DB_HOST, ENV_DB_NAME, ENV_DB_USER, ENV_DB_PORT,
        )
        return cls(
            host=settings.value(SETTINGS_DB_HOST, ENV_DB_HOST),
            port=int(settings.value(SETTINGS_DB_PORT, ENV_DB_PORT)),
            dbname=settings.value(SETTINGS_DB_NAME, ENV_DB_NAME),
            user=settings.value(SETTINGS_DB_USER, ENV_DB_USER),
            password="",  # Letta da keyring, non da QSettings
            schema=settings.value(SETTINGS_DB_SCHEMA, "catasto"),
        )

    def with_password(self, password: str) -> "DatabaseConfig":
        """Restituisce una nuova istanza con la password impostata."""
        return replace(self, password=password)


# ---------------------------------------------------------------------------
# AppConfig
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class AppConfig:
    """Configurazione generale dell'applicazione."""

    log_level: str = "INFO"
    log_file: Optional[str] = None
    export_directory: str = "./esportazioni"
    session_timeout_minutes: int = 15
    development_mode: bool = False
    cache_enabled: bool = True

    def __post_init__(self) -> None:
        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if self.log_level.upper() not in valid_levels:
            raise ValueError(f"log_level non valido: {self.log_level}")
        if self.session_timeout_minutes < 0:
            raise ValueError("session_timeout_minutes non può essere negativo")

    @classmethod
    def from_env(cls) -> "AppConfig":
        """Costruisce da variabili d'ambiente FOLIARIUM_*."""
        return cls(
            log_level=os.environ.get("FOLIARIUM_LOG_LEVEL", "INFO"),
            log_file=os.environ.get("FOLIARIUM_LOG_FILE"),
            export_directory=os.environ.get(
                "FOLIARIUM_EXPORT_DIR", "./esportazioni"
            ),
            development_mode=os.environ.get(
                "FOLIARIUM_DEV", "false"
            ).lower() == "true",
        )

    @property
    def export_path(self) -> Path:
        return Path(self.export_directory)


# ---------------------------------------------------------------------------
# EmailConfig
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class EmailConfig:
    """Configurazione SMTP per notifiche email."""

    enabled: bool = False
    host: str = ""
    port: int = 587
    user: str = ""
    use_tls: bool = True
    from_address: str = ""
    notify_on_create: bool = True
    notify_on_password: bool = True
    notify_on_role: bool = True
    notify_on_login: bool = False

    @property
    def is_configured(self) -> bool:
        return bool(self.enabled and self.host and self.user and self.from_address)

    @classmethod
    def from_qsettings(cls, settings) -> "EmailConfig":
        """Costruisce da QSettings (password letta separatamente da keyring)."""
        from config import (
            SETTINGS_SMTP_ENABLED, SETTINGS_SMTP_HOST, SETTINGS_SMTP_PORT,
            SETTINGS_SMTP_USER, SETTINGS_SMTP_USE_TLS, SETTINGS_SMTP_FROM_ADDR,
            SETTINGS_EMAIL_ON_CREATE, SETTINGS_EMAIL_ON_PASSWD,
            SETTINGS_EMAIL_ON_ROLE, SETTINGS_EMAIL_ON_LOGIN,
        )

        def _bool(key: str, default: bool) -> bool:
            val = settings.value(key, default)
            if isinstance(val, bool):
                return val
            return str(val).lower() in ("true", "1", "yes")

        return cls(
            enabled=_bool(SETTINGS_SMTP_ENABLED, False),
            host=settings.value(SETTINGS_SMTP_HOST, ""),
            port=int(settings.value(SETTINGS_SMTP_PORT, 587)),
            user=settings.value(SETTINGS_SMTP_USER, ""),
            use_tls=_bool(SETTINGS_SMTP_USE_TLS, True),
            from_address=settings.value(SETTINGS_SMTP_FROM_ADDR, ""),
            notify_on_create=_bool(SETTINGS_EMAIL_ON_CREATE, True),
            notify_on_password=_bool(SETTINGS_EMAIL_ON_PASSWD, True),
            notify_on_role=_bool(SETTINGS_EMAIL_ON_ROLE, True),
            notify_on_login=_bool(SETTINGS_EMAIL_ON_LOGIN, False),
        )


# ---------------------------------------------------------------------------
# ConfigManager
# ---------------------------------------------------------------------------

@dataclass
class ConfigManager:
    """
    Aggregatore di tutte le configurazioni dell'applicazione.

    Istanza singleton tipicamente creata all'avvio in gui_main.py.
    """

    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    app: AppConfig = field(default_factory=AppConfig)
    email: EmailConfig = field(default_factory=EmailConfig)

    @classmethod
    def from_env(cls) -> "ConfigManager":
        """Costruisce tutte le sezioni da variabili d'ambiente."""
        return cls(
            database=DatabaseConfig.from_env(),
            app=AppConfig.from_env(),
        )

    @classmethod
    def from_qsettings(cls, settings, db_password: str = "") -> "ConfigManager":
        """
        Costruisce da QSettings con password DB fornita esternamente (keyring).
        """
        db = DatabaseConfig.from_qsettings(settings).with_password(db_password)
        email = EmailConfig.from_qsettings(settings)
        return cls(database=db, email=email)

    def update_db_password(self, password: str) -> "ConfigManager":
        """
        Restituisce una nuova istanza con la password DB aggiornata.
        Utile dopo il recupero da keyring.
        """
        return ConfigManager(
            database=self.database.with_password(password),
            app=self.app,
            email=self.email,
        )
