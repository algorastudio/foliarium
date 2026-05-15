-- File: 00_svuota_dati.sql (Nuova Versione - Più Robusta)
-- Oggetto: Ricrea completamente lo schema 'catasto' per una pulizia totale.
-- USO: Eseguire PRIMA di qualsiasi altro script di setup.

-- ATTENZIONE: Questa operazione è distruttiva e cancellerà TUTTE le tabelle,
-- le funzioni, le viste e i dati all'interno dello schema 'catasto'.

-- Imposta un timeout per il lock, per evitare attese infinite
-- se un'altra sessione dovesse bloccare lo schema.
SET lock_timeout = '5s';

-- Elimina lo schema 'catasto' e tutti gli oggetti al suo interno in cascata.
-- IF EXISTS previene errori se lo schema non dovesse esistere.
DROP SCHEMA IF EXISTS catasto CASCADE;

-- Ricrea lo schema vuoto, pronto per essere popolato dallo script successivo.
CREATE SCHEMA catasto;

-- Imposta il percorso di ricerca per la sessione corrente, in modo che
-- lo script 02_creazione-schema-tabelle funzioni correttamente.
SET search_path TO catasto, public;

-- Non è necessario un \echo perché lo script Python logga già l'esecuzione.
-- Se si desidera un messaggio, usare: RAISE NOTICE 'Schema catasto ricreato con successo.';