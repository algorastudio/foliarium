-- =============================================================================
-- 07a_bootstrap_admin.sql
-- Crea l'utente amministratore iniziale dell'applicazione (NON il superuser DB).
--
-- Uso:
--   psql -v admin_password=mia_password -v admin_email=admin@host \
--        -f 07a_bootstrap_admin.sql
--
-- Se admin_password non è passata, viene usato il default 'admin123' (solo dev).
-- L'hash bcrypt viene generato dinamicamente via pgcrypto (compatibile con
-- la libreria Python `bcrypt` usata dall'app: prefisso $2a accettato da bcrypt).
--
-- Nota: la sostituzione delle variabili psql (`:'name'`) NON funziona dentro
-- i blocchi $$ ... $$, quindi usiamo un INSERT diretto con guard idempotente.
--
-- Idempotente: se l'utente 'admin' esiste già, non viene toccato.
-- =============================================================================

CREATE EXTENSION IF NOT EXISTS pgcrypto;

\set ON_ERROR_STOP on

-- La variabile admin_password è obbligatoria; senza di essa lo script si interrompe.
\if :{?admin_password}
\else
  \echo 'ERRORE: variabile admin_password non impostata.'
  \echo 'Uso: psql -v admin_password=password_sicura -f 07a_bootstrap_admin.sql'
  \quit
\endif

\if :{?admin_email}
\else
  \set admin_email admin@archivio.local
\endif

INSERT INTO catasto.utente (
    username, password_hash, nome_completo, email, ruolo, attivo
)
SELECT
    'admin',
    crypt(:'admin_password', gen_salt('bf', 12)),
    'Amministratore Sistema',
    :'admin_email',
    'admin',
    TRUE
WHERE NOT EXISTS (
    SELECT 1 FROM catasto.utente WHERE username = 'admin'
);
