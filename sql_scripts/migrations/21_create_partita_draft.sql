-- sql_scripts/migrations/21_create_partita_draft.sql
--
-- Migrazione idempotente: crea la tabella catasto.partita_draft per il
-- salvataggio in bozza dei wizard "Nuova Partita" e "Registrazione
-- Proprietà".
--
-- La tabella conserva uno snapshot serializzato dello stato del wizard
-- in JSONB, legato all'utente che ha creato la bozza. La colonna
-- wizard_kind discrimina il wizard d'origine per evitare di mescolare
-- bozze incompatibili tra i due flussi.
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
    wizard_kind VARCHAR(64) NOT NULL DEFAULT 'nuova_partita_wizard',
    titolo      VARCHAR(255) NOT NULL,
    payload     JSONB NOT NULL,
    app_version VARCHAR(32),
    created_at  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Per DB con la tabella già esistente prima dell'introduzione di
-- wizard_kind: aggiunge la colonna con default.
ALTER TABLE catasto.partita_draft
    ADD COLUMN IF NOT EXISTS wizard_kind VARCHAR(64) NOT NULL DEFAULT 'nuova_partita_wizard';

CREATE INDEX IF NOT EXISTS idx_partita_draft_utente_kind
    ON catasto.partita_draft(utente_id, wizard_kind, updated_at DESC);

COMMENT ON TABLE catasto.partita_draft IS
    'Bozze dei wizard partita (Nuova Partita / Registrazione Proprietà): '
    'snapshot JSONB dello stato wizard per ripresa successiva. '
    'wizard_kind discrimina il flusso di origine.';

SELECT 'Tabella catasto.partita_draft creata o gia presente.' AS stato;
