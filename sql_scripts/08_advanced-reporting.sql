-- Imposta lo schema
SET search_path TO catasto, public; -- Aggiunto public per estensioni

-- 1. Vista materializzata per statistiche per comune (MODIFICATA)
-- Rimuovi la vecchia vista se esiste, per poterla ricreare con la nuova struttura
DROP MATERIALIZED VIEW IF EXISTS mv_statistiche_comune;
CREATE MATERIALIZED VIEW mv_statistiche_comune AS
SELECT
    c.nome AS comune, -- Seleziona nome da tabella comune
    c.provincia,
    COUNT(DISTINCT p.id) AS totale_partite,
    COUNT(DISTINCT CASE WHEN p.stato = 'attiva' THEN p.id END) AS partite_attive,
    COUNT(DISTINCT CASE WHEN p.stato = 'inattiva' THEN p.id END) AS partite_inattive,
    COUNT(DISTINCT pos.id) AS totale_possessori,
    COUNT(DISTINCT i.id) AS totale_immobili
FROM comune c -- Parte da comune
LEFT JOIN partita p ON c.id = p.comune_id -- Join con partita su ID
LEFT JOIN partita_possessore pp ON p.id = pp.partita_id
LEFT JOIN possessore pos ON pp.possessore_id = pos.id -- Questo join è corretto
LEFT JOIN immobile i ON p.id = i.partita_id
GROUP BY c.id, c.nome, c.provincia; -- Raggruppa per ID, NOME e Provincia

CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_statistiche_comune ON mv_statistiche_comune(comune); -- Indice sul nome va bene

-- Procedura per aggiornare le statistiche (invariata nella chiamata, ma aggiorna la nuova vista)
CREATE OR REPLACE PROCEDURE aggiorna_statistiche_comune()
LANGUAGE plpgsql
AS $$
BEGIN
    RAISE NOTICE 'Aggiornamento vista materializzata mv_statistiche_comune...';
    REFRESH MATERIALIZED VIEW CONCURRENTLY mv_statistiche_comune; -- Usa CONCURRENTLY se possibile
    RAISE NOTICE 'Aggiornamento vista mv_statistiche_comune completato.';
END;
$$;

-- 2. Vista materializzata per riepilogo immobili per tipologia (MODIFICATA)
DROP MATERIALIZED VIEW IF EXISTS mv_immobili_per_tipologia;
CREATE MATERIALIZED VIEW mv_immobili_per_tipologia AS
SELECT
    c.nome AS comune_nome, -- Seleziona nome da tabella comune
    COALESCE(i.classificazione, 'Non Classificati') AS classificazione, -- Usa COALESCE
    COUNT(*) AS numero_immobili,
    SUM(COALESCE(i.numero_piani, 0)) AS totale_piani,
    SUM(COALESCE(i.numero_vani, 0)) AS totale_vani
FROM immobile i
JOIN partita p ON i.partita_id = p.id
JOIN comune c ON p.comune_id = c.id -- Join con comune su ID
WHERE p.stato = 'attiva'
GROUP BY c.nome, COALESCE(i.classificazione, 'Non Classificati'); -- Raggruppa per nome comune e classificazione

CREATE INDEX IF NOT EXISTS idx_mv_immobili_tipologia_comune ON mv_immobili_per_tipologia(comune_nome);
CREATE INDEX IF NOT EXISTS idx_mv_immobili_tipologia_class ON mv_immobili_per_tipologia(classificazione);

-- 3. Vista materializzata per l'elenco completo delle partite (MODIFICATA)
DROP MATERIALIZED VIEW IF EXISTS mv_partite_complete;
CREATE MATERIALIZED VIEW mv_partite_complete AS
SELECT
    p.id AS partita_id,
    c.nome AS comune_nome, -- Seleziona nome da comune
    p.numero_partita,
    p.tipo,
    p.data_impianto,
    p.stato,
    string_agg(DISTINCT pos.nome_completo, ', ') AS possessori,
    COUNT(DISTINCT i.id) AS num_immobili,
    string_agg(DISTINCT i.natura, ', ') AS tipi_immobili,
    string_agg(DISTINCT l.nome, ', ') AS localita
FROM partita p
JOIN comune c ON p.comune_id = c.id -- Join con comune su ID
LEFT JOIN partita_possessore pp ON p.id = pp.partita_id
LEFT JOIN possessore pos ON pp.possessore_id = pos.id
LEFT JOIN immobile i ON p.id = i.partita_id
LEFT JOIN localita l ON i.localita_id = l.id
GROUP BY p.id, c.nome, p.numero_partita, p.tipo, p.data_impianto, p.stato; -- Raggruppa per nome comune

