"""
db/localita.py — Mixin CRUD per Località e Tipi Località.
Estratto da catasto_db_manager.py — mixin per CatastoDBManager.
"""

from __future__ import annotations
import logging
from typing import Optional, List, Dict, Any, Union, TYPE_CHECKING

import psycopg2
from psycopg2.extras import DictCursor

from catasto_exceptions import DBMError, DBUniqueConstraintError, DBNotFoundError, DBDataError
from db.base import db_handle_errors

if TYPE_CHECKING:
    from catasto_db_manager import CatastoDBManager


class DBLocalitaMixin:
    """Mixin CRUD per Località e Tipi Località."""

    @db_handle_errors
    def get_tipi_localita(self) -> List[Dict[str, Any]]:
        """Recupera tutte le tipologie di località disponibili.

        TIER 1: @db_handle_errors centralizes exception handling.
        TIER 3 Phase 4: Cached (immutable reference data).
        """
        def _fetch():
            query = "SELECT id, nome, descrizione FROM catasto.tipo_localita ORDER BY nome;"
            with self._get_connection() as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                    cur.execute(query)
                    return [dict(row) for row in cur.fetchall()]
        try:
            return self._try_with_cache("tipi_localita", _fetch)
        except Exception as e:
            self.logger.error(f"Errore in get_tipi_localita: {e}", exc_info=True)
            return []

    def gestisci_tipo_localita(self, tipo_id: Optional[int], nome: str, descrizione: Optional[str] = None) -> int:
        """Crea o aggiorna una tipologia di località."""
        if not nome or not nome.strip():
            raise DBDataError("Il nome della tipologia non può essere vuoto.")
        
        nome = nome.strip()
        descrizione = descrizione.strip() if descrizione else None

        if tipo_id: # Modalità aggiornamento
            query = "UPDATE catasto.tipo_localita SET nome = %s, descrizione = %s WHERE id = %s RETURNING id;"
            params = (nome, descrizione, tipo_id)
        else: # Modalità inserimento
            query = "INSERT INTO catasto.tipo_localita (nome, descrizione) VALUES (%s, %s) ON CONFLICT (nome) DO NOTHING RETURNING id;"
            params = (nome, descrizione)
        
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(query, params)
                    result = cur.fetchone()
                    if result:
                        return result[0]
                    # Se ON CONFLICT non ha fatto nulla, l'ID non viene restituito. Potremmo voler gestire questo caso.
                    raise DBUniqueConstraintError(f"Una tipologia con nome '{nome}' esiste già.")
        except psycopg2.errors.UniqueViolation:
            raise DBUniqueConstraintError(f"Una tipologia con nome '{nome}' esiste già.") from None
        except Exception as e:
            self.logger.error(f"Errore in gestisci_tipo_localita: {e}", exc_info=True)
            raise DBMError("Operazione sulla tipologia di località fallita.") from e

    def elimina_tipo_localita(self, tipo_id: int) -> bool:
        """Elimina una tipologia di località, solo se non è utilizzata."""
        query = "DELETE FROM catasto.tipo_localita WHERE id = %s;"
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(query, (tipo_id,))
                    return cur.rowcount > 0
        except psycopg2.errors.ForeignKeyViolation:
            raise DBMError("Impossibile eliminare: questa tipologia è utilizzata da una o più località.") from None
        except Exception as e:
            self.logger.error(f"Errore in elimina_tipo_localita: {e}", exc_info=True)
            raise DBMError("Eliminazione della tipologia fallita.") from e

    @db_handle_errors
    def get_elenco_localita_per_esportazione(self, comune_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """Recupera un elenco completo di località per l'esportazione (civico incorporato nel nome da v1.6.1).

        TIER 1: @db_handle_errors centralizes exception handling.
        """
        query = f"""
            SELECT l.id, l.nome, l.tipologia_stradale, c.nome AS comune_nome
            FROM {self.schema}.localita l
            JOIN {self.schema}.comune c ON l.comune_id = c.id
        """
        params = []
        if comune_id:
            query += " WHERE l.comune_id = %s AND NOT l.archiviato"
            params.append(comune_id)
        else:
            query += " WHERE NOT l.archiviato"
        query += " ORDER BY c.nome, l.nome;"
        with self._get_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                cur.execute(query, params)
                return [dict(row) for row in cur.fetchall()]

    def get_localita_by_comune(self, comune_id: int, filter_text: Optional[str] = None) -> List[Dict[str, Any]]:
        """Recupera località per comune_id (civico incorporato nel nome da v1.6.1)."""
        if not isinstance(comune_id, int) or comune_id <= 0:
            raise DBDataError("ID comune non valido.")

        query_base = f"""
            SELECT
                loc.id,
                loc.nome,
                loc.tipologia_stradale
            FROM {self.schema}.localita loc
            WHERE loc.comune_id = %s AND NOT loc.archiviato
        """

        params: List[Union[int, str]] = [comune_id]

        if filter_text:
            query_base += " AND loc.nome ILIKE %s"
            params.append(f"%{filter_text}%")

        query = query_base + " ORDER BY loc.nome;"

        try:
            with self._get_connection() as conn:
                with conn.cursor(cursor_factory=DictCursor) as cur:
                    cur.execute(query, tuple(params))
                    results = [dict(row) for row in cur.fetchall()]
                    self.logger.info(f"Recuperate {len(results)} località per comune ID {comune_id} (filtro: '{filter_text}').")
                    return results
        except Exception as e:
            self.logger.error(f"Errore DB in get_localita_by_comune: {e}", exc_info=True)
            return [] # Restituisce lista vuota in caso di errore

    def insert_localita(self, comune_id: int, nome: str, tipologia_stradale: str) -> int:
        """
        Inserisce una nuova località. Da v1.7.0 il nome NON contiene il civico
        (es. 'Repubblica') e la tipologia_stradale è obbligatoria.
        Univoco per (comune_id, nome, tipologia_stradale).
        """
        if not all([isinstance(comune_id, int), comune_id > 0, isinstance(nome, str), nome.strip()]):
            raise DBDataError("Parametri per l'inserimento della località non validi.")
        if not (isinstance(tipologia_stradale, str) and tipologia_stradale.strip()):
            raise DBDataError("La tipologia stradale è obbligatoria (es. Via, Piazza, Borgata).")

        query_insert = (
            f"INSERT INTO {self.schema}.localita (comune_id, nome, tipologia_stradale) "
            f"VALUES (%s, %s, %s) "
            f"ON CONFLICT (comune_id, nome, tipologia_stradale) DO NOTHING RETURNING id;"
        )
        query_select = (
            f"SELECT id FROM {self.schema}.localita "
            f"WHERE comune_id = %s AND nome = %s AND tipologia_stradale = %s;"
        )

        try:
            with self._get_connection() as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                    cur.execute(query_insert, (comune_id, nome.strip(), tipologia_stradale.strip()))
                    insert_result = cur.fetchone()

                    if insert_result and insert_result['id']:
                        localita_id = insert_result['id']
                        self.logger.info(f"Località '{tipologia_stradale} {nome}' inserita con successo. ID: {localita_id}.")
                    else: # Conflitto, recupera l'ID esistente
                        cur.execute(query_select, (comune_id, nome.strip(), tipologia_stradale.strip()))
                        select_result = cur.fetchone()
                        if select_result and select_result['id']:
                            localita_id = select_result['id']
                            self.logger.info(f"Località '{tipologia_stradale} {nome}' già esistente trovata. ID: {localita_id}.")
                        else:
                            raise DBMError(f"Logica inconsistente: impossibile inserire o trovare la località '{nome}'.")
            return localita_id
        except Exception as e:
            self.logger.error(f"Errore in insert_localita per '{nome}': {e}", exc_info=True)
            raise DBMError(f"Errore database durante l'operazione sulla località: {e}") from e

    @db_handle_errors
    def get_localita_details(self, localita_id: int) -> Optional[Dict[str, Any]]:
        """Recupera i dettagli di una singola località (civico incorporato nel nome da v1.6.1).

        TIER 1: @db_handle_errors centralizes exception handling.
        """
        if not isinstance(localita_id, int) or localita_id <= 0:
            raise DBDataError(f"ID località non valido: {localita_id}")

        query = f"""
            SELECT loc.id, loc.nome, loc.tipologia_stradale, loc.comune_id, com.nome AS comune_nome
            FROM {self.schema}.localita loc
            JOIN {self.schema}.comune com ON loc.comune_id = com.id
            WHERE loc.id = %s;
        """
        with self._get_connection() as conn:
            with conn.cursor(cursor_factory=DictCursor) as cur:
                cur.execute(query, (localita_id,))
                result = cur.fetchone()
                if result:
                    return dict(result)
                else:
                    raise DBNotFoundError(f"Località con ID {localita_id} non trovata.")

    @db_handle_errors
    def update_localita(self, localita_id: int, dati_modificati: Dict[str, Any]):
        """Aggiorna i dati di una località esistente (civico incorporato nel nome da v1.6.1).

        TIER 1: @db_handle_errors centralizes exception handling.
        """
        if not (isinstance(localita_id, int) and localita_id > 0):
            raise DBDataError("ID località non valido.")
        if not isinstance(dati_modificati, dict) or not dati_modificati:
            raise DBDataError("Dati per aggiornamento non validi.")

        set_clauses = []
        params = []

        if "nome" in dati_modificati and dati_modificati["nome"] and dati_modificati["nome"].strip():
            set_clauses.append("nome = %s")
            params.append(dati_modificati["nome"].strip())

        if "tipologia_stradale" in dati_modificati:
            tip = dati_modificati["tipologia_stradale"]
            if not (isinstance(tip, str) and tip.strip()):
                raise DBDataError("La tipologia stradale è obbligatoria e non può essere vuota.")
            set_clauses.append("tipologia_stradale = %s")
            params.append(tip.strip())

        if not set_clauses:
            return

        set_clauses.append("data_modifica = CURRENT_TIMESTAMP")
        query = f"UPDATE {self.schema}.localita SET {', '.join(set_clauses)} WHERE id = %s;"
        params.append(localita_id)

        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, tuple(params))
                if cur.rowcount == 0:
                    raise DBNotFoundError(f"Nessuna località trovata con ID {localita_id} da aggiornare.")

