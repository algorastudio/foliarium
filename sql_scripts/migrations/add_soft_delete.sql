-- =============================================================================
-- 07_soft_delete_archiviazione.sql
-- Migrazione: aggiunge supporto soft delete (archiviazione) alle tabelle
-- catasto.comune, catasto.localita, catasto.partita, catasto.possessore
-- =============================================================================

BEGIN;

-- ─────────────────────────────────────────────────────────────
-- COMUNE
-- ─────────────────────────────────────────────────────────────
ALTER TABLE catasto.comune
    ADD COLUMN IF NOT EXISTS archiviato   BOOLEAN   NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS archiviato_il TIMESTAMP WITHOUT TIME ZONE DEFAULT NULL;

CREATE INDEX IF NOT EXISTS idx_comune_archiviato ON catasto.comune (archiviato);

-- ─────────────────────────────────────────────────────────────
-- LOCALITA
-- ─────────────────────────────────────────────────────────────
ALTER TABLE catasto.localita
    ADD COLUMN IF NOT EXISTS archiviato   BOOLEAN   NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS archiviato_il TIMESTAMP WITHOUT TIME ZONE DEFAULT NULL;

CREATE INDEX IF NOT EXISTS idx_localita_archiviato ON catasto.localita (archiviato);

-- ─────────────────────────────────────────────────────────────
-- PARTITA
-- ─────────────────────────────────────────────────────────────
ALTER TABLE catasto.partita
    ADD COLUMN IF NOT EXISTS archiviato   BOOLEAN   NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS archiviato_il TIMESTAMP WITHOUT TIME ZONE DEFAULT NULL;

CREATE INDEX IF NOT EXISTS idx_partita_archiviato ON catasto.partita (archiviato);

-- ─────────────────────────────────────────────────────────────
-- POSSESSORE
-- La colonna 'attivo' esiste già e svolge la funzione di soft delete.
-- Aggiungiamo solo la data di archiviazione per uniformità.
-- ─────────────────────────────────────────────────────────────
ALTER TABLE catasto.possessore
    ADD COLUMN IF NOT EXISTS archiviato_il TIMESTAMP WITHOUT TIME ZONE DEFAULT NULL;

-- Indice su attivo (già usato nelle query)
CREATE INDEX IF NOT EXISTS idx_possessore_attivo ON catasto.possessore (attivo);

COMMIT;
