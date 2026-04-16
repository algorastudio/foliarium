@echo off
CLS
echo =================================================================
echo  SCRIPT PER LA CREAZIONE DI UN NUOVO UTENTE ADMIN PER MERIDIANA
echo =================================================================
echo.

REM --- CONFIGURAZIONE CONNESSIONE DATABASE ---
SET PG_USER=postgres
SET PG_DB=catasto_storico
SET PG_HOST=10.99.80.131
SET PG_PORT=5432
REM -----------------------------------------

echo Questo script ti guidera' nella creazione di un nuovo utente.
echo.
echo Fase 1 di 2: Generazione della password sicura (hash).
echo Premi un tasto per continuare...
pause > nul
echo.

python crea_hash.py

IF %ERRORLEVEL% NEQ 0 (
    echo.
    echo ERRORE: Si e' verificato un problema durante la generazione dell'hash.
    pause
    exit /b
)

echo.
echo Fase 2 di 2: Inserimento dei dati nel database.
echo Assicurati di aver copiato l'hash generato qui sopra.
echo.
echo Premi un tasto per avviare la procedura di inserimento interattivo...
pause > nul
echo.

REM Esecuzione dello script SQL interattivo tramite psql
psql -U %PG_USER% -d %PG_DB% -h %PG_HOST% -p %PG_PORT% -f crea_admin_interattivo.sql

echo.
echo =================================================================
echo                           OPERAZIONE COMPLETATA
echo =================================================================
echo.
pause