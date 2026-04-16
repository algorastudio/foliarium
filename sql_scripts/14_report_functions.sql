-- File: 14_report_functions.sql (Versione v1.3 - Corretto errore SELECT INTO)
-- Oggetto: Funzioni di reportistica per Catasto Storico
-- Data: 30/04/2025

SET search_path TO catasto, public;

-- ========================================================================
-- Funzione: genera_report_genealogico
-- ========================================================================
CREATE OR REPLACE FUNCTION genera_report_genealogico(p_partita_id INTEGER)
RETURNS TEXT AS $$
DECLARE
    v_partita partita%ROWTYPE; -- Manteniamo ROWTYPE per dati base partita
    v_comune_nome_partita comune.nome%TYPE; -- Variabile separata per nome comune
    v_report TEXT := '';
    v_record RECORD;
    v_predecessori_trovati BOOLEAN := FALSE;
    v_successori_trovati BOOLEAN := FALSE;
BEGIN
    -- Recupera dati partita base
    SELECT * INTO v_partita FROM partita WHERE id = p_partita_id;
    IF NOT FOUND THEN RETURN 'Partita con ID ' || p_partita_id || ' non trovata'; END IF;
    -- Recupera nome comune separatamente
    SELECT nome INTO v_comune_nome_partita FROM comune WHERE id = v_partita.comune_id;

    -- Intestazione report (invariata)
    v_report := '============================================================' || E'\n';
    v_report := v_report || '              REPORT GENEALOGICO DELLA PROPRIETA' || E'\n';
    v_report := v_report || '                   CATASTO STORICO ANNI ''50' || E'\n';
    v_report := v_report || '============================================================' || E'\n\n';

    -- Dati generali (usa v_comune_nome_partita)
    v_report := v_report || 'COMUNE: ' || v_comune_nome_partita || E'\n';
    v_report := v_report || 'PARTITA N.: ' || v_partita.numero_partita || E'\n';
    v_report := v_report || 'TIPO: ' || v_partita.tipo || E'\n';
    v_report := v_report || 'DATA IMPIANTO: ' || v_partita.data_impianto::TEXT || E'\n';
    v_report := v_report || 'STATO: ' || v_partita.stato || E'\n';
    IF v_partita.data_chiusura IS NOT NULL THEN
        v_report := v_report || 'DATA CHIUSURA: ' || v_partita.data_chiusura::TEXT || E'\n';
    END IF;
    v_report := v_report || E'\n';

    -- Possessori (invariato)
    v_report := v_report || '-------------------- INTESTATARI --------------------' || E'\n';
    FOR v_record IN
        SELECT pos.nome_completo, pp.titolo, pp.quota
        FROM partita_possessore pp JOIN possessore pos ON pp.possessore_id = pos.id
        WHERE pp.partita_id = p_partita_id ORDER BY pos.nome_completo
    LOOP
        v_report := v_report || '- ' || v_record.nome_completo;
        IF v_record.titolo = 'comproprieta' AND v_record.quota IS NOT NULL THEN
            v_report := v_report || ' (quota: ' || v_record.quota || ')'; END IF;
        v_report := v_report || E'\n';
    END LOOP;
    v_report := v_report || E'\n';

    -- Predecessori (invariato nella logica del loop)
    v_report := v_report || '-------------------- PREDECESSORI --------------------' || E'\n';
    FOR v_record IN
        SELECT p.id AS partita_id, c.nome AS comune_nome, p.numero_partita, p.data_impianto, p.data_chiusura,
               string_agg(DISTINCT pos.nome_completo, ', ') AS possessori, v.tipo AS tipo_variazione, v.data_variazione
        FROM variazione v JOIN partita p ON v.partita_origine_id = p.id JOIN comune c ON p.comune_id = c.id
        LEFT JOIN partita_possessore pp ON p.id = pp.partita_id LEFT JOIN possessore pos ON pp.possessore_id = pos.id
        WHERE v.partita_destinazione_id = p_partita_id
        GROUP BY p.id, c.nome, p.numero_partita, p.data_impianto, p.data_chiusura, v.tipo, v.data_variazione
        ORDER BY v.data_variazione DESC
    LOOP
        v_predecessori_trovati := TRUE;
        v_report := v_report || 'Partita n. ' || v_record.numero_partita || ' (' || v_record.comune_nome || ')' || E'\n';
        v_report := v_report || '  Periodo: ' || COALESCE(v_record.data_impianto::TEXT, 'N/D') || ' - ';
        IF v_record.data_chiusura IS NOT NULL THEN v_report := v_report || v_record.data_chiusura::TEXT; ELSE v_report := v_report || 'attiva'; END IF;
        v_report := v_report || E'\n';
        v_report := v_report || '  Intestatari: ' || COALESCE(v_record.possessori, 'N/D') || E'\n';
        v_report := v_report || '  Variazione Origine: ' || v_record.tipo_variazione || ' del ' || v_record.data_variazione::TEXT || E'\n';
        v_report := v_report || E'\n';
    END LOOP;
     IF NOT v_predecessori_trovati THEN
         IF v_partita.numero_provenienza IS NOT NULL THEN
              v_report := v_report || 'Nessun predecessore diretto trovato tramite variazioni (Provenienza indicata: Partita N.' || v_partita.numero_provenienza || ').' || E'\n\n';
         ELSE v_report := v_report || 'Nessun predecessore trovato. Partita originale o dati di variazione mancanti.' || E'\n\n'; END IF;
    END IF;

    -- Successori (invariato nella logica del loop)
    v_report := v_report || '-------------------- SUCCESSORI --------------------' || E'\n';
    FOR v_record IN
        SELECT p.id AS partita_id, c.nome AS comune_nome, p.numero_partita, p.data_impianto, p.data_chiusura,
               string_agg(DISTINCT pos.nome_completo, ', ') AS possessori, v.tipo AS tipo_variazione, v.data_variazione
        FROM variazione v JOIN partita p ON v.partita_destinazione_id = p.id JOIN comune c ON p.comune_id = c.id
        LEFT JOIN partita_possessore pp ON p.id = pp.partita_id LEFT JOIN possessore pos ON pp.possessore_id = pos.id
        WHERE v.partita_origine_id = p_partita_id
        GROUP BY p.id, c.nome, p.numero_partita, p.data_impianto, p.data_chiusura, v.tipo, v.data_variazione
        ORDER BY v.data_variazione
    LOOP
        v_successori_trovati := TRUE;
        v_report := v_report || 'Partita n. ' || v_record.numero_partita || ' (' || v_record.comune_nome || ')' || E'\n';
        v_report := v_report || '  Periodo: ' || COALESCE(v_record.data_impianto::TEXT, 'N/D') || ' - ';
        IF v_record.data_chiusura IS NOT NULL THEN v_report := v_report || v_record.data_chiusura::TEXT; ELSE v_report := v_report || 'attiva'; END IF;
        v_report := v_report || E'\n';
        v_report := v_report || '  Intestatari: ' || COALESCE(v_record.possessori, 'N/D') || E'\n';
        v_report := v_report || '  Variazione Destinazione: ' || v_record.tipo_variazione || ' del ' || v_record.data_variazione::TEXT || E'\n';
        v_report := v_report || E'\n';
    END LOOP;
     IF NOT v_successori_trovati THEN
        IF v_partita.stato = 'attiva' THEN v_report := v_report || 'Nessun successore trovato. La partita e'' ancora attiva.' || E'\n\n';
        ELSE v_report := v_report || 'Nessun successore trovato nonostante la partita sia chiusa (Dati di variazione mancanti?).' || E'\n\n'; END IF;
    END IF;

    -- Piè di pagina (invariato)
    v_report := v_report || '============================================================' || E'\n';
    v_report := v_report || 'Report generato il: ' || CURRENT_DATE || E'\n';
    v_report := v_report || 'Il presente report ha valore puramente storico e documentale.' || E'\n';
    v_report := v_report || '============================================================' || E'\n';
    RETURN v_report;
