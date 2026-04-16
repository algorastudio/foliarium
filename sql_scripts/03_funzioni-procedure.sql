-- Imposta lo schema
SET search_path TO catasto, public; -- Aggiunto public per estensioni

-- 1. Funzione per aggiornare automaticamente il timestamp di modifica
-- (Questa funzione è corretta e rimane invariata)
CREATE OR REPLACE FUNCTION update_modified_column()
RETURNS TRIGGER AS $$
BEGIN
    -- Assicurati che la tabella abbia la colonna data_modifica
    IF TG_OP = 'UPDATE' THEN
        NEW.data_modifica = now();
    END IF;
    -- Potresti voler gestire anche data_creazione qui se non impostata di default
    -- IF TG_OP = 'INSERT' THEN
    --    NEW.data_creazione = now();
    --    NEW.data_modifica = now();
    -- END IF;
    RETURN NEW;
END;
$$ LANGUAGE 'plpgsql';

-- Applica i trigger per aggiornare il timestamp sulle tabelle principali
-- (Assicurati che questi trigger vengano creati una sola volta)
--DROP TRIGGER IF EXISTS update_comune_modifica ON comune; -- Esempio drop se necessario
CREATE TRIGGER update_comune_modifica
BEFORE UPDATE ON comune
FOR EACH ROW EXECUTE FUNCTION update_modified_column();

--DROP TRIGGER IF EXISTS update_partita_modifica ON partita;
CREATE TRIGGER update_partita_modifica
BEFORE UPDATE ON partita
FOR EACH ROW EXECUTE FUNCTION update_modified_column();

--DROP TRIGGER IF EXISTS update_possessore_modifica ON possessore;
CREATE TRIGGER update_possessore_modifica
BEFORE UPDATE ON possessore
FOR EACH ROW EXECUTE FUNCTION update_modified_column();

--DROP TRIGGER IF EXISTS update_immobile_modifica ON immobile;
CREATE TRIGGER update_immobile_modifica
BEFORE UPDATE ON immobile
FOR EACH ROW EXECUTE FUNCTION update_modified_column();

--DROP TRIGGER IF EXISTS update_localita_modifica ON localita;
CREATE TRIGGER update_localita_modifica
BEFORE UPDATE ON localita
FOR EACH ROW EXECUTE FUNCTION update_modified_column();

--DROP TRIGGER IF EXISTS update_variazione_modifica ON variazione;
CREATE TRIGGER update_variazione_modifica
BEFORE UPDATE ON variazione
FOR EACH ROW EXECUTE FUNCTION update_modified_column();

-- 2. Procedura per inserire un nuovo possessore (MODIFICATA: usa comune_id)
CREATE OR REPLACE PROCEDURE inserisci_possessore(
    p_comune_id INTEGER, -- Modificato da p_comune_nome
    p_cognome_nome VARCHAR(255),
    p_paternita VARCHAR(255),
    p_nome_completo VARCHAR(255),
    p_attivo BOOLEAN DEFAULT TRUE
)
LANGUAGE plpgsql
AS $$
BEGIN
    -- Verifica che il comune_id esista (opzionale ma consigliato)
    IF NOT EXISTS (SELECT 1 FROM comune WHERE id = p_comune_id) THEN
        RAISE EXCEPTION 'Comune con ID % non trovato.', p_comune_id;
    END IF;

    INSERT INTO possessore(comune_id, cognome_nome, paternita, nome_completo, attivo)
    VALUES (p_comune_id, p_cognome_nome, p_paternita, p_nome_completo, p_attivo);
END;
$$;

-- 3. Funzione per verificare se una partita è attiva (Invariata)
CREATE OR REPLACE FUNCTION is_partita_attiva(p_partita_id INTEGER)
RETURNS BOOLEAN AS $$
DECLARE
    v_stato VARCHAR(20);
BEGIN
    SELECT stato INTO v_stato FROM partita WHERE id = p_partita_id;
    RETURN (v_stato = 'attiva');
END;
$$ LANGUAGE plpgsql;