CREATE INDEX IF NOT EXISTS idx_mv_partite_complete_partita_id ON mv_partite_complete(partita_id); -- Aggiunto indice su ID
CREATE INDEX IF NOT EXISTS idx_mv_partite_complete_comune ON mv_partite_complete(comune_nome);
CREATE INDEX IF NOT EXISTS idx_mv_partite_complete_numero ON mv_partite_complete(numero_partita);
CREATE INDEX IF NOT EXISTS idx_mv_partite_complete_stato ON mv_partite_complete(stato);

-- 4. Vista materializzata per la cronologia delle variazioni (MODIFICATA)
DROP MATERIALIZED VIEW IF EXISTS mv_cronologia_variazioni;
CREATE MATERIALIZED VIEW mv_cronologia_variazioni AS
SELECT
    v.id AS variazione_id,
    v.tipo AS tipo_variazione,
    v.data_variazione,
    p_orig.numero_partita AS partita_origine_numero,
    c_orig.nome AS comune_origine, -- Seleziona nome da comune origine
    string_agg(DISTINCT pos_orig.nome_completo, ', ') AS possessori_origine,
    p_dest.numero_partita AS partita_dest_numero,
    c_dest.nome AS comune_dest, -- Seleziona nome da comune destinazione
    string_agg(DISTINCT pos_dest.nome_completo, ', ') AS possessori_dest,
    con.tipo AS tipo_contratto, -- Alias contratto cambiato in 'con' per evitare ambiguità
    con.notaio,
    con.data_contratto
FROM variazione v
JOIN partita p_orig ON v.partita_origine_id = p_orig.id
JOIN comune c_orig ON p_orig.comune_id = c_orig.id -- Join comune origine
LEFT JOIN partita p_dest ON v.partita_destinazione_id = p_dest.id
LEFT JOIN comune c_dest ON p_dest.comune_id = c_dest.id -- Join comune destinazione
LEFT JOIN contratto con ON v.id = con.variazione_id -- Alias contratto 'con'
LEFT JOIN partita_possessore pp_orig ON p_orig.id = pp_orig.partita_id
LEFT JOIN possessore pos_orig ON pp_orig.possessore_id = pos_orig.id
LEFT JOIN partita_possessore pp_dest ON p_dest.id = pp_dest.partita_id
LEFT JOIN possessore pos_dest ON pp_dest.possessore_id = pos_dest.id
GROUP BY v.id, v.tipo, v.data_variazione, p_orig.numero_partita, c_orig.nome, -- Raggruppa per nome comune origine
         p_dest.numero_partita, c_dest.nome, -- Raggruppa per nome comune destinazione
         con.tipo, con.notaio, con.data_contratto;

CREATE INDEX IF NOT EXISTS idx_mv_variazioni_var_id ON mv_cronologia_variazioni(variazione_id); -- Aggiunto indice su ID
CREATE INDEX IF NOT EXISTS idx_mv_variazioni_data ON mv_cronologia_variazioni(data_variazione);
CREATE INDEX IF NOT EXISTS idx_mv_variazioni_tipo ON mv_cronologia_variazioni(tipo_variazione);
CREATE INDEX IF NOT EXISTS idx_mv_variazioni_comune_orig ON mv_cronologia_variazioni(comune_origine);

