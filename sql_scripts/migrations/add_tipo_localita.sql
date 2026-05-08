-- File: 20_feature_tipi_localita.sql (v1.2 - Idempotente)
-- Scopo: Rende le tipologie di località un'entità gestibile dinamicamente.
-- Note: Questo script può essere eseguito più volte senza causare errori.

SET search_path TO catasto, public;

DO $$
BEGIN

-- 1. Creare la nuova tabella per le tipologie di località
CREATE TABLE IF NOT EXISTS tipo_localita (
    id SERIAL PRIMARY KEY,
    nome VARCHAR(50) NOT NULL UNIQUE,
    descrizione TEXT
);
RAISE NOTICE 'Tabella tipo_localita verificata/creata.';

-- 2. Popolare la nuova tabella con i valori di default
INSERT INTO tipo_localita (nome) VALUES
('Regione'), ('Via'), ('Borgata'), ('Altro')
ON CONFLICT (nome) DO NOTHING;
RAISE NOTICE 'Dati di default per tipo_localita inseriti/verificati.';

-- 3. Aggiungere la nuova colonna tipo_id alla tabella localita, se non esiste
IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='localita' AND column_name='tipo_id' AND table_schema='catasto') THEN
    ALTER TABLE localita ADD COLUMN tipo_id INTEGER REFERENCES tipo_localita(id);
    RAISE NOTICE 'Colonna "tipo_id" aggiunta a localita.';
END IF;

-- 4. Eseguire la migrazione dei dati SOLO SE la vecchia colonna 'tipo' esiste ancora
IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='localita' AND column_name='tipo' AND table_schema='catasto') THEN
    RAISE NOTICE 'Trovata vecchia colonna "tipo". Eseguo la migrazione dei dati a "tipo_id"...';
    UPDATE localita l SET tipo_id = tl.id FROM tipo_localita tl WHERE l.tipo = tl.nome;
    RAISE NOTICE 'Migrazione dati completata.';

    -- 5. Rimuovere la vecchia colonna 'tipo' solo dopo una migrazione riuscita
    ALTER TABLE localita DROP COLUMN tipo;
    RAISE NOTICE 'Vecchia colonna "tipo" rimossa.';
ELSE
    RAISE NOTICE 'Vecchia colonna "tipo" non trovata. Migrazione e rimozione saltate.';
END IF;

-- 6. Rendere la nuova colonna non nulla, ma solo se non ci sono valori NULL
IF EXISTS (SELECT 1 FROM localita WHERE tipo_id IS NULL) THEN
    RAISE WARNING 'ATTENZIONE: Esistono località con tipo_id NULL. Impossibile impostare la colonna a NOT NULL. Correggere i dati manualmente.';
ELSE
    ALTER TABLE localita ALTER COLUMN tipo_id SET NOT NULL;
    RAISE NOTICE 'Colonna "tipo_id" impostata a NOT NULL.';
END IF;

END $$;

-- 'Script per la gestione dinamica dei tipi di località eseguito con successo.';

-- ========================================================================
-- Fine Script
-- ======================================================================== 