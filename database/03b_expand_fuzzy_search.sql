-- ========================================================================
-- AMPLIAMENTO RICERCA FUZZY - NUOVI CAMPI E INDICI
-- File: expand_fuzzy_search.sql
-- ========================================================================

-- Imposta lo schema
SET search_path TO catasto, public;

-- ========================================================================
-- 1. CREAZIONE NUOVI INDICI GIN PER RICERCA FUZZY
-- ========================================================================

-- Indice per natura degli immobili
CREATE INDEX IF NOT EXISTS idx_gin_immobili_natura 
ON immobile USING gin(to_tsvector('italian', natura));

-- Indice per classificazione immobili
CREATE INDEX IF NOT EXISTS idx_gin_immobili_classificazione 
ON immobile USING gin(to_tsvector('italian', COALESCE(classificazione, '')));

-- Indice per consistenza immobili
CREATE INDEX IF NOT EXISTS idx_gin_immobili_consistenza 
ON immobile USING gin(to_tsvector('italian', COALESCE(consistenza, '')));

-- Indice per tipo variazioni
CREATE INDEX IF NOT EXISTS idx_gin_variazioni_tipo 
ON variazione USING gin(to_tsvector('italian', tipo));

-- Indice per nominativo di riferimento nelle variazioni
CREATE INDEX IF NOT EXISTS idx_gin_variazioni_nominativo 
ON variazione USING gin(to_tsvector('italian', COALESCE(nominativo_riferimento, '')));

-- Indice per numero di riferimento nelle variazioni
CREATE INDEX IF NOT EXISTS idx_gin_variazioni_numero_rif 
ON variazione USING gin(to_tsvector('italian', COALESCE(numero_riferimento, '')));

-- Indice per tipo contratti
CREATE INDEX IF NOT EXISTS idx_gin_contratti_tipo 
ON contratto USING gin(to_tsvector('italian', tipo));

-- Indice per notaio nei contratti
CREATE INDEX IF NOT EXISTS idx_gin_contratti_notaio 
ON contratto USING gin(to_tsvector('italian', COALESCE(notaio, '')));

-- Indice per repertorio nei contratti
CREATE INDEX IF NOT EXISTS idx_gin_contratti_repertorio 
ON contratto USING gin(to_tsvector('italian', COALESCE(repertorio, '')));

-- Indice per note nei contratti
CREATE INDEX IF NOT EXISTS idx_gin_contratti_note 
ON contratto USING gin(to_tsvector('italian', COALESCE(note, '')));

-- Indice per numero partita (per ricerca fuzzy numerica)
CREATE INDEX IF NOT EXISTS idx_gin_partite_numero 
ON partita USING gin(to_tsvector('simple', numero_partita::text));

-- Indice per suffisso partita
CREATE INDEX IF NOT EXISTS idx_gin_partite_suffisso 
ON partita USING gin(to_tsvector('italian', COALESCE(suffisso_partita, '')));

-- Eseguire questi comandi sul database PostgreSQL per migliorare le performance

-- Per la tabella 'variazione'
CREATE INDEX idx_gin_variazione_tipo ON catasto.variazione USING gin (tipo gin_trgm_ops);
--CREATE INDEX idx_gin_variazione_note ON catasto.variazione USING gin (note gin_trgm_ops);

-- Per la tabella 'contratto'
CREATE INDEX idx_gin_contratto_tipo ON catasto.contratto USING gin (tipo gin_trgm_ops);
CREATE INDEX idx_gin_contratto_notaio ON catasto.contratto USING gin (notaio gin_trgm_ops);
CREATE INDEX idx_gin_contratto_note ON catasto.contratto USING gin (note gin_trgm_ops);

-- Per la tabella 'partita'
CREATE INDEX idx_gin_partita_tipo ON catasto.partita USING gin (tipo gin_trgm_ops);
CREATE INDEX idx_gin_partita_suffisso ON catasto.partita USING gin (suffisso_partita gin_trgm_ops);


-- ========================================================================
-- 2. FUNZIONI DI RICERCA FUZZY AMPLIATE
-- ========================================================================

