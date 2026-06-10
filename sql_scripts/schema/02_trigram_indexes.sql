-- schema/02_trigram_indexes.sql
-- Indici GIN trigram per ricerca fuzzy.
-- IMPORTANTE: deve essere eseguito FUORI da una transazione (CONCURRENTLY).
-- Versione: Foliarium v1.7.0+

-- Enable pg_trgm extension (required for trigram GIN indexes)
CREATE EXTENSION IF NOT EXISTS pg_trgm;

SET search_path TO catasto, public;

-- ========================================================================
-- INDICI GIN TRIGRAM (gin_trgm_ops) — per ricerca fuzzy con similarity()
-- Da: 07_create_trigram_indexes.sql
-- ========================================================================

-- Index on possessore.nome_completo (used in search_possessori_by_term_globally)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_possessore_nome_completo_trgm
  ON possessore USING gin (nome_completo gin_trgm_ops);

-- Index on possessore.cognome_nome (used in ILIKE filters in get_possessori_by_comune)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_possessore_cognome_nome_trgm
  ON possessore USING gin (cognome_nome gin_trgm_ops);

-- Index on comune.nome (used in get_comuni search)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_comune_nome_trgm
  ON comune USING gin (nome gin_trgm_ops);

-- Index on documento_storico.titolo (used in search_historical_documents)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_documento_titolo_trgm
  ON documento_storico USING gin (titolo gin_trgm_ops);

-- ========================================================================
-- INDICI GIN TRIGRAM AGGIUNTIVI — da 16_advanced_search.sql
-- ========================================================================

-- Indice opzionale su paternita (solo per valori non NULL)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_gin_possessore_paternita_trgm
  ON possessore USING gin (paternita gin_trgm_ops)
  WHERE paternita IS NOT NULL;

-- ========================================================================
-- INDICI GIN TSVECTOR per ricerca full-text — da 03b_expand_fuzzy_search.sql
-- ========================================================================

-- Indice per natura degli immobili
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_gin_immobili_natura
  ON immobile USING gin(to_tsvector('italian', natura));

-- Indice per classificazione immobili
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_gin_immobili_classificazione
  ON immobile USING gin(to_tsvector('italian', COALESCE(classificazione, '')));

-- Indice per consistenza immobili
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_gin_immobili_consistenza
  ON immobile USING gin(to_tsvector('italian', COALESCE(consistenza, '')));

-- Indice per tipo variazioni
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_gin_variazioni_tipo
  ON variazione USING gin(to_tsvector('italian', tipo));

-- Indice per nominativo di riferimento nelle variazioni
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_gin_variazioni_nominativo
  ON variazione USING gin(to_tsvector('italian', COALESCE(nominativo_riferimento, '')));

-- Indice per numero di riferimento nelle variazioni
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_gin_variazioni_numero_rif
  ON variazione USING gin(to_tsvector('italian', COALESCE(numero_riferimento, '')));

-- Indice per tipo contratti
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_gin_contratti_tipo
  ON contratto USING gin(to_tsvector('italian', tipo));

-- Indice per notaio nei contratti
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_gin_contratti_notaio
  ON contratto USING gin(to_tsvector('italian', COALESCE(notaio, '')));

-- Indice per repertorio nei contratti
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_gin_contratti_repertorio
  ON contratto USING gin(to_tsvector('italian', COALESCE(repertorio, '')));

-- Indice per note nei contratti
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_gin_contratti_note
  ON contratto USING gin(to_tsvector('italian', COALESCE(note, '')));

-- Indice per numero partita (per ricerca fuzzy numerica)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_gin_partite_numero
  ON partita USING gin(to_tsvector('simple', numero_partita::text));

-- Indice per suffisso partita
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_gin_partite_suffisso
  ON partita USING gin(to_tsvector('italian', COALESCE(suffisso_partita, '')));

-- ========================================================================
-- INDICI GIN TRIGRAM (gin_trgm_ops) su variazione, contratto, partita
-- Da: 03b_expand_fuzzy_search.sql
-- ========================================================================

-- Per la tabella 'variazione'
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_gin_variazione_tipo
  ON catasto.variazione USING gin (tipo gin_trgm_ops);

-- Per la tabella 'contratto'
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_gin_contratto_tipo
  ON catasto.contratto USING gin (tipo gin_trgm_ops);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_gin_contratto_notaio
  ON catasto.contratto USING gin (notaio gin_trgm_ops);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_gin_contratto_note
  ON catasto.contratto USING gin (note gin_trgm_ops);

-- Per la tabella 'partita'
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_gin_partita_tipo
  ON catasto.partita USING gin (tipo gin_trgm_ops);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_gin_partita_suffisso
  ON catasto.partita USING gin (suffisso_partita gin_trgm_ops);
