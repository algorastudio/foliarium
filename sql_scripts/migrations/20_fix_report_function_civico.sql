-- sql_scripts/migrations/20_fix_report_function_civico.sql
--
-- Aggiorna la funzione catasto.genera_report_proprieta(p_partita_id) per
-- adeguarla allo schema v1.6.1: la colonna `localita.civico` e' stata
-- rimossa nel rebrand (il civico ora e' incorporato in `localita.nome`,
-- es. "Via Roma 17").
--
-- Senza questa migration `genera_report_proprieta(...)` solleva
-- `column l.civico does not exist` quando viene chiamata (lo abbiamo
-- visto fallire test_golden_path su CI).
--
-- Idempotente: CREATE OR REPLACE FUNCTION sovrascrive la definizione
-- precedente.

SET search_path TO catasto, public;

CREATE OR REPLACE FUNCTION genera_report_proprieta(p_partita_id INTEGER)
RETURNS TEXT AS $$
DECLARE
    v_partita partita%ROWTYPE;
    v_comune_nome comune.nome%TYPE;
    v_report TEXT := '';
    v_record RECORD;
    v_immobile RECORD;
BEGIN
    SELECT * INTO v_partita FROM partita WHERE id = p_partita_id;
    IF NOT FOUND THEN
        RETURN 'Partita con ID ' || p_partita_id || ' non trovata';
    END IF;
    SELECT nome INTO v_comune_nome FROM comune WHERE id = v_partita.comune_id;

    -- Intestazione
    v_report := '============================================================' || E'\n';
    v_report := v_report || '                REPORT PROPRIETA IMMOBILIARE' || E'\n';
    v_report := v_report || '                     CATASTO STORICO ANNI ''50' || E'\n';
    v_report := v_report || '============================================================' || E'\n\n';

    -- Dati generali
    v_report := v_report || 'COMUNE: ' || v_comune_nome || E'\n';
    v_report := v_report || 'PARTITA N.: ' || v_partita.numero_partita || E'\n';
    v_report := v_report || 'TIPO: ' || v_partita.tipo || E'\n';
    v_report := v_report || 'DATA IMPIANTO: ' || COALESCE(v_partita.data_impianto::TEXT, 'N/D') || E'\n';
    v_report := v_report || 'STATO: ' || v_partita.stato || E'\n';
    IF v_partita.data_chiusura IS NOT NULL THEN
        v_report := v_report || 'DATA CHIUSURA: ' || v_partita.data_chiusura::TEXT || E'\n';
    END IF;
    IF v_partita.numero_provenienza IS NOT NULL THEN
        v_report := v_report || 'PROVENIENZA: Partita n. ' || v_partita.numero_provenienza || E'\n';
    END IF;
    v_report := v_report || E'\n';

    -- Possessori
    v_report := v_report || '-------------------- INTESTATARI --------------------' || E'\n';
    FOR v_record IN
        SELECT pos.nome_completo, pp.titolo, pp.quota
        FROM partita_possessore pp
        JOIN possessore pos ON pp.possessore_id = pos.id
        WHERE pp.partita_id = p_partita_id
        ORDER BY pos.nome_completo
    LOOP
        v_report := v_report || '- ' || v_record.nome_completo;
        IF v_record.titolo = 'comproprieta' AND v_record.quota IS NOT NULL THEN
            v_report := v_report || ' (quota: ' || v_record.quota || ')';
        END IF;
        v_report := v_report || E'\n';
    END LOOP;
    v_report := v_report || E'\n';

    -- Immobili — schema v1.6.1: NIENTE l.civico (incorporato in l.nome)
    v_report := v_report || '-------------------- IMMOBILI --------------------' || E'\n';
    FOR v_immobile IN
        SELECT i.id,
               i.natura,
               i.numero_piani,
               i.numero_vani,
               i.consistenza,
               i.classificazione,
               i.numero_civico AS civico_immobile,
               l.tipologia_stradale AS tipo_localita,
               l.nome AS nome_localita
        FROM immobile i
        JOIN localita l ON i.localita_id = l.id
        WHERE i.partita_id = p_partita_id
        ORDER BY l.nome, i.natura
    LOOP
        v_report := v_report || 'Immobile ID: ' || v_immobile.id || E'\n';
        v_report := v_report || '  Natura: ' || COALESCE(v_immobile.natura, 'N/D') || E'\n';
        v_report := v_report || '  Localita: ' || COALESCE(v_immobile.nome_localita, 'N/D');
        -- Nel nuovo schema il civico, se presente, e' su immobile.numero_civico
        IF v_immobile.civico_immobile IS NOT NULL AND v_immobile.civico_immobile != '' THEN
            v_report := v_report || ', ' || v_immobile.civico_immobile;
        END IF;
        v_report := v_report || ' (' || COALESCE(v_immobile.tipo_localita, 'N/D') || ')' || E'\n';
        IF v_immobile.numero_piani IS NOT NULL THEN
            v_report := v_report || '  Piani: ' || v_immobile.numero_piani || E'\n';
        END IF;
        IF v_immobile.numero_vani IS NOT NULL THEN
            v_report := v_report || '  Vani: ' || v_immobile.numero_vani || E'\n';
        END IF;
        IF v_immobile.consistenza IS NOT NULL THEN
            v_report := v_report || '  Consistenza: ' || v_immobile.consistenza || E'\n';
        END IF;
        IF v_immobile.classificazione IS NOT NULL THEN
            v_report := v_report || '  Classificazione: ' || v_immobile.classificazione || E'\n';
        END IF;
        v_report := v_report || E'\n';
    END LOOP;

    -- Variazioni
    v_report := v_report || '-------------------- VARIAZIONI --------------------' || E'\n';
    FOR v_record IN
        SELECT v.tipo, v.data_variazione, v.numero_riferimento,
               p2.numero_partita AS partita_destinazione_numero,
               c2.nome AS partita_destinazione_comune,
               con.tipo AS tipo_contratto, con.data_contratto, con.notaio, con.repertorio
        FROM variazione v
        LEFT JOIN partita p2 ON v.partita_destinazione_id = p2.id
        LEFT JOIN comune c2 ON p2.comune_id = c2.id
        LEFT JOIN contratto con ON v.id = con.variazione_id
        WHERE v.partita_origine_id = p_partita_id
        ORDER BY v.data_variazione DESC
    LOOP
        v_report := v_report || 'Variazione: ' || COALESCE(v_record.tipo, 'N/D')
                             || ' del ' || COALESCE(v_record.data_variazione::TEXT, 'N/D') || E'\n';
        IF v_record.partita_destinazione_numero IS NOT NULL THEN
            v_report := v_report || '  Nuova partita: ' || v_record.partita_destinazione_numero;
            IF v_record.partita_destinazione_comune IS NOT NULL THEN
                v_report := v_report || ' (' || v_record.partita_destinazione_comune || ')';
            END IF;
            v_report := v_report || E'\n';
        END IF;
        IF v_record.tipo_contratto IS NOT NULL THEN
            v_report := v_report || '  Contratto: ' || v_record.tipo_contratto
                                 || ' del ' || COALESCE(v_record.data_contratto::TEXT, 'N/D') || E'\n';
            IF v_record.notaio IS NOT NULL THEN
                v_report := v_report || '  Notaio: ' || v_record.notaio || E'\n';
            END IF;
            IF v_record.repertorio IS NOT NULL THEN
                v_report := v_report || '  Repertorio: ' || v_record.repertorio || E'\n';
            END IF;
        END IF;
        v_report := v_report || E'\n';
    END LOOP;

    RETURN v_report;
END;
$$ LANGUAGE plpgsql;

SELECT 'Funzione catasto.genera_report_proprieta aggiornata (schema v1.6.1).' AS stato;
