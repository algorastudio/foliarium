-- Script di migrazione v1.6.1
-- Incorpora il civico nel campo nome della tabella localita
-- Rimuove la colonna civico e semplifica l'UNIQUE constraint

BEGIN;

-- 1. Aggiorna i nomi incorporando il civico
UPDATE localita
SET nome = CASE
    WHEN civico IS NOT NULL AND civico != '' THEN CONCAT(nome, ' ', civico)
    ELSE nome
END
WHERE civico IS NOT NULL AND civico != '';

-- 2. Rimuovi l'UNIQUE constraint vecchio
ALTER TABLE localita
DROP CONSTRAINT IF EXISTS localita_comune_id_nome_civico_key;

-- 3. Aggiungi il nuovo UNIQUE constraint su (comune_id, nome)
ALTER TABLE localita
ADD CONSTRAINT localita_comune_id_nome_unique UNIQUE (comune_id, nome);

-- 4. Rimuovi la colonna civico
ALTER TABLE localita
DROP COLUMN civico;

-- 5. Aggiorna il commento della tabella
COMMENT ON TABLE localita IS 'Località o indirizzi degli immobili (comune_id + nome univoco). Civico incorporato nel nome.';

COMMIT;
