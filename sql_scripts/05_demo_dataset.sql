-- File: 05_demo_dataset.sql  (v2 — dataset ampliato)
\encoding UTF8
-- Dataset demo completo per Meridiana — Archivio Catastale Storico
-- Provincia di Savona, periodo 1870–1985
--
-- Totale generato (circa):
--   10 comuni, 120 possessori, 80 località, 300 partite,
--   600 immobili, 80 variazioni, 80 contratti, 60 consultazioni,
--   20 registri partite
--
-- Uso: psql -d catasto_storico -f sql_scripts/05_demo_dataset.sql

SET search_path TO catasto, public;

-- ============================================================
-- DROP + RICREA per idempotenza
-- ============================================================
DROP PROCEDURE IF EXISTS carica_demo_savona_v2();

CREATE OR REPLACE PROCEDURE carica_demo_savona_v2()
LANGUAGE plpgsql AS $$
DECLARE
    -- === TIPO_LOCALITA IDs ===
    tl_via INTEGER; tl_pza INTEGER; tl_reg INTEGER; tl_bor INTEGER;
    tl_fra INTEGER; tl_lng INTEGER; tl_cso INTEGER; tl_vco INTEGER;

    -- === POOL NOMI / DATI ===
    v_cognomi TEXT[] := ARRAY[
        'Bruzzone','Ferrando','Bovio','Rolando','Zunino','Bolla','Rebagliati','Ricci',
        'Muzio','Scarrone','Lanteri','Saccone','Parodi','Molinaro','Vignolo','Bonino',
        'Ardissone','Pastorino','Bagnasco','Crovetto','Anfossi','Casanova','Trucco',
        'Riccardi','Aicardi','Delfino','Siffredi','Lavaggi','Gandolfo','Ferroni',
        'Raimondo','Pellegrino','Gaggero','Castelletto','Briasco','Bozzano','Rollero',
        'Marenco','Ferretti','Colombo','Siri','Repetto','Astengo','Grasso','Negro',
        'Ferrari','Rossi','Bianchi','Gallo','Oddo','Pistone','Traverso','Magnone',
        'Bracco','Canepa','Rosso','Ghiglione','Viale','Ottonello','Ighina',
        'Ferrero','Cuneo','Olivieri','Bigatti','Piccardo','Ravera','Ghiso',
        'Baracco','Simonetti','Oddone','Calvo','Delucchi','Leoni','Monti',
        'Serra','Sasso','Capello','Davide','Rizzo','Russo','Martino',
        'Giaime','Perini','Celoria','Tamburini','Frumento','Calcagno','Molinelli',
        'Peluffo','Dagnino','Firpo','Pera','Beato','Gallizia','Genta',
        'Bertonasco','Capurro','Manzino','Poggio','Verardo','Maccio','Morando',
        'Ponzo','Rosasco','Cevasco','Pastrone','Queirolo','Zunini','Borgogno',
        'Cavassa','Dellacha','Fassio','Garelli','Lanzone','Amoretti','Bertone',
        'Chiarlone','Ferruccio','Campora','Novaro','Rebora','Spotorno','Tasso'
    ];

    v_nomi_m TEXT[] := ARRAY[
        'Giovanni','Pietro','Luigi','Carlo','Angelo','Giuseppe','Battista',
        'Stefano','Antonio','Marco','Agostino','Francesco','Emilio','Natale',
        'Domenico','Giacomo','Vincenzo','Luca','Roberto','Ernesto','Ugo',
        'Raimondo','Bernardo','Aldo','Silvio','Renato','Edoardo','Ottavio',
        'Dario','Ezio','Ilario','Ambrogio','Severino','Felice','Costantino'
    ];

    v_nomi_f TEXT[] := ARRAY[
        'Maria','Anna','Teresa','Caterina','Giuseppina','Rosa','Elena',
        'Luisa','Margherita','Lucia','Ida','Rina','Angela','Rita','Carla',
        'Emma','Lidia','Elvira','Adelina','Concetta','Giannina','Palmira',
        'Iolanda','Giovanna','Carmela','Vittoria','Olimpia','Assunta','Amelia','Elisa'
    ];

    v_paternita TEXT[] := ARRAY[
        'fu Giovanni','di Pietro','fu Carlo','di Giuseppe','fu Angelo',
        'fu Luigi','di Francesco','fu Antonio','di Marco','fu Stefano',
        'fu Battista','di Agostino','fu Domenico','di Giacomo','fu Natale'
    ];

    v_nature TEXT[] := ARRAY[
        'Casa di abitazione','Fabbricato rurale','Magazzino','Orto','Vigna',
        'Bosco ceduo','Prato','Molino da cereali','Bottega','Laboratorio artigianale',
        'Oliveto','Stalla','Fienile','Castagneto','Cantina','Deposito attrezzi',
        'Cascinale','Terreno agricolo','Villa','Opificio','Cascina','Rustico',
        'Frantoio','Locanda','Palazzo'
    ];

    v_classif TEXT[] := ARRAY[
        'Abitazione civile','Abitazione rurale','Deposito','Agricola','Forestale',
        'Artigianale','Locale commerciale','Abitazione signorile','Industriale',
        'Abitazione storica','Area coltivata','Area scoperta','Rustico','Misto'
    ];

    v_vie_nomi TEXT[] := ARRAY[
        'Roma','Garibaldi','Mazzini','Cavour','Dante','Vittorio Emanuele',
        'Palestro','Genova','Torino','Milano','Aurelia','Provinciale',
        'San Martino','Santa Lucia','Madonna delle Grazie','Giuseppe Verdi',
        'Carlo Alberto','Bormida','Orba','Letimbro','Nino Bixio','Trento',
        'Trieste','San Francesco','Cristoforo Colombo','Venti Settembre',
        'Quattro Novembre','Caduti sul Lavoro','Pio VII','Re Umberto'
    ];

    v_piazze_nomi TEXT[] := ARRAY[
        'Libertà','Italia','Vittoria','della Repubblica','del Popolo',
        'San Giovanni','Santa Maria','Municipio','dei Martiri','Garibaldi',
        'Verdi','Cavour','Mazzini','Umberto I','Roma'
    ];

    v_regioni_nomi TEXT[] := ARRAY[
        'Vispa','Turchino','Bormida','Alta Valle','Colletta',
        'Montarosio','Poggio Alto','Siepi','Fossatello','Pianura',
        'Crosa','Quarzina','Ronco','Riviera','Castellaro',
        'Madonnetta','Passatore','Ponti','Varaldo','Grillaia'
    ];

    v_borgate_nomi TEXT[] := ARRAY[
        'Bragno','Ferrere','Casanova','Mulino Vecchio','Ponte Vecchio',
        'Acquafredda','Valle Scura','Cascina Grande','Camporotondo','Molino Nuovo',
        'Fornaci','Casalino','Casette','Colle','Piandistella'
    ];

    v_notai TEXT[] := ARRAY[
        'Anfossi Giovanni','Gaggero Luigi','Ferretti Oreste','Briasco Franco',
        'Rollero Piero','Bozzano Carlo','Marenco Ettore','Castelletto Mario',
        'Bruzzone Paolo','Ricci Antonio','Pastorino Ernesto','Colombo Giorgio',
        'Siri Battista','Negro Felice','Traverso Agostino','Bonino Alberto',
        'Ardissone Enrico','Casanova Pietro','Vignolo Silvio','Rebagliati Marco'
    ];

    v_tipi_var TEXT[] := ARRAY[
        'Vendita','Successione','Frazionamento','Divisione',
        'Trasferimento','Acquisto','Variazione','Altro'
    ];

    -- === COMUNI (10) ===
    v_comuni_nomi TEXT[] := ARRAY[
        'Savona','Cairo Montenotte','Carcare','Altare','Millesimo',
        'Finale Ligure','Albenga','Loano','Vado Ligure','Celle Ligure'
    ];
    v_comuni_cod TEXT[] := ARRAY[
        'I480','B369','B748','A226','F213','D600','A145','E635','L527','C443'
    ];
    v_comuni_note TEXT[] := ARRAY[
        'Capoluogo di provincia','Principale centro Val Bormida',
        'Centro commerciale Valle Bormida','Tradizione vetraria storica',
        'Borgo medievale Val Bormida','Centro turistico riviera',
        'Città romana, centro storico','Comune costiero',
        'Porto industriale','Comune costiero riviera'
    ];

    -- === CONSULTAZIONI (dati espliciti) ===
    v_cons_richiedenti TEXT[] := ARRAY[
        'Studio Legale Bruzzone & Ferrando','Geom. Riccardo Pastorino',
        'Arch. Luisa Colombo','Tribunale Civile di Savona',
        'Sig. Antonio Rolando','Studio Notarile Gaggero',
        'Comune di Albenga — Ufficio Tecnico','Dott.ssa Elena Moretti',
        'Sig.ra Marina Saccone','Studio Legale Romano & Associati',
        'Soprintendenza Archeologia Liguria','Sig. Franco Bruzzone',
        'Istituto Storico della Resistenza SV','Geom. Paolo Anfossi',
        'Studio Legale Crovetto','Sig. Roberto Gandolfo',
        'Arch. Studio Pellegrino','Comune di Finale Ligure',
        'Dott. Sergio Vignolo','Sig.ra Caterina Parodi',
        'Università di Genova — Dip. Storia','Avv. Marco Bolla',
        'Comune di Cairo Montenotte','Geom. Franco Traverso',
        'Sig. Luigi Rebagliati','Agenzia delle Entrate — Uff. Savona',
        'Studio Notarile Ferretti','Sig.ra Rosa Bonino',
        'Ricercatore Dott. Andrea Siri','Comune di Loano — UT',
        'Banca CR Savona — Ufficio Legale','Dott. Emilio Ferroni',
        'Arch. Claudia Astengo','Sig. Pietro Siffreddi',
        'Comune di Vado Ligure','Notaio Costantino Rollero',
        'Sig.ra Angela Morando','Studio Tecnico Assoc. Ferrero',
        'Museo Civico di Savona','Dott.ssa Ida Ghiso',
        'Geom. Giovanni Ponzo','Comune di Millesimo',
        'Sig. Battista Canepa','Avv. Rosaria Calcagno',
        'Studio Legale Briasco','INPS — Sede di Savona',
        'Sig. Angelo Oddone','Arch. Paolo Bertonasco',
        'Istituto Scolastico Liceo Chiabrera SV','Sig.ra Teresa Capurro',
        'Associazione Culturale Val Bormida','Dott. Mario Marenco',
        'Comune di Altare','Geom. Roberto Peluffo',
        'Studio Notarile Casanova','Sig.ra Luisa Lavaggi',
        'Banca Monte dei Paschi SV','Dott. Silvio Cuneo',
        'Archivio di Stato di Genova','Sig. Giovanni Baracco'
    ];
    v_cons_doc_id TEXT[] := ARRAY[
        'CI AX1234567','CI BX9876543','PA0012345','Ufficio Cancelleria',
        'CI CX4567891','PA0055678','Ufficio Pubblico','CI DX7654321',
        'CI EX3210987','PI 01234567890','Ufficio Pubblico','CI FX6543210',
        'PI 00987654321','CI GX1122334','CI HX5566778','CI IX9900112',
        'PI 02233445566','Ufficio Pubblico','CI JX1234500','CI KX5678900',
        'PI 03344556677','CI LX9012345','Ufficio Pubblico','CI MX2345678',
        'CI NX8901234','PI 04455667788','PA0099887','CI OX3456789',
        'CI PX7890123','Ufficio Pubblico','PI 05566778899','CI QX4567890',
        'PA0011223','CI RX8901234','Ufficio Pubblico','PA0022334',
        'CI SX5678901','PI 06677889900','CI TX9012345','CI UX3456789',
        'CI VX7890123','Ufficio Pubblico','CI WX1234567','CI XX5678901',
        'PA0033445','PI 07788990011','CI YY9012345','PA0044556',
        'PI 08899001122','CI ZA1234567','PI 09900112233','CI ZB5678901',
        'PI 01011223344','Ufficio Pubblico','PA0055667','CI ZC3456789',
        'PI 02122334455','CI ZD7890123','PI 03233445566','CI ZE1234567'
    ];
    v_cons_motivazioni TEXT[] := ARRAY[
        'Verifica titoli proprietà per successione',
        'Frazionamento catastale immobile',
        'Ricerca storica edifici industriali',
        'Accertamento titoli per lite ereditaria',
        'Ricerca antenati — genealogia familiare',
        'Rogito compravendita immobile',
        'Verifica confini catastali centro storico',
        'Tesi dottorato — proprietà fondiarie Liguria 1870–1920',
        'Verifica atti notarili avo',
        'Perizia immobiliare',
        'Catalogazione patrimonio industriale storico',
        'Verifica intestazione immobile ereditato',
        'Ricerca beni periodo 1940–45',
        'Aggiornamento planimetrie catastali',
        'Consulenza tecnica divisione ereditaria',
        'Verifica proprietà zona industriale',
        'Progetto recupero borgo storico',
        'Variante PRG — verifica catastale',
        'Ricerca proprietà ai fini fiscali',
        'Verifica ipoteca immobiliare'
    ];
    v_cons_funzionari TEXT[] := ARRAY[
        'Dott.ssa Anfossi Carla','Dott. Ferretti Mario',
        'Dott.ssa Vignolo Laura','Dott. Saccone Paolo'
    ];

    -- === LOOP VARIABLES ===
    i_com  INTEGER;
    i_pos  INTEGER;
    i_loc  INTEGER;
    i_par  INTEGER;
    i_imm  INTEGER;
    i_cons INTEGER;

    v_com_id  INTEGER;
    v_tmp_id  INTEGER;

    v_pos_ids  INTEGER[];
    v_loc_ids  INTEGER[];
    v_par_ids  INTEGER[];
    v_par_inattive INTEGER[];
    v_par_attive   INTEGER[];

    v_par_id   INTEGER;
    v_par_prev INTEGER;
    v_var_id   INTEGER;

    v_cognome    TEXT; v_nome TEXT; v_patern TEXT;
    v_cogn_nome  TEXT; v_nome_compl TEXT;
    v_loc_nome   TEXT; v_loc_tipo_id INTEGER; v_loc_civico TEXT;
    v_par_tipo   TEXT; v_par_stato TEXT;
    v_par_data_imp DATE; v_par_data_ch DATE;
    v_par_numero INTEGER;
    v_imm_natura TEXT; v_imm_class TEXT;
    v_tipo_var   TEXT; v_tipo_contr TEXT;
    v_anno_var   INTEGER;
    v_notaio     TEXT; v_rep TEXT;
    v_n_pos      INTEGER; v_n_loc INTEGER;
    v_n_inattive INTEGER; v_n_attive INTEGER;
    v_cons_data  DATE; v_mat TEXT;