END;
$$ LANGUAGE plpgsql;

-- ========================================================================
-- Funzione: genera_report_proprieta
-- ========================================================================
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

    -- Immobili (invariato)
    v_report := v_report || '-------------------- IMMOBILI --------------------' || E'\n';
    FOR v_immobile IN SELECT i.id, i.natura, i.numero_piani, i.numero_vani, i.consistenza, i.classificazione, l.tipologia_stradale AS tipo_localita, l.nome AS nome_localita, l.civico FROM immobile i JOIN localita l ON i.localita_id = l.id WHERE i.partita_id = p_partita_id ORDER BY l.nome, i.natura LOOP
        v_report := v_report || 'Immobile ID: ' || v_immobile.id || E'\n';
        v_report := v_report || '  Natura: ' || COALESCE(v_immobile.natura, 'N/D') || E'\n';
        v_report := v_report || '  Localita: ' || COALESCE(v_immobile.nome_localita, 'N/D');
        IF v_immobile.civico IS NOT NULL THEN v_report := v_report || ', ' || v_immobile.civico; END IF;
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

-- ========================================================================
-- Funzione: genera_report_possessore
-- ========================================================================
CREATE OR REPLACE FUNCTION genera_report_possessore(p_possessore_id INTEGER)
RETURNS TEXT AS $$
DECLARE
    v_possessore possessore%ROWTYPE;
    v_comune_nome_possessore comune.nome%TYPE;
    v_report TEXT := '';
    v_record RECORD;
    v_immobile RECORD;
