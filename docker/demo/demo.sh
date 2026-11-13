#!/usr/bin/env bash
# demo.sh — gestione delle postazioni della demo di Foliarium.
#
# Una POSTAZIONE e' una copia del programma con il suo database, il suo
# schermo e le sue credenziali: un progetto Compose con due container (app e
# db). Un solo proxy, comune a tutte, termina HTTPS, chiede le credenziali e
# instrada per percorso: https://<dominio>/<nome>/.
#
#   demo.sh costruisci          costruisce le immagini dai sorgenti
#   demo.sh crea <nome>         crea una postazione e ne stampa le credenziali
#   demo.sh ripristina <nome>   la riporta allo stato iniziale
#   demo.sh rimuovi <nome>      la elimina con tutti i suoi dati
#   demo.sh elenco              postazioni esistenti e loro stato
#
# Guida completa: docker/demo/README.md
set -euo pipefail

# Con LC_ALL=C gli intervalli [a-z] delle espressioni regolari valgono solo
# per le lettere ASCII: in altre lingue comprenderebbero quelle accentate.
export LC_ALL=C

QUI="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RADICE_REPO="$(cd "$QUI/../.." && pwd)"

# Dove stanno la configurazione e i dati delle postazioni. Di norma accanto
# a questo script; la prova automatica usa una cartella temporanea.
DATI="${DEMO_CARTELLA_DATI:-$QUI}"
FILE_CONF="$DATI/demo.env"
POSTAZIONI="$DATI/postazioni"          # <nome>.env, con le password in chiaro
# Frammenti di configurazione del proxy: solo hash, mai password. Stanno in
# una cartella a parte perche' e' l'unica che il container del proxy monta.
CARTELLA_PROXY="${DEMO_CARTELLA_PROXY:-$DATI/proxy}"

# Prefisso dei nomi di progetto e container. Cambiandolo si puo' tenere una
# seconda installazione sulla stessa macchina senza che si tocchino: e'
# cosi' che la prova automatica non interferisce con le postazioni vere.
PREFISSO="${DEMO_PREFISSO:-foliarium-demo}"
CONTAINER_PROXY="$PREFISSO-proxy"

IMMAGINE_APP="${DEMO_IMMAGINE_APP:-foliarium-demo-app:locale}"
IMMAGINE_DB="${DEMO_IMMAGINE_DB:-foliarium-demo-db:locale}"
IMMAGINE_PROXY="caddy:2-alpine"

NOMI_RISERVATI="proxy"

# Codici d'uscita: 0 riuscito, 2 uso o nome non valido, 3 postazione gia'
# esistente o inesistente, 1 ogni altro errore.
ERR_USO=2
ERR_STATO=3

errore() { echo "demo.sh: $*" >&2; }

uso() {
    cat >&2 <<'EOF'
Uso: demo.sh <comando> [nome]

  costruisci          costruisce le immagini dai sorgenti presenti sul server
  crea <nome>         crea una postazione e ne stampa indirizzo e credenziali
  ripristina <nome>   riporta una postazione allo stato iniziale
  rimuovi <nome>      elimina una postazione con tutti i suoi dati
  elenco              postazioni esistenti e loro stato

Il nome: lettere minuscole, cifre e trattini, da 2 a 31 caratteri, con una
lettera all'inizio. Diventa parte dell'indirizzo: https://<dominio>/<nome>/
EOF
    exit "$ERR_USO"
}

# ---------------------------------------------------------------------------
# Configurazione
# ---------------------------------------------------------------------------

# Legge demo.env riga per riga, senza eseguirlo. Una variabile gia' presente
# nell'ambiente ha la precedenza sul file.
leggi_configurazione() {
    local chiave valore
    if [ -f "$FILE_CONF" ]; then
        while IFS='=' read -r chiave valore; do
            case "$chiave" in
                DEMO_DOMINIO|DEMO_PORTA_LOCALE|DEMO_INDIRIZZO_PUBBLICO|PG_MAJOR|DEMO_MEM_APP|DEMO_MEM_DB)
                    if [ -z "${!chiave+impostata}" ]; then
                        valore="${valore%$'\r'}"
                        printf -v "$chiave" '%s' "$valore"
                    fi
                    ;;
            esac
        done < <(grep -E '^[A-Z_]+=' "$FILE_CONF" || true)
    fi
    DEMO_DOMINIO="${DEMO_DOMINIO:-}"
    DEMO_PORTA_LOCALE="${DEMO_PORTA_LOCALE:-8080}"
    DEMO_INDIRIZZO_PUBBLICO="${DEMO_INDIRIZZO_PUBBLICO:-}"
    PG_MAJOR="${PG_MAJOR:-16}"
    # Limiti di memoria: a riposo una postazione occupa circa 245 MB (app) e
    # 50 MB (db). Sono un argine contro un processo impazzito, non un tetto
    # stretto: un programma ucciso a meta' demo costa piu' della memoria.
    DEMO_MEM_APP="${DEMO_MEM_APP:-1024m}"
    DEMO_MEM_DB="${DEMO_MEM_DB:-512m}"
}

