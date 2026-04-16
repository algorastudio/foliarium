-- Imposta lo schema
SET search_path TO catasto;

-- Tabella per tenere traccia dei backup
CREATE TABLE backup_registro (
    id SERIAL PRIMARY KEY,
    nome_file VARCHAR(255) NOT NULL,
    timestamp TIMESTAMP(0) DEFAULT CURRENT_TIMESTAMP,
    utente VARCHAR(100) NOT NULL,
    dimensione_bytes BIGINT,
    tipo VARCHAR(20) NOT NULL CHECK (tipo IN ('completo', 'schema', 'dati')),
    esito BOOLEAN NOT NULL,
    messaggio TEXT,
    percorso_file TEXT NOT NULL
);

CREATE INDEX idx_backup_timestamp ON backup_registro(timestamp);
CREATE INDEX idx_backup_tipo ON backup_registro(tipo);

-- Funzione per registrare un backup nel registro
CREATE OR REPLACE FUNCTION registra_backup(
    p_nome_file VARCHAR(255),
    p_utente VARCHAR(100),
    p_dimensione_bytes BIGINT,
    p_tipo VARCHAR(20),
    p_esito BOOLEAN,
    p_messaggio TEXT,
    p_percorso_file TEXT
)
RETURNS INTEGER AS $$
DECLARE
    v_backup_id INTEGER;
BEGIN
    INSERT INTO backup_registro (nome_file, utente, dimensione_bytes, tipo, esito, messaggio, percorso_file)
    VALUES (p_nome_file, p_utente, p_dimensione_bytes, p_tipo, p_esito, p_messaggio, p_percorso_file)
    RETURNING id INTO v_backup_id;
    
    RETURN v_backup_id;
END;
$$ LANGUAGE plpgsql;

-- Funzione per ottenere i comandi SQL per il backup
CREATE OR REPLACE FUNCTION get_backup_commands(p_tipo VARCHAR DEFAULT 'completo')
RETURNS TEXT AS $$
DECLARE
    v_timestamp TEXT;
    v_comando TEXT;
    v_filename TEXT;
    v_backup_dir TEXT := '/path/to/backup/directory'; -- Personalizza questo percorso