-- Funzione per ricerca fuzzy in immobili
CREATE OR REPLACE FUNCTION search_immobili_fuzzy(
    query_text TEXT,
    similarity_threshold REAL DEFAULT 0.3,
    max_results INTEGER DEFAULT 50
)
RETURNS TABLE (
    id INTEGER,
    partita_id INTEGER,
    numero_partita INTEGER,
    suffisso_partita VARCHAR(20),
    comune_nome VARCHAR(100),
    localita_nome VARCHAR(255),
    natura VARCHAR(100),
    classificazione VARCHAR(100),
    consistenza VARCHAR(255),
    similarity_score REAL,
    search_field TEXT
) 
LANGUAGE plpgsql
AS $$
BEGIN
    -- Imposta la soglia di similarità
    PERFORM set_limit(similarity_threshold);
    
    RETURN QUERY
    WITH immobili_search AS (
        -- Ricerca per natura
        SELECT 
            i.id,
            i.partita_id,
            p.numero_partita,
            p.suffisso_partita,
            c.nome as comune_nome,
            l.nome as localita_nome,
            i.natura,
            i.classificazione,
            i.consistenza,
            similarity(i.natura, query_text) as sim_score,
            'natura' as search_field
        FROM immobile i
        JOIN partita p ON i.partita_id = p.id
        JOIN comune c ON p.comune_id = c.id
        JOIN localita l ON i.localita_id = l.id
        WHERE i.natura % query_text
        
        UNION ALL
        
        -- Ricerca per classificazione
        SELECT 
            i.id,
            i.partita_id,
            p.numero_partita,
            p.suffisso_partita,
            c.nome as comune_nome,
            l.nome as localita_nome,
            i.natura,
            i.classificazione,
            i.consistenza,
            similarity(COALESCE(i.classificazione, ''), query_text) as sim_score,
            'classificazione' as search_field
        FROM immobile i
        JOIN partita p ON i.partita_id = p.id
        JOIN comune c ON p.comune_id = c.id
        JOIN localita l ON i.localita_id = l.id
        WHERE COALESCE(i.classificazione, '') % query_text
        
        UNION ALL
        
        -- Ricerca per consistenza
        SELECT 
            i.id,
            i.partita_id,
            p.numero_partita,
            p.suffisso_partita,
            c.nome as comune_nome,
            l.nome as localita_nome,
            i.natura,
            i.classificazione,
            i.consistenza,
            similarity(COALESCE(i.consistenza, ''), query_text) as sim_score,
            'consistenza' as search_field
        FROM immobile i
        JOIN partita p ON i.partita_id = p.id
        JOIN comune c ON p.comune_id = c.id
        JOIN localita l ON i.localita_id = l.id
        WHERE COALESCE(i.consistenza, '') % query_text
		UNION ALL
        -- Ricerca per numero partita associato
        SELECT 
            i.id, i.partita_id, p.numero_partita, p.suffisso_partita, c.nome, l.nome, 
            i.natura, i.classificazione, i.consistenza,
            similarity(p.numero_partita::text, query_text) as sim_score,
            'numero_partita' as search_field
        FROM immobile i
        JOIN partita p ON i.partita_id = p.id
        JOIN comune c ON p.comune_id = c.id
        JOIN localita l ON i.localita_id = l.id
        WHERE p.numero_partita::text % query_text
        -- --- FINE NUOVA SEZIONE ---
    )
    SELECT DISTINCT ON (ims.id) 
        ims.id,
        ims.partita_id,
        ims.numero_partita,
        ims.suffisso_partita,
        ims.comune_nome,
        ims.localita_nome,
        ims.natura,
        ims.classificazione,
        ims.consistenza,
        ims.sim_score,
        ims.search_field
    FROM immobili_search ims
    WHERE ims.sim_score >= similarity_threshold
    ORDER BY ims.id, ims.sim_score DESC
    LIMIT max_results;
END;
$$;

