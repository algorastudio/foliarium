"""
db/archivio.py — Mixin per soft delete (archiviazione) delle entità principali.

Semantica:
  - comune, localita, partita: colonna `archiviato BOOLEAN DEFAULT FALSE`
  - possessore: colonna `attivo BOOLEAN DEFAULT TRUE` (pre-esistente) + `archiviato_il`

API pubblica:
  archivia_*(id)      → soft delete
  ripristina_*(id)    → annulla soft delete
  get_archiviati_*()  → lista elementi archiviati (per pannello admin)
  get_tutti_archiviati() → dict con tutti i tipi
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from psycopg2.extras import DictCursor

from catasto_exceptions import DBDataError, DBMError, DBNotFoundError
from db.base import db_handle_errors

if TYPE_CHECKING:
    from catasto_db_manager import CatastoDBManager


class DBArchiviaMixin:
    """Soft delete per comune, possessore, localita, partita."""

    # ─────────────────────────────────────────────────────────────────────────
    # COMUNE
    # ─────────────────────────────────────────────────────────────────────────

    @db_handle_errors
    def archivia_comune(self, comune_id: int) -> bool:
        if not isinstance(comune_id, int) or comune_id <= 0:
            raise DBDataError(f"ID comune non valido: {comune_id}")
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"UPDATE {self.schema}.comune "
                    "SET archiviato = TRUE, archiviato_il = NOW() "
                    "WHERE id = %s AND NOT archiviato RETURNING id",
                    (comune_id,)
                )
                if cur.fetchone() is None:
                    raise DBNotFoundError(f"Comune ID {comune_id} non trovato o già archiviato.")
        self.logger.info(f"Comune {comune_id} archiviato.")
        return True

    @db_handle_errors
    def ripristina_comune(self, comune_id: int) -> bool:
        if not isinstance(comune_id, int) or comune_id <= 0:
            raise DBDataError(f"ID comune non valido: {comune_id}")
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"UPDATE {self.schema}.comune "
                    "SET archiviato = FALSE, archiviato_il = NULL "
                    "WHERE id = %s AND archiviato RETURNING id",
                    (comune_id,)
                )
                if cur.fetchone() is None:
                    raise DBNotFoundError(f"Comune ID {comune_id} non trovato o non archiviato.")
        self.logger.info(f"Comune {comune_id} ripristinato.")
        return True

    @db_handle_errors
    def get_archiviati_comuni(self) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            with conn.cursor(cursor_factory=DictCursor) as cur:
                cur.execute(
                    f"SELECT id, nome, provincia, regione, archiviato_il "
                    f"FROM {self.schema}.comune WHERE archiviato ORDER BY archiviato_il DESC"
                )
                return [dict(r) for r in cur.fetchall()]

    # ─────────────────────────────────────────────────────────────────────────
    # POSSESSORE  (usa colonna 'attivo'; FALSE = archiviato)
    # ─────────────────────────────────────────────────────────────────────────

    @db_handle_errors
    def archivia_possessore(self, possessore_id: int) -> bool:
        if not isinstance(possessore_id, int) or possessore_id <= 0:
            raise DBDataError(f"ID possessore non valido: {possessore_id}")
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"UPDATE {self.schema}.possessore "
                    "SET attivo = FALSE, archiviato_il = NOW() "
                    "WHERE id = %s AND attivo RETURNING id",
                    (possessore_id,)
                )
                if cur.fetchone() is None:
                    raise DBNotFoundError(
                        f"Possessore ID {possessore_id} non trovato o già archiviato.")
        self.logger.info(f"Possessore {possessore_id} archiviato.")
        return True

    @db_handle_errors
    def ripristina_possessore(self, possessore_id: int) -> bool:
        if not isinstance(possessore_id, int) or possessore_id <= 0:
            raise DBDataError(f"ID possessore non valido: {possessore_id}")
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"UPDATE {self.schema}.possessore "
                    "SET attivo = TRUE, archiviato_il = NULL "
                    "WHERE id = %s AND NOT attivo RETURNING id",
                    (possessore_id,)
                )
                if cur.fetchone() is None:
                    raise DBNotFoundError(
                        f"Possessore ID {possessore_id} non trovato o non archiviato.")
        self.logger.info(f"Possessore {possessore_id} ripristinato.")
        return True

    @db_handle_errors
    def get_archiviati_possessori(self) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            with conn.cursor(cursor_factory=DictCursor) as cur:
                cur.execute(
                    f"SELECT p.id, p.nome_completo, p.cognome_nome, p.paternita, "
                    f"c.nome AS comune_nome, p.archiviato_il "
                    f"FROM {self.schema}.possessore p "
                    f"LEFT JOIN {self.schema}.comune c ON p.comune_id = c.id "
                    f"WHERE NOT p.attivo ORDER BY p.archiviato_il DESC"
                )
                return [dict(r) for r in cur.fetchall()]

    # ─────────────────────────────────────────────────────────────────────────
    # LOCALITA
    # ─────────────────────────────────────────────────────────────────────────

    @db_handle_errors
    def archivia_localita(self, localita_id: int) -> bool:
        if not isinstance(localita_id, int) or localita_id <= 0:
            raise DBDataError(f"ID località non valido: {localita_id}")
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"UPDATE {self.schema}.localita "
                    "SET archiviato = TRUE, archiviato_il = NOW() "
                    "WHERE id = %s AND NOT archiviato RETURNING id",
                    (localita_id,)
                )
                if cur.fetchone() is None:
                    raise DBNotFoundError(
                        f"Località ID {localita_id} non trovata o già archiviata.")
        self.logger.info(f"Località {localita_id} archiviata.")
        return True

    @db_handle_errors
    def ripristina_localita(self, localita_id: int) -> bool:
        if not isinstance(localita_id, int) or localita_id <= 0:
            raise DBDataError(f"ID località non valido: {localita_id}")
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"UPDATE {self.schema}.localita "
                    "SET archiviato = FALSE, archiviato_il = NULL "
                    "WHERE id = %s AND archiviato RETURNING id",
                    (localita_id,)
                )
                if cur.fetchone() is None:
                    raise DBNotFoundError(
                        f"Località ID {localita_id} non trovata o non archiviata.")
        self.logger.info(f"Località {localita_id} ripristinata.")
        return True

    @db_handle_errors
    def get_archiviati_localita(self) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            with conn.cursor(cursor_factory=DictCursor) as cur:
                cur.execute(
                    f"SELECT l.id, l.nome, l.tipologia_stradale, "
                    f"c.nome AS comune_nome, l.archiviato_il "
                    f"FROM {self.schema}.localita l "
                    f"LEFT JOIN {self.schema}.comune c ON l.comune_id = c.id "
                    f"WHERE l.archiviato ORDER BY l.archiviato_il DESC"
                )
                return [dict(r) for r in cur.fetchall()]

    # ─────────────────────────────────────────────────────────────────────────
    # PARTITA
    # ─────────────────────────────────────────────────────────────────────────

    @db_handle_errors
    def archivia_partita(self, partita_id: int) -> bool:
        if not isinstance(partita_id, int) or partita_id <= 0:
            raise DBDataError(f"ID partita non valido: {partita_id}")
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"UPDATE {self.schema}.partita "
                    "SET archiviato = TRUE, archiviato_il = NOW() "
                    "WHERE id = %s AND NOT archiviato RETURNING id",
                    (partita_id,)
                )
                if cur.fetchone() is None:
                    raise DBNotFoundError(
                        f"Partita ID {partita_id} non trovata o già archiviata.")
        self.logger.info(f"Partita {partita_id} archiviata.")
        return True

    @db_handle_errors
    def ripristina_partita(self, partita_id: int) -> bool:
        if not isinstance(partita_id, int) or partita_id <= 0:
            raise DBDataError(f"ID partita non valido: {partita_id}")
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"UPDATE {self.schema}.partita "
                    "SET archiviato = FALSE, archiviato_il = NULL "
                    "WHERE id = %s AND archiviato RETURNING id",
                    (partita_id,)
                )
                if cur.fetchone() is None:
                    raise DBNotFoundError(
                        f"Partita ID {partita_id} non trovata o non archiviata.")
        self.logger.info(f"Partita {partita_id} ripristinata.")
        return True

    @db_handle_errors
    def get_archiviati_partite(self) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            with conn.cursor(cursor_factory=DictCursor) as cur:
                cur.execute(
                    f"SELECT p.id, p.numero_partita, p.suffisso_partita, p.stato, p.tipo, "
                    f"c.nome AS comune_nome, p.archiviato_il "
                    f"FROM {self.schema}.partita p "
                    f"JOIN {self.schema}.comune c ON p.comune_id = c.id "
                    f"WHERE p.archiviato ORDER BY p.archiviato_il DESC"
                )
                return [dict(r) for r in cur.fetchall()]

    # ─────────────────────────────────────────────────────────────────────────
    # AGGREGATO
    # ─────────────────────────────────────────────────────────────────────────

    def get_tutti_archiviati(self) -> Dict[str, List[Dict[str, Any]]]:
        """Ritorna tutti gli elementi archiviati raggruppati per tipo."""
        return {
            "comuni":     self.get_archiviati_comuni(),
            "possessori": self.get_archiviati_possessori(),
            "localita":   self.get_archiviati_localita(),
            "partite":    self.get_archiviati_partite(),
        }
