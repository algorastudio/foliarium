-- File: 17_funzione_ricerca_immobili.sql
-- Oggetto: Definizione funzione per ricerca avanzata immobili
-- Versione: 2.0
-- Data: 24/05/2025
-- File: 17_funzione_ricerca_immobili.sql (Versione Estesa Proposta)
SET search_path TO catasto, public;

CREATE OR REPLACE FUNCTION catasto.ricerca_avanzata_immobili(
    p_comune_id INTEGER DEFAULT NULL,                   -- ID del comune (o NULL per tutti)
    p_localita_id INTEGER DEFAULT NULL,                 -- ID della località (o NULL per tutte nel comune o globalmente)
    p_natura_search TEXT DEFAULT NULL,                  -- Natura immobile (ricerca parziale ILIKE)
    p_classificazione_search TEXT DEFAULT NULL,         -- Classificazione (ricerca parziale ILIKE)
    p_consistenza_search TEXT DEFAULT NULL,             -- Ricerca testuale in consistenza (es. 'mq', 'are', 'vani')
    p_piani_min INTEGER DEFAULT NULL,
    p_piani_max INTEGER DEFAULT NULL,
    p_vani_min INTEGER DEFAULT NULL,
    p_vani_max INTEGER DEFAULT NULL,
    p_nome_possessore_search TEXT DEFAULT NULL,         -- Nome possessore (ricerca parziale ILIKE)
    p_data_inizio_possesso_search DATE DEFAULT NULL,    -- Non ancora usato nella GUI, ma previsto
    p_data_fine_possesso_search DATE DEFAULT NULL       -- Non ancora usato nella GUI, ma previsto
)
RETURNS TABLE (
    id_immobile INTEGER,
    numero_partita INTEGER,
    comune_nome VARCHAR,
    localita_nome VARCHAR,
    civico INTEGER,         -- Aggiunto per completezza località
    localita_tipo VARCHAR,  -- Aggiunto per completezza località
    natura VARCHAR,
    classificazione VARCHAR,
    consistenza VARCHAR,
    numero_piani INTEGER,
    numero_vani INTEGER,
    possessori_attuali TEXT -- Aggregazione dei nomi possessori attuali sulla partita
) AS $$
BEGIN
    RETURN QUERY
    SELECT DISTINCT
        i.id AS id_immobile,
        p.numero_partita,
        c.nome AS comune_nome,
        l.nome AS localita_nome,
        l.civico AS civico,
        l.tipo AS localita_tipo,
        i.natura,
        i.classificazione,
        i.consistenza,
        i.numero_piani,
        i.numero_vani,
        (SELECT string_agg(DISTINCT pos_agg.nome_completo, ', ')
         FROM catasto.partita_possessore pp_agg
         JOIN catasto.possessore pos_agg ON pp_agg.possessore_id = pos_agg.id
         WHERE pp_agg.partita_id = p.id AND pos_agg.attivo = TRUE) AS possessori_attuali -- Considera solo possessori attivi
    FROM
        catasto.immobile i
    JOIN
        catasto.partita p ON i.partita_id = p.id
    JOIN
        catasto.comune c ON p.comune_id = c.id
    JOIN
        catasto.localita l ON i.localita_id = l.id
    -- LEFT JOIN opzionale per il filtro possessore (se p_nome_possessore_search è fornito)
    LEFT JOIN
        catasto.partita_possessore pp_filter ON p.id = pp_filter.partita_id AND p_nome_possessore_search IS NOT NULL
    LEFT JOIN
        catasto.possessore pos_filter ON pp_filter.possessore_id = pos_filter.id AND pos_filter.nome_completo ILIKE ('%' || p_nome_possessore_search || '%')
    WHERE
        (p_comune_id IS NULL OR p.comune_id = p_comune_id)
    AND (p_localita_id IS NULL OR i.localita_id = p_localita_id) -- Filtro per ID località
    AND (p_natura_search IS NULL OR i.natura ILIKE ('%' || p_natura_search || '%'))
    AND (p_classificazione_search IS NULL OR i.classificazione ILIKE ('%' || p_classificazione_search || '%'))
    AND (p_consistenza_search IS NULL OR i.consistenza ILIKE ('%' || p_consistenza_search || '%'))
    AND (p_piani_min IS NULL OR i.numero_piani >= p_piani_min)
    AND (p_piani_max IS NULL OR i.numero_piani <= p_piani_max)
    AND (p_vani_min IS NULL OR i.numero_vani >= p_vani_min)
    AND (p_vani_max IS NULL OR i.numero_vani <= p_vani_max)
    AND (p_nome_possessore_search IS NULL OR pos_filter.id IS NOT NULL) -- Se cerco un possessore, deve esistere il join
    -- AND (p_data_inizio_possesso_search IS NULL OR ...) -- Logica per date possesso da aggiungere se necessaria
    -- AND (p_data_fine_possesso_search IS NULL OR ...)
    ORDER BY
        c.nome, p.numero_partita, i.natura;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION catasto.ricerca_avanzata_immobili(INTEGER, INTEGER, TEXT, TEXT, TEXT, INTEGER, INTEGER, INTEGER, INTEGER, TEXT, DATE, DATE) IS
'Ricerca immobili avanzata con criteri estesi (ID comune, ID località, natura, classificazione, consistenza, piani, vani, nome possessore, date possesso).';