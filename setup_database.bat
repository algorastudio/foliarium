@echo off
REM ============================================================================
REM setup_database.bat — Inizializzazione PostgreSQL + DB Foliarium
REM
REM Eseguito automaticamente dall'installer Inno Setup dopo la copia dei file.
REM Puo' essere rieseguito manualmente per ricreare il database.
REM
REM Parametri (passati da Inno Setup):
REM   %1 = directory di installazione (es. C:\Program Files\Foliarium)
REM   %2 = password per l'utente PostgreSQL 'foliarium' (generata dall'installer)
REM   %3 = password per l'utente admin applicativo (generata dall'installer)
REM ============================================================================
setlocal enabledelayedexpansion

set "INSTALL_DIR=%~1"
set "DB_PASSWORD=%~2"
set "ADMIN_PASSWORD=%~3"

REM --- Percorsi ---
REM PG_DATA va in %ProgramData% perche' 'initdb' non puo' scrivere in
REM Program Files (initdb droppa i privilegi e l'utente non-admin non ha
REM write access). %ProgramData%\Foliarium\ e' la location standard Windows
REM per dati di sistema condivisi tra utenti.
set "PG_BIN=%INSTALL_DIR%\pgsql\bin"
set "DATA_ROOT=%ProgramData%\Foliarium"
set "PG_DATA=%DATA_ROOT%\pg_data"
set "SQL_DIR=%INSTALL_DIR%\sql_scripts"
set "CONFIG_FILE=%INSTALL_DIR%\config.ini"
set "LOGFILE=%INSTALL_DIR%\setup_database.log"

REM Crea la cartella dati condivisa se non esiste
if not exist "%DATA_ROOT%" mkdir "%DATA_ROOT%"

set "DB_NAME=catasto_storico"
set "DB_USER=foliarium"
set "DB_PORT=5432"
set "SERVICE_NAME=FoliariumDB"

echo ============================================== > "%LOGFILE%"
echo  Foliarium — Inizializzazione Database        >> "%LOGFILE%"
echo  %DATE% %TIME%                                >> "%LOGFILE%"
echo ============================================== >> "%LOGFILE%"

REM ============================================================================
REM 1. Verifica che PostgreSQL non sia gia' installato sulla porta 5432
REM ============================================================================
echo [1/8] Verifica porta %DB_PORT%... >> "%LOGFILE%"
netstat -an | findstr ":%DB_PORT% " | findstr "LISTENING" > nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo   ATTENZIONE: porta %DB_PORT% gia' in uso. >> "%LOGFILE%"
    echo   Provo porta 5433... >> "%LOGFILE%"
    set "DB_PORT=5433"
    netstat -an | findstr ":5433 " | findstr "LISTENING" > nul 2>&1
    if !ERRORLEVEL! EQU 0 (
        echo   Anche porta 5433 in uso. Provo 5434... >> "%LOGFILE%"
        set "DB_PORT=5434"
    )
)
echo   Porta selezionata: %DB_PORT% >> "%LOGFILE%"

REM ============================================================================
REM 2. initdb — Creazione cluster PostgreSQL
REM ============================================================================
echo [2/8] Inizializzazione cluster PostgreSQL... >> "%LOGFILE%"
if exist "%PG_DATA%\PG_VERSION" (
    echo   Cluster gia' esistente in pg_data\, skip initdb. >> "%LOGFILE%"
    goto :start_service
)

REM Se pg_data esiste ma non ha PG_VERSION e' un residuo di un'installazione
REM precedente fallita: initdb rifiuta di scrivere in una dir non vuota, quindi
REM la puliamo. Prima pero' proviamo a fermare un eventuale postgres orfano.
if exist "%PG_DATA%" (
    echo   ATTENZIONE: pg_data esiste ma e' incompleto - pulizia in corso... >> "%LOGFILE%"
    REM Prova a fermare un eventuale processo postgres che tiene bloccati i file
    taskkill /F /IM postgres.exe >> "%LOGFILE%" 2>&1
    timeout /t 2 /nobreak > nul
    rmdir /s /q "%PG_DATA%" >> "%LOGFILE%" 2>&1
    if exist "%PG_DATA%" (
        echo ERRORE: impossibile rimuovere %PG_DATA%. >> "%LOGFILE%"
        echo Eliminarlo manualmente e riprovare. >> "%LOGFILE%"
        exit /b 1
    )
)

