-- ===========================================================================
-- Foliarium — Dati demo fittizi per il catasto storico
-- ===========================================================================
-- ATTENZIONE: Tutti i dati contenuti in questo file sono INVENTATI.
-- Nomi, cognomi, località e dettagli sono puramente di fantasia e non
-- corrispondono a persone, luoghi o atti reali.
-- ===========================================================================

SET search_path TO catasto, public;

-- ===== PERIODI STORICI =====
-- (già inseriti nello schema 02, ma li inseriamo con ON CONFLICT per sicurezza)
INSERT INTO periodo_storico (nome, anno_inizio, anno_fine, descrizione)
VALUES
    ('Regno di Sardegna', 1720, 1861, 'Periodo del Regno di Sardegna prima dell''unità d''Italia'),
    ('Regno d''Italia', 1861, 1946, 'Periodo del Regno d''Italia'),
    ('Repubblica Italiana', 1946, NULL, 'Periodo della Repubblica Italiana')
ON CONFLICT (nome) DO NOTHING;

-- ===== COMUNI (3 comuni liguri fittizi) =====
INSERT INTO comune (nome, provincia, regione, codice_catastale, data_istituzione, note, periodo_id)
VALUES
    ('Pietrachiara', 'Savona', 'Liguria', 'Z901', '1742-06-15',
     'Comune fittizio nella Val Bormida.',
     (SELECT id FROM periodo_storico WHERE nome = 'Regno di Sardegna')),
    ('Montalvento', 'Savona', 'Liguria', 'Z902', '1756-03-22',
     'Comune fittizio dell''entroterra savonese.',
     (SELECT id FROM periodo_storico WHERE nome = 'Regno di Sardegna')),
    ('Riofranco', 'Genova', 'Liguria', 'Z903', '1802-11-08',
     'Comune fittizio della riviera di levante.',
     (SELECT id FROM periodo_storico WHERE nome = 'Regno d''Italia'))
ON CONFLICT (nome) DO NOTHING;

-- ===== REGISTRI PARTITE =====
INSERT INTO registro_partite (comune_id, anno_impianto, numero_volumi, stato_conservazione)
VALUES
    ((SELECT id FROM comune WHERE nome = 'Pietrachiara'), 1870, 3, 'Buono'),
    ((SELECT id FROM comune WHERE nome = 'Montalvento'), 1875, 2, 'Discreto'),
    ((SELECT id FROM comune WHERE nome = 'Riofranco'), 1880, 4, 'Buono')
ON CONFLICT (comune_id, anno_impianto) DO NOTHING;

-- ===== REGISTRI MATRICOLE =====
INSERT INTO registro_matricole (comune_id, anno_impianto, numero_volumi, stato_conservazione)
VALUES
    ((SELECT id FROM comune WHERE nome = 'Pietrachiara'), 1870, 2, 'Buono'),
    ((SELECT id FROM comune WHERE nome = 'Montalvento'), 1875, 1, 'Mediocre'),
    ((SELECT id FROM comune WHERE nome = 'Riofranco'), 1880, 3, 'Buono')
ON CONFLICT (comune_id, anno_impianto) DO NOTHING;

-- ===== LOCALITA (4 località fittizie) =====
INSERT INTO localita (comune_id, nome, tipologia_stradale, civico)
VALUES
    ((SELECT id FROM comune WHERE nome = 'Pietrachiara'), 'Via dei Forni', 'Via', '12'),
    ((SELECT id FROM comune WHERE nome = 'Pietrachiara'), 'Piazza della Rocca', 'Piazza', '3'),
    ((SELECT id FROM comune WHERE nome = 'Montalvento'), 'Strada della Fontana', 'Strada', '7'),
    ((SELECT id FROM comune WHERE nome = 'Riofranco'), 'Salita del Castello', 'Salita', '1')
ON CONFLICT (comune_id, nome, civico) DO NOTHING;

