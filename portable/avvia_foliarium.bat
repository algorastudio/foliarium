@ECHO OFF
CHCP 65001 >nul
TITLE Foliarium - Avvio

REM Foliarium - Script di avvio
REM Avvia PostgreSQL portatile e lancia l'applicazione
REM Autore: Marco Santoro - ALGORASTUDIO
REM Licenza: AGPL-3.0-or-later

REM --- Percorsi ---
SET FOLIARIUM_ROOT=%~dp0..
SET PGDIR=%~dp0pgsql
SET PGDATA=C:\FoliariumData\pgdata
SET PGPORT=5433
SET PGUSER=postgres
SET PGLOCALEDIR=%PGDIR%\share\locale
SET PATH=%PGDIR%\bin;%PATH%

REM --- Verifica primo avvio ---
IF NOT EXIST "%PGDATA%" (
    ECHO.
    ECHO [ERRORE] Database non inizializzato.
    ECHO Esegui prima: setup_primo_avvio.bat
    ECHO.
    PAUSE
    EXIT /B 1
)

ECHO.
ECHO ============================================================
ECHO   Foliarium - Avvio in corso...
ECHO ============================================================
ECHO.

REM --- Controlla se PostgreSQL e' gia in esecuzione ---
"%PGDIR%\bin\pg_ctl.exe" -D "%PGDATA%" status >nul 2>&1
IF NOT ERRORLEVEL 1 (
    ECHO [INFO] PostgreSQL gia in esecuzione.
) ELSE (
    ECHO [AVVIO] PostgreSQL sulla porta %PGPORT%...
    "%PGDIR%\bin\pg_ctl.exe" -D "%PGDATA%" -l "C:\FoliariumData\pg_log.txt" start
    TIMEOUT /T 2 /NOBREAK >nul
)

REM --- Verifica connessione ---
"%PGDIR%\bin\psql.exe" -U postgres -p %PGPORT% -c "SELECT 1;" >nul 2>&1
IF ERRORLEVEL 1 (
    ECHO [ERRORE] PostgreSQL non risponde. Controlla C:\FoliariumData\pg_log.txt
    PAUSE
    EXIT /B 1
)

ECHO [OK] PostgreSQL attivo.
ECHO.
ECHO [AVVIO] Foliarium...
ECHO.

REM --- Avvia applicazione ---
cd /D "%FOLIARIUM_ROOT%"
python main.py

REM --- Quando l'utente chiude l'app, chiedi se fermare PostgreSQL ---
ECHO.
ECHO Foliarium chiuso.
ECHO.
SET /P STOP_PG="Arrestare anche PostgreSQL? (S/N): "
IF /I "%STOP_PG%"=="S" (
    ECHO [ARRESTO] PostgreSQL...
    "%PGDIR%\bin\pg_ctl.exe" -D "%PGDATA%" stop
    ECHO [OK] PostgreSQL arrestato.
) ELSE (
    ECHO [INFO] PostgreSQL resta in esecuzione sulla porta %PGPORT%.
    ECHO        Per arrestarlo manualmente: arresta_foliarium.bat
)
ECHO.
