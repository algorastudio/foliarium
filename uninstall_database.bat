@echo off
REM ============================================================================
REM uninstall_database.bat — Rimozione servizio PostgreSQL Foliarium
REM
REM Eseguito automaticamente dall'uninstaller Inno Setup.
REM Ferma il servizio, lo deregistra e rimuove pg_data/.
REM
REM Parametri:
REM   %1 = directory di installazione (es. C:\Program Files\Foliarium)
REM ============================================================================
setlocal enabledelayedexpansion

set "INSTALL_DIR=%~1"
set "PG_BIN=%INSTALL_DIR%\pgsql\bin"
set "DATA_ROOT=%ProgramData%\Foliarium"
set "PG_DATA=%DATA_ROOT%\pg_data"
set "SERVICE_NAME=FoliariumDB"

echo Arresto servizio %SERVICE_NAME%...
net stop "%SERVICE_NAME%" > nul 2>&1
timeout /t 3 /nobreak > nul

echo Rimozione servizio %SERVICE_NAME%...
"%PG_BIN%\pg_ctl.exe" unregister -N "%SERVICE_NAME%" > nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    sc delete "%SERVICE_NAME%" > nul 2>&1
)
timeout /t 2 /nobreak > nul

echo Rimozione dati database...
if exist "%PG_DATA%" (
    rmdir /s /q "%PG_DATA%" > nul 2>&1
)

REM Rimuovi anche la cartella padre se vuota
if exist "%DATA_ROOT%" (
    rmdir "%DATA_ROOT%" > nul 2>&1
)

echo Pulizia completata.
exit /b 0
