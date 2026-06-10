#!/usr/bin/env python3
"""
bin/test_mcp_e2e.py — Test end-to-end della catena MCP → API → DB.

Verifica passo per passo che tutta la catena per Claude Desktop funzioni:

  1. L'API REST di Foliarium risponde su FOLIARIUM_API_BASE_URL.
  2. La chiave FOLIARIUM_API_KEY è valida e ha gli scope necessari.
  3. Ognuno degli 8 tool MCP riesce a chiamare l'API senza errori.

Lo script NON modifica dati: usa solo endpoint di lettura.

Usage:
    # Imposta credenziali nell'ambiente (stesso pattern di Claude Desktop)
    export FOLIARIUM_API_BASE_URL=http://localhost:8765
    export FOLIARIUM_API_KEY=flr_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
    python bin/test_mcp_e2e.py

    # Oppure passando i parametri da CLI
    python bin/test_mcp_e2e.py --base-url http://localhost:8765 \\
                               --api-key flr_xxx

Exit code:
    0   tutti i tool ok (catena pronta per Claude)
    1   almeno un tool fallisce
    2   configurazione mancante o API irraggiungibile
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Callable

# Permetti l'esecuzione anche da fuori la root del progetto
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))


# ─────────────────────────────────────────────────────────────────────
# Colori semplici (no dipendenze esterne)
# ─────────────────────────────────────────────────────────────────────

class C:
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    RESET = "\033[0m"


def _ok(msg: str) -> None:
    print(f"  {C.GREEN}✓{C.RESET} {msg}")


def _fail(msg: str) -> None:
    print(f"  {C.RED}✗{C.RESET} {msg}")


def _info(msg: str) -> None:
    print(f"  {C.BLUE}ℹ{C.RESET} {msg}")


def _section(num: int, title: str) -> None:
    print(f"\n{C.BOLD}{C.BLUE}━━━ STEP {num}: {title} ━━━{C.RESET}")


# ─────────────────────────────────────────────────────────────────────
# Step 1 — Config
# ─────────────────────────────────────────────────────────────────────

def step_config(args) -> tuple[str, str]:
    _section(1, "Configurazione")

    base_url = (args.base_url or os.environ.get("FOLIARIUM_API_BASE_URL", "")).strip()
    api_key = (args.api_key or os.environ.get("FOLIARIUM_API_KEY", "")).strip()

    if not base_url:
        _fail("FOLIARIUM_API_BASE_URL non impostato.")
        _info("Esempio: export FOLIARIUM_API_BASE_URL=http://localhost:8765")
        sys.exit(2)
    if not api_key:
        _fail("FOLIARIUM_API_KEY non impostata.")
        _info("Genera una chiave dal dialog Impostazioni → Gestione Chiavi API… di Foliarium")
        sys.exit(2)
    if not api_key.startswith("flr_"):
        _fail(f"FOLIARIUM_API_KEY non sembra valida (deve iniziare con 'flr_'): {api_key[:8]}...")
        sys.exit(2)

    _ok(f"API base URL:  {base_url}")
    _ok(f"API key:       {api_key[:8]}...{api_key[-4:]}  (prefix + last 4)")

    # Dipendenze MCP installate nel Python corrente?
    # Se Claude Desktop fosse configurato col Python sbagliato, l'errore
    # sarebbe "No module named mcp_server" / "No module named mcp".
    # Qui controlliamo che il Python in uso (questo interprete) le abbia.
    missing = []
    try:
        import mcp  # noqa: F401
    except ImportError:
        missing.append("mcp")
    try:
        import httpx  # noqa: F401
    except ImportError:
        missing.append("httpx")
    if missing:
        _fail(f"Dipendenze mancanti nel Python corrente: {', '.join(missing)}")
        _info(f"Python in uso: {sys.executable}")
        _info(f"Installa con: {sys.executable} -m pip install {' '.join(missing)}")
        _info("Se hai una venv, attivala prima di rilanciare lo script.")
        sys.exit(2)
    _ok(f"Python corrente: {sys.executable}")
    _ok("Dipendenze mcp + httpx presenti")

    return base_url, api_key


# ─────────────────────────────────────────────────────────────────────
# Step 2 — Connettività + auth
# ─────────────────────────────────────────────────────────────────────

def step_connectivity(base_url: str, api_key: str):
    _section(2, "Connettività API + autenticazione")

    from mcp_server.client import FoliariumApiClient, FoliariumApiError

    try:
        client = FoliariumApiClient(base_url=base_url, api_key=api_key, timeout=5.0)
    except ValueError as e:
        _fail(f"Impossibile costruire il client: {e}")
        sys.exit(2)

    _info("Provo a leggere l'elenco comuni come smoke test...")
    try:
        comuni = client.list_comuni()
    except FoliariumApiError as e:
        _fail(f"Chiamata fallita ({e.status}): {e}")
        if e.status == 401:
            _info("→ La chiave API è invalida, scaduta o revocata.")
            _info("  Apri Foliarium → Impostazioni → Gestione Chiavi API…")
            _info("  e genera una nuova chiave.")
        elif e.status is None:
            _info("→ L'API non è raggiungibile.")
            _info("  Verifica che Foliarium sia avviato e che il frontend integrato sia attivo.")
        sys.exit(2)

    if not isinstance(comuni, list):
        _fail(f"Risposta inattesa: tipo {type(comuni).__name__} invece di list")
        sys.exit(1)

    _ok(f"Connessione OK — {len(comuni)} comuni nel database")
    return client, comuni


# ─────────────────────────────────────────────────────────────────────
# Step 3 — Dispatch dei tool MCP
# ─────────────────────────────────────────────────────────────────────

def step_tools(client, comuni: list) -> int:
    _section(3, "Test degli 8 tool MCP")

    from mcp_server.client import FoliariumApiError

    failures: list[str] = []

    def _run(label: str, fn: Callable, *args, **kwargs):
        try:
            result = fn(*args, **kwargs)
        except FoliariumApiError as e:
            _fail(f"{label}  →  {e.status} {e}")
            failures.append(label)
            return None
        n = len(result) if isinstance(result, list) else 1
        _ok(f"{label}  →  OK ({n} risultati)")
        return result

    # 1. elenca_comuni (già fatto come smoke test)
    _ok("elenca_comuni       →  OK (già verificato in step 2)")

    # Scelgo il primo comune per i test successivi
    if not comuni:
        _info("Database vuoto: i test sui dettagli sono saltati (servono comuni con dati).")
        return 0
    first_comune = comuni[0]
    first_id = first_comune.get("id")
    _info(f"Comune di test: {first_comune.get('nome')} (id={first_id})")

    # 2. elenca_localita
    _run("elenca_localita     ", client.list_localita, first_id)

    # 3. cerca_partite
    partite = _run("cerca_partite       ", client.search_partite, comune_id=first_id)

    # 4. dettagli_partita (se ce ne sono)
    first_partita_id = None
    if isinstance(partite, list) and partite:
        first_partita_id = partite[0].get("id") or partite[0].get("partita_id")
        if first_partita_id:
            _run("dettagli_partita    ", client.get_partita, first_partita_id)
        else:
            _info("dettagli_partita     →  skip (id partita non disponibile nella risposta)")
    else:
        _info("dettagli_partita     →  skip (nessuna partita nel comune)")

    # 5. cerca_possessori
    possessori = _run("cerca_possessori    ", client.search_possessori, "a")

    # 6. dettagli_possessore
    if isinstance(possessori, list) and possessori:
        pid = possessori[0].get("id")
        if pid:
            _run("dettagli_possessore ", client.get_possessore, pid)
        else:
            _info("dettagli_possessore  →  skip (id possessore non disponibile)")
    else:
        _info("dettagli_possessore  →  skip (nessun possessore trovato)")

    # 7. genealogia_partita
    if first_partita_id:
        _run("genealogia_partita  ", client.get_genealogia, first_partita_id)
    else:
        _info("genealogia_partita   →  skip (nessuna partita di test)")

    # 8. timeline_partita
    if first_partita_id:
        _run("timeline_partita    ", client.get_timeline_partita, first_partita_id)
    else:
        _info("timeline_partita     →  skip (nessuna partita di test)")

    return len(failures)


# ─────────────────────────────────────────────────────────────────────
# Step 4 — Verifica registrazione tool MCP
# ─────────────────────────────────────────────────────────────────────

def step_mcp_registration():
    _section(4, "Registrazione tool nel server MCP")

    import asyncio
    from mcp_server.server import build_server
    from unittest.mock import MagicMock

    server = build_server(client=MagicMock())
    tools = asyncio.run(server.list_tools())

    expected = {
        "elenca_comuni", "elenca_localita",
        "cerca_partite", "dettagli_partita",
        "cerca_possessori", "dettagli_possessore",
        "genealogia_partita", "timeline_partita",
    }
    got = {t.name for t in tools}

    missing = expected - got
    extra = got - expected
    if missing:
        _fail(f"Tool mancanti nel server MCP: {sorted(missing)}")
        return False
    if extra:
        _info(f"Tool extra registrati (non previsti dall'E2E): {sorted(extra)}")

    _ok("Tutti gli 8 tool registrati nel server MCP")
    for t in sorted(tools, key=lambda t: t.name):
        first_line = (t.description or "").split("\n", 1)[0]
        print(f"      {C.DIM}- {t.name}: {first_line}{C.RESET}")
    return True


# ─────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser(
        description="Test E2E della catena Claude Desktop → MCP → API → DB Foliarium",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    ap.add_argument("--base-url", help="URL base API (default: $FOLIARIUM_API_BASE_URL)")
    ap.add_argument("--api-key", help="Chiave API flr_... (default: $FOLIARIUM_API_KEY)")
    args = ap.parse_args()

    print(f"{C.BOLD}Foliarium MCP — test end-to-end{C.RESET}")
    print(f"{C.DIM}Verifica che l'app, l'API, la chiave e i tool MCP funzionino "
          f"come catena unica.{C.RESET}")

    # Step 1: config
    base_url, api_key = step_config(args)

    # Step 2: connettività + auth
    client, comuni = step_connectivity(base_url, api_key)

    # Step 3: dispatch dei tool
    n_failures = step_tools(client, comuni)

    # Step 4: registrazione MCP
    mcp_ok = step_mcp_registration()

    # Riepilogo
    print(f"\n{C.BOLD}━━━ RISULTATO ━━━{C.RESET}")
    if n_failures == 0 and mcp_ok:
        print(f"{C.GREEN}{C.BOLD}✓ Tutto funziona.{C.RESET} "
              "La catena è pronta per Claude Desktop.")
        print("\nProssimo passo: configura claude_desktop_config.json")
        print(f"come spiegato in {C.BLUE}docs/admin/mcp.md{C.RESET}, "
              f"poi riavvia Claude Desktop.")
        sys.exit(0)
    elif n_failures:
        print(f"{C.RED}{C.BOLD}✗ {n_failures} tool hanno fallito.{C.RESET} "
              "Vedi messaggi sopra per i dettagli.")
        sys.exit(1)
    else:
        sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nInterrotto.")
        sys.exit(130)