# Indirizzo che il cliente digita nel browser, senza barra finale.
indirizzo_base() {
    if [ -n "$DEMO_INDIRIZZO_PUBBLICO" ]; then
        printf '%s' "${DEMO_INDIRIZZO_PUBBLICO%/}"
    elif [ -n "$DEMO_DOMINIO" ]; then
        printf 'https://%s' "$DEMO_DOMINIO"
    else
        printf 'http://127.0.0.1:%s' "$DEMO_PORTA_LOCALE"
    fi
}

# ---------------------------------------------------------------------------
# Nomi
# ---------------------------------------------------------------------------

# Il nome finisce in percorsi di file, nomi di progetto Compose, alias di
# rete e configurazione del proxy: va controllato PRIMA di ogni altra cosa.
valida_nome() {
    local nome="${1-}" riservato
    if ! [[ "$nome" =~ ^[a-z][a-z0-9-]{1,30}$ ]]; then
        errore "nome non valido: servono lettere minuscole, cifre e trattini," \
               "da 2 a 31 caratteri, con una lettera all'inizio."
        exit "$ERR_USO"
    fi
    for riservato in $NOMI_RISERVATI; do
        if [ "$nome" = "$riservato" ]; then
            errore "nome non valido: «$nome» e' riservato."
            exit "$ERR_USO"
        fi
    done
}

progetto() { printf '%s-%s' "$PREFISSO" "$1"; }

esiste() { [ -f "$POSTAZIONI/$1.env" ]; }

# ---------------------------------------------------------------------------
# Docker
# ---------------------------------------------------------------------------

# silenzioso <comando...>: nasconde l'output di un comando riuscito; se
# fallisce lo mostra tutto, perche' e' li' che sta la spiegazione.
silenzioso() {
    local uscita
    if ! uscita="$("$@" 2>&1)"; then
        printf '%s\n' "$uscita" >&2
        return 1
    fi
}

richiedi_docker() {
    if ! docker compose version >/dev/null 2>&1; then
        errore "serve Docker con il plugin Compose (docker compose)."
        exit 1
    fi
}

richiedi_immagini() {
    local immagine
    for immagine in "$IMMAGINE_APP" "$IMMAGINE_DB"; do
        if ! docker image inspect "$immagine" >/dev/null 2>&1; then
            errore "immagine $immagine assente: eseguire prima «demo.sh costruisci»."
            exit 1
        fi
    done
}

# compose_postazione <nome> <argomenti di docker compose...>
compose_postazione() {
    local nome="$1"
    shift
    DEMO_IMMAGINE_APP="$IMMAGINE_APP" DEMO_IMMAGINE_DB="$IMMAGINE_DB" \
    DEMO_MEM_APP="$DEMO_MEM_APP" DEMO_MEM_DB="$DEMO_MEM_DB" \
    DEMO_SALTA_EULA="${DEMO_SALTA_EULA:-}" \
        docker compose -p "$(progetto "$nome")" \
            --env-file "$POSTAZIONI/$nome.env" \
            -f "$QUI/compose.postazione.yml" "$@"
}

compose_proxy() {
    local sito modalita
    if [ -n "$DEMO_DOMINIO" ]; then
        sito="$DEMO_DOMINIO"
        modalita="$QUI/compose.proxy.pubblico.yml"
    else
        sito="http://:8080"
        modalita="$QUI/compose.proxy.locale.yml"
    fi
    DEMO_SITO="$sito" DEMO_CONTAINER_PROXY="$CONTAINER_PROXY" \
    DEMO_CARTELLA_PROXY="$CARTELLA_PROXY" DEMO_PORTA_LOCALE="$DEMO_PORTA_LOCALE" \
    DEMO_IMMAGINE_PROXY="$IMMAGINE_PROXY" \
        docker compose -p "$PREFISSO-proxy" \
            -f "$QUI/compose.proxy.yml" -f "$modalita" "$@"
}

