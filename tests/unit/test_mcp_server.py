"""
tests/unit/test_mcp_server.py
=============================
Test unitari per ``mcp_server/`` (client HTTP + server FastMCP).

Copre:
* FoliariumApiClient: header auth, query params puliti, gestione status
  401/403/404/5xx, parsing JSON / fallback testo.
* build_server: registrazione tool, signature visibili nel manifest MCP.
* Dispatch tool: chiamata al client con i giusti argomenti, formattazione
  output come JSON pretty-printed.
"""

from __future__ import annotations

import asyncio
import json
from unittest.mock import MagicMock, patch

import httpx
import pytest


pytestmark = pytest.mark.unit


# ─────────────────────────────────────────────────────────────────────
# FoliariumApiClient
# ─────────────────────────────────────────────────────────────────────

class TestClientConstruction:

    def test_missing_base_url_raises(self):
        from mcp_server.client import FoliariumApiClient
        with pytest.raises(ValueError, match="FOLIARIUM_API_BASE_URL"):
            FoliariumApiClient(base_url="", api_key="flr_x")

    def test_missing_api_key_raises(self):
        from mcp_server.client import FoliariumApiClient
        with pytest.raises(ValueError, match="FOLIARIUM_API_KEY"):
            FoliariumApiClient(base_url="http://localhost:8765", api_key="")

    def test_from_env_reads_env_vars(self, monkeypatch):
        from mcp_server.client import FoliariumApiClient
        monkeypatch.setenv("FOLIARIUM_API_BASE_URL", "http://x:1")
        monkeypatch.setenv("FOLIARIUM_API_KEY", "flr_abc")
        c = FoliariumApiClient.from_env()
        assert c.base_url == "http://x:1"
        assert c.api_key == "flr_abc"

    def test_base_url_trailing_slash_stripped(self):
        from mcp_server.client import FoliariumApiClient
        c = FoliariumApiClient(base_url="http://x:1///", api_key="flr_a")
        assert c.base_url == "http://x:1"


class TestClientErrorMapping:

    @pytest.fixture
    def client(self):
        from mcp_server.client import FoliariumApiClient
        return FoliariumApiClient(base_url="http://x:1", api_key="flr_a")

    def _resp(self, status: int, body=None, text: str = ""):
        """Costruisce una httpx.Response sintetica."""
        import json as _json
        if body is not None:
            content = _json.dumps(body).encode("utf-8")
            headers = {"content-type": "application/json"}
        else:
            content = text.encode("utf-8")
            headers = {"content-type": "text/plain"}
        return httpx.Response(status_code=status, content=content, headers=headers)

    def test_401_raises_with_helpful_message(self, client):
        from mcp_server.client import FoliariumApiError
        with patch.object(client._client, "get", return_value=self._resp(401, {"detail": "x"})):
            with pytest.raises(FoliariumApiError) as ei:
                client._get("/api/v1/comuni")
            assert ei.value.status == 401
            assert "Chiave API" in str(ei.value)
            assert "Gestione Chiavi API" in str(ei.value)

    def test_403_includes_detail(self, client):
        from mcp_server.client import FoliariumApiError
        with patch.object(client._client, "get",
                          return_value=self._resp(403, {"detail": "scope mancante"})):
            with pytest.raises(FoliariumApiError) as ei:
                client._get("/api/v1/partite")
            assert ei.value.status == 403
            assert "scope mancante" in str(ei.value)

    def test_404_raises(self, client):
        from mcp_server.client import FoliariumApiError
        with patch.object(client._client, "get",
                          return_value=self._resp(404)):
            with pytest.raises(FoliariumApiError) as ei:
                client._get("/api/v1/partite/9999")
            assert ei.value.status == 404

    def test_500_includes_log_hint(self, client):
        from mcp_server.client import FoliariumApiError
        with patch.object(client._client, "get",
                          return_value=self._resp(500)):
            with pytest.raises(FoliariumApiError) as ei:
                client._get("/api/v1/comuni")
            assert "Esporta log" in str(ei.value)

    def test_network_error_raises(self, client):
        from mcp_server.client import FoliariumApiError
        with patch.object(client._client, "get",
                          side_effect=httpx.ConnectError("connection refused")):
            with pytest.raises(FoliariumApiError) as ei:
                client._get("/api/v1/comuni")
            assert "Impossibile contattare" in str(ei.value)

    def test_200_returns_parsed_json(self, client):
        with patch.object(client._client, "get",
                          return_value=self._resp(200, [{"id": 1}])):
            result = client._get("/api/v1/comuni")
            assert result == [{"id": 1}]

    def test_200_non_json_returns_text(self, client):
        with patch.object(client._client, "get",
                          return_value=self._resp(200, text="hello")):
            result = client._get("/api/v1/comuni")
            assert result == "hello"


