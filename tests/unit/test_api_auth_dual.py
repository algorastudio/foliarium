"""
tests/unit/test_api_auth_dual.py
================================
Test del dual-auth FastAPI (api/deps.py): sessione bearer + API key header.
Verifica anche il matching scope con wildcard.
"""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest


pytestmark = pytest.mark.unit


@pytest.fixture
def client_factory():
    """Crea un TestClient con un mock db_manager iniettato in api.deps."""
    from fastapi import FastAPI, Depends
    from fastapi.testclient import TestClient
    import api.deps as deps

    def _factory(validate_return=None, route_dep=None):
        mock_db = MagicMock()
        mock_db.validate_api_key = MagicMock(return_value=validate_return)
        deps._db_manager = mock_db

        app = FastAPI()
        dep = route_dep or deps.get_current_session

        @app.get("/protected")
        def protected(s=Depends(dep)):
            return s

        return TestClient(app), mock_db

    yield _factory

    # Cleanup singleton
    import api.deps as deps
    deps._db_manager = None


# ─────────────────────────────────────────────────────────────────────
# get_current_session
# ─────────────────────────────────────────────────────────────────────

class TestGetCurrentSession:

    def test_no_credentials_returns_401(self, client_factory):
        client, _ = client_factory()
        r = client.get("/protected")
        assert r.status_code == 401
        assert "Credenziali mancanti" in r.json()["detail"]

    def test_invalid_api_key_returns_401(self, client_factory):
        client, _ = client_factory(validate_return=None)
        r = client.get("/protected", headers={"X-Foliarium-Api-Key": "flr_invalid"})
        assert r.status_code == 401
        assert "Chiave API" in r.json()["detail"]

    def test_valid_api_key_returns_principal(self, client_factory):
        client, _ = client_factory(validate_return={
            "id": 42, "name": "mcp", "prefix": "flr_abcd1234",
            "scopes": ["read:partite"],
            "created_by": 1, "created_by_username": "admin",
            "created_by_ruolo": "admin", "rate_limit_per_min": 60,
        })
        r = client.get("/protected", headers={"X-Foliarium-Api-Key": "flr_xxx"})
        assert r.status_code == 200
        body = r.json()
        assert body["auth_method"] == "api_key"
        assert body["api_key_id"] == 42
        assert body["api_key_name"] == "mcp"
        assert body["scopes"] == ["read:partite"]
        assert body["username"] == "admin"

    def test_api_key_without_user_uses_prefix_as_username(self, client_factory):
        client, _ = client_factory(validate_return={
            "id": 5, "name": "headless", "prefix": "flr_zzzz9999",
            "scopes": [],
            "created_by": None, "created_by_username": None,
            "created_by_ruolo": None, "rate_limit_per_min": 60,
        })
        r = client.get("/protected", headers={"X-Foliarium-Api-Key": "flr_xxx"})
        assert r.status_code == 200
        body = r.json()
        assert body["username"] == "api-key:flr_zzzz9999"
        assert body["ruolo"] == "api"

    def test_invalid_bearer_token_returns_401(self, client_factory):
        client, _ = client_factory()
        r = client.get("/protected",
                       headers={"Authorization": "Bearer invalid-token"})
        assert r.status_code == 401
        assert "Sessione" in r.json()["detail"]

    def test_valid_bearer_session_returns_wildcard_scope(self, client_factory):
        from api.auth import create_session
        tok = create_session(7, "marco", "admin")

        client, _ = client_factory()
        r = client.get("/protected", headers={"Authorization": f"Bearer {tok}"})
        assert r.status_code == 200
        body = r.json()
        assert body["auth_method"] == "session"
        assert body["scopes"] == ["*:*"]
        assert body["username"] == "marco"

    def test_api_key_takes_precedence_over_bearer(self, client_factory):
        """Se entrambi gli header sono presenti, viene usato l'API key."""
        client, _ = client_factory(validate_return={
            "id": 1, "name": "k", "prefix": "flr_aaaa1111",
            "scopes": ["read:audit"],
            "created_by": None, "created_by_username": None,
            "created_by_ruolo": None, "rate_limit_per_min": 60,
        })
        from api.auth import create_session
        tok = create_session(99, "human", "guest")
        r = client.get("/protected", headers={
            "X-Foliarium-Api-Key": "flr_xxx",
            "Authorization": f"Bearer {tok}",
        })
        assert r.status_code == 200
        assert r.json()["auth_method"] == "api_key"


