-- Script: 05_query-test_corretto.sql
-- Oggetto: Script di test SQL rivisto per il database Catasto Storico
-- Versione: 1.1
-- Data: 30/04/2025
-- Note: Questo script tiene conto dell'uso di comune_id come PK
--       e delle correzioni apportate a funzioni, procedure e viste.
--       Eseguire DOPO 04_dati-esempio_modificato.sql corretto.

-- Imposta lo schema
SET search_path TO catasto, public;

DO $$
BEGIN RAISE NOTICE '--- INIZIO SCRIPT DI TEST (05_query-test_corretto.sql) ---'; END $$;

-- ================================================
-- TEST 1: Inserimento/Verifica Possessore Esistente
-- ================================================
DO $$
DECLARE
    v_possessore_id INTEGER;
    v_comune_id INTEGER;
    v_cognome VARCHAR := 'Rossi Marco';
    v_paternita VARCHAR := 'fu Antonio';
    v_nome_completo VARCHAR := 'Rossi Marco fu Antonio';
    v_comune_nome VARCHAR := 'Carcare';
BEGIN
    RAISE NOTICE '--- TEST 1: Inserisci/Verifica Possessore Esistente ---';
    SELECT id INTO v_comune_id FROM comune WHERE nome = v_comune_nome;
    IF NOT FOUND THEN RAISE WARNING 'Comune % non trovato, test saltato.', v_comune_nome; RETURN; END IF;

    -- Verifica se esiste già
    SELECT id INTO v_possessore_id FROM possessore
    WHERE comune_id = v_comune_id AND nome_completo = v_nome_completo;

    IF v_possessore_id IS NULL THEN
        RAISE WARNING 'Test 1: INASPETTATO - Possessore % non trovato, tentativo inserimento.', v_nome_completo;
        CALL inserisci_possessore(v_comune_id, v_cognome, v_paternita, v_nome_completo, true);
    ELSE
        RAISE NOTICE 'Test 1: OK - Possessore già esistente con ID %: %', v_possessore_id, v_nome_completo;
    END IF;
END $$;

-- Verifica risultato Test 1
SELECT pos.id, pos.cognome_nome, pos.paternita, pos.nome_completo, c.nome as comune_nome
FROM possessore pos JOIN comune c ON pos.comune_id = c.id
WHERE c.nome = 'Carcare' AND pos.cognome_nome = 'Rossi Marco';

DO $$ BEGIN RAISE NOTICE '---------------------------------'; END $$;

-- ================================================
-- TEST 2: Registra Nuova Consultazione
-- ================================================
DO $$
DECLARE
    v_consultazione_id INTEGER;
    v_richiedente VARCHAR := 'Luigi Neri'; -- Nuovo richiedente diverso
    v_oggi DATE := CURRENT_DATE;
BEGIN
    RAISE NOTICE '--- TEST 2: Registra Nuova Consultazione ---';
    -- Verifica se esiste già per questo richiedente oggi
    SELECT id INTO v_consultazione_id FROM consultazione
    WHERE richiedente = v_richiedente AND data = v_oggi;

    IF v_consultazione_id IS NULL THEN
        CALL registra_consultazione(v_oggi, v_richiedente, 'CI ZZ9876543',
            'Verifica genealogica', 'Matricole Altare anni 50', 'Dott. Bianchi');
        RAISE NOTICE 'Test 2: OK - Inserita nuova consultazione per: %', v_richiedente;
    ELSE
        RAISE NOTICE 'Test 2: ATTENZIONE - Consultazione già esistente oggi con ID % per: %', v_consultazione_id, v_richiedente;
    END IF;
END $$;

-- Verifica risultato Test 2
SELECT id, data, richiedente, motivazione FROM consultazione
WHERE richiedente = 'Luigi Neri' ORDER BY data DESC;

DO $$ BEGIN RAISE NOTICE '---------------------------------'; END $$;

-- ================================================
-- TEST 3: Crea Nuova Partita con Possessori
-- ================================================
DO $$
DECLARE
    v_partita_id INTEGER;
    v_numero_partita INTEGER := 303; -- Numero non usato negli esempi
    v_comune_id INTEGER;
    v_comune_nome VARCHAR := 'Carcare';
    v_fossati_id INTEGER;
    v_caviglia_id INTEGER;
    v_possessore_ids INTEGER[];