BEGIN
    v_timestamp := to_char(current_timestamp, 'YYYYMMDD_HH24MISS');
    
    IF p_tipo = 'completo' THEN
        v_filename := 'catasto_backup_completo_' || v_timestamp || '.sql';
        v_comando := 'pg_dump -U postgres -d catasto_storico -f ' || v_backup_dir || '/' || v_filename;
    ELSIF p_tipo = 'schema' THEN
        v_filename := 'catasto_backup_schema_' || v_timestamp || '.sql';
        v_comando := 'pg_dump -U postgres -d catasto_storico --schema-only -f ' || v_backup_dir || '/' || v_filename;
    ELSIF p_tipo = 'dati' THEN
        v_filename := 'catasto_backup_dati_' || v_timestamp || '.sql';
        v_comando := 'pg_dump -U postgres -d catasto_storico --data-only -f ' || v_backup_dir || '/' || v_filename;
    ELSE
        RAISE EXCEPTION 'Tipo di backup sconosciuto: %', p_tipo;
    END IF;
    
    RETURN E'-- Esegui questo comando dalla riga di comando:\n' || v_comando || E'\n\n-- Quindi registra il backup con:\nSELECT registra_backup(''' 
           || v_filename || ''', current_user, NULL, ''' || p_tipo || ''', TRUE, ''Backup completato con successo'', ''' 
           || v_backup_dir || '/' || v_filename || ''');';
END;
$$ LANGUAGE plpgsql;

-- Funzione per ottenere i comandi di restore
CREATE OR REPLACE FUNCTION get_restore_commands(p_backup_id INTEGER)
RETURNS TEXT AS $$
DECLARE
    v_backup_record backup_registro%ROWTYPE;
    v_comando TEXT;
BEGIN
    SELECT * INTO v_backup_record FROM backup_registro WHERE id = p_backup_id;
    
    IF v_backup_record.id IS NULL THEN
        RAISE EXCEPTION 'Backup ID % non trovato', p_backup_id;
    END IF;
    
    v_comando := 'psql -U postgres -d catasto_storico -f ' || v_backup_record.percorso_file;
    
    RETURN E'-- Esegui questo comando dalla riga di comando per ripristinare il backup:\n' || v_comando;
END;
$$ LANGUAGE plpgsql;

-- Procedura per la pulizia automatica dei backup vecchi
CREATE OR REPLACE PROCEDURE pulizia_backup_vecchi(p_giorni_conservazione INTEGER DEFAULT 30)
LANGUAGE plpgsql
AS $$
DECLARE
    v_data_limite TIMESTAMP(0);
    v_backup_record backup_registro%ROWTYPE;
BEGIN
    v_data_limite := current_timestamp - (p_giorni_conservazione || ' days')::INTERVAL;
    
    -- Identificare i backup da eliminare (nella pratica, qui dovremmo eliminare anche i file)
    FOR v_backup_record IN
        SELECT * FROM backup_registro
        WHERE timestamp < v_data_limite
    LOOP
        -- Qui in un sistema reale dovremmo eliminare il file fisico:
        -- PERFORM pg_catalog.pg_file_unlink(v_backup_record.percorso_file);
        
        -- Log dell'eliminazione
        RAISE NOTICE 'Backup % sarebbe stato eliminato in un sistema reale', v_backup_record.nome_file;
    END LOOP;
    
    -- Rimuovere le voci dal registro
    DELETE FROM backup_registro WHERE timestamp < v_data_limite;
END;
$$;

-- Script per generare un job di backup automatico giornaliero
-- NOTA: Questo è solo un esempio. In PostgreSQL si userebbe pg_cron o un job di sistema esterno
CREATE OR REPLACE FUNCTION genera_script_backup_automatico(p_backup_dir TEXT)
RETURNS TEXT AS $$
DECLARE
    v_script TEXT;
BEGIN
    v_script := E'#!/bin/bash\n\n';
    v_script := v_script || '# Script di backup automatico per Catasto Storico\n';
    v_script := v_script || '# Creato: ' || to_char(current_timestamp, 'YYYY-MM-DD HH24:MI:SS') || '\n\n';
    
    v_script := v_script || 'BACKUP_DIR="' || p_backup_dir || '"\n';
    v_script := v_script || 'TIMESTAMP=$(date +%Y%m%d_%H%M%S)\n';
    v_script := v_script || 'FILENAME="catasto_backup_completo_${TIMESTAMP}.sql"\n';
    v_script := v_script || 'LOGFILE="backup_${TIMESTAMP}.log"\n\n';
    
    v_script := v_script || '# Creazione della directory di backup se non esiste\n';
    v_script := v_script || 'mkdir -p ${BACKUP_DIR}\n\n';
    
    v_script := v_script || '# Esecuzione del backup\n';
    v_script := v_script || 'echo "Inizio backup: $(date)" > ${BACKUP_DIR}/${LOGFILE}\n';
    v_script := v_script || 'pg_dump -U postgres -d catasto_storico -f ${BACKUP_DIR}/${FILENAME} 2>> ${BACKUP_DIR}/${LOGFILE}\n';
    v_script := v_script || 'RESULT=$?\n\n';
    
    v_script := v_script || '# Registrazione del backup nel database\n';
    v_script := v_script || 'if [ $RESULT -eq 0 ]; then\n';
    v_script := v_script || '    echo "Backup completato con successo: $(date)" >> ${BACKUP_DIR}/${LOGFILE}\n';
    v_script := v_script || '    FILESIZE=$(stat -c%s "${BACKUP_DIR}/${FILENAME}")\n';
    v_script := v_script || '    psql -U postgres -d catasto_storico -c "SELECT registra_backup(''${FILENAME}'', ''backup_automatico'', ${FILESIZE}, ''completo'', TRUE, ''Backup completato con successo'', ''${BACKUP_DIR}/${FILENAME}'');" >> ${BACKUP_DIR}/${LOGFILE}\n';
    v_script := v_script || 'else\n';
    v_script := v_script || '    echo "Errore durante il backup: $(date)" >> ${BACKUP_DIR}/${LOGFILE}\n';
    v_script := v_script || '    psql -U postgres -d catasto_storico -c "SELECT registra_backup(''${FILENAME}'', ''backup_automatico'', NULL, ''completo'', FALSE, ''Errore durante il backup'', ''${BACKUP_DIR}/${FILENAME}'');" >> ${BACKUP_DIR}/${LOGFILE}\n';
    v_script := v_script || 'fi\n\n';
    
    v_script := v_script || '# Rimozione backup vecchi (opzionale)\n';
    v_script := v_script || 'psql -U postgres -d catasto_storico -c "CALL pulizia_backup_vecchi(30);" >> ${BACKUP_DIR}/${LOGFILE}\n';
    
    v_script := v_script || '\necho "Processo di backup terminato: $(date)" >> ${BACKUP_DIR}/${LOGFILE}\n';
    
    RETURN v_script;
END;
$$ LANGUAGE plpgsql;