"%PG_BIN%\initdb.exe" -D "%PG_DATA%" -U postgres --locale=C --encoding=UTF8 --no-instructions >> "%LOGFILE%" 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo ERRORE: initdb fallito. >> "%LOGFILE%"
    exit /b 1
)

REM ============================================================================
REM 3. Configurazione PostgreSQL (postgresql.conf + avvio temporaneo + password)
REM ============================================================================
echo [3/8] Configurazione PostgreSQL... >> "%LOGFILE%"

REM postgresql.conf — impostazioni minimali (pg_hba.conf restera' 'trust'
REM finche' non abbiamo impostato la password del superuser)
(
    echo # Foliarium PostgreSQL Configuration
    echo port = %DB_PORT%
    echo listen_addresses = '127.0.0.1'
    echo max_connections = 30
    echo shared_buffers = 64MB
    echo work_mem = 4MB
    echo logging_collector = on
    echo log_directory = 'log'
    echo log_filename = 'postgresql-%%Y-%%m-%%d.log'
    echo log_min_messages = warning
    echo password_encryption = scram-sha-256
) >> "%PG_DATA%\postgresql.conf"

REM Avvio temporaneo del server (pg_hba di initdb = trust, nessuna password)
echo   Avvio temporaneo (trust) per impostare la password... >> "%LOGFILE%"
"%PG_BIN%\pg_ctl.exe" start -D "%PG_DATA%" -l "%PG_DATA%\pg_start.log" -w -t 30 >> "%LOGFILE%" 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo ERRORE: avvio temporaneo del server fallito. >> "%LOGFILE%"
    type "%PG_DATA%\pg_start.log" >> "%LOGFILE%" 2>&1
    exit /b 1
)

REM Imposta password postgres (connessione trust - initdb default)
set "PGPASSWORD="
"%PG_BIN%\psql.exe" -h 127.0.0.1 -p %DB_PORT% -U postgres -d postgres -c "ALTER USER postgres PASSWORD '%DB_PASSWORD%';" >> "%LOGFILE%" 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo ERRORE: impostazione password postgres fallita. >> "%LOGFILE%"
    "%PG_BIN%\pg_ctl.exe" stop -D "%PG_DATA%" -m fast >> "%LOGFILE%" 2>&1
    exit /b 1
)
echo   Password superuser impostata. >> "%LOGFILE%"

REM ADESSO che postgres ha una password, sovrascrivo pg_hba.conf con scram-sha-256
(
    echo # TYPE  DATABASE  USER       ADDRESS        METHOD
    echo local   all       all                       scram-sha-256
    echo host    all       all        127.0.0.1/32   scram-sha-256
    echo host    all       all        ::1/128        scram-sha-256
) > "%PG_DATA%\pg_hba.conf"

REM Ferma il server temporaneo (verra' riavviato come servizio con hba aggiornato)
"%PG_BIN%\pg_ctl.exe" stop -D "%PG_DATA%" -m fast >> "%LOGFILE%" 2>&1
timeout /t 2 /nobreak > nul

:start_service
REM ============================================================================
REM 4. Registrazione come servizio Windows
REM ============================================================================
echo [4/8] Registrazione servizio Windows '%SERVICE_NAME%'... >> "%LOGFILE%"

REM Rimuove eventuale servizio preesistente
sc query "%SERVICE_NAME%" > nul 2>&1
if %ERRORLEVEL% EQU 0 (
    net stop "%SERVICE_NAME%" > nul 2>&1
    sc delete "%SERVICE_NAME%" > nul 2>&1
    timeout /t 2 /nobreak > nul
)

"%PG_BIN%\pg_ctl.exe" register -N "%SERVICE_NAME%" -D "%PG_DATA%" -S auto >> "%LOGFILE%" 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo   ATTENZIONE: registrazione servizio fallita, provo avvio manuale. >> "%LOGFILE%"
)