BEGIN
     RAISE NOTICE '--- TEST 3: Crea Nuova Partita con Possessori Esistenti ---';
    SELECT id INTO v_comune_id FROM comune WHERE nome = v_comune_nome;
    IF NOT FOUND THEN RAISE WARNING 'Comune % non trovato, test saltato.', v_comune_nome; RETURN; END IF;

    -- Verifica se la partita esiste già
    SELECT id INTO v_partita_id FROM partita
    WHERE comune_id = v_comune_id AND numero_partita = v_numero_partita;

    -- Trova gli ID dei possessori esistenti
    SELECT id INTO v_fossati_id FROM possessore WHERE comune_id=v_comune_id AND nome_completo LIKE 'Fossati Angelo%';
    SELECT id INTO v_caviglia_id FROM possessore WHERE comune_id=v_comune_id AND nome_completo LIKE 'Caviglia Maria%';

    v_possessore_ids := ARRAY[]::INTEGER[];
    IF v_fossati_id IS NOT NULL THEN v_possessore_ids := array_append(v_possessore_ids, v_fossati_id); END IF;
    IF v_caviglia_id IS NOT NULL THEN v_possessore_ids := array_append(v_possessore_ids, v_caviglia_id); END IF;

    IF v_partita_id IS NULL THEN
        IF array_length(v_possessore_ids, 1) > 0 THEN
            -- La procedura inserisci_partita_con_possessori è nello script 03
            CALL inserisci_partita_con_possessori(v_comune_id, v_numero_partita, 'principale', CURRENT_DATE, v_possessore_ids);
            RAISE NOTICE 'Test 3: OK - Inserita nuova partita % (Comune ID %) con possessori: %', v_numero_partita, v_comune_id, v_possessore_ids;
        ELSE
            RAISE WARNING 'Test 3: FALLITO - Non trovati possessori (Fossati/Caviglia) nel comune ID %', v_comune_id;
        END IF;
    ELSE
        RAISE NOTICE 'Test 3: ATTENZIONE - Partita % (Comune ID %) già esistente con ID %', v_numero_partita, v_comune_id, v_partita_id;
    END IF;
END $$;

-- Verifica risultato Test 3
SELECT p.*, c.nome as comune_nome
FROM partita p JOIN comune c ON p.comune_id = c.id
WHERE c.nome = 'Carcare' AND p.numero_partita = 303;

DO $$ BEGIN RAISE NOTICE '---------------------------------'; END $$;

-- ================================================
-- TEST 4: Ricerca Partita Esistente (Carcare 221)
-- ================================================
DO $$ BEGIN RAISE NOTICE '--- TEST 4: Ricerca partita numero 221 (Carcare) ---'; END $$;
SELECT
    p.id, c.nome as comune_nome, p.numero_partita, p.tipo, p.stato,
    string_agg(pos.nome_completo, ', ') AS possessori
FROM partita p
JOIN comune c ON p.comune_id = c.id
LEFT JOIN partita_possessore pp ON p.id = pp.partita_id
LEFT JOIN possessore pos ON pp.possessore_id = pos.id
WHERE p.numero_partita = 221 AND c.nome = 'Carcare' -- Filtra per nome comune
GROUP BY p.id, c.nome, p.numero_partita, p.tipo, p.stato;

DO $$ BEGIN RAISE NOTICE '---------------------------------'; END $$;

-- ================================================
-- TEST 5: Ricerca Immobili per Località (Carcare, Via G. Verdi)
-- ================================================
DO $$ BEGIN RAISE NOTICE '--- TEST 5: Ricerca immobili in Via Giuseppe Verdi (Carcare) ---'; END $$;
SELECT
    i.id, i.natura, i.consistenza, i.classificazione,
    l.nome AS localita, c.nome AS comune_nome,
    p.numero_partita,
    string_agg(pos.nome_completo, ', ') AS possessori
