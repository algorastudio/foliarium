-- Imposta lo schema
SET search_path TO catasto,public;

-- Tabella per gli utenti
CREATE TABLE IF NOT EXISTS catasto.utente (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL, -- Hash della password (NON salvare password in chiaro!)
    nome_completo VARCHAR(100) NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    ruolo VARCHAR(20) NOT NULL CHECK (ruolo IN ('admin', 'archivista', 'consultatore')),
    attivo BOOLEAN DEFAULT TRUE,
    ultimo_accesso TIMESTAMP(0),
    data_creazione TIMESTAMP(0) DEFAULT CURRENT_TIMESTAMP,
    data_modifica TIMESTAMP(0) DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_utente_username ON utente(username);
CREATE INDEX idx_utente_ruolo ON utente(ruolo);

-- Trigger per aggiornare il timestamp di modifica
-- Tabella per i permessi
CREATE TABLE permesso (
    id SERIAL PRIMARY KEY,
    nome VARCHAR(50) UNIQUE NOT NULL,
    descrizione TEXT
);

-- Tabella di collegamento tra utenti e permessi
CREATE TABLE utente_permesso (
    utente_id INTEGER REFERENCES utente(id) ON DELETE CASCADE,
    permesso_id INTEGER REFERENCES permesso(id) ON DELETE CASCADE,
    data_assegnazione TIMESTAMP(0) DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (utente_id, permesso_id)
);

-- Funzione per verificare se un utente ha un determinato permesso
CREATE OR REPLACE FUNCTION ha_permesso(p_utente_id INTEGER, p_permesso_nome VARCHAR)
RETURNS BOOLEAN AS $$
DECLARE
    v_ruolo VARCHAR(20);
    v_permesso_count INTEGER;
BEGIN
    -- Verifica se l'utente è attivo
    SELECT ruolo INTO v_ruolo FROM utente 
    WHERE id = p_utente_id AND attivo = TRUE;
    
    IF v_ruolo IS NULL THEN
        RETURN FALSE; -- Utente non trovato o non attivo
    END IF;
    
    -- Gli amministratori hanno tutti i permessi
    IF v_ruolo = 'admin' THEN
        RETURN TRUE;
    END IF;
    
    -- Verifica permessi specifici
    SELECT COUNT(*) INTO v_permesso_count
    FROM utente_permesso up
    JOIN permesso p ON up.permesso_id = p.id
    WHERE up.utente_id = p_utente_id AND p.nome = p_permesso_nome;
    
    RETURN v_permesso_count > 0;
END;
$$ LANGUAGE plpgsql;

-- Procedura per creare un nuovo utente (con password hash)
CREATE OR REPLACE PROCEDURE crea_utente(
    p_username VARCHAR(50),
    p_password VARCHAR(255), -- Questa dovrebbe essere già hashata nell'applicazione
    p_nome_completo VARCHAR(100),
    p_email VARCHAR(100),
    p_ruolo VARCHAR(20)
)
LANGUAGE plpgsql
AS $$
BEGIN
    INSERT INTO utente (username, password_hash, nome_completo, email, ruolo)
    VALUES (p_username, p_password, p_nome_completo, p_email, p_ruolo);
END;
$$;

-- Procedura per aggiornare l'ultimo accesso di un utente
-- In 07_user-management.sql (o in 19_creazione_tabella_sessioni.sql dopo la creazione della tabella)
CREATE OR REPLACE PROCEDURE catasto.registra_evento_sessione(
    p_utente_id INTEGER,
    p_id_sessione_uuid TEXT, -- UUID generato dall'app
    p_azione VARCHAR(50), -- 'login', 'logout', 'fail_login', 'timeout'
    p_esito BOOLEAN,
    p_indirizzo_ip VARCHAR(45) DEFAULT NULL,
    p_applicazione VARCHAR(100) DEFAULT NULL,
    p_dettagli TEXT DEFAULT NULL
)
LANGUAGE plpgsql
AS $$
BEGIN
    IF p_azione = 'login' AND p_esito = TRUE THEN
        INSERT INTO catasto.sessioni_accesso 
            (utente_id, id_sessione, data_login, indirizzo_ip, applicazione, azione, esito, dettagli, attiva)
        VALUES 
            (p_utente_id, p_id_sessione_uuid, CURRENT_TIMESTAMP, p_indirizzo_ip, p_applicazione, p_azione, p_esito, p_dettagli, TRUE);

        -- Aggiorna ultimo_accesso nella tabella utente
        UPDATE catasto.utente SET ultimo_accesso = CURRENT_TIMESTAMP WHERE id = p_utente_id;

    ELSIF p_azione = 'fail_login' THEN
        INSERT INTO catasto.sessioni_accesso
            (utente_id, id_sessione, data_login, indirizzo_ip, applicazione, azione, esito, dettagli, attiva)
        VALUES
            (p_utente_id, p_id_sessione_uuid, CURRENT_TIMESTAMP, p_indirizzo_ip, p_applicazione, p_azione, FALSE, p_dettagli, FALSE);
    -- Altri casi come 'logout', 'timeout' verranno gestiti da procedure specifiche
    -- che aggiornano record esistenti in sessioni_accesso.
    END IF;
END;
$$;
COMMENT ON PROCEDURE catasto.registra_evento_sessione IS 'Registra eventi di login o tentativi falliti nella tabella sessioni_accesso.';

CREATE OR REPLACE PROCEDURE catasto.logout_utente_sessione(
    p_utente_id INTEGER,
    p_id_sessione_uuid TEXT,
    p_client_ip VARCHAR(45) DEFAULT NULL,
    p_applicazione VARCHAR(100) DEFAULT NULL -- Assicurati che catasto.sessioni_accesso abbia questa colonna
)
LANGUAGE plpgsql
AS $$
BEGIN
    UPDATE catasto.sessioni_accesso
    SET data_logout = CURRENT_TIMESTAMP,
        attiva = FALSE,
        azione = 'logout', 
        esito = TRUE
        -- Puoi aggiornare p_indirizzo_ip e p_applicazione se necessario al logout
    WHERE utente_id = p_utente_id 
      AND id_sessione = p_id_sessione_uuid
      AND attiva = TRUE;

    RAISE NOTICE 'Logout registrato in sessioni_accesso per utente ID % (Sessione UUID: %)', p_utente_id, p_id_sessione_uuid;

EXCEPTION
    WHEN OTHERS THEN
        RAISE WARNING '[logout_utente_sessione] Errore durante la registrazione del logout per utente ID % (Sessione UUID: %): % - SQLSTATE: %', p_utente_id, p_id_sessione_uuid, SQLERRM, SQLSTATE;
END;
$$;
COMMENT ON PROCEDURE catasto.logout_utente_sessione IS 'Aggiorna la sessione attiva di un utente come terminata (logout) nella tabella sessioni_accesso.';


  

-- Inserimento permessi base
INSERT INTO catasto.permesso (nome, descrizione) VALUES
    ('visualizza_partite', 'Permesso di visualizzare le partite catastali'),
    ('modifica_partite', 'Permesso di modificare le partite catastali'),
    ('visualizza_possessori', 'Permesso di visualizzare i possessori'),
    ('modifica_possessori', 'Permesso di modificare i possessori'),
    ('visualizza_immobili', 'Permesso di visualizzare gli immobili'),
    ('modifica_immobili', 'Permesso di modificare gli immobili'),
    ('registra_variazioni', 'Permesso di registrare variazioni di proprietà'), -- Corretto "proprietà"
    ('gestione_utenti', 'Permesso di gestire gli utenti')
ON CONFLICT (nome) DO NOTHING; -- IL PUNTO E VIRGOLA VA QUI, ALLA FINE DELL'INTERA ISTRUZIONE INSERT


-- NOTA: la creazione dell'utente amministratore iniziale è gestita da
-- 07a_bootstrap_admin.sql, che riceve la password generata dall'installer
-- via psql -v admin_password=... e produce un hash bcrypt dinamico.
-- Eseguire questo script SENZA bootstrap_admin lascia il sistema senza admin.

-- Applicazione del trigger (corretto)
CREATE TRIGGER update_utente_modifica
BEFORE UPDATE ON catasto.utente
FOR EACH ROW EXECUTE FUNCTION catasto.update_modified_column();

-- =====================================================================
-- TABELLA SESSIONI ACCESSO
-- (era 19_creazione_tabella_sessioni.sql, integrata qui dalla v1.0.0)
-- Deve stare nello stesso file di catasto.utente perché è referenziata
-- dalle procedure registra_evento_sessione e logout_utente_sessione qui sopra.
-- =====================================================================
CREATE TABLE IF NOT EXISTS catasto.sessioni_accesso (
    id SERIAL PRIMARY KEY,
    utente_id INTEGER NOT NULL REFERENCES catasto.utente(id) ON DELETE CASCADE,
    id_sessione VARCHAR(100) NOT NULL UNIQUE,
    data_login  TIMESTAMP(0) WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    data_logout TIMESTAMP(0) WITHOUT TIME ZONE,
    indirizzo_ip VARCHAR(45),
    applicazione VARCHAR(100),
    azione VARCHAR(50) NOT NULL DEFAULT 'login',
    esito  BOOLEAN NOT NULL DEFAULT FALSE,
    dettagli TEXT,
    attiva   BOOLEAN DEFAULT TRUE
);

CREATE INDEX IF NOT EXISTS idx_sessioni_accesso_utente_id   ON catasto.sessioni_accesso(utente_id);
CREATE INDEX IF NOT EXISTS idx_sessioni_accesso_id_sessione ON catasto.sessioni_accesso(id_sessione);
CREATE INDEX IF NOT EXISTS idx_sessioni_accesso_data_login  ON catasto.sessioni_accesso(data_login);

COMMENT ON TABLE catasto.sessioni_accesso IS 'Registra le sessioni di accesso degli utenti alle applicazioni.';
COMMENT ON COLUMN catasto.sessioni_accesso.attiva IS 'True se la sessione è considerata attiva, False se è stato effettuato il logout o è scaduta.';