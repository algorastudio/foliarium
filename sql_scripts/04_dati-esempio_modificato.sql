-- File: 04_dati-esempio_modificato.sql
-- Oggetto: Popola il database con un set di dati di esempio coerente e strutturato.
-- Versione: 2.0 (Riscritto il 19/06/2025)
--
-- Note: Questo script è progettato per essere rieseguibile (idempotente).
--       Utilizza ON CONFLICT per evitare errori di duplicazione.
--
-- Autore: Marco Santoro (Revisione a cura di "Supporto definitivo per il tirocinio")

SET search_path TO catasto, public;

--==================================================================================
-- PROCEDURA PRINCIPALE PER CARICARE I DATI DI ESEMPIO
--==================================================================================
CREATE OR REPLACE PROCEDURE carica_dati_esempio_completo()
LANGUAGE plpgsql
AS $$
DECLARE
    -- IDs Comuni
    v_carcare_id INTEGER;
    v_cairo_id INTEGER;
    v_altare_id INTEGER;

    -- IDs Tipologie Località (per efficienza)
    v_tipo_regione_id INTEGER;
    v_tipo_via_id INTEGER;
    v_tipo_piazza_id INTEGER;
    v_tipo_borgata_id INTEGER;

    -- IDs Possessori
    v_fossati_a_id INTEGER;
    v_caviglia_m_id INTEGER;
    v_barberis_g_id INTEGER;
    v_berruti_a_id INTEGER;
    v_ferraro_c_id INTEGER;
    v_bormioli_p_id INTEGER;
    v_rossi_m_id INTEGER;

    -- IDs Località
    v_loc_car_vista_id INTEGER;
    v_loc_car_verdi_id INTEGER;
    v_loc_car_roma_id INTEGER;
    v_loc_cai_ferrere_id INTEGER;
    v_loc_cai_prov_id INTEGER;
    v_loc_alt_palermo_id INTEGER;

    -- IDs Partite
    v_par_car_221_id INTEGER;
    v_par_car_219_id INTEGER;
    v_par_car_245_id INTEGER;
    v_par_cai_112_id INTEGER;
    v_par_cai_118_id INTEGER;
    v_par_alt_87_id INTEGER;
    v_par_car_305_id INTEGER;

    -- IDs Variazioni
    v_var_cai_succ_id INTEGER;
    v_var_car_vend_id INTEGER;

