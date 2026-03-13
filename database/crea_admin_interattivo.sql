-- File: crea_admin_interattivo.sql
-- Script interattivo per creare un nuovo admin.
-- ATTENZIONE: Eseguire esclusivamente tramite il client psql.

-- '*** CREAZIONE NUOVO UTENTE AMMINISTRATORE PER MERIDIANA ***'
-- '-------------------------------------------------------'
-- 'Passo 2 -> Inserisci i dettagli del nuovo utente qui sotto.'
-- ''

-- Richieste interattive per l'utente
\prompt 'Inserisci il nuovo username: ' v_username
\prompt 'Inserisci il nome completo (es. Mario Rossi): ' v_nome_completo
\prompt 'Inserisci l''email (deve essere unica): ' v_email
\prompt 'Incolla l''hash della password generato al Passo 1 e premi Invio: ' v_password_hash

-- Inizio del blocco di transazione
BEGIN;

-- Imposta lo schema per la sessione
SET search_path TO catasto, public;

-- Esegue l'inserimento utilizzando le variabili popolate interattivamente
-- La sintassi :'nome_variabile' è specifica di psql
INSERT INTO utente (username, password_hash, nome_completo, email, ruolo, attivo)
SELECT
    :'v_username',
    :'v_password_hash',
    :'v_nome_completo',
    :'v_email',
    'admin',
    TRUE
WHERE NOT EXISTS (
    SELECT 1 FROM utente WHERE username = :'v_username' OR email = :'v_email'
);

-- Controlla se l'inserimento è avvenuto
GET DIAGNOSTICS row_count = ROW_COUNT;
\if :row_count > 0
    -- '\nSUCCESS: Utente amministratore "' :'v_username' '" creato con successo nel database.'
\else
    -- '\nATTENZIONE: L''utente "' :'v_username' '" o l''email "' :'v_email' '" esistono già. Nessuna modifica effettuata.'
\endif

-- Fine della transazione
COMMIT;

-- '-------------------------------------------------------'