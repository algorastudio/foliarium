"""
db/base.py — DBConnectionBase: pool, connessione, cache, transazioni.
Classe base per CatastoDBManager (non usare direttamente).
"""

import psycopg2
import psycopg2.errors
import psycopg2.pool  # noqa: F401  — registra psycopg2.pool.X (usato via dotted access)
from psycopg2.extras import DictCursor
from psycopg2 import sql
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple, Callable
import json
from contextlib import contextmanager
from functools import wraps





COLONNE_POSSESSORI_DETTAGLI_NUM = 6 # Esempio: ID, Nome Compl, Cognome/Nome, Paternità, Quota, Titolo
COLONNE_POSSESSORI_DETTAGLI_LABELS = ["ID Poss.", "Nome Completo", "Cognome Nome", "Paternità", "Quota", "Titolo"]

logger = logging.getLogger(__name__)
# ------------ ECCEZIONI PERSONALIZZATE ------------
# Definite in catasto_exceptions.py; re-esportate qui per backward compatibility.
# Importare preferibilmente da catasto_exceptions direttamente.
from catasto_exceptions import (
    DBMError,
    DBUniqueConstraintError,
    DBDataError,
)
# -------------------------------------------------

# ------------ ERROR HANDLER DECORATOR ------------
def db_handle_errors(method: Callable) -> Callable:
    """
    Decorator: catch common DB errors, log, and translate to custom exceptions.

    Usage:
        @db_handle_errors
        def get_partita(self, partita_id: int) -> Optional[Dict]:
            with self._get_connection() as conn:
                ...
    """
    @wraps(method)
    def wrapper(self, *args, **kwargs):
        try:
            return method(self, *args, **kwargs)
        except psycopg2.errors.UniqueViolation as e:
            self.logger.error(f"{method.__name__}: unique constraint violation: {e}")
            raise DBUniqueConstraintError(str(e)) from e
        except psycopg2.errors.OperationalError as e:
            self.logger.error(f"{method.__name__}: DB unreachable: {e}")
            self.last_connection_error = str(e)
            raise DBMError("Database unreachable") from e
        except psycopg2.errors.DataError as e:
            self.logger.error(f"{method.__name__}: data type mismatch: {e}")
            raise DBDataError(str(e)) from e
        except psycopg2.errors.ForeignKeyViolation as e:
            self.logger.error(f"{method.__name__}: foreign key constraint violation: {e}")
            raise DBMError(f"Foreign key constraint violated: {e}") from e
        except Exception as e:
            self.logger.error(f"{method.__name__}: unexpected error: {e}", exc_info=True)
            raise
    return wrapper
# -------------------------------------------------

