-- File: 18_funzioni_trigger_audit.sql
-- Oggetto: Creazione della funzione trigger generica per l'audit e associazione alle tabelle.
-- Versione: 1.0
-- Data: 24/05/2025

SET search_path TO catasto, public; -- Assicurati che lo schema sia corretto

-- ========================================================================
-- Funzione Trigger Generica per Audit Log
-- ========================================================================
CREATE OR REPLACE FUNCTION catasto.log_audit_trigger_function()
RETURNS TRIGGER AS $$
DECLARE
    v_old_data JSONB;
    v_new_data JSONB;
    v_app_user_id INTEGER;
    v_session_id TEXT;
    v_ip_address TEXT;
    v_record_id_text TEXT; -- Per gestire PK come testo prima della conversione
BEGIN
    -- Tentativo di recuperare le variabili di sessione impostate dall'applicazione
    BEGIN
        v_app_user_id := current_setting('catasto.app_user_id', true)::INTEGER;
    EXCEPTION WHEN OTHERS THEN
        v_app_user_id := NULL; -- Lascia NULL se non impostata o errore
    END;

    BEGIN
        v_session_id := current_setting('catasto.session_id', true);
    EXCEPTION WHEN OTHERS THEN
        v_session_id := NULL; -- Lascia NULL se non impostata o errore
    END;

    BEGIN
        v_ip_address := inet_client_addr()::TEXT; -- IP del client connesso al DB
    EXCEPTION WHEN OTHERS THEN
        v_ip_address := NULL; -- Lascia NULL in caso di errore (es. chiamata non da client)
    END;

    -- Determina i dati vecchi, nuovi e l'ID del record
    IF (TG_OP = 'INSERT') THEN
        v_new_data := to_jsonb(NEW);
        v_old_data := NULL;
        -- Assumendo che la PK si chiami 'id'
        IF TG_TABLE_SCHEMA IS NOT NULL AND TG_TABLE_NAME IS NOT NULL THEN
             -- Controlla se la colonna 'id' esiste per la tabella NEW
            IF (SELECT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = TG_TABLE_SCHEMA AND table_name = TG_TABLE_NAME AND column_name = 'id')) THEN
                 v_record_id_text := (NEW.id)::TEXT;
            ELSE
                 v_record_id_text := NULL;
            END IF;
        ELSE
            v_record_id_text := NULL;
        END IF;

    ELSIF (TG_OP = 'UPDATE') THEN
        v_old_data := to_jsonb(OLD);
        v_new_data := to_jsonb(NEW);
        IF TG_TABLE_SCHEMA IS NOT NULL AND TG_TABLE_NAME IS NOT NULL THEN
            IF (SELECT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = TG_TABLE_SCHEMA AND table_name = TG_TABLE_NAME AND column_name = 'id')) THEN
                 v_record_id_text := (NEW.id)::TEXT; -- o OLD.id, dovrebbe essere lo stesso per la PK
            ELSE
                 v_record_id_text := NULL;
            END IF;
        ELSE
            v_record_id_text := NULL;
        END IF;

    ELSIF (TG_OP = 'DELETE') THEN
        v_old_data := to_jsonb(OLD);
        v_new_data := NULL;
        IF TG_TABLE_SCHEMA IS NOT NULL AND TG_TABLE_NAME IS NOT NULL THEN
            IF (SELECT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = TG_TABLE_SCHEMA AND table_name = TG_TABLE_NAME AND column_name = 'id')) THEN
                 v_record_id_text := (OLD.id)::TEXT;
            ELSE
                 v_record_id_text := NULL;
            END IF;
        ELSE
            v_record_id_text := NULL;
        END IF;
    END IF;

    -- Inserimento nel log di audit
    INSERT INTO catasto.audit_log (
        tabella,
        operazione,
        record_id,    -- Colonna INTEGER in audit_log
        dati_prima,
        dati_dopo,
        utente,       -- Utente del database (session_user o current_user)
        ip_address,
        app_user_id,  -- ID utente dell'applicazione Python
        session_id    -- ID sessione dell'applicazione Python
    )
    VALUES (
        TG_TABLE_NAME,
        LEFT(TG_OP, 1), -- 'I', 'U', o 'D'
        CASE -- Converte in INTEGER se v_record_id_text è numerico, altrimenti NULL
            WHEN v_record_id_text ~ '^[0-9]+$' THEN v_record_id_text::INTEGER
            ELSE NULL
        END,
        v_old_data,
        v_new_data,
        session_user, -- L'utente della sessione DB corrente
        v_ip_address,
        v_app_user_id,
        v_session_id
    );

    -- Valore di ritorno corretto per i trigger AFTER
    IF (TG_OP = 'DELETE') THEN
        RETURN OLD;
    ELSE
        RETURN NEW;
    END IF;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION catasto.log_audit_trigger_function() IS
