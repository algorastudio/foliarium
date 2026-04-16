@echo off
echo ========================================
echo Esecuzione script drop_db.sql su PostgreSQL
echo ========================================
echo.

REM --- INIZIO MODIFICA: Richiesta Username ---

REM Chiede all'utente di inserire il nome utente e lo salva nella variabile DB_USER
set /p DB_USER="Inserisci lo username per PostgreSQL (default: postgres): "

REM Se l'utente non inserisce nulla, imposta il valore di default a "postgres"
if "%DB_USER%"=="" set DB_USER=postgres

echo.
echo Tentativo di connessione con l'utente: %DB_USER%
echo ----------------------------------------

REM --- FINE MODIFICA ---


REM Esegui il comando psql usando la variabile %DB_USER%
psql -U %DB_USER% -h localhost -d postgres -f drop_db.sql

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