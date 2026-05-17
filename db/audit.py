"""
db/audit.py — Mixin per audit, sessioni, log e consultazioni.
Estratto da catasto_db_manager.py — mixin per CatastoDBManager.
"""

from __future__ import annotations
import logging
from datetime import date, datetime
from typing import Optional, List, Dict, Any, Tuple

import psycopg2
from psycopg2.extras import DictCursor

from catasto_exceptions import DBMError, DBDataError


# Messaggio mostrato (una sola volta per processo) quando la vista
# v_audit_dettagliato manca: indica come applicare la migrazione 19.
_MISSING_AUDIT_VIEW_MSG = (
    "La vista 'catasto.v_audit_dettagliato' non esiste nel database. "
    "Applica la migrazione sql_scripts/migrations/19_create_v_audit_dettagliato.sql "
    "(es. `psql -U postgres -d catasto_storico "
    "-f sql_scripts/migrations/19_create_v_audit_dettagliato.sql`). "
    "Fino ad allora il visualizzatore audit log restituira' risultati vuoti."
)
_audit_view_warning_logged = False


def _warn_missing_audit_view_once(logger: logging.Logger) -> None:
    global _audit_view_warning_logged
    if not _audit_view_warning_logged:
        logger.warning(_MISSING_AUDIT_VIEW_MSG)
        _audit_view_warning_logged = True


