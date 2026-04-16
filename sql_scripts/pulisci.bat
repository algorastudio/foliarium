@echo off
echo ========================================
echo Esecuzione script drop_db.sql su PostgreSQL
echo ========================================
echo.

REM Esegui il comando psql
psql -U postgres -h localhost -d postgres -f drop_db.sql

REM Controlla se il comando è stato eseguito con successo
if %ERRORLEVEL% EQU 0 (
    echo.
    echo ========================================
    echo Script eseguito con successo!
    echo ========================================
) else (
    echo.
    echo ========================================
    echo ERRORE: Il comando ha restituito il codice %ERRORLEVEL%
    echo ========================================
)

echo.
echo Premi un tasto per chiudere...
pause >nul