class TestClientEndpoints:
    """Verifica che ogni metodo wrapper colpisca il path giusto."""

    @pytest.fixture
    def client(self):
        from mcp_server.client import FoliariumApiClient
        return FoliariumApiClient(base_url="http://x:1", api_key="flr_a")

    def _ok(self, body):
        return httpx.Response(
            status_code=200,
            content=json.dumps(body).encode("utf-8"),
            headers={"content-type": "application/json"},
        )

    def test_list_comuni_path(self, client):
        with patch.object(client._client, "get", return_value=self._ok([])) as m:
            client.list_comuni()
            assert m.call_args.args[0] == "/api/v1/comuni"

    def test_list_localita_path_with_id(self, client):
        with patch.object(client._client, "get", return_value=self._ok([])) as m:
            client.list_localita(7)
            assert m.call_args.args[0] == "/api/v1/comuni/7/localita"

    def test_search_partite_drops_none_params(self, client):
        with patch.object(client._client, "get", return_value=self._ok([])) as m:
            client.search_partite(comune_id=1, possessore="rossi",
                                  numero_partita=None)
            kwargs = m.call_args.kwargs
            assert kwargs["params"] == {"comune_id": 1, "possessore": "rossi"}

    def test_get_partita_path(self, client):
        with patch.object(client._client, "get", return_value=self._ok({})) as m:
            client.get_partita(42)
            assert m.call_args.args[0] == "/api/v1/partite/42"

    def test_search_possessori_passes_query(self, client):
        with patch.object(client._client, "get", return_value=self._ok([])) as m:
            client.search_possessori("rossi")
            assert m.call_args.kwargs["params"] == {"q": "rossi"}

    def test_get_possessore_path(self, client):
        with patch.object(client._client, "get", return_value=self._ok({})) as m:
            client.get_possessore(99)
            assert m.call_args.args[0] == "/api/v1/possessori/99"

    def test_get_genealogia_path(self, client):
        with patch.object(client._client, "get", return_value=self._ok({})) as m:
            client.get_genealogia(5)
            assert m.call_args.args[0] == "/api/v1/genealogia/5"

    def test_get_timeline_partita_path(self, client):
        with patch.object(client._client, "get", return_value=self._ok([])) as m:
            client.get_timeline_partita(5)
            assert m.call_args.args[0] == "/api/v1/timeline/partita/5"

    def test_search_immobili_drops_none(self, client):
        with patch.object(client._client, "get", return_value=self._ok([])) as m:
            client.search_immobili(partita_id=3, comune_id=None)
            assert m.call_args.args[0] == "/api/v1/immobili"
            assert m.call_args.kwargs["params"] == {"partita_id": 3}

    def test_dashboard_stats_path(self, client):
        with patch.object(client._client, "get", return_value=self._ok({})) as m:
            client.get_dashboard_stats()
            assert m.call_args.args[0] == "/api/v1/dashboard/stats"

    def test_dashboard_analytics_path(self, client):
        with patch.object(client._client, "get", return_value=self._ok({})) as m:
            client.get_dashboard_analytics()
            assert m.call_args.args[0] == "/api/v1/dashboard/analytics"

    def test_list_audit_path_and_params(self, client):
        with patch.object(client._client, "get", return_value=self._ok({})) as m:
            client.list_audit(table_name="partita", operation="U")
            assert m.call_args.args[0] == "/api/v1/audit"
            params = m.call_args.kwargs["params"]
            assert params["table_name"] == "partita"
            assert params["operation"] == "U"

    def test_audit_summary_path(self, client):
        with patch.object(client._client, "get", return_value=self._ok({})) as m:
            client.get_audit_summary()
            assert m.call_args.args[0] == "/api/v1/audit/summary"

    def test_auth_header_present(self, client):
        # Verifica che il client httpx abbia l'header configurato
        assert client._client.headers["X-Foliarium-Api-Key"] == "flr_a"


