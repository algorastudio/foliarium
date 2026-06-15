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

    def _send(self, method: str, path: str,
              json_body: Optional[dict] = None,
              params: Optional[dict] = None) -> Any:
        """Primitiva per POST/PATCH/DELETE con body JSON opzionale.

        I parametri ``None`` del body vengono ripuliti per non sovrascrivere
        i default lato API con ``null``.
        """
        try:
            r = self._client.request(
                method, path,
                params=_clean_params(params),
                json=_clean_params(json_body),
            )
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

    # ── lettura aggiuntiva ─────────────────────────────────────────
    def search_immobili(
        self,
        partita_id: Optional[int] = None,
        comune_id: Optional[int] = None,
    ) -> list[dict]:
        return self._get("/api/v1/immobili", params={
            "partita_id": partita_id,
            "comune_id": comune_id,
        }) or []

    def get_dashboard_stats(self) -> dict:
        return self._get("/api/v1/dashboard/stats")

    def get_dashboard_analytics(self) -> dict:
        return self._get("/api/v1/dashboard/analytics")

    def list_audit(
        self,
        table_name: Optional[str] = None,
        username: Optional[str] = None,
        operation: Optional[str] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> dict:
        return self._get("/api/v1/audit", params={
            "table_name": table_name,
            "username": username,
            "operation": operation,
            "page": page,
            "page_size": page_size,
        })

    def get_audit_summary(self) -> dict:
        return self._get("/api/v1/audit/summary")

    # ── scrittura: comuni / possessori ─────────────────────────────
    def create_comune(self, nome: str, provincia: str, regione: str,
                       codice_catastale: Optional[str] = None) -> dict:
        return self._send("POST", "/api/v1/comuni", json_body={
            "nome": nome,
            "provincia": provincia,
            "regione": regione,
            "codice_catastale": codice_catastale,
        })

    def create_possessore(self, nome_completo: str, comune_id: int,
                          cognome_nome: Optional[str] = None,
                          paternita: Optional[str] = None) -> dict:
        return self._send("POST", "/api/v1/possessori", json_body={
            "nome_completo": nome_completo,
            "comune_id": comune_id,
            "cognome_nome": cognome_nome,
            "paternita": paternita,
        })

    # ── scrittura: partite ─────────────────────────────────────────
    def create_partita(self, comune_id: int, numero_partita: int,
                       suffisso_partita: Optional[str] = None,
                       data_impianto: Optional[str] = None,
                       tipo: str = "Principale", stato: str = "attiva",
                       numero_provenienza: Optional[int] = None) -> dict:
        return self._send("POST", "/api/v1/partite", json_body={
            "comune_id": comune_id,
            "numero_partita": numero_partita,
            "suffisso_partita": suffisso_partita,
            "data_impianto": data_impianto,
            "tipo": tipo,
            "stato": stato,
            "numero_provenienza": numero_provenienza,
        })

    def update_partita(self, partita_id: int,
                      stato: Optional[str] = None,
                      data_chiusura: Optional[str] = None,
                      suffisso_partita: Optional[str] = None,
                      numero_provenienza: Optional[int] = None,
                      tipo: Optional[str] = None) -> dict:
        return self._send("PATCH", f"/api/v1/partite/{partita_id}", json_body={
            "stato": stato,
            "data_chiusura": data_chiusura,
            "suffisso_partita": suffisso_partita,
            "numero_provenienza": numero_provenienza,
            "tipo": tipo,
        })

    # ── scrittura: immobili ────────────────────────────────────────
    def add_immobile(self, partita_id: int, localita_nome: str,
                    tipologia_stradale: str, natura: str,
                    numero_civico: Optional[str] = None,
                    numero_piani: Optional[int] = None,
                    numero_vani: Optional[int] = None,
                    consistenza: Optional[str] = None,
                    classificazione: Optional[str] = None) -> dict:
        return self._send("POST", f"/api/v1/partite/{partita_id}/immobili", json_body={
            "localita_nome": localita_nome,
            "tipologia_stradale": tipologia_stradale,
            "natura": natura,
            "numero_civico": numero_civico,
            "numero_piani": numero_piani,
            "numero_vani": numero_vani,
            "consistenza": consistenza,
            "classificazione": classificazione,
        })

    def remove_immobile(self, partita_id: int, immobile_id: int) -> dict:
        return self._send(
            "DELETE", f"/api/v1/partite/{partita_id}/immobili/{immobile_id}")

    # ── scrittura: variazioni ──────────────────────────────────────
    def add_variazione(self, partita_id: int, tipo: str, data_variazione: str,
                     partita_destinazione_id: Optional[int] = None,
                     numero_riferimento: Optional[str] = None,
                     nominativo_riferimento: Optional[str] = None) -> dict:
        return self._send("POST", f"/api/v1/partite/{partita_id}/variazioni", json_body={
            "tipo": tipo,
            "data_variazione": data_variazione,
            "partita_destinazione_id": partita_destinazione_id,
            "numero_riferimento": numero_riferimento,
            "nominativo_riferimento": nominativo_riferimento,
        })

    def remove_variazione(self, partita_id: int, variazione_id: int) -> dict:
        return self._send(
            "DELETE", f"/api/v1/partite/{partita_id}/variazioni/{variazione_id}")

    # ── scrittura: legame partita ↔ possessore ─────────────────────
    def add_possessore_to_partita(self, partita_id: int, possessore_id: int,
                                titolo: str = "proprietà esclusiva",
                                quota: Optional[str] = None,
                                tipo_partita: Optional[str] = None) -> dict:
        return self._send("POST", f"/api/v1/partite/{partita_id}/possessori", json_body={
            "possessore_id": possessore_id,
            "titolo": titolo,
            "quota": quota,
            "tipo_partita": tipo_partita,
        })

    def remove_possessore_from_partita(self, partita_id: int,
                                     possessore_id: int) -> dict:
        return self._send(
            "DELETE", f"/api/v1/partite/{partita_id}/possessori/{possessore_id}")


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
    # 204 No Content (tipico delle DELETE) — nessun body da decodificare.
    if response.status_code == 204 or not response.content:
        return {"ok": True}
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
