"""
db/drafts.py — Mixin per bozze dei wizard partita.

Le bozze salvano uno snapshot JSONB dello stato del wizard, legato
all'utente che le ha create, per permettere di sospendere e riprendere
inserimenti complessi anche da postazioni diverse.

La colonna `wizard_kind` discrimina il wizard d'origine: i due flussi
(`nuova_partita_wizard` e `registrazione_proprieta`) hanno schemi di
payload diversi e non vanno mescolati nelle liste.

Schema: catasto.partita_draft (auto-applicato in db/base.py).
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from psycopg2.extras import DictCursor

from catasto_exceptions import DBMError, DBNotFoundError
from db.base import db_handle_errors


# Costanti per i wizard supportati
WIZARD_KIND_NUOVA_PARTITA = "nuova_partita_wizard"
WIZARD_KIND_REGISTRAZIONE_PROPRIETA = "registrazione_proprieta"


class DBDraftsMixin:
    """CRUD per le bozze dei wizard partita."""

    @db_handle_errors
    def save_partita_draft(
        self,
        utente_id: Optional[int],
        titolo: str,
        payload: Dict[str, Any],
        draft_id: Optional[int] = None,
        app_version: Optional[str] = None,
        wizard_kind: str = WIZARD_KIND_NUOVA_PARTITA,
    ) -> int:
        """Crea una nuova bozza o aggiorna quella indicata. Ritorna l'id.

        Su UPDATE l'ownership è verificata sia per `utente_id` sia per
        `wizard_kind` (non si può sovrascrivere una bozza di un altro
        wizard).
        """
        payload_json = json.dumps(payload, ensure_ascii=False, default=str)

        with self._get_connection() as conn:
            with conn.cursor(cursor_factory=DictCursor) as cur:
                if draft_id is not None:
                    cur.execute(
                        f"UPDATE {self.schema}.partita_draft "
                        f"SET titolo = %s, payload = %s::jsonb, "
                        f"    app_version = COALESCE(%s, app_version), "
                        f"    updated_at = CURRENT_TIMESTAMP "
                        f"WHERE id = %s "
                        f"  AND wizard_kind = %s "
                        f"  AND (utente_id IS NOT DISTINCT FROM %s) "
                        f"RETURNING id",
                        (titolo, payload_json, app_version, draft_id,
                         wizard_kind, utente_id),
                    )
                    row = cur.fetchone()
                    if not row:
                        raise DBNotFoundError(
                            f"Bozza id={draft_id} non trovata o non accessibile."
                        )
                    return int(row["id"])

                cur.execute(
                    f"INSERT INTO {self.schema}.partita_draft "
                    f"  (utente_id, wizard_kind, titolo, payload, app_version) "
                    f"VALUES (%s, %s, %s, %s::jsonb, %s) "
                    f"RETURNING id",
                    (utente_id, wizard_kind, titolo, payload_json, app_version),
                )
                row = cur.fetchone()
                if not row:
                    raise DBMError("Inserimento bozza fallito, nessun ID restituito.")
                return int(row["id"])

    @db_handle_errors
    def list_partita_drafts(
        self,
        utente_id: Optional[int],
        limit: int = 50,
        wizard_kind: Optional[str] = WIZARD_KIND_NUOVA_PARTITA,
    ) -> List[Dict[str, Any]]:
        """Elenca le bozze dell'utente per il wizard indicato (più recenti prima).

        Se `wizard_kind` è None vengono restituite le bozze di tutti i
        wizard. Se `utente_id` è None vengono elencate solo le bozze
        orfane (utente_id IS NULL): non si mescolano bozze di utenti diversi.
        """
        conds: List[str] = []
        params: List[Any] = []
        if utente_id is None:
            conds.append("utente_id IS NULL")
        else:
            conds.append("utente_id = %s")
            params.append(utente_id)
        if wizard_kind is not None:
            conds.append("wizard_kind = %s")
            params.append(wizard_kind)
        where = " AND ".join(conds) if conds else "TRUE"
        params.append(limit)

        with self._get_connection() as conn:
            with conn.cursor(cursor_factory=DictCursor) as cur:
                cur.execute(
                    f"SELECT id, wizard_kind, titolo, app_version, created_at, updated_at "
                    f"FROM {self.schema}.partita_draft "
                    f"WHERE {where} "
                    f"ORDER BY updated_at DESC LIMIT %s",
                    tuple(params),
                )
                return [dict(row) for row in cur.fetchall()]

    @db_handle_errors
    def load_partita_draft(
        self,
        draft_id: int,
        utente_id: Optional[int] = None,
        wizard_kind: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Carica una bozza completa.

        Se `utente_id` è fornito, verifica l'ownership.
        Se `wizard_kind` è fornito, verifica anche il tipo wizard
        (evita di caricare in un wizard un payload destinato all'altro).
        """
        conds: List[str] = ["id = %s"]
        params: List[Any] = [draft_id]
        if utente_id is not None:
            conds.append("(utente_id IS NOT DISTINCT FROM %s)")
            params.append(utente_id)
        if wizard_kind is not None:
            conds.append("wizard_kind = %s")
            params.append(wizard_kind)
        where = " AND ".join(conds)

        with self._get_connection() as conn:
            with conn.cursor(cursor_factory=DictCursor) as cur:
                cur.execute(
                    f"SELECT id, utente_id, wizard_kind, titolo, payload, "
                    f"       app_version, created_at, updated_at "
                    f"FROM {self.schema}.partita_draft "
                    f"WHERE {where}",
                    tuple(params),
                )
                row = cur.fetchone()
                if not row:
                    raise DBNotFoundError(
                        f"Bozza id={draft_id} non trovata o non accessibile."
                    )
                result = dict(row)
                # psycopg2 deserializza già JSONB → dict, ma se arriva str
                # gestiamo entrambi i casi.
                if isinstance(result.get("payload"), str):
                    result["payload"] = json.loads(result["payload"])
                return result

    @db_handle_errors
    def delete_partita_draft(
        self,
        draft_id: int,
        utente_id: Optional[int] = None,
        wizard_kind: Optional[str] = None,
    ) -> bool:
        """Elimina una bozza. Ritorna True se è stata effettivamente cancellata."""
        conds: List[str] = ["id = %s"]
        params: List[Any] = [draft_id]
        if utente_id is not None:
            conds.append("(utente_id IS NOT DISTINCT FROM %s)")
            params.append(utente_id)
        if wizard_kind is not None:
            conds.append("wizard_kind = %s")
            params.append(wizard_kind)
        where = " AND ".join(conds)

        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"DELETE FROM {self.schema}.partita_draft WHERE {where}",
                    tuple(params),
                )
                return cur.rowcount > 0