-- Funzione per ricerca fuzzy in variazioni
CREATE OR REPLACE FUNCTION search_variazioni_fuzzy(
    query_text TEXT,
    similarity_threshold REAL DEFAULT 0.3,
    max_results INTEGER DEFAULT 50
)
RETURNS TABLE (
    id INTEGER,
    partita_origine_id INTEGER,
    numero_partita_origine INTEGER,
    partita_destinazione_id INTEGER,
    numero_partita_destinazione INTEGER,
    tipo VARCHAR(50),
    data_variazione DATE,
    numero_riferimento VARCHAR(50),
    nominativo_riferimento VARCHAR(255),
    comune_nome VARCHAR(100),
    similarity_score REAL,
    search_field TEXT
) 
LANGUAGE plpgsql
AS $$
BEGIN
    -- Imposta la soglia di similarità
    PERFORM set_limit(similarity_threshold);
    
    RETURN QUERY
    WITH variazioni_search AS (
        -- Ricerca per tipo variazione
        SELECT 
            v.id,
            v.partita_origine_id,
            po.numero_partita as numero_partita_origine,
            v.partita_destinazione_id,
            pd.numero_partita as numero_partita_destinazione,
            v.tipo,
            v.data_variazione,
            v.numero_riferimento,
            v.nominativo_riferimento,
            co.nome as comune_nome,
            similarity(v.tipo, query_text) as sim_score,
            'tipo' as search_field
        FROM variazione v
        JOIN partita po ON v.partita_origine_id = po.id
        LEFT JOIN partita pd ON v.partita_destinazione_id = pd.id
        JOIN comune co ON po.comune_id = co.id
        WHERE v.tipo % query_text
        
        UNION ALL
        
        -- Ricerca per nominativo riferimento
        SELECT 
            v.id,
            v.partita_origine_id,
            po.numero_partita as numero_partita_origine,
            v.partita_destinazione_id,
            pd.numero_partita as numero_partita_destinazione,
            v.tipo,
            v.data_variazione,
            v.numero_riferimento,
            v.nominativo_riferimento,
            co.nome as comune_nome,
            similarity(COALESCE(v.nominativo_riferimento, ''), query_text) as sim_score,
            'nominativo' as search_field
        FROM variazione v
        JOIN partita po ON v.partita_origine_id = po.id
        LEFT JOIN partita pd ON v.partita_destinazione_id = pd.id
        JOIN comune co ON po.comune_id = co.id
        WHERE COALESCE(v.nominativo_riferimento, '') % query_text
        
        UNION ALL
        
        -- Ricerca per numero riferimento
        SELECT 
            v.id,
            v.partita_origine_id,
            po.numero_partita as numero_partita_origine,
            v.partita_destinazione_id,
            pd.numero_partita as numero_partita_destinazione,
            v.tipo,
            v.data_variazione,
            v.numero_riferimento,
            v.nominativo_riferimento,
            co.nome as comune_nome,
            similarity(COALESCE(v.numero_riferimento, ''), query_text) as sim_score,
            'numero_riferimento' as search_field
        FROM variazione v
        JOIN partita po ON v.partita_origine_id = po.id
        LEFT JOIN partita pd ON v.partita_destinazione_id = pd.id
        JOIN comune co ON po.comune_id = co.id
        WHERE COALESCE(v.numero_riferimento, '') % query_text
		-- --- INIZIO NUOVA SEZIONE ---
        UNION ALL
        -- Ricerca per numero partita origine o destinazione
        SELECT
            v.id, v.partita_origine_id, po.numero_partita, v.partita_destinazione_id, pd.numero_partita,
            v.tipo, v.data_variazione, v.numero_riferimento, v.nominativo_riferimento, co.nome,
            GREATEST(similarity(po.numero_partita::text, query_text), similarity(pd.numero_partita::text, query_text)) as sim_score,
            'numero_partita' as search_field
        FROM variazione v
        JOIN partita po ON v.partita_origine_id = po.id
        LEFT JOIN partita pd ON v.partita_destinazione_id = pd.id
        JOIN comune co ON po.comune_id = co.id
        WHERE po.numero_partita::text % query_text OR pd.numero_partita::text % query_text
        -- --- FINE NUOVA SEZIONE ---
    )
    SELECT DISTINCT ON (vs.id) 
        vs.id,
        vs.partita_origine_id,
        vs.numero_partita_origine,
        vs.partita_destinazione_id,
        vs.numero_partita_destinazione,
        vs.tipo,
        vs.data_variazione,
        vs.numero_riferimento,
        vs.nominativo_riferimento,
        vs.comune_nome,
        vs.sim_score,
        vs.search_field
    FROM variazioni_search vs
    WHERE vs.sim_score >= similarity_threshold
    ORDER BY vs.id, vs.sim_score DESC
    LIMIT max_results;