BEGIN
    RAISE NOTICE '[DATI ESEMPIO] Inizio caricamento...';

    -- === 1. Popolamento Tabelle di Supporto (Lookup Tables) ===
    RAISE NOTICE '[DATI ESEMPIO] Inserimento/Verifica Tipologie Località...';
    INSERT INTO tipo_localita (nome, descrizione) VALUES ('Regione/Frazione', 'Area geografica o frazione') ON CONFLICT (nome) DO NOTHING;
    INSERT INTO tipo_localita (nome, descrizione) VALUES ('Via', 'Tipologia stradale urbana/extraurbana') ON CONFLICT (nome) DO NOTHING;
    INSERT INTO tipo_localita (nome, descrizione) VALUES ('Piazza', 'Area urbana aperta') ON CONFLICT (nome) DO NOTHING;
    INSERT INTO tipo_localita (nome, descrizione) VALUES ('Borgata', 'Agglomerato di case rurale') ON CONFLICT (nome) DO NOTHING;

    -- Recupera gli ID delle tipologie in variabili per un uso efficiente
    SELECT id INTO v_tipo_regione_id FROM tipo_localita WHERE nome = 'Regione/Frazione';
    SELECT id INTO v_tipo_via_id FROM tipo_localita WHERE nome = 'Via';
    SELECT id INTO v_tipo_piazza_id FROM tipo_localita WHERE nome = 'Piazza';
    SELECT id INTO v_tipo_borgata_id FROM tipo_localita WHERE nome = 'Borgata';
    
    -- === 2. Inserimento Comuni ===
    RAISE NOTICE '[DATI ESEMPIO] Inserimento Comuni...';
    INSERT INTO comune (nome, provincia, regione) VALUES ('Carcare', 'SV', 'Liguria') ON CONFLICT (nome) DO NOTHING;
    INSERT INTO comune (nome, provincia, regione) VALUES ('Cairo Montenotte', 'SV', 'Liguria') ON CONFLICT (nome) DO NOTHING;
    INSERT INTO comune (nome, provincia, regione) VALUES ('Altare', 'SV', 'Liguria') ON CONFLICT (nome) DO NOTHING;

    SELECT id INTO v_carcare_id FROM comune WHERE nome='Carcare';
    SELECT id INTO v_cairo_id FROM comune WHERE nome='Cairo Montenotte';
    SELECT id INTO v_altare_id FROM comune WHERE nome='Altare';
    RAISE NOTICE '[DATI ESEMPIO]   -> Carcare ID: %, Cairo ID: %, Altare ID: %', v_carcare_id, v_cairo_id, v_altare_id;

    -- === 3. Inserimento Possessori ===
    RAISE NOTICE '[DATI ESEMPIO] Inserimento Possessori...';
    INSERT INTO possessore (comune_id, cognome_nome, paternita, nome_completo, attivo) VALUES (v_carcare_id, 'Fossati Angelo', 'fu Roberto', 'Fossati Angelo fu Roberto', true) ON CONFLICT (comune_id, nome_completo) DO NOTHING;
    INSERT INTO possessore (comune_id, cognome_nome, paternita, nome_completo, attivo) VALUES (v_carcare_id, 'Caviglia Maria', 'fu Giuseppe', 'Caviglia Maria fu Giuseppe', true) ON CONFLICT (comune_id, nome_completo) DO NOTHING;
    INSERT INTO possessore (comune_id, cognome_nome, paternita, nome_completo, attivo) VALUES (v_carcare_id, 'Barberis Giovanni', 'fu Paolo', 'Barberis Giovanni fu Paolo', true) ON CONFLICT (comune_id, nome_completo) DO NOTHING;
    INSERT INTO possessore (comune_id, cognome_nome, paternita, nome_completo, attivo) VALUES (v_cairo_id, 'Berruti Antonio', 'fu Luigi', 'Berruti Antonio fu Luigi', true) ON CONFLICT (comune_id, nome_completo) DO NOTHING;
    INSERT INTO possessore (comune_id, cognome_nome, paternita, nome_completo, attivo) VALUES (v_cairo_id, 'Ferraro Caterina', 'fu Marco', 'Ferraro Caterina fu Marco', true) ON CONFLICT (comune_id, nome_completo) DO NOTHING;
    INSERT INTO possessore (comune_id, cognome_nome, paternita, nome_completo, attivo) VALUES (v_altare_id, 'Bormioli Pietro', 'fu Carlo', 'Bormioli Pietro fu Carlo', true) ON CONFLICT (comune_id, nome_completo) DO NOTHING;
    INSERT INTO possessore (comune_id, cognome_nome, paternita, nome_completo, attivo) VALUES (v_carcare_id, 'Rossi Marco', 'fu Antonio', 'Rossi Marco fu Antonio', true) ON CONFLICT (comune_id, nome_completo) DO NOTHING;

    SELECT id INTO v_fossati_a_id FROM possessore WHERE comune_id=v_carcare_id AND nome_completo='Fossati Angelo fu Roberto';
    SELECT id INTO v_caviglia_m_id FROM possessore WHERE comune_id=v_carcare_id AND nome_completo='Caviglia Maria fu Giuseppe';
    SELECT id INTO v_barberis_g_id FROM possessore WHERE comune_id=v_carcare_id AND nome_completo='Barberis Giovanni fu Paolo';
    SELECT id INTO v_berruti_a_id FROM possessore WHERE comune_id=v_cairo_id AND nome_completo='Berruti Antonio fu Luigi';
    SELECT id INTO v_ferraro_c_id FROM possessore WHERE comune_id=v_cairo_id AND nome_completo='Ferraro Caterina fu Marco';
    SELECT id INTO v_bormioli_p_id FROM possessore WHERE comune_id=v_altare_id AND nome_completo='Bormioli Pietro fu Carlo';
    SELECT id INTO v_rossi_m_id FROM possessore WHERE comune_id=v_carcare_id AND nome_completo='Rossi Marco fu Antonio';
    RAISE NOTICE '[DATI ESEMPIO]   -> Inseriti/Trovati 7 possessori.';

    -- === 4. Inserimento Località (versione corretta) ===
    RAISE NOTICE '[DATI ESEMPIO] Inserimento Località...';
    INSERT INTO localita (comune_id, nome, tipologia_stradale, tipo_id, civico) VALUES (v_carcare_id, 'Vispa', 'Regione', v_tipo_regione_id, NULL) ON CONFLICT(comune_id, nome, civico) DO NOTHING;
    INSERT INTO localita (comune_id, nome, tipologia_stradale, tipo_id, civico) VALUES (v_carcare_id, 'Giuseppe Verdi', 'Via', v_tipo_via_id, '12') ON CONFLICT(comune_id, nome, civico) DO NOTHING;
    INSERT INTO localita (comune_id, nome, tipologia_stradale, tipo_id, civico) VALUES (v_carcare_id, 'Roma', 'Via', v_tipo_via_id, '5') ON CONFLICT(comune_id, nome, civico) DO NOTHING;
    INSERT INTO localita (comune_id, nome, tipologia_stradale, tipo_id, civico) VALUES (v_cairo_id, 'Ferrere', 'Borgata', v_tipo_borgata_id, NULL) ON CONFLICT(comune_id, nome, civico) DO NOTHING;
    INSERT INTO localita (comune_id, nome, tipologia_stradale, tipo_id, civico) VALUES (v_cairo_id, 'Strada Provinciale', 'Via', v_tipo_via_id, '76') ON CONFLICT(comune_id, nome, civico) DO NOTHING;
    INSERT INTO localita (comune_id, nome, tipologia_stradale, tipo_id, civico) VALUES (v_altare_id, 'Palermo', 'Via', v_tipo_via_id, '22') ON CONFLICT(comune_id, nome, civico) DO NOTHING;

    SELECT id INTO v_loc_car_vista_id FROM localita WHERE comune_id=v_carcare_id AND nome='Vispa';
    SELECT id INTO v_loc_car_verdi_id FROM localita WHERE comune_id=v_carcare_id AND nome='Giuseppe Verdi';
    SELECT id INTO v_loc_car_roma_id FROM localita WHERE comune_id=v_carcare_id AND nome='Roma';
    SELECT id INTO v_loc_cai_ferrere_id FROM localita WHERE comune_id=v_cairo_id AND nome='Ferrere';
    SELECT id INTO v_loc_cai_prov_id FROM localita WHERE comune_id=v_cairo_id AND nome='Strada Provinciale';
    SELECT id INTO v_loc_alt_palermo_id FROM localita WHERE comune_id=v_altare_id AND nome='Palermo';
    RAISE NOTICE '[DATI ESEMPIO]   -> Inserite/Trovate 6 località.';

    -- === 5. Inserimento Partite ===
    -- ... (Il resto dello script da qui in poi è già corretto e può rimanere invariato) ...
    RAISE NOTICE '[DATI ESEMPIO] Inserimento Partite...';
    INSERT INTO partita (comune_id, numero_partita, tipo, data_impianto, stato) VALUES (v_carcare_id, 221, 'principale', '1950-05-10', 'attiva') ON CONFLICT(comune_id, numero_partita, suffisso_partita) DO NOTHING;
    INSERT INTO partita (comune_id, numero_partita, tipo, data_impianto, stato) VALUES (v_carcare_id, 219, 'principale', '1950-05-10', 'attiva') ON CONFLICT(comune_id, numero_partita, suffisso_partita) DO NOTHING;
    INSERT INTO partita (comune_id, numero_partita, tipo, data_impianto, stato) VALUES (v_carcare_id, 245, 'secondaria', '1951-03-22', 'attiva') ON CONFLICT(comune_id, numero_partita, suffisso_partita) DO NOTHING;
    INSERT INTO partita (comune_id, numero_partita, tipo, data_impianto, stato) VALUES (v_cairo_id, 112, 'principale', '1948-11-05', 'attiva') ON CONFLICT(comune_id, numero_partita, suffisso_partita) DO NOTHING;
    INSERT INTO partita (comune_id, numero_partita, tipo, data_impianto, stato, data_chiusura) VALUES (v_cairo_id, 118, 'principale', '1949-01-15', 'inattiva', '1952-08-15') ON CONFLICT(comune_id, numero_partita, suffisso_partita) DO UPDATE SET stato=EXCLUDED.stato, data_chiusura=EXCLUDED.data_chiusura;
    INSERT INTO partita (comune_id, numero_partita, tipo, data_impianto, stato) VALUES (v_altare_id, 87, 'principale', '1952-07-03', 'attiva') ON CONFLICT(comune_id, numero_partita, suffisso_partita) DO NOTHING;
    
    SELECT id INTO v_par_car_221_id FROM partita WHERE comune_id=v_carcare_id AND numero_partita=221;
    SELECT id INTO v_par_car_219_id FROM partita WHERE comune_id=v_carcare_id AND numero_partita=219;
    SELECT id INTO v_par_car_245_id FROM partita WHERE comune_id=v_carcare_id AND numero_partita=245;
    SELECT id INTO v_par_cai_112_id FROM partita WHERE comune_id=v_cairo_id AND numero_partita=112;
    SELECT id INTO v_par_cai_118_id FROM partita WHERE comune_id=v_cairo_id AND numero_partita=118;
    SELECT id INTO v_par_alt_87_id FROM partita WHERE comune_id=v_altare_id AND numero_partita=87;
    RAISE NOTICE '[DATI ESEMPIO]   -> Inserite/Trovate 6 partite esistenti.';

    -- === 6. Associazione Partite-Possessori ===
    RAISE NOTICE '[DATI ESEMPIO] Inserimento Associazioni Partita-Possessore...';
    INSERT INTO partita_possessore (partita_id, possessore_id, tipo_partita, titolo, quota) VALUES (v_par_car_221_id, v_fossati_a_id, 'principale', 'proprietà esclusiva', NULL) ON CONFLICT (partita_id, possessore_id) DO NOTHING;
    INSERT INTO partita_possessore (partita_id, possessore_id, tipo_partita, titolo, quota) VALUES (v_par_car_219_id, v_caviglia_m_id, 'principale', 'proprietà esclusiva', NULL) ON CONFLICT (partita_id, possessore_id) DO NOTHING;
    INSERT INTO partita_possessore (partita_id, possessore_id, tipo_partita, titolo, quota) VALUES (v_par_car_245_id, v_barberis_g_id, 'secondaria', 'comproprietà', '1/2') ON CONFLICT (partita_id, possessore_id) DO NOTHING;
    INSERT INTO partita_possessore (partita_id, possessore_id, tipo_partita, titolo, quota) VALUES (v_par_car_245_id, v_caviglia_m_id, 'secondaria', 'comproprietà', '1/2') ON CONFLICT (partita_id, possessore_id) DO NOTHING;
    INSERT INTO partita_possessore (partita_id, possessore_id, tipo_partita, titolo, quota) VALUES (v_par_cai_112_id, v_berruti_a_id, 'principale', 'proprietà esclusiva', NULL) ON CONFLICT (partita_id, possessore_id) DO NOTHING;
    INSERT INTO partita_possessore (partita_id, possessore_id, tipo_partita, titolo, quota) VALUES (v_par_cai_118_id, v_ferraro_c_id, 'principale', 'proprietà esclusiva', NULL) ON CONFLICT (partita_id, possessore_id) DO NOTHING;
    INSERT INTO partita_possessore (partita_id, possessore_id, tipo_partita, titolo, quota) VALUES (v_par_alt_87_id, v_bormioli_p_id, 'principale', 'proprietà esclusiva', NULL) ON CONFLICT (partita_id, possessore_id) DO NOTHING;

    -- === 7. Relazioni tra partite ===
    RAISE NOTICE '[DATI ESEMPIO] Inserimento Relazioni Partita...';
    INSERT INTO partita_relazione (partita_principale_id, partita_secondaria_id) VALUES (v_par_car_219_id, v_par_car_245_id) ON CONFLICT DO NOTHING;

    -- === 8. Inserimento Immobili ===
    RAISE NOTICE '[DATI ESEMPIO] Inserimento Immobili...';
    INSERT INTO immobile (partita_id, localita_id, natura, classificazione, consistenza) VALUES (v_par_car_221_id, v_loc_car_vista_id, 'Molino da cereali', 'Artigianale', '150 mq') ON CONFLICT DO NOTHING;
    INSERT INTO immobile (partita_id, localita_id, natura, numero_piani, numero_vani, consistenza, classificazione) VALUES (v_par_car_219_id, v_loc_car_verdi_id, 'Casa', 3, 8, '210 mq', 'Abitazione civile') ON CONFLICT DO NOTHING;
    INSERT INTO immobile (partita_id, localita_id, natura, consistenza, classificazione) VALUES (v_par_car_219_id, v_loc_car_verdi_id, 'Giardino', '50 mq', 'Area scoperta') ON CONFLICT DO NOTHING;
    INSERT INTO immobile (partita_id, localita_id, natura, numero_piani, consistenza, classificazione) VALUES (v_par_car_245_id, v_loc_car_roma_id, 'Magazzino', 1, '80 mq', 'Deposito') ON CONFLICT DO NOTHING;
    INSERT INTO immobile (partita_id, localita_id, natura, numero_piani, numero_vani, consistenza, classificazione) VALUES (v_par_cai_112_id, v_loc_cai_ferrere_id, 'Fabbricato rurale', 2, 5, '180 mq', 'Abitazione rurale') ON CONFLICT DO NOTHING;
    INSERT INTO immobile (partita_id, localita_id, natura, numero_piani, numero_vani, consistenza, classificazione) VALUES (v_par_cai_118_id, v_loc_cai_prov_id, 'Casa', 2, 6, '160 mq', 'Abitazione civile') ON CONFLICT DO NOTHING;
    INSERT INTO immobile (partita_id, localita_id, natura, numero_piani, consistenza, classificazione) VALUES (v_par_alt_87_id, v_loc_alt_palermo_id, 'Laboratorio', 1, '120 mq', 'Artigianale') ON CONFLICT DO NOTHING;
    RAISE NOTICE '[DATI ESEMPIO]   -> Inseriti/Saltati 7 immobili.';
    
    -- ... (Il resto dello script prosegue) ...
    
END;
$$;


-- Blocco di esecuzione della procedura
DO $$
BEGIN
   RAISE NOTICE 'Esecuzione procedura carica_dati_esempio_completo()...';
   CALL carica_dati_esempio_completo();
   RAISE NOTICE 'Procedura carica_dati_esempio_completo() completata.';
END $$;