-- 4. Procedura per registrare una nuova partita e relativi possessori (MODIFICATA: usa comune_id)
CREATE OR REPLACE PROCEDURE inserisci_partita_con_possessori(
    p_comune_id INTEGER, -- Modificato da p_comune_nome
    p_numero_partita INTEGER,
    p_tipo VARCHAR(20),
    p_data_impianto DATE,
    p_possessore_ids INTEGER[]
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_partita_id INTEGER;
    v_possessore_id INTEGER;
BEGIN
    -- Verifica che il comune_id esista (opzionale ma consigliato)
    IF NOT EXISTS (SELECT 1 FROM comune WHERE id = p_comune_id) THEN
        RAISE EXCEPTION 'Comune con ID % non trovato.', p_comune_id;
    END IF;

    -- Inserisci la partita
    INSERT INTO partita(comune_id, numero_partita, tipo, data_impianto, stato)
    VALUES (p_comune_id, p_numero_partita, p_tipo, p_data_impianto, 'attiva')
    RETURNING id INTO v_partita_id;

    -- Collega i possessori
    FOREACH v_possessore_id IN ARRAY p_possessore_ids
    LOOP
        -- Verifica che il possessore esista
        IF EXISTS (SELECT 1 FROM possessore WHERE id = v_possessore_id) THEN
             INSERT INTO partita_possessore(partita_id, possessore_id, tipo_partita)
             VALUES (v_partita_id, v_possessore_id, p_tipo);
        ELSE
             RAISE WARNING 'Possessore ID % non trovato, impossibile collegarlo alla partita ID %', v_possessore_id, v_partita_id;
        END IF;
    END LOOP;
END;
$$;

-- 5. Procedura per registrare una variazione di proprietà (Invariata rispetto a comune_id)
--    Nota: La logica assume che partita_origine_id e partita_destinazione_id siano corretti.
CREATE OR REPLACE PROCEDURE registra_variazione(
    p_partita_origine_id INTEGER,
    p_partita_destinazione_id INTEGER,
    p_tipo VARCHAR(50),
    p_data_variazione DATE,
    p_numero_riferimento VARCHAR(50),
    p_nominativo_riferimento VARCHAR(255),
    p_tipo_contratto VARCHAR(50),
    p_data_contratto DATE,
    p_notaio VARCHAR(255),
    p_repertorio VARCHAR(100),
    p_note TEXT
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_variazione_id INTEGER;
BEGIN
    -- Verifica che la partita origine sia attiva
    IF NOT is_partita_attiva(p_partita_origine_id) THEN
        RAISE EXCEPTION 'La partita di origine ID % non è attiva', p_partita_origine_id;
    END IF;

    -- Inserisci la variazione
    INSERT INTO variazione(partita_origine_id, partita_destinazione_id, tipo, data_variazione,
                          numero_riferimento, nominativo_riferimento)
    VALUES (p_partita_origine_id, p_partita_destinazione_id, p_tipo, p_data_variazione,
           p_numero_riferimento, p_nominativo_riferimento)
    RETURNING id INTO v_variazione_id;

    -- Inserisci il contratto associato (se fornito)
    IF p_tipo_contratto IS NOT NULL AND p_data_contratto IS NOT NULL THEN
        INSERT INTO contratto(variazione_id, tipo, data_contratto, notaio, repertorio, note)
        VALUES (v_variazione_id, p_tipo_contratto, p_data_contratto, p_notaio, p_repertorio, p_note);
    END IF;

    -- Se è una variazione che inattiva la partita di origine (es. vendita totale, successione completa)
    -- La logica workflow più complessa è in script 13
    IF p_tipo IN ('Vendita', 'Successione', 'Frazionamento') AND p_partita_destinazione_id IS NOT NULL THEN
         -- Potrebbe essere necessario verificare se TUTTI gli immobili sono stati trasferiti
         -- per decidere se chiudere la partita origine. Questa logica semplice la chiude.
        UPDATE partita SET stato = 'inattiva', data_chiusura = p_data_variazione
        WHERE id = p_partita_origine_id;
    END IF;
END;
$$;

-- 6. Funzione per ottenere tutti gli immobili di un possessore (MODIFICATA: join con comune)
CREATE OR REPLACE FUNCTION get_immobili_possessore(p_possessore_id INTEGER)
RETURNS TABLE (
    immobile_id INTEGER,
    natura VARCHAR(100),
    localita_nome VARCHAR(255),
    comune_nome VARCHAR(100), -- Nome colonna output
    partita_numero INTEGER,
    tipo_partita VARCHAR(20)
) AS $$
BEGIN
    RETURN QUERY
    SELECT i.id, i.natura, l.nome, c.nome, p.numero_partita, pp.tipo_partita -- Seleziona c.nome
    FROM immobile i
    JOIN localita l ON i.localita_id = l.id
    JOIN partita p ON i.partita_id = p.id
    JOIN comune c ON p.comune_id = c.id -- *** JOIN AGGIUNTO ***
    JOIN partita_possessore pp ON p.id = pp.partita_id
    WHERE pp.possessore_id = p_possessore_id AND p.stato = 'attiva';
END;
$$ LANGUAGE plpgsql;

-- 7. Procedura per registrare una consultazione (Invariata)
CREATE OR REPLACE PROCEDURE registra_consultazione(
    p_data DATE,
    p_richiedente VARCHAR(255),
    p_documento_identita VARCHAR(100),
    p_motivazione TEXT,
    p_materiale_consultato TEXT,
    p_funzionario_autorizzante VARCHAR(255)
)
LANGUAGE plpgsql
AS $$
BEGIN
    INSERT INTO consultazione(data, richiedente, documento_identita, motivazione,
                             materiale_consultato, funzionario_autorizzante)
    VALUES (p_data, p_richiedente, p_documento_identita, p_motivazione,
           p_materiale_consultato, p_funzionario_autorizzante);
END;
$$;

-- 8. Vista per facilitare la ricerca di partite (MODIFICATA: join con comune)
-- DROP VIEW IF EXISTS v_partite_complete; -- Rimuovi se necessario ricrearla
CREATE OR REPLACE VIEW v_partite_complete AS
SELECT
    p.id AS partita_id,
    c.nome AS comune_nome, -- Seleziona c.nome
    p.numero_partita,
    p.tipo,
    p.data_impianto,
    p.data_chiusura,
    p.stato,
    pos.id AS possessore_id,
    pos.cognome_nome,
    pos.paternita,
    pos.nome_completo,
    pp.titolo,
    pp.quota,
    COUNT(i.id) AS num_immobili -- Conta immobili associati
FROM partita p
JOIN comune c ON p.comune_id = c.id -- *** JOIN AGGIUNTO ***
LEFT JOIN partita_possessore pp ON p.id = pp.partita_id
LEFT JOIN possessore pos ON pp.possessore_id = pos.id
LEFT JOIN immobile i ON p.id = i.partita_id
GROUP BY p.id, c.nome, p.numero_partita, p.tipo, p.data_impianto, p.data_chiusura,
         p.stato, pos.id, pos.cognome_nome, pos.paternita, pos.nome_completo, pp.titolo, pp.quota;

-- 9. Vista per le variazioni complete con contratti (MODIFICATA: join con comune)
-- DROP VIEW IF EXISTS v_variazioni_complete; -- Rimuovi se necessario ricrearla
CREATE OR REPLACE VIEW catasto.v_variazioni_complete AS
SELECT
    v.id AS variazione_id,
    v.tipo AS tipo_variazione,
    v.data_variazione,
    p_orig.id as partita_origine_id,
    p_orig.numero_partita AS partita_origine_numero,
    c_orig.nome AS partita_origine_comune,
    p_orig.comune_id AS partita_origine_comune_id, -- <-- AGGIUNTA CHIAVE
    p_dest.id as partita_destinazione_id,
    p_dest.numero_partita AS partita_dest_numero,
    c_dest.nome AS partita_dest_comune,
    con.tipo AS tipo_contratto,
    con.data_contratto,
    con.notaio,
    con.repertorio
FROM variazione v
JOIN partita p_orig ON v.partita_origine_id = p_orig.id
JOIN comune c_orig ON p_orig.comune_id = c_orig.id
LEFT JOIN partita p_dest ON v.partita_destinazione_id = p_dest.id
LEFT JOIN comune c_dest ON p_dest.comune_id = c_dest.id
LEFT JOIN contratto con ON v.id = con.variazione_id;

-- 10. Funzione per ricerca full-text di possessori (MODIFICATA: join con comune)
CREATE OR REPLACE FUNCTION cerca_possessori(p_query TEXT)
RETURNS TABLE (
    id INTEGER,
    nome_completo VARCHAR(255),
    comune_nome VARCHAR(100), -- Nome colonna output
    num_partite BIGINT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        p.id,
        p.nome_completo,
        c.nome, -- Seleziona c.nome
        COUNT(DISTINCT pp.partita_id) AS num_partite
    FROM possessore p
    JOIN comune c ON p.comune_id = c.id -- *** JOIN AGGIUNTO ***
    LEFT JOIN partita_possessore pp ON p.id = pp.possessore_id
    WHERE
        p.nome_completo ILIKE '%' || p_query || '%' OR
        p.cognome_nome ILIKE '%' || p_query || '%' OR
        p.paternita ILIKE '%' || p_query || '%'
    GROUP BY p.id, p.nome_completo, c.nome -- Raggruppa per c.nome
    ORDER BY num_partite DESC;
END;
$$ LANGUAGE plpgsql;

-- ========================================================================
-- FUNZIONI PER RICERCA FUZZY AMPLIATA
-- 
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
        CONCAT(l.tipo, ' ', l.nome, ' - ', c.nome)::TEXT,
        similarity(l.nome, query_text),
        'nome'::TEXT,
        jsonb_build_object(
            'tipo', l.tipo,
            'civico', l.civico,
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
-- Test
SELECT 'Fix applicato con successo!' as status;