BEGIN
    RAISE NOTICE '[DEMO v2] Inizio caricamento dataset ampliato provincia di Savona...';

    -- ============================================================
    -- 0. SELF-HEAL SCHEMA (v1.6.1+ usa tipologia_stradale)
    --    Se il DB ha ancora la vecchia colonna tipo_id con vincolo
    --    NOT NULL, lo rilassiamo per permettere agli INSERT seguenti
    --    (che non specificano tipo_id) di completare. La colonna non
    --    viene rimossa: lo farà eventualmente la migrazione 10.
    -- ============================================================
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = current_schema()
          AND table_name = 'localita'
          AND column_name = 'tipo_id'
          AND is_nullable = 'NO'
    ) THEN
        RAISE NOTICE '[DEMO v2] Rilascio NOT NULL su localita.tipo_id (schema legacy).';
        ALTER TABLE localita ALTER COLUMN tipo_id DROP NOT NULL;
    END IF;

    -- ============================================================
    -- 1. TIPO_LOCALITA
    -- ============================================================
    INSERT INTO tipo_localita (nome, descrizione) VALUES
        ('Via',       'Strada urbana o extraurbana'),
        ('Piazza',    'Spazio aperto urbano'),
        ('Regione',   'Area geografica rurale o collinare'),
        ('Borgata',   'Agglomerato di case rurale'),
        ('Corso',     'Arteria principale urbana'),
        ('Frazione',  'Nucleo abitato dipendente da comune'),
        ('Lungomare', 'Passeggiata costiera'),
        ('Vico',      'Vicolo stretto urbano')
    ON CONFLICT (nome) DO NOTHING;

    SELECT id INTO tl_via FROM tipo_localita WHERE nome = 'Via';
    SELECT id INTO tl_pza FROM tipo_localita WHERE nome = 'Piazza';
    SELECT id INTO tl_reg FROM tipo_localita WHERE nome = 'Regione';
    SELECT id INTO tl_bor FROM tipo_localita WHERE nome = 'Borgata';
    SELECT id INTO tl_fra FROM tipo_localita WHERE nome = 'Frazione';
    SELECT id INTO tl_lng FROM tipo_localita WHERE nome = 'Lungomare';
    SELECT id INTO tl_cso FROM tipo_localita WHERE nome = 'Corso';
    SELECT id INTO tl_vco FROM tipo_localita WHERE nome = 'Vico';

    -- ============================================================
    -- 2. LOOP PRINCIPALE: per ogni comune
    -- ============================================================
    FOR i_com IN 1..10 LOOP

        -- ---- COMUNE ----
        INSERT INTO comune (nome, provincia, regione, codice_catastale, note)
        VALUES (
            v_comuni_nomi[i_com], 'SV', 'Liguria',
            v_comuni_cod[i_com], v_comuni_note[i_com]
        )
        ON CONFLICT (nome) DO NOTHING;

        SELECT id INTO v_com_id FROM comune WHERE nome = v_comuni_nomi[i_com];
        RAISE NOTICE '[DEMO v2] >>> Comune: % (id=%)', v_comuni_nomi[i_com], v_com_id;

        -- ============================================================
        -- 2a. POSSESSORI (12 per comune)
        -- ============================================================
        v_pos_ids := ARRAY[]::INTEGER[];

        FOR i_pos IN 1..12 LOOP
            -- Cognome: scorre il pool evitando ripetizioni per comune
            v_cognome := v_cognomi[((i_com - 1) * 12 + i_pos - 1) % array_length(v_cognomi, 1) + 1];

            -- Nome: alterna M/F
            IF i_pos % 2 = 1 THEN
                v_nome := v_nomi_m[(i_pos - 1) % array_length(v_nomi_m, 1) + 1];
            ELSE
                v_nome := v_nomi_f[(i_pos / 2 - 1) % array_length(v_nomi_f, 1) + 1];
            END IF;

            v_patern     := v_paternita[(i_pos - 1) % array_length(v_paternita, 1) + 1];
            v_cogn_nome  := v_cognome || ' ' || v_nome;
            v_nome_compl := v_cogn_nome || ' ' || v_patern;

            -- Controlla esistenza (evita duplicati su riesecuzione)
            SELECT id INTO v_tmp_id FROM possessore
            WHERE comune_id = v_com_id AND nome_completo = v_nome_compl;

            IF v_tmp_id IS NULL THEN
                INSERT INTO possessore (comune_id, cognome_nome, paternita, nome_completo, attivo)
                VALUES (v_com_id, v_cogn_nome, v_patern, v_nome_compl, i_pos % 10 <> 0)
                RETURNING id INTO v_tmp_id;
            END IF;

            v_pos_ids := array_append(v_pos_ids, v_tmp_id);
        END LOOP;

        v_n_pos := array_length(v_pos_ids, 1);
        RAISE NOTICE '[DEMO v2]   Possessori: %', v_n_pos;

        -- ============================================================
        -- 2b. LOCALITA (8 per comune)
        --     3 vie + 2 piazze + 2 regioni + 1 borgata
        -- ============================================================
        v_loc_ids := ARRAY[]::INTEGER[];

        -- 3 VIE (civico incorporato nel nome da v1.6.1)
        FOR i_loc IN 1..3 LOOP
            v_loc_nome   := v_vie_nomi[((i_com - 1) * 3 + i_loc - 1) % array_length(v_vie_nomi, 1) + 1];
            v_loc_civico := (i_loc * 7)::TEXT;
            v_loc_nome := CONCAT(v_loc_nome, ' ', v_loc_civico);

            SELECT id INTO v_tmp_id FROM localita
            WHERE comune_id = v_com_id AND nome = v_loc_nome;

            IF v_tmp_id IS NULL THEN
                INSERT INTO localita (comune_id, nome, tipologia_stradale)
                VALUES (v_com_id, v_loc_nome, 'Via')
                RETURNING id INTO v_tmp_id;
            END IF;
            v_loc_ids := array_append(v_loc_ids, v_tmp_id);
        END LOOP;

        -- 2 PIAZZE
        FOR i_loc IN 1..2 LOOP
            v_loc_nome := v_piazze_nomi[((i_com - 1) * 2 + i_loc - 1) % array_length(v_piazze_nomi, 1) + 1];

            SELECT id INTO v_tmp_id FROM localita
            WHERE comune_id = v_com_id AND nome = v_loc_nome;

            IF v_tmp_id IS NULL THEN
                INSERT INTO localita (comune_id, nome, tipologia_stradale)
                VALUES (v_com_id, v_loc_nome, 'Piazza')
                RETURNING id INTO v_tmp_id;
            END IF;
            v_loc_ids := array_append(v_loc_ids, v_tmp_id);
        END LOOP;

        -- 2 REGIONI
        FOR i_loc IN 1..2 LOOP
            v_loc_nome := v_regioni_nomi[((i_com - 1) * 2 + i_loc - 1) % array_length(v_regioni_nomi, 1) + 1];

            SELECT id INTO v_tmp_id FROM localita
            WHERE comune_id = v_com_id AND nome = v_loc_nome;

            IF v_tmp_id IS NULL THEN
                INSERT INTO localita (comune_id, nome, tipologia_stradale)
                VALUES (v_com_id, v_loc_nome, 'Regione')
                RETURNING id INTO v_tmp_id;
            END IF;
            v_loc_ids := array_append(v_loc_ids, v_tmp_id);
        END LOOP;

        -- 1 BORGATA
        v_loc_nome := v_borgate_nomi[(i_com - 1) % array_length(v_borgate_nomi, 1) + 1];

        SELECT id INTO v_tmp_id FROM localita
        WHERE comune_id = v_com_id AND nome = v_loc_nome;

        IF v_tmp_id IS NULL THEN
            INSERT INTO localita (comune_id, nome, tipologia_stradale)
            VALUES (v_com_id, v_loc_nome, 'Borgata')
            RETURNING id INTO v_tmp_id;
        END IF;
        v_loc_ids := array_append(v_loc_ids, v_tmp_id);

        v_n_loc := array_length(v_loc_ids, 1);  -- = 8
        RAISE NOTICE '[DEMO v2]   Località: %', v_n_loc;

        -- ============================================================
        -- 2c. PARTITE (30 per comune)
        --     Ogni 6a = inattiva con data_chiusura, le altre attive.
        --     Numeri: (i_com * 1000) + i_par  per evitare collisioni.
        -- ============================================================
        v_par_ids      := ARRAY[]::INTEGER[];
        v_par_inattive := ARRAY[]::INTEGER[];
        v_par_attive   := ARRAY[]::INTEGER[];

        FOR i_par IN 1..30 LOOP
            v_par_numero := (i_com * 1000) + i_par;

            -- tipo
            v_par_tipo := CASE WHEN i_par % 8 = 0 THEN 'secondaria' ELSE 'principale' END;

            -- data_impianto: distribuita su 1870–1970
            v_par_data_imp := ('1870-01-01'::DATE +
                ((i_par - 1) * 4 + (i_com - 1) * 12 || ' months')::INTERVAL)::DATE;
            -- Evita date future
            IF v_par_data_imp > '1970-12-31'::DATE THEN
                v_par_data_imp := ('1930-01-01'::DATE + (i_par || ' months')::INTERVAL)::DATE;
            END IF;

            -- Ogni 6a partita è inattiva
            IF i_par % 6 = 0 THEN
                v_par_data_ch := (v_par_data_imp + ((8 + i_par % 20) || ' years')::INTERVAL)::DATE;
                IF v_par_data_ch > '1985-12-31'::DATE THEN
                    v_par_data_ch := '1984-06-01'::DATE;
                END IF;

                SELECT id INTO v_par_id FROM partita
                WHERE comune_id = v_com_id AND numero_partita = v_par_numero AND suffisso_partita IS NULL;

                IF v_par_id IS NULL THEN
                    INSERT INTO partita
                        (comune_id, numero_partita, tipo, data_impianto, stato, data_chiusura)
                    VALUES
                        (v_com_id, v_par_numero, v_par_tipo, v_par_data_imp, 'inattiva', v_par_data_ch)
                    RETURNING id INTO v_par_id;
                END IF;
                v_par_inattive := array_append(v_par_inattive, v_par_id);

            ELSE
                SELECT id INTO v_par_id FROM partita
                WHERE comune_id = v_com_id AND numero_partita = v_par_numero AND suffisso_partita IS NULL;

                IF v_par_id IS NULL THEN
                    INSERT INTO partita
                        (comune_id, numero_partita, tipo, data_impianto, stato)
                    VALUES
                        (v_com_id, v_par_numero, v_par_tipo, v_par_data_imp, 'attiva')
                    RETURNING id INTO v_par_id;
                END IF;
                v_par_attive := array_append(v_par_attive, v_par_id);
            END IF;

            v_par_ids := array_append(v_par_ids, v_par_id);
        END LOOP;

        -- Alcune partite con suffisso (bis / ter) per varietà
        FOR i_par IN 1..3 LOOP
            v_par_numero := (i_com * 1000) + i_par;  -- stessa base, suffisso diverso

            SELECT id INTO v_par_id FROM partita
            WHERE comune_id = v_com_id AND numero_partita = v_par_numero AND suffisso_partita = 'bis';

            IF v_par_id IS NULL THEN
                INSERT INTO partita
                    (comune_id, numero_partita, suffisso_partita, tipo, data_impianto, stato)
                VALUES
                    (v_com_id, v_par_numero, 'bis', 'secondaria',
                     ('1950-01-01'::DATE + (i_par * 6 || ' months')::INTERVAL)::DATE, 'attiva')
                RETURNING id INTO v_par_id;
            END IF;
            v_par_attive := array_append(v_par_attive, v_par_id);
            v_par_ids    := array_append(v_par_ids, v_par_id);
        END LOOP;

        v_n_inattive := array_length(v_par_inattive, 1);
        v_n_attive   := array_length(v_par_attive, 1);
        RAISE NOTICE '[DEMO v2]   Partite: % (attive=%, inattive=%)',
            array_length(v_par_ids, 1), v_n_attive, v_n_inattive;

        -- ============================================================
        -- 2d. IMMOBILI (2 per partita)
        -- ============================================================
        FOR i_par IN 1..array_length(v_par_ids, 1) LOOP
            v_par_id := v_par_ids[i_par];
            IF v_par_id IS NULL THEN CONTINUE; END IF;

            -- Immobile principale
            v_imm_natura := v_nature[(i_par - 1) % array_length(v_nature, 1) + 1];
            v_imm_class  := v_classif[(i_par - 1) % array_length(v_classif, 1) + 1];

            INSERT INTO immobile
                (partita_id, localita_id, natura, classificazione, consistenza, numero_piani, numero_vani)
            VALUES (
                v_par_id,
                v_loc_ids[(i_par - 1) % v_n_loc + 1],
                v_imm_natura,
                v_imm_class,
                (50 + (i_par * 17 + i_com * 23) % 300) || ' mq',
                1 + (i_par % 3),
                2 + (i_par % 8)
            );

            -- Immobile secondario (pertinenza o terreno)
            v_imm_natura := v_nature[i_par % array_length(v_nature, 1) + 1];
            v_imm_class  := v_classif[i_par % array_length(v_classif, 1) + 1];

            INSERT INTO immobile
                (partita_id, localita_id, natura, classificazione, consistenza)
            VALUES (
                v_par_id,
                v_loc_ids[i_par % v_n_loc + 1],
                v_imm_natura,
                v_imm_class,
                (20 + (i_par * 11 + i_com * 13) % 200) || ' mq'
            );
        END LOOP;

        RAISE NOTICE '[DEMO v2]   Immobili inseriti per comune %', v_comuni_nomi[i_com];

        -- ============================================================
        -- 2e. PARTITA_POSSESSORE
        -- ============================================================
        FOR i_par IN 1..array_length(v_par_ids, 1) LOOP
            v_par_id := v_par_ids[i_par];
            IF v_par_id IS NULL THEN CONTINUE; END IF;

            -- Possessore primario
            INSERT INTO partita_possessore
                (partita_id, possessore_id, tipo_partita, titolo, quota)
            VALUES (
                v_par_id,
                v_pos_ids[(i_par - 1) % v_n_pos + 1],
                CASE WHEN i_par % 8 = 0 THEN 'secondaria' ELSE 'principale' END,
                'proprietà esclusiva',
                NULL
            )
            ON CONFLICT (partita_id, possessore_id) DO NOTHING;

            -- Comproprietà: ogni 4a partita ha un secondo possessore
            IF i_par % 4 = 0 THEN
                -- Secondo possessore (assicurandosi che sia diverso dal primo)
                INSERT INTO partita_possessore
                    (partita_id, possessore_id, tipo_partita, titolo, quota)
                VALUES (
                    v_par_id,
                    v_pos_ids[i_par % v_n_pos + 1],
                    CASE WHEN i_par % 8 = 0 THEN 'secondaria' ELSE 'principale' END,
                    'comproprietà',
                    '1/2'
                )
                ON CONFLICT (partita_id, possessore_id) DO NOTHING;

                -- Aggiorna il primo a comproprietà
                UPDATE partita_possessore
                SET titolo = 'comproprietà', quota = '1/2'
                WHERE partita_id = v_par_id
                  AND possessore_id = v_pos_ids[(i_par - 1) % v_n_pos + 1];
            END IF;

            -- Tre possessori: ogni 9a partita
            IF i_par % 9 = 0 THEN
                INSERT INTO partita_possessore
                    (partita_id, possessore_id, tipo_partita, titolo, quota)
                VALUES (
                    v_par_id,
                    v_pos_ids[(i_par + 3) % v_n_pos + 1],
                    'principale',
                    'comproprietà',
                    '1/3'
                )
                ON CONFLICT (partita_id, possessore_id) DO NOTHING;

                UPDATE partita_possessore
                SET quota = '1/3'
                WHERE partita_id = v_par_id
                  AND possessore_id IN (
                      v_pos_ids[(i_par - 1) % v_n_pos + 1],
                      v_pos_ids[i_par % v_n_pos + 1]
                  );
            END IF;
        END LOOP;

        -- ============================================================
        -- 2f. VARIAZIONI: inattive → attive + variazioni su attive
        -- ============================================================
        IF v_n_inattive IS NOT NULL AND v_n_inattive > 0 THEN
            FOR i_par IN 1..v_n_inattive LOOP
                v_par_prev := v_par_inattive[i_par];
                v_par_id   := v_par_attive[(i_par - 1) % v_n_attive + 1];

                v_tipo_var  := v_tipi_var[(i_par - 1) % array_length(v_tipi_var, 1) + 1];
                v_anno_var  := 1875 + (i_com * 9 + i_par * 7) % 110;
                v_notaio    := v_notai[(i_par + i_com - 2) % array_length(v_notai, 1) + 1];
                v_rep       := 'Rep.' || v_anno_var || '/' || (i_com * 100 + i_par * 11)::TEXT;

                INSERT INTO variazione
                    (partita_origine_id, partita_destinazione_id, tipo,
                     data_variazione, numero_riferimento, nominativo_riferimento)
                VALUES (
                    v_par_prev, v_par_id, v_tipo_var,
                    (v_anno_var || '-06-15')::DATE,
                    v_rep, 'Notaio ' || v_notaio
                )
                RETURNING id INTO v_var_id;

                v_tipo_contr := CASE v_tipo_var
                    WHEN 'Vendita'       THEN 'Atto di Compravendita'
                    WHEN 'Acquisto'      THEN 'Atto di Compravendita'
                    WHEN 'Successione'   THEN 'Dichiarazione di Successione'
                    WHEN 'Divisione'     THEN 'Atto di Divisione'
                    WHEN 'Frazionamento' THEN 'Atto di Divisione'
                    WHEN 'Trasferimento' THEN 'Atto di Compravendita'
                    ELSE 'Altro Atto Pubblico'
                END;

                INSERT INTO contratto
                    (variazione_id, tipo, data_contratto, notaio, repertorio, note)
                VALUES (
                    v_var_id, v_tipo_contr,
                    (v_anno_var || '-06-01')::DATE,
                    v_notaio, v_rep,
                    'Passaggio proprietà partita ' ||
                    (i_com * 1000 + i_par * 6) || ' — ' || v_comuni_nomi[i_com]
                );
            END LOOP;
        END IF;

        -- Variazioni extra su partite attive (acquisti / vendite puri)
        FOR i_par IN 1..4 LOOP
            IF array_length(v_par_attive, 1) >= i_par THEN
                v_par_id   := v_par_attive[i_par];
                v_tipo_var := CASE i_par % 3
                    WHEN 0 THEN 'Vendita'
                    WHEN 1 THEN 'Acquisto'
                    ELSE        'Variazione'
                END;
                v_anno_var := 1900 + (i_com * 6 + i_par * 13) % 80;
                v_notaio   := v_notai[(i_com + i_par - 1) % array_length(v_notai, 1) + 1];
                v_rep      := 'Prot.' || v_anno_var || '/' || (i_com * 50 + i_par * 7)::TEXT;

                INSERT INTO variazione
                    (partita_origine_id, tipo, data_variazione,
                     numero_riferimento, nominativo_riferimento)
                VALUES (
                    v_par_id, v_tipo_var,
                    (v_anno_var || '-09-20')::DATE,
                    v_rep, 'Notaio ' || v_notaio
                )
                RETURNING id INTO v_var_id;

                INSERT INTO contratto
                    (variazione_id, tipo, data_contratto, notaio, repertorio, note)
                VALUES (
                    v_var_id,
                    CASE v_tipo_var WHEN 'Variazione' THEN 'Altro Atto Pubblico'
                                    ELSE 'Atto di Compravendita' END,
                    (v_anno_var || '-09-10')::DATE,
                    v_notaio, v_rep,
                    v_tipo_var || ' — ' || v_comuni_nomi[i_com]
                );
            END IF;
        END LOOP;

        -- ============================================================
        -- 2g. REGISTRI PARTITE (2 per comune)
        -- ============================================================
        INSERT INTO registro_partite (comune_id, anno_impianto, numero_volumi, stato_conservazione)
        VALUES (
            v_com_id,
            1870 + (i_com * 3),
            2 + (i_com % 3),
            (ARRAY['Ottimo','Buono','Discreto','Deteriorato'])[i_com % 4 + 1]
        )
        ON CONFLICT (comune_id, anno_impianto) DO NOTHING;

        INSERT INTO registro_partite (comune_id, anno_impianto, numero_volumi, stato_conservazione)
        VALUES (
            v_com_id,
            1900 + (i_com * 4),
            1 + (i_com % 2),
            (ARRAY['Buono','Ottimo','Discreto','Buono'])[i_com % 4 + 1]
        )
        ON CONFLICT (comune_id, anno_impianto) DO NOTHING;

    END LOOP; -- fine loop comuni

    RAISE NOTICE '[DEMO v2] Loop comuni completato.';

    -- ============================================================
    -- 3. CONSULTAZIONI (60 records)
    -- ============================================================
    FOR i_cons IN 1..60 LOOP
        -- Data: distribuita negli ultimi 3 anni (2023–2025)
        v_cons_data := '2023-01-01'::DATE + ((i_cons - 1) * 18);
        IF v_cons_data > '2025-12-31'::DATE THEN
            v_cons_data := '2025-01-01'::DATE + ((i_cons - 1) * 5);
        END IF;

        v_mat := 'Partite ' || v_comuni_nomi[(i_cons - 1) % 10 + 1] || ' — ' ||
                 'fascicolo n.' || (1000 + i_cons * 3)::TEXT;

        INSERT INTO consultazione
            (data, richiedente, documento_identita, motivazione,
             materiale_consultato, funzionario_autorizzante)
        VALUES (
            v_cons_data,
            v_cons_richiedenti[i_cons],
            v_cons_doc_id[i_cons],
            v_cons_motivazioni[(i_cons - 1) % array_length(v_cons_motivazioni, 1) + 1],
            v_mat,
            v_cons_funzionari[(i_cons - 1) % array_length(v_cons_funzionari, 1) + 1]
        );
    END LOOP;

    RAISE NOTICE '[DEMO v2] Consultazioni inserite: 60';

    -- ============================================================
    -- 4. RIEPILOGO FINALE
    -- ============================================================
    RAISE NOTICE '============================================================';
    RAISE NOTICE '[DEMO v2] === DATASET AMPLIATO CARICATO CON SUCCESSO ===';
    RAISE NOTICE '  Comuni:        %', (SELECT COUNT(*) FROM comune);
    RAISE NOTICE '  Possessori:    %', (SELECT COUNT(*) FROM possessore);
    RAISE NOTICE '  Localita:      %', (SELECT COUNT(*) FROM localita);
    RAISE NOTICE '  Partite:       %', (SELECT COUNT(*) FROM partita);
    RAISE NOTICE '  - attive:      %', (SELECT COUNT(*) FROM partita WHERE stato='attiva');
    RAISE NOTICE '  - inattive:    %', (SELECT COUNT(*) FROM partita WHERE stato='inattiva');
    RAISE NOTICE '  Immobili:      %', (SELECT COUNT(*) FROM immobile);
    RAISE NOTICE '  Part.Possess.: %', (SELECT COUNT(*) FROM partita_possessore);
    RAISE NOTICE '  Variazioni:    %', (SELECT COUNT(*) FROM variazione);
    RAISE NOTICE '  Contratti:     %', (SELECT COUNT(*) FROM contratto);
    RAISE NOTICE '  Consultazioni: %', (SELECT COUNT(*) FROM consultazione);
    RAISE NOTICE '  Registri:      %', (SELECT COUNT(*) FROM registro_partite);
    RAISE NOTICE '============================================================';

END;
$$;

-- ============================================================
-- ESECUZIONE
-- ============================================================
DO $$
BEGIN
    RAISE NOTICE 'Avvio procedura carica_demo_savona_v2()...';
    CALL carica_demo_savona_v2();
END $$;