END;
$$;


-- Funzione per ricerca fuzzy in contratti
CREATE OR REPLACE FUNCTION search_contratti_fuzzy(
    query_text TEXT,
    similarity_threshold REAL DEFAULT 0.3,
    max_results INTEGER DEFAULT 50
)
RETURNS TABLE (
    id INTEGER,
    variazione_id INTEGER,
    tipo VARCHAR(50),
    data_contratto DATE,
    notaio VARCHAR(255),
    repertorio VARCHAR(100),
    note TEXT,
    similarity_score REAL,
    search_field TEXT
) 
LANGUAGE plpgsql
AS $$
BEGIN
    -- Imposta la soglia di similarità
    PERFORM set_limit(similarity_threshold);
    
    RETURN QUERY
    WITH contratti_search AS (
        -- Ricerca per tipo contratto
        SELECT 
            c.id,
            c.variazione_id,
            c.tipo,
            c.data_contratto,
            c.notaio,
            c.repertorio,
            c.note,
            similarity(c.tipo, query_text) as sim_score,
            'tipo' as search_field
        FROM contratto c
        WHERE c.tipo % query_text
        
        UNION ALL
        
        -- Ricerca per notaio
        SELECT 
            c.id,
            c.variazione_id,
            c.tipo,
            c.data_contratto,
            c.notaio,
            c.repertorio,
            c.note,
            similarity(COALESCE(c.notaio, ''), query_text) as sim_score,
            'notaio' as search_field
        FROM contratto c
        WHERE COALESCE(c.notaio, '') % query_text
        
        UNION ALL
        
        -- Ricerca per repertorio
        SELECT 
            c.id,
            c.variazione_id,
            c.tipo,
            c.data_contratto,
            c.notaio,
            c.repertorio,
            c.note,
            similarity(COALESCE(c.repertorio, ''), query_text) as sim_score,
            'repertorio' as search_field
        FROM contratto c
        WHERE COALESCE(c.repertorio, '') % query_text
        
        UNION ALL
        
        -- Ricerca nelle note
        SELECT 
            c.id,
            c.variazione_id,
            c.tipo,
            c.data_contratto,
            c.notaio,
            c.repertorio,
            c.note,
            similarity(COALESCE(c.note, ''), query_text) as sim_score,
            'note' as search_field
        FROM contratto c
        WHERE COALESCE(c.note, '') % query_text
		-- --- INIZIO NUOVA SEZIONE ---
        UNION ALL
        -- Ricerca per numero partita associato tramite la variazione
        SELECT 
            c.id, c.variazione_id, c.tipo, c.data_contratto, c.notaio, c.repertorio, c.note,
            similarity(p.numero_partita::text, query_text) as sim_score,
            'numero_partita' as search_field
        FROM contratto c
        JOIN variazione v ON c.variazione_id = v.id
        JOIN partita p ON v.partita_origine_id = p.id
        WHERE p.numero_partita::text % query_text
        -- --- FINE NUOVA SEZIONE ---
    )
    SELECT DISTINCT ON (cs.id) 
        cs.id,
        cs.variazione_id,
        cs.tipo,
        cs.data_contratto,
        cs.notaio,
        cs.repertorio,
        cs.note,
        cs.sim_score,
        cs.search_field
    FROM contratti_search cs
    WHERE cs.sim_score >= similarity_threshold
    ORDER BY cs.id, cs.sim_score DESC
    LIMIT max_results;
END;
$$;

