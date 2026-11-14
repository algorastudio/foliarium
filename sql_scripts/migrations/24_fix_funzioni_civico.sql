-- sql_scripts/migrations/24_fix_funzioni_civico.sql
--
-- Migrazione idempotente: sostituisce le tre funzioni che leggevano colonne
-- di `localita` che dalla v1.7.0 non esistono piu'.
--
--   localita.civico   -> immobile.numero_civico
--   localita.tipo_id  -> localita.tipologia_stradale
--
-- Le funzioni fallivano a ogni chiamata con «column l.civico does not exist»
-- (o «l.tipo_id»), anche su una partita senza immobili:
--
--   esporta_partita_json       le esportazioni di una partita dalla GUI
--                              (JSON, CSV, PDF)
--   genera_report_proprieta    la pagina Reportistica
--   ricerca_avanzata_immobili  non usata dalla GUI, che ha una query propria
--
-- Chi ne ha bisogno. Ogni database creato prima di questa correzione, con
-- gli script canonici (setup_database.py, docker/postgres/init.sh) o con
-- quelli numerati storici (setup_database.bat, devcontainer). I database
-- creati dall'installer Windows si riparano anche reinstallando la nuova
-- versione: il setup riapplica gli script delle funzioni sopra il database
-- esistente.
--
-- Le definizioni sono copiate da functions/02_crud.sql, functions/05_reporting.sql
-- e functions/04_search.sql: dopo la migrazione il database e' identico a uno
-- creato ora. tests/integration/test_funzioni_civico.py lo verifica.
-- Sostituisce, per genera_report_proprieta, la migrazione 20, che corregge il
-- civico ma cambia anche altre parti del report.
--
-- Esecuzione:
--   psql -U postgres -d catasto_storico -f 24_fix_funzioni_civico.sql
--
-- Sicurezza: solo CREATE OR REPLACE FUNCTION, con firma e tipo restituito
-- invariati. Nessun dato viene toccato.

SET search_path TO catasto, public;

-- ---------------------------------------------------------------------------
-- Da functions/02_crud.sql
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION catasto.esporta_partita_json(p_partita_id integer)
 RETURNS jsonb
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_partita_details jsonb;
    v_possessori jsonb;
    v_immobili jsonb;
    v_variazioni jsonb;
BEGIN
    -- Dettagli Partita (con suffisso)
    SELECT to_jsonb(p.*) || jsonb_build_object('comune_nome', c.nome)
    INTO v_partita_details
    FROM catasto.partita p
    JOIN catasto.comune c ON p.comune_id = c.id
    WHERE p.id = p_partita_id;

    -- Possessori
    SELECT jsonb_agg(to_jsonb(poss_data))
    INTO v_possessori
    FROM (
        SELECT pos.id, pos.nome_completo, pp.titolo, pp.quota
        FROM catasto.possessore pos
        JOIN catasto.partita_possessore pp ON pos.id = pp.possessore_id
        WHERE pp.partita_id = p_partita_id
        ORDER BY pos.nome_completo
    ) AS poss_data;

    -- Immobili. Dalla v1.7.0 il civico sta in immobile.numero_civico, non in
    -- localita: la chiave del JSON resta «civico».
    SELECT jsonb_agg(to_jsonb(imm_data))
    INTO v_immobili
    FROM (
        SELECT i.id, i.natura, l.nome as localita_nome, i.classificazione, i.consistenza,
               i.numero_civico AS civico
        FROM catasto.immobile i
        JOIN catasto.localita l ON i.localita_id = l.id
        WHERE i.partita_id = p_partita_id
    ) AS imm_data;

    -- Variazioni
    SELECT jsonb_agg(to_jsonb(var_data))
    INTO v_variazioni
    FROM (
        SELECT v.*, con.tipo as contratto_tipo, con.data_contratto, con.notaio
        FROM catasto.variazione v
        LEFT JOIN catasto.contratto con ON v.id = con.variazione_id
        WHERE v.partita_origine_id = p_partita_id OR v.partita_destinazione_id = p_partita_id
        ORDER BY v.data_variazione
    ) AS var_data;

    -- Costruzione JSON finale
    RETURN jsonb_build_object(
        'partita', COALESCE(v_partita_details, '{}'::jsonb),
        'possessori', COALESCE(v_possessori, '[]'::jsonb),
        'immobili', COALESCE(v_immobili, '[]'::jsonb),
        'variazioni', COALESCE(v_variazioni, '[]'::jsonb)
    );
