
-- ========================================================================
-- SCRIPT DI ESECUZIONE COMPLETA PER RICERCA FUZZY AMPLIATA
-- Da eseguire in pgAdmin o psql
-- ========================================================================

-- Connessione al database catasto_storico
\c catasto_storico;

-- Imposta lo schema
SET search_path TO catasto, public;

-- Verifica estensioni necessarie
SELECT 'Verificando estensioni...' as status;
CREATE EXTENSION IF NOT EXISTS "pg_trgm" WITH SCHEMA public;

-- Mostra estensioni installate
SELECT extname, extversion FROM pg_extension WHERE extname IN ('pg_trgm');

-- Esegui lo script di ampliamento (deve essere già stato salvato)
-- \i expand_fuzzy_search.sql

-- Verifica risultato
SELECT 'Verifica indici GIN...' as status;
SELECT * FROM verify_gin_indices();

-- Test delle nuove funzioni
SELECT 'Test ricerca immobili:' as test;
SELECT COUNT(*) as risultati FROM search_immobili_fuzzy('terra', 0.3, 5);

SELECT 'Test ricerca variazioni:' as test;
SELECT COUNT(*) as risultati FROM search_variazioni_fuzzy('vend', 0.3, 5);

SELECT 'Test ricerca unificata:' as test;
SELECT COUNT(*) as risultati FROM search_all_entities_fuzzy('test', 0.3, true, true, true, true, true, true, 5);

SELECT 'Implementazione database completata!' as status;
