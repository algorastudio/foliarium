"""mcp_server/server.py — Definizione dei 7 tool Foliarium per Claude via MCP.

Costruisce un ``FastMCP`` server con 7 tool che incapsulano le chiamate
all'API REST. Ogni tool ha una docstring descrittiva: il client MCP
(Claude Desktop, ecc.) la legge per decidere quando invocare il tool.

Esecuzione (stdio, default Claude Desktop)::

    python -m mcp_server

Le credenziali sono lette dall'ambiente:

* ``FOLIARIUM_API_BASE_URL`` (es. ``http://localhost:8765``)
* ``FOLIARIUM_API_KEY``      (formato ``flr_<32 hex>``)
"""

from __future__ import annotations

import json
import logging
import sys
from typing import Any, Optional

from mcp.server.fastmcp import FastMCP

from mcp_server.client import (
    FoliariumApiClient,
    FoliariumApiError,
    ENV_BASE_URL,
    ENV_API_KEY,
)


_log = logging.getLogger("mcp_server")


# ─────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────

def _format_result(data: Any) -> str:
    """Serializza il risultato in JSON leggibile per Claude."""
    try:
        return json.dumps(data, ensure_ascii=False, indent=2, default=str)
    except (TypeError, ValueError):
        return str(data)


def _safe_call(fn, *args, **kwargs) -> str:
    """Esegue una chiamata API e ne formatta esito o errore."""
    try:
        return _format_result(fn(*args, **kwargs))
    except FoliariumApiError as e:
        return f"Errore Foliarium: {e}"
    except Exception as e:  # noqa: BLE001
        _log.exception("Errore inatteso nel tool MCP")
        return f"Errore imprevisto: {e}"


# ─────────────────────────────────────────────────────────────────────
# Costruzione server
# ─────────────────────────────────────────────────────────────────────

def build_server(client: Optional[FoliariumApiClient] = None) -> FastMCP:
    """Costruisce il server MCP. Se ``client`` è None, lo carica dall'ambiente.

    Esposto come funzione separata per consentire l'iniezione del client
    nei test (mock httpx).
    """
    mcp = FastMCP("foliarium")

    # Il client viene risolto in modo lazy: se non passato esplicitamente,
    # viene letto dall'ambiente al primo uso di un tool. In questo modo
    # ``build_server()`` non fallisce in import-time se le env var non
    # sono ancora pronte.
    _client_box: dict[str, Optional[FoliariumApiClient]] = {"c": client}

    def _client_or_env() -> FoliariumApiClient:
        if _client_box["c"] is None:
            _client_box["c"] = FoliariumApiClient.from_env()
        return _client_box["c"]

    # ── Tool 1 — Elenco comuni ────────────────────────────────────
    @mcp.tool()
    def elenca_comuni() -> str:
        """Restituisce l'elenco completo dei comuni registrati nell'archivio
        catastale storico (id, nome, provincia).

        Usalo quando l'utente chiede "quali comuni ci sono?" o vuole sapere
        l'``id`` di un comune per filtrare ricerche successive."""
        return _safe_call(_client_or_env().list_comuni)

    # ── Tool 2 — Elenco località per comune ───────────────────────
    @mcp.tool()
    def elenca_localita(comune_id: int) -> str:
        """Restituisce le località (vie, piazze, contrade) di un comune.

        Args:
            comune_id: ID del comune (ottenibile via ``elenca_comuni``).
        """
        return _safe_call(_client_or_env().list_localita, comune_id)

    # ── Tool 3 — Ricerca partite ──────────────────────────────────
    @mcp.tool()
    def cerca_partite(
        comune_id: Optional[int] = None,
        numero_partita: Optional[int] = None,
        possessore: Optional[str] = None,
        immobile_natura: Optional[str] = None,
        suffisso: Optional[str] = None,
    ) -> str:
        """Cerca partite catastali per uno o più filtri.

        Almeno un filtro è raccomandato per non restituire l'intero archivio.

        Args:
            comune_id: ID comune (vedi ``elenca_comuni``).
            numero_partita: Numero progressivo della partita.
            possessore: Sotto-stringa del nome/cognome del possessore.
            immobile_natura: Tipo di immobile (es. ``"vigneto"``, ``"casa"``).
            suffisso: Suffisso alfabetico opzionale del numero (es. ``"bis"``).
        """
        return _safe_call(
            _client_or_env().search_partite,
            comune_id=comune_id,
            numero_partita=numero_partita,
            possessore=possessore,
            immobile_natura=immobile_natura,
            suffisso=suffisso,
        )

    # ── Tool 4 — Dettagli partita ─────────────────────────────────
    @mcp.tool()
    def dettagli_partita(partita_id: int) -> str:
        """Restituisce il dettaglio completo di una partita: dati anagrafici,
        possessori, immobili associati, variazioni e contratti.

        Args:
            partita_id: ID della partita (ottenibile da ``cerca_partite``).
        """
        return _safe_call(_client_or_env().get_partita, partita_id)

    # ── Tool 5 — Ricerca possessori ───────────────────────────────
    @mcp.tool()
    def cerca_possessori(q: str) -> str:
        """Ricerca full-text sui possessori (proprietari storici) per
        nome, cognome o paternità.

        Args:
            q: Termine di ricerca (minimo 2 caratteri).
        """
        if not q or len(q.strip()) < 2:
            return "Errore: termine di ricerca deve avere almeno 2 caratteri."
        return _safe_call(_client_or_env().search_possessori, q.strip())

    # ── Tool 6 — Dettagli possessore ──────────────────────────────
    @mcp.tool()
    def dettagli_possessore(possessore_id: int) -> str:
        """Restituisce i dati anagrafici di un possessore.

        Args:
            possessore_id: ID del possessore (da ``cerca_possessori``).
        """
        return _safe_call(_client_or_env().get_possessore, possessore_id)

    # ── Tool 7 — Albero genealogico partita ───────────────────────
    @mcp.tool()
    def genealogia_partita(partita_id: int) -> str:
        """Restituisce l'albero genealogico di una partita: predecessori
        (partite da cui deriva) e successori (partite che ne derivano).

        Utile per ricostruire la storia di una proprietà attraverso
        variazioni, frazionamenti e successioni.

        Args:
            partita_id: ID della partita di interesse.
        """
        return _safe_call(_client_or_env().get_genealogia, partita_id)

    # ── Tool 8 — Timeline variazioni partita ──────────────────────
    @mcp.tool()
    def timeline_partita(partita_id: int) -> str:
        """Restituisce la timeline cronologica delle variazioni di una
        partita (impianto, vendite, frazionamenti, chiusura).

        Args:
            partita_id: ID della partita.
        """
        return _safe_call(_client_or_env().get_timeline_partita, partita_id)

    return mcp


# ─────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────

def main() -> None:
    """Avvia il server MCP in modalità stdio (default Claude Desktop)."""
    # Logging su stderr per non sporcare lo stdout (riservato al protocollo MCP).
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        stream=sys.stderr,
    )

    import os
    if not os.environ.get(ENV_BASE_URL) or not os.environ.get(ENV_API_KEY):
        _log.error(
            "Configurazione mancante: imposta %s e %s come variabili "
            "d'ambiente (es. nel claude_desktop_config.json).",
            ENV_BASE_URL, ENV_API_KEY,
        )
        sys.exit(2)

    server = build_server()
    _log.info("Foliarium MCP server avviato (stdio mode)")
    server.run()


if __name__ == "__main__":
    main()
