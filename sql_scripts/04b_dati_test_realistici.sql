-- File: 04b_dati_test_realistici.sql
-- Script per l'inserimento di dati di test più realistici e diversificati.
-- Assicurarsi che lo schema e le tabelle base siano già stati creati.

SET search_path TO catasto, public;

-- Disabilitare temporaneamente i trigger di audit se l'inserimento massivo è troppo lento
-- SET session_replication_role = 'replica'; -- ATTENZIONE: Usare con cautela
BEGIN
RAISE NOTICE 'Inizio inserimento dati di test realistici...';

-- 1. COMUNI (Alcuni esempi liguri e italiani)
RAISE NOTICE 'Inserimento Comuni...';
INSERT INTO comune (nome, provincia, regione, codice_catastale, note) VALUES
('Savona', 'SV', 'Liguria', 'I480', 'Capoluogo di provincia'),
('Genova', 'GE', 'Liguria', 'D969', 'Capoluogo di regione'),
('Varazze', 'SV', 'Liguria', 'L675', 'Comune costiero'),
('Albenga', 'SV', 'Liguria', 'A145', 'Centro storico importante'),
('Cairo Montenotte', 'SV', 'Liguria', 'B369', 'Comune dell entroterra'),
('Sassello', 'SV', 'Liguria', 'I45S', 'Altro comune dell entroterra'), -- Codice catastale inventato se non noto
('Milano', 'MI', 'Lombardia', 'F205', 'Grande città'),
('Roma', 'RM', 'Lazio', 'H501', 'Capitale d Italia'),
('Altare', 'SV', 'Liguria', 'A226', NULL),
('Celle Ligure', 'SV', 'Liguria', 'C43L', NULL)
ON CONFLICT (codice_catastale) DO NOTHING; -- Evita errori se i comuni esistono già

-- 2. PERIODI STORICI (se non già presenti da altri script)
RAISE NOTICE 'Inserimento Periodi Storici...';
INSERT INTO periodo_storico (nome, anno_inizio, anno_fine, descrizione) VALUES
('Regno di Sardegna', 1815, 1861, 'Periodo pre-unitario'),
('Regno d''Italia', 1861, 1946, 'Dall''unità alla Repubblica'),
('Repubblica Italiana - Dopoguerra', 1946, 1970, 'Primo periodo repubblicano'),
('Repubblica Italiana - Recente', 1971, NULL, 'Periodo più recente')
ON CONFLICT (nome) DO NOTHING;

-- 3. POSSESSORI (Nomi italiani vari, con e senza dettagli)
RAISE NOTICE 'Inserimento Possessori...';
DO $$

END $$;
DECLARE
    comune_savona_id INTEGER;
    comune_varazze_id INTEGER;
    comune_genova_id INTEGER;
