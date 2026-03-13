-- Imposta lo schema
SET search_path TO catasto;
/* 
-- 1. Estensione per la gestione di periodi storici
CREATE TABLE periodo_storico (
    id SERIAL PRIMARY KEY,
    nome VARCHAR(100) NOT NULL UNIQUE,
    anno_inizio INTEGER NOT NULL,
    anno_fine INTEGER,
    descrizione TEXT,
    data_creazione TIMESTAMP(0) DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO periodo_storico (nome, anno_inizio, anno_fine, descrizione)
VALUES 
('Regno di Sardegna', 1720, 1861, 'Periodo del Regno di Sardegna prima dell''unità d''Italia'),
('Regno d''Italia', 1861, 1946, 'Periodo del Regno d''Italia'),
('Repubblica Italiana', 1946, NULL, 'Periodo della Repubblica Italiana')
ON CONFLICT (nome) DO NOTHING; -- O DO UPDATE SET ... se preferisci aggiornare */

-- 2. Estensione delle tabelle per contemplare il periodo storico
--ALTER TABLE comune ADD COLUMN periodo_id INTEGER REFERENCES periodo_storico(id);
ALTER TABLE localita ADD COLUMN periodo_id INTEGER REFERENCES periodo_storico(id);

-- Aggiorna i dati esistenti
UPDATE comune SET periodo_id = 3; -- Repubblica Italiana
UPDATE localita SET periodo_id = 3; -- Repubblica Italiana