BEGIN
     -- Recupera dati possessore base
    SELECT * INTO v_possessore FROM possessore WHERE id = p_possessore_id;
    IF NOT FOUND THEN RETURN 'Possessore con ID ' || p_possessore_id || ' non trovato'; END IF;
    -- Recupera nome comune separatamente
    SELECT nome INTO v_comune_nome_possessore FROM comune WHERE id = v_possessore.comune_id;

    -- Intestazione (invariata)
    v_report := '============================================================' || E'\n';
    v_report := v_report || '              REPORT STORICO DEL POSSESSORE' || E'\n';
    v_report := v_report || '                CATASTO STORICO ANNI ''50' || E'\n';
    v_report := v_report || '============================================================' || E'\n\n';

    -- Dati generali (usa v_comune_nome_possessore)
    v_report := v_report || 'POSSESSORE: ' || v_possessore.nome_completo || E'\n';
    IF v_possessore.paternita IS NOT NULL THEN v_report := v_report || 'PATERNITA: ' || v_possessore.paternita || E'\n'; END IF;
    v_report := v_report || 'COMUNE: ' || v_comune_nome_possessore || E'\n';
    v_report := v_report || 'STATO: ' || CASE WHEN v_possessore.attivo THEN 'Attivo' ELSE 'Non attivo' END || E'\n\n';

    -- Partite intestate (invariato nella logica del loop)
    v_report := v_report || '-------------------- PARTITE INTESTATE --------------------' || E'\n';
    FOR v_record IN SELECT p.id AS partita_id, c.nome as comune_nome, p.numero_partita, p.tipo, p.data_impianto, p.data_chiusura, p.stato, pp.titolo, pp.quota, COUNT(i.id) AS num_immobili FROM partita p JOIN comune c ON p.comune_id = c.id JOIN partita_possessore pp ON p.id = pp.partita_id LEFT JOIN immobile i ON p.id = i.partita_id WHERE pp.possessore_id = p_possessore_id GROUP BY p.id, c.nome, p.numero_partita, p.tipo, p.data_impianto, p.data_chiusura, p.stato, pp.titolo, pp.quota ORDER BY p.data_impianto DESC LOOP
        v_report := v_report || 'Partita n. ' || v_record.numero_partita || ' (' || v_record.comune_nome || ')' || E'\n';
        v_report := v_report || '  Tipo: ' || v_record.tipo || E'\n';
        v_report := v_report || '  Periodo: ' || COALESCE(v_record.data_impianto::TEXT, 'N/D') || ' - ';
        IF v_record.data_chiusura IS NOT NULL THEN v_report := v_report || v_record.data_chiusura::TEXT; ELSE v_report := v_report || 'attiva'; END IF;
        v_report := v_report || E'\n';
        v_report := v_report || '  Stato: ' || v_record.stato || E'\n';
        v_report := v_report || '  Titolo: ' || COALESCE(v_record.titolo, 'N/D');
        IF v_record.quota IS NOT NULL THEN v_report := v_report || ' (quota: ' || v_record.quota || ')'; END IF;
        v_report := v_report || E'\n';
        v_report := v_report || '  Immobili associati: ' || v_record.num_immobili || E'\n';
        v_report := v_report || '    Immobili:' || E'\n';
        FOR v_immobile IN SELECT i.natura, l.nome AS localita_nome, l.tipologia_stradale AS tipo_localita, i.classificazione FROM immobile i JOIN localita l ON i.localita_id = l.id WHERE i.partita_id = v_record.partita_id ORDER BY l.nome, i.natura LOOP
            v_report := v_report || '      - ' || COALESCE(v_immobile.natura, 'N/D') || ' in ' || COALESCE(v_immobile.localita_nome, 'N/D');
            IF v_immobile.classificazione IS NOT NULL THEN v_report := v_report || ' (' || v_immobile.classificazione || ')'; END IF;
            v_report := v_report || E'\n';
        END LOOP;
        v_report := v_report || E'\n';
    END LOOP;

    -- Variazioni correlate (invariato nella logica del loop)
    v_report := v_report || '-------------------- VARIAZIONI CORRELATE --------------------' || E'\n';
    FOR v_record IN SELECT v.tipo AS tipo_variazione, v.data_variazione, c_orig.nome AS comune_origine, p_orig.numero_partita AS partita_origine, c_dest.nome AS comune_destinazione, p_dest.numero_partita AS partita_destinazione, con.tipo AS tipo_contratto, con.data_contratto, con.notaio, con.repertorio FROM variazione v JOIN partita p_orig ON v.partita_origine_id = p_orig.id JOIN comune c_orig ON p_orig.comune_id = c_orig.id LEFT JOIN partita p_dest ON v.partita_destinazione_id = p_dest.id LEFT JOIN comune c_dest ON p_dest.comune_id = c_dest.id LEFT JOIN contratto con ON v.id = con.variazione_id WHERE EXISTS (SELECT 1 FROM partita_possessore pp WHERE pp.partita_id = p_orig.id AND pp.possessore_id = p_possessore_id) OR EXISTS (SELECT 1 FROM partita_possessore pp WHERE pp.partita_id = p_dest.id AND pp.possessore_id = p_possessore_id) ORDER BY v.data_variazione DESC LOOP
        v_report := v_report || 'Variazione: ' || COALESCE(v_record.tipo_variazione, 'N/D') || ' del ' || COALESCE(v_record.data_variazione::TEXT, 'N/D') || E'\n';
        v_report := v_report || '  Da: Partita n. ' || v_record.partita_origine || ' (' || v_record.comune_origine || ')' || E'\n';
        IF v_record.partita_destinazione IS NOT NULL THEN v_report := v_report || '  A: Partita n. ' || v_record.partita_destinazione || ' (' || COALESCE(v_record.comune_destinazione, 'N/D') || ')' || E'\n'; END IF;
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

