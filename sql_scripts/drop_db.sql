-- Script per cancellare il database catasto_storico
-- ATTENZIONE: Questa operazione è irreversibile!
-- Assicurati di essere connesso a un database DIVERSO (es. postgres) prima di lanciare questo script.

DROP DATABASE catasto_storico WITH (FORCE);

-- L'opzione WITH (FORCE) (PostgreSQL 13+) tenta di terminare le connessioni esistenti.
-- Se usi una versione precedente o preferisci terminare le connessioni manualmente,
-- rimuovi WITH (FORCE) e assicurati che non ci siano connessioni attive.

-- Se non usi WITH (FORCE), potresti dover prima terminare le connessioni:
-- SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = 'catasto_storico';
-- DROP DATABASE catasto_storico;

\q