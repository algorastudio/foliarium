-- sql_scripts/migrations/22_create_api_keys.sql
--
-- Migrazione idempotente: crea la tabella catasto.api_keys per gestire le
-- chiavi di autenticazione delle integrazioni esterne (MCP server, Zapier,
-- script di automazione, ecc.).
--
-- La chiave in chiaro NON è mai memorizzata: si conserva solo lo SHA-256
-- (`key_hash`) per la verifica e un prefisso identificativo (`prefix`,
-- es. `flr_a3b9c1d2`) per riconoscere la chiave nella UI di amministrazione
-- senza esporre il segreto. Il valore in chiaro viene mostrato all'utente
-- una sola volta al momento della creazione.
--
-- Scopes: lista di permessi granulari (es. `read:partite`, `write:partite`,
-- `read:*`). Le sessioni utente standard hanno tutti gli scope impliciti;
-- gli scope sono usati solo dalle chiavi API.
--
-- Esecuzione manuale (DB già inizializzati):
--   psql -U postgres -d catasto_storico -f 22_create_api_keys.sql
--
-- Auto-applicazione: db/base.py::_ensure_api_keys_table() applica
-- equivalentemente questa migrazione all'avvio del pool (best-effort,
-- idempotente).

SET search_path TO catasto, public;

CREATE TABLE IF NOT EXISTS catasto.api_keys (
    id                  SERIAL PRIMARY KEY,
    name                VARCHAR(100) NOT NULL,
    key_hash            VARCHAR(64)  NOT NULL UNIQUE,
    prefix              VARCHAR(12)  NOT NULL,
    scopes              TEXT[]       NOT NULL DEFAULT ARRAY[]::TEXT[],
    created_by          INTEGER      NULL REFERENCES catasto.utente(id) ON DELETE SET NULL,
    created_at          TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    expires_at          TIMESTAMPTZ  NULL,
    revoked_at          TIMESTAMPTZ  NULL,
    last_used_at        TIMESTAMPTZ  NULL,
    rate_limit_per_min  INTEGER      NOT NULL DEFAULT 60
);

CREATE INDEX IF NOT EXISTS idx_api_keys_prefix
    ON catasto.api_keys(prefix);

CREATE INDEX IF NOT EXISTS idx_api_keys_active
    ON catasto.api_keys(revoked_at, expires_at)
    WHERE revoked_at IS NULL;

COMMENT ON TABLE  catasto.api_keys IS 'Chiavi API per integrazioni esterne (MCP, script). Solo hash, mai plaintext.';
COMMENT ON COLUMN catasto.api_keys.key_hash IS 'SHA-256 della chiave in chiaro (formato flr_<32 hex>).';
COMMENT ON COLUMN catasto.api_keys.prefix   IS 'Primi 12 caratteri della chiave in chiaro (es. flr_a3b9c1d2), per identificazione UI.';
COMMENT ON COLUMN catasto.api_keys.scopes   IS 'Lista permessi granulari, es. ARRAY[''read:partite'',''write:partite''].';