BEGIN
    SELECT id INTO comune_savona_id FROM comune WHERE codice_catastale = 'I480';
    SELECT id INTO comune_varazze_id FROM comune WHERE codice_catastale = 'L675';
    SELECT id INTO comune_genova_id FROM comune WHERE codice_catastale = 'D969';

    INSERT INTO possessore (comune_id, cognome, nome, paternita, nome_completo, codice_fiscale, data_nascita, luogo_nascita, indirizzo_residenza, note, attivo) VALUES
    (comune_savona_id, 'Rossi', 'Mario', 'Giovanni', 'Rossi Mario di Giovanni', 'RSSMRA70A01I480X', '1970-01-01', 'Savona', 'Via Roma 10, Savona', 'Primo proprietario storico', TRUE),
    (comune_varazze_id, 'Bianchi', 'Luisa', 'Carlo', 'Bianchi Luisa fu Carlo', 'BNCLSU75B41L675Y', '1975-02-01', 'Varazze', 'Corso Colombo 2, Varazze', NULL, TRUE),
    (comune_genova_id, 'Verdi', 'Giuseppe', NULL, 'Verdi Giuseppe', 'VRDGPP60C03D969Z', '1960-03-03', 'Genova', 'Piazza De Ferrari 5, Genova', 'Artista', TRUE),
    (comune_savona_id, 'Ferrari', 'Anna', 'Luigi', 'Ferrari Anna di Luigi', 'FRRNNA80D44I480A', '1980-04-04', 'Genova', 'Via Paleocapa 1, Savona', 'Erede Rossi', TRUE),
    (comune_varazze_id, 'Ricci', 'Paolo', NULL, 'Ricci Paolo', 'RCCPLA55E05L675B', '1955-05-05', 'Milano', 'Via Milano 15, Varazze', NULL, FALSE), -- Possessore non attivo
    (comune_genova_id, 'Gallo', 'Elena', 'Antonio', 'Gallo Elena fu Antonio', 'GLLLNE90F46D969C', '1990-06-06', 'Roma', 'Via XX Settembre 30, Genova', NULL, TRUE),
    (comune_savona_id, 'Conti', 'Roberto', 'Pietro', 'Conti Roberto di Pietro', 'CNTRRT65G07I480D', '1965-07-07', 'Savona', 'Piazza Sisto IV 2, Savona', 'Commerciante', TRUE),
    (comune_varazze_id, 'Bruno', 'Chiara', NULL, 'Bruno Chiara', 'BRNCRA88H48L675E', '1988-08-08', 'Varazze', 'Lungomare Europa 100, Varazze', NULL, TRUE),
    (comune_genova_id, 'Marino', 'Franco', 'Marco', 'Marino Franco di Marco', 'MRNFNC72I09D969F', '1972-09-09', 'Albenga', 'Corso Italia 50, Genova', 'Professionista', TRUE),
    (comune_savona_id, 'Greco', 'Sofia', NULL, 'Greco Sofia', 'GRCSFO95J50I480G', '1995-10-10', 'Sassello', 'Via Torino 22, Savona', NULL, TRUE);
END $$;

-- 4. LOCALITA (Nomi di vie e zone più realistici per i comuni inseriti)
RAISE NOTICE 'Inserimento Località...';
DO $$
DECLARE
    comune_savona_id INTEGER;
    comune_varazze_id INTEGER;
    comune_genova_id INTEGER;
    comune_albenga_id INTEGER;
    comune_cairo_id INTEGER;
BEGIN
    SELECT id INTO comune_savona_id FROM comune WHERE codice_catastale = 'I480';
    SELECT id INTO comune_varazze_id FROM comune WHERE codice_catastale = 'L675';
    SELECT id INTO comune_genova_id FROM comune WHERE codice_catastale = 'D969';
    SELECT id INTO comune_albenga_id FROM comune WHERE codice_catastale = 'A145';
    SELECT id INTO comune_cairo_id FROM comune WHERE codice_catastale = 'B369';

    INSERT INTO localita (comune_id, nome, tipo, civico, note) VALUES
    -- Savona
    (comune_savona_id, 'Roma', 'Via', '10', 'Centro città'),
    (comune_savona_id, 'Paleocapa', 'Via', '1', 'Zona Priamar'),
    (comune_savona_id, 'Sisto IV', 'Piazza', '2', 'Vicino al Duomo'),
    (comune_savona_id, 'Astengo', 'Via', '25A', NULL),
    (comune_savona_id, 'Guidobono', 'Corso', '15', NULL),
    (comune_savona_id, 'Lavagnola', 'Frazione', NULL, 'Periferia collinare'),
    -- Varazze
    (comune_varazze_id, 'Colombo', 'Corso', '2', 'Fronte mare'),
    (comune_varazze_id, 'Milano', 'Via', '15', 'Zona residenziale'),
    (comune_varazze_id, 'Europa', 'Lungomare', '100', NULL),
    (comune_varazze_id, 'Casanova', 'Frazione', NULL, 'Entroterra Varazze'),
    -- Genova
    (comune_genova_id, 'De Ferrari', 'Piazza', '5', 'Piazza principale'),
    (comune_genova_id, 'XX Settembre', 'Via', '30', 'Via commerciale'),
    (comune_genova_id, 'Garibaldi', 'Via', '12', 'Strada Nuova, Palazzi dei Rolli'),
    (comune_genova_id, 'Nervi', 'Quartiere', NULL, 'Zona Levante'),
    -- Albenga
    (comune_albenga_id, 'Martiri della Libertà', 'Piazza', '1', 'Centro Storico'),
    (comune_albenga_id, 'Aurelia', 'Via', '255', 'Strada statale'),
    -- Cairo Montenotte
    (comune_cairo_id, 'Roma', 'Via', '110', 'Centro'),
    (comune_cairo_id, 'Bragno', 'Frazione', NULL, 'Zona industriale');
