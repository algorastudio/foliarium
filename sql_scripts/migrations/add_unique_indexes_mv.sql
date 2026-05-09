-- =============================================================================
-- add_unique_indexes_mv.sql
-- Aggiunge indici UNIQUE alle viste materializzate che ne sono prive.
--
-- Prerequisito per REFRESH MATERIALIZED VIEW CONCURRENTLY (PostgreSQL richiede
-- almeno un indice UNIQUE senza clausola WHERE sulla vista).
--
-- Idempotente: usa IF NOT EXISTS e DROP IF EXISTS per essere rieseguibile.
--
-- Uso:
--   psql -d catasto_storico -f add_unique_indexes_mv.sql
-- =============================================================================

\set ON_ERROR_STOP on

SET search_path TO catasto, public;

-- -----------------------------------------------------------------------------
-- mv_immobili_per_tipologia
-- Univocità garantita da (comune_nome, classificazione) — GROUP BY della vista.
-- -----------------------------------------------------------------------------
DROP INDEX IF EXISTS catasto.idx_mv_immobili_tipologia_unique;
CREATE UNIQUE INDEX idx_mv_immobili_tipologia_unique
    ON catasto.mv_immobili_per_tipologia(comune_nome, classificazione);

-- -----------------------------------------------------------------------------
-- mv_partite_complete
-- Univocità garantita da partita_id (PK di catasto.partita).
-- -----------------------------------------------------------------------------
DROP INDEX IF EXISTS catasto.idx_mv_partite_complete_partita_id;
CREATE UNIQUE INDEX idx_mv_partite_complete_partita_id
    ON catasto.mv_partite_complete(partita_id);

-- -----------------------------------------------------------------------------
-- mv_cronologia_variazioni
-- Univocità garantita da variazione_id (PK di catasto.variazione).
-- La LEFT JOIN su contratto è 0..1 per variazione, quindi variazione_id
-- identifica univocamente ogni riga della vista.
-- -----------------------------------------------------------------------------
DROP INDEX IF EXISTS catasto.idx_mv_variazioni_var_id;
CREATE UNIQUE INDEX idx_mv_variazioni_var_id
    ON catasto.mv_cronologia_variazioni(variazione_id);

-- Verifica
DO $$
DECLARE
    v_missing TEXT := '';
    r RECORD;
BEGIN
    FOR r IN
        SELECT matviewname
        FROM pg_matviews
        WHERE schemaname = 'catasto'
          AND matviewname IN (
              'mv_immobili_per_tipologia',
              'mv_partite_complete',
              'mv_cronologia_variazioni'
          )
          AND NOT EXISTS (
              SELECT 1
              FROM pg_indexes
              WHERE schemaname = 'catasto'
                AND tablename = matviewname
                AND indexdef ILIKE '%unique%'
          )
    LOOP
        v_missing := v_missing || r.matviewname || ' ';
    END LOOP;

    IF v_missing <> '' THEN
        RAISE EXCEPTION 'Viste senza indice UNIQUE: %', v_missing;
    END IF;

    RAISE NOTICE 'OK — tutti gli indici UNIQUE creati correttamente.';
END $$;
