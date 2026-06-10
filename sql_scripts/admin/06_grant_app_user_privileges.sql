-- =============================================================================
-- 06_grant_app_user_privileges.sql
-- Concede all'utente applicativo tutti i privilegi necessari per:
--   - operare normalmente dall'app (SELECT/INSERT/UPDATE/DELETE)
--   - eseguire pg_dump (richiede SELECT/USAGE su sequenze, oltre alle tabelle)
--
-- Contesto:
--   Le migrazioni successive al setup iniziale possono creare nuove tabelle
--   e sequenze senza riapplicare i GRANT. Risultato: l'utente applicativo
--   funziona per le tabelle ereditate ma fallisce con `permesso negato per
--   la sequenza X_seq` quando pg_dump le legge.
--
-- Uso:
--   psql -U postgres -d catasto_storico \
--        -v target_user=foliarium \
--        -f sql_scripts/admin/06_grant_app_user_privileges.sql
--
--   Variabile opzionale: target_schema (default: catasto)
--
-- Richiede:
--   Connessione come superuser o come owner degli oggetti.
--
-- Idempotente: GRANT e ALTER DEFAULT PRIVILEGES sono no-op se i privilegi
-- esistono già. Ri-eseguibile in sicurezza.
-- =============================================================================

\set ON_ERROR_STOP on

\if :{?target_user}
\else
  \echo 'ERRORE: variabile target_user non impostata.'
  \echo 'Uso: psql -v target_user=foliarium -f 06_grant_app_user_privileges.sql'
  \quit
\endif

\if :{?target_schema}
\else
  \set target_schema catasto
\endif

\echo 'Concessione privilegi a:' :target_user 'su schema:' :target_schema

-- Schema
GRANT USAGE ON SCHEMA :target_schema TO :target_user;

-- Oggetti esistenti
GRANT SELECT, INSERT, UPDATE, DELETE
    ON ALL TABLES IN SCHEMA :target_schema
    TO :target_user;

GRANT USAGE, SELECT, UPDATE
    ON ALL SEQUENCES IN SCHEMA :target_schema
    TO :target_user;

GRANT EXECUTE
    ON ALL FUNCTIONS IN SCHEMA :target_schema
    TO :target_user;

-- Oggetti futuri (creati da chi esegue questo script). Se le migration
-- vengono applicate da postgres, e' postgres che dobbiamo settare come
-- "FOR ROLE". Per coprire entrambi i casi, settiamo i default privileges
-- sia per il ruolo corrente (chi sta eseguendo) sia per postgres.
ALTER DEFAULT PRIVILEGES IN SCHEMA :target_schema
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO :target_user;

ALTER DEFAULT PRIVILEGES IN SCHEMA :target_schema
    GRANT USAGE, SELECT, UPDATE ON SEQUENCES TO :target_user;

ALTER DEFAULT PRIVILEGES IN SCHEMA :target_schema
    GRANT EXECUTE ON FUNCTIONS TO :target_user;

ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA :target_schema
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO :target_user;

ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA :target_schema
    GRANT USAGE, SELECT, UPDATE ON SEQUENCES TO :target_user;

ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA :target_schema
    GRANT EXECUTE ON FUNCTIONS TO :target_user;

\echo 'Privilegi concessi. Verifica veloce delle sequenze:'

SELECT
    sequencename,
    has_sequence_privilege(:'target_user', schemaname || '.' || sequencename, 'SELECT') AS can_select,
    has_sequence_privilege(:'target_user', schemaname || '.' || sequencename, 'USAGE')  AS can_usage,
    has_sequence_privilege(:'target_user', schemaname || '.' || sequencename, 'UPDATE') AS can_update
FROM pg_sequences
WHERE schemaname = :'target_schema'
ORDER BY sequencename;