FROM immobile i
JOIN localita l ON i.localita_id = l.id
JOIN comune c ON l.comune_id = c.id
JOIN partita p ON i.partita_id = p.id
LEFT JOIN partita_possessore pp ON p.id = pp.partita_id
LEFT JOIN possessore pos ON pp.possessore_id = pos.id
WHERE l.nome LIKE '%Verdi%' AND c.nome = 'Carcare' -- Filtra per nome comune
GROUP BY i.id, i.natura, i.consistenza, i.classificazione, l.nome, c.nome, p.numero_partita;

DO $$ BEGIN RAISE NOTICE '---------------------------------'; END $$;

-- ================================================
-- TEST 6: Elenco Possessori con Conteggi
-- ================================================
DO $$ BEGIN RAISE NOTICE '--- TEST 6: Elenco possessori con num partite/immobili ---'; END $$;
SELECT
    pos.id, pos.nome_completo, c.nome AS comune_nome,
    COUNT(DISTINCT p.id) AS num_partite_totali,
    COUNT(DISTINCT CASE WHEN p.stato='attiva' THEN p.id ELSE NULL END) as num_partite_attive,
    COUNT(DISTINCT i.id) AS numero_immobili_associati
FROM possessore pos
JOIN comune c ON pos.comune_id = c.id
LEFT JOIN partita_possessore pp ON pos.id = pp.possessore_id
LEFT JOIN partita p ON pp.partita_id = p.id
LEFT JOIN immobile i ON p.id = i.partita_id
GROUP BY pos.id, pos.nome_completo, c.nome
ORDER BY c.nome, pos.nome_completo;

DO $$ BEGIN RAISE NOTICE '---------------------------------'; END $$;

-- ================================================
-- TEST 7: Ricerca Possessori Semplice (Funzione cerca_possessori)
-- ================================================
DO $$ BEGIN RAISE NOTICE '--- TEST 7: Ricerca possessore "Fossati" ---'; END $$;
SELECT * FROM cerca_possessori('Fossati'); -- Funzione da script 03 (presume join comune corretto)

DO $$ BEGIN RAISE NOTICE '--- TEST 7: Ricerca possessore "Maria" ---'; END $$;
SELECT * FROM cerca_possessori('Maria');

DO $$ BEGIN RAISE NOTICE '---------------------------------'; END $$;

-- ================================================
-- TEST 8: Immobili di un Possessore (Funzione get_immobili_possessore)
-- ================================================
DO $$
DECLARE
    v_possessore_id INTEGER;
BEGIN
    RAISE NOTICE '--- TEST 8: Immobili di Caviglia Maria ---';
    SELECT id INTO v_possessore_id FROM possessore WHERE nome_completo LIKE 'Caviglia Maria%' LIMIT 1;
    IF v_possessore_id IS NOT NULL THEN
        RAISE NOTICE 'Test 8: Esecuzione get_immobili_possessore per ID % (Caviglia Maria)', v_possessore_id;
    ELSE
        RAISE NOTICE 'Test 8: Possessore "Caviglia Maria" non trovato';
    END IF;
END $$;
-- Esegui la funzione (presume join comune corretto)
SELECT * FROM get_immobili_possessore( (SELECT id FROM possessore WHERE nome_completo LIKE 'Caviglia Maria%' LIMIT 1) );

DO $$ BEGIN RAISE NOTICE '---------------------------------'; END $$;

-- ================================================
-- TEST 9: Vista Partite Complete (v_partite_complete)
-- ================================================
DO $$ BEGIN RAISE NOTICE '--- TEST 9: Vista v_partite_complete (Comune Carcare) ---'; END $$;
SELECT * FROM v_partite_complete WHERE comune_nome = 'Carcare'; -- Vista da script 03 (presume join comune corretto)

DO $$ BEGIN RAISE NOTICE '---------------------------------'; END $$;

-- ================================================
-- TEST 10: Vista Variazioni Complete (v_variazioni_complete)
-- ================================================
DO $$ BEGIN RAISE NOTICE '--- TEST 10: Vista v_variazioni_complete ---'; END $$;
SELECT * FROM v_variazioni_complete ORDER BY data_variazione DESC; -- Vista da script 03 (presume join comune corretto)

