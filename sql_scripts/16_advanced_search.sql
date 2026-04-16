-- File: 16_advanced_search.sql (Versione Corretta)
-- Oggetto: Funzioni per la ricerca avanzata nel database Catasto Storico
-- Versione: 1.1
-- Data: 30/04/2025
-- Note: Corretta sintassi funzione e aggiunto join con comune.

-- Imposta lo schema (assicurati che sia corretto nel tuo ambiente)
SET search_path TO catasto, public; -- Aggiunto public se pg_trgm è lì

-- ========================================================================
-- Funzione: ricerca_avanzata_possessori
-- Ricerca possessori basandosi sulla similarità testuale con nome/cognome/paternità
-- utilizzando l'estensione pg_trgm.
-- Include il nome del comune nei risultati.
-- ========================================================================
-- Nello script SQL che definisce ricerca_avanzata_possessori(TEXT, REAL)
CREATE OR REPLACE FUNCTION catasto.ricerca_avanzata_possessori(
    p_query_text TEXT,
    p_similarity_threshold REAL DEFAULT 0.2
)
RETURNS TABLE (
    id INTEGER,
    nome_completo VARCHAR, -- o TEXT
    cognome_nome VARCHAR,  -- Aggiunto (assicurati esista in tabella possessore)
    paternita VARCHAR,     -- Aggiunto (assicurati esista in tabella possessore)
    comune_nome VARCHAR,   -- o TEXT
    similarity REAL,
    num_partite BIGINT
) AS $$
BEGIN
    RETURN QUERY
    WITH possessore_base AS (
        SELECT
            p.id,
            p.nome_completo,
            p.cognome_nome, -- Includi qui
            p.paternita,    -- Includi qui
            c.nome AS comune_nome
        FROM possessore p
        LEFT JOIN comune c ON p.comune_id = c.id
    ),
    possessore_similarity AS (
        SELECT
            pb.id,
            pb.nome_completo,
            pb.cognome_nome, -- Propaga
            pb.paternita,    -- Propaga
            pb.comune_nome,
            GREATEST(
                similarity(pb.nome_completo, p_query_text),
                COALESCE(similarity(pb.cognome_nome, p_query_text), 0.0), -- Se cognome_nome non esiste, rimuovi
                COALESCE(similarity(pb.paternita, p_query_text), 0.0)
            ) AS sim
        FROM possessore_base pb
    )
    SELECT
        ps.id,
        ps.nome_completo::VARCHAR,
        ps.cognome_nome::VARCHAR,  -- Restituisci
        ps.paternita::VARCHAR,     -- Restituisci
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
-- OTTIMIZZAZIONE (CONSIGLIATA): Creare indici GIN per pg_trgm
-- Questi indici migliorano drasticamente le performance della ricerca per similarità
-- su tabelle grandi. Eseguire una sola volta dopo aver creato l'estensione.
-- (Lasciati commentati per evitare errori se già esistenti o se l'estensione non c'è)
-- ========================================================================


-- Indice principale su nome_completo
CREATE INDEX IF NOT EXISTS idx_gin_possessore_nome_completo_trgm
ON possessore
USING gin (nome_completo gin_trgm_ops);

-- Indice opzionale su cognome_nome
CREATE INDEX IF NOT EXISTS idx_gin_possessore_cognome_nome_trgm
ON possessore
USING gin (cognome_nome gin_trgm_ops);

-- Indice opzionale su paternita (solo per valori non NULL)
CREATE INDEX IF NOT EXISTS idx_gin_possessore_paternita_trgm
ON possessore
USING gin (paternita gin_trgm_ops)
WHERE paternita IS NOT NULL;

