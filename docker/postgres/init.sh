#!/bin/bash
# init.sh — applica gli script SQL di Foliarium al database appena creato.
#
# Eseguito da /docker-entrypoint-initdb.d al PRIMO avvio del container, dopo
# che l'immagine postgres ha creato $POSTGRES_DB. In questa fase il server
# ascolta solo sul socket Unix: chi aspetta il database via TCP (pg_isready
# -h ...) lo vede pronto solo a inizializzazione conclusa.
#
# Variabili facoltative:
#   FOLIARIUM_ADMIN_PASSWORD  crea l'utente applicativo `admin`
#   FOLIARIUM_DEMO_PASSWORD   crea l'utente `demo` e carica l'archivio
#                             dimostrativo
# Le password non vengono mai scritte nell'output.
set -euo pipefail

DB="${POSTGRES_DB:-catasto_storico}"
UTENTE_PG="${POSTGRES_USER:-postgres}"
CARTELLA_SQL="/opt/foliarium-sql"

# Ordine di applicazione su un database nuovo.
#
# DEVE restare identico a SQL_SCRIPTS in setup_database.py, che e' l'elenco
# usato dall'installer. La duplicazione e' voluta (estrarre l'elenco in un
# file comune toccherebbe il percorso dell'installer Windows) ed e'
# sorvegliata da tests/unit/test_docker_db_init.py.
#
# admin/01_users.sql precede functions/06_audit.sql perche' crea
# catasto.utente, su cui l'audit costruisce una vista e una chiave esterna.
SCRIPTS=(
    "schema/01_tables.sql"
    "functions/01_core.sql"
    "functions/02_crud.sql"
    "functions/03_workflow.sql"
    "functions/04_search.sql"
    "functions/05_reporting.sql"
    "admin/01_users.sql"
    "functions/06_audit.sql"
    "functions/07_features.sql"
    "admin/02_backup.sql"
    "admin/03_performance.sql"
    "schema/02_trigram_indexes.sql"
)

# percorso_di <script>: stampa il percorso completo, o fallisce.
percorso_di() {
    local percorso="$CARTELLA_SQL/$1"
    if [ ! -f "$percorso" ]; then
        # Un file mancante e' un errore, non un avviso: saltarlo lascerebbe
        # uno schema incompleto con il container che risulta comunque sano.
        echo "[foliarium-init] ERRORE: $1 non trovato in $CARTELLA_SQL" >&2
        exit 1
    fi
    printf '%s' "$percorso"
}

# applica <script> [opzioni psql aggiuntive...]: il primo errore ferma tutto.
applica() {
    local script="$1" percorso
    shift
    percorso="$(percorso_di "$script")"
    echo "[foliarium-init] -> $script"
    psql --quiet -v ON_ERROR_STOP=1 -U "$UTENTE_PG" -d "$DB" "$@" -f "$percorso" \
        || { echo "[foliarium-init] ERRORE in $script" >&2; exit 1; }
}

echo "[foliarium-init] Applico gli script SQL al database '$DB'..."

for script in "${SCRIPTS[@]}"; do
    applica "$script"
done

if [ -n "${FOLIARIUM_ADMIN_PASSWORD:-}" ]; then
    # Lo script di bootstrap richiede la variabile psql admin_password:
    # senza, esce prima dell'INSERT e l'utente non viene creato.
    applica "admin/04_bootstrap_admin.sql" -v admin_password="$FOLIARIUM_ADMIN_PASSWORD"
    echo "[foliarium-init] Utente applicativo 'admin' creato."
fi

if [ -n "${FOLIARIUM_DEMO_PASSWORD:-}" ]; then
    applica "demo/demo_user.sql" -v demo_password="$FOLIARIUM_DEMO_PASSWORD"
    applica "demo/demo_data.sql"
    # Le viste materializzate nascono a tabelle vuote: vanno ricalcolate.
    applica "demo/demo_statistiche.sql"
    echo "[foliarium-init] Utente 'demo' creato e archivio dimostrativo caricato."
fi

# Segnale di inizializzazione conclusa. Se uno script fallisce, il container
# esce; al riavvio l'immagine trova la cartella dei dati gia' presente, salta
# l'inizializzazione e il server risponde con uno schema a meta'. Chi deve
# sapere se il database e' davvero pronto (il controllo di salute della demo,
# docker/demo/compose.postazione.yml) guarda questo file, che sta nel volume
# dei dati e nasce solo se si arriva fin qui.
touch "${PGDATA:?}/foliarium_init_completato"

echo "[foliarium-init] Setup completato."