-- 5. Funzione per generare report annuale delle partite per comune (MODIFICATA)
CREATE OR REPLACE FUNCTION report_annuale_partite(
    p_comune_id INTEGER, -- Modificato parametro da VARCHAR a INTEGER
    p_anno INTEGER
)
RETURNS TABLE (
    numero_partita INTEGER,
    tipo VARCHAR,
    data_impianto DATE,
    stato VARCHAR,
    possessori TEXT,
    num_immobili BIGINT,
    variazioni_anno BIGINT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        p.numero_partita,
        p.tipo,
        p.data_impianto,
        p.stato,
        string_agg(DISTINCT pos.nome_completo, ', ') AS possessori,
        COUNT(DISTINCT i.id) AS num_immobili,
        (SELECT COUNT(*) FROM variazione v
         WHERE (v.partita_origine_id = p.id OR v.partita_destinazione_id = p.id)
         AND EXTRACT(YEAR FROM v.data_variazione) = p_anno) AS variazioni_anno
    FROM partita p
    -- Non serve join con comune se non mostriamo il nome
    LEFT JOIN partita_possessore pp ON p.id = pp.partita_id
    LEFT JOIN possessore pos ON pp.possessore_id = pos.id
    LEFT JOIN immobile i ON p.id = i.partita_id
    WHERE p.comune_id = p_comune_id -- Filtra per ID comune
    AND (EXTRACT(YEAR FROM p.data_impianto) <= p_anno)
    AND (p.data_chiusura IS NULL OR EXTRACT(YEAR FROM p.data_chiusura) >= p_anno)
    GROUP BY p.id, p.numero_partita, p.tipo, p.data_impianto, p.stato -- Raggruppa per p.id
    ORDER BY p.numero_partita;
END;
$$ LANGUAGE plpgsql;

-- 6. Funzione per generare report delle proprietà di un possessore in un determinato periodo (MODIFICATA)
CREATE OR REPLACE FUNCTION report_proprieta_possessore(
    p_possessore_id INTEGER,
    p_data_inizio DATE,
    p_data_fine DATE
)
RETURNS TABLE (
    partita_id INTEGER,
    comune_nome VARCHAR, -- Manteniamo nome output
    numero_partita INTEGER,
    titolo VARCHAR,
    quota VARCHAR,
    data_inizio DATE,
    data_fine DATE,
    immobili_posseduti TEXT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        p.id AS partita_id,
        c.nome AS comune_nome, -- Seleziona nome da comune
        p.numero_partita,
        pp.titolo,
        pp.quota,
        GREATEST(p.data_impianto, p_data_inizio) AS data_inizio,
        LEAST(COALESCE(p.data_chiusura, p_data_fine), p_data_fine) AS data_fine,
        string_agg(DISTINCT i.natura || ' in ' || l.nome, ', ') AS immobili_posseduti
    FROM partita p
    JOIN comune c ON p.comune_id = c.id -- Join con comune su ID
    JOIN partita_possessore pp ON p.id = pp.partita_id
    LEFT JOIN immobile i ON p.id = i.partita_id
    LEFT JOIN localita l ON i.localita_id = l.id
    WHERE pp.possessore_id = p_possessore_id
    AND p.data_impianto <= p_data_fine
    AND (p.data_chiusura IS NULL OR p.data_chiusura >= p_data_inizio)
    GROUP BY p.id, c.nome, p.numero_partita, pp.titolo, pp.quota -- Raggruppa per nome comune
    ORDER BY c.nome, p.numero_partita;
END;
$$ LANGUAGE plpgsql;

-- 7. Procedura per aggiornare tutte le viste materializzate (MODIFICATA con CONCURRENTLY)
CREATE OR REPLACE PROCEDURE aggiorna_tutte_statistiche()
LANGUAGE plpgsql
AS $$
BEGIN
    RAISE NOTICE 'Aggiornamento vista materializzata mv_statistiche_comune...';
    REFRESH MATERIALIZED VIEW mv_statistiche_comune;
    RAISE NOTICE 'Aggiornamento vista mv_statistiche_comune completato.';

    RAISE NOTICE 'Aggiornamento vista materializzata mv_immobili_per_tipologia...';
    REFRESH MATERIALIZED VIEW mv_immobili_per_tipologia;
    RAISE NOTICE 'Aggiornamento vista mv_immobili_per_tipologia completato.';

    RAISE NOTICE 'Aggiornamento vista materializzata mv_partite_complete...';
    REFRESH MATERIALIZED VIEW mv_partite_complete;
    RAISE NOTICE 'Aggiornamento vista mv_partite_complete completato.';

    RAISE NOTICE 'Aggiornamento vista materializzata mv_cronologia_variazioni...';
    REFRESH MATERIALIZED VIEW mv_cronologia_variazioni;
    RAISE NOTICE 'Aggiornamento vista mv_cronologia_variazioni completato.';

    RAISE NOTICE 'Aggiornamento di tutte le viste materializzate completato.';
EXCEPTION
    WHEN OTHERS THEN
        RAISE WARNING '[aggiorna_tutte_statistiche] Errore durante l''aggiornamento: %', SQLERRM;
END;
$$;

-- Commento sulla pianificazione (invariato)
COMMENT ON PROCEDURE aggiorna_tutte_statistiche() IS 'Procedura da eseguire con pg_cron o job esterno (es. giornaliero).';

-- Aggiornamento iniziale delle viste materializzate (chiamato alla fine dello script per sicurezza)
-- Assicurarsi che i dati base siano presenti se eseguito qui, altrimenti chiamare dopo script 04
DO $$ BEGIN
    RAISE NOTICE 'Chiamata iniziale aggiorna_tutte_statistiche()...';
    CALL aggiorna_tutte_statistiche();
END $$;