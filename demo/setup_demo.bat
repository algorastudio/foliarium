@ECHO OFF
CHCP 65001 >nul
TITLE Foliarium DEMO - Setup

REM Foliarium - Script di setup versione DEMO
REM Configura automaticamente PostgreSQL portatile con dati dimostrativi
REM Autore: Marco Santoro - ALGORASTUDIO
REM Licenza: AGPL-3.0-or-later

ECHO.
ECHO ============================================================
ECHO   Foliarium DEMO - Configurazione automatica
ECHO   Tutti i dati sono fittizi a scopo dimostrativo.
ECHO ============================================================
ECHO.

REM --- Percorsi ---
SET FOLIARIUM_ROOT=%~dp0..
SET PGDIR=%~dp0pgsql
SET PGDATA=C:\FoliariumDemo\pgdata
SET PGPORT=5434
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
    ECHO Estrai il contenuto della cartella "pgsql" dentro:
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

REM --- Crea cartella dati demo ---
IF NOT EXIST "C:\FoliariumDemo" (
    ECHO [SETUP] Creazione cartella dati demo C:\FoliariumDemo ...
    MKDIR "C:\FoliariumDemo"
)

REM --- Inizializzazione cluster PostgreSQL ---
IF EXIST "%PGDATA%" (
    ECHO [INFO] Il cluster demo esiste gia in: %PGDATA%
    ECHO        Se vuoi ricominciare da zero, elimina la cartella C:\FoliariumDemo\pgdata
    ECHO.
) ELSE (
    ECHO [SETUP] Inizializzazione cluster PostgreSQL per la demo...
    "%PGDIR%\bin\initdb.exe" -D "%PGDATA%" -U postgres -A trust -E UTF8 --locale=C
    IF ERRORLEVEL 1 (
        ECHO [ERRORE] Inizializzazione fallita.
        PAUSE
        EXIT /B 1
    )

    REM --- Configura porta personalizzata (5434 per non confliggere) ---
    powershell -Command "(Get-Content '%PGDATA%\postgresql.conf') -replace '#port = 5432', 'port = %PGPORT%' | Set-Content '%PGDATA%\postgresql.conf'"
    ECHO [OK] Cluster PostgreSQL demo inizializzato.
    ECHO.
)

REM --- Avvio PostgreSQL ---
ECHO [SETUP] Avvio PostgreSQL demo sulla porta %PGPORT%...
"%PGDIR%\bin\pg_ctl.exe" -D "%PGDATA%" -l "C:\FoliariumDemo\pg_log.txt" start
TIMEOUT /T 3 /NOBREAK >nul

REM --- Verifica connessione ---
"%PGDIR%\bin\psql.exe" -U postgres -p %PGPORT% -c "SELECT 1;" >nul 2>&1
IF ERRORLEVEL 1 (
    ECHO [ERRORE] PostgreSQL non risponde. Controlla C:\FoliariumDemo\pg_log.txt
    PAUSE
    EXIT /B 1
)
ECHO [OK] PostgreSQL in esecuzione.
ECHO.

REM --- Installazione dipendenze Python ---
ECHO [SETUP] Installazione dipendenze Python...
pip install -r "%FOLIARIUM_ROOT%\requirements.txt" --quiet
IF ERRORLEVEL 1 (
    ECHO [ATTENZIONE] Alcune dipendenze potrebbero non essere state installate.
)
ECHO [OK] Dipendenze installate.
ECHO.

REM --- Creazione database catasto_storico ---
ECHO [SETUP] Creazione database demo...
"%PGDIR%\bin\psql.exe" -U postgres -p %PGPORT% -c "SELECT 1 FROM pg_database WHERE datname='catasto_storico';" | findstr /C:"1" >nul 2>&1
IF ERRORLEVEL 1 (
    "%PGDIR%\bin\psql.exe" -U postgres -p %PGPORT% -f "%FOLIARIUM_ROOT%\database\01_creazione-database.sql"
    IF ERRORLEVEL 1 (
        ECHO [ERRORE] Creazione database fallita.
        PAUSE
        EXIT /B 1
    )
    ECHO [OK] Database demo creato.
) ELSE (
    ECHO [INFO] Database demo esiste gia.
)
ECHO.

REM --- Inizializzazione schema e tabelle ---
ECHO [SETUP] Inizializzazione schema e tabelle...
python "%FOLIARIUM_ROOT%\setup_db.py" --host localhost --port %PGPORT% --dbname catasto_storico --user postgres --password ""
ECHO.

REM --- Caricamento automatico dati dimostrativi ---
ECHO [SETUP] Caricamento dati dimostrativi (automatico)...
"%PGDIR%\bin\psql.exe" -U postgres -p %PGPORT% -d catasto_storico -f "%FOLIARIUM_ROOT%\database\demo_data.sql"
IF ERRORLEVEL 1 (
    ECHO [ATTENZIONE] Errore nel caricamento dei dati demo.
) ELSE (
    ECHO [OK] Dati dimostrativi caricati.
)
ECHO.

REM --- Creazione config.ini demo ---
ECHO [SETUP] Creazione configurazione demo...
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
    ECHO demo_mode = true
) > "%~dp0config_demo.ini"
ECHO [OK] Configurazione demo creata.

REM --- Arresto PostgreSQL ---
ECHO.
ECHO [SETUP] Arresto PostgreSQL demo...
"%PGDIR%\bin\pg_ctl.exe" -D "%PGDATA%" stop
ECHO.

ECHO ============================================================
ECHO   Setup DEMO completato!
ECHO.
ECHO   Per avviare la demo usa:  avvia_demo.bat
ECHO   I dati sono fittizi e non corrispondono a persone reali.
ECHO ============================================================
ECHO.
PAUSE