# ─────────────────────────────────────────────────────────────────────
# Database non disponibile: 503, non 401
# ─────────────────────────────────────────────────────────────────────

_CHIAVE = "flr_" + "a" * 32


class TestApiKeyDatabaseNonDisponibile:
    """Con il database irraggiungibile la chiave non è "non valida".

    Un 401 farebbe dire al client MCP «Genera una nuova chiave», consiglio
    sbagliato: la chiave è valida, è il database che non risponde.
    """

    def test_errore_db_risponde_503(self, client_factory):
        from catasto_exceptions import DBMError
        client, mock_db = client_factory()
        mock_db.validate_api_key.side_effect = DBMError("connessione rifiutata")
        r = client.get("/protected", headers={"X-Foliarium-Api-Key": _CHIAVE})
        assert r.status_code == 503
        assert r.json()["detail"] == "Database non disponibile"

    def test_errore_db_non_consuma_il_rate_limit(self, client_factory):
        from unittest.mock import patch
        from catasto_exceptions import DBMError
        client, mock_db = client_factory()
        mock_db.validate_api_key.side_effect = DBMError("connessione rifiutata")
        with patch("api.deps.check_and_increment") as rate:
            client.get("/protected", headers={"X-Foliarium-Api-Key": _CHIAVE})
        rate.assert_not_called()

    def test_manager_assente_risponde_503(self, client_factory):
        """L'API è partita senza database: nessuna chiave si può verificare."""
        import api.deps as deps
        client, _ = client_factory()
        deps._db_manager = None
        r = client.get("/protected", headers={"X-Foliarium-Api-Key": _CHIAVE})
        assert r.status_code == 503
        assert r.json()["detail"] == "Database non disponibile"


class TestApiKeyCatenaReale:
    """Mixin DB reale dietro la dipendenza FastAPI reale.

    Protegge il contratto fra i due strati: ciò che ``validate_api_key``
    solleva è ciò che ``get_current_session`` intercetta.
    """

    @pytest.fixture
    def manager(self):
        import logging
        from catasto_db_manager import CatastoDBManager
        m = CatastoDBManager.__new__(CatastoDBManager)
        m.pool = None
        m.schema = "catasto"
        m.logger = logging.getLogger("test_api_auth_dual")
        m._pool_metrics = {
            "total_getconn": 0, "total_putconn": 0, "connection_errors": 0,
            "peak_active": 0, "last_error_time": None,
        }
        return m

    @pytest.fixture
    def client(self, manager):
        from fastapi import FastAPI, Depends
        from fastapi.testclient import TestClient
        import api.deps as deps

        deps._db_manager = manager
        app = FastAPI()

        @app.get("/protected")
        def protected(s=Depends(deps.get_current_session)):
            return s

        yield TestClient(app)
        deps._db_manager = None

    @staticmethod
    def _connessione_con_riga(riga):
        cur = MagicMock()
        cur.fetchone.return_value = riga
        cur_cm = MagicMock()
        cur_cm.__enter__ = MagicMock(return_value=cur)
        cur_cm.__exit__ = MagicMock(return_value=False)
        conn = MagicMock()
        conn.cursor.return_value = cur_cm
        conn_cm = MagicMock()
        conn_cm.__enter__ = MagicMock(return_value=conn)
        conn_cm.__exit__ = MagicMock(return_value=False)
        return conn_cm

    def test_pool_non_inizializzato_risponde_503(self, client):
        r = client.get("/protected", headers={"X-Foliarium-Api-Key": _CHIAVE})
        assert r.status_code == 503
        assert r.json()["detail"] == "Database non disponibile"

    def test_connessione_persa_a_meta_risponde_503(self, client, manager):
        """Prima richiesta dopo la caduta del server: il pool esiste ancora,
        la sua connessione no. Rispondeva 500 invece di 503."""
        import psycopg2
        conn_cm = self._connessione_con_riga(None)
        conn = conn_cm.__enter__.return_value
        cur = conn.cursor.return_value.__enter__.return_value
        cur.execute.side_effect = psycopg2.OperationalError(
            "SSL connection has been closed unexpectedly"
        )
        conn.rollback.side_effect = psycopg2.InterfaceError(
            "connection already closed"
        )
        pool = MagicMock()
        pool.getconn.return_value = conn
        manager.pool = pool
        manager.application_name = "test"
        r = client.get("/protected", headers={"X-Foliarium-Api-Key": _CHIAVE})
        assert r.status_code == 503
        assert r.json()["detail"] == "Database non disponibile"

    @pytest.mark.parametrize("revocata,scaduta", [
        (False, False),  # riga assente: chiave inesistente
        (True, False),
        (False, True),
    ], ids=["inesistente", "revocata", "scaduta"])
    def test_chiave_non_valida_resta_401(self, client, manager,
                                         revocata, scaduta):
        from datetime import datetime, timedelta, timezone
        from unittest.mock import patch

        adesso = datetime.now(timezone.utc)
        riga = None
        if revocata or scaduta:
            riga = {
                "id": 1, "name": "k", "prefix": "flr_aaaaaaaa",
                "scopes": ["read:*"], "created_by": None,
                "created_by_username": None, "created_by_ruolo": None,
                "expires_at": adesso - timedelta(days=1) if scaduta else None,
                "revoked_at": adesso if revocata else None,
                "rate_limit_per_min": 60,
            }
        with patch.object(manager, "_get_connection",
                          return_value=self._connessione_con_riga(riga)):
            r = client.get("/protected",
                           headers={"X-Foliarium-Api-Key": _CHIAVE})
        assert r.status_code == 401
        assert "Chiave API" in r.json()["detail"]


