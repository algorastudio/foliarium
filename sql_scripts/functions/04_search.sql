-- functions/04_search.sql
-- Funzioni di ricerca: fuzzy search (trigram), ricerca avanzata possessori,
-- ricerca avanzata immobili.
-- Versione: Foliarium v1.7.0+

-- ========================================================================
-- DA: 03b_expand_fuzzy_search.sql — SOLO FUNZIONI (senza CREATE INDEX)
-- ========================================================================

SET search_path TO catasto, public;

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

COMMENT ON FUNCTION search_immobili_fuzzy(TEXT, REAL, INTEGER) IS
'Ricerca fuzzy negli immobili per natura, classificazione e consistenza';

COMMENT ON FUNCTION search_variazioni_fuzzy(TEXT, REAL, INTEGER) IS
'Ricerca fuzzy nelle variazioni per tipo, nominativo e numero di riferimento';

COMMENT ON FUNCTION search_contratti_fuzzy(TEXT, REAL, INTEGER) IS
'Ricerca fuzzy nei contratti per tipo, notaio, repertorio e note';

COMMENT ON FUNCTION search_partite_fuzzy(TEXT, REAL, INTEGER) IS
'Ricerca fuzzy nelle partite per numero e suffisso';

COMMENT ON FUNCTION verify_gin_indices() IS
'Verifica la presenza e lo stato degli indici GIN per la ricerca fuzzy';

-- ========================================================================
-- DA: 16_advanced_search.sql — SOLO FUNZIONI (senza CREATE INDEX)
-- ========================================================================

-- File: 16_advanced_search.sql (Versione Corretta)
-- Oggetto: Funzioni per la ricerca avanzata nel database Catasto Storico
-- Versione: 1.1

SET search_path TO catasto, public;

-- ========================================================================
-- Funzione: ricerca_avanzata_possessori
-- ========================================================================
CREATE OR REPLACE FUNCTION catasto.ricerca_avanzata_possessori(
    p_query_text TEXT,
    p_similarity_threshold REAL DEFAULT 0.2
)
RETURNS TABLE (
    id INTEGER,
    nome_completo VARCHAR,
    cognome_nome VARCHAR,
    paternita VARCHAR,
    comune_nome VARCHAR,
    similarity REAL,
    num_partite BIGINT
) AS $$
BEGIN
    RETURN QUERY
    WITH possessore_base AS (
        SELECT
            p.id,
            p.nome_completo,
            p.cognome_nome,
            p.paternita,
            c.nome AS comune_nome
        FROM possessore p
        LEFT JOIN comune c ON p.comune_id = c.id
    ),
    possessore_similarity AS (
        SELECT
            pb.id,
            pb.nome_completo,
            pb.cognome_nome,
            pb.paternita,
            pb.comune_nome,
            GREATEST(
                similarity(pb.nome_completo, p_query_text),
                COALESCE(similarity(pb.cognome_nome, p_query_text), 0.0),
                COALESCE(similarity(pb.paternita, p_query_text), 0.0)
            ) AS sim
        FROM possessore_base pb
    )
    SELECT
        ps.id,
        ps.nome_completo::VARCHAR,
        ps.cognome_nome::VARCHAR,
        ps.paternita::VARCHAR,
        ps.comune_nome::VARCHAR,
        ps.sim AS similarity,
        (SELECT COUNT(DISTINCT pp.partita_id) FROM catasto.partita_possessore pp WHERE pp.possessore_id = ps.id)::BIGINT AS num_partite
    FROM possessore_similarity ps
    WHERE ps.sim >= p_similarity_threshold
    ORDER BY similarity DESC, ps.nome_completo
    LIMIT 100;
END;
$$ LANGUAGE plpgsql STABLE;

COMMENT ON FUNCTION catasto.ricerca_avanzata_possessori(TEXT, REAL) IS
'Ricerca possessori per similarita testuale.';

-- ========================================================================
-- Funzione: search_all_entities_fuzzy (versione corretta/aggiornata)
-- ========================================================================
DROP FUNCTION IF EXISTS search_all_entities_fuzzy(text,real,boolean,boolean,boolean,boolean,boolean,boolean,integer);