REM ============================================================================
REM 5. Avvio servizio PostgreSQL
REM ============================================================================
echo [5/8] Avvio servizio PostgreSQL... >> "%LOGFILE%"
net start "%SERVICE_NAME%" >> "%LOGFILE%" 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo   Servizio non partito, provo avvio diretto... >> "%LOGFILE%"
    "%PG_BIN%\pg_ctl.exe" start -D "%PG_DATA%" -l "%PG_DATA%\pg_start.log" -w -t 30 >> "%LOGFILE%" 2>&1
)

REM Attendi che il server sia pronto
echo   Attesa server... >> "%LOGFILE%"
set /a ATTEMPTS=0
:wait_loop
"%PG_BIN%\pg_isready.exe" -h 127.0.0.1 -p %DB_PORT% > nul 2>&1
if %ERRORLEVEL% EQU 0 goto :server_ready
set /a ATTEMPTS+=1
if %ATTEMPTS% GEQ 30 (
    echo ERRORE: PostgreSQL non risponde dopo 30 tentativi. >> "%LOGFILE%"
    exit /b 1
)
timeout /t 1 /nobreak > nul
goto :wait_loop

:server_ready
echo   Server PostgreSQL pronto sulla porta %DB_PORT%. >> "%LOGFILE%"

REM ============================================================================
REM 6. Creazione ruolo applicativo e database
REM ============================================================================
echo [6/8] Creazione database e ruolo... >> "%LOGFILE%"
set "PGPASSWORD=%DB_PASSWORD%"

REM Crea il ruolo 'foliarium' se non esiste
"%PG_BIN%\psql.exe" -h 127.0.0.1 -p %DB_PORT% -U postgres -d postgres -c "DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname='%DB_USER%') THEN CREATE ROLE %DB_USER% LOGIN PASSWORD '%DB_PASSWORD%'; END IF; END $$;" >> "%LOGFILE%" 2>&1

REM Crea il database se non esiste
"%PG_BIN%\psql.exe" -h 127.0.0.1 -p %DB_PORT% -U postgres -d postgres -tc "SELECT 1 FROM pg_database WHERE datname='%DB_NAME%'" | findstr "1" > nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    "%PG_BIN%\psql.exe" -h 127.0.0.1 -p %DB_PORT% -U postgres -d postgres -c "CREATE DATABASE %DB_NAME% OWNER postgres ENCODING 'UTF8';" >> "%LOGFILE%" 2>&1
)

REM Grant permessi
"%PG_BIN%\psql.exe" -h 127.0.0.1 -p %DB_PORT% -U postgres -d %DB_NAME% -c "GRANT CONNECT ON DATABASE %DB_NAME% TO %DB_USER%;" >> "%LOGFILE%" 2>&1

REM ============================================================================
REM 7. Esecuzione script SQL
REM    Ordine: schema base -> funzioni -> feature aggiuntive -> user mgmt
REM           -> indici trigram (ultima, no-transaction) -> bootstrap admin
REM ============================================================================
echo [7/8] Inizializzazione schema, procedure e feature... >> "%LOGFILE%"

REM Script in ordine di applicazione (escluso bootstrap admin, gestito a parte).
REM Da v1.0.0: lookup tipo_possesso/tipo_localita, soft-delete e tabella sessioni
REM sono integrati in 02 e 07_user-management (vedi sql_scripts/README.md).
for %%F in (
    "%SQL_DIR%\02_creazione-schema-tabelle.sql"
    "%SQL_DIR%\03_funzioni-procedure.sql"
    "%SQL_DIR%\03b_expand_fuzzy_search.sql"
    "%SQL_DIR%\07_user-management.sql"
    "%SQL_DIR%\08_advanced-reporting.sql"
    "%SQL_DIR%\09_backup-system.sql"
    "%SQL_DIR%\10_performance-optimization.sql"
    "%SQL_DIR%\11_advanced-cadastral-features.sql"
    "%SQL_DIR%\12_procedure_crud.sql"
    "%SQL_DIR%\13_workflow_integrati.sql"
    "%SQL_DIR%\14_report_functions.sql"
    "%SQL_DIR%\15_integration_audit_users.sql"
    "%SQL_DIR%\16_advanced_search.sql"
    "%SQL_DIR%\17_funzione_ricerca_immobili.sql"
    "%SQL_DIR%\18_funzioni_trigger_audit.sql"
    "%SQL_DIR%\07_create_trigram_indexes.sql"
) do (
    if exist "%%~F" (
        echo   Esecuzione %%~nxF... >> "%LOGFILE%"
        "%PG_BIN%\psql.exe" -h 127.0.0.1 -p %DB_PORT% -U postgres -d %DB_NAME% -f "%%~F" >> "%LOGFILE%" 2>&1
    ) else (
        echo   ATTENZIONE: %%~nxF non trovato, saltato. >> "%LOGFILE%"
    )
)

