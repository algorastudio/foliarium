-- Script di migrazione v1.7.0
-- Separa il civico dalla località:
--   PRIMA:  localita.nome = "Repubblica 17" (civico embedded da v1.6.1)
--   DOPO:   localita.nome = "Repubblica" + immobile.numero_civico = "17"
--
-- Inoltre: tipologia_stradale diventa NOT NULL (selezione obbligatoria
-- da elenco tipo_localita: Via, Piazza, Borgata, Regione, ecc.).
--
-- Idempotente: può essere eseguito più volte senza errori.

BEGIN;

-- ============================================================================
-- 1. Aggiungi colonna numero_civico a immobile (alfanumerico per "17/A", "s.n.c.")
-- ============================================================================
ALTER TABLE immobile
    ADD COLUMN IF NOT EXISTS numero_civico VARCHAR(20);

COMMENT ON COLUMN immobile.numero_civico IS
    'Numero civico (alfanumerico: es. ''17'', ''17/A'', ''s.n.c.'', ''3 bis'')';

-- ============================================================================
-- 2. Estrai il civico dal nome località e popola immobile.numero_civico
--    Regex: pattern terminale che inizia con cifre, opzionalmente seguito da
--    suffissi tipici (/A, bis, ter, lettere singole, ecc.).
-- ============================================================================
UPDATE immobile i
SET numero_civico = trim((regexp_match(l.nome, '\s+(\d+[A-Za-z0-9/\s\.\-]*)$'))[1])
FROM localita l
WHERE i.localita_id = l.id
  AND l.nome ~ '\s+\d+[A-Za-z0-9/\s\.\-]*$'
  AND (i.numero_civico IS NULL OR i.numero_civico = '');

-- ============================================================================
-- 3. Drop temporaneamente UNIQUE constraint per permettere il merge dei duplicati
-- ============================================================================
ALTER TABLE localita DROP CONSTRAINT IF EXISTS localita_comune_id_nome_unique;
ALTER TABLE localita DROP CONSTRAINT IF EXISTS localita_comune_id_nome_key;

-- ============================================================================
-- 4. Normalizza localita.nome rimuovendo la parte civico
-- ============================================================================
UPDATE localita
SET nome = trim(regexp_replace(nome, '\s+\d+[A-Za-z0-9/\s\.\-]*$', ''))
WHERE nome ~ '\s+\d+[A-Za-z0-9/\s\.\-]*$';

-- ============================================================================
-- 5. Deduplica: per ogni (comune_id, nome, tipologia_stradale) tieni il MIN(id)
--    come canonical, redirigi le FK su immobile, elimina i duplicati.
--    NOTA: il group-by considera anche tipologia_stradale per non fondere
--    "Via Repubblica" con "Piazza Repubblica".
-- ============================================================================
CREATE TEMP TABLE localita_dedup ON COMMIT DROP AS
SELECT
    MIN(id)                                  AS canonical_id,
    array_agg(id ORDER BY id)                AS all_ids,
    comune_id,
    nome,
    COALESCE(tipologia_stradale, '')         AS tipologia_norm
FROM localita
GROUP BY comune_id, nome, COALESCE(tipologia_stradale, '')
HAVING COUNT(*) > 1;

-- Aggiorna immobile.localita_id verso il canonical_id
UPDATE immobile i
SET localita_id = ld.canonical_id
FROM localita_dedup ld
WHERE i.localita_id = ANY(ld.all_ids)
  AND i.localita_id <> ld.canonical_id;

-- Elimina i duplicati non canonical
DELETE FROM localita l
USING localita_dedup ld
WHERE l.id = ANY(ld.all_ids)
  AND l.id <> ld.canonical_id;

-- ============================================================================
-- 6. Reinstaura UNIQUE constraint su (comune_id, nome)
--    NOTA: includiamo anche tipologia_stradale per consentire, in futuro,
--    "Via Garibaldi" e "Piazza Garibaldi" come località distinte.
-- ============================================================================
ALTER TABLE localita
    ADD CONSTRAINT localita_comune_nome_tipo_unique
    UNIQUE (comune_id, nome, tipologia_stradale);

-- ============================================================================
-- 7. Backfill tipologia_stradale per le righe NULL (default 'Via', più comune)
-- ============================================================================
UPDATE localita
SET tipologia_stradale = 'Via'
WHERE tipologia_stradale IS NULL OR tipologia_stradale = '';

-- ============================================================================
-- 8. tipologia_stradale NOT NULL
-- ============================================================================
ALTER TABLE localita
    ALTER COLUMN tipologia_stradale SET NOT NULL;

-- ============================================================================
-- 9. Aggiorna commenti
-- ============================================================================
COMMENT ON TABLE localita IS
    'Località degli immobili. Solo nome strada (senza civico) + tipologia_stradale obbligatoria. Civico in immobile.numero_civico.';

COMMENT ON COLUMN localita.nome IS
    'Nome della località senza civico (es. ''Repubblica'', ''Garibaldi''). Univoco per (comune_id, nome, tipologia_stradale).';

COMMENT ON COLUMN localita.tipologia_stradale IS
    'Tipologia (obbligatoria): Via, Piazza, Borgata, Regione, Frazione, ecc. Valori popolati da tipo_localita.';

-- ============================================================================
-- 10. Ricrea procedure SQL che ora supportano numero_civico
-- ============================================================================
CREATE OR REPLACE PROCEDURE aggiorna_immobile(
    p_id INTEGER,
    p_natura VARCHAR(100) DEFAULT NULL,
    p_numero_piani INTEGER DEFAULT NULL,
    p_numero_vani INTEGER DEFAULT NULL,
    p_consistenza VARCHAR(255) DEFAULT NULL,
    p_classificazione VARCHAR(100) DEFAULT NULL,
    p_localita_id INTEGER DEFAULT NULL,
    p_numero_civico VARCHAR(20) DEFAULT NULL
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
        numero_civico = COALESCE(p_numero_civico, numero_civico),
        data_modifica = CURRENT_TIMESTAMP
    WHERE id = p_id;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Immobile con ID % non trovato', p_id;
    END IF;
END;
$$;

COMMIT;