END $$;

-- 5. PARTITE, IMMOBILI, PARTITA_POSSESSORE (Più complesse)
RAISE NOTICE 'Inserimento Partite, Immobili e legami...';
DO $$
DECLARE
    -- ID Comuni
    com_sv INTEGER; com_vr INTEGER; com_ge INTEGER; com_al INTEGER; com_ca INTEGER;
    -- ID Possessori (ipotizziamo di conoscerli o recuperarli)
    -- Rossi Mario (SV), Bianchi Luisa (VR), Verdi Giuseppe (GE), Ferrari Anna (SV), Conti Roberto (SV), Gallo Elena (GE)
    p_rossi INTEGER; p_bianchi INTEGER; p_verdi INTEGER; p_ferrari INTEGER; p_conti INTEGER; p_gallo INTEGER;
    -- ID Località (ipotizziamo)
    loc_sv_roma10 INTEGER; loc_sv_paleo1 INTEGER; loc_vr_col2 INTEGER; loc_ge_deF5 INTEGER;
    -- ID Partite create
    partita1_id INTEGER; partita2_id INTEGER; partita3_id INTEGER; partita4_id INTEGER; partita5_id INTEGER;
BEGIN
    SELECT id INTO com_sv FROM comune WHERE nome = 'Savona';
    SELECT id INTO com_vr FROM comune WHERE nome = 'Varazze';
    SELECT id INTO com_ge FROM comune WHERE nome = 'Genova';
    SELECT id INTO com_al FROM comune WHERE nome = 'Albenga';
    SELECT id INTO com_ca FROM comune WHERE nome = 'Cairo Montenotte';

    SELECT id INTO p_rossi FROM possessore WHERE nome_completo LIKE 'Rossi Mario%';
    SELECT id INTO p_bianchi FROM possessore WHERE nome_completo LIKE 'Bianchi Luisa%';
    SELECT id INTO p_verdi FROM possessore WHERE nome_completo LIKE 'Verdi Giuseppe%';
    SELECT id INTO p_ferrari FROM possessore WHERE nome_completo LIKE 'Ferrari Anna%';
    SELECT id INTO p_conti FROM possessore WHERE nome_completo LIKE 'Conti Roberto%';
    SELECT id INTO p_gallo FROM possessore WHERE nome_completo LIKE 'Gallo Elena%';

    SELECT id INTO loc_sv_roma10 FROM localita WHERE comune_id = com_sv AND nome = 'Roma' AND civico = '10';
    SELECT id INTO loc_sv_paleo1 FROM localita WHERE comune_id = com_sv AND nome = 'Paleocapa' AND civico = '1';
    SELECT id INTO loc_vr_col2 FROM localita WHERE comune_id = com_vr AND nome = 'Colombo' AND civico = '2';
    SELECT id INTO loc_ge_deF5 FROM localita WHERE comune_id = com_ge AND nome = 'De Ferrari' AND civico = '5';

    -- Partita 1 (Savona, Rossi Mario, appartamento e box)
    INSERT INTO partita (comune_id, numero_partita, tipo, data_impianto, stato)
    VALUES (com_sv, 101, 'Urbano', '1965-03-15', 'Attiva') RETURNING id INTO partita1_id;
    INSERT INTO immobile (partita_id, localita_id, natura, classificazione, consistenza, numero_vani, numero_piani, note) VALUES
    (partita1_id, loc_sv_roma10, 'Abitazione', 'A/2', '120 mq', 6, 3, 'Appartamento signorile'),
    (partita1_id, loc_sv_roma10, 'Autorimessa', 'C/6', '18 mq', 1, -1, 'Box auto pertinenziale');
    INSERT INTO partita_possessore (partita_id, possessore_id, titolo_possesso, quota, data_inizio_possesso) VALUES
    (partita1_id, p_rossi, 'Proprietà', '1/1', '1965-03-15');

    -- Partita 2 (Varazze, Bianchi Luisa, villa)
    INSERT INTO partita (comune_id, numero_partita, tipo, data_impianto, stato)
    VALUES (com_vr, 201, 'Urbano', '1978-09-20', 'Attiva') RETURNING id INTO partita2_id;
    INSERT INTO immobile (partita_id, localita_id, natura, classificazione, consistenza, numero_vani, numero_piani) VALUES
    (partita2_id, loc_vr_col2, 'Villa', 'A/7', '250 mq', 10, 2);
    INSERT INTO partita_possessore (partita_id, possessore_id, titolo_possesso, quota, data_inizio_possesso) VALUES
    (partita2_id, p_bianchi, 'Proprietà', '1/1', '1978-09-20');

    -- Partita 3 (Genova, Verdi e Gallo comproprietà, ufficio)
    INSERT INTO partita (comune_id, numero_partita, tipo, data_impianto, stato)
    VALUES (com_ge, 301, 'Urbano', '1992-01-10', 'Attiva') RETURNING id INTO partita3_id;
    INSERT INTO immobile (partita_id, localita_id, natura, classificazione, consistenza, numero_vani) VALUES
    (partita3_id, loc_ge_deF5, 'Ufficio', 'A/10', '80 mq', 4);
    INSERT INTO partita_possessore (partita_id, possessore_id, titolo_possesso, quota, data_inizio_possesso) VALUES
    (partita3_id, p_verdi, 'Comproprietà', '1/2', '1992-01-10'),
    (partita3_id, p_gallo, 'Comproprietà', '1/2', '1995-05-20'); -- Gallo entra dopo

    -- Partita 4 (Savona, Rossi la vende a Ferrari, poi Ferrari la vende a Conti)
    INSERT INTO partita (comune_id, numero_partita, tipo, data_impianto, stato, data_chiusura)
    VALUES (com_sv, 102, 'Urbano', '1980-06-01', 'Soppressa', '2005-12-31') RETURNING id INTO partita4_id;
    INSERT INTO immobile (partita_id, localita_id, natura, classificazione, consistenza, numero_vani) VALUES
    (partita4_id, loc_sv_paleo1, 'Negozio', 'C/1', '60 mq', 2);
    INSERT INTO partita_possessore (partita_id, possessore_id, titolo_possesso, quota, data_inizio_possesso, data_fine_possesso) VALUES
    (partita4_id, p_rossi, 'Proprietà', '1/1', '1980-06-01', '1998-07-15'); -- Rossi vende
    -- Inserire la variazione e il nuovo possessore tramite la procedura se possibile, o manualmente per test
    -- Per ora, inseriamo manualmente il nuovo possessore su questa stessa partita (non ideale, ma per dati di test)
    INSERT INTO partita_possessore (partita_id, possessore_id, titolo_possesso, quota, data_inizio_possesso, data_fine_possesso) VALUES
    (partita4_id, p_ferrari, 'Proprietà', '1/1', '1998-07-16', '2005-12-30'); -- Ferrari vende

    -- Partita 5 (Nuova partita per Conti dopo acquisto da Ferrari)
    -- Questo simulerebbe il risultato di un passaggio di proprietà che sopprime la vecchia e ne crea una nuova.
    INSERT INTO partita (comune_id, numero_partita, tipo, data_impianto, stato)
    VALUES (com_sv, 103, 'Urbano', '2005-12-31', 'Attiva') RETURNING id INTO partita5_id;
    -- Stesso immobile della partita 4, ma ora sulla partita 5
    INSERT INTO immobile (partita_id, localita_id, natura, classificazione, consistenza, numero_vani) VALUES
    (partita5_id, loc_sv_paleo1, 'Negozio', 'C/1', '60 mq', 2);
    INSERT INTO partita_possessore (partita_id, possessore_id, titolo_possesso, quota, data_inizio_possesso) VALUES
    (partita5_id, p_conti, 'Proprietà', '1/1', '2005-12-31');