-- Funzione per ricerca fuzzy in partite (numero e suffisso)
CREATE OR REPLACE FUNCTION search_partite_fuzzy(
    query_text TEXT,
    similarity_threshold REAL DEFAULT 0.3,
    max_results INTEGER DEFAULT 50
)
RETURNS TABLE (
    id INTEGER,
    numero_partita INTEGER,
    suffisso_partita VARCHAR(20),
    comune_nome VARCHAR(100),
    data_impianto DATE,
    stato VARCHAR(20),
    tipo VARCHAR(20),
    num_possessori BIGINT,
    num_immobili BIGINT,
    similarity_score REAL,
    search_field TEXT
) 
LANGUAGE plpgsql
AS $$
BEGIN
    -- Imposta la soglia di similarità
    PERFORM set_limit(similarity_threshold);
    
    RETURN QUERY
    WITH partite_search AS (
        -- Ricerca per numero partita (convertito in testo)
        SELECT 
            p.id,
            p.numero_partita,
            p.suffisso_partita,
            c.nome as comune_nome,
            p.data_impianto,
            p.stato,
            p.tipo,
            COALESCE(pp_count.num_possessori, 0) as num_possessori,
            COALESCE(i_count.num_immobili, 0) as num_immobili,
            similarity(p.numero_partita::text, query_text) as sim_score,
            'numero' as search_field
        FROM partita p
        JOIN comune c ON p.comune_id = c.id
        LEFT JOIN (
            SELECT partita_id, COUNT(*) as num_possessori
            FROM partita_possessore
            GROUP BY partita_id
        ) pp_count ON p.id = pp_count.partita_id
        LEFT JOIN (
            SELECT partita_id, COUNT(*) as num_immobili
            FROM immobile
            GROUP BY partita_id
        ) i_count ON p.id = i_count.partita_id
        WHERE p.numero_partita::text % query_text
        
        UNION ALL
        
        -- Ricerca per suffisso partita
        SELECT 
            p.id,
            p.numero_partita,
            p.suffisso_partita,
            c.nome as comune_nome,
            p.data_impianto,
            p.stato,
            p.tipo,
            COALESCE(pp_count.num_possessori, 0) as num_possessori,
            COALESCE(i_count.num_immobili, 0) as num_immobili,
            similarity(COALESCE(p.suffisso_partita, ''), query_text) as sim_score,
            'suffisso' as search_field
        FROM partita p
        JOIN comune c ON p.comune_id = c.id
        LEFT JOIN (
            SELECT partita_id, COUNT(*) as num_possessori
            FROM partita_possessore
            GROUP BY partita_id
        ) pp_count ON p.id = pp_count.partita_id
        LEFT JOIN (
            SELECT partita_id, COUNT(*) as num_immobili
            FROM immobile
            GROUP BY partita_id
        ) i_count ON p.id = i_count.partita_id
        WHERE COALESCE(p.suffisso_partita, '') % query_text
    )
    SELECT DISTINCT ON (ps.id) 
        ps.id,
        ps.numero_partita,
        ps.suffisso_partita,
        ps.comune_nome,
        ps.data_impianto,
        ps.stato,
        ps.tipo,
        ps.num_possessori,
        ps.num_immobili,
        ps.sim_score,
        ps.search_field
    FROM partite_search ps
    WHERE ps.sim_score >= similarity_threshold
    ORDER BY ps.id, ps.sim_score DESC
    LIMIT max_results;
END;
$$;

-- ========================================================================
-- 3. FUNZIONE DI RICERCA UNIFICATA AVANZATA
-- ========================================================================

