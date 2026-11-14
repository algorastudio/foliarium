-- sql_scripts/migrations/23_add_fk_audit_log_utente.sql
--
-- Migrazione idempotente: crea la chiave esterna
--     catasto.audit_log.app_user_id -> catasto.utente.id  (ON DELETE SET NULL)
-- sui database che non ce l'hanno.
--
-- Chi non ce l'ha. Fino alla v1.0.2 `setup_database.py` applicava
-- `functions/06_audit.sql` prima di `admin/01_users.sql`, cioe' prima che
-- la tabella `utente` esistesse: l'istruzione falliva e, senza
-- ON_ERROR_STOP, l'installazione proseguiva. Tutti i database creati
-- dall'installer sono quindi privi del vincolo. Quelli creati con gli
-- script numerati (15_integration_audit_users.sql) o con i container
-- Docker lo hanno gia': per loro questo script non fa nulla.
--
-- Effetto dell'assenza. Eliminando un utente, le sue righe di `audit_log`
-- conservano un `app_user_id` che non corrisponde piu' a nessuno, invece
-- di diventare NULL.
--
-- L'applicazione esegue la stessa operazione da sola all'avvio
-- (db/base.py, _ensure_audit_user_fk). Questo script serve quando il ruolo
-- dell'applicazione non puo' modificare le tabelle: va eseguito come
-- proprietario o superuser.
--
-- Esecuzione:
--   psql -U postgres -d catasto_storico -f 23_add_fk_audit_log_utente.sql
--
-- Il registro di audit NON viene riscritto. Se esistono gia' righe di
-- utenti eliminati, il vincolo viene creato NOT VALID: vale per le righe
-- nuove e per le eliminazioni future, mentre le righe esistenti restano
-- come sono (conservano l'identificativo dell'utente che non c'e' piu').
-- Chi preferisce allinearle al comportamento del vincolo puo' farlo a
-- mano, dopo averlo deciso:
--
--   UPDATE catasto.audit_log al SET app_user_id = NULL
--    WHERE al.app_user_id IS NOT NULL
--      AND NOT EXISTS (SELECT 1 FROM catasto.utente u WHERE u.id = al.app_user_id);
--   ALTER TABLE catasto.audit_log VALIDATE CONSTRAINT fk_audit_log_app_user_id_utente;

DO $$
DECLARE
    v_orfane BIGINT;
BEGIN
    IF EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'fk_audit_log_app_user_id_utente'
          AND conrelid = 'catasto.audit_log'::regclass
    ) THEN
        RAISE NOTICE 'Chiave esterna fk_audit_log_app_user_id_utente gia'' presente: nulla da fare.';
        RETURN;
    END IF;

    -- NOT VALID: nessuna scansione della tabella, riesce anche con righe orfane.
    ALTER TABLE catasto.audit_log
        ADD CONSTRAINT fk_audit_log_app_user_id_utente
        FOREIGN KEY (app_user_id) REFERENCES catasto.utente(id)
        ON DELETE SET NULL NOT VALID;

    -- La convalida riesce solo se non ci sono righe orfane. Il blocco
    -- annidato apre un savepoint: se fallisce, il vincolo creato sopra resta.
    BEGIN
        ALTER TABLE catasto.audit_log
            VALIDATE CONSTRAINT fk_audit_log_app_user_id_utente;
        RAISE NOTICE 'Chiave esterna fk_audit_log_app_user_id_utente creata e convalidata.';
    EXCEPTION WHEN foreign_key_violation THEN
        SELECT count(*) INTO v_orfane
          FROM catasto.audit_log al
         WHERE al.app_user_id IS NOT NULL
           AND NOT EXISTS (SELECT 1 FROM catasto.utente u WHERE u.id = al.app_user_id);
        RAISE NOTICE 'Chiave esterna fk_audit_log_app_user_id_utente creata senza convalida: % righe di audit appartengono a utenti gia'' eliminati e non sono state modificate.', v_orfane;
    END;
END $$;
