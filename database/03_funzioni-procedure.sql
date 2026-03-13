-- ========================================================================
-- SCRIPT UNIFICATO PER FUNZIONI, PROCEDURE, VISTE E INDICI GIN
-- Versione: Definitiva
-- ========================================================================

SET search_path TO catasto, public;

-- ========================================================================
-- 1. FUNZIONI E TRIGGER DI UTILITÀ (dal file originale 03)
-- ========================================================================

CREATE OR REPLACE FUNCTION update_modified_column()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'UPDATE' THEN
        NEW.data_modifica = now();
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE 'plpgsql';

-- Applicazione dei trigger (omesso per brevità, ma da includere nel tuo script finale)
-- CREATE TRIGGER update_comune_modifica BEFORE UPDATE ON comune... etc.


-- ========================================================================
-- 2. VISTE PRINCIPALI (dal file originale 03)
-- ========================================================================

CREATE OR REPLACE VIEW v_partite_complete AS
SELECT
    p.id AS partita_id, c.nome AS comune_nome, p.numero_partita, p.suffisso_partita,
    p.tipo, p.data_impianto, p.data_chiusura, p.stato,
    pos.id AS possessore_id, pos.nome_completo, pp.titolo, pp.quota,
    (SELECT COUNT(i.id) FROM immobile i WHERE i.partita_id = p.id) AS num_immobili
FROM partita p
JOIN comune c ON p.comune_id = c.id
LEFT JOIN partita_possessore pp ON p.id = pp.partita_id
LEFT JOIN possessore pos ON pp.possessore_id = pos.id;

CREATE OR REPLACE VIEW v_variazioni_complete AS
SELECT
    v.id AS variazione_id, v.tipo AS tipo_variazione, v.data_variazione,
    p_orig.id as partita_origine_id, p_orig.numero_partita AS partita_origine_numero, c_orig.nome AS partita_origine_comune,
    p_dest.id as partita_destinazione_id, p_dest.numero_partita AS partita_dest_numero, c_dest.nome AS partita_dest_comune,
    con.tipo AS tipo_contratto, con.data_contratto, con.notaio, con.repertorio
FROM variazione v
JOIN partita p_orig ON v.partita_origine_id = p_orig.id
JOIN comune c_orig ON p_orig.comune_id = c_orig.id
LEFT JOIN partita p_dest ON v.partita_destinazione_id = p_dest.id
LEFT JOIN comune c_dest ON p_dest.comune_id = c_dest.id
LEFT JOIN contratto con ON v.id = con.variazione_id;


-- ========================================================================
-- 3. INDICI GIN PER RICERCA FUZZY (versione pulita da 03b)
-- Assicurati che l'estensione pg_trgm sia installata: CREATE EXTENSION IF NOT EXISTS pg_trgm;
-- ========================================================================

-- Indici per 'possessore'
CREATE INDEX IF NOT EXISTS idx_gin_possessore_nome_completo_trgm ON catasto.possessore USING gin (nome_completo gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_gin_possessore_cognome_nome_trgm ON catasto.possessore USING gin (cognome_nome gin_trgm_ops);

-- Indici per 'localita'
CREATE INDEX IF NOT EXISTS idx_gin_localita_nome_trgm ON catasto.localita USING gin (nome gin_trgm_ops);

-- Indici per 'immobile'
CREATE INDEX IF NOT EXISTS idx_gin_immobile_natura_trgm ON catasto.immobile USING gin (natura gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_gin_immobile_classificazione_trgm ON catasto.immobile USING gin (classificazione gin_trgm_ops);

-- Indici per 'variazione'
CREATE INDEX IF NOT EXISTS idx_gin_variazione_tipo_trgm ON catasto.variazione USING gin (tipo gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_gin_variazione_nominativo_trgm ON catasto.variazione USING gin (nominativo_riferimento gin_trgm_ops);

-- Indici per 'contratto'
CREATE INDEX IF NOT EXISTS idx_gin_contratto_tipo_trgm ON catasto.contratto USING gin (tipo gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_gin_contratto_notaio_trgm ON catasto.contratto USING gin (notaio gin_trgm_ops);

-- Indici per 'partita'
CREATE INDEX IF NOT EXISTS idx_gin_partita_numero_trgm ON catasto.partita USING gin (cast(numero_partita as text) gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_gin_partita_suffisso_trgm ON catasto.partita USING gin (suffisso_partita gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_gin_partita_tipo_trgm ON catasto.partita USING gin (tipo gin_trgm_ops);


-- ========================================================================
-- 4. FUNZIONE DI VERIFICA INDICI GIN (dal file 03b)
-- ========================================================================
CREATE OR REPLACE FUNCTION verify_gin_indices()
RETURNS TABLE (table_name TEXT, index_name TEXT, column_name TEXT, is_gin BOOLEAN, status TEXT) 
LANGUAGE plpgsql AS $$
BEGIN
    RETURN QUERY
    SELECT 
        t.table_name::TEXT,
        i.indexname::TEXT as index_name,
        i.indexdef::TEXT as column_name, -- Mostra la definizione completa per chiarezza
        (i.indexdef LIKE '%USING gin%')::BOOLEAN as is_gin,
        CASE 
            WHEN i.indexdef LIKE '%USING gin%' THEN 'OK'
            ELSE 'Missing or not GIN'
        END::TEXT as status
    FROM pg_tables t
    LEFT JOIN pg_indexes i ON t.tablename = i.tablename AND t.schemaname = i.schemaname
    WHERE t.schemaname = 'catasto'
      AND t.tablename IN ('possessore', 'localita', 'immobile', 'variazione', 'contratto', 'partita');
END;
$$;
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

-- Nota: le funzioni di ricerca fuzzy specifiche per ogni entità e la funzione unificata
-- sono state rimosse da qui perché ora sono gestite direttamente nel codice Python
-- nel file catasto_db_manager.py, il che è un approccio più flessibile.