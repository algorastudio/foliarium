-- File: 04_dati_stress_test.sql
-- Oggetto: Popola il database con un ampio set di dati per stress test.
-- Versione: 2.0 (Riscritto il 19/06/2025)
--
-- ATTENZIONE: Questo script è distruttivo per i dati di test che genera.
-- Eseguire preferibilmente su un database di sviluppo/test pulito.
--
-- Autore: Marco Santoro (Revisione a cura di "Supporto definitivo per il tirocinio")

SET search_path TO catasto, public;

--==================================================================================
-- PROCEDURA PRINCIPALE DI POPOLAMENTO
--==================================================================================

CREATE OR REPLACE PROCEDURE popola_dati_stress_test(
    p_num_comuni INTEGER DEFAULT 5,
    p_possessori_per_comune INTEGER DEFAULT 100,
    p_partite_per_possessore_medio INTEGER DEFAULT 5,
    p_immobili_per_partita_media INTEGER DEFAULT 3,
    p_percentuale_variazioni FLOAT DEFAULT 0.1 -- Percentuale di partite che subiscono una variazione
)
LANGUAGE plpgsql
AS $$
DECLARE
    -- Variabili per gli ID
    v_comune_id INTEGER;
    v_possessore_id INTEGER;
    v_partita_id INTEGER;
    v_localita_id INTEGER;
    v_variazione_id INTEGER;
    v_partita_origine_id INTEGER;
    v_partita_destinazione_id INTEGER;

    -- Variabili per le tipologie (più efficiente caricarle una sola volta)
    v_tipo_via_id INTEGER;
    v_tipo_piazza_id INTEGER;
    v_tipo_regione_id INTEGER;

    -- Contatori e generatori
    v_comune_counter INTEGER;
    v_possessore_counter INTEGER;
    v_partita_counter INTEGER;
    v_immobile_counter INTEGER;
    v_localita_counter INTEGER;
    v_random_float FLOAT;
    v_last_partita_num INTEGER := 1000;

    -- Dati generati
    v_nome_comune TEXT;
    v_nome_possessore TEXT;
    v_nome_localita TEXT;

    -- Array per memorizzare gli ID generati per ogni comune
    v_possessore_ids INTEGER[];
    v_partita_ids INTEGER[];
    v_localita_ids INTEGER[];

    -- Variabili per il timing
    v_start_time TIMESTAMPTZ(0);
    v_end_time TIMESTAMPTZ(0);