CREATE OR REPLACE FUNCTION search_all_entities_fuzzy(
    query_text TEXT,
    similarity_threshold REAL DEFAULT 0.3,
    search_possessori BOOLEAN DEFAULT TRUE,
    search_localita BOOLEAN DEFAULT TRUE,
    search_immobili BOOLEAN DEFAULT FALSE,
    search_variazioni BOOLEAN DEFAULT FALSE,
    search_contratti BOOLEAN DEFAULT FALSE,
    search_partite BOOLEAN DEFAULT FALSE,
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
    PERFORM set_limit(similarity_threshold);

    RETURN QUERY

    -- Possessori
    (SELECT
        'possessore'::TEXT,
        p.id,
        p.nome_completo::TEXT,
        CONCAT(p.cognome_nome, ' - ', c.nome)::TEXT,
        similarity(p.nome_completo, query_text),
        'nome_completo'::TEXT,
        jsonb_build_object(
            'paternita', p.paternita,
            'comune', c.nome,
            'attivo', p.attivo
        )
    FROM possessore p
    JOIN comune c ON p.comune_id = c.id
    WHERE search_possessori AND p.nome_completo % query_text
    ORDER BY similarity(p.nome_completo, query_text) DESC, p.id
    LIMIT max_results_per_type)

    UNION ALL

    -- Località
    (SELECT
        'localita'::TEXT,
        l.id,
        l.nome::TEXT,
        CONCAT(l.nome, ' - ', c.nome)::TEXT,
        similarity(l.nome, query_text),
        'nome'::TEXT,
        jsonb_build_object(
            'tipologia', l.tipologia_stradale,
            'comune', c.nome
        )
    FROM localita l
    JOIN comune c ON l.comune_id = c.id
    WHERE search_localita AND l.nome % query_text
    ORDER BY similarity(l.nome, query_text) DESC, l.id
    LIMIT max_results_per_type)

    UNION ALL

    -- Immobili (FIX APPLICATO)
    (SELECT
        'immobile'::TEXT,
        i.id,
        i.natura::TEXT,
        CONCAT('Partita ', p.numero_partita,
               CASE WHEN p.suffisso_partita IS NOT NULL AND p.suffisso_partita != ''
                    THEN CONCAT('/', p.suffisso_partita)
                    ELSE '' END,
               ' - ', l.nome, ' - ', c.nome)::TEXT,
        similarity(i.natura, query_text),
        'natura'::TEXT,
        jsonb_build_object(
            'partita', p.numero_partita,
            'suffisso_partita', COALESCE(p.suffisso_partita, ''),
            'localita', l.nome,
            'comune', c.nome,
            'classificazione', i.classificazione,
            'consistenza', i.consistenza
        )
    FROM immobile i
    JOIN partita p ON i.partita_id = p.id
    JOIN localita l ON i.localita_id = l.id
    JOIN comune c ON p.comune_id = c.id
    WHERE search_immobili AND i.natura % query_text
    ORDER BY similarity(i.natura, query_text) DESC, i.id
    LIMIT max_results_per_type * 2);

END;
$$;

SET search_path TO catasto, public;

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
        COALESCE(i.indexname, 'N/A')::TEXT as index_name,
        CASE
            WHEN i.indexdef LIKE '%gin(%' THEN
                substring(i.indexdef from 'gin\(([^)]+)\)')
            ELSE 'N/A'
        END::TEXT as column_name,
        COALESCE(i.indexdef LIKE '%USING gin%', false)::BOOLEAN as is_gin,
        CASE
            WHEN i.indexdef LIKE '%USING gin%' THEN 'OK'
            WHEN i.indexname IS NULL THEN 'No Index'
            ELSE 'Not GIN'
        END::TEXT as status
    FROM information_schema.tables t
    LEFT JOIN pg_indexes i ON t.table_name = i.tablename AND i.indexname LIKE '%gin%'
    WHERE t.table_schema = 'catasto'
    AND t.table_name IN ('possessore', 'localita', 'immobile', 'variazione', 'contratto', 'partita')
    ORDER BY t.table_name, i.indexname;
END;
$$;

-- ========================================================================
-- DA: 17_funzione_ricerca_immobili.sql — contenuto completo
-- ========================================================================

-- File: 17_funzione_ricerca_immobili.sql
-- Oggetto: Definizione funzione per ricerca avanzata immobili
-- Versione: 2.0
-- Data: 24/05/2025
SET search_path TO catasto, public;

CREATE OR REPLACE FUNCTION catasto.ricerca_avanzata_immobili(
    p_comune_id INTEGER DEFAULT NULL,
    p_localita_id INTEGER DEFAULT NULL,
    p_natura_search TEXT DEFAULT NULL,
    p_classificazione_search TEXT DEFAULT NULL,
    p_consistenza_search TEXT DEFAULT NULL,
    p_piani_min INTEGER DEFAULT NULL,
    p_piani_max INTEGER DEFAULT NULL,
    p_vani_min INTEGER DEFAULT NULL,
    p_vani_max INTEGER DEFAULT NULL,
    p_nome_possessore_search TEXT DEFAULT NULL,
    p_data_inizio_possesso_search DATE DEFAULT NULL,
    p_data_fine_possesso_search DATE DEFAULT NULL
)
RETURNS TABLE (
    id_immobile INTEGER,
    numero_partita INTEGER,
    comune_nome VARCHAR,
    localita_nome VARCHAR,
    civico VARCHAR,
    localita_tipo VARCHAR,
    natura VARCHAR,
    classificazione VARCHAR,
    consistenza VARCHAR,
    numero_piani INTEGER,
    numero_vani INTEGER,
    possessori_attuali TEXT
) AS $$
BEGIN
    RETURN QUERY
    SELECT DISTINCT
        i.id AS id_immobile,
        p.numero_partita,
        c.nome AS comune_nome,
        l.nome AS localita_nome,
        l.civico AS civico,
        tl.nome AS localita_tipo,
        i.natura,
        i.classificazione,
        i.consistenza,
        i.numero_piani,
        i.numero_vani,
        (SELECT string_agg(DISTINCT pos_agg.nome_completo, ', ')
         FROM catasto.partita_possessore pp_agg
         JOIN catasto.possessore pos_agg ON pp_agg.possessore_id = pos_agg.id
         WHERE pp_agg.partita_id = p.id AND pos_agg.attivo = TRUE) AS possessori_attuali
    FROM
        catasto.immobile i
    JOIN
        catasto.partita p ON i.partita_id = p.id
    JOIN
        catasto.comune c ON p.comune_id = c.id
    JOIN
        catasto.localita l ON i.localita_id = l.id
    LEFT JOIN
        catasto.tipo_localita tl ON l.tipo_id = tl.id
    LEFT JOIN
        catasto.partita_possessore pp_filter ON p.id = pp_filter.partita_id AND p_nome_possessore_search IS NOT NULL
    LEFT JOIN
        catasto.possessore pos_filter ON pp_filter.possessore_id = pos_filter.id AND pos_filter.nome_completo ILIKE ('%' || p_nome_possessore_search || '%')
    WHERE
        (p_comune_id IS NULL OR p.comune_id = p_comune_id)
    AND (p_localita_id IS NULL OR i.localita_id = p_localita_id)
    AND (p_natura_search IS NULL OR i.natura ILIKE ('%' || p_natura_search || '%'))
    AND (p_classificazione_search IS NULL OR i.classificazione ILIKE ('%' || p_classificazione_search || '%'))
    AND (p_consistenza_search IS NULL OR i.consistenza ILIKE ('%' || p_consistenza_search || '%'))
    AND (p_piani_min IS NULL OR i.numero_piani >= p_piani_min)
    AND (p_piani_max IS NULL OR i.numero_piani <= p_piani_max)
    AND (p_vani_min IS NULL OR i.numero_vani >= p_vani_min)
    AND (p_vani_max IS NULL OR i.numero_vani <= p_vani_max)
    AND (p_nome_possessore_search IS NULL OR pos_filter.id IS NOT NULL)
    ORDER BY
        c.nome, p.numero_partita, i.natura;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION catasto.ricerca_avanzata_immobili(INTEGER, INTEGER, TEXT, TEXT, TEXT, INTEGER, INTEGER, INTEGER, INTEGER, TEXT, DATE, DATE) IS
'Ricerca immobili avanzata con criteri estesi (ID comune, ID località, natura, classificazione, consistenza, piani, vani, nome possessore, date possesso).';
