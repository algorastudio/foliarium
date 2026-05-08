-- =============================================================================
-- 07a_bootstrap_admin.sql
-- Crea l'utente amministratore iniziale dell'applicazione (NON il superuser DB).
--
-- Uso:
--   psql -v admin_password='<password>' -v admin_email='<email>' -f 07a_bootstrap_admin.sql
--
-- Se admin_password non è passata, viene usato il default 'admin123' (solo dev).
-- L'hash bcrypt viene generato dinamicamente via pgcrypto (compatibile con
-- la libreria Python `bcrypt` usata dall'app: prefisso $2a accettato da bcrypt).
--
-- Idempotente: se l'utente 'admin' esiste già, non viene toccato.
-- =============================================================================

CREATE EXTENSION IF NOT EXISTS pgcrypto;

\set ON_ERROR_STOP on

-- Default per le variabili psql non passate da -v
\if :{?admin_password}
\else
  \set admin_password '\'admin123\''
\endif

\if :{?admin_email}
\else
  \set admin_email '\'admin@archivio.local\''
\endif

DO $$
DECLARE
    v_admin_username TEXT := 'admin';
    v_admin_password TEXT := :'admin_password';
    v_admin_email    TEXT := :'admin_email';
    v_admin_hash     TEXT;
    v_user_exists    BOOLEAN;
BEGIN
    SELECT EXISTS(
        SELECT 1 FROM catasto.utente WHERE username = v_admin_username
    ) INTO v_user_exists;

    IF v_user_exists THEN
        RAISE NOTICE 'Utente "%" già esistente, password non modificata.', v_admin_username;
    ELSE
        v_admin_hash := crypt(v_admin_password, gen_salt('bf', 12));

        INSERT INTO catasto.utente (
            username, password_hash, nome_completo, email, ruolo, attivo
        ) VALUES (
            v_admin_username, v_admin_hash, 'Amministratore Sistema',
            v_admin_email, 'admin', TRUE
        );

        RAISE NOTICE 'Utente amministratore "%" creato con email %.',
            v_admin_username, v_admin_email;
    END IF;
END $$;
