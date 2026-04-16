@echo off
setlocal EnableDelayedExpansion

:: Configurazione
set DB_USER=postgres
set DB_HOST=localhost
set DB_DEFAULT=postgres
set DB_NAME=catasto_storico
REM --- Ottieni percorso dello script ---
SET SCRIPT_DIR=%~dp0

:: Chiedi la password solo una volta
set /p DB_PASSWORD=Inserisci la password per l'utente PostgreSQL: 

:: Impostare la variabile d'ambiente PGPASSWORD (questo evita di dover reinserire la password)
set "PGPASSWORD=%DB_PASSWORD%"

:: Step 1: Creiamo il database sul database postgres
echo Esecuzione di 01_creazione-database.sql...
psql -U %DB_USER% -h %DB_HOST% -d %DB_DEFAULT% -f "%SCRIPTS_DIR%01_creazione-database.sql"
if %ERRORLEVEL% neq 0 (
    echo Errore nell'esecuzione di 01_creazione-database.sql
    exit /b 1
)
echo Script 01_creazione-database.sql eseguito con successo
echo ---------------------------------

:: Step 2: Eseguiamo gli altri script sul nuovo database
set "scripts=02_creazione-schema-tabelle.sql 03_funzioni-procedure.sql 03_funzioni-procedure_def.sql 07_user-management.sql 19_creazione_tabella_sessioni.sql 18_funzioni_trigger_audit.sql  08_advanced-reporting.sql 09_backup-system.sql 10_performance-optimization.sql 11_advanced-cadastral-features.sql 12_procedure_crud.sql 13_workflow_integrati.sql 14_report_functions.sql 16_advanced_search.sql 17_funzione_ricerca_immobili.sql  15_integration_audit_users.sql 20_feature_tipi_localita.sql 05_query-test_aggiornato.sql 04_dati-esempio_modificato.sql 04_dati_stress_test.sql "

for %%s in (%scripts%) do (
    echo Esecuzione di %%s...
    psql -U %DB_USER% -h %DB_HOST% -d %DB_NAME% -f "%SCRIPTS_DIR%%%s"
    if !ERRORLEVEL! neq 0 (
        echo Errore nell'esecuzione di %%s
        exit /b 1
    )
    echo Script %%s eseguito con successo
    echo ---------------------------------
)

echo Tutti gli script sono stati eseguiti con successo!