class DBConnectionBase:

    # Host considerati locali: per questi il default TLS è 'prefer' (TLS se il
    # server lo offre, altrimenti connessione in chiaro accettabile sul loopback).
    _LOCAL_HOSTS = frozenset({"", "localhost", "127.0.0.1", "::1", "::ffff:127.0.0.1"})

    @staticmethod
    def _resolve_sslmode(sslmode, host):
        """Determina il sslmode effettivo per la connessione PostgreSQL.

        Precedenza:
          1. valore esplicito passato al costruttore;
          2. override da config (config.ini [database].sslmode / env DB_SSLMODE);
          3. default basato sull'host: 'prefer' per host locali, 'require' per
             host remoti (TLS obbligatorio — le credenziali e i dati personali
             dei possessori non viaggiano mai in chiaro su rete).

        Valori libpq validi: disable, allow, prefer, require, verify-ca,
        verify-full.
        """
        if sslmode:
            return sslmode
        try:
            import config as _cfg
            configured = (getattr(_cfg, "ENV_DB_SSLMODE", "") or "").strip()
        except Exception:
            configured = ""
        if configured:
            return configured
        if (host or "").strip().lower() in DBConnectionBase._LOCAL_HOSTS:
            return "prefer"
        return "require"

    def __init__(self, dbname, user, password, host, port,
                 schema="catasto",
                 application_name="CatastoApp_Pool",
                 log_file="catasto_db_manager.log",
                 log_level=logging.DEBUG, # O il suo default
                 min_conn=2,
                 max_conn=20,
                 sslmode=None):


        effective_sslmode = self._resolve_sslmode(sslmode, host)
        self._main_db_conn_params = {"dbname": dbname, "user": user, "password": password,
                                     "host": host, "port": port, "sslmode": effective_sslmode}
        self._maintenance_db_name = "postgres"
        self.schema = schema
        self.application_name = application_name
        self._min_conn_pool = min_conn
        self._max_conn_pool = max_conn
        # --- AGGIUNGERE QUESTA RIGA ---
        self.last_connection_error = None # Per memorizzare i dettagli dell'ultimo errore
        # -----------------------------

        self.logger = logging.getLogger(f"CatastoDB_{dbname}_{host}_{port}")
        # ... (resto della configurazione del logger come prima) ...
        self.logger.info(f"Inizializzato gestore DB (parametri memorizzati) per {dbname}@{host} (sslmode={effective_sslmode})")
        self.pool = None # Il pool viene inizializzato esplicitamente dopo

        # --- TIER 3 Phase 2: Pool health metrics ---
        self._pool_metrics = {
            "total_getconn": 0,
            "total_putconn": 0,
            "connection_errors": 0,
            "peak_active": 0,
            "last_error_time": None,
        }

        # --- Modalità offline / cache locale ---
        self.offline_mode: bool = False
        self.offline_cache_timestamp: Optional[str] = None
        try:
            from app_paths import CACHE_DIR
            self._cache_dir = CACHE_DIR
        except Exception:
            self._cache_dir = None
            self.logger.warning("CACHE_DIR non disponibile; cache offline disabilitata.")
    # In catasto_db_manager.py, SOSTITUISCI il metodo initialize_main_pool con questo:

    def initialize_main_pool(self) -> bool:
        if self.pool:
            self.logger.info("Pool principale già inizializzato.")
            return True

        self.last_connection_error = None
        target_dbname = self._main_db_conn_params.get("dbname")
        
        pool_config = {
            "minconn": self._min_conn_pool,
            "maxconn": self._max_conn_pool,
            **self._main_db_conn_params,
            "options": f"-c search_path={self.schema},public -c application_name='{self.application_name}_{target_dbname}' -c client_encoding=UTF8"
        }
        
        try:
            self.logger.info(f"Tentativo di inizializzazione pool per DB '{target_dbname}'...")
            self.pool = psycopg2.pool.ThreadedConnectionPool(**pool_config)
            
            conn_test = self.pool.getconn()
            self.pool.putconn(conn_test)
            
            self.logger.info(f"Pool di connessioni per DB '{target_dbname}' inizializzato e testato con successo.")
            self._apply_pending_schema_migrations()
            return True

        except (psycopg2.pool.PoolError, psycopg2.Error) as e_init:
            
            # --- NUOVA LOGICA ROBUSTA DI ANALISI DELL'ERRORE ---
            error_string = str(e_init).lower()
            custom_pgcode = "UNKNOWN_DB_ERROR" # Default

            if "password authentication failed" in error_string or "autenticazione con password fallita" in error_string:
                custom_pgcode = "28P01" # Codice per Authentication Failure
            elif 'database' in error_string and ('does not exist' in error_string or 'non esiste' in error_string):
                custom_pgcode = "3D000" # Codice per Invalid Catalog Name
            elif "connection refused" in error_string or "connessione rifiutata" in error_string or "timed out" in error_string or "could not connect" in error_string:
                custom_pgcode = "08001" # Codice per Connection Exception

            self.last_connection_error = {
                'pgcode': custom_pgcode,
                'pgerror': str(e_init).strip() # Salva sempre il messaggio completo
            }
            # --- FINE NUOVA LOGICA ---
            
            self.logger.critical(f"FALLIMENTO inizializzazione pool per DB '{target_dbname}'. Errore: {e_init}", exc_info=False)
            self.logger.critical(f"   Dettagli Errore Analizzati: pgcode={self.last_connection_error['pgcode']}, pgerror='{self.last_connection_error['pgerror']}'")
            
            if self.pool:
                self.pool.closeall()
            self.pool = None
            return False
            
        except Exception as e_generic:
            self.last_connection_error = {'pgcode': 'GENERIC_PYTHON_ERROR', 'pgerror': str(e_generic)}
            self.logger.critical(f"FALLIMENTO inizializzazione pool per DB '{target_dbname}'. Errore generico: {e_generic}", exc_info=True)
            if self.pool:
                self.pool.closeall()
            self.pool = None
            return False

    def check_missing_migrations(self) -> list[str]:
        """Verifica se mancano migrazioni critiche nello schema del DB.

        Restituisce una lista di descrizioni delle migrazioni mancanti.
        Lista vuota → schema aggiornato.  Errori di connessione → lista vuota
        (non bloccante: il DB potrebbe essere offline).
        """
        missing = []
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    # Soft-delete (archiviazione) — migrations/add_soft_delete.sql
                    cur.execute(
                        "SELECT 1 FROM information_schema.columns "
                        "WHERE table_schema = %s AND table_name = 'comune' "
                        "  AND column_name = 'archiviato'",
                        (self.schema,)
                    )
                    if not cur.fetchone():
                        missing.append("soft_delete")

                    # Tipo possesso — migrations/add_tipo_possesso.sql
                    cur.execute(
                        "SELECT 1 FROM information_schema.tables "
                        "WHERE table_schema = %s AND table_name = 'tipo_possesso'",
                        (self.schema,)
                    )
                    if not cur.fetchone():
                        missing.append("tipo_possesso")

        except Exception as e:
            self.logger.debug(f"check_missing_migrations: impossibile verificare ({e})")
        return missing

    def _apply_pending_schema_migrations(self):
        """Applica migrazioni schema idempotenti all'avvio (silent best-effort).

        Ogni step è isolato: il fallimento di uno non blocca gli altri. Tutti
        gli step sono idempotenti (no-op se già applicati).
        """
        # Migrazione v1.6.1: rimuove tipo_id e incorpora civico nel nome località.
        # Eseguita solo su DB pre-v1.6.1 (rilevamento via colonna tipo_id).
        self._apply_v161_localita_migration()

        # Ownership delle MV — REFRESH MATERIALIZED VIEW richiede di esserne
        # proprietari. Va eseguito prima di creare gli indici (anche CREATE
        # INDEX richiede l'ownership). Best-effort, non bloccante.
        self._ensure_mv_ownership()

        # Indici UNIQUE sulle MV — richiesti per REFRESH ... CONCURRENTLY.
        # Idempotente: ogni CREATE è IF NOT EXISTS, l'esistenza della MV
        # è verificata prima per evitare errori se la MV non è stata creata.
        self._ensure_mv_unique_indexes()

        # Vista v_audit_dettagliato — assente nei DB inizializzati prima di
        # sql_scripts/18_funzioni_trigger_audit.sql; senza, il visualizzatore
        # audit log lancia UndefinedTable. CREATE OR REPLACE = idempotente.
        self._ensure_audit_view()

        # Tabella partita_draft — bozze del wizard Nuova Partita.
        # Idempotente: CREATE TABLE IF NOT EXISTS.
        self._ensure_partita_draft_table()

        # Tabella api_keys — chiavi API per integrazioni esterne.
        # Idempotente: CREATE TABLE IF NOT EXISTS.
        self._ensure_api_keys_table()

    def _apply_v161_localita_migration(self):
        """Migrazione v1.6.1: rimuove tipo_id da localita e incorpora civico.

        Step isolato dagli altri ensure_*: un errore qui non blocca gli step
        successivi (la separazione e' stata introdotta per fixare un bug in
        cui il return early da questo metodo, quando inserito inline in
        _apply_pending_schema_migrations, saltava silenziosamente tutti gli
        ensure_* successivi su qualunque DB gia' aggiornato).
        """
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT 1 FROM information_schema.columns "
                        "WHERE table_schema = %s AND table_name = 'localita' AND column_name = 'tipo_id'",
                        (self.schema,)
                    )
                    if not cur.fetchone():
                        return  # schema già aggiornato

                    self.logger.info("Schema pre-v1.6.1 rilevato (tipo_id presente). Applico migrazione automatica...")

                    # Popola tipologia_stradale dove mancante
                    cur.execute(
                        f"UPDATE {self.schema}.localita l "
                        f"SET tipologia_stradale = tl.nome "
                        f"FROM {self.schema}.tipo_localita tl "
                        f"WHERE l.tipo_id = tl.id "
                        f"  AND (l.tipologia_stradale IS NULL OR l.tipologia_stradale = '')"
                    )

                    # Rimuovi FK constraint su tipo_id
                    cur.execute(
                        "SELECT con.conname FROM pg_constraint con "
                        "JOIN pg_class rel ON rel.oid = con.conrelid "
                        "JOIN pg_namespace ns ON ns.oid = rel.relnamespace "
                        "WHERE rel.relname = 'localita' AND ns.nspname = %s "
                        "  AND con.contype = 'f' AND con.conname ILIKE '%%tipo%%'",
                        (self.schema,)
                    )
                    fk_row = cur.fetchone()
                    if fk_row:
                        cur.execute(f"ALTER TABLE {self.schema}.localita DROP CONSTRAINT IF EXISTS {fk_row[0]}")

                    # Rimuovi colonna tipo_id
                    cur.execute(f"ALTER TABLE {self.schema}.localita DROP COLUMN IF EXISTS tipo_id")

                    # Rimuovi colonna civico se ancora presente
                    cur.execute(
                        "SELECT 1 FROM information_schema.columns "
                        "WHERE table_schema = %s AND table_name = 'localita' AND column_name = 'civico'",
                        (self.schema,)
                    )
                    if cur.fetchone():
                        cur.execute(
                            f"UPDATE {self.schema}.localita "
                            f"SET nome = CONCAT(nome, ' ', civico) "
                            f"WHERE civico IS NOT NULL AND civico != ''"
                        )
                        cur.execute(f"ALTER TABLE {self.schema}.localita DROP COLUMN IF EXISTS civico")

                    self.logger.info("Migrazione automatica schema v1.6.1 completata con successo.")
        except Exception as e:
            self.logger.warning(f"Migrazione schema v1.6.1 saltata (non bloccante): {e}")

    def _ensure_api_keys_table(self):
        """Crea la tabella catasto.api_keys se mancante.

        Equivale alla migrazione `migrations/22_create_api_keys.sql` ma
        applicata automaticamente all'avvio. Best-effort: non blocca
        l'avvio se fallisce (es. permessi DDL insufficienti).
        """
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        f"CREATE TABLE IF NOT EXISTS {self.schema}.api_keys ("
                        f"  id                 SERIAL PRIMARY KEY, "
                        f"  name               VARCHAR(100) NOT NULL, "
                        f"  key_hash           VARCHAR(64)  NOT NULL UNIQUE, "
                        f"  prefix             VARCHAR(12)  NOT NULL, "
                        f"  scopes             TEXT[]       NOT NULL "
                        f"                     DEFAULT ARRAY[]::TEXT[], "
                        f"  created_by         INTEGER      NULL "
                        f"                     REFERENCES {self.schema}.utente(id) "
                        f"                     ON DELETE SET NULL, "
                        f"  created_at         TIMESTAMPTZ  NOT NULL DEFAULT NOW(), "
                        f"  expires_at         TIMESTAMPTZ  NULL, "
                        f"  revoked_at         TIMESTAMPTZ  NULL, "
                        f"  last_used_at       TIMESTAMPTZ  NULL, "
                        f"  rate_limit_per_min INTEGER      NOT NULL DEFAULT 60 "
                        f")"
                    )
                    cur.execute(
                        f"CREATE INDEX IF NOT EXISTS idx_api_keys_prefix "
                        f"ON {self.schema}.api_keys(prefix)"
                    )
                    cur.execute(
                        f"CREATE INDEX IF NOT EXISTS idx_api_keys_active "
                        f"ON {self.schema}.api_keys(revoked_at, expires_at) "
                        f"WHERE revoked_at IS NULL"
                    )
                conn.commit()
        except Exception as e:
            self.logger.warning(
                f"_ensure_api_keys_table fallita (non bloccante): {e}. "
                f"Applicare manualmente sql_scripts/migrations/22_create_api_keys.sql."
            )

    def _ensure_partita_draft_table(self):
        """Crea (o aggiorna) la tabella catasto.partita_draft se mancante.

        Equivale alla migrazione `migrations/21_create_partita_draft.sql`
        ma applicata automaticamente all'avvio. Best-effort: non blocca
        l'avvio.

        Aggiorna anche la tabella esistente aggiungendo la colonna
        `wizard_kind` (introdotta per supportare più wizard) se mancante.
        """
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT 1 FROM information_schema.tables "
                        "WHERE table_schema = %s AND table_name = 'partita_draft'",
                        (self.schema,)
                    )
                    table_exists = cur.fetchone() is not None

                    if not table_exists:
                        # Verifica che la tabella utente esista per la FK
                        cur.execute(
                            "SELECT 1 FROM information_schema.tables "
                            "WHERE table_schema = %s AND table_name = 'utente'",
                            (self.schema,)
                        )
                        has_utente = cur.fetchone() is not None
                        fk_clause = (
                            f"REFERENCES {self.schema}.utente(id) ON DELETE SET NULL"
                            if has_utente else ""
                        )
                        try:
                            cur.execute(
                                f"CREATE TABLE IF NOT EXISTS {self.schema}.partita_draft ("
                                f"  id          SERIAL PRIMARY KEY,"
                                f"  utente_id   INTEGER NULL {fk_clause},"
                                f"  wizard_kind VARCHAR(64) NOT NULL DEFAULT 'nuova_partita_wizard',"
                                f"  titolo      VARCHAR(255) NOT NULL,"
                                f"  payload     JSONB NOT NULL,"
                                f"  app_version VARCHAR(32),"
                                f"  created_at  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,"
                                f"  updated_at  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP"
                                f")"
                            )
                            cur.execute(
                                f"CREATE INDEX IF NOT EXISTS idx_partita_draft_utente "
                                f"ON {self.schema}.partita_draft(utente_id, wizard_kind, updated_at DESC)"
                            )
                            self.logger.info(
                                "Tabella %s.partita_draft creata automaticamente all'avvio.",
                                self.schema,
                            )
                        except psycopg2.Error as e:
                            conn.rollback()
                            self.logger.warning(
                                "Impossibile creare la tabella %s.partita_draft "
                                "(%s). Applicare come superuser "
                                "sql_scripts/migrations/21_create_partita_draft.sql; "
                                "fino ad allora la funzione 'Salva bozza' dei "
                                "wizard partita non sarà disponibile.",
                                self.schema, e
                            )
                        return

                    # Tabella già presente: verifica colonna wizard_kind
                    cur.execute(
                        "SELECT 1 FROM information_schema.columns "
                        "WHERE table_schema = %s AND table_name = 'partita_draft' "
                        "  AND column_name = 'wizard_kind'",
                        (self.schema,)
                    )
                    if cur.fetchone():
                        return  # già aggiornata
                    try:
                        cur.execute(
                            f"ALTER TABLE {self.schema}.partita_draft "
                            f"ADD COLUMN IF NOT EXISTS wizard_kind VARCHAR(64) "
                            f"NOT NULL DEFAULT 'nuova_partita_wizard'"
                        )
                        # Indice nuovo (vecchio resta come fallback)
                        cur.execute(
                            f"CREATE INDEX IF NOT EXISTS idx_partita_draft_utente_kind "
                            f"ON {self.schema}.partita_draft(utente_id, wizard_kind, updated_at DESC)"
                        )
                        self.logger.info(
                            "Colonna wizard_kind aggiunta a %s.partita_draft.",
                            self.schema,
                        )
                    except psycopg2.Error as e:
                        conn.rollback()
                        self.logger.warning(
                            "Impossibile aggiornare %s.partita_draft con la colonna "
                            "wizard_kind (%s). Le bozze esistenti continueranno a "
                            "funzionare nel wizard Nuova Partita.",
                            self.schema, e
                        )
        except Exception as e:
            self.logger.debug(f"_ensure_partita_draft_table: {e}")

    def _ensure_audit_view(self):
        """Crea la vista catasto.v_audit_dettagliato se mancante.

        Equivale alla migrazione `migrations/19_create_v_audit_dettagliato.sql`
        ma applicata automaticamente all'avvio. Best-effort: non blocca
        l'avvio. Se la CREATE fallisce per privilegi insufficienti viene
        loggato un warning che rimanda alla migrazione manuale.
        """
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT 1 FROM information_schema.views "
                        "WHERE table_schema = %s AND table_name = 'v_audit_dettagliato'",
                        (self.schema,)
                    )
                    if cur.fetchone():
                        return  # vista già presente
                    cur.execute(
                        "SELECT 1 FROM information_schema.tables "
                        "WHERE table_schema = %s "
                        "  AND table_name IN ('audit_log', 'utente')",
                        (self.schema,)
                    )
                    # Devono esistere entrambe (audit_log + utente) per costruirla
                    if cur.rowcount < 2:
                        return
                    try:
                        cur.execute(
                            f"CREATE OR REPLACE VIEW {self.schema}.v_audit_dettagliato AS "
                            f"SELECT al.id, CAST(al.timestamp AS TIMESTAMP(0)) AS timestamp, "
                            f"  al.app_user_id, u.username, u.nome_completo, al.session_id, "
                            f"  al.tabella, al.operazione, al.record_id, al.ip_address, "
                            f"  al.utente AS db_user, al.dati_prima, al.dati_dopo "
                            f"FROM {self.schema}.audit_log al "
                            f"LEFT JOIN {self.schema}.utente u ON al.app_user_id = u.id"
                        )
                        self.logger.info(
                            "Vista %s.v_audit_dettagliato creata automaticamente all'avvio.",
                            self.schema,
                        )
                    except psycopg2.Error as e:
                        # Tipicamente 42501 (insufficient_privilege): l'utente
                        # del DB non può creare viste. L'audit viewer resterà
                        # vuoto finché un amministratore non applica la
                        # migrazione 19 come superuser.
                        conn.rollback()
                        self.logger.warning(
                            "Impossibile creare la vista %s.v_audit_dettagliato "
                            "(%s). Applicare come superuser "
                            "sql_scripts/migrations/19_create_v_audit_dettagliato.sql; "
                            "fino ad allora il visualizzatore audit log "
                            "resterà vuoto.", self.schema, e
                        )
        except Exception as e:
            self.logger.debug(f"_ensure_audit_view: {e}")

    def _ensure_mv_ownership(self):
        """Allinea all'utente connesso l'ownership delle viste materializzate.

        `REFRESH MATERIALIZED VIEW` richiede di essere proprietari della MV:
        PostgreSQL non offre un GRANT equivalente. Se le MV sono di un altro
        ruolo — tipicamente `postgres`, che le crea durante il setup — il
        refresh dalla GUI fallisce con InsufficientPrivilege. Equivale a
        `sql_scripts/admin/05_fix_mv_ownership.sql` applicato all'avvio
        (best-effort, non bloccante).

        Riesce solo se l'utente connesso è superuser o proprietario corrente
        delle MV; altrimenti lo script admin va eseguito come superuser.
        """
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT matviewname FROM pg_matviews "
                        "WHERE schemaname = %s AND matviewowner <> current_user",
                        (self.schema,)
                    )
                    pending = [row[0] for row in cur.fetchall()]
                    if not pending:
                        return
                    for mv_name in pending:
                        try:
                            cur.execute(
                                f"ALTER MATERIALIZED VIEW {self.schema}.{mv_name} "
                                f"OWNER TO CURRENT_USER"
                            )
                        except psycopg2.Error as e:
                            conn.rollback()
                            self.logger.warning(
                                "Impossibile allineare l'ownership delle viste "
                                "materializzate: l'utente del database non è "
                                "superuser né proprietario. Il refresh delle "
                                "statistiche resta disabilitato finché un "
                                "amministratore non esegue "
                                "sql_scripts/admin/05_fix_mv_ownership.sql. "
                                f"Dettaglio: {e}"
                            )
                            return  # stesso esito per le altre MV: inutile ritentare
                    self.logger.info(
                        f"Ownership di {len(pending)} vista/e materializzata/e "
                        f"allineata all'utente connesso."
                    )
        except Exception as e:
            self.logger.debug(f"_ensure_mv_ownership: {e}")

    def _ensure_mv_unique_indexes(self):
        """Crea gli indici UNIQUE mancanti sulle viste materializzate.

        Prerequisito per `REFRESH MATERIALIZED VIEW CONCURRENTLY`: PostgreSQL
        richiede almeno un indice UNIQUE senza clausola WHERE sulla MV.
        Equivale alla migrazione `migrations/add_unique_indexes_mv.sql` ma
        applicata automaticamente all'avvio (best-effort, non bloccante).
        """
        # MV → (nome_indice, lista colonne)
        mv_indexes = {
            "mv_immobili_per_tipologia": ("idx_mv_immobili_tipologia_unique",
                                          "comune_nome, classificazione"),
            "mv_partite_complete":       ("idx_mv_partite_complete_partita_id",
                                          "partita_id"),
            "mv_cronologia_variazioni":  ("idx_mv_variazioni_var_id",
                                          "variazione_id"),
            "mv_statistiche_comune":     ("idx_mv_statistiche_comune", "comune"),
        }
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT matviewname FROM pg_matviews WHERE schemaname = %s",
                        (self.schema,)
                    )
                    existing_mvs = {row[0] for row in cur.fetchall()}

                    for mv_name, (idx_name, cols) in mv_indexes.items():
                        if mv_name not in existing_mvs:
                            continue
                        try:
                            cur.execute(
                                f"CREATE UNIQUE INDEX IF NOT EXISTS {idx_name} "
                                f"ON {self.schema}.{mv_name} ({cols})"
                            )
                            self.logger.debug(
                                f"Indice UNIQUE garantito su {self.schema}.{mv_name} ({cols})"
                            )
                        except psycopg2.Error as e:
                            # Es. duplicati nella MV — non blocchiamo l'avvio.
                            self.logger.warning(
                                f"Impossibile creare {idx_name} su {mv_name}: {e}"
                            )
                            conn.rollback()
        except Exception as e:
            self.logger.debug(f"_ensure_mv_unique_indexes: {e}")

    def close_pool(self):
        """
        Chiude tutte le connessioni nel pool e imposta self.pool a None.
        Questo metodo dovrebbe essere chiamato quando l'applicazione si chiude
        o quando il database a cui il pool è connesso viene cancellato.
        """
        if self.pool:
            try:
                pool_name_app = self.pool._kwargs.get('application_name', self.application_name) # Tenta di ottenere il nome specifico del pool
                db_name_pooled = self.pool._kwargs.get('dbname', 'N/D')
                self.logger.info(f"Tentativo di chiusura del pool di connessioni '{pool_name_app}' per il database '{db_name_pooled}'...")
                self.pool.closeall()
                self.logger.info(f"Pool di connessioni '{pool_name_app}' (DB: '{db_name_pooled}') chiuso con successo.")
            except Exception as e:
                self.logger.error(f"Errore durante la chiusura del pool di connessioni: {e}", exc_info=True)
            finally:
                self.pool = None # Assicura che il pool sia None dopo il tentativo di chiusura, anche in caso di errore.
        else:
            self.logger.info("close_pool chiamato, ma il pool non era attivo o già None.")

    def get_pool_metrics(self) -> Dict[str, Any]:
        """
        TIER 3 Phase 2: Restituisce metriche di salute del pool.
        Utile per monitoraggio e diagnostica.
        """
        metrics = self._pool_metrics.copy()
        if self.pool:
            metrics.update({
                "pool_size": self.pool.getconn.__self__.minconn if hasattr(self.pool, 'minconn') else 'N/A',
                "pool_max": self._max_conn_pool,
                "closed_connections": getattr(self.pool, '_closed', 0),
            })
        return metrics

    def get_pool_health_status(self) -> str:
        """
        TIER 3 Phase 2: Ritorna stato salute pool (OK, DEGRADED, CRITICAL).
        """
        if not self.pool:
            return "OFFLINE"
        errors = self._pool_metrics.get("connection_errors", 0)
        total = max(self._pool_metrics.get("total_getconn", 1), 1)
        error_rate = errors / total if total > 0 else 0

        if error_rate > 0.1:  # >10% error rate
            return "CRITICAL"
        elif error_rate > 0.05:  # >5% error rate
            return "DEGRADED"
        return "OK"

    def _get_maintenance_connection(self, db_user_admin: str, db_password_admin: str, maintenance_dbname: str = "postgres"):
        """Ottiene una connessione singola a un database di manutenzione (es. postgres)."""
        maint_conn_params = self._main_db_conn_params.copy()
        maint_conn_params["dbname"] = maintenance_dbname
        # Usa le credenziali dell'utente admin del DB fornite, non quelle dell'app per catasto_storico
        maint_conn_params["user"] = db_user_admin
        maint_conn_params["password"] = db_password_admin 
        
        self.logger.info(f"Tentativo di connessione al DB di manutenzione '{maintenance_dbname}' come utente '{db_user_admin}'.")
        try:
            conn = psycopg2.connect(**maint_conn_params)
            conn.autocommit = True # Utile per comandi come CREATE DATABASE
            return conn
        except psycopg2.Error as e:
            self.logger.error(f"Errore connessione al DB di manutenzione '{maintenance_dbname}': {e}", exc_info=True)
            raise DBMError(f"Impossibile connettersi al database '{maintenance_dbname}': {e}") from e

    def check_database_exists(self, target_dbname: str, admin_user: str, admin_password: str) -> bool:
        """Verifica se un database specifico esiste connettendosi a 'postgres'."""
        conn_maint = None
        exists = False
        try:
            conn_maint = self._get_maintenance_connection(admin_user, admin_password, maintenance_dbname="postgres")
            with conn_maint.cursor() as cur:
                cur.execute("SELECT 1 FROM pg_database WHERE datname = %s;", (target_dbname,))
                exists = cur.fetchone() is not None
                self.logger.info(f"Controllo esistenza database '{target_dbname}': {'Esiste' if exists else 'Non esiste'}.")
        except DBMError as e: # Errore di connessione al DB di manutenzione
            self.logger.error(f"Impossibile verificare esistenza DB '{target_dbname}' due to error connecting to maintenance DB: {e}")
            # In questo caso, non possiamo sapere se esiste, consideriamo che non esista o sia inaccessibile
            exists = False 
        except psycopg2.Error as e: # Altri errori SQL
            self.logger.error(f"Errore DB verificando esistenza database '{target_dbname}': {e}", exc_info=True)
            exists = False
        finally:
            if conn_maint:
                conn_maint.close()
        return exists

    def create_target_database(self, target_dbname: str, admin_user: str, admin_password: str) -> bool:
        """Crea il database target (es. catasto_storico) se non esiste, connettendosi a 'postgres'."""
        conn_maint = None
        try:
            # Prima verifica se esiste per evitare errore CREATE se esiste già
            if self.check_database_exists(target_dbname, admin_user, admin_password):
                self.logger.info(f"Il database '{target_dbname}' esiste già. Nessuna azione di creazione eseguita.")
                return True # Considera successo se esiste già

            conn_maint = self._get_maintenance_connection(admin_user, admin_password, maintenance_dbname="postgres")
            with conn_maint.cursor() as cur: # autocommit è True sulla connessione
                self.logger.info(f"Tentativo di creare il database '{target_dbname}'...")
                # Usa sql.SQL per formattare nomi di database in modo sicuro
                cur.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(target_dbname)))
                self.logger.info(f"Database '{target_dbname}' creato con successo.")
            return True
        except DBMError as e: # Errore di connessione al DB di manutenzione
            self.logger.error(f"Impossibile creare DB '{target_dbname}' due to error connecting to maintenance DB: {e}")
            return False
        except psycopg2.Error as e: # Altri errori SQL, es. "database ... already exists" se il check precedente fallisce
            self.logger.error(f"Errore DB durante la creazione del database '{target_dbname}': {getattr(e, 'pgerror', str(e))}", exc_info=False)
            if "already exists" in str(e).lower(): # Se esiste già, consideralo OK
                self.logger.info(f"Database '{target_dbname}' esisteva già (errore CREATE DATABASE ignorato).")
                return True
            return False
        except Exception as e:
            self.logger.error(f"Errore Python imprevisto durante la creazione del database '{target_dbname}': {e}", exc_info=True)
            return False
        finally:
            if conn_maint:
                conn_maint.close()
