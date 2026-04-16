-- Inserimento utente amministratore di default
-- ATTENZIONE: Il seguente hash è per la password 'admin123'. 
-- CAMBIARE QUESTA PASSWORD E RIGENERARE L'HASH IN UN AMBIENTE DI PRODUZIONE!
-- Per generare l'hash, puoi usare uno script Python temporaneo:
-- import bcrypt
-- password = b'admin123' # O la password desiderata
-- salt = bcrypt.gensalt()
-- hashed = bcrypt.hashpw(password, salt)
-- print(hashed.decode('utf-8'))

DO $$
DECLARE
    admin_username TEXT := 'admin';
    admin_email TEXT := 'admin@archivio.savona.it'; -- Modificare se necessario
    -- Esempio di hash bcrypt per 'admin123' (QUESTO È SOLO UN ESEMPIO, GENERANE UNO TUO!)
    admin_password_hash TEXT := '$2b$12$r0aa.7569LtbyofetxSRtOWZzWAQDbD9XTC1SQ4bHVXDURlQwXszy'; -- SOSTITUIRE CON UN HASH REALE
    user_exists BOOLEAN;
BEGIN
    SELECT EXISTS(SELECT 1 FROM catasto.utente WHERE username = admin_username) INTO user_exists;

    IF NOT user_exists THEN
        INSERT INTO catasto.utente (username, password_hash, nome_completo, email, ruolo, attivo)
        VALUES (admin_username, admin_password_hash, 'Amministratore Sistema', admin_email, 'admin', TRUE);
        RAISE NOTICE 'Utente amministratore di default "%" creato.', admin_username;
    ELSE
        RAISE NOTICE 'Utente amministratore di default "%" già esistente.', admin_username;
    END IF;
END $$;