'Funzione trigger generica per registrare modifiche (INSERT, UPDATE, DELETE) nella tabella audit_log.
Tenta di recuperare app_user_id e session_id dalle impostazioni di sessione PostgreSQL (es. catasto.app_user_id, catasto.session_id).
Assume che le tabelle auditate abbiano una PK chiamata ''id''.';

-- ========================================================================
-- Creazione dei Trigger di Audit per le Tabelle
-- ========================================================================

-- Tabella: comune
DROP TRIGGER IF EXISTS audit_trigger_comune ON catasto.comune;
CREATE TRIGGER audit_trigger_comune
AFTER INSERT OR UPDATE OR DELETE ON catasto.comune
    FOR EACH ROW EXECUTE FUNCTION catasto.log_audit_trigger_function();
COMMENT ON TRIGGER audit_trigger_comune ON catasto.comune IS 'Trigger per audit sulla tabella comune.';

-- Tabella: registro_partite
DROP TRIGGER IF EXISTS audit_trigger_registro_partite ON catasto.registro_partite;
CREATE TRIGGER audit_trigger_registro_partite
AFTER INSERT OR UPDATE OR DELETE ON catasto.registro_partite
    FOR EACH ROW EXECUTE FUNCTION catasto.log_audit_trigger_function();
COMMENT ON TRIGGER audit_trigger_registro_partite ON catasto.registro_partite IS 'Trigger per audit sulla tabella registro_partite.';

-- Tabella: registro_matricole
DROP TRIGGER IF EXISTS audit_trigger_registro_matricole ON catasto.registro_matricole;
CREATE TRIGGER audit_trigger_registro_matricole
AFTER INSERT OR UPDATE OR DELETE ON catasto.registro_matricole
    FOR EACH ROW EXECUTE FUNCTION catasto.log_audit_trigger_function();
COMMENT ON TRIGGER audit_trigger_registro_matricole ON catasto.registro_matricole IS 'Trigger per audit sulla tabella registro_matricole.';

-- Tabella: partita
DROP TRIGGER IF EXISTS audit_trigger_partita ON catasto.partita;
CREATE TRIGGER audit_trigger_partita
AFTER INSERT OR UPDATE OR DELETE ON catasto.partita
    FOR EACH ROW EXECUTE FUNCTION catasto.log_audit_trigger_function();
COMMENT ON TRIGGER audit_trigger_partita ON catasto.partita IS 'Trigger per audit sulla tabella partita.';

-- Tabella: possessore
DROP TRIGGER IF EXISTS audit_trigger_possessore ON catasto.possessore;
CREATE TRIGGER audit_trigger_possessore
AFTER INSERT OR UPDATE OR DELETE ON catasto.possessore
    FOR EACH ROW EXECUTE FUNCTION catasto.log_audit_trigger_function();
COMMENT ON TRIGGER audit_trigger_possessore ON catasto.possessore IS 'Trigger per audit sulla tabella possessore.';

-- Tabella: partita_possessore (Tabella di relazione)
DROP TRIGGER IF EXISTS audit_trigger_partita_possessore ON catasto.partita_possessore;
CREATE TRIGGER audit_trigger_partita_possessore
AFTER INSERT OR UPDATE OR DELETE ON catasto.partita_possessore
    FOR EACH ROW EXECUTE FUNCTION catasto.log_audit_trigger_function();
COMMENT ON TRIGGER audit_trigger_partita_possessore ON catasto.partita_possessore IS 'Trigger per audit sulla tabella partita_possessore.';

-- Tabella: localita
DROP TRIGGER IF EXISTS audit_trigger_localita ON catasto.localita;
CREATE TRIGGER audit_trigger_localita
AFTER INSERT OR UPDATE OR DELETE ON catasto.localita
    FOR EACH ROW EXECUTE FUNCTION catasto.log_audit_trigger_function();
