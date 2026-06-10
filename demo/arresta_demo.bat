@ECHO OFF
CHCP 65001 >nul
TITLE Foliarium DEMO - Arresto

REM Foliarium - Script di arresto versione DEMO
REM Autore: Marco Santoro - ALGORASTUDIO
REM Licenza: AGPL-3.0-or-later

SET PGDIR=%~dp0pgsql
SET PGDATA=C:\FoliariumDemo\pgdata
SET PATH=%PGDIR%\bin;%PATH%

ECHO.
ECHO [ARRESTO] Arresto PostgreSQL demo...
"%PGDIR%\bin\pg_ctl.exe" -D "%PGDATA%" stop
IF ERRORLEVEL 1 (
    ECHO [INFO] PostgreSQL demo non era in esecuzione.
) ELSE (
    ECHO [OK] PostgreSQL demo arrestato.
)
ECHO.
PAUSE