END $$;

-- 6. VARIAZIONI e CONTRATTI (Esempi)
RAISE NOTICE 'Inserimento Variazioni e Contratti...';
DO $$
DECLARE
    -- ID Partite
    p4_id INTEGER; p5_id INTEGER;
    -- ID Possessori
    p_rossi_id INTEGER; p_ferrari_id INTEGER; p_conti_id INTEGER;
    var1_id INTEGER; var2_id INTEGER;
BEGIN
    SELECT id INTO p4_id FROM partita WHERE comune_id = (SELECT id FROM comune WHERE nome='Savona') AND numero_partita = 102;
    SELECT id INTO p5_id FROM partita WHERE comune_id = (SELECT id FROM comune WHERE nome='Savona') AND numero_partita = 103;
    SELECT id INTO p_rossi_id FROM possessore WHERE nome_completo LIKE 'Rossi Mario%';
    SELECT id INTO p_ferrari_id FROM possessore WHERE nome_completo LIKE 'Ferrari Anna%';
    SELECT id INTO p_conti_id FROM possessore WHERE nome_completo LIKE 'Conti Roberto%';

    -- Variazione 1: Rossi vende a Ferrari (sulla partita 102 che viene soppressa)
    -- Questa è una semplificazione, idealmente la procedura di passaggio gestisce la creazione/soppressione
    INSERT INTO variazione (partita_origine_id, tipo, data_variazione, numero_riferimento, nominativo_riferimento, note)
    VALUES (p4_id, 'Compravendita', '1998-07-15', 'Rep. 12345', 'Notaio Rossi', 'Passaggio da Rossi a Ferrari') RETURNING id INTO var1_id;
    INSERT INTO contratto (variazione_id, tipo, data, notaio, repertorio_numero, note)
    VALUES (var1_id, 'Compravendita', '1998-07-10', 'Dott. Mario Rossi', '12345', 'Atto di compravendita registrato');
    -- Qui la procedura aggiornerebbe partita_possessore e lo stato della partita p4_id

    -- Variazione 2: Ferrari vende a Conti (sopprime p4_id, crea p5_id)
    INSERT INTO variazione (partita_origine_id, partita_destinazione_id, tipo, data_variazione, numero_riferimento, nominativo_riferimento, note)
    VALUES (p4_id, p5_id, 'Compravendita', '2005-12-30', 'Rep. 67890', 'Notaio Bianchi', 'Passaggio da Ferrari a Conti con creazione nuova partita') RETURNING id INTO var2_id;
    INSERT INTO contratto (variazione_id, tipo, data, notaio, repertorio_numero, note)
    VALUES (var2_id, 'Compravendita', '2005-12-20', 'Dott. Luisa Bianchi', '67890', 'Atto di compravendita registrato');
    -- Aggiornamento stato partita p4_id a Soppressa (se non già fatto dal workflow)
    -- UPDATE partita SET stato = 'Soppressa', data_chiusura = '2005-12-30' WHERE id = p4_id;