-- ===== POSSESSORI (10 possessori con nomi inventati) =====
INSERT INTO possessore (comune_id, cognome_nome, paternita, nome_completo, attivo)
VALUES
    ((SELECT id FROM comune WHERE nome = 'Pietrachiara'), 'Dellavalle Giovanni', 'fu Pietro', 'Giovanni Dellavalle fu Pietro', TRUE),
    ((SELECT id FROM comune WHERE nome = 'Pietrachiara'), 'Boscherini Maria', 'fu Antonio', 'Maria Boscherini fu Antonio', TRUE),
    ((SELECT id FROM comune WHERE nome = 'Pietrachiara'), 'Traverso Luigi', 'fu Francesco', 'Luigi Traverso fu Francesco', TRUE),
    ((SELECT id FROM comune WHERE nome = 'Montalvento'), 'Canepa Rosa', 'fu Giuseppe', 'Rosa Canepa fu Giuseppe', TRUE),
    ((SELECT id FROM comune WHERE nome = 'Montalvento'), 'Ferrando Carlo', 'fu Bartolomeo', 'Carlo Ferrando fu Bartolomeo', TRUE),
    ((SELECT id FROM comune WHERE nome = 'Montalvento'), 'Parodi Angela', 'di Giacomo', 'Angela Parodi di Giacomo', TRUE),
    ((SELECT id FROM comune WHERE nome = 'Riofranco'), 'Zunino Stefano', 'fu Lorenzo', 'Stefano Zunino fu Lorenzo', TRUE),
    ((SELECT id FROM comune WHERE nome = 'Riofranco'), 'Bruzzone Caterina', 'fu Domenico', 'Caterina Bruzzone fu Domenico', TRUE),
    ((SELECT id FROM comune WHERE nome = 'Riofranco'), 'Ottonello Marco', 'fu Agostino', 'Marco Ottonello fu Agostino', TRUE),
    ((SELECT id FROM comune WHERE nome = 'Pietrachiara'), 'Ghiglione Teresa', 'fu Sebastiano', 'Teresa Ghiglione fu Sebastiano', FALSE);

-- ===== PARTITE CATASTALI (6 partite) =====
INSERT INTO partita (comune_id, numero_partita, data_impianto, stato, tipo)
VALUES
    ((SELECT id FROM comune WHERE nome = 'Pietrachiara'), 101, '1870-04-12', 'attiva', 'principale'),
    ((SELECT id FROM comune WHERE nome = 'Pietrachiara'), 102, '1870-04-12', 'attiva', 'principale'),
    ((SELECT id FROM comune WHERE nome = 'Pietrachiara'), 103, '1875-09-03', 'inattiva', 'principale'),
    ((SELECT id FROM comune WHERE nome = 'Montalvento'), 201, '1876-01-20', 'attiva', 'principale'),
    ((SELECT id FROM comune WHERE nome = 'Montalvento'), 202, '1876-01-20', 'attiva', 'secondaria'),
    ((SELECT id FROM comune WHERE nome = 'Riofranco'), 301, '1881-06-15', 'attiva', 'principale');

-- ===== LEGAMI PARTITA-POSSESSORE =====
INSERT INTO partita_possessore (partita_id, possessore_id, tipo_partita, titolo, quota)
VALUES
    -- Partita 101 Pietrachiara: Dellavalle Giovanni proprietario esclusivo
    ((SELECT id FROM partita WHERE numero_partita = 101 AND comune_id = (SELECT id FROM comune WHERE nome = 'Pietrachiara')),
     (SELECT id FROM possessore WHERE cognome_nome = 'Dellavalle Giovanni'),
     'principale', 'proprietà esclusiva', NULL),
    -- Partita 102 Pietrachiara: Boscherini e Traverso comproprietari
    ((SELECT id FROM partita WHERE numero_partita = 102 AND comune_id = (SELECT id FROM comune WHERE nome = 'Pietrachiara')),
     (SELECT id FROM possessore WHERE cognome_nome = 'Boscherini Maria'),
     'principale', 'comproprietà', '1/2'),
    ((SELECT id FROM partita WHERE numero_partita = 102 AND comune_id = (SELECT id FROM comune WHERE nome = 'Pietrachiara')),
     (SELECT id FROM possessore WHERE cognome_nome = 'Traverso Luigi'),
     'principale', 'comproprietà', '1/2'),
    -- Partita 103 Pietrachiara: Ghiglione Teresa (partita chiusa)
    ((SELECT id FROM partita WHERE numero_partita = 103 AND comune_id = (SELECT id FROM comune WHERE nome = 'Pietrachiara')),
     (SELECT id FROM possessore WHERE cognome_nome = 'Ghiglione Teresa'),
     'principale', 'proprietà esclusiva', NULL),
    -- Partita 201 Montalvento: Canepa Rosa e Ferrando Carlo
    ((SELECT id FROM partita WHERE numero_partita = 201 AND comune_id = (SELECT id FROM comune WHERE nome = 'Montalvento')),
     (SELECT id FROM possessore WHERE cognome_nome = 'Canepa Rosa'),
     'principale', 'comproprietà', '2/3'),
    ((SELECT id FROM partita WHERE numero_partita = 201 AND comune_id = (SELECT id FROM comune WHERE nome = 'Montalvento')),
     (SELECT id FROM possessore WHERE cognome_nome = 'Ferrando Carlo'),
     'principale', 'comproprietà', '1/3'),
    -- Partita 202 Montalvento: Parodi Angela (secondaria)
    ((SELECT id FROM partita WHERE numero_partita = 202 AND comune_id = (SELECT id FROM comune WHERE nome = 'Montalvento')),
     (SELECT id FROM possessore WHERE cognome_nome = 'Parodi Angela'),
     'secondaria', 'proprietà esclusiva', NULL),
    -- Partita 301 Riofranco: Zunino Stefano e Bruzzone Caterina
    ((SELECT id FROM partita WHERE numero_partita = 301 AND comune_id = (SELECT id FROM comune WHERE nome = 'Riofranco')),
     (SELECT id FROM possessore WHERE cognome_nome = 'Zunino Stefano'),
     'principale', 'comproprietà', '1/2'),
    ((SELECT id FROM partita WHERE numero_partita = 301 AND comune_id = (SELECT id FROM comune WHERE nome = 'Riofranco')),
     (SELECT id FROM possessore WHERE cognome_nome = 'Bruzzone Caterina'),
     'principale', 'comproprietà', '1/2');

