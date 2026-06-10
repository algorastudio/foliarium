-- sql_scripts/migrations/19_create_v_audit_dettagliato.sql
--
-- Migrazione idempotente: crea la vista catasto.v_audit_dettagliato se
-- mancante. La vista era stata aggiunta nello script
-- 18_funzioni_trigger_audit.sql ma alcuni DB inizializzati prima della
-- v1.0 non la contengono e crashano con UndefinedTable quando si apre
-- "Visualizzatore Audit Log" (db/audit.py::get_audit_logs).
--
-- Esecuzione:
--   psql -U postgres -d catasto_storico -f 19_create_v_audit_dettagliato.sql
--
-- Sicurezza: CREATE OR REPLACE — non distrugge dati. Idempotente.

SET search_path TO catasto, public;

CREATE OR REPLACE VIEW catasto.v_audit_dettagliato AS
SELECT
    al.id,
    CAST(al.timestamp AS TIMESTAMP(0)) AS timestamp,
    al.app_user_id,
    u.username,
    u.nome_completo,
    al.session_id,
    al.tabella,
    al.operazione,
    al.record_id,
    al.ip_address,
    al.utente AS db_user,
    al.dati_prima,
    al.dati_dopo
FROM
    catasto.audit_log al
LEFT JOIN
    catasto.utente u ON al.app_user_id = u.id;

COMMENT ON VIEW catasto.v_audit_dettagliato IS
    'Vista che unisce i log di audit con i nomi degli utenti applicativi '
    '(timestamp formattato senza millisecondi).';

-- Verifica conclusiva (utile in psql interattivo)
SELECT 'Vista catasto.v_audit_dettagliato creata o gia presente.' AS stato;