END;
$function$;

-- ---------------------------------------------------------------------------
-- Da functions/05_reporting.sql
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION genera_report_proprieta(p_partita_id INTEGER)
RETURNS TEXT AS $$
DECLARE
    v_partita partita%ROWTYPE;
    v_comune_nome comune.nome%TYPE;
    v_report TEXT := '';
    v_immobile RECORD;
    v_record RECORD;
BEGIN
    -- Recupera dati partita base
    SELECT * INTO v_partita FROM partita WHERE id = p_partita_id;
    IF NOT FOUND THEN RETURN 'Partita con ID ' || p_partita_id || ' non trovata'; END IF;
    -- Recupera nome comune separatamente
    SELECT nome INTO v_comune_nome FROM comune WHERE id = v_partita.comune_id;

    -- Intestazione (invariata)
    v_report := '============================================================' || E'\n';
    v_report := v_report || '                REPORT PROPRIETA IMMOBILIARE' || E'\n';
    v_report := v_report || '                     CATASTO STORICO ANNI ''50' || E'\n';
    v_report := v_report || '============================================================' || E'\n\n';

    -- Dati generali (usa v_comune_nome)
    v_report := v_report || 'COMUNE: ' || v_comune_nome || E'\n';
    v_report := v_report || 'PARTITA N.: ' || v_partita.numero_partita || E'\n';
    v_report := v_report || 'TIPO: ' || v_partita.tipo || E'\n';
    v_report := v_report || 'DATA IMPIANTO: ' || COALESCE(v_partita.data_impianto::TEXT, 'N/D') || E'\n';
    v_report := v_report || 'STATO: ' || v_partita.stato || E'\n';
    IF v_partita.data_chiusura IS NOT NULL THEN v_report := v_report || 'DATA CHIUSURA: ' || v_partita.data_chiusura::TEXT || E'\n'; END IF;
    IF v_partita.numero_provenienza IS NOT NULL THEN v_report := v_report || 'PROVENIENZA: Partita n. ' || v_partita.numero_provenienza || E'\n'; END IF;
    v_report := v_report || E'\n';

    -- Possessori (invariato)
    v_report := v_report || '-------------------- INTESTATARI --------------------' || E'\n';
    FOR v_record IN SELECT pos.nome_completo, pp.titolo, pp.quota FROM partita_possessore pp JOIN possessore pos ON pp.possessore_id = pos.id WHERE pp.partita_id = p_partita_id ORDER BY pos.nome_completo LOOP
        v_report := v_report || '- ' || v_record.nome_completo;
        IF v_record.titolo = 'comproprieta' AND v_record.quota IS NOT NULL THEN v_report := v_report || ' (quota: ' || v_record.quota || ')'; END IF;
        v_report := v_report || E'\n';
    END LOOP;
    v_report := v_report || E'\n';

    -- Immobili. Dalla v1.7.0 il civico sta in immobile.numero_civico, non in localita.
    v_report := v_report || '-------------------- IMMOBILI --------------------' || E'\n';
    FOR v_immobile IN SELECT i.id, i.natura, i.numero_piani, i.numero_vani, i.consistenza, i.classificazione, l.tipologia_stradale AS tipo_localita, l.nome AS nome_localita, i.numero_civico AS civico FROM immobile i JOIN localita l ON i.localita_id = l.id WHERE i.partita_id = p_partita_id ORDER BY l.nome, i.natura LOOP
        v_report := v_report || 'Immobile ID: ' || v_immobile.id || E'\n';
        v_report := v_report || '  Natura: ' || COALESCE(v_immobile.natura, 'N/D') || E'\n';
        v_report := v_report || '  Localita: ' || COALESCE(v_immobile.nome_localita, 'N/D');
        IF v_immobile.civico IS NOT NULL AND v_immobile.civico <> '' THEN v_report := v_report || ', ' || v_immobile.civico; END IF;
        v_report := v_report || ' (' || COALESCE(v_immobile.tipo_localita, 'N/D') || ')' || E'\n';
        IF v_immobile.numero_piani IS NOT NULL THEN v_report := v_report || '  Piani: ' || v_immobile.numero_piani || E'\n'; END IF;
        IF v_immobile.numero_vani IS NOT NULL THEN v_report := v_report || '  Vani: ' || v_immobile.numero_vani || E'\n'; END IF;
        IF v_immobile.consistenza IS NOT NULL THEN v_report := v_report || '  Consistenza: ' || v_immobile.consistenza || E'\n'; END IF;
        IF v_immobile.classificazione IS NOT NULL THEN v_report := v_report || '  Classificazione: ' || v_immobile.classificazione || E'\n'; END IF;
        v_report := v_report || E'\n';
    END LOOP;

    -- Variazioni (invariato nella logica del loop)
    v_report := v_report || '-------------------- VARIAZIONI --------------------' || E'\n';
    FOR v_record IN SELECT v.tipo, v.data_variazione, v.numero_riferimento, p2.numero_partita AS partita_destinazione_numero, c2.nome AS partita_destinazione_comune, con.tipo AS tipo_contratto, con.data_contratto, con.notaio, con.repertorio FROM variazione v LEFT JOIN partita p2 ON v.partita_destinazione_id = p2.id LEFT JOIN comune c2 ON p2.comune_id = c2.id LEFT JOIN contratto con ON v.id = con.variazione_id WHERE v.partita_origine_id = p_partita_id ORDER BY v.data_variazione DESC LOOP
        v_report := v_report || 'Variazione: ' || COALESCE(v_record.tipo, 'N/D') || ' del ' || COALESCE(v_record.data_variazione::TEXT, 'N/D') || E'\n';
        IF v_record.partita_destinazione_numero IS NOT NULL THEN
            v_report := v_report || '  Nuova partita: ' || v_record.partita_destinazione_numero;
            v_report := v_report || ' (Comune: ' || COALESCE(v_record.partita_destinazione_comune, 'N/D') || ')';
            v_report := v_report || E'\n'; END IF;
        IF v_record.tipo_contratto IS NOT NULL THEN
            v_report := v_report || '  Contratto: ' || v_record.tipo_contratto || ' del ' || COALESCE(v_record.data_contratto::TEXT, 'N/D') || E'\n';
            IF v_record.notaio IS NOT NULL THEN v_report := v_report || '  Notaio: ' || v_record.notaio || E'\n'; END IF;
            IF v_record.repertorio IS NOT NULL THEN v_report := v_report || '  Repertorio: ' || v_record.repertorio || E'\n'; END IF;
        END IF;
        v_report := v_report || E'\n';
    END LOOP;

    -- Piè di pagina (invariato)
    v_report := v_report || '============================================================' || E'\n';
    v_report := v_report || 'Report generato il: ' || CURRENT_DATE || E'\n';
    v_report := v_report || 'Il presente report ha valore puramente storico e documentale.' || E'\n';
    v_report := v_report || '============================================================' || E'\n';
    RETURN v_report;
END;
$$ LANGUAGE plpgsql;

-- ---------------------------------------------------------------------------
-- Da functions/04_search.sql
-- ---------------------------------------------------------------------------
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
        -- Dalla v1.7.0 il civico sta in immobile e il tipo di localita' in
        -- localita.tipologia_stradale (le colonne civico e tipo_id non esistono).
        i.numero_civico AS civico,
        l.tipologia_stradale AS localita_tipo,
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
