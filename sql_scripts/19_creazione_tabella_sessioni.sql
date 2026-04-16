-- In un nuovo file SQL, es. 19_creazione_tabella_sessioni.sql
SET search_path TO catasto, public;

CREATE TABLE IF NOT EXISTS catasto.sessioni_accesso (
    id SERIAL PRIMARY KEY,
    utente_id INTEGER NOT NULL REFERENCES catasto.utente(id) ON DELETE CASCADE, -- Chi si è loggato
    id_sessione VARCHAR(100) NOT NULL UNIQUE, -- UUID della sessione
    data_login TIMESTAMP(0) WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    data_logout TIMESTAMP(0) WITHOUT TIME ZONE,
    indirizzo_ip VARCHAR(45),
    applicazione VARCHAR(100), -- Nome dell'applicazione client
    azione VARCHAR(50) NOT NULL DEFAULT 'login', -- login, logout, timeout, fail_login
    esito BOOLEAN NOT NULL DEFAULT FALSE,
    dettagli TEXT, -- Eventuali dettagli aggiuntivi (es. user agent, motivo fallimento)
    attiva BOOLEAN DEFAULT TRUE -- Indica se la sessione è considerata ancora attiva
);

CREATE INDEX IF NOT EXISTS idx_sessioni_accesso_utente_id ON catasto.sessioni_accesso(utente_id);
CREATE INDEX IF NOT EXISTS idx_sessioni_accesso_id_sessione ON catasto.sessioni_accesso(id_sessione);
CREATE INDEX IF NOT EXISTS idx_sessioni_accesso_data_login ON catasto.sessioni_accesso(data_login);

COMMENT ON TABLE catasto.sessioni_accesso IS 'Registra le sessioni di accesso degli utenti alle applicazioni.';
COMMENT ON COLUMN catasto.sessioni_accesso.attiva IS 'True se la sessione è considerata attiva, False se è stato effettuato il logout o è scaduta.';