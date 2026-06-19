"""
tests/unit/test_db_sslmode.py
=============================
Test della risoluzione del ``sslmode`` per la connessione PostgreSQL
(``DBConnectionBase._resolve_sslmode``). Garantisce che gli host remoti
richiedano TLS per default, senza rompere i flussi locali/demo.
"""
from __future__ import annotations

import pytest


pytestmark = pytest.mark.unit


# config importa PyQt6 (QStandardPaths); in alcuni ambienti headless puro può
# non essere disponibile. _resolve_sslmode è progettato per tollerarlo (cattura
# l'errore di import e ricade sul default per-host), quindi i test del default
# e del valore esplicito funzionano comunque. I test dell'override da config
# vengono saltati se config non è importabile.
try:
    import config as _config_mod
    _CONFIG_AVAILABLE = True
except Exception:
    _config_mod = None
    _CONFIG_AVAILABLE = False


@pytest.fixture(autouse=True)
def _no_config_override(monkeypatch):
    """Neutralizza un eventuale override da config.ENV_DB_SSLMODE dell'ambiente."""
    if _CONFIG_AVAILABLE:
        monkeypatch.setattr(_config_mod, "ENV_DB_SSLMODE", "", raising=False)
    yield


def _resolve(sslmode, host):
    from db.base import DBConnectionBase
    return DBConnectionBase._resolve_sslmode(sslmode, host)


class TestDefaultByHost:

    @pytest.mark.parametrize("host", ["", "localhost", "127.0.0.1", "::1", "LOCALHOST"])
    def test_local_hosts_default_prefer(self, host):
        assert _resolve(None, host) == "prefer"

    @pytest.mark.parametrize("host", [
        "db.archivio.example", "10.0.0.5", "192.168.1.20", "postgres.internal",
    ])
    def test_remote_hosts_default_require(self, host):
        assert _resolve(None, host) == "require"


class TestExplicitWins:

    def test_explicit_value_overrides_host_default(self):
        # Anche su host remoto, un valore esplicito ha la precedenza.
        assert _resolve("verify-full", "db.remote.example") == "verify-full"
        # E su host locale può forzare disable.
        assert _resolve("disable", "localhost") == "disable"


@pytest.mark.skipif(not _CONFIG_AVAILABLE, reason="config (PyQt6) non importabile in questo ambiente")
class TestConfigOverride:

    def test_config_override_used_when_no_explicit(self, monkeypatch):
        monkeypatch.setattr(_config_mod, "ENV_DB_SSLMODE", "verify-ca", raising=False)
        # host locale: senza override sarebbe 'prefer', ma l'override vince.
        assert _resolve(None, "localhost") == "verify-ca"

    def test_explicit_beats_config_override(self, monkeypatch):
        monkeypatch.setattr(_config_mod, "ENV_DB_SSLMODE", "verify-ca", raising=False)
        assert _resolve("require", "localhost") == "require"


class TestStoredInConnParams:

    def test_init_stores_sslmode_in_conn_params(self):
        from db.base import DBConnectionBase
        mgr = DBConnectionBase(
            dbname="d", user="u", password="p", host="db.remote.example", port="5432",
        )
        assert mgr._main_db_conn_params["sslmode"] == "require"

    def test_local_host_keeps_prefer(self):
        from db.base import DBConnectionBase
        mgr = DBConnectionBase(
            dbname="d", user="u", password="p", host="127.0.0.1", port="5432",
        )
        assert mgr._main_db_conn_params["sslmode"] == "prefer"
