"""mcp_server/client.py — Thin wrapper httpx per la REST API di Foliarium.

Tutte le chiamate usano l'header ``X-Foliarium-Api-Key``. Gli errori HTTP
sono tradotti in eccezioni ``FoliariumApiError`` con un messaggio leggibile,
così i tool MCP possono restituire spiegazioni utili a Claude (e quindi
all'utente finale) invece di stack trace tecnici.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Optional

import httpx


_log = logging.getLogger("mcp_server.client")

API_KEY_HEADER = "X-Foliarium-Api-Key"
ENV_BASE_URL = "FOLIARIUM_API_BASE_URL"
ENV_API_KEY = "FOLIARIUM_API_KEY"

DEFAULT_TIMEOUT = 15.0


class FoliariumApiError(RuntimeError):
    """Errore HTTP o di rete chiamando l'API Foliarium."""

    def __init__(self, message: str, *, status: Optional[int] = None,
                 detail: Optional[str] = None):
        super().__init__(message)
        self.status = status
        self.detail = detail


class FoliariumApiClient:
    """Wrapper sincrono. Una sola istanza per processo è sufficiente."""

    def __init__(self, base_url: str, api_key: str,
                 timeout: float = DEFAULT_TIMEOUT):
        if not base_url:
            raise ValueError(f"{ENV_BASE_URL} non configurato")
        if not api_key:
            raise ValueError(f"{ENV_API_KEY} non configurato")
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self._client = httpx.Client(
            base_url=self.base_url,
            timeout=timeout,
            headers={API_KEY_HEADER: api_key,
                     "User-Agent": "foliarium-mcp/1.0"},
        )

    @classmethod
    def from_env(cls) -> "FoliariumApiClient":
        """Costruisce dall'ambiente. Solleva ``ValueError`` se manca config."""
        base = os.environ.get(ENV_BASE_URL, "")
        key = os.environ.get(ENV_API_KEY, "")
        return cls(base_url=base, api_key=key)

    def close(self):
        self._client.close()

    # ── primitive ──────────────────────────────────────────────────
    def _get(self, path: str, params: Optional[dict] = None) -> Any:
        try:
            r = self._client.get(path, params=_clean_params(params))
        except httpx.RequestError as e:
            raise FoliariumApiError(
                f"Impossibile contattare {self.base_url}{path}: {e}"
            ) from e
        return _decode(r, path=path)

    # ── endpoint wrapper ───────────────────────────────────────────
    def list_comuni(self) -> list[dict]:
        return self._get("/api/v1/comuni") or []

    def list_localita(self, comune_id: int) -> list[dict]:
        return self._get(f"/api/v1/comuni/{comune_id}/localita") or []

    def search_partite(
        self,
        comune_id: Optional[int] = None,
        numero_partita: Optional[int] = None,
        possessore: Optional[str] = None,
        immobile_natura: Optional[str] = None,
        suffisso: Optional[str] = None,
    ) -> list[dict]:
        return self._get("/api/v1/partite", params={
            "comune_id": comune_id,
            "numero_partita": numero_partita,
            "possessore": possessore,
            "immobile_natura": immobile_natura,
            "suffisso": suffisso,
        }) or []

    def get_partita(self, partita_id: int) -> dict:
        return self._get(f"/api/v1/partite/{partita_id}")

    def search_possessori(self, q: str) -> list[dict]:
        return self._get("/api/v1/possessori", params={"q": q}) or []

    def get_possessore(self, possessore_id: int) -> dict:
        return self._get(f"/api/v1/possessori/{possessore_id}")

    def get_genealogia(self, partita_id: int) -> dict:
        return self._get(f"/api/v1/genealogia/{partita_id}")

    def get_timeline_partita(self, partita_id: int) -> list[dict]:
        return self._get(f"/api/v1/timeline/partita/{partita_id}") or []


# ─────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────

def _clean_params(params: Optional[dict]) -> Optional[dict]:
    """Rimuove i parametri None per non sporcare la query string."""
    if not params:
        return None
    return {k: v for k, v in params.items() if v is not None and v != ""}


def _decode(response: httpx.Response, *, path: str) -> Any:
    """Decodifica la risposta o solleva FoliariumApiError con messaggio utile."""
    if response.status_code == 401:
        raise FoliariumApiError(
            "Chiave API non valida, scaduta o revocata. "
            "Genera una nuova chiave dal dialog "
            "Impostazioni → Gestione Chiavi API… di Foliarium.",
            status=401,
        )
    if response.status_code == 403:
        detail = _safe_detail(response)
        raise FoliariumApiError(
            f"Permesso negato. La chiave API non ha gli scope richiesti "
            f"per questa operazione. ({detail})",
            status=403, detail=detail,
        )
    if response.status_code == 404:
        raise FoliariumApiError(
            f"Risorsa non trovata: {path}", status=404,
        )
    if response.status_code >= 500:
        raise FoliariumApiError(
            f"Errore server Foliarium ({response.status_code}) su {path}. "
            f"Controllare i log dell'app desktop (Help → Esporta log per supporto).",
            status=response.status_code,
        )
    if response.status_code >= 400:
        detail = _safe_detail(response)
        raise FoliariumApiError(
            f"Errore {response.status_code} su {path}: {detail}",
            status=response.status_code, detail=detail,
        )
    try:
        return response.json()
    except ValueError:
        return response.text


def _safe_detail(response: httpx.Response) -> str:
    try:
        body = response.json()
        if isinstance(body, dict) and "detail" in body:
            return str(body["detail"])
        return str(body)
    except ValueError:
        return response.text[:200]
