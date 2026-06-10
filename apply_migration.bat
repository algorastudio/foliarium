@echo off
REM Apply soft delete migration to an existing database (Windows batch version)

setlocal enabledelayedexpansion

set DB_HOST=localhost
set DB_PORT=5432
set DB_NAME=catasto_storico
set DB_USER=postgres

if not "%DB_HOST_ENV%"=="" set DB_HOST=%DB_HOST_ENV%
if not "%DB_PORT_ENV%"=="" set DB_PORT=%DB_PORT_ENV%
if not "%DB_NAME_ENV%"=="" set DB_NAME=%DB_NAME_ENV%
if not "%DB_USER_ENV%"=="" set DB_USER=%DB_USER_ENV%

echo Applying migration: soft delete archiviazione...
echo Target: %DB_USER%@%DB_HOST%:%DB_PORT%/%DB_NAME%
echo.

REM Execute migration script
psql -h %DB_HOST% -p %DB_PORT% -U %DB_USER% -d %DB_NAME% -f sql_scripts\migrations\add_soft_delete.sql

if %ERRORLEVEL% equ 0 (
    echo.
    echo * Migration completed successfully!
    echo.
    echo Verifying schema changes...
    psql -h %DB_HOST% -p %DB_PORT% -U %DB_USER% -d %DB_NAME% -c "\d catasto.partita" | find "archiviato"
    echo.
    echo You can now restart Foliarium. RicercaPartiteWidget should work correctly.
) else (
    echo.
    echo X Migration failed. Check error messages above.
    exit /b 1
)

pause