BEGIN
    v_start_time := clock_timestamp();
    RAISE NOTICE '[STRESS TEST] Inizio popolamento: %', v_start_time;

    -- === PASSO PRELIMINARE: Assicura l'esistenza dei tipi di località necessari ===
    -- Questo rende lo script auto-contenuto e robusto, evitando errori se le tipologie non esistono.
    RAISE NOTICE 'Verifica e creazione delle tipologie di località necessarie...';
    INSERT INTO catasto.tipo_localita (nome, descrizione) VALUES ('Strada', 'Tipologia generica per vie, corsi, ecc.') ON CONFLICT (nome) DO NOTHING;
    INSERT INTO catasto.tipo_localita (nome, descrizione) VALUES ('Piazza', 'Area urbana aperta') ON CONFLICT (nome) DO NOTHING;
    INSERT INTO catasto.tipo_localita (nome, descrizione) VALUES ('Regione/Frazione', 'Area geografica o frazione') ON CONFLICT (nome) DO NOTHING;

    -- Recupera gli ID delle tipologie in variabili per un uso efficiente nei cicli
    SELECT id INTO v_tipo_via_id FROM catasto.tipo_localita WHERE nome = 'Strada';
    SELECT id INTO v_tipo_piazza_id FROM catasto.tipo_localita WHERE nome = 'Piazza';
    SELECT id INTO v_tipo_regione_id FROM catasto.tipo_localita WHERE nome = 'Regione/Frazione';

    IF v_tipo_via_id IS NULL OR v_tipo_piazza_id IS NULL OR v_tipo_regione_id IS NULL THEN
        RAISE EXCEPTION 'Impossibile recuperare gli ID delle tipologie di località base. Test interrotto.';
    END IF;


    -- ==============================================================================
    -- CICLO 1: Genera Comuni
    -- ==============================================================================
    RAISE NOTICE 'Generazione % Comuni...', p_num_comuni;
    FOR v_comune_counter IN 1..p_num_comuni LOOP
        v_nome_comune := 'Comune Stress Test ' || v_comune_counter;
        INSERT INTO comune (nome, provincia, regione)
        VALUES (v_nome_comune, 'Prov ' || v_comune_counter, 'Regione Stress')
        RETURNING id INTO v_comune_id;

        -- Reset degli array per ogni nuovo comune
        v_possessore_ids := '{}';
        v_partita_ids := '{}';
        v_localita_ids := '{}';
        v_last_partita_num := 1000;

        -- ==============================================================================
        -- CICLO 2: Genera Località per il Comune corrente
        -- ==============================================================================
        v_localita_counter := 1;
        -- Generiamo un numero ridotto di località per comune per rendere i dati più realistici
        WHILE v_localita_counter <= 10 LOOP
             
             -- Logica per alternare tipologie stradali
             IF v_localita_counter % 2 = 0 THEN
                -- Inserisce una Piazza
                v_nome_localita := 'Libertà ' || v_localita_counter;
                INSERT INTO localita (comune_id, nome, tipologia_stradale, tipo_id, civico)
                VALUES (v_comune_id, v_nome_localita, 'Piazza', v_tipo_piazza_id, floor(random()*50 + 1)::text)
                RETURNING id INTO v_localita_id;
             ELSE
                -- Inserisce una Via
                v_nome_localita := 'Roma ' || v_localita_counter;
                INSERT INTO localita (comune_id, nome, tipologia_stradale, tipo_id, civico)
                VALUES (v_comune_id, v_nome_localita, 'Via', v_tipo_via_id, floor(random()*100 + 1)::text)
                RETURNING id INTO v_localita_id;
             END IF;

             v_localita_ids := array_append(v_localita_ids, v_localita_id);
             v_localita_counter := v_localita_counter + 1;
        END LOOP;

        IF array_length(v_localita_ids, 1) IS NULL THEN
             RAISE WARNING 'Nessuna località creata per comune ID %, impossibile creare immobili.', v_comune_id;
             CONTINUE; -- Salta al prossimo comune
        END IF;

        -- ==============================================================================
        -- CICLO 3: Genera Possessori per il Comune corrente
        -- ==============================================================================
        RAISE NOTICE '  Generazione % Possessori per Comune ID %...', p_possessori_per_comune, v_comune_id;
        FOR v_possessore_counter IN 1..p_possessori_per_comune LOOP
            v_nome_possessore := 'Possessore ' || v_comune_counter || '-' || v_possessore_counter || ' Rossi';
            INSERT INTO possessore (comune_id, cognome_nome, paternita, nome_completo, attivo)
            VALUES (v_comune_id, 'Stress ' || v_possessore_counter, 'fu Test', v_nome_possessore, TRUE)
            RETURNING id INTO v_possessore_id;
            v_possessore_ids := array_append(v_possessore_ids, v_possessore_id);
        END LOOP;

        -- ==============================================================================
        -- CICLO 4: Genera Partite e Immobili per ogni Possessore
        -- ==============================================================================
        RAISE NOTICE '  Generazione Partite e Immobili...';
        FOR v_possessore_id IN SELECT unnest(v_possessore_ids) LOOP
            FOR v_partita_counter IN 1..p_partite_per_possessore_medio LOOP
                v_last_partita_num := v_last_partita_num + 1;
                INSERT INTO partita (comune_id, numero_partita, tipo, data_impianto, stato)
                VALUES (v_comune_id, v_last_partita_num, 'principale', NOW()::date - interval '1 year' * floor(random()*50), 'attiva')
                RETURNING id INTO v_partita_id;
                v_partita_ids := array_append(v_partita_ids, v_partita_id);

                INSERT INTO partita_possessore (partita_id, possessore_id, tipo_partita, titolo)
                VALUES (v_partita_id, v_possessore_id, 'principale', 'proprieta esclusiva');

                FOR v_immobile_counter IN 1..p_immobili_per_partita_media LOOP
                    v_localita_id := v_localita_ids[floor(random()*array_length(v_localita_ids, 1) + 1)];
                    INSERT INTO immobile (partita_id, localita_id, natura, classificazione, consistenza)
                    VALUES (
                        v_partita_id, v_localita_id, 'Edificio Stress ' || v_immobile_counter,
                        'Classe Stress ' || floor(random()*5+1), floor(random()*200 + 50)::text || ' mq'
                    );
                END LOOP;
            END LOOP;
        END LOOP;

        -- ==============================================================================
        -- CICLO 5: Genera Variazioni e Contratti (opzionale)
        -- ==============================================================================
        RAISE NOTICE '  Generazione Variazioni e Contratti...';
        FOR v_partita_origine_id IN SELECT unnest(v_partita_ids) LOOP
             IF random() < p_percentuale_variazioni THEN
                 v_last_partita_num := v_last_partita_num + 1;
                 INSERT INTO partita (comune_id, numero_partita, tipo, data_impianto, numero_provenienza, stato)
                 VALUES (v_comune_id, v_last_partita_num, 'principale', NOW()::date - interval '1 day' * floor(random()*100), (SELECT numero_partita FROM partita WHERE id=v_partita_origine_id)::text, 'attiva')
                 RETURNING id INTO v_partita_destinazione_id;

                 v_possessore_id := v_possessore_ids[floor(random()*array_length(v_possessore_ids, 1) + 1)];
                 INSERT INTO partita_possessore (partita_id, possessore_id, tipo_partita, titolo)
                 VALUES (v_partita_destinazione_id, v_possessore_id, 'principale', 'proprieta esclusiva');

                 INSERT INTO variazione (partita_origine_id, partita_destinazione_id, tipo, data_variazione)
                 VALUES (v_partita_origine_id, v_partita_destinazione_id, 'Vendita', NOW()::date - interval '1 day' * floor(random()*100))
                 RETURNING id INTO v_variazione_id;

                 INSERT INTO contratto (variazione_id, tipo, data_contratto, notaio)
                 VALUES (v_variazione_id, 'Atto di Compravendita', NOW()::date - interval '1 day' * floor(random()*100 + 1), 'Notaio Stress Test');

                 UPDATE partita SET stato = 'inattiva', data_chiusura = (SELECT data_variazione FROM variazione WHERE id = v_variazione_id)
                 WHERE id = v_partita_origine_id;

                 UPDATE immobile SET partita_id = v_partita_destinazione_id
                 WHERE partita_id = v_partita_origine_id;
             END IF;
        END LOOP;

    END LOOP; -- Fine loop comuni

    v_end_time := clock_timestamp();
    RAISE NOTICE '[STRESS TEST] Fine popolamento: %', v_end_time;
    RAISE NOTICE '[STRESS TEST] Durata totale: %', v_end_time - v_start_time;

EXCEPTION WHEN OTHERS THEN
    RAISE WARNING '[STRESS TEST] Errore durante il popolamento: % - SQLSTATE: %', SQLERRM, SQLSTATE;
END;
$$;


-- ==================================================================================
-- ESECUZIONE DELLA PROCEDURA
-- ==================================================================================
DO $$ BEGIN
    RAISE NOTICE 'Esecuzione procedura popola_dati_stress_test...';
END $$;

CALL popola_dati_stress_test(
    p_num_comuni => 20,
    p_possessori_per_comune => 100,
    p_partite_per_possessore_medio => 5,
    p_immobili_per_partita_media => 3,
    p_percentuale_variazioni => 0.40
);

DO $$ BEGIN
    RAISE NOTICE 'Procedura popola_dati_stress_test completata.';
END $$;