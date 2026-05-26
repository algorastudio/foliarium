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