-- ===== IMMOBILI (6 immobili) =====
INSERT INTO immobile (partita_id, localita_id, natura, numero_piani, numero_vani, consistenza, classificazione)
VALUES
    -- Casa in Via dei Forni, Pietrachiara (partita 101)
    ((SELECT id FROM partita WHERE numero_partita = 101 AND comune_id = (SELECT id FROM comune WHERE nome = 'Pietrachiara')),
     (SELECT id FROM localita WHERE nome = 'Via dei Forni' AND comune_id = (SELECT id FROM comune WHERE nome = 'Pietrachiara')),
     'Casa civile', 3, 8, 'Vani 8 su tre piani', 'Classe II'),
    -- Bottega in Piazza della Rocca, Pietrachiara (partita 102)
    ((SELECT id FROM partita WHERE numero_partita = 102 AND comune_id = (SELECT id FROM comune WHERE nome = 'Pietrachiara')),
     (SELECT id FROM localita WHERE nome = 'Piazza della Rocca' AND comune_id = (SELECT id FROM comune WHERE nome = 'Pietrachiara')),
     'Bottega con magazzino', 1, 2, 'Vani 2 al piano terreno', 'Classe III'),
    -- Fabbricato rurale in Piazza della Rocca (partita 103)
    ((SELECT id FROM partita WHERE numero_partita = 103 AND comune_id = (SELECT id FROM comune WHERE nome = 'Pietrachiara')),
     (SELECT id FROM localita WHERE nome = 'Piazza della Rocca' AND comune_id = (SELECT id FROM comune WHERE nome = 'Pietrachiara')),
     'Fabbricato rurale', 2, 4, 'Vani 4 su due piani con stalla', 'Classe IV'),
    -- Abitazione in Strada della Fontana, Montalvento (partita 201)
    ((SELECT id FROM partita WHERE numero_partita = 201 AND comune_id = (SELECT id FROM comune WHERE nome = 'Montalvento')),
     (SELECT id FROM localita WHERE nome = 'Strada della Fontana' AND comune_id = (SELECT id FROM comune WHERE nome = 'Montalvento')),
     'Abitazione signorile', 2, 10, 'Vani 10 su due piani con giardino', 'Classe I'),
    -- Orto annesso (partita 202, secondaria)
    ((SELECT id FROM partita WHERE numero_partita = 202 AND comune_id = (SELECT id FROM comune WHERE nome = 'Montalvento')),
     (SELECT id FROM localita WHERE nome = 'Strada della Fontana' AND comune_id = (SELECT id FROM comune WHERE nome = 'Montalvento')),
     'Orto', NULL, NULL, 'Tavole 15', 'Terreno agricolo'),
    -- Casa con corte in Salita del Castello, Riofranco (partita 301)
    ((SELECT id FROM partita WHERE numero_partita = 301 AND comune_id = (SELECT id FROM comune WHERE nome = 'Riofranco')),
     (SELECT id FROM localita WHERE nome = 'Salita del Castello' AND comune_id = (SELECT id FROM comune WHERE nome = 'Riofranco')),
     'Casa con corte', 2, 6, 'Vani 6 su due piani con corte interna', 'Classe II');

