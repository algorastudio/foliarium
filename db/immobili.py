"""
db/immobili.py — Mixin CRUD per Immobili.
Estratto da catasto_db_manager.py — mixin per CatastoDBManager.
"""

from __future__ import annotations
import logging
from typing import Optional, List, Dict, Any, TYPE_CHECKING

import psycopg2
from psycopg2.extras import DictCursor

from catasto_exceptions import DBMError, DBUniqueConstraintError, DBNotFoundError, DBDataError
from db.base import db_handle_errors

if TYPE_CHECKING:
    from catasto_db_manager import CatastoDBManager


class DBImmobiliMixin:
    """Mixin CRUD per Immobili."""

    @db_handle_errors
    def get_elenco_immobili_per_esportazione(self, comune_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """Recupera un elenco completo di immobili per l'esportazione.

        TIER 1: @db_handle_errors centralizes exception handling.
        """
        query = f"""
            SELECT
                i.id AS id_immobile, i.natura, i.classificazione, i.consistenza,
                i.numero_piani, i.numero_vani, l.nome AS localita_nome,
                l.tipologia_stradale, p.numero_partita,
                p.suffisso_partita, c.nome AS comune_nome
            FROM {self.schema}.immobile i
            JOIN {self.schema}.partita p ON i.partita_id = p.id
            JOIN {self.schema}.comune c ON p.comune_id = c.id
            JOIN {self.schema}.localita l ON i.localita_id = l.id
        """
        params = []
        if comune_id:
            query += " WHERE p.comune_id = %s"
            params.append(comune_id)
        query += " ORDER BY c.nome, p.numero_partita, l.nome, i.natura;"
        with self._get_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                cur.execute(query, params)
                return [dict(row) for row in cur.fetchall()]

    @db_handle_errors
    def search_immobili(self, partita_id: Optional[int] = None, comune_id: Optional[int] = None,
                        localita_id: Optional[int] = None, natura: Optional[str] = None,
                        classificazione: Optional[str] = None) -> List[Dict]:
        """Chiama la funzione SQL cerca_immobili con filtri opzionali su partita, comune, località, natura.

        TIER 1: @db_handle_errors centralizes exception handling.
        """
        query = "SELECT * FROM cerca_immobili(%s, %s, %s, %s, %s)"
        params = (partita_id, comune_id, localita_id, natura, classificazione)
        with self._get_connection() as conn:
            with conn.cursor(cursor_factory=DictCursor) as cur:
                cur.execute(query, params)
                return [dict(row) for row in cur.fetchall()]

    def update_immobile(self, immobile_id: int, **kwargs) -> bool:
        """Chiama la procedura SQL aggiorna_immobile. Il commit è automatico."""
        params = {'p_id': immobile_id, 'p_natura': kwargs.get('natura'), 'p_numero_piani': kwargs.get('numero_piani'),
                  'p_numero_vani': kwargs.get('numero_vani'), 'p_consistenza': kwargs.get('consistenza'),
                  'p_classificazione': kwargs.get('classificazione'), 'p_localita_id': kwargs.get('localita_id')}
        call_proc = "CALL aggiorna_immobile(%(p_id)s, %(p_natura)s, %(p_numero_piani)s, %(p_numero_vani)s, %(p_consistenza)s, %(p_classificazione)s, %(p_localita_id)s)"
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(call_proc, params)
            self.logger.info(f"Immobile ID {immobile_id} aggiornato.")
            return True
        except psycopg2.Error as db_err: self.logger.error(f"Errore DB aggiornamento immobile ID {immobile_id}: {db_err}"); return False
        except Exception as e: self.logger.error(f"Errore Python aggiornamento immobile ID {immobile_id}: {e}"); return False

    def delete_immobile(self, immobile_id: int) -> bool:
        """
        Elimina un immobile tramite la funzione SQL delete_immobile_by_id.
        Il commit e il rollback sono gestiti automaticamente dal context manager _get_connection.
        """
        call_proc = f"SELECT {self.schema}.delete_immobile_by_id(%s);"
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(call_proc, (immobile_id,))
            self.logger.info(f"Immobile ID {immobile_id} eliminato con successo.")
            return True
        except Exception as e:
            self.logger.error(f"Errore durante l'eliminazione dell'immobile ID {immobile_id}: {e}")
            return False

    def transfer_immobile(self, immobile_id: int, nuova_partita_id: int, registra_variazione: bool = False) -> bool:
        """
        Chiama la procedura SQL per trasferire un immobile a una nuova partita in modo transazionale.
        """
        call_proc_str = f"CALL {self.schema}.trasferisci_immobile(%s, %s, %s);"
        params = (immobile_id, nuova_partita_id, registra_variazione)
        
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    self.logger.info(f"Trasferimento immobile ID {immobile_id} a partita ID {nuova_partita_id}...")
                    cur.execute(call_proc_str, params)
            
            # Il commit è automatico qui se la procedura non ha sollevato eccezioni
            self.logger.info(f"Immobile ID {immobile_id} trasferito con successo.")
            return True
            
        except psycopg2.Error as db_err:
            # Il rollback è automatico
            pgerror_msg = getattr(db_err, 'pgerror', str(db_err))
            self.logger.error(f"Errore DB durante trasferimento immobile ID {immobile_id}: {pgerror_msg}", exc_info=True)
            raise DBMError(f"Errore database durante il trasferimento: {pgerror_msg}") from db_err
        except Exception as e:
            self.logger.error(f"Errore imprevisto durante trasferimento immobile ID {immobile_id}: {e}", exc_info=True)
            raise DBMError(f"Errore di sistema imprevisto durante il trasferimento: {e}") from e

    @db_handle_errors
    def get_immobile_details(self, immobile_id: int) -> Optional[Dict[str, Any]]:
        """Recupera i dettagli completi di un singolo immobile in modo sicuro.

        TIER 1: @db_handle_errors centralizes exception handling.
        """
        if not isinstance(immobile_id, int) or immobile_id <= 0:
            raise DBDataError(f"ID immobile non valido: {immobile_id}")

        query = f"""
            SELECT
                i.id, i.partita_id, i.localita_id, i.natura, i.classificazione, i.consistenza,
                i.numero_piani, i.numero_vani,
                p.numero_partita, p.suffisso_partita,
                c.nome AS comune_nome,
                l.nome AS localita_nome, l.tipologia_stradale
            FROM {self.schema}.immobile i
            JOIN {self.schema}.partita p ON i.partita_id = p.id
            JOIN {self.schema}.comune c ON p.comune_id = c.id
            JOIN {self.schema}.localita l ON i.localita_id = l.id
            WHERE i.id = %s;
        """
        with self._get_connection() as conn:
            with conn.cursor(cursor_factory=DictCursor) as cur:
                cur.execute(query, (immobile_id,))
                immobile_data = cur.fetchone()
                if immobile_data:
                    return dict(immobile_data)
                else:
                    raise DBNotFoundError(f"Immobile con ID {immobile_id} non trovato.")

    @db_handle_errors
    def get_immobili_per_tipologia(self, comune_id: Optional[int] = None, limit: int = 100) -> List[Dict[str, Any]]:
        """Recupera dati dalla vista materializzata mv_immobili_per_tipologia in modo sicuro.

        TIER 1: @db_handle_errors centralizes exception handling.
        """
        if comune_id is not None:
            query = f"""
                SELECT m.* FROM {self.schema}.mv_immobili_per_tipologia m
                JOIN {self.schema}.comune c ON m.comune_nome = c.nome
                WHERE c.id = %s
                ORDER BY m.comune_nome, m.classificazione LIMIT %s;
            """
            params = [comune_id, limit]
        else:
            query = f"SELECT * FROM {self.schema}.mv_immobili_per_tipologia ORDER BY comune_nome, classificazione LIMIT %s;"
            params = [limit]

        with self._get_connection() as conn:
            with conn.cursor(cursor_factory=DictCursor) as cur:
                cur.execute(query, tuple(params))
                return [dict(row) for row in cur.fetchall()]

