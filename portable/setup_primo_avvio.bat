@ECHO OFF
CHCP 65001 >nul
TITLE Foliarium - Primo Avvio (Setup)

REM Foliarium - Script di primo avvio
REM Inizializza PostgreSQL portatile e configura il database
REM Autore: Marco Santoro - ALGORASTUDIO
REM Licenza: AGPL-3.0-or-later

ECHO.
ECHO ============================================================
ECHO   Foliarium - Configurazione Primo Avvio
ECHO ============================================================
ECHO.

REM --- Percorsi ---
SET FOLIARIUM_ROOT=%~dp0..
SET PGDIR=%~dp0pgsql
SET PGDATA=C:\FoliariumData\pgdata
SET PGPORT=5433
SET PGUSER=postgres
SET PGDATABASE=postgres
SET PGLOCALEDIR=%PGDIR%\share\locale
SET PATH=%PGDIR%\bin;%PATH%

REM --- Verifica binari PostgreSQL ---
IF NOT EXIST "%PGDIR%\bin\pg_ctl.exe" (
    ECHO [ERRORE] Binari PostgreSQL non trovati in: %PGDIR%
    ECHO.
    ECHO Scarica i binari da:
    ECHO   https://www.enterprisedb.com/download-postgresql-binaries
    ECHO.
    ECHO Estrai il contenuto della cartella "pgsql" in:
    ECHO   %PGDIR%
    ECHO.
    PAUSE
    EXIT /B 1
)

REM --- Verifica Python ---
python --version >nul 2>&1
IF ERRORLEVEL 1 (
    ECHO [ERRORE] Python non trovato nel PATH.
    ECHO Installa Python 3.8+ da https://www.python.org/downloads/
    ECHO Assicurati di spuntare "Add Python to PATH" durante l'installazione.
    ECHO.
    PAUSE
    EXIT /B 1
)

REM --- Crea cartella dati locale se non esiste ---
IF NOT EXIST "C:\FoliariumData" (
    ECHO [SETUP] Creazione cartella dati locale C:\FoliariumData ...
    MKDIR "C:\FoliariumData"
)

REM --- Inizializzazione cluster PostgreSQL ---
IF EXIST "%PGDATA%" (
    ECHO [INFO] Il cluster PostgreSQL esiste gia in: %PGDATA%
    ECHO        Se vuoi ricominciare da zero, elimina la cartella C:\FoliariumData\pgdata
    ECHO.
) ELSE (
    ECHO [SETUP] Inizializzazione cluster PostgreSQL...
    ECHO         I dati vengono salvati su disco locale: %PGDATA%
    ECHO.
    "%PGDIR%\bin\initdb.exe" -D "%PGDATA%" -U postgres -A trust -E UTF8 --locale=C
    IF ERRORLEVEL 1 (
        ECHO [ERRORE] Inizializzazione fallita.
        PAUSE
        EXIT /B 1
    )

    REM --- Configura porta personalizzata ---
    ECHO.
    ECHO [SETUP] Configurazione porta %PGPORT%...
    powershell -Command "(Get-Content '%PGDATA%\postgresql.conf') -replace '#port = 5432', 'port = %PGPORT%' | Set-Content '%PGDATA%\postgresql.conf'"

    ECHO [OK] Cluster PostgreSQL inizializzato.
    ECHO.
)

REM --- Avvio PostgreSQL ---
ECHO [SETUP] Avvio PostgreSQL sulla porta %PGPORT%...
"%PGDIR%\bin\pg_ctl.exe" -D "%PGDATA%" -l "C:\FoliariumData\pg_log.txt" start

REM --- Attendi che il server sia pronto ---
TIMEOUT /T 3 /NOBREAK >nul

REM --- Verifica connessione ---
"%PGDIR%\bin\psql.exe" -U postgres -p %PGPORT% -c "SELECT 1;" >nul 2>&1
IF ERRORLEVEL 1 (
    ECHO [ERRORE] PostgreSQL non risponde. Controlla C:\FoliariumData\pg_log.txt
    PAUSE
    EXIT /B 1
)

ECHO [OK] PostgreSQL in esecuzione.
ECHO.

REM --- Creazione database catasto_storico ---
ECHO [SETUP] Creazione database catasto_storico...
"%PGDIR%\bin\psql.exe" -U postgres -p %PGPORT% -c "SELECT 1 FROM pg_database WHERE datname='catasto_storico';" | findstr /C:"1" >nul 2>&1
IF ERRORLEVEL 1 (
    "%PGDIR%\bin\psql.exe" -U postgres -p %PGPORT% -f "%FOLIARIUM_ROOT%\database\01_creazione-database.sql"
    IF ERRORLEVEL 1 (
        ECHO [ERRORE] Creazione database fallita.
        PAUSE
        EXIT /B 1
    )
    ECHO [OK] Database catasto_storico creato.
) ELSE (
    ECHO [INFO] Database catasto_storico esiste gia.
)
ECHO.

REM --- Installazione dipendenze Python ---
ECHO [SETUP] Installazione dipendenze Python...
pip install -r "%FOLIARIUM_ROOT%\requirements.txt" --quiet
IF ERRORLEVEL 1 (
    ECHO [ATTENZIONE] Alcune dipendenze potrebbero non essere state installate.
    ECHO Verifica manualmente con: pip install -r requirements.txt
    ECHO.
)
ECHO [OK] Dipendenze installate.
ECHO.

REM --- Inizializzazione schema database ---
ECHO [SETUP] Inizializzazione schema e tabelle...
ECHO.
python "%FOLIARIUM_ROOT%\setup_db.py" --host localhost --port %PGPORT% --dbname catasto_storico --user postgres --password ""
ECHO.

REM --- Chiedi se caricare dati demo ---
ECHO.
SET /P LOAD_DEMO="Vuoi caricare i dati dimostrativi? (S/N): "
IF /I "%LOAD_DEMO%"=="S" (
    ECHO.
    ECHO [SETUP] Caricamento dati dimostrativi...
    "%PGDIR%\bin\psql.exe" -U postgres -p %PGPORT% -d catasto_storico -f "%FOLIARIUM_ROOT%\database\demo_data.sql"
    ECHO [OK] Dati demo caricati.
)

REM --- Creazione config.ini se non esiste ---
IF NOT EXIST "%FOLIARIUM_ROOT%\config.ini" (
    ECHO.
    ECHO [SETUP] Creazione file di configurazione...
    (
        ECHO [database]
        ECHO host = localhost
        ECHO port = %PGPORT%
        ECHO database = catasto_storico
        ECHO user = postgres
        ECHO password =
        ECHO.
        ECHO [application]
        ECHO language = it
        ECHO theme = default
        ECHO log_level = INFO
    ) > "%FOLIARIUM_ROOT%\config.ini"
    ECHO [OK] File config.ini creato.
)

REM --- Arresto PostgreSQL ---
ECHO.
ECHO [SETUP] Arresto PostgreSQL...
"%PGDIR%\bin\pg_ctl.exe" -D "%PGDATA%" stop
ECHO.

ECHO ============================================================
ECHO   Configurazione completata con successo!
ECHO.
ECHO   Per avviare Foliarium usa:  avvia_foliarium.bat
ECHO   Per arrestare il server:    arresta_foliarium.bat
ECHO ============================================================
ECHO.
PAUSE