-- ========================================================================
-- Funzione: genera_report_consultazioni
-- ========================================================================
CREATE OR REPLACE FUNCTION genera_report_consultazioni(
    p_data_inizio DATE DEFAULT NULL,
    p_data_fine DATE DEFAULT NULL,
    p_richiedente VARCHAR DEFAULT NULL
)
RETURNS TEXT AS $$
DECLARE
    v_report TEXT := '';
    v_record RECORD;
    v_count INTEGER := 0;
BEGIN
    -- Intestazione (invariata)
    v_report := '============================================================' || E'\n';
    v_report := v_report || '              REPORT DELLE CONSULTAZIONI' || E'\n';
    v_report := v_report || '                CATASTO STORICO ANNI ''50' || E'\n';
    v_report := v_report || '============================================================' || E'\n\n';

    -- Parametri (invariato)
    v_report := v_report || 'PARAMETRI DI RICERCA:' || E'\n';
    IF p_data_inizio IS NOT NULL THEN v_report := v_report || 'Data inizio: ' || p_data_inizio::TEXT || E'\n'; END IF;
    IF p_data_fine IS NOT NULL THEN v_report := v_report || 'Data fine: ' || p_data_fine::TEXT || E'\n'; END IF;
    IF p_richiedente IS NOT NULL THEN v_report := v_report || 'Richiedente: ' || p_richiedente || E'\n'; END IF;
    v_report := v_report || E'\n';

    -- Elenco consultazioni (invariato)
    v_report := v_report || '-------------------- CONSULTAZIONI --------------------' || E'\n';
    FOR v_record IN SELECT c.id, c.data, c.richiedente, c.documento_identita, c.motivazione, c.materiale_consultato, c.funzionario_autorizzante FROM consultazione c WHERE (p_data_inizio IS NULL OR c.data >= p_data_inizio) AND (p_data_fine IS NULL OR c.data <= p_data_fine) AND (p_richiedente IS NULL OR c.richiedente ILIKE '%' || p_richiedente || '%') ORDER BY c.data DESC, c.richiedente LOOP
        v_count := v_count + 1;
        v_report := v_report || 'Consultazione ID: ' || v_record.id || ' - ' || v_record.data::TEXT || E'\n';
        v_report := v_report || '  Richiedente: ' || COALESCE(v_record.richiedente, 'N/D') || E'\n';
        IF v_record.documento_identita IS NOT NULL THEN v_report := v_report || '  Documento: ' || v_record.documento_identita || E'\n'; END IF;
        IF v_record.motivazione IS NOT NULL THEN v_report := v_report || '  Motivazione: ' || v_record.motivazione || E'\n'; END IF;
        v_report := v_report || '  Materiale consultato: ' || COALESCE(v_record.materiale_consultato, 'N/D') || E'\n';
        v_report := v_report || '  Funzionario autorizzante: ' || COALESCE(v_record.funzionario_autorizzante, 'N/D') || E'\n';
        v_report := v_report || E'\n';
    END LOOP;
    IF v_count = 0 THEN v_report := v_report || 'Nessuna consultazione trovata per i parametri specificati.' || E'\n\n';
    ELSE v_report := v_report || 'Totale consultazioni: ' || v_count || E'\n\n'; END IF;

    -- Piè di pagina (invariato)
    v_report := v_report || '============================================================' || E'\n';
    v_report := v_report || 'Report generato il: ' || CURRENT_DATE || E'\n';
    v_report := v_report || 'Il presente report ha valore puramente storico e documentale.' || E'\n';
    v_report := v_report || '============================================================' || E'\n';
    RETURN v_report;
END;
$$ LANGUAGE plpgsql;