class TestClientWriteEndpoints:
    """Verifica metodo HTTP, path e body dei wrapper di scrittura."""

    @pytest.fixture
    def client(self):
        from mcp_server.client import FoliariumApiClient
        return FoliariumApiClient(base_url="http://x:1", api_key="flr_a")

    def _ok(self, body, status=201):
        return httpx.Response(
            status_code=status,
            content=json.dumps(body).encode("utf-8"),
            headers={"content-type": "application/json"},
        )

    def test_create_comune(self, client):
        with patch.object(client._client, "request", return_value=self._ok({"id": 1})) as m:
            client.create_comune("Savona", "SV", "Liguria")
            assert m.call_args.args == ("POST", "/api/v1/comuni")
            assert m.call_args.kwargs["json"] == {
                "nome": "Savona", "provincia": "SV", "regione": "Liguria",
            }

    def test_create_possessore_drops_none(self, client):
        with patch.object(client._client, "request", return_value=self._ok({"id": 2})) as m:
            client.create_possessore("Rossi Mario", comune_id=1)
            assert m.call_args.args == ("POST", "/api/v1/possessori")
            assert m.call_args.kwargs["json"] == {
                "nome_completo": "Rossi Mario", "comune_id": 1,
            }

    def test_create_partita(self, client):
        with patch.object(client._client, "request", return_value=self._ok({"id": 9})) as m:
            client.create_partita(comune_id=1, numero_partita=42)
            assert m.call_args.args == ("POST", "/api/v1/partite")
            body = m.call_args.kwargs["json"]
            assert body["comune_id"] == 1 and body["numero_partita"] == 42

    def test_update_partita_patch(self, client):
        with patch.object(client._client, "request", return_value=self._ok({"ok": True}, 200)) as m:
            client.update_partita(7, stato="inattiva")
            assert m.call_args.args == ("PATCH", "/api/v1/partite/7")
            assert m.call_args.kwargs["json"] == {"stato": "inattiva"}

    def test_add_immobile_path(self, client):
        with patch.object(client._client, "request", return_value=self._ok({"id": 5})) as m:
            client.add_immobile(3, "Centro", "via", "casa")
            assert m.call_args.args == ("POST", "/api/v1/partite/3/immobili")

    def test_remove_immobile_delete_204(self, client):
        resp = httpx.Response(status_code=204, content=b"")
        with patch.object(client._client, "request", return_value=resp) as m:
            result = client.remove_immobile(3, 5)
            assert m.call_args.args == ("DELETE", "/api/v1/partite/3/immobili/5")
            assert result == {"ok": True}

    def test_add_variazione_path(self, client):
        with patch.object(client._client, "request", return_value=self._ok({"id": 1})) as m:
            client.add_variazione(3, "Vendita", "1900-01-01")
            assert m.call_args.args == ("POST", "/api/v1/partite/3/variazioni")

    def test_remove_variazione_delete(self, client):
        resp = httpx.Response(status_code=204, content=b"")
        with patch.object(client._client, "request", return_value=resp) as m:
            client.remove_variazione(3, 8)
            assert m.call_args.args == ("DELETE", "/api/v1/partite/3/variazioni/8")

    def test_add_possessore_to_partita_path(self, client):
        with patch.object(client._client, "request", return_value=self._ok({"ok": True})) as m:
            client.add_possessore_to_partita(3, 4)
            assert m.call_args.args == ("POST", "/api/v1/partite/3/possessori")
            assert m.call_args.kwargs["json"]["possessore_id"] == 4

    def test_remove_possessore_from_partita_delete(self, client):
        resp = httpx.Response(status_code=204, content=b"")
        with patch.object(client._client, "request", return_value=resp) as m:
            client.remove_possessore_from_partita(3, 4)
            assert m.call_args.args == ("DELETE", "/api/v1/partite/3/possessori/4")