# Avvia il proxy (se non c'e') e lo collega alla rete di OGNI postazione.
#
# Ogni postazione ha una rete sua, cosi' nessuna puo' raggiungerne un'altra;
# il proxy e' l'unico container presente su tutte. I collegamenti aggiunti
# con «docker network connect» si perdono quando il container viene
# ricreato: per questo si rifanno qui ogni volta, per tutte, e non solo per
# la postazione appena creata.
_proxy_su() {
    local file nome rete
    mkdir -p "$CARTELLA_PROXY"
    silenzioso compose_proxy up -d "$@"
    for file in "$POSTAZIONI"/*.env; do
        [ -e "$file" ] || continue
        nome="$(basename "$file" .env)"
        rete="$(progetto "$nome")_default"
        if docker network inspect "$rete" >/dev/null 2>&1; then
            docker network connect "$rete" "$CONTAINER_PROXY" 2>/dev/null || true
        fi
    done
    # Rilegge i frammenti. Subito dopo l'avvio l'interfaccia di
    # amministrazione puo' non rispondere ancora: qualche tentativo.
    local tentativo
    for tentativo in 1 2 3 4 5 6 7 8 9 10; do
        if docker exec "$CONTAINER_PROXY" caddy reload \
                --config /etc/caddy/Caddyfile >/dev/null 2>&1; then
            return 0
        fi
        sleep 1
    done
    errore "il proxy non ha accettato la nuova configurazione:" \
           "vedere «docker logs $CONTAINER_PROXY»."
    return 1
}

# ---------------------------------------------------------------------------
# Segreti e configurazione del proxy
# ---------------------------------------------------------------------------

# Lettere e cifre soltanto: il valore finisce in un file .env, in variabili
# d'ambiente e in una variabile di psql, e cosi' non serve alcuna quotatura.
genera_segreto() {
    local lunghezza="$1" alfabeto="$2" esito=""
    # head chiude la pipe appena ha letto abbastanza e tr riceve SIGPIPE:
    # con pipefail sarebbe un errore, da qui il «|| true».
    esito="$(tr -dc "$alfabeto" < /dev/urandom 2>/dev/null | head -c "$lunghezza" || true)"
    if [ "${#esito}" -ne "$lunghezza" ]; then
        errore "impossibile generare un segreto casuale."
        exit 1
    fi
    printf '%s' "$esito"
}

# L'hash lo calcola Caddy stesso (bcrypt). La password passa da standard
# input, non dalla riga di comando, dove sarebbe visibile con «ps».
hash_password() {
    local esito
    esito="$(printf '%s\n' "$1" | docker run --rm -i "$IMMAGINE_PROXY" caddy hash-password 2>/dev/null | tail -n 1)"
    case "$esito" in
        '$2'*) printf '%s' "$esito" ;;
        *) errore "calcolo dell'hash della password fallito."; exit 1 ;;
    esac
}

# frammento <nome> <hash> <token>: configurazione del proxy per una postazione.
#
# Solo blocchi «handle»: Caddy li ordina dal percorso piu' lungo al piu'
# corto, quindi il WebSocket e sessione.json vengono prima della regola
# generica della postazione.
#
# Il WebSocket dello schermo NON chiede le credenziali: Safari storicamente
# non le invia in quella connessione. Lo protegge il token nel percorso, 64
# cifre esadecimali casuali, che la pagina riceve da sessione.json, cioe'
# solo dopo essersi autenticata.
frammento() {
    local nome="$1" hash="$2" token="$3"
    cat <<EOF
# Postazione «$nome» — generato da demo.sh: non modificare a mano.

redir /$nome /$nome/ 308
redir /$nome/file /$nome/file/ 308

handle /$nome/ws/$token {
	rewrite * /websockify
	reverse_proxy app-$nome:6080
}

handle /$nome/sessione.json {
	basic_auth {
		demo $hash
	}
	header Cache-Control no-store
	header Content-Type application/json
	respond \`{"ws":"ws/$token"}\` 200
}

handle /$nome/file/* {
	basic_auth {
		demo $hash
	}
	uri strip_prefix /$nome/file
	reverse_proxy app-$nome:6081
}

handle /$nome/* {
	basic_auth {
		demo $hash
	}
	uri strip_prefix /$nome
	reverse_proxy app-$nome:6080
}
EOF
}

# ---------------------------------------------------------------------------
# Comandi
# ---------------------------------------------------------------------------

cmd_costruisci() {
    richiedi_docker
    leggi_configurazione
    # DEMO_BUILD_OPZIONI: opzioni aggiunte a «docker build», per esempio dove
    # le build escono da un proxy. La divisione in parole e' voluta.
    # shellcheck disable=SC2086
    docker build -f "$RADICE_REPO/docker/postgres/Dockerfile" \
        --build-arg "PG_MAJOR=$PG_MAJOR" -t "$IMMAGINE_DB" \
        ${DEMO_BUILD_OPZIONI_DB:-${DEMO_BUILD_OPZIONI:-}} "$RADICE_REPO"
    # shellcheck disable=SC2086
    docker build -f "$RADICE_REPO/docker/demo/Dockerfile" \
        --build-arg "PG_MAJOR=$PG_MAJOR" -t "$IMMAGINE_APP" \
        ${DEMO_BUILD_OPZIONI_APP:-${DEMO_BUILD_OPZIONI:-}} "$RADICE_REPO"
    echo "Immagini pronte: $IMMAGINE_DB, $IMMAGINE_APP (PostgreSQL $PG_MAJOR)."
}

# Attende che il container «app» della postazione risulti sano.
attendi_postazione() {
    local nome="$1" container stato secondi=0
    container="$(progetto "$nome")-app-1"
    while [ "$secondi" -lt 240 ]; do
        stato="$(docker inspect -f '{{if .State.Health}}{{.State.Health.Status}}{{end}}' "$container" 2>/dev/null || true)"
        [ "$stato" = "healthy" ] && return 0
        sleep 3
        secondi=$((secondi + 3))
    done
    return 1
}

cmd_crea() {
    local nome="${1-}" password password_db token hash
    valida_nome "$nome"
    if esiste "$nome"; then
        errore "la postazione «$nome» esiste gia'."
        exit "$ERR_STATO"
    fi
    richiedi_docker
    leggi_configurazione
    richiedi_immagini

    password="$(genera_segreto 20 'A-Za-z0-9')"
    password_db="$(genera_segreto 24 'A-Za-z0-9')"
    token="$(genera_segreto 64 'a-f0-9')"
    hash="$(hash_password "$password")"

    mkdir -p "$POSTAZIONI" "$CARTELLA_PROXY"
    # Se qualcosa va storto si toglie tutto: una postazione a meta' non si
    # potrebbe ne' usare ne' ricreare con lo stesso nome.
    trap 'annulla_creazione "$nome"' ERR
    (
        umask 077
        cat > "$POSTAZIONI/$nome.env" <<EOF
# Postazione «$nome» — generato da demo.sh. Contiene password in chiaro.
DEMO_NOME=$nome
DEMO_PASSWORD=$password
DEMO_DB_PASS=$password_db
DEMO_WS_TOKEN=$token
EOF
    )
    frammento "$nome" "$hash" "$token" > "$CARTELLA_PROXY/$nome.caddy"

    silenzioso compose_postazione "$nome" up -d
    _proxy_su
    trap - ERR

    if ! attendi_postazione "$nome"; then
        errore "la postazione «$nome» e' stata creata ma non risulta ancora pronta:" \
               "controllare con «demo.sh elenco» e «docker logs $(progetto "$nome")-app-1»."
    fi

    cat <<EOF

Postazione «$nome» creata.

  Indirizzo : $(indirizzo_base)/$nome/
  Utente    : demo
  Password  : $password

Le stesse credenziali valgono nel login di Foliarium.
File esportati: $(indirizzo_base)/$nome/file/
EOF
}

annulla_creazione() {
    local nome="$1"
    trap - ERR
    errore "creazione di «$nome» fallita: tolgo cio' che era stato preparato."
    compose_postazione "$nome" down -v >/dev/null 2>&1 || true
    rm -f "$POSTAZIONI/$nome.env" "$CARTELLA_PROXY/$nome.caddy"
    exit 1
}

cmd_elenco() {
    local file nome stato trovate=0
    leggi_configurazione
    for file in "$POSTAZIONI"/*.env; do
        [ -e "$file" ] || continue
        if [ "$trovate" = 0 ]; then
            richiedi_docker
            printf '%-32s %-14s %s\n' "NOME" "STATO" "INDIRIZZO"
            trovate=1
        fi
        nome="$(basename "$file" .env)"
        stato="$(docker inspect -f '{{.State.Status}}{{if .State.Health}} ({{.State.Health.Status}}){{end}}' \
                    "$(progetto "$nome")-app-1" 2>/dev/null || true)"
        case "$stato" in
            "running (healthy)")   stato="attiva" ;;
            "running (starting)")  stato="in avvio" ;;
            "running (unhealthy)") stato="non pronta" ;;
            "")                    stato="assente" ;;
        esac
        printf '%-32s %-14s %s\n' "$nome" "$stato" "$(indirizzo_base)/$nome/"
    done
    if [ "$trovate" = 0 ]; then
        echo "Nessuna postazione. Crearne una con: demo.sh crea <nome>"
    fi
}

richiedi_esistente() {
    if ! esiste "$1"; then
        errore "la postazione «$1» non esiste."
        exit "$ERR_STATO"
    fi
}

# Ferma la postazione ed elimina i suoi volumi (database, impostazioni,
# esportazioni). Prima la stacca dal proxy: finche' il proxy resta collegato
# alla rete della postazione, Docker non puo' eliminarla e «down» fallisce.
ferma_e_svuota() {
    local nome="$1"
    docker network disconnect "$(progetto "$nome")_default" "$CONTAINER_PROXY" \
        >/dev/null 2>&1 || true
    silenzioso compose_postazione "$nome" down -v
}

cmd_ripristina() {
    local nome="${1-}"
    valida_nome "$nome"
    richiedi_esistente "$nome"
    richiedi_docker
    leggi_configurazione
    richiedi_immagini

    ferma_e_svuota "$nome"
    # Stesso file .env: credenziali e token non cambiano, e non cambia
    # nemmeno il frammento del proxy.
    silenzioso compose_postazione "$nome" up -d
    _proxy_su
    if ! attendi_postazione "$nome"; then
        errore "la postazione «$nome» e' stata ripristinata ma non risulta ancora pronta:" \
               "controllare con «demo.sh elenco»."
    fi
    echo "Postazione «$nome» ripristinata: archivio dimostrativo iniziale, stesse credenziali."
}

cmd_rimuovi() {
    local nome="${1-}" conferma="${2-}" risposta=""
    valida_nome "$nome"
    richiedi_esistente "$nome"
    if [ "$conferma" != "--si" ]; then
        printf 'Per eliminare la postazione «%s» con tutti i suoi dati, digitarne il nome: ' "$nome" >&2
        # Standard input chiuso (per esempio da cron): vale come un no.
        read -r risposta || true
        if [ "$risposta" != "$nome" ]; then
            errore "rimozione annullata."
            exit 1
        fi
    fi
    richiedi_docker
    leggi_configurazione

    ferma_e_svuota "$nome"
    rm -f "$POSTAZIONI/$nome.env" "$CARTELLA_PROXY/$nome.caddy"
    # Il proxy, se c'e', deve dimenticare la postazione.
    if docker inspect "$CONTAINER_PROXY" >/dev/null 2>&1; then
        _proxy_su
    fi
    echo "Postazione «$nome» rimossa."
}

# ---------------------------------------------------------------------------

comando="${1-}"
[ "$#" -gt 0 ] && shift

case "$comando" in
    costruisci) cmd_costruisci ;;
    crea)       cmd_crea "$@" ;;
    elenco)     cmd_elenco ;;
    ripristina) cmd_ripristina "$@" ;;
    rimuovi)    cmd_rimuovi "$@" ;;
    # Comandi interni, usati dalle prove automatiche.
    _frammento)
        valida_nome "${1-}"
        frammento "$1" "${2-}" "${3-}"
        ;;
    _proxy_su)
        # Gli argomenti passano a «docker compose up» (es. --force-recreate).
        richiedi_docker
        leggi_configurazione
        _proxy_su "$@"
        ;;
    _proxy_giu)
        # Ferma ed elimina il proxy con i suoi volumi (certificati compresi).
        richiedi_docker
        leggi_configurazione
        silenzioso compose_proxy down -v
        ;;
    *) uso ;;
esac
