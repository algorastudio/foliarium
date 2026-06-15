"""mcp_server/server.py — Definizione dei tool Foliarium per Claude via MCP.

Costruisce un ``FastMCP`` server che incapsula le chiamate all'API REST.
Ogni tool ha una docstring descrittiva: il client MCP (Claude Desktop, ecc.)
la legge per decidere quando invocare il tool.

I tool si dividono in tre famiglie:

* **lettura** — elenco/ricerca/dettaglio + statistiche e audit (sola lettura,
  scope API key ``read:*``);
* **scrittura "sicura"** — creazione comuni, possessori, partite, immobili,
  variazioni e legami possessore (scope ``write:*``);
* **scrittura distruttiva** — aggiornamento partita e rimozione di
  immobili/variazioni/legami (scope ``write:*``).

Per evitare modifiche accidentali da prompt ambigui, **tutti i tool di
scrittura richiedono il parametro esplicito ``confirm=True``**. Senza
conferma il tool restituisce un'anteprima testuale dell'operazione e non
chiama l'API.

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


def _needs_confirm(confirm: bool, anteprima: str) -> Optional[str]:
    """Guard per i tool di scrittura.

    Se ``confirm`` è falso restituisce un messaggio di anteprima (l'operazione
    NON viene eseguita); altrimenti restituisce ``None`` e il chiamante
    procede con la scrittura. Implementa la conferma esplicita richiesta per
    tutte le operazioni che modificano l'archivio.
    """
    if confirm:
        return None
    return (
        "⚠️ Operazione di scrittura NON eseguita (anteprima).\n\n"
        f"{anteprima}\n\n"
        "Questa operazione modifica l'archivio catastale. Per eseguirla "
        "davvero, richiama di nuovo lo stesso tool aggiungendo confirm=true."
    )


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

    # ════════════════════════════════════════════════════════════════
    #  LETTURA AGGIUNTIVA (sola lettura, scope read:*)
    # ════════════════════════════════════════════════════════════════

    # ── Tool 9 — Elenco immobili ──────────────────────────────────
    @mcp.tool()
    def elenca_immobili(
        partita_id: Optional[int] = None,
        comune_id: Optional[int] = None,
    ) -> str:
        """Elenca gli immobili (fabbricati, terreni) filtrando per partita
        e/o comune.

        Args:
            partita_id: ID della partita di cui elencare gli immobili.
            comune_id: ID del comune per filtrare gli immobili.
        """
        return _safe_call(
            _client_or_env().search_immobili,
            partita_id=partita_id,
            comune_id=comune_id,
        )

    # ── Tool 10 — Statistiche dashboard ───────────────────────────
    @mcp.tool()
    def statistiche_dashboard() -> str:
        """Restituisce le statistiche aggregate dell'archivio: totale partite,
        comuni, possessori, immobili e i primi comuni per numero di partite.

        Usalo per domande tipo "quante partite ci sono in archivio?" o
        "quali sono i comuni con più partite?"."""
        return _safe_call(_client_or_env().get_dashboard_stats)

    # ── Tool 11 — Analytics dashboard ─────────────────────────────
    @mcp.tool()
    def analytics_dashboard() -> str:
        """Restituisce gli analytics avanzati: KPI (partite, particelle,
        variazioni, utenti attivi), top 5 comuni, distribuzione dei documenti
        per tipologia e metriche di qualità dei dati (completezza, duplicati).
        """
        return _safe_call(_client_or_env().get_dashboard_analytics)

    # ── Tool 12 — Registro audit ──────────────────────────────────
    @mcp.tool()
    def registro_audit(
        table_name: Optional[str] = None,
        username: Optional[str] = None,
        operation: Optional[str] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> str:
        """Consulta il registro di audit (chi ha fatto cosa e quando).

        Args:
            table_name: Filtra per tabella (es. ``"partita"``, ``"possessore"``).
            username: Filtra per nome utente.
            operation: Tipo operazione: ``I`` (insert), ``U`` (update),
                ``D`` (delete), ``S`` (view/select).
            page: Pagina dei risultati (default 1).
            page_size: Righe per pagina (1-500, default 50).
        """
        return _safe_call(
            _client_or_env().list_audit,
            table_name=table_name,
            username=username,
            operation=operation,
            page=page,
            page_size=page_size,
        )

    # ── Tool 13 — Riepilogo audit ─────────────────────────────────
    @mcp.tool()
    def riepilogo_audit() -> str:
        """Restituisce i KPI di audit della giornata corrente: azioni oggi,
        utenti attivi, export effettuati, anomalie (cancellazioni)."""
        return _safe_call(_client_or_env().get_audit_summary)

    # ════════════════════════════════════════════════════════════════
    #  SCRITTURA "SICURA" (creazione/inserimento, scope write:*)
    #  Richiedono confirm=True per essere eseguite.
    # ════════════════════════════════════════════════════════════════

    # ── Tool 14 — Crea comune ─────────────────────────────────────
    @mcp.tool()
    def crea_comune(
        nome: str,
        provincia: str,
        regione: str,
        codice_catastale: Optional[str] = None,
        confirm: bool = False,
    ) -> str:
        """Registra un nuovo comune nell'archivio catastale.

        ⚠️ Operazione di scrittura: richiede confirm=True per essere eseguita.

        Args:
            nome: Nome del comune.
            provincia: Sigla o nome della provincia.
            regione: Regione.
            codice_catastale: Codice catastale Belfiore opzionale.
            confirm: Deve essere True per eseguire davvero la creazione.
        """
        guard = _needs_confirm(
            confirm, f"Verrà creato il comune '{nome}' ({provincia}, {regione}).")
        if guard:
            return guard
        return _safe_call(
            _client_or_env().create_comune,
            nome=nome, provincia=provincia, regione=regione,
            codice_catastale=codice_catastale,
        )

    # ── Tool 15 — Crea possessore ─────────────────────────────────
    @mcp.tool()
    def crea_possessore(
        nome_completo: str,
        comune_id: int,
        cognome_nome: Optional[str] = None,
        paternita: Optional[str] = None,
        confirm: bool = False,
    ) -> str:
        """Registra un nuovo possessore (proprietario storico).

        ⚠️ Operazione di scrittura: richiede confirm=True per essere eseguita.

        Args:
            nome_completo: Nome completo del possessore (es. "Rossi Mario").
            comune_id: ID del comune di riferimento (vedi ``elenca_comuni``).
            cognome_nome: Forma "Cognome Nome" opzionale.
            paternita: Paternità opzionale (es. "fu Giuseppe").
            confirm: Deve essere True per eseguire davvero la creazione.
        """
        guard = _needs_confirm(
            confirm, f"Verrà creato il possessore '{nome_completo}' "
                     f"(comune_id={comune_id}).")
        if guard:
            return guard
        return _safe_call(
            _client_or_env().create_possessore,
            nome_completo=nome_completo, comune_id=comune_id,
            cognome_nome=cognome_nome, paternita=paternita,
        )

    # ── Tool 16 — Crea partita ────────────────────────────────────
    @mcp.tool()
    def crea_partita(
        comune_id: int,
        numero_partita: int,
        suffisso_partita: Optional[str] = None,
        data_impianto: Optional[str] = None,
        tipo: str = "Principale",
        stato: str = "attiva",
        numero_provenienza: Optional[int] = None,
        confirm: bool = False,
    ) -> str:
        """Crea una nuova partita catastale.

        ⚠️ Operazione di scrittura: richiede confirm=True per essere eseguita.

        Args:
            comune_id: ID del comune (vedi ``elenca_comuni``).
            numero_partita: Numero progressivo della partita.
            suffisso_partita: Suffisso alfabetico opzionale (es. "bis").
            data_impianto: Data di impianto in formato ISO (YYYY-MM-DD).
            tipo: Tipo partita ("Principale" o "Secondaria").
            stato: Stato iniziale ("attiva" o "inattiva").
            numero_provenienza: Numero partita di provenienza opzionale.
            confirm: Deve essere True per eseguire davvero la creazione.
        """
        guard = _needs_confirm(
            confirm, f"Verrà creata la partita n. {numero_partita}"
                     f"{(' ' + suffisso_partita) if suffisso_partita else ''} "
                     f"nel comune_id={comune_id} (tipo={tipo}, stato={stato}).")
        if guard:
            return guard
        return _safe_call(
            _client_or_env().create_partita,
            comune_id=comune_id, numero_partita=numero_partita,
            suffisso_partita=suffisso_partita, data_impianto=data_impianto,
            tipo=tipo, stato=stato, numero_provenienza=numero_provenienza,
        )

    # ── Tool 17 — Aggiungi immobile a partita ─────────────────────
    @mcp.tool()
    def aggiungi_immobile(
        partita_id: int,
        localita_nome: str,
        tipologia_stradale: str,
        natura: str,
        numero_civico: Optional[str] = None,
        numero_piani: Optional[int] = None,
        numero_vani: Optional[int] = None,
        consistenza: Optional[str] = None,
        classificazione: Optional[str] = None,
        confirm: bool = False,
    ) -> str:
        """Aggiunge un immobile a una partita. La località viene creata
        automaticamente se non esiste già nel comune della partita.

        ⚠️ Operazione di scrittura: richiede confirm=True per essere eseguita.

        Args:
            partita_id: ID della partita a cui aggiungere l'immobile.
            localita_nome: Nome della località (via, contrada, ecc.).
            tipologia_stradale: Tipologia (es. "via", "piazza", "contrada").
            natura: Natura dell'immobile (es. "casa", "vigneto", "terreno").
            numero_civico: Numero civico opzionale.
            numero_piani: Numero di piani opzionale.
            numero_vani: Numero di vani opzionale.
            consistenza: Consistenza opzionale (testo libero).
            classificazione: Classificazione catastale opzionale.
            confirm: Deve essere True per eseguire davvero l'inserimento.
        """
        guard = _needs_confirm(
            confirm, f"Verrà aggiunto un immobile '{natura}' in "
                     f"{tipologia_stradale} {localita_nome} alla partita "
                     f"id={partita_id}.")
        if guard:
            return guard
        return _safe_call(
            _client_or_env().add_immobile,
            partita_id=partita_id, localita_nome=localita_nome,
            tipologia_stradale=tipologia_stradale, natura=natura,
            numero_civico=numero_civico, numero_piani=numero_piani,
            numero_vani=numero_vani, consistenza=consistenza,
            classificazione=classificazione,
        )

    # ── Tool 18 — Aggiungi variazione a partita ───────────────────
    @mcp.tool()
    def aggiungi_variazione(
        partita_id: int,
        tipo: str,
        data_variazione: str,
        partita_destinazione_id: Optional[int] = None,
        numero_riferimento: Optional[str] = None,
        nominativo_riferimento: Optional[str] = None,
        confirm: bool = False,
    ) -> str:
        """Registra una variazione su una partita (vendita, successione,
        frazionamento, ecc.).

        ⚠️ Operazione di scrittura: richiede confirm=True per essere eseguita.

        Args:
            partita_id: ID della partita di origine.
            tipo: Tipo variazione. Valori ammessi: Vendita, Acquisto,
                Successione, Variazione, Frazionamento, Divisione,
                Trasferimento, Altro.
            data_variazione: Data in formato ISO (YYYY-MM-DD).
            partita_destinazione_id: ID partita di destinazione opzionale.
            numero_riferimento: Riferimento documentale opzionale.
            nominativo_riferimento: Nominativo di riferimento opzionale.
            confirm: Deve essere True per eseguire davvero la registrazione.
        """
        guard = _needs_confirm(
            confirm, f"Verrà registrata una variazione '{tipo}' del "
                     f"{data_variazione} sulla partita id={partita_id}.")
        if guard:
            return guard
        return _safe_call(
            _client_or_env().add_variazione,
            partita_id=partita_id, tipo=tipo, data_variazione=data_variazione,
            partita_destinazione_id=partita_destinazione_id,
            numero_riferimento=numero_riferimento,
            nominativo_riferimento=nominativo_riferimento,
        )

    # ── Tool 19 — Associa possessore a partita ────────────────────
    @mcp.tool()
    def aggiungi_possessore_a_partita(
        partita_id: int,
        possessore_id: int,
        titolo: str = "proprietà esclusiva",
        quota: Optional[str] = None,
        tipo_partita: Optional[str] = None,
        confirm: bool = False,
    ) -> str:
        """Associa un possessore esistente a una partita come intestatario.

        ⚠️ Operazione di scrittura: richiede confirm=True per essere eseguita.

        Args:
            partita_id: ID della partita.
            possessore_id: ID del possessore (vedi ``cerca_possessori``).
            titolo: Titolo di possesso (es. "proprietà esclusiva").
            quota: Quota di possesso opzionale (es. "1/2").
            tipo_partita: "principale" o "secondaria" (default: il tipo
                della partita stessa).
            confirm: Deve essere True per eseguire davvero l'associazione.
        """
        guard = _needs_confirm(
            confirm, f"Il possessore id={possessore_id} verrà associato alla "
                     f"partita id={partita_id} (titolo='{titolo}').")
        if guard:
            return guard
        return _safe_call(
            _client_or_env().add_possessore_to_partita,
            partita_id=partita_id, possessore_id=possessore_id,
            titolo=titolo, quota=quota, tipo_partita=tipo_partita,
        )

    # ════════════════════════════════════════════════════════════════
    #  SCRITTURA DISTRUTTIVA (update/delete, scope write:*)
    #  Irreversibili: richiedono confirm=True.
    # ════════════════════════════════════════════════════════════════

    # ── Tool 20 — Aggiorna partita ────────────────────────────────
    @mcp.tool()
    def aggiorna_partita(
        partita_id: int,
        stato: Optional[str] = None,
        data_chiusura: Optional[str] = None,
        suffisso_partita: Optional[str] = None,
        numero_provenienza: Optional[int] = None,
        tipo: Optional[str] = None,
        confirm: bool = False,
    ) -> str:
        """Aggiorna i campi di una partita esistente (es. chiusura).

        ⚠️ Operazione di scrittura: richiede confirm=True per essere eseguita.
        Fornisci solo i campi da modificare.

        Args:
            partita_id: ID della partita da aggiornare.
            stato: Nuovo stato ("attiva" / "inattiva").
            data_chiusura: Data di chiusura in formato ISO (YYYY-MM-DD).
            suffisso_partita: Nuovo suffisso.
            numero_provenienza: Nuovo numero di provenienza.
            tipo: Nuovo tipo ("Principale" / "Secondaria").
            confirm: Deve essere True per eseguire davvero l'aggiornamento.
        """
        campi = {
            k: v for k, v in {
                "stato": stato, "data_chiusura": data_chiusura,
                "suffisso_partita": suffisso_partita,
                "numero_provenienza": numero_provenienza, "tipo": tipo,
            }.items() if v is not None
        }
        if not campi:
            return "Errore: nessun campo da aggiornare fornito."
        guard = _needs_confirm(
            confirm, f"La partita id={partita_id} verrà aggiornata: {campi}.")
        if guard:
            return guard
        return _safe_call(
            _client_or_env().update_partita, partita_id, **campi)

    # ── Tool 21 — Rimuovi immobile ────────────────────────────────
    @mcp.tool()
    def rimuovi_immobile(
        partita_id: int,
        immobile_id: int,
        confirm: bool = False,
    ) -> str:
        """Rimuove un immobile da una partita. Operazione IRREVERSIBILE.

        ⚠️ Operazione di scrittura: richiede confirm=True per essere eseguita.

        Args:
            partita_id: ID della partita.
            immobile_id: ID dell'immobile da rimuovere.
            confirm: Deve essere True per eseguire davvero la rimozione.
        """
        guard = _needs_confirm(
            confirm, f"L'immobile id={immobile_id} verrà rimosso dalla "
                     f"partita id={partita_id}. Operazione irreversibile.")
        if guard:
            return guard
        return _safe_call(
            _client_or_env().remove_immobile, partita_id, immobile_id)

    # ── Tool 22 — Rimuovi variazione ──────────────────────────────
    @mcp.tool()
    def rimuovi_variazione(
        partita_id: int,
        variazione_id: int,
        confirm: bool = False,
    ) -> str:
        """Rimuove una variazione da una partita. Operazione IRREVERSIBILE.

        ⚠️ Operazione di scrittura: richiede confirm=True per essere eseguita.

        Args:
            partita_id: ID della partita.
            variazione_id: ID della variazione da rimuovere.
            confirm: Deve essere True per eseguire davvero la rimozione.
        """
        guard = _needs_confirm(
            confirm, f"La variazione id={variazione_id} verrà rimossa dalla "
                     f"partita id={partita_id}. Operazione irreversibile.")
        if guard:
            return guard
        return _safe_call(
            _client_or_env().remove_variazione, partita_id, variazione_id)

    # ── Tool 23 — Dissocia possessore da partita ──────────────────
    @mcp.tool()
    def rimuovi_possessore_da_partita(
        partita_id: int,
        possessore_id: int,
        confirm: bool = False,
    ) -> str:
        """Rimuove l'associazione tra un possessore e una partita.
        Operazione IRREVERSIBILE.

        ⚠️ Operazione di scrittura: richiede confirm=True per essere eseguita.

        Args:
            partita_id: ID della partita.
            possessore_id: ID del possessore da dissociare.
            confirm: Deve essere True per eseguire davvero la rimozione.
        """
        guard = _needs_confirm(
            confirm, f"Il legame tra possessore id={possessore_id} e partita "
                     f"id={partita_id} verrà rimosso. Operazione irreversibile.")
        if guard:
            return guard
        return _safe_call(
            _client_or_env().remove_possessore_from_partita,
            partita_id, possessore_id)

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
