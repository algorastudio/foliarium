"""
db/variazioni.py — Mixin CRUD per Variazioni e Contratti.
Estratto da catasto_db_manager.py — mixin per CatastoDBManager.
"""

from __future__ import annotations
from datetime import date
from typing import Optional, List, Dict, Any

import psycopg2
from psycopg2.extras import DictCursor

from catasto_exceptions import DBNotFoundError
from db.base import db_handle_errors


class DBVariazioniMixin:
    """Mixin CRUD per Variazioni e Contratti."""

    @db_handle_errors
    def get_elenco_variazioni_per_esportazione(
        self, comune_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Recupera un elenco completo di variazioni, usando la vista aggiornata.

        TIER 1: @db_handle_errors centralizes exception handling.
        """
        query = f"SELECT * FROM {self.schema}.v_variazioni_complete"
        params = []

        if comune_id:
            comune_info = self.get_comune_by_id(comune_id)
            if comune_info and comune_info.get("nome_comune"):
                query += " WHERE partita_origine_comune = %s"
                params.append(comune_info["nome_comune"])
            else:
                raise DBNotFoundError(f"Comune con ID {comune_id} non trovato.")

        query += " ORDER BY data_variazione DESC;"

        with self._get_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                cur.execute(query, params)
                return [dict(row) for row in cur.fetchall()]

    @db_handle_errors
    def search_variazioni(
        self,
        tipo: Optional[str] = None,
        data_inizio: Optional[date] = None,
        data_fine: Optional[date] = None,
        partita_origine_id: Optional[int] = None,
        partita_destinazione_id: Optional[int] = None,
        comune_id: Optional[int] = None,
    ) -> List[Dict]:
        """Chiama la funzione SQL cerca_variazioni con tutti i filtri opzionali.

        TIER 1: @db_handle_errors centralizes exception handling.
        """
        query = "SELECT * FROM cerca_variazioni(%s, %s, %s, %s, %s, %s)"
        params = (
            tipo,
            data_inizio,
            data_fine,
            partita_origine_id,
            partita_destinazione_id,
            comune_id,
        )
        with self._get_connection() as conn:
            with conn.cursor(cursor_factory=DictCursor) as cur:
                cur.execute(query, params)
                return [dict(row) for row in cur.fetchall()]

    def update_variazione(self, variazione_id: int, **kwargs) -> bool:
        """Chiama la procedura SQL aggiorna_variazione. Il commit è automatico."""
        params = {
            "p_variazione_id": variazione_id,
            "p_tipo": kwargs.get("tipo"),
            "p_data_variazione": kwargs.get("data_variazione"),
            "p_numero_riferimento": kwargs.get("numero_riferimento"),
            "p_nominativo_riferimento": kwargs.get("nominativo_riferimento"),
        }
        call_proc = "CALL aggiorna_variazione(%(p_variazione_id)s, %(p_tipo)s, %(p_data_variazione)s, %(p_numero_riferimento)s, %(p_nominativo_riferimento)s)"
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(call_proc, params)
            self.logger.info(f"Variazione ID {variazione_id} aggiornata.")
            return True
        except psycopg2.Error as db_err:
            self.logger.error(
                f"Errore DB aggiornamento variazione ID {variazione_id}: {db_err}"
            )
            return False
        except Exception as e:
            self.logger.error(
                f"Errore Python aggiornamento variazione ID {variazione_id}: {e}"
            )
            return False

    def delete_variazione(
        self, variazione_id: int, force: bool = False, restore_partita: bool = False
    ) -> bool:
        """Chiama la procedura SQL elimina_variazione. Se restore_partita=True, riattiva la partita origine."""
        call_proc = "CALL elimina_variazione(%s, %s, %s)"
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(call_proc, (variazione_id, force, restore_partita))
            self.logger.info(f"Variazione ID {variazione_id} eliminata.")
            return True
        except psycopg2.Error as db_err:
            self.logger.error(
                f"Errore DB eliminazione variazione ID {variazione_id}: {db_err}"
            )
            return False
        except Exception as e:
            self.logger.error(
                f"Errore Python eliminazione variazione ID {variazione_id}: {e}"
            )
            return False

    def insert_contratto(
        self,
        variazione_id: int,
        tipo: str,
        data_contratto: date,
        notaio: Optional[str] = None,
        repertorio: Optional[str] = None,
        note: Optional[str] = None,
    ) -> bool:
        """Chiama la procedura SQL inserisci_contratto. Il commit è automatico."""
        call_proc = "CALL inserisci_contratto(%s, %s, %s, %s, %s, %s)"
        params = (variazione_id, tipo, data_contratto, notaio, repertorio, note)
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(call_proc, params)
            self.logger.info(f"Contratto inserito per variazione ID {variazione_id}.")
            return True
        except psycopg2.Error as db_err:
            # SQLSTATE P0001 = RAISE EXCEPTION dalla procedura SQL → contratto duplicato
            if (
                hasattr(db_err, "pgcode")
                and db_err.pgcode == "P0001"
                and "Esiste già un contratto" in str(db_err)
            ):
                self.logger.warning(
                    f"Contratto per variazione ID {variazione_id} esiste già."
                )
            else:
                self.logger.error(
                    f"Errore DB inserimento contratto var ID {variazione_id}: {db_err}"
                )
            return False

    def update_contratto(self, contratto_id: int, **kwargs) -> bool:
        """Chiama la procedura SQL aggiorna_contratto. Il commit è automatico."""
        params = {
            "p_id": contratto_id,
            "p_tipo": kwargs.get("tipo"),
            "p_data_contratto": kwargs.get("data_contratto"),
            "p_notaio": kwargs.get("notaio"),
            "p_repertorio": kwargs.get("repertorio"),
            "p_note": kwargs.get("note"),
        }
        call_proc = "CALL aggiorna_contratto(%(p_id)s, %(p_tipo)s, %(p_data_contratto)s, %(p_notaio)s, %(p_repertorio)s, %(p_note)s)"
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(call_proc, params)
            self.logger.info(f"Contratto ID {contratto_id} aggiornato.")
            return True
        except psycopg2.Error as db_err:
            self.logger.error(
                f"Errore DB aggiornamento contratto ID {contratto_id}: {db_err}"
            )
            return False
        except Exception as e:
            self.logger.error(
                f"Errore Python aggiornamento contratto ID {contratto_id}: {e}"
            )
            return False

    def delete_contratto(self, contratto_id: int) -> bool:
        """Chiama la procedura SQL elimina_contratto. Il commit è automatico."""
        call_proc = "CALL elimina_contratto(%s)"
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(call_proc, (contratto_id,))
            self.logger.info(f"Contratto ID {contratto_id} eliminato.")
            return True
        except psycopg2.Error as db_err:
            self.logger.error(
                f"Errore DB eliminazione contratto ID {contratto_id}: {db_err}"
            )
            return False
        except Exception as e:
            self.logger.error(
                f"Errore Python eliminazione contratto ID {contratto_id}: {e}"
            )
            return False
