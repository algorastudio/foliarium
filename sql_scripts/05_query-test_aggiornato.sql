-- File: 05_query-test_aggiornato.sql
-- Oggetto: Script di test coerente con la struttura DB v2.0
-- Esecuzione: Eseguire DOPO che il DB è stato creato e popolato con dati di esempio.

SET search_path TO catasto, public;
RAISE NOTICE '--- INIZIO SCRIPT DI TEST AGGIORNATO (05) ---';

-- ================================================
-- TEST 1: Creazione/aggiornamento di un POSSESSORE
-- ================================================
DO $$
DECLARE
    v_comune_id INTEGER;
    v_possessore_id INTEGER;
    v_comune_nome VARCHAR := 'Cairo Montenotte'; -- Assumiamo che questo comune esista nei dati di test
    v_nome_completo VARCHAR := 'Verdi Giuseppe di Giacomo';
BEGIN
    RAISE NOTICE '--- TEST 1: Creazione/aggiornamento Possessore ---';
    SELECT id INTO v_comune_id FROM comune WHERE nome = v_comune_nome LIMIT 1;
    IF v_comune_id IS NULL THEN RAISE WARNING 'Comune % non trovato, test saltato.', v_comune_nome; RETURN; END IF;

    -- Test della funzione da 12_procedure_crud.sql
    SELECT crea_o_aggiorna_possessore(
        p_id => NULL, -- Passiamo NULL per creare un nuovo possessore
        p_comune_id => v_comune_id,
        p_cognome_nome => 'Verdi Giuseppe',
        p_paternita => 'di Giacomo',
        p_nome_completo => v_nome_completo
    ) INTO v_possessore_id;

    IF v_possessore_id IS NOT NULL THEN
        RAISE NOTICE '  -> SUCCESS: Possessore creato/trovato con ID: %', v_possessore_id;
    ELSE
        RAISE WARNING '  -> FAILURE: La funzione crea_o_aggiorna_possessore non ha restituito un ID.';
    END IF;
END $$;

-- ================================================
-- TEST 2: Creazione/aggiornamento di una PARTITA
-- ================================================
DO $$
DECLARE
    v_comune_id INTEGER;
    v_partita_id INTEGER;
    v_comune_nome VARCHAR := 'Cairo Montenotte';
BEGIN
    RAISE NOTICE '--- TEST 2: Creazione/aggiornamento Partita ---';
    SELECT id INTO v_comune_id FROM comune WHERE nome = v_comune_nome LIMIT 1;
    IF v_comune_id IS NULL THEN RAISE WARNING 'Comune % non trovato, test saltato.', v_comune_nome; RETURN; END IF;

    -- Test della funzione da 12_procedure_crud.sql
    SELECT crea_o_aggiorna_partita(
        p_id => NULL, -- Crea nuova
        p_comune_id => v_comune_id,
        p_numero_partita => 9999, -- Un numero di partita di test
        p_suffisso_partita => 'TEST',
        p_data_impianto => '1950-01-01',
        p_data_chiusura => NULL,
        p_stato => 'attiva',
        p_tipo => 'principale',
        p_numero_provenienza => 'Test'
    ) INTO v_partita_id;
    
    IF v_partita_id IS NOT NULL THEN
        RAISE NOTICE '  -> SUCCESS: Partita creata/trovata con ID: %', v_partita_id;
    ELSE
        RAISE WARNING '  -> FAILURE: La funzione crea_o_aggiorna_partita non ha restituito un ID.';
    END IF;
END $$;


-- ================================================
-- TEST 3: Generazione REPORT PROPRIETA'
-- ================================================
DO $$
DECLARE
    v_partita_id INTEGER := 1; -- Uso un ID basso, che probabilmente esiste nei dati di test
    v_report TEXT;
BEGIN
    RAISE NOTICE '--- TEST 3: Generazione Report Proprietà (Partita ID: %) ---', v_partita_id;
    -- Test della funzione da 14_report_functions.sql
    SELECT genera_report_proprieta(v_partita_id) INTO v_report;

    IF v_report IS NOT NULL AND LENGTH(v_report) > 0 THEN
         RAISE NOTICE '  -> SUCCESS: Report generato. Lunghezza: % caratteri.', LENGTH(v_report);
         -- Per vedere il report completo, decommenta la riga seguente:
         -- RAISE NOTICE E'\n%\n', v_report;
    ELSE
        RAISE WARNING '  -> FAILURE: Il report è vuoto o NULL.';
    END IF;
END $$;


-- ================================================
-- TEST 4: Generazione REPORT GENEALOGICO
-- ================================================
DO $$
DECLARE
    v_partita_id INTEGER := 1; -- Uso un ID basso, che probabilmente esiste nei dati di test
    v_report TEXT;
BEGIN
    RAISE NOTICE '--- TEST 4: Generazione Report Genealogico (Partita ID: %) ---', v_partita_id;
    -- Test della funzione da 14_report_functions.sql
    SELECT genera_report_genealogico(v_partita_id) INTO v_report;

    IF v_report IS NOT NULL AND LENGTH(v_report) > 0 THEN
         RAISE NOTICE '  -> SUCCESS: Report generato. Lunghezza: % caratteri.', LENGTH(v_report);
    ELSE
        RAISE WARNING '  -> FAILURE: Il report è vuoto o NULL.';
    END IF;
END $$;


-- ================================================
-- TEST 5: RICERCA IMMOBILI PER POSSESSORE
-- ================================================
DO $$
DECLARE
    v_possessore_id INTEGER;
    v_possessore_nome VARCHAR := 'Abramo Adolfo'; -- Un nome dai suoi dati di test
    v_num_risultati INTEGER := 0;
BEGIN
    RAISE NOTICE '--- TEST 5: Ricerca Immobili per Possessore (%) ---', v_possessore_nome;
    SELECT id INTO v_possessore_id FROM possessore WHERE nome_completo ILIKE v_possessore_nome || '%' LIMIT 1;
    IF v_possessore_id IS NULL THEN RAISE WARNING 'Possessore % non trovato, test saltato.', v_possessore_nome; RETURN; END IF;
    
    -- Test della funzione da 17_funzione_ricerca_immobili.sql
    SELECT count(*) INTO v_num_risultati FROM ricerca_immobili_per_possessore(v_possessore_id);

    RAISE NOTICE '  -> RISULTATO: Trovati % immobili per il possessore ID %.', v_num_risultati, v_possessore_id;
    
END $$;

RAISE NOTICE '--- FINE SCRIPT DI TEST AGGIORNATO ---';