-- ===== VARIAZIONI (3 variazioni con contratti) =====

-- Variazione 1: Vendita dalla partita 103 alla partita 101 (Pietrachiara)
INSERT INTO variazione (partita_origine_id, partita_destinazione_id, tipo, data_variazione, numero_riferimento, nominativo_riferimento)
VALUES
    ((SELECT id FROM partita WHERE numero_partita = 103 AND comune_id = (SELECT id FROM comune WHERE nome = 'Pietrachiara')),
     (SELECT id FROM partita WHERE numero_partita = 101 AND comune_id = (SELECT id FROM comune WHERE nome = 'Pietrachiara')),
     'Vendita', '1892-03-18', 'Rep. 1456/1892', 'Ghiglione Teresa a Dellavalle Giovanni');

INSERT INTO contratto (variazione_id, tipo, data_contratto, notaio, repertorio, note)
VALUES
    ((SELECT id FROM variazione WHERE numero_riferimento = 'Rep. 1456/1892'),
     'Atto di Compravendita', '1892-03-15', 'Not. Caviglia Emanuele', 'Rep. 1456',
     'Compravendita del fabbricato rurale in Piazza della Rocca. Prezzo pattuito: Lire 3.200.');

-- Variazione 2: Successione nella partita 201 (Montalvento)
INSERT INTO variazione (partita_origine_id, tipo, data_variazione, numero_riferimento, nominativo_riferimento)
VALUES
    ((SELECT id FROM partita WHERE numero_partita = 201 AND comune_id = (SELECT id FROM comune WHERE nome = 'Montalvento')),
     'Successione', '1905-11-22', 'Atti n. 892/1905', 'Eredità Canepa fu Giuseppe');

INSERT INTO contratto (variazione_id, tipo, data_contratto, notaio, repertorio, note)
VALUES
    ((SELECT id FROM variazione WHERE numero_riferimento = 'Atti n. 892/1905'),
     'Dichiarazione di Successione', '1905-11-20', 'Not. Persico Alberto', 'Rep. 892',
     'Successione ereditaria in favore di Canepa Rosa e Ferrando Carlo per decesso del padre.');

-- Variazione 3: Divisione nella partita 301 (Riofranco)
INSERT INTO variazione (partita_origine_id, tipo, data_variazione, numero_riferimento, nominativo_riferimento)
VALUES
    ((SELECT id FROM partita WHERE numero_partita = 301 AND comune_id = (SELECT id FROM comune WHERE nome = 'Riofranco')),
     'Divisione', '1910-07-04', 'Rep. 2301/1910', 'Divisione Zunino-Bruzzone');

INSERT INTO contratto (variazione_id, tipo, data_contratto, notaio, repertorio, note)
VALUES
    ((SELECT id FROM variazione WHERE numero_riferimento = 'Rep. 2301/1910'),
     'Atto di Divisione', '1910-07-01', 'Not. Galleano Francesco', 'Rep. 2301',
     'Divisione consensuale della proprietà in due unità distinte. Quote uguali.');

-- ===== RELAZIONE TRA PARTITE =====
INSERT INTO partita_relazione (partita_principale_id, partita_secondaria_id)
VALUES
    ((SELECT id FROM partita WHERE numero_partita = 201 AND comune_id = (SELECT id FROM comune WHERE nome = 'Montalvento')),
     (SELECT id FROM partita WHERE numero_partita = 202 AND comune_id = (SELECT id FROM comune WHERE nome = 'Montalvento')));

-- ===== CONSULTAZIONE DEMO =====
INSERT INTO consultazione (data, richiedente, documento_identita, motivazione, materiale_consultato, funzionario_autorizzante)
VALUES
    ('2025-09-15', 'Prof. Andrea Bertonelli', 'CI AX1234567',
     'Ricerca storica per tesi di dottorato sulle trasformazioni fondiarie nell''entroterra ligure.',
     'Registro partite Pietrachiara vol. I-III, Matricole vol. I-II',
     'Dott.ssa Francesca Molinari');

-- ===========================================================================
-- Fine dati demo
-- ===========================================================================