REM Bootstrap admin: passa la password generata dall'installer come variabile psql
REM CRITICO: senza questo step l'utente non può accedere al primo avvio.
echo   Esecuzione 07a_bootstrap_admin.sql con password dinamica... >> "%LOGFILE%"
"%PG_BIN%\psql.exe" -h 127.0.0.1 -p %DB_PORT% -U postgres -d %DB_NAME% ^
    -v admin_password="'%ADMIN_PASSWORD%'" ^
    -v admin_email="'admin@archivio.local'" ^
    -f "%SQL_DIR%\07a_bootstrap_admin.sql" >> "%LOGFILE%" 2>&1

REM Grant su tutte le tabelle create
"%PG_BIN%\psql.exe" -h 127.0.0.1 -p %DB_PORT% -U postgres -d %DB_NAME% -c "GRANT USAGE ON SCHEMA catasto TO %DB_USER%; GRANT USAGE ON SCHEMA public TO %DB_USER%; GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA catasto TO %DB_USER%; GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO %DB_USER%; GRANT USAGE, SELECT, UPDATE ON ALL SEQUENCES IN SCHEMA catasto TO %DB_USER%; GRANT USAGE, SELECT, UPDATE ON ALL SEQUENCES IN SCHEMA public TO %DB_USER%; ALTER DEFAULT PRIVILEGES IN SCHEMA catasto GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO %DB_USER%; ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO %DB_USER%; ALTER DEFAULT PRIVILEGES IN SCHEMA catasto GRANT USAGE, SELECT, UPDATE ON SEQUENCES TO %DB_USER%; ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT, UPDATE ON SEQUENCES TO %DB_USER%; ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA catasto GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO %DB_USER%; ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA catasto GRANT USAGE, SELECT, UPDATE ON SEQUENCES TO %DB_USER%;" >> "%LOGFILE%" 2>&1

REM Trasferimento proprieta' delle viste materializzate all'utente applicativo per consentirne il REFRESH
"%PG_BIN%\psql.exe" -h 127.0.0.1 -p %DB_PORT% -U postgres -d %DB_NAME% -c "DO $$ DECLARE r RECORD; BEGIN FOR r IN (SELECT matviewname FROM pg_matviews WHERE schemaname = 'catasto') LOOP EXECUTE 'ALTER MATERIALIZED VIEW catasto.' || quote_ident(r.matviewname) || ' OWNER TO %DB_USER%'; END LOOP; END $$;" >> "%LOGFILE%" 2>&1

REM ============================================================================
REM 8. Scrittura config.ini
REM ============================================================================
echo [8/8] Scrittura config.ini... >> "%LOGFILE%"

(
    echo [database]
    echo host     = 127.0.0.1
    echo port     = %DB_PORT%
    echo dbname   = %DB_NAME%
    echo user     = %DB_USER%
    echo password = %DB_PASSWORD%
    echo.
    echo [service]
    echo name     = %SERVICE_NAME%
    echo pg_bin   = %PG_BIN%
    echo pg_data  = %PG_DATA%
) > "%CONFIG_FILE%"

echo. >> "%LOGFILE%"
echo ============================================== >> "%LOGFILE%"
echo  Installazione database completata!           >> "%LOGFILE%"
echo  Porta: %DB_PORT%                             >> "%LOGFILE%"
echo  Database: %DB_NAME%                          >> "%LOGFILE%"
echo  Utente DB: %DB_USER%                         >> "%LOGFILE%"
echo  Servizio: %SERVICE_NAME%                     >> "%LOGFILE%"
echo  Config: %CONFIG_FILE%                        >> "%LOGFILE%"
echo ============================================== >> "%LOGFILE%"

exit /b 0