# ─────────────────────────────────────────────────────────────────────
# Server MCP — registrazione e dispatch
# ─────────────────────────────────────────────────────────────────────

class TestBuildServer:

    EXPECTED_TOOLS = [
        # lettura
        "elenca_comuni", "elenca_localita",
        "cerca_partite", "dettagli_partita",
        "cerca_possessori", "dettagli_possessore",
        "genealogia_partita", "timeline_partita",
        "elenca_immobili", "statistiche_dashboard",
        "analytics_dashboard", "registro_audit", "riepilogo_audit",
        # scrittura sicura
        "crea_comune", "crea_possessore", "crea_partita",
        "aggiungi_immobile", "aggiungi_variazione",
        "aggiungi_possessore_a_partita",
        # scrittura distruttiva
        "aggiorna_partita", "rimuovi_immobile", "rimuovi_variazione",
        "rimuovi_possessore_da_partita",
    ]

    def test_registers_all_tools(self):
        from mcp_server.server import build_server
        from mcp_server.client import FoliariumApiClient
        mock = MagicMock(spec=FoliariumApiClient)
        server = build_server(client=mock)

        tools = asyncio.run(server.list_tools())
        names = sorted(t.name for t in tools)
        assert names == sorted(self.EXPECTED_TOOLS)

    def test_tools_have_descriptions(self):
        from mcp_server.server import build_server
        from mcp_server.client import FoliariumApiClient
        mock = MagicMock(spec=FoliariumApiClient)
        server = build_server(client=mock)
        tools = asyncio.run(server.list_tools())
        for t in tools:
            assert t.description, f"tool {t.name} senza description"
            assert len(t.description) > 20

    def test_cerca_possessori_rejects_short_query(self):
        """Validazione client-side: q < 2 char restituisce errore senza
        chiamare l'API."""
        from mcp_server.server import build_server
        from mcp_server.client import FoliariumApiClient
        mock = MagicMock(spec=FoliariumApiClient)
        server = build_server(client=mock)

        result = asyncio.run(server.call_tool("cerca_possessori", {"q": "a"}))
        # FastMCP ritorna sempre una lista di Content
        text = _extract_text(result)
        assert "almeno 2 caratteri" in text
        mock.search_possessori.assert_not_called()

    def test_dispatch_elenca_comuni_calls_client(self):
        from mcp_server.server import build_server
        from mcp_server.client import FoliariumApiClient
        mock = MagicMock(spec=FoliariumApiClient)
        mock.list_comuni.return_value = [
            {"id": 1, "nome": "Savona", "provincia": "SV"},
        ]
        server = build_server(client=mock)
        result = asyncio.run(server.call_tool("elenca_comuni", {}))
        text = _extract_text(result)
        mock.list_comuni.assert_called_once()
        assert "Savona" in text
        # Output formattato come JSON indentato
        assert json.loads(text) == [{"id": 1, "nome": "Savona", "provincia": "SV"}]

    def test_dispatch_cerca_partite_forwards_args(self):
        from mcp_server.server import build_server
        from mcp_server.client import FoliariumApiClient
        mock = MagicMock(spec=FoliariumApiClient)
        mock.search_partite.return_value = []
        server = build_server(client=mock)
        asyncio.run(server.call_tool("cerca_partite", {
            "comune_id": 1, "possessore": "rossi",
        }))
        kwargs = mock.search_partite.call_args.kwargs
        assert kwargs["comune_id"] == 1
        assert kwargs["possessore"] == "rossi"

    def test_dispatch_handles_api_error(self):
        from mcp_server.server import build_server
        from mcp_server.client import FoliariumApiClient, FoliariumApiError
        mock = MagicMock(spec=FoliariumApiClient)
        mock.list_comuni.side_effect = FoliariumApiError(
            "Chiave API revocata", status=401,
        )
        server = build_server(client=mock)
        result = asyncio.run(server.call_tool("elenca_comuni", {}))
        text = _extract_text(result)
        assert "Errore Foliarium" in text
        assert "Chiave API revocata" in text

    def test_dispatch_elenca_immobili_forwards_args(self):
        from mcp_server.server import build_server
        from mcp_server.client import FoliariumApiClient
        mock = MagicMock(spec=FoliariumApiClient)
        mock.search_immobili.return_value = []
        server = build_server(client=mock)
        asyncio.run(server.call_tool("elenca_immobili", {"partita_id": 3}))
        assert mock.search_immobili.call_args.kwargs["partita_id"] == 3