DO $$ BEGIN RAISE NOTICE '---------------------------------'; END $$;

-- ================================================
-- TEST 11: Ricerca Avanzata Possessori (pg_trgm)
-- ================================================
DO $$ BEGIN RAISE NOTICE '--- TEST 11: Ricerca avanzata possessore ---'; END $$;
-- Assumiamo che la funzione sia stata corretta in 16_advanced_search.sql per includere comune_nome
DO $$ BEGIN RAISE NOTICE '  -> Ricerca "Angelo Fosati" (typo)'; END $$;
SELECT * FROM ricerca_avanzata_possessori('Angelo Fosati', 0.2);

DO $$ BEGIN RAISE NOTICE '  -> Ricerca "Rossi A"'; END $$;
SELECT * FROM ricerca_avanzata_possessori('Rossi A', 0.3);

DO $$ BEGIN RAISE NOTICE '---------------------------------'; END $$;

-- ================================================
-- TEST 12: Funzione Report Annuale Partite
-- ================================================
DO $$
DECLARE v_comune_id INTEGER; v_comune_nome VARCHAR := 'Carcare';
BEGIN
    RAISE NOTICE '--- TEST 12: Report Annuale Partite ---';
    SELECT id INTO v_comune_id FROM comune WHERE nome = v_comune_nome;
    IF v_comune_id IS NOT NULL THEN
        RAISE NOTICE '  -> Report per % (ID: %), Anno 1950', v_comune_nome, v_comune_id;
        -- Esegui la funzione (l'output viene mostrato dal SELECT successivo)
    ELSE
         RAISE NOTICE '  -> Comune % non trovato per report.', v_comune_nome;
    END IF;
END $$;
-- Funzione da script 08 (modificata per usare comune_id)
SELECT * FROM report_annuale_partite((SELECT id FROM comune WHERE nome = 'Carcare'), 1950);

DO $$ BEGIN RAISE NOTICE '---------------------------------'; END $$;

-- ================================================
-- TEST 13: Funzione Report Proprietà Possessore per Periodo
-- ================================================
DO $$
DECLARE v_possessore_id INTEGER; v_nome VARCHAR := 'Fossati Angelo fu Roberto';
BEGIN
    RAISE NOTICE '--- TEST 13: Report Proprietà Possessore per Periodo ---';
    SELECT id INTO v_possessore_id FROM possessore WHERE nome_completo = v_nome;
    IF v_possessore_id IS NOT NULL THEN
        RAISE NOTICE '  -> Report per % (ID: %), Periodo 1950-01-01 - 1952-12-31', v_nome, v_possessore_id;
    ELSE
         RAISE NOTICE '  -> Possessore % non trovato per report.', v_nome;
    END IF;
END $$;
-- Funzione da script 08 (presume join comune corretto)
SELECT * FROM report_proprieta_possessore(
    (SELECT id FROM possessore WHERE nome_completo = 'Fossati Angelo fu Roberto'),
    '1950-01-01',
    '1952-12-31'
);

DO $$ BEGIN RAISE NOTICE '---------------------------------'; END $$;

-- ================================================
-- TEST 14: Funzione Report Statistico Comune
-- ================================================
DO $$
DECLARE v_comune_id INTEGER; v_comune_nome VARCHAR := 'Cairo Montenotte';
BEGIN
    RAISE NOTICE '--- TEST 14: Report Statistico Comune ---';
    SELECT id INTO v_comune_id FROM comune WHERE nome = v_comune_nome;
    IF v_comune_id IS NOT NULL THEN
        RAISE NOTICE '  -> Report per % (ID: %)', v_comune_nome, v_comune_id;
    ELSE
         RAISE NOTICE '  -> Comune % non trovato per report.', v_comune_nome;
    END IF;
END $$;
-- Funzione da script 14 (modificata per usare comune_id)
-- In 05_query-test_corretto.sql, Test 14
SELECT * FROM genera_report_comune((SELECT id FROM comune WHERE nome = 'Cairo Montenotte'));

DO $$ BEGIN RAISE NOTICE '---------------------------------'; END $$;


DO $$ BEGIN RAISE NOTICE '--- FINE SCRIPT DI TEST ---'; END $$;