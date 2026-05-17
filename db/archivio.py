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
  elimina_definitivamente_*() → DELETE su elementi gia' archiviati (hard delete)
"""
from __future__ import annotations

from typing import Any, Dict, List

from psycopg2.extras import DictCursor
from psycopg2 import IntegrityError

from catasto_exceptions import DBDataError, DBMError, DBNotFoundError
from db.base import db_handle_errors



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
        # archiviato_il IS NOT NULL distingue gli archiviati dagli inattivi storici
        with self._get_connection() as conn:
            with conn.cursor(cursor_factory=DictCursor) as cur:
                cur.execute(
                    f"SELECT p.id, p.nome_completo, p.cognome_nome, p.paternita, "
                    f"c.nome AS comune_nome, p.archiviato_il "
                    f"FROM {self.schema}.possessore p "
                    f"LEFT JOIN {self.schema}.comune c ON p.comune_id = c.id "
                    f"WHERE NOT p.attivo AND p.archiviato_il IS NOT NULL "
                    f"ORDER BY p.archiviato_il DESC"
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
    # ELIMINAZIONE DEFINITIVA (hard delete su elementi già archiviati)
    # ─────────────────────────────────────────────────────────────────────────

    @db_handle_errors
    def elimina_definitivamente_comune(self, comune_id: int) -> bool:
        if not isinstance(comune_id, int) or comune_id <= 0:
            raise DBDataError(f"ID comune non valido: {comune_id}")
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        f"DELETE FROM {self.schema}.comune "
                        "WHERE id = %s AND archiviato RETURNING id",
                        (comune_id,)
                    )
                    if cur.fetchone() is None:
                        raise DBNotFoundError(
                            f"Comune ID {comune_id} non archiviato o non trovato. "
                            "Solo elementi archiviati possono essere eliminati definitivamente.")
        except IntegrityError as e:
            if "partita_comune_id_fkey" in str(e):
                raise DBMError(
                    f"Impossibile eliminare il comune: esistono ancora partite "
                    "che lo referenziano. Elimina prima le partite correlate."
                )
            raise
        self.logger.info(f"Comune {comune_id} eliminato definitivamente.")
        return True

    @db_handle_errors
    def elimina_definitivamente_possessore(self, possessore_id: int) -> bool:
        if not isinstance(possessore_id, int) or possessore_id <= 0:
            raise DBDataError(f"ID possessore non valido: {possessore_id}")
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        f"DELETE FROM {self.schema}.possessore "
                        "WHERE id = %s AND NOT attivo AND archiviato_il IS NOT NULL "
                        "RETURNING id",
                        (possessore_id,)
                    )
                    if cur.fetchone() is None:
                        raise DBNotFoundError(
                            f"Possessore ID {possessore_id} non archiviato o non trovato.")
        except IntegrityError as e:
            if "legame_possesso" in str(e) or "legame" in str(e).lower():
                raise DBMError(
                    f"Impossibile eliminare il possessore: è ancora collegato a partite "
                    "(attraverso legami di possesso). Elimina prima i legami."
                )
            raise
        self.logger.info(f"Possessore {possessore_id} eliminato definitivamente.")
        return True

    @db_handle_errors
    def elimina_definitivamente_localita(self, localita_id: int) -> bool:
        if not isinstance(localita_id, int) or localita_id <= 0:
            raise DBDataError(f"ID località non valido: {localita_id}")
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        f"DELETE FROM {self.schema}.localita "
                        "WHERE id = %s AND archiviato RETURNING id",
                        (localita_id,)
                    )
                    if cur.fetchone() is None:
                        raise DBNotFoundError(
                            f"Località ID {localita_id} non archiviata o non trovata.")
        except IntegrityError as e:
            if "immobile" in str(e).lower():
                raise DBMError(
                    f"Impossibile eliminare la località: è ancora collegata a immobili. "
                    "Elimina prima gli immobili correlati."
                )
            raise
        self.logger.info(f"Località {localita_id} eliminata definitivamente.")
        return True

    @db_handle_errors
    def elimina_definitivamente_partita(self, partita_id: int) -> bool:
        if not isinstance(partita_id, int) or partita_id <= 0:
            raise DBDataError(f"ID partita non valido: {partita_id}")
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        f"DELETE FROM {self.schema}.partita "
                        "WHERE id = %s AND archiviato RETURNING id",
                        (partita_id,)
                    )
                    if cur.fetchone() is None:
                        raise DBNotFoundError(
                            f"Partita ID {partita_id} non archiviata o non trovata.")
        except IntegrityError as e:
            if "immobile" in str(e).lower():
                raise DBMError(
                    f"Impossibile eliminare la partita: contiene ancora immobili. "
                    "Elimina prima gli immobili correlati."
                )
            elif "variazione" in str(e).lower():
                raise DBMError(
                    f"Impossibile eliminare la partita: è referenziata da variazioni. "
                    "Elimina prima le variazioni correlate."
                )
            elif "legame" in str(e).lower():
                raise DBMError(
                    f"Impossibile eliminare la partita: ha ancora legami di possesso. "
                    "Elimina prima i legami."
                )
            raise
        self.logger.info(f"Partita {partita_id} eliminata definitivamente.")
        return True

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
