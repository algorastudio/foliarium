-- sql_scripts/migrations/21_create_partita_draft.sql
--
-- Migrazione idempotente: crea la tabella catasto.partita_draft per il
-- salvataggio in bozza del wizard "Nuova Partita".
--
-- La tabella conserva uno snapshot serializzato dello stato del wizard
-- in JSONB, legato all'utente che ha creato la bozza. Permette di
-- sospendere un inserimento complesso e riprenderlo successivamente,
-- anche da una postazione diversa (la persistenza è centralizzata su DB).
--
-- Esecuzione manuale (DB già inizializzati):
--   psql -U postgres -d catasto_storico -f 21_create_partita_draft.sql
--
-- Auto-applicazione: db/base.py::_ensure_partita_draft_table() applica
-- equivalentemente questa migrazione all'avvio del pool (best-effort,
-- idempotente).

SET search_path TO catasto, public;

CREATE TABLE IF NOT EXISTS catasto.partita_draft (
    id          SERIAL PRIMARY KEY,
    utente_id   INTEGER NULL REFERENCES catasto.utente(id) ON DELETE SET NULL,
    titolo      VARCHAR(255) NOT NULL,
    payload     JSONB NOT NULL,
    app_version VARCHAR(32),
    created_at  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_partita_draft_utente
    ON catasto.partita_draft(utente_id, updated_at DESC);

COMMENT ON TABLE catasto.partita_draft IS
    'Bozze del wizard Nuova Partita: snapshot JSONB dello stato wizard '
    'per ripresa successiva. Legate a utente.id (SET NULL on delete).';

SELECT 'Tabella catasto.partita_draft creata o gia presente.' AS stato;