# ─────────────────────────────────────────────────────────────────────
# require_scope (factory)
# ─────────────────────────────────────────────────────────────────────

class TestRequireScope:

    def test_session_has_wildcard_scope(self, client_factory):
        import api.deps as deps
        from api.auth import create_session
        tok = create_session(1, "u", "admin")

        client, _ = client_factory(route_dep=deps.require_scope("any:scope"))
        r = client.get("/protected", headers={"Authorization": f"Bearer {tok}"})
        assert r.status_code == 200

    def test_api_key_with_exact_scope_passes(self, client_factory):
        import api.deps as deps
        client, _ = client_factory(
            validate_return={
                "id": 1, "name": "k", "prefix": "flr_a",
                "scopes": ["read:partite"],
                "created_by": None, "created_by_username": None,
                "created_by_ruolo": None, "rate_limit_per_min": 60,
            },
            route_dep=deps.require_scope("read:partite"),
        )
        r = client.get("/protected", headers={"X-Foliarium-Api-Key": "flr_x"})
        assert r.status_code == 200

    def test_api_key_without_scope_returns_403(self, client_factory):
        import api.deps as deps
        client, _ = client_factory(
            validate_return={
                "id": 1, "name": "k", "prefix": "flr_a",
                "scopes": ["read:audit"],
                "created_by": None, "created_by_username": None,
                "created_by_ruolo": None, "rate_limit_per_min": 60,
            },
            route_dep=deps.require_scope("write:partite"),
        )
        r = client.get("/protected", headers={"X-Foliarium-Api-Key": "flr_x"})
        assert r.status_code == 403
        assert "write:partite" in r.json()["detail"]

    def test_wildcard_action_scope(self, client_factory):
        """`read:*` deve coprire `read:partite`, `read:audit`, ecc."""
        import api.deps as deps
        client, _ = client_factory(
            validate_return={
                "id": 1, "name": "k", "prefix": "flr_a",
                "scopes": ["read:*"],
                "created_by": None, "created_by_username": None,
                "created_by_ruolo": None, "rate_limit_per_min": 60,
            },
            route_dep=deps.require_scope("read:partite"),
        )
        r = client.get("/protected", headers={"X-Foliarium-Api-Key": "flr_x"})
        assert r.status_code == 200


# ─────────────────────────────────────────────────────────────────────
# _scope_matches (puro)
# ─────────────────────────────────────────────────────────────────────

class TestScopeMatches:

    @pytest.mark.parametrize("granted,required,expected", [
        # match esatto
        ("read:partite", "read:partite", True),
        # wildcard universale
        ("*:*", "anything:here", True),
        # wildcard sull'azione
        ("read:*", "read:partite", True),
        ("read:*", "write:partite", False),
        # wildcard sulla risorsa
        ("*:partite", "read:partite", True),
        ("*:partite", "read:audit", False),
        # mismatch
        ("read:audit", "write:audit", False),
        ("read:partite", "read:audit", False),
        # scope malformato
        ("nopcol", "read:partite", False),
        ("read:partite", "nopcol", False),
    ])
    def test_matches(self, granted, required, expected):
        from api.deps import _scope_matches
        assert _scope_matches(granted, required) is expected
