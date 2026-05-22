"""
db/drafts.py — Mixin per bozze del wizard Nuova Partita.

Le bozze salvano uno snapshot JSONB dello stato del wizard, legato
all'utente che le ha create, per permettere di sospendere e riprendere
inserimenti complessi anche da postazioni diverse.

Schema: catasto.partita_draft (auto-applicato in db/base.py).
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from psycopg2.extras import DictCursor

from catasto_exceptions import DBMError, DBNotFoundError
from db.base import db_handle_errors


class DBDraftsMixin:
    """CRUD per le bozze del wizard Nuova Partita."""

    @db_handle_errors
    def save_partita_draft(
        self,
        utente_id: Optional[int],
        titolo: str,
        payload: Dict[str, Any],
        draft_id: Optional[int] = None,
        app_version: Optional[str] = None,
    ) -> int:
        """Crea una nuova bozza o aggiorna quella indicata. Ritorna l'id."""
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
                        f"  AND (utente_id IS NOT DISTINCT FROM %s) "
                        f"RETURNING id",
                        (titolo, payload_json, app_version, draft_id, utente_id),
                    )
                    row = cur.fetchone()
                    if not row:
                        raise DBNotFoundError(
                            f"Bozza id={draft_id} non trovata o non accessibile."
                        )
                    return int(row["id"])

                cur.execute(
                    f"INSERT INTO {self.schema}.partita_draft "
                    f"  (utente_id, titolo, payload, app_version) "
                    f"VALUES (%s, %s, %s::jsonb, %s) "
                    f"RETURNING id",
                    (utente_id, titolo, payload_json, app_version),
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
    ) -> List[Dict[str, Any]]:
        """Elenca le bozze dell'utente (più recenti prima).

        Se utente_id è None vengono elencate solo le bozze orfane
        (utente_id IS NULL): non si mescolano bozze di utenti diversi.
        """
        with self._get_connection() as conn:
            with conn.cursor(cursor_factory=DictCursor) as cur:
                if utente_id is None:
                    cur.execute(
                        f"SELECT id, titolo, app_version, created_at, updated_at "
                        f"FROM {self.schema}.partita_draft "
                        f"WHERE utente_id IS NULL "
                        f"ORDER BY updated_at DESC LIMIT %s",
                        (limit,),
                    )
                else:
                    cur.execute(
                        f"SELECT id, titolo, app_version, created_at, updated_at "
                        f"FROM {self.schema}.partita_draft "
                        f"WHERE utente_id = %s "
                        f"ORDER BY updated_at DESC LIMIT %s",
                        (utente_id, limit),
                    )
                return [dict(row) for row in cur.fetchall()]

    @db_handle_errors
    def load_partita_draft(
        self,
        draft_id: int,
        utente_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Carica una bozza completa. Se utente_id è fornito, verifica l'ownership."""
        with self._get_connection() as conn:
            with conn.cursor(cursor_factory=DictCursor) as cur:
                if utente_id is None:
                    cur.execute(
                        f"SELECT id, utente_id, titolo, payload, app_version, "
                        f"       created_at, updated_at "
                        f"FROM {self.schema}.partita_draft WHERE id = %s",
                        (draft_id,),
                    )
                else:
                    cur.execute(
                        f"SELECT id, utente_id, titolo, payload, app_version, "
                        f"       created_at, updated_at "
                        f"FROM {self.schema}.partita_draft "
                        f"WHERE id = %s "
                        f"  AND (utente_id IS NOT DISTINCT FROM %s)",
                        (draft_id, utente_id),
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
    ) -> bool:
        """Elimina una bozza. Ritorna True se è stata effettivamente cancellata."""
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                if utente_id is None:
                    cur.execute(
                        f"DELETE FROM {self.schema}.partita_draft WHERE id = %s",
                        (draft_id,),
                    )
                else:
                    cur.execute(
                        f"DELETE FROM {self.schema}.partita_draft "
                        f"WHERE id = %s "
                        f"  AND (utente_id IS NOT DISTINCT FROM %s)",
                        (draft_id, utente_id),
                    )
                return cur.rowcount > 0
