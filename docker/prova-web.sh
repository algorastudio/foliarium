#!/usr/bin/env bash
# prova-web.sh — prova completa dello stack web (docker-compose.yml in radice).
#
# Costruisce le immagini, avvia `db` e `app`, verifica che il frontend sia
# servito e che il login funzioni contro il database del compose, poi toglie
# tutto, volume compreso. La CI la esegue a ogni pull request
# (.github/workflows/web_docker.yml); a mano, dalla radice del repository:
#
#   bash docker/prova-web.sh
#
# docker-compose.yml usa nomi fissi (container foliarium-db e foliarium-app,
# volume foliarium_db_data): la prova non parte se uno di questi esiste gia',
# perche' la pulizia finale cancellerebbe i dati dello stack in uso.
#
# Variabili:
#   PROVA_WEB_ATTESA=<s>    secondi concessi a build e avvio (default 600)
#   PROVA_WEB_CONSERVA=1    a prova finita lascia lo stack acceso, per
#                           ispezionarlo; poi: docker compose down -v
#
# Rispetta COMPOSE_FILE: un file aggiuntivo puo' passare argomenti di build
# (per esempio immagini di base con la CA di un proxy in uscita).
#
# Esce con 0 solo se tutte le verifiche passano.

set -uo pipefail
export LC_ALL=C

RADICE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$RADICE" || exit 1

ATTESA="${PROVA_WEB_ATTESA:-600}"
CONTAINER_DB="foliarium-db"
CONTAINER_APP="foliarium-app"
VOLUME="foliarium_db_data"

# Password dell'utente applicativo creata per questa prova: diversa dal
# default, cosi' il login dimostra che ADMIN_PASSWORD arriva al database.
ADMIN_PASSWORD="prova-$(od -An -N8 -tx1 /dev/urandom | tr -d ' \n')"
export ADMIN_PASSWORD

superate=0
fallite=0
avviato=0

esito() {  # esito <OK|FALLITO> <descrizione> [dettaglio]
    printf '%-8s %s%s\n' "$1" "$2" "${3:+ — $3}"
    if [ "$1" = OK ]; then
        superate=$((superate + 1))
    else
        fallite=$((fallite + 1))
    fi
}

# verifica <descrizione> <funzione>: la funzione riesce o fallisce, e puo'
# lasciare una spiegazione nella variabile «dettaglio».
verifica() {
    local descrizione="$1"
    shift
    dettaglio=""
    if "$@"; then
        esito OK "$descrizione" "$dettaglio"
    else
        esito FALLITO "$descrizione" "$dettaglio"
    fi
}

# contiene <testo> <cercato>
#
# Mai `comando | grep -q` in questo script: con pipefail fallisce a caso.
# grep esce appena trova il testo, il comando a monte riceve SIGPIPE e la
# pipe risulta fallita anche se il testo c'era.
contiene() {
    case "$1" in
        *"$2"*) return 0 ;;
    esac
    return 1
}

# richiesta <file corpo> <curl args...>: stampa il codice HTTP.
richiesta() {
    local corpo="$1"
    shift
    curl -s -o "$corpo" -w '%{http_code}' --noproxy '*' --max-time 15 "$@"
}

chiudi() {
    local codice=$?
    if [ "$avviato" = 1 ]; then
        if [ "$fallite" -gt 0 ] || [ "$codice" -ne 0 ]; then
            echo
            echo "=== Registri dei container ==="
            docker compose logs --no-color --tail 200
        fi
        if [ "${PROVA_WEB_CONSERVA:-}" = 1 ]; then
            echo
            echo "Stack lasciato acceso (PROVA_WEB_CONSERVA=1)."
            echo "Password di admin: $ADMIN_PASSWORD"
            echo "Per toglierlo: docker compose down -v"
        else
            docker compose down -v --remove-orphans >/dev/null 2>&1
        fi
    fi
    [ -n "${LAVORO:-}" ] && rm -rf -- "$LAVORO"
}

LAVORO="$(mktemp -d)"
trap chiudi EXIT

# --- Precondizioni -----------------------------------------------------------

if ! docker info >/dev/null 2>&1; then
    echo "ERRORE: Docker non risponde." >&2
    exit 2
fi

for nome in "$CONTAINER_DB" "$CONTAINER_APP"; do
    if docker container inspect "$nome" >/dev/null 2>&1; then
        echo "ERRORE: il container $nome esiste gia'. La prova lo sostituirebbe" >&2
        echo "e alla fine cancellerebbe il volume $VOLUME con i suoi dati." >&2
        echo "Se lo stack non serve piu': docker compose down -v" >&2
        exit 2
    fi
done
if docker volume inspect "$VOLUME" >/dev/null 2>&1; then
    echo "ERRORE: il volume $VOLUME esiste gia' e contiene un database." >&2
    echo "La prova lo cancellerebbe. Se non serve piu': docker volume rm $VOLUME" >&2
    exit 2