-- 3. Estensione per gestire le variazioni dei nomi storici di luoghi
CREATE TABLE nome_storico (
    id SERIAL PRIMARY KEY,
    entita_tipo VARCHAR(20) NOT NULL CHECK (entita_tipo IN ('comune', 'localita')),
    entita_id INTEGER NOT NULL,
    nome VARCHAR(100) NOT NULL,
    periodo_id INTEGER REFERENCES periodo_storico(id),
    anno_inizio INTEGER NOT NULL,
    anno_fine INTEGER,
    note TEXT,
    data_creazione TIMESTAMP(0) DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_nome_storico_entita ON nome_storico(entita_tipo, entita_id);
CREATE INDEX idx_nome_storico_periodo ON nome_storico(periodo_id);

-- 4. Funzione per ottenere il nome storico corretto per una data
CREATE OR REPLACE FUNCTION get_nome_storico(
    p_entita_tipo VARCHAR,
    p_entita_id INTEGER,
    p_anno INTEGER DEFAULT EXTRACT(YEAR FROM CURRENT_DATE)
)
RETURNS TABLE (
    nome VARCHAR,
    anno_inizio INTEGER,
    anno_fine INTEGER,
    periodo_nome VARCHAR
) AS $$
BEGIN
    RETURN QUERY
    WITH nomi AS (
        -- Nome storico se esiste per il periodo specificato
        SELECT 
            ns.nome,
            ns.anno_inizio,
            ns.anno_fine,
            ps.nome AS periodo_nome
        FROM nome_storico ns
        JOIN periodo_storico ps ON ns.periodo_id = ps.id
        WHERE ns.entita_tipo = p_entita_tipo
          AND ns.entita_id = p_entita_id
          AND ns.anno_inizio <= p_anno
          AND (ns.anno_fine IS NULL OR ns.anno_fine >= p_anno)
        
        UNION ALL
        
        -- Nome attuale dal comune se non c'è un nome storico
        SELECT 
            c.nome,
            ps.anno_inizio,
            ps.anno_fine,
            ps.nome AS periodo_nome
        FROM comune c
        JOIN periodo_storico ps ON c.periodo_id = ps.id
        WHERE p_entita_tipo = 'comune'
          AND c.id = p_entita_id
          AND NOT EXISTS (
              SELECT 1 FROM nome_storico ns
              WHERE ns.entita_tipo = 'comune'
                AND ns.entita_id = c.id
                AND ns.anno_inizio <= p_anno
                AND (ns.anno_fine IS NULL OR ns.anno_fine >= p_anno)
          )
          AND ps.anno_inizio <= p_anno
          AND (ps.anno_fine IS NULL OR ps.anno_fine >= p_anno)
        
        UNION ALL
        
        -- Nome attuale dalla località se non c'è un nome storico
        SELECT 
            l.nome,
            ps.anno_inizio,
            ps.anno_fine,
            ps.nome AS periodo_nome
        FROM localita l
        JOIN periodo_storico ps ON l.periodo_id = ps.id
        WHERE p_entita_tipo = 'localita'
          AND l.id = p_entita_id
          AND NOT EXISTS (
              SELECT 1 FROM nome_storico ns
              WHERE ns.entita_tipo = 'localita'
                AND ns.entita_id = l.id
                AND ns.anno_inizio <= p_anno
                AND (ns.anno_fine IS NULL OR ns.anno_fine >= p_anno)
          )
          AND ps.anno_inizio <= p_anno
          AND (ps.anno_fine IS NULL OR ps.anno_fine >= p_anno)
    )
    SELECT * FROM nomi
    LIMIT 1;
END;
$$ LANGUAGE plpgsql;

-- 5. Procedura per registrare un nome storico
CREATE OR REPLACE PROCEDURE registra_nome_storico(
    p_entita_tipo VARCHAR,
    p_entita_id INTEGER,
    p_nome VARCHAR,
    p_periodo_id INTEGER,
    p_anno_inizio INTEGER,
    p_anno_fine INTEGER DEFAULT NULL,
    p_note TEXT DEFAULT NULL
)
LANGUAGE plpgsql
AS $$
BEGIN
    INSERT INTO nome_storico (entita_tipo, entita_id, nome, periodo_id, anno_inizio, anno_fine, note)
    VALUES (p_entita_tipo, p_entita_id, p_nome, p_periodo_id, p_anno_inizio, p_anno_fine, p_note);
END;
$$;

-- 6. Estensione per la gestione dei documenti storici
CREATE TABLE documento_storico (
    id SERIAL PRIMARY KEY,
    titolo VARCHAR(255) NOT NULL,
    descrizione TEXT,
    anno INTEGER,
    periodo_id INTEGER REFERENCES periodo_storico(id),
    tipo_documento VARCHAR(100) NOT NULL,
    percorso_file VARCHAR(255),
    metadati JSONB,
    data_creazione TIMESTAMP(0) DEFAULT CURRENT_TIMESTAMP,
    data_modifica TIMESTAMP(0) DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_documento_anno ON documento_storico(anno);
CREATE INDEX idx_documento_tipo ON documento_storico(tipo_documento);
CREATE INDEX idx_documento_periodo ON documento_storico(periodo_id);

-- 7. Tabella di collegamento tra documenti e partite
CREATE TABLE documento_partita (
    documento_id INTEGER REFERENCES documento_storico(id) ON DELETE CASCADE,
    partita_id INTEGER REFERENCES partita(id) ON DELETE CASCADE,
    rilevanza VARCHAR(20) NOT NULL CHECK (rilevanza IN ('primaria', 'secondaria', 'correlata')),
    note TEXT,
    data_creazione TIMESTAMP(0) DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (documento_id, partita_id)
);

-- 8. Funzione per la ricerca di documenti storici
CREATE OR REPLACE FUNCTION ricerca_documenti_storici(
    p_titolo VARCHAR DEFAULT NULL,
    p_tipo VARCHAR DEFAULT NULL,
    p_periodo_id INTEGER DEFAULT NULL,
    p_anno_inizio INTEGER DEFAULT NULL,
    p_anno_fine INTEGER DEFAULT NULL,
    p_partita_id INTEGER DEFAULT NULL
)
RETURNS TABLE (
    documento_id INTEGER,
    titolo VARCHAR,
    descrizione TEXT,
    anno INTEGER,
    periodo_nome VARCHAR,
    tipo_documento VARCHAR,
    partite_correlate TEXT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        d.id AS documento_id,
        d.titolo,
        d.descrizione,
        d.anno,
        ps.nome AS periodo_nome,
        d.tipo_documento,
        string_agg(DISTINCT p.comune_nome || ' - ' || p.numero_partita, ', ') AS partite_correlate
    FROM documento_storico d
    JOIN periodo_storico ps ON d.periodo_id = ps.id
    LEFT JOIN documento_partita dp ON d.id = dp.documento_id
    LEFT JOIN partita p ON dp.partita_id = p.id
    WHERE 
        (p_titolo IS NULL OR d.titolo ILIKE '%' || p_titolo || '%') AND
        (p_tipo IS NULL OR d.tipo_documento = p_tipo) AND
        (p_periodo_id IS NULL OR d.periodo_id = p_periodo_id) AND
        (p_anno_inizio IS NULL OR d.anno >= p_anno_inizio) AND
        (p_anno_fine IS NULL OR d.anno <= p_anno_fine) AND
        (p_partita_id IS NULL OR dp.partita_id = p_partita_id)
    GROUP BY d.id, d.titolo, d.descrizione, d.anno, ps.nome, d.tipo_documento
    ORDER BY d.anno DESC, d.titolo;
END;
$$ LANGUAGE plpgsql;

-- 9. Funzione per ricostruire l'albero genealogico di proprietà
CREATE OR REPLACE FUNCTION albero_genealogico_proprieta(p_partita_id INTEGER)
RETURNS TABLE (
    livello INTEGER,
    tipo_relazione VARCHAR,
    partita_id INTEGER,
    comune_nome VARCHAR,
    numero_partita INTEGER,
    tipo VARCHAR,
    possessori TEXT,
    data_variazione DATE
) AS $$
BEGIN
    -- Crea una tabella temporanea per archiviare i risultati
    CREATE TEMPORARY TABLE IF NOT EXISTS temp_albero (
        livello INTEGER,
        tipo_relazione VARCHAR,
        partita_id INTEGER,
        comune_nome VARCHAR,
        numero_partita INTEGER,
        tipo VARCHAR,
        possessori TEXT,
        data_variazione DATE
    ) ON COMMIT DROP;
    
    -- Pulisci la tabella temporanea
    DELETE FROM temp_albero;
    
    -- Inserisci la partita corrente (radice)
    INSERT INTO temp_albero
    SELECT 
        0 AS livello,
        'corrente'::VARCHAR AS tipo_relazione,
        p.id AS partita_id,
        p.comune_nome,
        p.numero_partita,
        p.tipo,
        string_agg(DISTINCT pos.nome_completo, ', ') AS possessori,
        NULL::DATE AS data_variazione
    FROM partita p
    LEFT JOIN partita_possessore pp ON p.id = pp.partita_id
    LEFT JOIN possessore pos ON pp.possessore_id = pos.id
    WHERE p.id = p_partita_id
    GROUP BY p.id, p.comune_nome, p.numero_partita, p.tipo;
    
    -- Ricorsione manuale per i predecessori (livelli negativi)
    FOR i IN 1..5 LOOP
        -- Aggiungi i predecessori al livello corrente
        INSERT INTO temp_albero
        SELECT 
            -i AS livello,
            'predecessore'::VARCHAR,
            p.id,
            p.comune_nome,
            p.numero_partita,
            p.tipo,
            string_agg(DISTINCT pos.nome_completo, ', '),
            v.data_variazione
        FROM partita p
        JOIN variazione v ON p.id = v.partita_origine_id
        JOIN temp_albero a ON v.partita_destinazione_id = a.partita_id
        LEFT JOIN partita_possessore pp ON p.id = pp.partita_id
        LEFT JOIN possessore pos ON pp.possessore_id = pos.id
        WHERE a.livello = -(i-1)
        GROUP BY p.id, p.comune_nome, p.numero_partita, p.tipo, v.data_variazione;
    END LOOP;
    
    -- Ricorsione manuale per i successori (livelli positivi)
    FOR i IN 1..5 LOOP
        -- Aggiungi i successori al livello corrente
        INSERT INTO temp_albero
        SELECT 
            i AS livello,
            'successore'::VARCHAR,
            p.id,
            p.comune_nome,
            p.numero_partita,
            p.tipo,
            string_agg(DISTINCT pos.nome_completo, ', '),
            v.data_variazione
        FROM partita p
        JOIN variazione v ON p.id = v.partita_destinazione_id
        JOIN temp_albero a ON v.partita_origine_id = a.partita_id
        LEFT JOIN partita_possessore pp ON p.id = pp.partita_id
        LEFT JOIN possessore pos ON pp.possessore_id = pos.id
        WHERE a.livello = (i-1)
        GROUP BY p.id, p.comune_nome, p.numero_partita, p.tipo, v.data_variazione;
    END LOOP;
    
    -- Restituisci i risultati dalla tabella temporanea
    RETURN QUERY
    SELECT * FROM temp_albero
    ORDER BY livello, comune_nome, numero_partita;
END;
$$ LANGUAGE plpgsql;

-- 10. Funzione per calcolare le statistiche catastali per periodo
CREATE OR REPLACE FUNCTION statistiche_catastali_periodo(
    p_comune VARCHAR DEFAULT NULL,
    p_anno_inizio INTEGER DEFAULT 1900,
    p_anno_fine INTEGER DEFAULT EXTRACT(YEAR FROM CURRENT_DATE)::INTEGER
)
RETURNS TABLE (
    anno INTEGER,
    comune_nome VARCHAR,
    nuove_partite BIGINT,
    partite_chiuse BIGINT,
    totale_partite_attive BIGINT,
    variazioni BIGINT,
    immobili_registrati BIGINT
) AS $$
BEGIN
    RETURN QUERY
    WITH anni AS (
        SELECT generate_series(p_anno_inizio, p_anno_fine) AS anno
    ),
    comuni AS (
        SELECT nome FROM comune
        WHERE p_comune IS NULL OR nome = p_comune
    ),
    anni_comuni AS (
        SELECT a.anno, c.nome AS comune_nome
        FROM anni a
        CROSS JOIN comuni c
    ),
    statistiche AS (
        SELECT 
            EXTRACT(YEAR FROM p.data_impianto)::INTEGER AS anno,
            p.comune_nome,
            COUNT(*) AS nuove_partite,
            0 AS partite_chiuse
        FROM partita p
        WHERE EXTRACT(YEAR FROM p.data_impianto) BETWEEN p_anno_inizio AND p_anno_fine
        AND (p_comune IS NULL OR p.comune_nome = p_comune)
        GROUP BY EXTRACT(YEAR FROM p.data_impianto), p.comune_nome
        
        UNION ALL
        
        SELECT 
            EXTRACT(YEAR FROM p.data_chiusura)::INTEGER AS anno,
            p.comune_nome,
            0 AS nuove_partite,
            COUNT(*) AS partite_chiuse
        FROM partita p
        WHERE p.data_chiusura IS NOT NULL
        AND EXTRACT(YEAR FROM p.data_chiusura) BETWEEN p_anno_inizio AND p_anno_fine
        AND (p_comune IS NULL OR p.comune_nome = p_comune)
        GROUP BY EXTRACT(YEAR FROM p.data_chiusura), p.comune_nome
    ),
    variazioni_anno AS (
        SELECT 
            EXTRACT(YEAR FROM v.data_variazione)::INTEGER AS anno,
            p.comune_nome,
            COUNT(*) AS variazioni
        FROM variazione v
        JOIN partita p ON v.partita_origine_id = p.id
        WHERE EXTRACT(YEAR FROM v.data_variazione) BETWEEN p_anno_inizio AND p_anno_fine
        AND (p_comune IS NULL OR p.comune_nome = p_comune)
        GROUP BY EXTRACT(YEAR FROM v.data_variazione), p.comune_nome
    ),
    immobili_anno AS (
        SELECT 
            EXTRACT(YEAR FROM i.data_creazione)::INTEGER AS anno,
            p.comune_nome,
            COUNT(*) AS immobili_registrati
        FROM immobile i
        JOIN partita p ON i.partita_id = p.id
        WHERE EXTRACT(YEAR FROM i.data_creazione) BETWEEN p_anno_inizio AND p_anno_fine
        AND (p_comune IS NULL OR p.comune_nome = p_comune)
        GROUP BY EXTRACT(YEAR FROM i.data_creazione), p.comune_nome
    ),
    partite_cumulative AS (
        SELECT
            ac.anno,
            ac.comune_nome,
            COALESCE(SUM(s.nuove_partite) FILTER (WHERE s.anno = ac.anno), 0) AS nuove_partite,
            COALESCE(SUM(s.partite_chiuse) FILTER (WHERE s.anno = ac.anno), 0) AS partite_chiuse,
            COALESCE(SUM(v.variazioni), 0) AS variazioni,
            COALESCE(SUM(i.immobili_registrati), 0) AS immobili_registrati,
            SUM(s.nuove_partite) FILTER (WHERE s.anno <= ac.anno) OVER (PARTITION BY ac.comune_nome ORDER BY ac.anno) -
            SUM(s.partite_chiuse) FILTER (WHERE s.anno <= ac.anno) OVER (PARTITION BY ac.comune_nome ORDER BY ac.anno) AS totale_partite_attive
        FROM anni_comuni ac
        LEFT JOIN statistiche s ON ac.anno = s.anno AND ac.comune_nome = s.comune_nome
        LEFT JOIN variazioni_anno v ON ac.anno = v.anno AND ac.comune_nome = v.comune_nome
        LEFT JOIN immobili_anno i ON ac.anno = i.anno AND ac.comune_nome = i.comune_nome
        GROUP BY ac.anno, ac.comune_nome
    )
    SELECT 
        pc.anno,
        pc.comune_nome,
        pc.nuove_partite,
        pc.partite_chiuse,
        CASE WHEN pc.totale_partite_attive < 0 THEN 0 ELSE pc.totale_partite_attive END AS totale_partite_attive,
        pc.variazioni,
        pc.immobili_registrati
    FROM partite_cumulative pc
    ORDER BY pc.anno, pc.comune_nome;
END;
$$ LANGUAGE plpgsql;