CREATE OR REPLACE FUNCTION search_all_entities_fuzzy(
    query_text TEXT,
    similarity_threshold REAL DEFAULT 0.3,
    search_possessori BOOLEAN DEFAULT TRUE,
    search_localita BOOLEAN DEFAULT TRUE,
    search_immobili BOOLEAN DEFAULT TRUE,
    search_variazioni BOOLEAN DEFAULT TRUE,
    search_contratti BOOLEAN DEFAULT TRUE,
    search_partite BOOLEAN DEFAULT TRUE,
    max_results_per_type INTEGER DEFAULT 30
)
RETURNS TABLE (
    entity_type TEXT,
    entity_id INTEGER,
    display_text TEXT,
    detail_text TEXT,
    similarity_score REAL,
    search_field TEXT,
    additional_info JSONB
) 
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    
    -- Possessori (se abilitato)
    (SELECT 
        'possessore'::TEXT as entity_type,
        p.id as entity_id,
        p.nome_completo as display_text,
        CONCAT(p.cognome_nome, ' - ', c.nome) as detail_text,
        similarity(p.nome_completo, query_text) as similarity_score,
        'nome_completo'::TEXT as search_field,
        jsonb_build_object(
            'paternita', p.paternita,
            'comune', c.nome,
            'attivo', p.attivo
        ) as additional_info
    FROM possessore p
    JOIN comune c ON p.comune_id = c.id
    WHERE search_possessori AND p.nome_completo % query_text
    ORDER BY similarity(p.nome_completo, query_text) DESC
    LIMIT max_results_per_type)
    
    UNION ALL
    
    -- Località (se abilitato)
    (SELECT 
        'localita'::TEXT as entity_type,
        l.id as entity_id,
        l.nome as display_text,
        CONCAT(l.tipo, ' ', l.nome, ' - ', c.nome) as detail_text,
        similarity(l.nome, query_text) as similarity_score,
        'nome'::TEXT as search_field,
        jsonb_build_object(
            'tipo', l.tipo,
            'civico', l.civico,
            'comune', c.nome
        ) as additional_info
    FROM localita l
    JOIN comune c ON l.comune_id = c.id
    WHERE search_localita AND l.nome % query_text
    ORDER BY similarity(l.nome, query_text) DESC
    LIMIT max_results_per_type)
    
    UNION ALL
    
    -- Immobili (se abilitato)
    (SELECT 
        'immobile'::TEXT as entity_type,
        i.id as entity_id,
        i.natura as display_text,
        CONCAT('Partita ', p.numero_partita, 
               CASE WHEN p.suffisso_partita IS NOT NULL 
                    THEN CONCAT(' ', p.suffisso_partita) 
                    ELSE '' END,
               ' - ', l.nome, ' - ', c.nome) as detail_text,
        ims.similarity_score,
        ims.search_field,
        jsonb_build_object(
            'classificazione', i.classificazione,
            'consistenza', i.consistenza,
            'numero_partita', p.numero_partita,
            'suffisso_partita', p.suffisso_partita,
            'localita', l.nome,
            'comune', c.nome
        ) as additional_info
    FROM search_immobili_fuzzy(query_text, similarity_threshold, max_results_per_type) ims
    JOIN immobile i ON ims.id = i.id
    JOIN partita p ON i.partita_id = p.id
    JOIN localita l ON i.localita_id = l.id
    JOIN comune c ON p.comune_id = c.id
    WHERE search_immobili)
    
    UNION ALL
    
    -- Variazioni (se abilitato)
    (SELECT 
        'variazione'::TEXT as entity_type,
        vs.id as entity_id,
        vs.tipo as display_text,
        CONCAT('Partita ', vs.numero_partita_origine, ' → ',
               COALESCE(vs.numero_partita_destinazione::text, 'N/A'),
               ' - ', vs.comune_nome) as detail_text,
        vs.similarity_score,
        vs.search_field,
        jsonb_build_object(
            'data_variazione', vs.data_variazione,
            'numero_riferimento', vs.numero_riferimento,
            'nominativo_riferimento', vs.nominativo_riferimento,
            'comune', vs.comune_nome
        ) as additional_info
    FROM search_variazioni_fuzzy(query_text, similarity_threshold, max_results_per_type) vs
    WHERE search_variazioni)
    
    UNION ALL
    
    -- Contratti (se abilitato)
    (SELECT 
        'contratto'::TEXT as entity_type,
        cs.id as entity_id,
        cs.tipo as display_text,
        CONCAT('Variazione ', cs.variazione_id, ' - ',
               COALESCE(cs.notaio, 'Notaio non specificato')) as detail_text,
        cs.similarity_score,
        cs.search_field,
        jsonb_build_object(
            'data_contratto', cs.data_contratto,
            'notaio', cs.notaio,
            'repertorio', cs.repertorio,
            'variazione_id', cs.variazione_id
        ) as additional_info
    FROM search_contratti_fuzzy(query_text, similarity_threshold, max_results_per_type) cs
    WHERE search_contratti)
    
    UNION ALL
    
    -- Partite (se abilitato)
    (SELECT 
        'partita'::TEXT as entity_type,
        ps.id as entity_id,
        CONCAT('Partita ', ps.numero_partita,
               CASE WHEN ps.suffisso_partita IS NOT NULL 
                    THEN CONCAT(' ', ps.suffisso_partita) 
                    ELSE '' END) as display_text,
        CONCAT(ps.comune_nome, ' - ', ps.stato, ' - ',
               ps.num_possessori, ' possessori, ',
               ps.num_immobili, ' immobili') as detail_text,
        ps.similarity_score,
        ps.search_field,
        jsonb_build_object(
            'data_impianto', ps.data_impianto,
            'stato', ps.stato,
            'tipo', ps.tipo,
            'num_possessori', ps.num_possessori,
            'num_immobili', ps.num_immobili,
            'comune', ps.comune_nome
        ) as additional_info
    FROM search_partite_fuzzy(query_text, similarity_threshold, max_results_per_type) ps
    WHERE search_partite)
    
    ORDER BY similarity_score DESC;