fi

# --- Build e avvio -----------------------------------------------------------

echo "Build e avvio dello stack (fino a ${ATTESA}s)..."
avviato=1
if docker compose up -d --build --wait --wait-timeout "$ATTESA"; then
    esito OK "build completata, db e app avviati e sani"
else
    esito FALLITO "build o avvio dello stack"
    exit 1
fi

PORTA="$(docker compose port app 8765 | sed 's/.*://')"
BASE="http://127.0.0.1:$PORTA"
echo "App su $BASE"
echo

# --- Verifiche ---------------------------------------------------------------

stato_salute() {
    local stato
    stato="$(docker inspect -f '{{.State.Health.Status}}' "$1" 2>&1)"
    dettaglio="$stato"
    [ "$stato" = healthy ]
}

frontend_servito() {
    local codice pagina script
    codice="$(richiesta "$LAVORO/index.html" "$BASE/")"
    pagina="$(cat "$LAVORO/index.html" 2>/dev/null)"
    if [ "$codice" != 200 ] || ! contiene "$pagina" '<div id="root">'; then
        dettaglio="GET / -> $codice"
        return 1
    fi
    # La pagina deve essere quella compilata da Vite, con i suoi asset
    # raggiungibili: il sorgente di frontend/index.html non basterebbe.
    script="$(sed -n 's/.*src="\(\/assets\/[^"]*\.js\)".*/\1/p' "$LAVORO/index.html")"
    script="${script%%$'\n'*}"
    if [ -z "$script" ]; then
        dettaglio="nessuno script /assets/*.js nella pagina"
        return 1
    fi
    codice="$(richiesta "$LAVORO/script.js" "$BASE$script")"
    dettaglio="$script -> $codice"
    [ "$codice" = 200 ]
}

TOKEN=""

login_admin() {
    local codice corpo
    codice="$(richiesta "$LAVORO/login.json" -X POST "$BASE/api/v1/auth/login" \
        -H 'Content-Type: application/json' \
        -d "{\"username\":\"admin\",\"password\":\"$ADMIN_PASSWORD\"}")"
    corpo="$(cat "$LAVORO/login.json" 2>/dev/null)"
    TOKEN="$(printf '%s' "$corpo" | sed -n 's/.*"token":"\([^"]*\)".*/\1/p')"
    dettaglio="HTTP $codice"
    [ "$codice" = 200 ] && [ -n "$TOKEN" ]
}

sessione_admin() {
    local codice corpo
    codice="$(richiesta "$LAVORO/me.json" "$BASE/api/v1/auth/me" \
        -H "Authorization: Bearer $TOKEN")"
    corpo="$(cat "$LAVORO/me.json" 2>/dev/null)"
    dettaglio="HTTP $codice"
    [ "$codice" = 200 ] && contiene "$corpo" '"username":"admin"'
}

elenco_comuni() {
    # Una lettura vera dallo schema `catasto`, oltre alla tabella utenti.
    local codice
    codice="$(richiesta "$LAVORO/comuni.json" "$BASE/api/v1/comuni" \
        -H "Authorization: Bearer $TOKEN")"
    dettaglio="HTTP $codice"
    [ "$codice" = 200 ]
}

password_errata_rifiutata() {
    local codice
    codice="$(richiesta "$LAVORO/errata.json" -X POST "$BASE/api/v1/auth/login" \
        -H 'Content-Type: application/json' \
        -d '{"username":"admin","password":"non-e-questa"}')"
    dettaglio="HTTP $codice"
    [ "$codice" = 401 ]
}

senza_pyqt6() {
    local esito_import
    esito_import="$(docker compose exec -T app python -c \
        'import importlib.util as u; print("presente" if u.find_spec("PyQt6") else "assente")' 2>&1)"
    dettaglio="PyQt6 $esito_import"
    [ "$esito_import" = assente ]
}

utente_non_root() {
    local uid
    uid="$(docker compose exec -T app id -u 2>&1)"
    dettaglio="uid $uid"
    [ "$uid" != 0 ] && [ -n "$uid" ]
}

verifica "database sano" stato_salute "$CONTAINER_DB"
verifica "app sana" stato_salute "$CONTAINER_APP"
verifica "frontend React servito su /" frontend_servito
verifica "login di admin con ADMIN_PASSWORD" login_admin
verifica "sessione di admin valida (/auth/me)" sessione_admin
verifica "elenco dei comuni letto dal database" elenco_comuni
verifica "password errata rifiutata" password_errata_rifiutata
verifica "immagine senza PyQt6" senza_pyqt6
verifica "app eseguita da un utente senza privilegi" utente_non_root

echo
echo "Superate: $superate   Fallite: $fallite"
[ "$fallite" -eq 0 ]
