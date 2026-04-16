-- File: 12_procedure_crud_corretto.sql
-- Oggetto: Script corretto con procedure e funzioni CRUD per Catasto Storico
-- Versione: 1.1
-- Data: 30/04/2025
-- Note: Corretta la definizione della funzione genera_report_comune.

-- Imposta lo schema
SET search_path TO catasto;

-- Procedura aggiorna_immobile (come da file originale)
CREATE OR REPLACE PROCEDURE aggiorna_immobile(
    p_id INTEGER,
    p_natura VARCHAR(100) DEFAULT NULL,
    p_numero_piani INTEGER DEFAULT NULL,
    p_numero_vani INTEGER DEFAULT NULL,
    p_consistenza VARCHAR(255) DEFAULT NULL,
    p_classificazione VARCHAR(100) DEFAULT NULL,
    p_localita_id INTEGER DEFAULT NULL
)
LANGUAGE plpgsql
AS $$
BEGIN
    UPDATE immobile
    SET natura = COALESCE(p_natura, natura),
        numero_piani = COALESCE(p_numero_piani, numero_piani),
        numero_vani = COALESCE(p_numero_vani, numero_vani),
        consistenza = COALESCE(p_consistenza, consistenza),
        classificazione = COALESCE(p_classificazione, classificazione),
        localita_id = COALESCE(p_localita_id, localita_id),
        data_modifica = CURRENT_TIMESTAMP -- Aggiunto aggiornamento timestamp
    WHERE id = p_id;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Immobile con ID % non trovato', p_id;
    END IF;

    RAISE NOTICE 'Immobile con ID % aggiornato con successo', p_id;
EXCEPTION
    WHEN foreign_key_violation THEN
        RAISE EXCEPTION 'Errore FK durante aggiornamento immobile: La località specificata (ID %) non esiste o violazione di altro vincolo.', p_localita_id;
    WHEN OTHERS THEN
        RAISE EXCEPTION 'Errore durante l''aggiornamento dell''immobile ID %: %', p_id, SQLERRM;
END;
$$;

-- Procedura elimina_immobile (come da file originale)
CREATE OR REPLACE PROCEDURE elimina_immobile(
    p_id INTEGER
)
LANGUAGE plpgsql
AS $$
BEGIN
    DELETE FROM immobile WHERE id = p_id;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Immobile con ID % non trovato', p_id;
    END IF;

    RAISE NOTICE 'Immobile con ID % eliminato con successo', p_id;
EXCEPTION
    WHEN OTHERS THEN
        RAISE EXCEPTION 'Errore durante l''eliminazione dell''immobile ID %: %', p_id, SQLERRM;
END;
$$;

