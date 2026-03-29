"""
db/stats.py — Mixin per statistiche, dashboard e materialized views.
Estratto da catasto_db_manager.py — mixin per CatastoDBManager.
"""

from __future__ import annotations
import logging
from typing import Optional, List, Dict, Any, TYPE_CHECKING

from datetime import date, datetime
import psycopg2
from psycopg2.extras import DictCursor

from catasto_exceptions import DBMError, DBUniqueConstraintError, DBNotFoundError, DBDataError

if TYPE_CHECKING:
    from catasto_db_manager import CatastoDBManager


class DBStatsMixin:
    """Mixin per statistiche, dashboard e materialized views."""

    def get_statistiche_comune(self) -> List[Dict[str, Any]]:
        """Recupera dati dalla vista materializzata mv_statistiche_comune in modo sicuro."""
        def _fetch():
            query = f"SELECT * FROM {self.schema}.mv_statistiche_comune ORDER BY comune;"
            with self._get_connection() as conn:
                with conn.cursor(cursor_factory=DictCursor) as cur:
                    cur.execute(query)
                    results = [dict(row) for row in cur.fetchall()]
                    self.logger.info(f"Recuperate {len(results)} righe da mv_statistiche_comune.")
                    return results
        try:
            return self._try_with_cache("statistiche_comune", _fetch)
        except Exception as e:
            self.logger.error(f"Errore DB in get_statistiche_comune: {e}", exc_info=True)
            return []

    def get_dashboard_stats(self) -> Dict[str, int]:
        """Recupera le statistiche di base per la dashboard in un'unica query."""
        stats = {
            "total_comuni": 0,
            "total_partite": 0,
            "total_possessori": 0,
            "total_immobili": 0,
        }
        query = f"""
            SELECT 
                (SELECT COUNT(*) FROM {self.schema}.comune) AS total_comuni,
                (SELECT COUNT(*) FROM {self.schema}.partita) AS total_partite,
                (SELECT COUNT(*) FROM {self.schema}.possessore) AS total_possessori,
                (SELECT COUNT(*) FROM {self.schema}.immobile) AS total_immobili;
        """
        try:
            with self._get_connection() as conn:
                with conn.cursor(cursor_factory=DictCursor) as cur:
                    cur.execute(query)
                    result = cur.fetchone()
                    if result:
                        stats.update(dict(result))
            return stats
        except Exception as e:
            self.logger.error(f"Errore durante il recupero delle statistiche per la dashboard: {e}", exc_info=True)
            return stats # Restituisce il dizionario con gli zeri in caso di errore

    def get_ultimi_inserimenti_dashboard(self, limit: int = 3) -> Dict[str, List[Dict]]:
        """Recupera gli ultimi N record inseriti per comuni, partite e possessori."""
        result = {"comuni": [], "partite": [], "possessori": []}
        try:
            with self._get_connection() as conn:
                with conn.cursor(cursor_factory=DictCursor) as cur:
                    cur.execute(
                        f"SELECT nome, provincia FROM {self.schema}.comune ORDER BY id DESC LIMIT %s",
                        (limit,)
                    )
                    result["comuni"] = [dict(r) for r in cur.fetchall()]
                    cur.execute(
                        f"""SELECT p.numero_partita, c.nome AS comune
                            FROM {self.schema}.partita p
                            JOIN {self.schema}.comune c ON p.comune_id = c.id
                            ORDER BY p.id DESC LIMIT %s""",
                        (limit,)
                    )
                    result["partite"] = [dict(r) for r in cur.fetchall()]
                    cur.execute(
                        f"SELECT cognome_nome, nome_completo FROM {self.schema}.possessore ORDER BY id DESC LIMIT %s",
                        (limit,)
                    )
                    result["possessori"] = [dict(r) for r in cur.fetchall()]
        except Exception as e:
            self.logger.warning(f"get_ultimi_inserimenti_dashboard: {e}")
        return result

    def get_last_mv_refresh_timestamp(self) -> Optional[datetime]:
        """Recupera il timestamp dell'ultimo aggiornamento delle viste materializzate."""
        query = f"SELECT value_timestamp FROM {self.schema}.app_metadata WHERE key = 'last_mv_refresh';"
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(query)
                    result = cur.fetchone()
                    return result[0] if result else None
        except psycopg2.errors.UndefinedTable:
            self.logger.warning("Tabella 'app_metadata' non trovata. Creare la tabella per la funzionalità di refresh intelligente.")
            return None # La tabella potrebbe non esistere ancora
        except Exception as e:
            self.logger.error(f"Errore nel recuperare il timestamp di refresh: {e}", exc_info=True)
            return None

    def update_last_mv_refresh_timestamp(self):
        """Aggiorna il timestamp dell'ultimo refresh delle viste al tempo attuale (UTC)."""
        # Usiamo un "UPSERT" per inserire la chiave se non esiste, o aggiornarla se esiste.
        query = f"""
            INSERT INTO {self.schema}.app_metadata (key, value_timestamp)
            VALUES ('last_mv_refresh', NOW() at time zone 'utc')
            ON CONFLICT (key) DO UPDATE SET value_timestamp = EXCLUDED.value_timestamp;
        """
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(query)
            self.logger.info("Timestamp di aggiornamento viste materializzate aggiornato con successo.")
        except Exception as e:
            self.logger.error(f"Errore nell'aggiornare il timestamp di refresh: {e}", exc_info=True)

    def refresh_materialized_views(self, show_success_message: bool = False) -> bool:
        """Aggiorna tutte le viste materializzate del database in modo sicuro."""
        if not self.pool:
            self.logger.error("Pool di connessioni non inizializzato per refresh viste materializzate.")
            QMessageBox.critical(None, "Errore", "Pool di connessioni non attivo. Impossibile aggiornare le viste.")
            return False
        
        progress_dialog = QProgressDialog("Aggiornamento viste materializzate in corso...", "Annulla", 0, 0, None)
        progress_dialog.setWindowModality(Qt.WindowModality.WindowModal)
        progress_dialog.setCancelButton(None)
        progress_dialog.show()
        QApplication.processEvents()

        # --- CORREZIONE QUI: Rimosso CONCURRENTLY per compatibilità universale ---
        query = f"""
            DO $$
            DECLARE
                r RECORD;
            BEGIN
                FOR r IN
                    SELECT schemaname, matviewname
                    FROM pg_matviews
                    WHERE schemaname = '{self.schema}'
                LOOP
                    EXECUTE 'REFRESH MATERIALIZED VIEW ' || quote_ident(r.schemaname) 
                    || '.' || quote_ident(r.matviewname);
                END LOOP;
            END $$;
        """
        # --- FINE CORREZIONE ---
        
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    self.logger.info("Esecuzione dello script di aggiornamento per le viste materializzate...")
                    cur.execute(query)
                    # --- AGGIUNGERE QUESTA RIGA ALLA FINE DEL BLOCCO 'try' ---
                    self.update_last_mv_refresh_timestamp() # Aggiorna il timestamp dopo il successo
                    # --- FINE AGGIUNTA ---
                
                    progress_dialog.close()
            if show_success_message:
                QMessageBox.information(None, "Successo", "Tutte le viste materializzate sono state aggiornate con successo.")
            
            self.logger.info("Viste materializzate aggiornate con successo.")
            return True
            
        except psycopg2.Error as db_err:
            progress_dialog.close()
            error_message = f"Errore DB durante l'aggiornamento delle viste: {db_err}"
            self.logger.error(error_message, exc_info=True)
            QMessageBox.critical(None, "Errore Aggiornamento Viste", error_message)
            return False
        except Exception as e:
            progress_dialog.close()
            error_message = f"Errore critico durante l'aggiornamento delle viste: {e}"
            self.logger.error(error_message, exc_info=True)
            QMessageBox.critical(None, "Errore Aggiornamento Viste", error_message)
            return False

    def genera_report_consultazioni(self, data_inizio: Optional[date] = None, 
                                data_fine: Optional[date] = None,
                                richiedente: Optional[str] = None) -> str:
        """Chiama la funzione SQL catasto.genera_report_consultazioni in modo sicuro."""
        query = f"SELECT {self.schema}.genera_report_consultazioni(%s, %s, %s);"
        params = (data_inizio, data_fine, richiedente)
        
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    self.logger.debug(f"Esecuzione genera_report_consultazioni con filtri: {params}")
                    cur.execute(query, params)
                    result = cur.fetchone()
                    if result and result[0] is not None:
                        self.logger.info("Report consultazioni generato.")
                        return str(result[0])
                    else:
                        self.logger.warning("Nessun report consultazioni generato o risultato NULL.")
                        return "Nessun dato trovato per i criteri specificati."
        except Exception as e:
            self.logger.error(f"Errore in genera_report_consultazioni: {e}", exc_info=True)
            return "Errore durante la generazione del report."

    def genera_report_possessore(self, possessore_id: int) -> Optional[str]:
        """Chiama la funzione SQL catasto.genera_report_possessore in modo sicuro."""
        if not isinstance(possessore_id, int) or possessore_id <= 0:
            self.logger.error(f"ID possessore non valido: {possessore_id}")
            return None
                
        query = f"SELECT {self.schema}.genera_report_possessore(%s);"
        
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(query, (possessore_id,))
                    result = cur.fetchone()
                    return str(result[0]) if result and result[0] is not None else None
        except Exception as e:
            self.logger.error(f"Errore DB in genera_report_possessore (ID: {possessore_id}): {e}", exc_info=True)
            return None