END $$;

-- 7. REGISTRI (Esempio)
RAISE NOTICE 'Inserimento Registri...';
INSERT INTO registro_partite (nome, anno, volume, descrizione) VALUES
('Partite Urbane Savona 1960-1980', 1980, 'Vol. A', 'Registri delle partite urbane per il comune di Savona'),
('Partite Terreni Varazze 1970-1990', 1990, 'Vol. 1T', 'Registri dei terreni per il comune di Varazze')
ON CONFLICT (nome, anno, volume) DO NOTHING;

-- 8. CONSULTAZIONI (Esempio)
RAISE NOTICE 'Inserimento Consultazioni...';
INSERT INTO consultazione (data, richiedente, materiale_consultato, funzionario_autorizzante, note) VALUES
('2024-01-15', 'Studio Legale Bianchi', 'Partita SV/101, Mappe catastali zona Roma', 'Dott.ssa Verdi', 'Ricerca per successione Rossi'),
('2024-03-22', 'Geom. Ferrari', 'Partita VR/201 e documenti allegati', 'Sig. Rossi', 'Verifica confini proprietà Bianchi');

-- Riabilitare i trigger di audit se disabilitati
-- SET session_replication_role = 'origin';

RAISE NOTICE 'Inserimento dati di test realistici completato.';