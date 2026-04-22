-- TIER 2 Phase 4: Create GIN Trigram Indexes for full-text search optimization
-- Purpose: Enable fast ILIKE searches on frequently-searched text columns
-- Expected speedup: 5-50x on possessore/comune searches

-- Enable pg_trgm extension (required for trigram GIN indexes)
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Index on possessore.nome_completo (used in search_possessori_by_term_globally)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_possessore_nome_completo_trgm
  ON public.possessore USING gin (nome_completo gin_trgm_ops);

-- Index on possessore.cognome_nome (used in ILIKE filters in get_possessori_by_comune)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_possessore_cognome_nome_trgm
  ON public.possessore USING gin (cognome_nome gin_trgm_ops);

-- Index on comune.nome (used in get_comuni search)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_comune_nome_trgm
  ON public.comune USING gin (nome gin_trgm_ops);

-- Index on documento_storico.titolo (used in search_historical_documents)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_documento_titolo_trgm
  ON public.documento_storico USING gin (titolo gin_trgm_ops);

-- Verify indexes were created
SELECT
  schemaname,
  tablename,
  indexname,
  indexdef
FROM pg_indexes
WHERE indexname LIKE '%trgm%'
ORDER BY tablename, indexname;
