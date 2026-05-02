-- sql_scripts/07_create_tipo_possesso_table.sql
-- Tabella di lookup per i tipi di possesso
-- Da eseguire dopo la creazione dello schema base

CREATE TABLE IF NOT EXISTS public.tipo_possesso (
    id SERIAL PRIMARY KEY,
    nome VARCHAR(50) NOT NULL UNIQUE,
    descrizione TEXT,
    data_creazione TIMESTAMP(0) DEFAULT CURRENT_TIMESTAMP,
    data_modifica TIMESTAMP(0) DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE tipo_possesso IS 'Lookup table per i tipi di possesso (proprietà esclusiva, comproprietà, usufrutto, etc.)';
COMMENT ON COLUMN tipo_possesso.nome IS 'Nome del tipo di possesso (es. "proprietà esclusiva")';
COMMENT ON COLUMN tipo_possesso.descrizione IS 'Descrizione opzionale per chiarire il tipo';

-- Inserisci i tipi predefiniti comuni
INSERT INTO public.tipo_possesso (nome, descrizione) VALUES
    ('proprietà esclusiva', 'Pieno diritto di proprietà esclusivo'),
    ('comproprietà', 'Proprietà condivisa con altri soggetti'),
    ('usufrutto', 'Diritto di uso e godimento della proprietà altrui'),
    ('nuda proprietà', 'Proprietà separata dall''usufrutto'),
    ('enfiteusi', 'Diritto perpetuo di godere il bene altrui'),
    ('superficie', 'Diritto di costruire o costruito su suolo altrui'),
    ('servitù', 'Diritto limitato di passaggio o altro uso'),
    ('altro', 'Altro tipo di diritto/titolo non classificato')
ON CONFLICT (nome) DO NOTHING;
