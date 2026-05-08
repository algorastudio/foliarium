#!/bin/bash
# init.sh — applica gli script SQL Foliarium sul DB inizializzato dall'image postgres.
# Eseguito automaticamente da /docker-entrypoint-initdb.d al primo avvio del container,
# DOPO che POSTGRES_DB ($POSTGRES_DB) è stato creato e POSTGRES_USER è autenticato.
set -euo pipefail

DB="${POSTGRES_DB:-catasto_storico}"
USER="${POSTGRES_USER:-postgres}"
SCRIPTS_DIR="/opt/foliarium-sql"

echo "[foliarium-init] Applico gli script SQL su database '$DB' come '$USER'..."

# Ordine deterministico — schema → funzioni → utenti → admin → feature → indici.
# Esclusi: 00 (svuota), 01 (DB già creato dalla image), 04* (dati di esempio),
# 05* (query di test), 06 (migrazione civico — schema 02 è già allineato).
SCRIPTS=(
    "02_creazione-schema-tabelle.sql"
    "03_funzioni-procedure.sql"
    "07_user-management.sql"
    "07a_bootstrap_admin.sql"
    "08_advanced-reporting.sql"
    "09_backup-system.sql"
    "10_performance-optimization.sql"
    "11_advanced-cadastral-features.sql"
    "12_procedure_crud.sql"
    "13_workflow_integrati.sql"
    "14_report_functions.sql"
    "15_integration_audit_users.sql"
    "16_advanced_search.sql"
    "17_funzione_ricerca_immobili.sql"
    "18_funzioni_trigger_audit.sql"
    "19_creazione_tabella_sessioni.sql"
    "20_feature_tipi_localita.sql"
    "07_create_trigram_indexes.sql"
)

for script in "${SCRIPTS[@]}"; do
    path="$SCRIPTS_DIR/$script"
    if [ ! -f "$path" ]; then
        echo "[foliarium-init] WARN: $script non trovato, skip."
        continue
    fi
    echo "[foliarium-init] → $script"
    psql --set ON_ERROR_STOP=on -v ON_ERROR_STOP=1 \
         -U "$USER" -d "$DB" -f "$path" \
        || { echo "[foliarium-init] ERRORE in $script"; exit 1; }
done

echo "[foliarium-init] Setup completato."
echo "[foliarium-init] Utente di default creato dal bootstrap script: admin / admin123"
echo "[foliarium-init] *** CAMBIA SUBITO QUESTA PASSWORD IN PRODUZIONE ***"
