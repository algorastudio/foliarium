@ECHO OFF
CHCP 65001 >nul
TITLE Foliarium - Arresto

REM Foliarium - Script di arresto
REM Ferma PostgreSQL portatile in modo sicuro
REM Autore: Marco Santoro - ALGORASTUDIO
REM Licenza: AGPL-3.0-or-later

REM --- Percorsi ---
SET PGDIR=%~dp0pgsql
SET PGDATA=C:\FoliariumData\pgdata
SET PATH=%PGDIR%\bin;%PATH%

REM --- Verifica stato ---
"%PGDIR%\bin\pg_ctl.exe" -D "%PGDATA%" status >nul 2>&1
IF ERRORLEVEL 1 (
    ECHO.
    ECHO [INFO] PostgreSQL non e' in esecuzione.
    ECHO.
    PAUSE
    EXIT /B 0
)

ECHO.
ECHO [ARRESTO] PostgreSQL in corso...
"%PGDIR%\bin\pg_ctl.exe" -D "%PGDATA%" stop

IF ERRORLEVEL 1 (
    ECHO [ERRORE] Arresto fallito. Provo arresto forzato...
    "%PGDIR%\bin\pg_ctl.exe" -D "%PGDATA%" stop -m fast
)

ECHO.
ECHO [OK] PostgreSQL arrestato correttamente.
ECHO.
PAUSE
