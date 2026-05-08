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

# Nota: le classi Qt (QProgressDialog, QMessageBox) vengono importate in modo
# lazy all'interno di refresh_materialized_views() per evitare una dipendenza
# circolare tra il layer DB e il layer GUI, e per permettere l'import del modulo
# in ambienti headless (test CI senza display).

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

    def _get_base_tables_max_timestamp(self) -> Optional[datetime]:
        """
        TIER 3 Phase 1: Recupera il timestamp più recente di modifica tra tutte le tabelle base.
        Usato per determinare se un refresh delle MV è necessario.
        """
        query = f"""
            SELECT MAX(data_modifica) FROM (
                SELECT MAX(data_modifica) as data_modifica FROM {self.schema}.comune
                UNION ALL
                SELECT MAX(data_modifica) FROM {self.schema}.partita
                UNION ALL
                SELECT MAX(data_modifica) FROM {self.schema}.possessore
                UNION ALL
                SELECT MAX(data_modifica) FROM {self.schema}.immobile
                UNION ALL
                SELECT MAX(data_modifica) FROM {self.schema}.partita_possessore
                UNION ALL
                SELECT MAX(data_modifica) FROM {self.schema}.localita
            ) t;
        """
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(query)
                    result = cur.fetchone()
                    return result[0] if result and result[0] else None
        except Exception as e:
            self.logger.warning(f"Impossibile determinare timestamp base tables: {e}")
            return None

    def _should_refresh_materialized_views(self, min_interval_minutes: int = 10) -> bool:
        """
        TIER 3 Phase 1: Intelligent refresh check.
        Restituisce True se: (1) non mai aggiornate OR (2) > min_interval_minutes passati OR (3) base table modificate dopo ultimo refresh.
        """
        last_refresh = self.get_last_mv_refresh_timestamp()
        if last_refresh is None:
            self.logger.info("MV mai aggiornate; forziamo refresh.")
            return True

        from datetime import timedelta, timezone
        now_utc = datetime.now(timezone.utc).replace(tzinfo=None)
        if last_refresh.tzinfo is not None:
            last_refresh = last_refresh.replace(tzinfo=None)
        delta = now_utc - last_refresh

        if delta >= timedelta(minutes=min_interval_minutes):
            self.logger.info(f"MV refresh interval ({delta.total_seconds():.0f}s) >= {min_interval_minutes}min; refresh richiesto.")
            return True

        last_data_change = self._get_base_tables_max_timestamp()
        if last_data_change:
            if last_data_change.tzinfo is not None:
                last_data_change = last_data_change.replace(tzinfo=None)
        if last_data_change and last_data_change > last_refresh:
            self.logger.info(f"Dati modificati dopo ultimo refresh ({last_data_change} > {last_refresh}); refresh richiesto.")
            return True

        self.logger.info(f"MV non necessitano refresh (intervallo: {delta.total_seconds():.0f}s, nessuna modifica)")
        return False

    def refresh_materialized_views(self, show_success_message: bool = False, force: bool = False, concurrent: bool = True) -> bool:
        """
        TIER 3 Phase 1: Aggiorna viste materializzate in modo intelligente.
        - force=True: ignora il check sulla necessità di refresh
        - concurrent=True: usa CONCURRENTLY per refresh non-bloccante (se disponibile)
        """
        from PyQt6.QtWidgets import QApplication, QProgressDialog, QMessageBox
        from PyQt6.QtCore import Qt

        if not self.pool:
            self.logger.error("Pool di connessioni non inizializzato.")
            QMessageBox.critical(None, "Errore", "Pool di connessioni non attivo.")
            return False

        if not force and not self._should_refresh_materialized_views():
            self.logger.info("Refresh MV saltato (non necessario).")
            return True

        progress_dialog = QProgressDialog("Aggiornamento viste materializzate...", "Annulla", 0, 0, None)
        progress_dialog.setWindowModality(Qt.WindowModality.WindowModal)
        progress_dialog.setCancelButton(None)
        progress_dialog.show()
        QApplication.processEvents()

        concurrent_str = "CONCURRENTLY" if concurrent else ""
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
                    EXECUTE 'REFRESH MATERIALIZED VIEW {concurrent_str} ' || quote_ident(r.schemaname)
                    || '.' || quote_ident(r.matviewname);
                END LOOP;
            END $$;
        """

        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    self.logger.info("Esecuzione refresh materialized views...")
                    cur.execute(query)
                    self.update_last_mv_refresh_timestamp()
                    progress_dialog.close()

            if show_success_message:
                QMessageBox.information(None, "Successo", "Viste materializzate aggiornate con successo.")
            self.logger.info("Viste materializzate aggiornate con successo.")
            return True

        except psycopg2.Error as db_err:
            progress_dialog.close()
            if "CONCURRENTLY" in str(db_err) and concurrent:
                self.logger.warning("CONCURRENTLY non supportato; retry senza...")
                return self.refresh_materialized_views(show_success_message, force=True, concurrent=False)
            error_message = f"Errore DB durante aggiornamento MV: {db_err}"
            self.logger.error(error_message, exc_info=True)
            QMessageBox.critical(None, "Errore", error_message)
            return False
        except Exception as e:
            progress_dialog.close()
            error_message = f"Errore critico: {e}"
            self.logger.error(error_message, exc_info=True)
            QMessageBox.critical(None, "Errore", error_message)
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

