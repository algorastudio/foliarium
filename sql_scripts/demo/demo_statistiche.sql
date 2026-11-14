-- =============================================================================
-- demo/demo_statistiche.sql
-- Da applicare DOPO demo_data.sql.
--
-- Le viste materializzate vengono create quando le tabelle sono ancora vuote.
-- Caricato l'archivio dimostrativo vanno ricalcolate, altrimenti le pagine di
-- statistica e i report mostrerebbero dati vuoti finche' qualcuno non preme
-- «Aggiorna Ora», e la barra «dati non aggiornati» partirebbe dalla data
-- fittizia con cui nasce app_metadata (01/01/2000: oltre 235.000 ore).
--
-- Fa le stesse due cose di CatastoDBManager.refresh_materialized_views():
-- ricalcola tutte le viste materializzate dello schema e registra l'ora.
-- La colonna e' TIMESTAMPTZ: basta NOW(), senza conversioni di fuso.
-- Un errore qui ferma lo script: non si usa aggiorna_tutte_statistiche(),
-- che lo trasformerebbe in un semplice avviso.
-- =============================================================================

\set ON_ERROR_STOP on

DO $$
DECLARE
    vista record;
BEGIN
    FOR vista IN
        SELECT schemaname, matviewname
        FROM pg_matviews
        WHERE schemaname = 'catasto'
        ORDER BY matviewname
    LOOP
        EXECUTE 'REFRESH MATERIALIZED VIEW '
            || quote_ident(vista.schemaname) || '.' || quote_ident(vista.matviewname);
    END LOOP;
END $$;

INSERT INTO catasto.app_metadata (key, value_timestamp)
VALUES ('last_mv_refresh', NOW())
ON CONFLICT (key) DO UPDATE SET value_timestamp = EXCLUDED.value_timestamp;
