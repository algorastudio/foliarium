@ECHO OFF
CHCP 65001 >nul
TITLE Foliarium DEMO - Avvio

REM Foliarium - Script di avvio versione DEMO
REM Avvia PostgreSQL portatile e lancia Foliarium in modalita demo
REM Autore: Marco Santoro - ALGORASTUDIO
REM Licenza: AGPL-3.0-or-later

REM --- Percorsi ---
SET FOLIARIUM_ROOT=%~dp0..
SET PGDIR=%~dp0pgsql
SET PGDATA=C:\FoliariumDemo\pgdata
SET PGPORT=5434
SET PGUSER=postgres
SET PGLOCALEDIR=%PGDIR%\share\locale
SET PATH=%PGDIR%\bin;%PATH%

REM --- Attiva modalita demo ---
SET FOLIARIUM_DEMO=1
SET FOLIARIUM_DEMO_CONFIG=%~dp0config_demo.ini

REM --- Verifica che il setup sia stato eseguito ---
IF NOT EXIST "%PGDATA%" (
    ECHO.
    ECHO [ERRORE] Database demo non inizializzato.
    ECHO Esegui prima: setup_demo.bat
    ECHO.
    PAUSE
    EXIT /B 1
)

IF NOT EXIST "%~dp0config_demo.ini" (
    ECHO.
    ECHO [ERRORE] Configurazione demo non trovata.
    ECHO Esegui prima: setup_demo.bat
    ECHO.
    PAUSE
    EXIT /B 1
)

ECHO.
ECHO ============================================================
ECHO   Foliarium DEMO - Avvio in corso...
ECHO   I dati visualizzati sono FITTIZI a scopo dimostrativo.
ECHO ============================================================
ECHO.

REM --- Avvia PostgreSQL se non gia in esecuzione ---
"%PGDIR%\bin\pg_ctl.exe" -D "%PGDATA%" status >nul 2>&1
IF NOT ERRORLEVEL 1 (
    ECHO [INFO] PostgreSQL demo gia in esecuzione.
) ELSE (
    ECHO [AVVIO] PostgreSQL demo sulla porta %PGPORT%...
    "%PGDIR%\bin\pg_ctl.exe" -D "%PGDATA%" -l "C:\FoliariumDemo\pg_log.txt" start
    TIMEOUT /T 2 /NOBREAK >nul
)

REM --- Verifica connessione ---
"%PGDIR%\bin\psql.exe" -U postgres -p %PGPORT% -c "SELECT 1;" >nul 2>&1
IF ERRORLEVEL 1 (
    ECHO [ERRORE] PostgreSQL non risponde. Controlla C:\FoliariumDemo\pg_log.txt
    PAUSE
    EXIT /B 1
)

ECHO [OK] PostgreSQL demo attivo.
ECHO.
ECHO [AVVIO] Foliarium DEMO...
ECHO.

REM --- Avvia applicazione in modalita demo ---
cd /D "%FOLIARIUM_ROOT%"
python main.py

REM --- Alla chiusura, ferma PostgreSQL ---
ECHO.
ECHO Foliarium DEMO chiuso.
ECHO.
ECHO [ARRESTO] Arresto PostgreSQL demo...
"%PGDIR%\bin\pg_ctl.exe" -D "%PGDATA%" stop
ECHO [OK] PostgreSQL demo arrestato.
ECHO.
PAUSE