class DBAuditMixin:
    """Mixin per audit, sessioni, log e consultazioni."""

    def set_session_app_user(self, user_id: Optional[int], client_ip: Optional[str] = None) -> bool:
        """
        Imposta variabili di sessione PostgreSQL per tracciamento usando il context manager.
        """
        self.logger.debug(f"Impostazione var sessione: app.user_id='{user_id}', app.ip_address='{client_ip}'")
        
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    user_id_str = str(user_id) if user_id is not None else None
                    ip_str = client_ip if client_ip is not None else None
                    
                    # Il terzo argomento 'false' rende l'impostazione valida per l'intera sessione
                    cur.execute("SELECT set_config('app.user_id', %s, false);", (user_id_str,))
                    cur.execute("SELECT set_config('app.ip_address', %s, false);", (ip_str,))
            
            # Il commit è automatico all'uscita del blocco 'with' senza errori
            self.logger.info("Variabili di sessione applicative impostate con successo.")
            return True
            
        except Exception as e:
            self.logger.error(f"Errore DB impostando var sessione applicative: {e}", exc_info=True)
            # Il rollback è automatico, restituiamo False per indicare il fallimento
            return False

    def clear_session_app_user(self):
        """Resetta le variabili di sessione PostgreSQL 'app.user_id' e 'app.ip_address'."""
        self.logger.info("Reset variabili di sessione applicative (app.user_id, app.ip_address).")
        # Richiama set_session_app_user con None per resettarle.
        # In alternativa, si potrebbe usare RESET nome_variabile;
        return self.set_session_app_user(user_id=None, client_ip=None)

    def get_audit_log(self, tabella: Optional[str]=None, operazione: Optional[str]=None,
                      record_id: Optional[int]=None, data_inizio: Optional[date]=None,
                      data_fine: Optional[date]=None, utente_db: Optional[str]=None,
                      app_user_id: Optional[int]=None, session_id: Optional[str]=None,
                      limit: int=100) -> List[Dict]:
        """Recupera log di audit con filtri opzionali dalla vista v_audit_dettagliato."""
        try:
            conditions = []; params = []
            query = "SELECT * FROM v_audit_dettagliato"
            if tabella: conditions.append("tabella = %s"); params.append(tabella)
            if operazione and operazione.upper() in ['I', 'U', 'D']: conditions.append("operazione = %s"); params.append(operazione.upper())
            if record_id is not None: conditions.append("record_id = %s"); params.append(record_id)
            if data_inizio: conditions.append("timestamp >= %s"); params.append(data_inizio)
            if data_fine: data_fine_end_day = datetime.combine(data_fine, datetime.max.time()); conditions.append("timestamp <= %s"); params.append(data_fine_end_day)
            if utente_db: conditions.append("db_user = %s"); params.append(utente_db)
            if app_user_id is not None: conditions.append("al.app_user_id = %s"); params.append(app_user_id)
            if session_id: conditions.append("session_id = %s"); params.append(session_id)

            if conditions: query += " WHERE " + " AND ".join(conditions)
            query += " ORDER BY timestamp DESC LIMIT %s"; params.append(limit)

            # Usa il context manager per una connessione sicura dal pool
            with self._get_connection() as conn:
                with conn.cursor(cursor_factory=DictCursor) as cur:
                    cur.execute(query, tuple(params))
                    return [dict(row) for row in cur.fetchall()]
        except psycopg2.errors.UndefinedTable:
            _warn_missing_audit_view_once(self.logger)
            return []
        except psycopg2.Error as db_err: self.logger.error(f"Errore DB get_audit_log: {db_err}"); return []
        except Exception as e: self.logger.error(f"Errore Python get_audit_log: {e}"); return []
        return []

    def get_record_history(self, tabella: str, record_id: int) -> List[Dict]:
        """Chiama la funzione SQL get_record_history e restituisce la cronologia delle modifiche di un record."""
        try:
            query = "SELECT * FROM get_record_history(%s, %s)"
            with self._get_connection() as conn:
                with conn.cursor(cursor_factory=DictCursor) as cur:
                    cur.execute(query, (tabella, record_id))
                    return [dict(row) for row in cur.fetchall()]
        except psycopg2.Error as db_err: self.logger.error(f"Errore DB get_record_history: {db_err}"); return []
        except Exception as e: self.logger.error(f"Errore Python get_record_history: {e}"); return []
        return []

    def get_audit_logs(self,
                    filters: Optional[Dict[str, Any]] = None,
                    page: int = 1,
                    page_size: int = 50,
                    sort_by: str = 'timestamp',
                    sort_order: str = 'DESC'
                    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        Recupera i record dalla vista v_audit_dettagliato con filtri, paginazione e ordinamento.
        """
        if filters is None:
            filters = {}

        query_conditions = []
        query_params = []

        # Costruzione delle condizioni WHERE in base ai filtri
        if filters.get("table_name"):
            query_conditions.append("tabella ILIKE %s")
            query_params.append(f"%{filters['table_name']}%")

        # --- NUOVO: Filtro per username ---
        if filters.get("username"):
            query_conditions.append("username ILIKE %s")
            query_params.append(f"%{filters['username']}%")
        # --- FINE NUOVO ---

        # ... (gli altri filtri come operation_char, record_id, date rimangono uguali) ...
        if filters.get("operation_char"):
            query_conditions.append("operazione = %s")
            query_params.append(filters["operation_char"])
        if filters.get("record_id") is not None:
            query_conditions.append("record_id = %s")
            query_params.append(filters["record_id"])
        if filters.get("start_datetime"):
            query_conditions.append("timestamp >= %s")
            query_params.append(filters["start_datetime"])
        if filters.get("end_datetime"):
            query_conditions.append("timestamp <= %s")
            query_params.append(filters["end_datetime"])

        where_clause = ""
        if query_conditions:
            where_clause = "WHERE " + " AND ".join(query_conditions)

        # La query ora interroga la VISTA, non la tabella diretta
        base_query = f"FROM {self.schema}.v_audit_dettagliato {where_clause}"
        count_query = f"SELECT COUNT(*) {base_query};"

        # Validazione e costruzione ORDER BY (invariato)
        allowed_sort_columns = ['id', 'timestamp', 'username', 'tabella', 'operazione', 'record_id']
        if sort_by not in allowed_sort_columns: sort_by = 'timestamp'
        if sort_order.upper() not in ['ASC', 'DESC']: sort_order = 'DESC'
        order_by_clause = f"ORDER BY {sort_by} {sort_order.upper()}"

        offset = (page - 1) * page_size

        # La query dei dati ora seleziona direttamente dalla vista
        data_query = f"""
            SELECT * {base_query}
            {order_by_clause}
            LIMIT %s OFFSET %s;
        """
        query_params_data = query_params + [page_size, offset]

        try:
            with self._get_connection() as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                    cur.execute(count_query, query_params)
                    total_records = cur.fetchone()[0]

                    if total_records > 0:
                        cur.execute(data_query, query_params_data)
                        logs = [dict(row) for row in cur.fetchall()]
                    else:
                        logs = []

        except psycopg2.errors.UndefinedTable:
            _warn_missing_audit_view_once(self.logger)
            return [], 0
        except Exception as e:
            self.logger.error(f"Errore durante il recupero dei log di audit: {e}", exc_info=True)
            return [], 0

        return logs, total_records

    def set_audit_session_variables(self, app_user_id: Optional[int], session_id: Optional[str]) -> bool:
        """Imposta le variabili di sessione PostgreSQL per l'audit log in modo sicuro."""
        if app_user_id is None or session_id is None:
            self.logger.warning("Tentativo di impostare variabili audit con None.")
            return False
        
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    # Il terzo argomento 'false' rende l'impostazione valida per l'intera sessione
                    cur.execute("SELECT set_config(%s, %s, false);", (f"{self.schema}.app_user_id", str(app_user_id)))
                    cur.execute("SELECT set_config(%s, %s, false);", (f"{self.schema}.session_id", session_id))
            
            # Il commit è gestito automaticamente dal context manager _get_connection
            self.logger.info(f"Variabili di sessione per audit impostate: app_user_id={app_user_id}, session_id={session_id[:8]}...")
            return True
            
        except Exception as e:
            self.logger.error(f"Errore DB impostando variabili audit: {e}", exc_info=True)
            return False

    def clear_audit_session_variables(self) -> bool:
        """Resetta le variabili di sessione per l'audit in modo sicuro."""
        self.logger.info("Reset variabili di sessione per audit...")
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    # Impostare a NULL è un modo esplicito e sicuro per resettare
                    cur.execute(f"SELECT set_config('{self.schema}.app_user_id', NULL, false);")
                    cur.execute(f"SELECT set_config('{self.schema}.session_id', NULL, false);")
            
            self.logger.info("Variabili di sessione per audit resettate con successo.")
            return True
        except Exception as e:
            self.logger.error(f"Errore DB resettando variabili audit: {e}", exc_info=True)
            return False

    def log_app_event(self, user_id: Optional[int], session_id: Optional[str],
                      event_type: str, details: Optional[Dict[str, Any]] = None) -> None:
        """Registra un evento applicativo (es. export) nell'audit_log.
        Usa operazione='I' e tabella=event_type (es. 'export_csv', 'export_xlsx').
        Non solleva eccezioni: il log è best-effort.
        """
        try:
            import json as _json
            dati_dopo = _json.dumps(details or {}, ensure_ascii=False, default=str)
            query = f"""
                INSERT INTO {self.schema}.audit_log
                    (tabella, operazione, app_user_id, session_id, dati_dopo)
                VALUES (%s, 'I', %s, %s, %s::jsonb)
            """
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(query, (event_type, user_id, session_id, dati_dopo))
            self.logger.debug(f"log_app_event: {event_type} user={user_id}")
        except Exception as e:
            self.logger.warning(f"log_app_event fallito ({event_type}): {e}")

    def cleanup_audit_logs(self, days_to_keep: int) -> int:
        """
        Elimina i record di audit_log più vecchi di un certo numero di giorni.
        Restituisce il numero di record eliminati.
        """
        if not isinstance(days_to_keep, int) or days_to_keep < 0:
            raise DBDataError("Il numero di giorni da conservare deve essere un intero non negativo.")

        query = f"""
            DELETE FROM {self.schema}.audit_log
            WHERE timestamp < NOW() - INTERVAL '{days_to_keep} days';
        """
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(query)
                    deleted_rows = cur.rowcount
            self.logger.info(f"Eliminati {deleted_rows} record di audit log più vecchi di {days_to_keep} giorni.")
            return deleted_rows
        except Exception as e:
            self.logger.error(f"Errore durante la pulizia dei log di audit: {e}", exc_info=True)
            raise DBMError(f"Impossibile pulire i log di audit: {e}") from e

    def close_user_session(self, session_id: str) -> bool:
        """
        Imposta data_fine sulla sessione per registrare il logout.
        Il commit è automatico all'uscita dal context manager _get_connection.
        """
        if not session_id:
            self.logger.warning("Nessun ID di sessione fornito, impossibile chiudere la sessione nel DB.")
            return False

        # Imposta la data_fine solo se la sessione è ancora aperta (data_fine IS NULL)
        query = f"""
            UPDATE {self.schema}.sessioni
            SET data_fine = CURRENT_TIMESTAMP
            WHERE id = %s AND data_fine IS NULL;
        """
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(query, (session_id,))
                    if cur.rowcount > 0:
                        self.logger.info(f"Sessione {session_id} chiusa con successo.")
                    else:
                        self.logger.warning(f"Sessione {session_id} non trovata o già chiusa.")
            return True
        except Exception as e:
            self.logger.error(f"Errore DB durante la chiusura della sessione {session_id}: {e}")
            return False

    def registra_nuova_consultazione(self,
                                    data_consultazione: date,
                                    richiedente: str,
                                    materiale_consultato: str,
                                    funzionario_autorizzante: Optional[str],
                                    documento_identita: Optional[str] = None,
                                    motivazione: Optional[str] = None
                                    ) -> int:
        """
        Registra una nuova consultazione nel database in modo transazionale e sicuro.
        """
        if not all([data_consultazione, richiedente, materiale_consultato]):
            raise DBDataError("Data, Richiedente e Materiale Consultato sono campi obbligatori.")

        query = f"""
            INSERT INTO {self.schema}.consultazione
                (data, richiedente, documento_identita, motivazione, materiale_consultato, funzionario_autorizzante)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id;
        """
        params = (
            data_consultazione,
            richiedente.strip(),
            documento_identita.strip() if documento_identita else None,
            motivazione.strip() if motivazione else None,
            materiale_consultato.strip(),
            funzionario_autorizzante.strip() if funzionario_autorizzante else None
        )
        
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(query, params)
                    result = cur.fetchone()
                    if result and result[0] is not None:
                        new_id = result[0]
                        self.logger.info(f"Nuova consultazione registrata con successo. ID: {new_id}")
                        # Il commit è automatico all'uscita del blocco with
                        return new_id
                    else:
                        # Se non viene restituito un ID, solleva un'eccezione che causerà il rollback automatico
                        raise DBMError("Fallimento registrazione consultazione: nessun ID restituito.")
        except Exception as e:
            self.logger.error(f"Errore DB in registra_nuova_consultazione: {e}", exc_info=True)
            # Il rollback è automatico, rilanciamo un'eccezione chiara per il chiamante
            raise DBMError(f"Impossibile registrare la consultazione: {e}") from e

    def registra_consultazione(self, data: date, richiedente: str, documento_identita: Optional[str],
                             motivazione: Optional[str], materiale_consultato: Optional[str],
                             funzionario_autorizzante: Optional[str]) -> bool:
        """Chiama la procedura SQL registra_consultazione. Il commit è automatico."""
        try:
            call_proc = "CALL registra_consultazione(%s, %s, %s, %s, %s, %s)"
            params = (data, richiedente, documento_identita, motivazione, materiale_consultato, funzionario_autorizzante)
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(call_proc, params)
            self.logger.info(f"Consultazione registrata — richiedente: '{richiedente}', data: {data}")
            return True
        except psycopg2.Error as db_err: self.logger.error(f"Errore DB registrazione consultazione: {db_err}"); return False
        except Exception as e: self.logger.error(f"Errore Python registrazione consultazione: {e}"); return False

    def update_consultazione(self, consultazione_id: int, **kwargs) -> bool:
        """Chiama la procedura SQL aggiorna_consultazione. Il commit è automatico."""
        params = {'p_id': consultazione_id, 'p_data': kwargs.get('data'), 'p_richiedente': kwargs.get('richiedente'),
                  'p_documento_identita': kwargs.get('documento_identita'), 'p_motivazione': kwargs.get('motivazione'),
                  'p_materiale_consultato': kwargs.get('materiale_consultato'), 'p_funzionario_autorizzante': kwargs.get('funzionario_autorizzante')}
        call_proc = "CALL aggiorna_consultazione(%(p_id)s, %(p_data)s, %(p_richiedente)s, %(p_documento_identita)s, %(p_motivazione)s, %(p_materiale_consultato)s, %(p_funzionario_autorizzante)s)"
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(call_proc, params)
            self.logger.info(f"Consultazione ID {consultazione_id} aggiornata.")
            return True
        except psycopg2.Error as db_err: self.logger.error(f"Errore DB aggiornamento consultazione ID {consultazione_id}: {db_err}"); return False
        except Exception as e: self.logger.error(f"Errore Python aggiornamento consultazione ID {consultazione_id}: {e}"); return False

    def delete_consultazione(self, consultazione_id: int) -> bool:
        """Chiama la procedura SQL elimina_consultazione. Il commit è automatico."""
        call_proc = "CALL elimina_consultazione(%s)"
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(call_proc, (consultazione_id,))
            self.logger.info(f"Consultazione ID {consultazione_id} eliminata.")
            return True
        except psycopg2.Error as db_err: self.logger.error(f"Errore DB eliminazione consultazione ID {consultazione_id}: {db_err}"); return False
        except Exception as e: self.logger.error(f"Errore Python eliminazione consultazione ID {consultazione_id}: {e}"); return False

    def search_consultazioni(self, data_inizio: Optional[date] = None, data_fine: Optional[date] = None,
                             richiedente: Optional[str] = None, funzionario: Optional[str] = None) -> List[Dict]:
        """Chiama la funzione SQL cerca_consultazioni con filtri opzionali su periodo, richiedente e funzionario."""
        try:
            query = "SELECT * FROM cerca_consultazioni(%s, %s, %s, %s)"
            params = (data_inizio, data_fine, richiedente, funzionario)
            with self._get_connection() as conn:
                with conn.cursor(cursor_factory=DictCursor) as cur:
                    cur.execute(query, params)
                    return [dict(row) for row in cur.fetchall()]
        except psycopg2.Error as db_err: self.logger.error(f"Errore DB in search_consultazioni: {db_err}")
        except Exception as e: self.logger.error(f"Errore Python in search_consultazioni: {e}")
        return []

    def get_recent_session_logs(self, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Recupera gli ultimi N eventi di sessione (login, logout, etc.)
        unendo le informazioni con i nomi degli utenti.
        """
        self.logger.info(f"Recupero degli ultimi {limit} log di sessione.")
        
        # La query ora usa i nomi corretti delle colonne: 'data_login' e 'indirizzo_ip'
        query = f"""
            SELECT
                sa.data_login,
                sa.azione,
                sa.esito,
                sa.indirizzo_ip,
                u.username,
                u.nome_completo
            FROM {self.schema}.sessioni_accesso sa
            LEFT JOIN {self.schema}.utente u ON sa.utente_id = u.id
            ORDER BY sa.data_login DESC
            LIMIT %s;
        """

        try:
            with self._get_connection() as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                    cur.execute(query, (limit,))
                    results = [dict(row) for row in cur.fetchall()]
                    return results
        except Exception as e:
            self.logger.error(f"Errore durante il recupero dei log di sessione recenti: {e}", exc_info=True)
            return []

