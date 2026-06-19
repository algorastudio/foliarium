"""
tests/unit/test_api_route_scopes.py
===================================
Regression test del *wiring* degli scope sulle route reali (api/routes/*).

A differenza di ``test_api_auth_dual.py`` (che testa la dependency
``require_scope`` in isolamento), qui costruiamo l'app FastAPI reale via
``api.main.create_app`` e verifichiamo che ogni endpoint sia protetto dallo
scope corretto. Protegge dalla regressione in cui una route torni a usare
``get_current_session`` (che autentica ma NON verifica lo scope), permettendo
a una chiave read-only di eseguire scritture distruttive.
"""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest


pytestmark = pytest.mark.unit


def _api_key_info(scopes):
    """Shape ritornata da CatastoDBManager.validate_api_key per una chiave valida."""
    return {
        "id": 1, "name": "test-key", "prefix": "flr_test0001",
        "scopes": list(scopes),
        "created_by": None, "created_by_username": None,
        "created_by_ruolo": None, "rate_limit_per_min": 60,
    }


@pytest.fixture
def app_factory():
    """Costruisce l'app reale con un db_manager mockato e una chiave dagli scope dati."""
    from fastapi.testclient import TestClient
    from api.main import create_app
    import api.deps as deps
    import api.rate_limit as rl

    rl.reset()
    created = []

    def _factory(scopes):
        mock_db = MagicMock()
        mock_db.validate_api_key = MagicMock(return_value=_api_key_info(scopes))
        # Stub dei metodi invocati dagli handler protetti, così un 200 non
        # dipende dalla logica DB ma solo dal superamento del controllo scope.
        mock_db.search_partite = MagicMock(return_value=[])
        mock_db.create_partita = MagicMock(return_value=123)
        mock_db.delete_immobile = MagicMock(return_value=True)
        app = create_app(db_manager=mock_db)
        created.append(app)
        return TestClient(app), mock_db

    yield _factory

    import api.deps as deps
    deps._db_manager = None


def _hdr(key="flr_test"):
    return {"X-Foliarium-Api-Key": key}


# ─────────────────────────────────────────────────────────────────────
# Una chiave READ-ONLY non può scrivere (il finding originale)
# ─────────────────────────────────────────────────────────────────────

class TestReadOnlyKeyCannotWrite:

    def test_read_key_can_get_partite(self, app_factory):
        client, _ = app_factory(["read:partite"])
        r = client.get("/api/v1/partite", headers=_hdr())
        assert r.status_code == 200

    def test_read_key_cannot_create_partita(self, app_factory):
        client, mock_db = app_factory(["read:partite"])
        r = client.post(
            "/api/v1/partite",
            headers=_hdr(),
            json={"comune_id": 1, "numero_partita": 99},
        )
        assert r.status_code == 403
        assert "write:partite" in r.json()["detail"]
        # L'handler non deve essere stato raggiunto.
        mock_db.create_partita.assert_not_called()

    def test_read_key_cannot_delete_immobile(self, app_factory):
        """La cancellazione distruttiva è il rischio principale del finding."""
        client, mock_db = app_factory(["read:partite"])
        r = client.delete("/api/v1/partite/1/immobili/1", headers=_hdr())
        assert r.status_code == 403
        mock_db.delete_immobile.assert_not_called()


# ─────────────────────────────────────────────────────────────────────
# Gli scope corretti continuano a funzionare
# ─────────────────────────────────────────────────────────────────────

class TestCorrectScopePasses:

    def test_write_key_can_create_partita(self, app_factory):
        client, mock_db = app_factory(["write:partite"])
        r = client.post(
            "/api/v1/partite",
            headers=_hdr(),
            json={"comune_id": 1, "numero_partita": 99},
        )
        assert r.status_code == 201
        assert r.json() == {"id": 123}
        mock_db.create_partita.assert_called_once()

    def test_wildcard_key_can_do_everything(self, app_factory):
        client, _ = app_factory(["*:*"])
        assert client.get("/api/v1/partite", headers=_hdr()).status_code == 200
        r = client.post(
            "/api/v1/partite",
            headers=_hdr(),
            json={"comune_id": 1, "numero_partita": 99},
        )
        assert r.status_code == 201

    def test_read_wildcard_does_not_grant_write(self, app_factory):
        """`read:*` copre tutte le letture ma NON le scritture."""
        client, _ = app_factory(["read:*"])
        assert client.get("/api/v1/partite", headers=_hdr()).status_code == 200
        r = client.post(
            "/api/v1/partite",
            headers=_hdr(),
            json={"comune_id": 1, "numero_partita": 99},
        )
        assert r.status_code == 403


# ─────────────────────────────────────────────────────────────────────
# Mappa scope→route: ogni endpoint dichiara lo scope atteso
# ─────────────────────────────────────────────────────────────────────

class TestScopeIsolationAcrossResources:

    def test_read_partite_does_not_grant_read_audit(self, app_factory):
        client, _ = app_factory(["read:partite"])
        r = client.get("/api/v1/audit", headers=_hdr())
        assert r.status_code == 403
        assert "read:audit" in r.json()["detail"]

    def test_read_audit_key_can_read_audit(self, app_factory):
        client, mock_db = app_factory(["read:audit"])
        mock_db.get_audit_logs = MagicMock(return_value=([], 0))
        r = client.get("/api/v1/audit", headers=_hdr())
        assert r.status_code == 200
