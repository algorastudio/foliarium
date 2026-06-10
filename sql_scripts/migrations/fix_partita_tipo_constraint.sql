-- Migration: estende il vincolo partita_tipo_check per includere 'enfiteusi' e 'usufrutto'
-- I due tipi aggiuntivi erano già presenti nell'interfaccia utente ma non nel vincolo DB.

ALTER TABLE catasto.partita
    DROP CONSTRAINT IF EXISTS partita_tipo_check;

ALTER TABLE catasto.partita
    ADD CONSTRAINT partita_tipo_check
        CHECK (tipo IN ('principale', 'secondaria', 'enfiteusi', 'usufrutto'));