-- Funzione cerca_immobili (come da file originale, ma aggiornata per usare comune_id e JOIN)
CREATE OR REPLACE FUNCTION cerca_immobili(
    p_partita_id INTEGER DEFAULT NULL,
    p_comune_id INTEGER DEFAULT NULL, -- Modificato da p_comune_nome a p_comune_id
    p_localita_id INTEGER DEFAULT NULL,
    p_natura VARCHAR DEFAULT NULL,
    p_classificazione VARCHAR DEFAULT NULL
)
RETURNS TABLE (
    id INTEGER,
    partita_id INTEGER,
    numero_partita INTEGER,
    comune_nome VARCHAR, -- Manteniamo nome comune nell'output
    localita_nome VARCHAR,
    natura VARCHAR,
    numero_piani INTEGER,
    numero_vani INTEGER,
    consistenza VARCHAR,
    classificazione VARCHAR
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        i.id,
        i.partita_id,
        p.numero_partita,
        c.nome AS comune_nome, -- Seleziona nome da tabella comune
        l.nome AS localita_nome,
        i.natura,
        i.numero_piani,
        i.numero_vani,
        i.consistenza,
        i.classificazione
    FROM immobile i
    JOIN partita p ON i.partita_id = p.id
    JOIN localita l ON i.localita_id = l.id
    JOIN comune c ON p.comune_id = c.id -- *** JOIN AGGIUNTO ***
    WHERE (p_partita_id IS NULL OR i.partita_id = p_partita_id)
      AND (p_comune_id IS NULL OR p.comune_id = p_comune_id) -- *** Filtro su ID ***
      AND (p_localita_id IS NULL OR i.localita_id = p_localita_id)
      AND (p_natura IS NULL OR i.natura ILIKE '%' || p_natura || '%')
      AND (p_classificazione IS NULL OR i.classificazione = p_classificazione)
    ORDER BY c.nome, p.numero_partita, i.natura;
END;
$$ LANGUAGE plpgsql;

-- Procedura aggiorna_variazione (come da file originale)
CREATE OR REPLACE PROCEDURE aggiorna_variazione(
    p_variazione_id INTEGER,
    p_tipo VARCHAR(50) DEFAULT NULL,
    p_data_variazione DATE DEFAULT NULL,
    p_numero_riferimento VARCHAR(50) DEFAULT NULL,
    p_nominativo_riferimento VARCHAR(255) DEFAULT NULL
)
LANGUAGE plpgsql
AS $$
BEGIN
    UPDATE variazione
    SET tipo = COALESCE(p_tipo, tipo),
        data_variazione = COALESCE(p_data_variazione, data_variazione),
        numero_riferimento = COALESCE(p_numero_riferimento, numero_riferimento),
        nominativo_riferimento = COALESCE(p_nominativo_riferimento, nominativo_riferimento),
        data_modifica = CURRENT_TIMESTAMP -- Aggiunto aggiornamento timestamp
    WHERE id = p_variazione_id;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Variazione con ID % non trovata', p_variazione_id;
    END IF;

    RAISE NOTICE 'Variazione con ID % aggiornata con successo', p_variazione_id;
EXCEPTION
    WHEN OTHERS THEN
        RAISE EXCEPTION 'Errore durante l''aggiornamento della variazione ID %: %', p_variazione_id, SQLERRM;
END;
$$;

-- Procedura elimina_variazione (come da file originale)
CREATE OR REPLACE PROCEDURE elimina_variazione(
    p_id INTEGER,
    p_forza BOOLEAN DEFAULT FALSE,
    p_ripristina_partita BOOLEAN DEFAULT FALSE
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_count INTEGER;
    v_partita_origine_id INTEGER;
    v_data_variazione DATE;
BEGIN
    -- Verifica l'esistenza di dipendenze (contratti)
    IF NOT p_forza THEN
        SELECT COUNT(*) INTO v_count FROM contratto WHERE variazione_id = p_id;
        IF v_count > 0 THEN
            RAISE EXCEPTION 'La variazione con ID % ha % contratti associati. Usa p_forza=TRUE per eliminare comunque', p_id, v_count;
        END IF;
    END IF;

    -- Recupera informazioni sulla partita di origine e data
    SELECT partita_origine_id, data_variazione
    INTO v_partita_origine_id, v_data_variazione
    FROM variazione
    WHERE id = p_id;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Variazione con ID % non trovata', p_id;
    END IF;

    -- Elimina i contratti collegati se p_forza=TRUE
    IF p_forza THEN
        DELETE FROM contratto WHERE variazione_id = p_id;
        RAISE NOTICE 'Contratti associati alla variazione ID % eliminati (forzato).', p_id;
    END IF;

    -- Elimina la variazione
    DELETE FROM variazione WHERE id = p_id;

    -- Ripristina la partita di origine se richiesto
    IF p_ripristina_partita AND v_partita_origine_id IS NOT NULL THEN
        UPDATE partita
        SET stato = 'attiva',
            data_chiusura = NULL
        WHERE id = v_partita_origine_id
          AND data_chiusura = v_data_variazione; -- Solo se la data chiusura corrisponde

        RAISE NOTICE 'Tentativo di ripristino partita origine ID % come attiva (se la data chiusura corrispondeva).', v_partita_origine_id;
    END IF;

    RAISE NOTICE 'Variazione con ID % eliminata con successo', p_id;
EXCEPTION
    WHEN OTHERS THEN
        RAISE EXCEPTION 'Errore durante l''eliminazione della variazione ID %: %', p_id, SQLERRM;
END;
$$;

-- Funzione cerca_variazioni (come da file originale, ma aggiornata per usare comune_id e JOIN)
CREATE OR REPLACE FUNCTION cerca_variazioni(
    p_tipo VARCHAR DEFAULT NULL,
    p_data_inizio DATE DEFAULT NULL,
    p_data_fine DATE DEFAULT NULL,
    p_partita_origine_id INTEGER DEFAULT NULL,
    p_partita_destinazione_id INTEGER DEFAULT NULL,
    p_comune_id INTEGER DEFAULT NULL -- Modificato da p_comune a p_comune_id
)
RETURNS TABLE (
    id INTEGER,
    tipo VARCHAR,
    data_variazione DATE,
    partita_origine_id INTEGER,
    partita_origine_numero INTEGER,
    partita_destinazione_id INTEGER,
    partita_destinazione_numero INTEGER,
    comune_nome VARCHAR, -- Manteniamo nome comune nell'output
    numero_riferimento VARCHAR,
    nominativo_riferimento VARCHAR
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        v.id,
        v.tipo,
        v.data_variazione,
        v.partita_origine_id,
        po.numero_partita AS partita_origine_numero,
        v.partita_destinazione_id,
        pd.numero_partita AS partita_destinazione_numero,
        c.nome AS comune_nome, -- Seleziona nome da comune
        v.numero_riferimento,
        v.nominativo_riferimento
    FROM variazione v
    JOIN partita po ON v.partita_origine_id = po.id
    JOIN comune c ON po.comune_id = c.id -- *** JOIN AGGIUNTO ***
    LEFT JOIN partita pd ON v.partita_destinazione_id = pd.id
    WHERE (p_tipo IS NULL OR v.tipo = p_tipo)
      AND (p_data_inizio IS NULL OR v.data_variazione >= p_data_inizio)
      AND (p_data_fine IS NULL OR v.data_variazione <= p_data_fine)
      AND (p_partita_origine_id IS NULL OR v.partita_origine_id = p_partita_origine_id)
      AND (p_partita_destinazione_id IS NULL OR v.partita_destinazione_id = p_partita_destinazione_id)
      AND (p_comune_id IS NULL OR po.comune_id = p_comune_id) -- *** Filtro su ID ***
    ORDER BY v.data_variazione DESC, c.nome, po.numero_partita;
END;
$$ LANGUAGE plpgsql;

-- Procedura inserisci_contratto (come da file originale)
CREATE OR REPLACE PROCEDURE inserisci_contratto(
    p_variazione_id INTEGER,
    p_tipo VARCHAR(50),
    p_data_contratto DATE,
    p_notaio VARCHAR(255) DEFAULT NULL,
    p_repertorio VARCHAR(100) DEFAULT NULL,
    p_note TEXT DEFAULT NULL
)
LANGUAGE plpgsql
AS $$
BEGIN
    -- Verifica se la variazione esiste
    IF NOT EXISTS (SELECT 1 FROM variazione WHERE id = p_variazione_id) THEN
        RAISE EXCEPTION 'La variazione con ID % non esiste', p_variazione_id;
    END IF;

    -- Verifica se esiste già un contratto per questa variazione
    IF EXISTS (SELECT 1 FROM contratto WHERE variazione_id = p_variazione_id) THEN
        -- Considera se sollevare un WARNING invece di un EXCEPTION
        RAISE EXCEPTION 'Esiste già un contratto per la variazione con ID %', p_variazione_id;
    END IF;

    -- Inserisci il contratto
    INSERT INTO contratto(variazione_id, tipo, data_contratto, notaio, repertorio, note)
    VALUES (p_variazione_id, p_tipo, p_data_contratto, p_notaio, p_repertorio, p_note);

    RAISE NOTICE 'Contratto inserito con successo per la variazione con ID %', p_variazione_id;
EXCEPTION
    WHEN OTHERS THEN
        RAISE EXCEPTION 'Errore durante l''inserimento del contratto per variazione ID %: %', p_variazione_id, SQLERRM;
END;
$$;

-- Procedura aggiorna_contratto (come da file originale)
CREATE OR REPLACE PROCEDURE aggiorna_contratto(
    p_id INTEGER,
    p_tipo VARCHAR(50) DEFAULT NULL,
    p_data_contratto DATE DEFAULT NULL,
    p_notaio VARCHAR(255) DEFAULT NULL,
    p_repertorio VARCHAR(100) DEFAULT NULL,
    p_note TEXT DEFAULT NULL
)
LANGUAGE plpgsql
AS $$
BEGIN
    UPDATE contratto
    SET tipo = COALESCE(p_tipo, tipo),
        data_contratto = COALESCE(p_data_contratto, data_contratto),
        notaio = COALESCE(p_notaio, notaio),
        repertorio = COALESCE(p_repertorio, repertorio),
        note = COALESCE(p_note, note),
        data_modifica = CURRENT_TIMESTAMP -- Aggiunto aggiornamento timestamp
    WHERE id = p_id;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Contratto con ID % non trovato', p_id;
    END IF;

    RAISE NOTICE 'Contratto con ID % aggiornato con successo', p_id;
EXCEPTION
    WHEN OTHERS THEN
        RAISE EXCEPTION 'Errore durante l''aggiornamento del contratto ID %: %', p_id, SQLERRM;
END;
$$;

-- Procedura elimina_contratto (come da file originale)
CREATE OR REPLACE PROCEDURE elimina_contratto(
    p_id INTEGER
)
LANGUAGE plpgsql
AS $$
BEGIN
    DELETE FROM contratto WHERE id = p_id;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Contratto con ID % non trovato', p_id;
    END IF;

    RAISE NOTICE 'Contratto con ID % eliminato con successo', p_id;
EXCEPTION
    WHEN OTHERS THEN
        RAISE EXCEPTION 'Errore durante l''eliminazione del contratto ID %: %', p_id, SQLERRM;
END;
$$;

-- Procedura aggiorna_consultazione (come da file originale)
CREATE OR REPLACE PROCEDURE aggiorna_consultazione(
    p_id INTEGER,
    p_data DATE DEFAULT NULL,
    p_richiedente VARCHAR(255) DEFAULT NULL,
    p_documento_identita VARCHAR(100) DEFAULT NULL,
    p_motivazione TEXT DEFAULT NULL,
    p_materiale_consultato TEXT DEFAULT NULL,
    p_funzionario_autorizzante VARCHAR(255) DEFAULT NULL
)
LANGUAGE plpgsql
AS $$
BEGIN
    UPDATE consultazione
    SET data = COALESCE(p_data, data),
        richiedente = COALESCE(p_richiedente, richiedente),
        documento_identita = COALESCE(p_documento_identita, documento_identita),
        motivazione = COALESCE(p_motivazione, motivazione),
        materiale_consultato = COALESCE(p_materiale_consultato, materiale_consultato),
        funzionario_autorizzante = COALESCE(p_funzionario_autorizzante, funzionario_autorizzante),
        data_modifica = CURRENT_TIMESTAMP -- Aggiunto aggiornamento timestamp
    WHERE id = p_id;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Consultazione con ID % non trovata', p_id;
    END IF;

    RAISE NOTICE 'Consultazione con ID % aggiornata con successo', p_id;
EXCEPTION
    WHEN OTHERS THEN
        RAISE EXCEPTION 'Errore durante l''aggiornamento della consultazione ID %: %', p_id, SQLERRM;
END;
$$;

-- Procedura elimina_consultazione (come da file originale)
CREATE OR REPLACE PROCEDURE elimina_consultazione(
    p_id INTEGER
)
LANGUAGE plpgsql
AS $$
BEGIN
    DELETE FROM consultazione WHERE id = p_id;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Consultazione con ID % non trovata', p_id;
    END IF;

    RAISE NOTICE 'Consultazione con ID % eliminata con successo', p_id;
EXCEPTION
    WHEN OTHERS THEN
        RAISE EXCEPTION 'Errore durante l''eliminazione della consultazione ID %: %', p_id, SQLERRM;
END;
$$;

-- Funzione cerca_consultazioni (come da file originale)
CREATE OR REPLACE FUNCTION cerca_consultazioni(
    p_data_inizio DATE DEFAULT NULL,
    p_data_fine DATE DEFAULT NULL,
    p_richiedente VARCHAR DEFAULT NULL,
    p_funzionario VARCHAR DEFAULT NULL
)
RETURNS TABLE (
    id INTEGER,
    data DATE,
    richiedente VARCHAR,
    documento_identita VARCHAR,
    motivazione TEXT,
    materiale_consultato TEXT,
    funzionario_autorizzante VARCHAR
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        c.id,
        c.data,
        c.richiedente,
        c.documento_identita,
        c.motivazione,
        c.materiale_consultato,
        c.funzionario_autorizzante
    FROM consultazione c
    WHERE (p_data_inizio IS NULL OR c.data >= p_data_inizio)
      AND (p_data_fine IS NULL OR c.data <= p_data_fine)
      AND (p_richiedente IS NULL OR c.richiedente ILIKE '%' || p_richiedente || '%')
      AND (p_funzionario IS NULL OR c.funzionario_autorizzante ILIKE '%' || p_funzionario || '%')
    ORDER BY c.data DESC, c.richiedente;
END;
$$ LANGUAGE plpgsql;

-- Adatta la firma per includere p_nuovo_suffisso
CREATE OR REPLACE PROCEDURE catasto.duplica_partita(
    p_partita_id_originale INTEGER,
    p_nuovo_numero_partita INTEGER,
    p_mantenere_possessori BOOLEAN,
    p_mantenere_immobili BOOLEAN,
    p_nuovo_suffisso VARCHAR(20) DEFAULT NULL -- AGGIUNTO QUI
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_vecchia_partita_data catasto.partita;
    v_nuova_partita_id INTEGER;
    v_old_poss_rec RECORD;
    v_old_imm_rec RECORD;
BEGIN
    SELECT * INTO v_vecchia_partita_data FROM catasto.partita WHERE id = p_partita_id_originale;

    IF v_vecchia_partita_data IS NULL THEN
        RAISE EXCEPTION 'Partita originale con ID % non trovata.', p_partita_id_originale;
    END IF;

    -- Valida che la nuova partita non esista già
    IF EXISTS (SELECT 1 FROM catasto.partita
               WHERE comune_id = v_vecchia_partita_data.comune_id
                 AND numero_partita = p_nuovo_numero_partita
                 AND (suffisso_partita = p_nuovo_suffisso OR (suffisso_partita IS NULL AND p_nuovo_suffisso IS NULL))) THEN
        RAISE EXCEPTION 'Esiste già una partita con il numero %s e suffisso %s nel comune %s.',
                       p_nuovo_numero_partita, COALESCE(p_nuovo_suffisso, 'NULL'), v_vecchia_partita_data.comune_id;
    END IF;

    -- Inserisci la nuova partita, includendo il suffisso
    INSERT INTO catasto.partita (comune_id, numero_partita, data_impianto, stato, tipo,
                                 numero_provenienza, data_chiusura, suffisso_partita)
    VALUES (v_vecchia_partita_data.comune_id, p_nuovo_numero_partita, v_vecchia_partita_data.data_impianto,
            v_vecchia_partita_data.stato, v_vecchia_partita_data.tipo,
            v_vecchia_partita_data.numero_provenienza, v_vecchia_partita_data.data_chiusura,
            p_nuovo_suffisso)
    RETURNING id INTO v_nuova_partita_id;

    -- Copia possessori (se richiesto)
    IF p_mantenere_possessori THEN
        INSERT INTO catasto.partita_possessore (partita_id, possessore_id, tipo_partita, titolo, quota)
        SELECT v_nuova_partita_id, possessore_id, tipo_partita, titolo, quota
        FROM catasto.partita_possessore
        WHERE partita_id = p_partita_id_originale;
    END IF;

    -- Copia immobili (se richiesto)
    IF p_mantenere_immobili THEN
        INSERT INTO catasto.immobile (
            partita_id, natura, localita_id, classificazione, consistenza, numero_piani, numero_vani
        )
        SELECT
            v_nuova_partita_id, natura, localita_id, classificazione, consistenza, numero_piani, numero_vani
        FROM catasto.immobile
        WHERE partita_id = p_partita_id_originale;
    END IF;
END;
$$;

-- Procedura trasferisci_immobile (come da file originale)
CREATE OR REPLACE PROCEDURE trasferisci_immobile(
    p_immobile_id INTEGER,
    p_nuova_partita_id INTEGER,
    p_registra_variazione BOOLEAN DEFAULT FALSE
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_vecchia_partita_id INTEGER;
    v_nuova_partita_attiva BOOLEAN;
    v_variazione_id INTEGER;
BEGIN
    -- Verifica che l'immobile esista
    SELECT partita_id INTO v_vecchia_partita_id FROM immobile WHERE id = p_immobile_id;
    IF NOT FOUND THEN RAISE EXCEPTION 'Immobile con ID % non trovato', p_immobile_id; END IF;

    -- Verifica che la nuova partita esista ed è attiva
    SELECT stato = 'attiva' INTO v_nuova_partita_attiva FROM partita WHERE id = p_nuova_partita_id;
    IF NOT FOUND OR v_nuova_partita_attiva IS FALSE THEN
        RAISE EXCEPTION 'La nuova partita con ID % non esiste o non è attiva', p_nuova_partita_id;
    END IF;

    -- Verifica che le partite non siano le stesse
    IF v_vecchia_partita_id = p_nuova_partita_id THEN
        RAISE EXCEPTION 'Impossibile trasferire immobile alla stessa partita (ID: %)', p_nuova_partita_id;
    END IF;

    -- Registra una variazione se richiesto
    IF p_registra_variazione THEN
        INSERT INTO variazione(
            partita_origine_id, partita_destinazione_id, tipo, data_variazione,
            numero_riferimento, nominativo_riferimento
        ) VALUES (
            v_vecchia_partita_id, p_nuova_partita_id, 'Trasferimento', CURRENT_DATE,
            'TI-' || p_immobile_id, 'Trasferimento immobile ID ' || p_immobile_id
        )
        RETURNING id INTO v_variazione_id;
        RAISE NOTICE 'Registrata variazione con ID % per il trasferimento dell''immobile', v_variazione_id;
    END IF;

    -- Trasferisce l'immobile
    UPDATE immobile SET partita_id = p_nuova_partita_id, data_modifica = CURRENT_TIMESTAMP
    WHERE id = p_immobile_id;

    RAISE NOTICE 'Immobile con ID % trasferito con successo dalla partita ID % alla partita ID %',
                p_immobile_id, v_vecchia_partita_id, p_nuova_partita_id;
END;
$$;

-- Funzione esporta_partita_json (come da file originale, ma usa comune_id e JOIN)
CREATE OR REPLACE FUNCTION catasto.esporta_partita_json(p_partita_id integer)
 RETURNS jsonb
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_partita_details jsonb;
    v_possessori jsonb;
    v_immobili jsonb;
    v_variazioni jsonb;
BEGIN
    -- Dettagli Partita (con suffisso)
    SELECT to_jsonb(p.*) || jsonb_build_object('comune_nome', c.nome)
    INTO v_partita_details
    FROM catasto.partita p
    JOIN catasto.comune c ON p.comune_id = c.id
    WHERE p.id = p_partita_id;

    -- Possessori
    SELECT jsonb_agg(to_jsonb(poss_data))
    INTO v_possessori
    FROM (
        SELECT pos.id, pos.nome_completo, pp.titolo, pp.quota
        FROM catasto.possessore pos
        JOIN catasto.partita_possessore pp ON pos.id = pp.possessore_id
        WHERE pp.partita_id = p_partita_id
        ORDER BY pos.nome_completo
    ) AS poss_data;

    -- Immobili
    SELECT jsonb_agg(to_jsonb(imm_data))
    INTO v_immobili
    FROM (
        SELECT i.id, i.natura, l.nome as localita_nome, i.classificazione, i.consistenza, l.civico
        FROM catasto.immobile i
        JOIN catasto.localita l ON i.localita_id = l.id
        WHERE i.partita_id = p_partita_id
    ) AS imm_data;

    -- Variazioni
    SELECT jsonb_agg(to_jsonb(var_data))
    INTO v_variazioni
    FROM (
        SELECT v.*, con.tipo as contratto_tipo, con.data_contratto, con.notaio
        FROM catasto.variazione v
        LEFT JOIN catasto.contratto con ON v.id = con.variazione_id
        WHERE v.partita_origine_id = p_partita_id OR v.partita_destinazione_id = p_partita_id
        ORDER BY v.data_variazione
    ) AS var_data;

    -- Costruzione JSON finale
    RETURN jsonb_build_object(
        'partita', COALESCE(v_partita_details, '{}'::jsonb),
        'possessori', COALESCE(v_possessori, '[]'::jsonb),
        'immobili', COALESCE(v_immobili, '[]'::jsonb),
        'variazioni', COALESCE(v_variazioni, '[]'::jsonb)
    );
END;
$function$;

-- Funzione esporta_possessore_json (come da file originale, ma usa comune_id e JOIN)
CREATE OR REPLACE FUNCTION catasto.esporta_possessore_json(p_possessore_id integer)
 RETURNS jsonb
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_possessore_details jsonb;
    v_partite jsonb;
    v_immobili jsonb;
BEGIN
    -- Dettagli Possessore
    SELECT to_jsonb(p.*) || jsonb_build_object('comune_nome', c.nome)
    INTO v_possessore_details
    FROM catasto.possessore p
    JOIN catasto.comune c ON p.comune_id = c.id
    WHERE p.id = p_possessore_id;

    -- Partite associate (con suffisso)
    SELECT jsonb_agg(to_jsonb(part_data))
    INTO v_partite
    FROM (
        SELECT p.id, p.numero_partita, p.suffisso_partita, c.nome as comune_nome, p.tipo, pp.quota, pp.titolo
        FROM catasto.partita p
        JOIN catasto.partita_possessore pp ON p.id = pp.partita_id
        JOIN catasto.comune c ON p.comune_id = c.id
        WHERE pp.possessore_id = p_possessore_id
        ORDER BY c.nome, p.numero_partita
    ) AS part_data;

    -- Immobili associati indirettamente
    SELECT jsonb_agg(to_jsonb(imm_data))
    INTO v_immobili
    FROM (
        SELECT i.id, i.natura, l.nome as localita_nome, p.numero_partita, c.nome as comune_nome
        FROM catasto.immobile i
        JOIN catasto.localita l ON i.localita_id = l.id
        JOIN catasto.partita p ON i.partita_id = p.id
        JOIN catasto.comune c ON p.comune_id = c.id
        WHERE p.id IN (SELECT partita_id FROM catasto.partita_possessore WHERE possessore_id = p_possessore_id)
    ) AS imm_data;

    RETURN jsonb_build_object(
        'possessore', COALESCE(v_possessore_details, '{}'::jsonb),
        'partite', COALESCE(v_partite, '[]'::jsonb),
        'immobili', COALESCE(v_immobili, '[]'::jsonb)
    );
END;
$function$;

-- Funzione genera_report_comune (CORRETTA)
CREATE OR REPLACE FUNCTION genera_report_comune(
    p_comune_id INTEGER -- Modificato parametro da VARCHAR a INTEGER
)
-- *** CORREZIONE QUI: Definizione esplicita delle colonne restituite ***
RETURNS TABLE (
    comune VARCHAR,
    totale_partite BIGINT,
    totale_possessori BIGINT,
    totale_immobili BIGINT,
    partite_attive BIGINT,
    partite_inattive BIGINT,
    immobili_per_classe JSON,
    possessori_per_partita NUMERIC
) AS $$
BEGIN
    RETURN QUERY
    WITH comune_base AS ( -- CTE per ottenere il nome del comune dall'ID
        SELECT id, nome FROM comune WHERE id = p_comune_id LIMIT 1
    ),
    immobili_conteggio_classe AS ( -- Conteggio immobili per classificazione
        SELECT
            p.comune_id, -- Usiamo comune_id per il raggruppamento
            COALESCE(i.classificazione, 'Non Class.') AS classificazione_grp,
            COUNT(*) AS conteggio
        FROM immobile i
        JOIN partita p ON i.partita_id = p.id
        WHERE p.comune_id = p_comune_id -- Filtra per ID comune
        GROUP BY p.comune_id, classificazione_grp
    ),
    immobili_json_final AS ( -- Aggrega i conteggi in un JSON
        SELECT
            icc.comune_id,
            json_object_agg(icc.classificazione_grp, icc.conteggio) AS immobili_json
        FROM immobili_conteggio_classe icc
        GROUP BY icc.comune_id
    ),
    stats AS ( -- Calcola le statistiche generali per il comune
        SELECT
            c.id AS comune_id, -- Usa comune_id
            COUNT(DISTINCT p.id) AS totale_partite,
            COUNT(DISTINCT pos.id) AS totale_possessori,
            COUNT(DISTINCT i.id) AS totale_immobili,
            COUNT(DISTINCT CASE WHEN p.stato = 'attiva' THEN p.id END) AS partite_attive,
            COUNT(DISTINCT CASE WHEN p.stato = 'inattiva' THEN p.id END) AS partite_inattive
        FROM comune c
        LEFT JOIN partita p ON c.id = p.comune_id
        LEFT JOIN partita_possessore pp ON p.id = pp.partita_id
        LEFT JOIN possessore pos ON pp.possessore_id = pos.id
        LEFT JOIN immobile i ON p.id = i.partita_id
        WHERE c.id = p_comune_id -- Filtra per ID comune
        GROUP BY c.id
    )
    -- Query finale che combina i risultati
    SELECT
        cb.nome AS comune, -- Prende il nome dalla CTE comune_base
        COALESCE(s.totale_partite, 0) AS totale_partite,
        COALESCE(s.totale_possessori, 0) AS totale_possessori,
        COALESCE(s.totale_immobili, 0) AS totale_immobili,
        COALESCE(s.partite_attive, 0) AS partite_attive,
        COALESCE(s.partite_inattive, 0) AS partite_inattive,
        ijf.immobili_json AS immobili_per_classe,
        CASE -- Calcola possessori per partita
            WHEN COALESCE(s.totale_partite, 0) = 0 THEN 0
            ELSE COALESCE(s.totale_possessori, 0)::NUMERIC / s.totale_partite
        END AS possessori_per_partita
    FROM comune_base cb -- Parte dalla CTE comune_base
    LEFT JOIN stats s ON cb.id = s.comune_id -- Join con le statistiche
    LEFT JOIN immobili_json_final ijf ON cb.id = ijf.comune_id; -- Join con il JSON degli immobili

END;
$$ LANGUAGE plpgsql;