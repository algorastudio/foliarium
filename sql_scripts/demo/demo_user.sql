-- =============================================================================
-- demo/demo_user.sql
-- Crea l'utente applicativo `demo`, quello con cui la modalita' demo
-- (FOLIARIUM_DEMO=1) entra automaticamente: vedi config.DEMO_LOGIN_USER e
-- il blocco "MODALITA' DEMO" di gui_main.py.
--
-- Uso:
--   psql -v ON_ERROR_STOP=1 -v demo_password=la_password -f demo_user.sql
--
-- Il ruolo e' `admin` perche' la demo deve mostrare tutte le funzioni,
-- comprese quelle di amministrazione. Va usato solo su database
-- dimostrativi, che si ripristinano da capo.
--
-- A differenza di admin/04_bootstrap_admin.sql, se la variabile manca lo
-- script FALLISCE invece di uscire in silenzio: un `\quit` termina psql con
-- codice 0, e chi lo invoca crede che l'utente sia stato creato.
--
-- Idempotente: se l'utente `demo` esiste gia', non viene toccato.
-- =============================================================================

CREATE EXTENSION IF NOT EXISTS pgcrypto;

\set ON_ERROR_STOP on

\if :{?demo_password}
\else
  \echo 'ERRORE: variabile demo_password non impostata.'
  \echo 'Uso: psql -v demo_password=la_password -f demo_user.sql'
  DO $$ BEGIN RAISE EXCEPTION 'demo_password non impostata'; END $$;
\endif

-- La sostituzione delle variabili psql (:'nome') non funziona dentro i
-- blocchi $$ ... $$: per questo un INSERT diretto con guardia.
INSERT INTO catasto.utente (
    username, password_hash, nome_completo, email, ruolo, attivo
)
SELECT
    'demo',
    crypt(:'demo_password', gen_salt('bf', 12)),
    'Utente Demo',
    'demo@archivio.local',
    'admin',
    TRUE
WHERE NOT EXISTS (
    SELECT 1 FROM catasto.utente WHERE username = 'demo'
);