COMMENT ON TRIGGER audit_trigger_localita ON catasto.localita IS 'Trigger per audit sulla tabella localita.';

-- Tabella: immobile
DROP TRIGGER IF EXISTS audit_trigger_immobile ON catasto.immobile;
CREATE TRIGGER audit_trigger_immobile
AFTER INSERT OR UPDATE OR DELETE ON catasto.immobile
    FOR EACH ROW EXECUTE FUNCTION catasto.log_audit_trigger_function();
COMMENT ON TRIGGER audit_trigger_immobile ON catasto.immobile IS 'Trigger per audit sulla tabella immobile.';

-- Tabella: partita_relazione (Tabella di relazione)
DROP TRIGGER IF EXISTS audit_trigger_partita_relazione ON catasto.partita_relazione;
CREATE TRIGGER audit_trigger_partita_relazione
AFTER INSERT OR UPDATE OR DELETE ON catasto.partita_relazione
    FOR EACH ROW EXECUTE FUNCTION catasto.log_audit_trigger_function();
COMMENT ON TRIGGER audit_trigger_partita_relazione ON catasto.partita_relazione IS 'Trigger per audit sulla tabella partita_relazione.';

-- Tabella: variazione
DROP TRIGGER IF EXISTS audit_trigger_variazione ON catasto.variazione;
CREATE TRIGGER audit_trigger_variazione
AFTER INSERT OR UPDATE OR DELETE ON catasto.variazione
    FOR EACH ROW EXECUTE FUNCTION catasto.log_audit_trigger_function();
COMMENT ON TRIGGER audit_trigger_variazione ON catasto.variazione IS 'Trigger per audit sulla tabella variazione.';

-- Tabella: contratto
DROP TRIGGER IF EXISTS audit_trigger_contratto ON catasto.contratto;
CREATE TRIGGER audit_trigger_contratto
AFTER INSERT OR UPDATE OR DELETE ON catasto.contratto
    FOR EACH ROW EXECUTE FUNCTION catasto.log_audit_trigger_function();
COMMENT ON TRIGGER audit_trigger_contratto ON catasto.contratto IS 'Trigger per audit sulla tabella contratto.';

-- Tabella: consultazione
-- Valuta se l'audit delle modifiche ai record di consultazione è necessario,
-- o se la tabella 'consultazione' è essa stessa una forma di log.
-- Se vuoi tracciare modifiche ai record di consultazione (es. correzioni a posteriori):
DROP TRIGGER IF EXISTS audit_trigger_consultazione ON catasto.consultazione;
CREATE TRIGGER audit_trigger_consultazione
AFTER INSERT OR UPDATE OR DELETE ON catasto.consultazione
    FOR EACH ROW EXECUTE FUNCTION catasto.log_audit_trigger_function();
COMMENT ON TRIGGER audit_trigger_consultazione ON catasto.consultazione IS 'Trigger per audit sulla tabella consultazione.';

-- NON creare un trigger sulla tabella audit_log stessa!
-- File: 18a_vista_audit_dettagliato.sql (v1.2)
-- Scopo: Crea o sostituisce la vista per i log di audit, formattando il timestamp.

SET search_path TO catasto, public;

CREATE OR REPLACE VIEW catasto.v_audit_dettagliato AS
SELECT
    al.id,
    -- CORREZIONE: Formatta il timestamp per rimuovere i millisecondi
    CAST(al.timestamp AS TIMESTAMP(0)) AS timestamp,
    al.app_user_id,
    u.username,
    u.nome_completo,
    al.session_id,
    al.tabella,
    al.operazione,
    al.record_id,
    al.ip_address,
    al.utente AS db_user,
    al.dati_prima,
    al.dati_dopo
FROM
    catasto.audit_log al
LEFT JOIN
    catasto.utente u ON al.app_user_id = u.id;

COMMENT ON VIEW catasto.v_audit_dettagliato IS 'Vista che unisce i log di audit con i nomi degli utenti applicativi (timestamp formattato).';

-- 'Vista v_audit_dettagliato creata/aggiornata con successo (timestamp formattato).'
-- ========================================================================
-- Fine Script
-- ========================================================================