END;
$$;

-- ========================================================================
-- 4. FUNZIONE DI VERIFICA INDICI GIN
-- ========================================================================

CREATE OR REPLACE FUNCTION verify_gin_indices()
RETURNS TABLE (
    table_name TEXT,
    index_name TEXT,
    column_name TEXT,
    is_gin BOOLEAN,
    status TEXT
) 
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT 
        t.table_name::TEXT,
        i.indexname::TEXT as index_name,
        CASE 
            WHEN i.indexdef LIKE '%gin(%' THEN
                substring(i.indexdef from 'gin\(([^)]+)\)')
            ELSE 'N/A'
        END::TEXT as column_name,
        (i.indexdef LIKE '%USING gin%')::BOOLEAN as is_gin,
        CASE 
            WHEN i.indexdef LIKE '%USING gin%' THEN 'OK'
            ELSE 'Missing or not GIN'
        END::TEXT as status
    FROM information_schema.tables t
    LEFT JOIN pg_indexes i ON t.table_name = i.tablename
    WHERE t.table_schema = 'catasto'
    AND t.table_name IN ('possessore', 'localita', 'immobile', 'variazione', 'contratto', 'partita')
    AND (i.indexname IS NULL OR i.indexname LIKE '%gin%')
    ORDER BY t.table_name, i.indexname;
END;
$$;

-- ========================================================================
-- 5. COMMENTI E DOCUMENTAZIONE
-- ========================================================================

COMMENT ON FUNCTION search_immobili_fuzzy(TEXT, REAL, INTEGER) IS 
'Ricerca fuzzy negli immobili per natura, classificazione e consistenza';

COMMENT ON FUNCTION search_variazioni_fuzzy(TEXT, REAL, INTEGER) IS 
'Ricerca fuzzy nelle variazioni per tipo, nominativo e numero di riferimento';

COMMENT ON FUNCTION search_contratti_fuzzy(TEXT, REAL, INTEGER) IS 
'Ricerca fuzzy nei contratti per tipo, notaio, repertorio e note';

COMMENT ON FUNCTION search_partite_fuzzy(TEXT, REAL, INTEGER) IS 
'Ricerca fuzzy nelle partite per numero e suffisso';

COMMENT ON FUNCTION search_all_entities_fuzzy(TEXT, REAL, BOOLEAN, BOOLEAN, BOOLEAN, BOOLEAN, BOOLEAN, BOOLEAN, INTEGER) IS 
'Ricerca fuzzy unificata in tutte le entità del sistema catasto';

COMMENT ON FUNCTION verify_gin_indices() IS 
'Verifica la presenza e lo stato degli indici GIN per la ricerca fuzzy';

-- ========================================================================
-- 6. TEST DI VERIFICA
-- ========================================================================

-- Verifica degli indici creati
SELECT 'Indici GIN creati con successo' as status;
SELECT * FROM verify_gin_indices();

-- Test base delle nuove funzioni
SELECT 'Test ricerca immobili:' as test;
SELECT count(*) as risultati_immobili FROM search_immobili_fuzzy('terra', 0.3, 10);

SELECT 'Test ricerca variazioni:' as test;
SELECT count(*) as risultati_variazioni FROM search_variazioni_fuzzy('vend', 0.3, 10);

SELECT 'Test ricerca contratti:' as test;
SELECT count(*) as risultati_contratti FROM search_contratti_fuzzy('compr', 0.3, 10);

SELECT 'Test ricerca partite:' as test;
SELECT count(*) as risultati_partite FROM search_partite_fuzzy('1', 0.3, 10);

SELECT 'Ampliamento ricerca fuzzy completato con successo!' as status;