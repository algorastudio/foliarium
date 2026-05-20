-- =============================================================================
-- 05_fix_mv_ownership.sql
-- Trasferisce l'ownership delle materialized view dello schema applicativo
-- all'utente che la GUI userà per il REFRESH.
--
-- Contesto:
--   PostgreSQL (<= 16) richiede che `REFRESH MATERIALIZED VIEW` sia eseguito
--   dal proprietario della MV; non basta `GRANT`. Se le MV sono state create
--   da `postgres` (superuser di setup) ma la GUI si connette con un utente
--   applicativo dedicato, ogni refresh fallisce con `InsufficientPrivilege`.
--
-- Uso:
--   psql -U postgres -d catasto_storico \
--        -v target_user=foliarium_app \
--        -f sql_scripts/admin/05_fix_mv_ownership.sql
--
--   Variabile opzionale: target_schema (default: catasto)
--
-- Richiede:
--   Connessione come superuser o come owner corrente delle MV (solo loro
--   possono trasferire l'ownership).
--
-- Idempotente: ri-eseguibile in sicurezza, l'ALTER OWNER è no-op se l'owner
-- corrisponde già al target.
-- =============================================================================

\set ON_ERROR_STOP on

\if :{?target_user}
\else
  \echo 'ERRORE: variabile target_user non impostata.'
  \echo 'Uso: psql -v target_user=foliarium_app -f 05_fix_mv_ownership.sql'
  \quit
\endif

\if :{?target_schema}
\else
  \set target_schema catasto
\endif

-- Esponiamo i parametri come GUC per renderli leggibili dentro il DO block
-- (la sostituzione `:'name'` non funziona dentro `$$ ... $$`).
SET LOCAL foliarium.target_user = :'target_user';
SET LOCAL foliarium.target_schema = :'target_schema';

DO $$
DECLARE
    v_target text := current_setting('foliarium.target_user');
    v_schema text := current_setting('foliarium.target_schema');
    r        RECORD;
    v_count  int := 0;
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = v_target) THEN
        RAISE EXCEPTION 'Ruolo "%" non esiste. Crearlo prima di trasferire ownership.', v_target;
    END IF;

    FOR r IN
        SELECT schemaname, matviewname, matviewowner
        FROM pg_matviews
        WHERE schemaname = v_schema
        ORDER BY matviewname
    LOOP
        IF r.matviewowner = v_target THEN
            RAISE NOTICE 'OK   %.% gia di proprieta di %', r.schemaname, r.matviewname, v_target;
        ELSE
            EXECUTE format(
                'ALTER MATERIALIZED VIEW %I.%I OWNER TO %I',
                r.schemaname, r.matviewname, v_target
            );
            v_count := v_count + 1;
            RAISE NOTICE 'MOVE %.% (% -> %)', r.schemaname, r.matviewname, r.matviewowner, v_target;
        END IF;
    END LOOP;

    IF v_count = 0 THEN
        RAISE NOTICE 'Nessun trasferimento necessario nello schema "%".', v_schema;
    ELSE
        RAISE NOTICE 'Totale ownership trasferite: %', v_count;
    END IF;
END $$;