# In catasto_db_manager.py, all'interno della classe CatastoDBManager

    @contextmanager
    def _get_connection(self):
        """
        Context manager per ottenere e rilasciare in sicurezza una connessione dal pool.
        Garantisce che putconn() sia sempre chiamato.

        Thread-safety: ThreadedConnectionPool.getconn() è thread-safe; ogni chiamante
        riceve una connessione dedicata. NON conservare il conn fuori dal blocco `with`
        né passarlo ad altri thread — le connessioni psycopg2 non sono thread-safe.
        """
        conn = None
        try:
            if not self.pool:
                raise psycopg2.pool.PoolError("Il pool di connessioni non è inizializzato.")
            conn = self.pool.getconn()
            self._pool_metrics["total_getconn"] += 1
            yield conn
            conn.commit()
        except psycopg2.pool.PoolError as pe:
            self._pool_metrics["connection_errors"] += 1
            self._pool_metrics["last_error_time"] = datetime.now()
            self.logger.error(
                "Pool connessioni esaurito (max=%s in uso). Dettaglio: %s",
                getattr(self.pool, '_maxconn', '?'), pe,
            )
            raise psycopg2.OperationalError(
                "Il database è al massimo delle connessioni attive. "
                "Attendere un momento e riprovare l'operazione."
            ) from pe
        except Exception as e:
            if conn:
                try:
                    conn.rollback()
                except psycopg2.Error as rollback_err:
                    self.logger.error(f"Errore durante il rollback della connessione: {rollback_err}", exc_info=True)
                    if isinstance(e, psycopg2.OperationalError):
                        self.logger.critical("Errore operativo critico: il server ha chiuso la connessione.")
                        self.close_pool()
            self.logger.error(f"Errore durante l'uso della connessione: {e}", exc_info=True)
            raise
        finally:
            if conn:
                self._pool_metrics["total_putconn"] += 1
                self.pool.putconn(conn)
    
    # ------------------------------------------------------------------ #
    #  Transaction manager ad alto livello                                 #
    # ------------------------------------------------------------------ #

    @contextmanager
    def transaction(self):
        """
        Context manager per transazioni esplicite multi-operazione.

        Ottiene una connessione dal pool e la mantiene aperta per l'intera
        durata del blocco `with`.  Il commit viene eseguito solo all'uscita
        senza eccezioni; in caso di errore viene eseguito il rollback.

        Utilizzo::

            with db.transaction() as conn:
                with conn.cursor() as cur:
                    cur.execute("INSERT INTO ...", params1)
                    cur.execute("INSERT INTO ...", params2)
            # commit automatico qui

        A differenza di `_get_connection()` (che viene usato per singole
        operazioni atomiche), `transaction()` è pensato per raggruppare
        operazioni correlate in un'unica transazione ACID.

        Raises:
            psycopg2.OperationalError: Se il pool non è inizializzato.
            Qualunque eccezione sollevata nel blocco provoca il rollback.
        """
        conn = None
        try:
            if not self.pool:
                raise psycopg2.pool.PoolError(
                    "Il pool di connessioni non è inizializzato."
                )
            conn = self.pool.getconn()
            # Disabilitiamo l'autocommit per gestire la transazione manualmente
            conn.autocommit = False
            yield conn
            conn.commit()
            self.logger.debug("transaction(): commit eseguito con successo.")
        except psycopg2.pool.PoolError as pe:
            self.logger.error(
                "transaction(): impossibile ottenere connessione dal pool: %s", pe
            )
            raise psycopg2.OperationalError(
                f"Impossibile ottenere una connessione valida dal pool: {pe}"
            )
        except Exception as e:
            if conn:
                try:
                    conn.rollback()
                    self.logger.warning(
                        "transaction(): rollback eseguito per eccezione: %s", e
                    )
                except psycopg2.Error as rb_err:
                    self.logger.error(
                        "transaction(): errore durante rollback: %s", rb_err,
                        exc_info=True,
                    )
                    if isinstance(e, psycopg2.OperationalError):
                        self.logger.critical(
                            "transaction(): connessione persa — chiusura pool."
                        )
                        self.close_pool()
            raise
        finally:
            if conn:
                conn.autocommit = True   # Ripristina il default per il pool
                self.pool.putconn(conn)

    # ------------------------------------------------------------------ #
    #  Cache locale per modalità offline                                   #
    # ------------------------------------------------------------------ #

    def _cache_file(self, key: str):
        """Restituisce il Path del file JSON per la chiave data."""
        from pathlib import Path
        if self._cache_dir is None:
            return None
        return Path(self._cache_dir) / f"cache_{key}.json"

    def _save_cache(self, key: str, data) -> None:
        """Salva data nel file cache corrispondente alla chiave."""
        cf = self._cache_file(key)
        if cf is None:
            return
        try:
            payload = {"timestamp": datetime.now().isoformat(), "data": data}
            with open(cf, 'w', encoding='utf-8') as f:
                json.dump(payload, f, ensure_ascii=False, default=str)
        except Exception as e:
            self.logger.warning(f"Cache: impossibile salvare '{key}': {e}")

    def _load_cache(self, key: str) -> Tuple[Any, Optional[str]]:
        """Carica dal file cache. Restituisce (data, timestamp) o (None, None)."""
        cf = self._cache_file(key)
        if cf is None or not cf.exists():
            return None, None
        try:
            with open(cf, 'r', encoding='utf-8') as f:
                payload = json.load(f)
            return payload.get("data"), payload.get("timestamp")
        except Exception as e:
            self.logger.warning(f"Cache: impossibile leggere '{key}': {e}")
            return None, None

    def _try_with_cache(self, key: str, fetch_fn):
        """
        Esegue fetch_fn(). Se riesce salva in cache e azzera offline_mode.
        Se fallisce carica dalla cache e imposta offline_mode=True.
        """
        try:
            result = fetch_fn()
            self._save_cache(key, result)
            self.offline_mode = False
            return result
        except Exception as e:
            self.logger.warning(f"DB non raggiungibile ({e}); carico cache '{key}'.")
            cached, ts = self._load_cache(key)
            if cached is not None:
                self.offline_mode = True
                self.offline_cache_timestamp = ts
                return cached
            # Nessuna cache disponibile: rilancio l'eccezione originale
            raise

    def disconnect_pool_temporarily(self) -> bool:
        self.logger.info("Chiusura temporanea del pool di connessioni per operazione di ripristino...")
        self.close_pool() # Chiude e nullifica self.pool
        return True # Assume successo; close_pool gestisce i suoi log
    # In catasto_db_manager.py 

    def reconnect_pool_if_needed(self) -> bool:
        """
        Tenta di reinizializzare il pool di connessioni se non è attivo e ne verifica il funzionamento.
        Utilizza il pattern corretto con il context manager _get_connection.
        """
        self.logger.info("Tentativo di ricreare/verificare il pool di connessioni...")
        
        # 1. Tenta di inizializzare il pool se è None
        if not self.pool:
            self.logger.info("Pool non attivo. Tentativo di reinizializzazione...")
            if not self.initialize_main_pool():
                self.logger.error("Fallimento nella reinizializzazione del pool durante reconnect_pool_if_needed.")
                return False
                
        # 2. Verifica che il pool esista e sia funzionante tentando di ottenere una connessione
        if self.pool:
            try:
                # CORREZIONE: Usa 'with' per ottenere e rilasciare automaticamente la connessione.
                # Se questo blocco viene eseguito senza errori, significa che il pool funziona.
                with self._get_connection():
                    self.logger.info("Pool ricreato/verificato e testato con successo dopo riconnessione.")
                return True
            except (DBMError, psycopg2.pool.PoolError) as e:
                # _get_connection solleverà una di queste eccezioni se il pool ha problemi.
                self.logger.error(f"Pool sembra esistere, ma il test di connessione è fallito: {e}", exc_info=False)
                return False
        else:
            # Se self.pool è ancora None dopo il tentativo di initialize_main_pool()
            self.logger.error("Fallimento critico: il pool è ancora None dopo il tentativo di reinizializzazione.")
            return False

    def get_current_dbname(self) -> Optional[str]:
        if hasattr(self, '_main_db_conn_params') and self._main_db_conn_params: # DEVE USARE _main_db_conn_params
            return self._main_db_conn_params.get("dbname")
        # Aggiorna anche il messaggio di log se vuoi essere preciso
        self.logger.warning("Tentativo di accesso a dbname fallito: _main_db_conn_params non trovato o vuoto.")
        return None

    def get_current_user(self) -> Optional[str]:
        if hasattr(self, '_main_db_conn_params') and self._main_db_conn_params: # DEVE USARE _main_db_conn_params
            return self._main_db_conn_params.get("user")
        self.logger.warning("Tentativo di accesso a user fallito: _main_db_conn_params non trovato o vuoto.")
        return None

    def get_connection_parameters(self) -> Dict[str, Any]:
        if hasattr(self, '_main_db_conn_params') and self._main_db_conn_params: # DEVE USARE _main_db_conn_params
            params_copy = self._main_db_conn_params.copy()
            params_copy.pop('password', None) 
            return params_copy
        self.logger.warning("Tentativo di accesso ai parametri di connessione fallito: _main_db_conn_params non definito.")
        return {}
    def get_last_connect_error_details(self) -> Optional[Dict[str, str]]:
        """Restituisce i dettagli dell'ultimo errore di connessione occorso."""
        return self.last_connection_error
    

    
    def fetchall(self) -> List[Dict]:
        """Recupera tutti i risultati dell'ultima query come lista di dizionari."""
        # Utilizza self.cursor, che è impostato da execute_query
        if self.cursor and not self.cursor.closed:
            try:
                # Il DictCursor restituisce già dict-like rows, quindi dict(row) potrebbe essere ridondante
                # ma non è dannoso. Se self.cursor.fetchall() restituisce già una lista di dict (o DictRow),
                # la conversione esplicita potrebbe non essere necessaria.
                # Per sicurezza e chiarezza, lasciamola se DictCursor non restituisce dict nativi.
                # Se DictCursor restituisce oggetti DictRow, sono già simili a dizionari.
                risultati = self.cursor.fetchall()
                # Se DictCursor è usato, ogni 'row' in 'risultati' è già un oggetto simile a un dizionario.
                # La conversione [dict(row) for row in ...] è sicura.
                return risultati # Se DictCursor restituisce direttamente una lista di dizionari (o oggetti DictRow)
                # oppure: return [dict(row) for row in risultati] # Se necessario convertire esplicitamente
            except psycopg2.ProgrammingError: # Si verifica se si tenta di fetch da una query che non restituisce risultati
                self.logger.warning("Nessun risultato da recuperare per l'ultima query (fetchall).")
                return []
            except Exception as e:
                self.logger.error(f"Errore generico durante fetchall: {e}")
                return []
        else: # self.cursor è None o è chiuso
            self.logger.warning("Tentativo di fetchall senza un cursore valido o su un cursore chiuso.")
            return []

    def fetchone(self) -> Optional[Dict[str, Any]]:
        """Recupera una riga dal cursore."""
        if self.cursor: # Verifica che il cursore esista
            try:
                return self.cursor.fetchone()
            except psycopg2.Error as e:
                self.logger.error(f"Errore DB durante fetchone: {e}")
                return None
        else:
            self.logger.warning("Tentativo di fetchone senza un cursore valido.")
            return None

    # ------------------------------------------------------------------ #
    #  Helper Methods (TIER 1 improvements)                              #
    # ------------------------------------------------------------------ #

    def _tag_query(self, query: str, method_name: str, action: str = "read") -> str:
        """
        Prepend SQL comment with method name and action for debugging.
        Useful with pg_stat_statements to trace query source.

        Example:
            query = self._tag_query(
                "SELECT * FROM partita WHERE id = %s",
                method_name="get_partita",
                action="read"
            )
            cur.execute(query, (partita_id,))
        """
        return f"/* {method_name}:{action} */ {query}"

    def bulk_insert_with_savepoint(
        self,
        table: str,
        records: List[Dict[str, Any]],
        check_unique: Optional[Tuple[str, ...]] = None
    ) -> Dict[str, Any]:
        """
        Insert lista di record con SAVEPOINT per riga (fault-tolerant).
        Se un record fallisce, usa ROLLBACK TO SAVEPOINT per isolarlo.

        Args:
            table: Nome tabella (non-qualified, schema aggiunto automaticamente)
            records: Lista di dict {colonna: valore}
            check_unique: Tuple colonne uniche da loggare (info only, es. ('numero_partita',))

        Returns:
            {
                "success": [record, ...],  # Records inseriti
                "errors": [
                    {"row": line_number, "error": "msg", "data": record},
                    ...
                ]
            }

        Example:
            result = db.bulk_insert_with_savepoint("partita", [
                {"numero_partita": 1, "stato": "Attiva"},
                {"numero_partita": 2, "stato": "Inattiva"},
            ])
        """
        if not records:
            return {"success": [], "errors": []}

        success = []
        errors = []

        try:
            with self._get_connection() as conn:
                with conn.cursor(cursor_factory=DictCursor) as cur:
                    first_record = records[0]
                    columns = list(first_record.keys())
                    placeholders = ", ".join(["%s"] * len(columns))

                    for i, record in enumerate(records):
                        line_num = i + 2  # Riga CSV (header è riga 1)
                        cur.execute("SAVEPOINT record_sp")

                        try:
                            values = tuple(record.get(col) for col in columns)
                            insert_sql = (
                                f"INSERT INTO {self.schema}.{table} ({', '.join(columns)}) "
                                f"VALUES ({placeholders})"
                            )
                            cur.execute(insert_sql, values)
                            success.append(record)
                            self.logger.debug(f"bulk_insert({table}): riga {line_num} inserita")

                        except Exception as e:
                            cur.execute("ROLLBACK TO SAVEPOINT record_sp")
                            error_msg = str(e)
                            errors.append({
                                "row": line_num,
                                "error": error_msg,
                                "data": record
                            })
                            self.logger.warning(
                                f"bulk_insert({table}): riga {line_num} skipped: {error_msg}"
                            )

                    conn.commit()

        except Exception as e:
            self.logger.error(
                f"bulk_insert_with_savepoint({table}): errore fatale: {e}",
                exc_info=True
            )
            raise

        self.logger.info(
            f"bulk_insert({table}): {len(success)} success, {len(errors)} errors"
        )
        return {"success": success, "errors": errors}

    # ---- TIER 3 Phase 3: Safe Query Binding Helpers ----

    def build_select_query(self, table: str, columns: List[str], where_clause: Optional[str] = None,
                          order_by: Optional[str] = None) -> str:
        """
        TIER 3 Phase 3: Costruisce una SELECT query sicura con binding.
        Usa psycopg2.sql per table/column identification.

        Esempio:
            query = db.build_select_query("possessore", ["id", "nome_completo"],
                                         where_clause="id = %s", order_by="nome_completo")
        """
        safe_table = sql.Identifier(self.schema, table)
        safe_columns = sql.SQL(", ").join([sql.Identifier(col) for col in columns])

        query = sql.SQL("SELECT {} FROM {}").format(safe_columns, safe_table)

        if where_clause:
            query += sql.SQL(" WHERE {}").format(sql.SQL(where_clause))
        if order_by:
            query += sql.SQL(" ORDER BY {}").format(sql.SQL(order_by))

        return query.as_string(self.pool.getconn() if self.pool else None)

    def build_insert_query(self, table: str, columns: Dict[str, Any]) -> Tuple[str, List[Any]]:
        """
        TIER 3 Phase 3: Costruisce una INSERT query sicura.
        columns: dict {column_name: value}
        Restituisce (query, params) pronto per execute.

        Esempio:
            query, params = db.build_insert_query("possessore",
                                                 {"nome_completo": "Mario Rossi", "cognome_nome": "Rossi Mario"})
        """
        safe_table = sql.Identifier(self.schema, table)
        col_names = list(columns.keys())
        safe_columns = sql.SQL(", ").join([sql.Identifier(col) for col in col_names])
        placeholders = sql.SQL(", ").join([sql.Placeholder()] * len(col_names))

        query = sql.SQL("INSERT INTO {} ({}) VALUES ({})").format(
            safe_table, safe_columns, placeholders
        )

        return query.as_string(self.pool.getconn() if self.pool else None), list(columns.values())

    def clear_immutable_caches(self, cache_keys: Optional[List[str]] = None) -> None:
        """
        TIER 3 Phase 4: Invalida i cache di dati immutabili dopo modifiche.
        cache_keys: lista di chiavi di cache da invalidare (default: tutte le lookup tables)
        """
        if cache_keys is None:
            cache_keys = ["tipi_localita", "periodi_storici", "comuni_semplice", "statistiche_comune"]

        for key in cache_keys:
            cf = self._cache_file(key)
            if cf and cf.exists():
                try:
                    cf.unlink()
                    self.logger.info(f"Cache invalidato: {key}")
                except Exception as e:
                    self.logger.warning(f"Impossibile invalidare cache {key}: {e}")