class TestWriteConfirmation:
    """I tool di scrittura non devono chiamare l'API senza confirm=True."""

    def _server(self, mock):
        from mcp_server.server import build_server
        return build_server(client=mock)

    def _mock(self):
        from mcp_server.client import FoliariumApiClient
        return MagicMock(spec=FoliariumApiClient)

    def test_crea_comune_without_confirm_is_preview(self):
        mock = self._mock()
        server = self._server(mock)
        result = asyncio.run(server.call_tool("crea_comune", {
            "nome": "Savona", "provincia": "SV", "regione": "Liguria",
        }))
        text = _extract_text(result)
        assert "anteprima" in text.lower()
        assert "confirm=true" in text.lower()
        mock.create_comune.assert_not_called()

    def test_crea_comune_with_confirm_calls_api(self):
        mock = self._mock()
        mock.create_comune.return_value = {"id": 1}
        server = self._server(mock)
        result = asyncio.run(server.call_tool("crea_comune", {
            "nome": "Savona", "provincia": "SV", "regione": "Liguria",
            "confirm": True,
        }))
        _extract_text(result)
        mock.create_comune.assert_called_once()

    def test_rimuovi_immobile_without_confirm_is_preview(self):
        mock = self._mock()
        server = self._server(mock)
        result = asyncio.run(server.call_tool("rimuovi_immobile", {
            "partita_id": 3, "immobile_id": 5,
        }))
        text = _extract_text(result)
        assert "irreversibile" in text.lower()
        mock.remove_immobile.assert_not_called()

    def test_rimuovi_immobile_with_confirm_calls_api(self):
        mock = self._mock()
        mock.remove_immobile.return_value = {"ok": True}
        server = self._server(mock)
        asyncio.run(server.call_tool("rimuovi_immobile", {
            "partita_id": 3, "immobile_id": 5, "confirm": True,
        }))
        mock.remove_immobile.assert_called_once_with(3, 5)

    def test_aggiorna_partita_no_fields_errors(self):
        mock = self._mock()
        server = self._server(mock)
        result = asyncio.run(server.call_tool("aggiorna_partita", {
            "partita_id": 7, "confirm": True,
        }))
        text = _extract_text(result)
        assert "nessun campo" in text.lower()
        mock.update_partita.assert_not_called()

    def test_aggiorna_partita_with_fields_and_confirm(self):
        mock = self._mock()
        mock.update_partita.return_value = {"ok": True}
        server = self._server(mock)
        asyncio.run(server.call_tool("aggiorna_partita", {
            "partita_id": 7, "stato": "inattiva", "confirm": True,
        }))
        assert mock.update_partita.call_args.args[0] == 7
        assert mock.update_partita.call_args.kwargs == {"stato": "inattiva"}


# ─────────────────────────────────────────────────────────────────────
# Helper test
# ─────────────────────────────────────────────────────────────────────

def _extract_text(result) -> str:
    """FastMCP.call_tool ritorna una struttura che varia tra versioni.

    Supporta: list[TextContent], tuple (list, dict), o str diretta.
    """
    if isinstance(result, str):
        return result
    if isinstance(result, tuple) and result:
        result = result[0]
    if isinstance(result, list) and result:
        first = result[0]
        # TextContent ha .text; dict ha "text"
        return getattr(first, "text", None) or first.get("text", str(first))
    return str(result)
