-- Script di migrazione v1.6.1+
-- Rimuove la colonna tipo_id dalla tabella localita.
-- La colonna tipologia_stradale (VARCHAR) è già presente e contiene il valore testuale del tipo.
-- Eseguire DOPO 06_migrate_civico_to_nome.sql (se non ancora applicata).
--
-- Idempotente: usa IF EXISTS ovunque, può essere rieseguito senza errori.

BEGIN;

-- 1. Copia il nome del tipo da tipo_localita → tipologia_stradale per le righe che
--    hanno ancora tipo_id valorizzato e tipologia_stradale NULL/vuoto.
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = current_schema()
          AND table_name = 'localita'
          AND column_name = 'tipo_id'
    ) THEN
        UPDATE localita l
        SET tipologia_stradale = tl.nome
        FROM tipo_localita tl
        WHERE l.tipo_id = tl.id
          AND (l.tipologia_stradale IS NULL OR l.tipologia_stradale = '');
        RAISE NOTICE 'tipologia_stradale popolata da tipo_localita dove necessario.';
    ELSE
        RAISE NOTICE 'Colonna tipo_id non presente; migrazione dati saltata.';
    END IF;
END;
$$;

-- 2. Rimuovi il vincolo FK su tipo_id (se esiste).
DO $$
DECLARE
    v_constraint TEXT;
BEGIN
    SELECT con.conname INTO v_constraint
    FROM pg_constraint con
    JOIN pg_class rel ON rel.oid = con.conrelid
    JOIN pg_namespace ns ON ns.oid = rel.relnamespace
    WHERE rel.relname = 'localita'
      AND ns.nspname = current_schema()
      AND con.contype = 'f'
      AND con.conname ILIKE '%tipo%';

    IF v_constraint IS NOT NULL THEN
        EXECUTE format('ALTER TABLE localita DROP CONSTRAINT IF EXISTS %I', v_constraint);
        RAISE NOTICE 'Rimosso FK constraint: %', v_constraint;
    ELSE
        RAISE NOTICE 'Nessun FK constraint su tipo_id trovato; saltato.';
    END IF;
END;
$$;

-- 3. Rimuovi la colonna tipo_id.
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = current_schema()
          AND table_name = 'localita'
          AND column_name = 'tipo_id'
    ) THEN
        ALTER TABLE localita DROP COLUMN tipo_id;
        RAISE NOTICE 'Colonna tipo_id rimossa da localita.';
    ELSE
        RAISE NOTICE 'Colonna tipo_id già assente; saltato.';
    END IF;
END;
$$;

-- 4. (Opzionale) Se civico è ancora presente, rimuovilo anch'esso.
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = current_schema()
          AND table_name = 'localita'
          AND column_name = 'civico'
    ) THEN
        -- Concatena civico al nome prima di rimuoverlo.
        UPDATE localita
        SET nome = CONCAT(nome, ' ', civico)
        WHERE civico IS NOT NULL AND civico != '';

        ALTER TABLE localita DROP CONSTRAINT IF EXISTS localita_comune_id_nome_civico_key;
        ALTER TABLE localita DROP COLUMN civico;
        RAISE NOTICE 'Colonna civico rimossa (dati incorporati nel nome).';
    ELSE
        RAISE NOTICE 'Colonna civico già assente; saltato.';
    END IF;
END;
$$;

-- 5. Assicura UNIQUE constraint corretto su (comune_id, nome).
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint con
        JOIN pg_class rel ON rel.oid = con.conrelid
        JOIN pg_namespace ns ON ns.oid = rel.relnamespace
        WHERE rel.relname = 'localita'
          AND ns.nspname = current_schema()
          AND con.contype = 'u'
          AND con.conname = 'localita_comune_id_nome_unique'
    ) THEN
        ALTER TABLE localita ADD CONSTRAINT localita_comune_id_nome_unique UNIQUE (comune_id, nome);
        RAISE NOTICE 'Aggiunto UNIQUE constraint (comune_id, nome).';
    ELSE
        RAISE NOTICE 'UNIQUE constraint già presente; saltato.';
    END IF;
END;
$$;

COMMIT;
