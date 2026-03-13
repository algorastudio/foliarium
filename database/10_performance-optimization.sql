-- Script per l'ottimizzazione delle performance del database Catasto Storico
-- Versione: 1.1 (Corretto per compatibilità con PostgreSQL > 9.x)
-- Data: 2025-06-09

-- Aumenta la memoria di lavoro per le sessioni correnti per velocizzare le query complesse
SET work_mem = '256MB';

-- Procedura per eseguire VACUUM e ANALYZE su tutte le tabelle dello schema 'catasto'
-- Questo aggiorna le statistiche usate dal query planner e recupera spazio.
CREATE OR REPLACE PROCEDURE vacuum_analyze_catasto_schema()
LANGUAGE plpgsql
AS $$
DECLARE
    tbl_name text;
BEGIN
    FOR tbl_name IN
        SELECT tablename FROM pg_tables WHERE schemaname = 'catasto'
    LOOP
        RAISE NOTICE 'Eseguendo VACUUM ANALYZE su %.%', 'catasto', tbl_name;
        EXECUTE format('VACUUM (VERBOSE, ANALYZE) catasto.%I', tbl_name);
    END LOOP;
END;
$$;


-- Procedura per ricostruire tutti gli indici dello schema 'catasto'
-- Utile per ottimizzare indici frammentati. L'operazione può richiedere tempo e bloccare le tabelle.
-- Eseguire durante periodi di bassa attività.
CREATE OR REPLACE PROCEDURE reindex_catasto_schema()
LANGUAGE plpgsql
AS $$
DECLARE
    tbl_name text;
BEGIN
    FOR tbl_name IN
        SELECT tablename FROM pg_tables WHERE schemaname = 'catasto'
    LOOP
        RAISE NOTICE 'Re-indicizzando la tabella %.%', 'catasto', tbl_name;
        EXECUTE format('REINDEX TABLE catasto.%I', tbl_name);
    END LOOP;
END;
$$;

-- Funzione per identificare indici inutilizzati o raramente utilizzati
-- Un indice inutilizzato occupa spazio e rallenta le operazioni di scrittura (INSERT, UPDATE, DELETE)
-- senza portare benefici in lettura.
-- Restituisce una tabella con gli indici, la loro dimensione e il numero di volte che sono stati usati.
CREATE OR REPLACE FUNCTION get_unused_indexes(
    min_size_mb integer DEFAULT 1,
    min_scans integer DEFAULT 10
)
RETURNS TABLE(
    table_name text,
    index_name text,
    index_size text,
    index_scans bigint,
    suggestion text
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        i.tablename::text,
        i.indexname::text,
        pg_size_pretty(pg_relation_size(i.indexname::regclass))::text AS index_size,
        COALESCE(s.idx_scan, 0) AS index_scans,
        CASE
            WHEN COALESCE(s.idx_scan, 0) = 0 THEN 'Indice mai utilizzato. Considerare la rimozione.'
            WHEN COALESCE(s.idx_scan, 0) < min_scans THEN 'Indice raramente utilizzato. Valutare l''utilità.'
            ELSE 'Utilizzo normale.'
        END::text AS suggestion
    FROM
        pg_indexes i
    LEFT JOIN
        -- CORREZIONE: 's.indexname' è stato sostituito con 's.indexrelname' per compatibilità
        pg_stat_user_indexes s ON i.indexname = s.indexrelname AND i.schemaname = s.schemaname
    WHERE
        i.schemaname = 'catasto'
        AND pg_relation_size(i.indexname::regclass) > (min_size_mb * 1024 * 1024)
    ORDER BY
        COALESCE(s.idx_scan, 0),
        pg_relation_size(i.indexname::regclass) DESC;
END;
$$ LANGUAGE plpgsql;

-- Esempio di chiamata della funzione per trovare indici più grandi di 5MB usati meno di 50 volte
-- SELECT * FROM get_unused_indexes(min_size_mb => 5, min_scans => 50);
