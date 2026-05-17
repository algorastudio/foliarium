-- sql_scripts/migrations/00_schema_version_table.sql
--
-- Tabella di tracciamento delle migrazioni applicate al DB.
-- Idempotente: CREATE TABLE IF NOT EXISTS + INSERT ... ON CONFLICT DO NOTHING.
--
-- Usata da bin/migrate.py per:
--   1. registrare ogni script migrations/NN_*.sql applicato
--   2. evitare la riapplicazione (idempotenza forte vs idempotenza
--      "best-effort" attuale di db/base.py::_apply_pending_schema_migrations)
--   3. mostrare lo stato dello schema da CLI (bin/migrate.py status)
--
-- Schema deliberatamente minimo: id, filename, applied_at, optional checksum.
-- Espanderlo solo se diventa critico (es. dirty migrations, rollback ID, ecc.).

SET search_path TO catasto, public;

CREATE TABLE IF NOT EXISTS catasto.schema_version (
    id            SERIAL PRIMARY KEY,
    filename      TEXT NOT NULL UNIQUE,
    applied_at    TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    checksum      TEXT,
    note          TEXT
);

CREATE INDEX IF NOT EXISTS idx_schema_version_filename
    ON catasto.schema_version (filename);

COMMENT ON TABLE  catasto.schema_version IS
    'Tracciamento delle migrazioni SQL applicate. Gestita da bin/migrate.py.';

-- Backfill: marca come "applicate" le migrazioni gia' presenti nello
-- schema corrente (rilevate da indicatori specifici). Idempotente.

-- migration 19 (vista v_audit_dettagliato) — gia' applicata se la vista esiste
INSERT INTO catasto.schema_version (filename, note)
SELECT '19_create_v_audit_dettagliato.sql',
       'backfill: vista gia presente'
WHERE EXISTS (
    SELECT 1 FROM information_schema.views
    WHERE table_schema = 'catasto' AND table_name = 'v_audit_dettagliato'
)
ON CONFLICT (filename) DO NOTHING;

-- soft_delete migration — applicata se la colonna 'archiviato' esiste su comune
INSERT INTO catasto.schema_version (filename, note)
SELECT 'add_soft_delete.sql', 'backfill: colonne archiviato gia presenti'
WHERE EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'catasto'
      AND table_name = 'comune'
      AND column_name = 'archiviato'
)
ON CONFLICT (filename) DO NOTHING;

-- tipo_possesso migration — applicata se la tabella esiste
INSERT INTO catasto.schema_version (filename, note)
SELECT 'add_tipo_possesso.sql', 'backfill: tabella tipo_possesso gia presente'
WHERE EXISTS (
    SELECT 1 FROM information_schema.tables
    WHERE table_schema = 'catasto' AND table_name = 'tipo_possesso'
)
ON CONFLICT (filename) DO NOTHING;

SELECT 'schema_version table pronta. ' ||
       (SELECT COUNT(*)::TEXT FROM catasto.schema_version) ||
       ' migrazioni registrate.' AS stato;
