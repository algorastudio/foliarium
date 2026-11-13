#!/usr/bin/env bash
# prova.sh — prova completa della demo, con container veri.
#
# Crea due postazioni, verifica i criteri di accettazione del progetto
# (docs/internal/2026-11-10-demo-docker-design.md, §8.3) e alla fine toglie
# tutto. E' la prova che la CI esegue a ogni pull request, e si puo' lanciare
# a mano su un server per accertare che l'installazione funzioni.
#
# NON tocca un'installazione gia' presente sulla stessa macchina: usa un
# prefisso proprio per progetti e container (foliarium-prova), una cartella
# dati temporanea e una porta locale diversa.
#
#   bash docker/demo/prova.sh
#
# Variabili:
#   DEMO_PROVA_SENZA_BUILD=1   non ricostruisce le immagini
#   DEMO_PROVA_BROWSER=1       pretende la prova con il browser (Playwright);
#                              senza, la esegue solo se e' disponibile
#   DEMO_PROVA_PORTA           porta locale del proxy di prova (default 18080)
#   DEMO_PROVA_ESITO           dove scrivere esiti e immagini
#                              (default docker/demo/prova-esito)
#
# Esce con 0 solo se tutte le verifiche passano.

set -uo pipefail
export LC_ALL=C

QUI="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ESITO="${DEMO_PROVA_ESITO:-$QUI/prova-esito}"
PORTA="${DEMO_PROVA_PORTA:-18080}"
BASE="http://127.0.0.1:$PORTA"

export DEMO_PREFISSO="foliarium-prova"
DEMO_CARTELLA_DATI="$(mktemp -d)"
export DEMO_CARTELLA_DATI
export DEMO_DOMINIO="" DEMO_INDIRIZZO_PUBBLICO="" DEMO_PORTA_LOCALE="$PORTA"
export DEMO_SALTA_EULA=1
unset DEMO_CARTELLA_PROXY

APP_A="$DEMO_PREFISSO-prova-a-app-1"
APP_B="$DEMO_PREFISSO-prova-b-app-1"
DB_A="$DEMO_PREFISSO-prova-a-db-1"
DB_B="$DEMO_PREFISSO-prova-b-db-1"
TITOLO='Foliarium — Archivio Catastale Storico'

superate=0
fallite=0
saltate=0

demo() { bash "$QUI/demo.sh" "$@"; }

esito() {  # esito <OK|FALLITO|SALTATA> <descrizione> [dettaglio]
    printf '%-8s %s%s\n' "$1" "$2" "${3:+ — $3}"
    case "$1" in
        OK) superate=$((superate + 1)) ;;
        FALLITO) fallite=$((fallite + 1)) ;;
        *) saltate=$((saltate + 1)) ;;
    esac
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

codice() { curl -s -o /dev/null -w '%{http_code}' --noproxy '*' --max-time 15 "$@"; }

password_di() { grep '^DEMO_PASSWORD=' "$DEMO_CARTELLA_DATI/postazioni/$1.env" | cut -d= -f2; }

sql() {  # sql <container db> <istruzione>
    docker exec "$1" psql -U postgres -d catasto_storico -Atc "$2" 2>&1
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

finestra_principale() {
    local finestre
    finestre="$(docker exec "$1" xwininfo -root -tree 2>/dev/null)" || return 1
    contiene "$finestre" "$TITOLO"
}

# I registri dei container servono a capire un fallimento: vanno salvati
# finche' i container esistono, cioe' prima della verifica di rimozione.
registri_salvati=0
salva_registri() {
    local nome
    [ "$registri_salvati" = 1 ] && return 0
    registri_salvati=1
    for nome in "$APP_A" "$DB_A" "$APP_B" "$DB_B" "$DEMO_PREFISSO-proxy"; do
        docker logs "$nome" > "$ESITO/log-$nome.txt" 2>&1 || true
    done
}

attendi() {  # attendi <secondi> <comando...>
    local scadenza=$(( $(date +%s) + $1 ))
    shift
    until "$@"; do
        [ "$(date +%s)" -ge "$scadenza" ] && return 1
        sleep 2
    done
}

pulizia() {
    local nome
    if [ "$fallite" -gt 0 ]; then
        salva_registri
    fi
    for nome in prova-a prova-b; do
        if [ -f "$DEMO_CARTELLA_DATI/postazioni/$nome.env" ]; then
            demo rimuovi "$nome" --si >/dev/null 2>&1 || true
        fi
    done
    demo _proxy_giu >/dev/null 2>&1 || true
    rm -rf "$DEMO_CARTELLA_DATI"
}
trap pulizia EXIT

mkdir -p "$ESITO"
rm -f "$ESITO"/*.png "$ESITO"/*.txt "$ESITO"/*.log 2>/dev/null

# ---------------------------------------------------------------------------
# Preparazione
# ---------------------------------------------------------------------------
if [ "${DEMO_PROVA_SENZA_BUILD:-}" != "1" ]; then
    echo "Costruzione delle immagini (registro: $ESITO/costruisci.log)..."
    if ! demo costruisci > "$ESITO/costruisci.log" 2>&1; then
        tail -n 30 "$ESITO/costruisci.log"
        esito FALLITO "costruzione delle immagini"
        exit 1
    fi
fi

echo "Creazione di due postazioni di prova..."
for nome in prova-a prova-b; do
    if ! demo crea "$nome" > "$ESITO/crea-$nome.log" 2>&1; then
        cat "$ESITO/crea-$nome.log"
        esito FALLITO "creazione della postazione $nome"
        exit 1
    fi
done
# I registri della creazione contengono le password: non si conservano.
rm -f "$ESITO"/crea-*.log
PW_A="$(password_di prova-a)"
PW_B="$(password_di prova-b)"

# ---------------------------------------------------------------------------
# Verifiche
# ---------------------------------------------------------------------------

v_accesso() {
    local senza con altrui
    senza="$(codice "$BASE/prova-a/")"
    con="$(codice -u "demo:$PW_A" "$BASE/prova-a/")"
    altrui="$(codice -u "demo:$PW_B" "$BASE/prova-a/")"
    dettaglio="senza $senza, con $con, con quelle dell'altra $altrui"
    [ "$senza" = 401 ] && [ "$con" = 200 ] && [ "$altrui" = 401 ]
}
verifica "1. accesso: 401 senza credenziali, 200 con le proprie, 401 con quelle di un'altra postazione" v_accesso

v_database() {
    local utente comuni partite
    utente="$(sql "$DB_A" "SELECT ruolo || '|' || attivo FROM catasto.utente WHERE username='demo'")"
    comuni="$(sql "$DB_A" "SELECT count(*) FROM catasto.comune")"
    partite="$(sql "$DB_A" "SELECT count(*) FROM catasto.partita")"
    dettaglio="utente demo: $utente; comuni $comuni; partite $partite"
    [ "$utente" = "admin|true" ] && [ "${comuni:-0}" -gt 0 ] 2>/dev/null && [ "${partite:-0}" -gt 0 ] 2>/dev/null
}
verifica "2. database: utente demo attivo con ruolo admin, archivio dimostrativo caricato" v_database

v_stessa_password() {
    # La password dell'ingresso deve valere anche nel login di Foliarium, che
    # la verifica con bcrypt di Python sull'hash scritto dal database.
    dettaglio="$(docker exec -e PW="$PW_A" "$APP_A" python -c '
import os, bcrypt, psycopg2
c = psycopg2.connect(host=os.environ["DEMO_DB_HOST"], port=os.environ["DEMO_DB_PORT"],
                     dbname=os.environ["DEMO_DB_NAME"], user=os.environ["DEMO_DB_USER"],
                     password=os.environ["DEMO_DB_PASS"])
cur = c.cursor()
cur.execute("SELECT password_hash FROM catasto.utente WHERE username = %s", ("demo",))
h = cur.fetchone()[0].encode()
print("giusta:", bcrypt.checkpw(os.environ["PW"].encode(), h),
      "sbagliata:", bcrypt.checkpw(b"un-altra-password", h))
' 2>&1 | tail -n 1)"
    [ "$dettaglio" = "giusta: True sbagliata: False" ]
}
verifica "3. la password dell'ingresso vale anche nel login di Foliarium" v_stessa_password

v_riparte() {
    if ! attendi 60 finestra_principale "$APP_A"; then
        dettaglio="la finestra principale non e' comparsa"
        return 1
    fi
    docker exec "$APP_A" pkill -f '/opt/foliarium/gui_main.py' || true
    sleep 1
    if finestra_principale "$APP_A"; then
        dettaglio="il programma non si e' chiuso"
        return 1
    fi
    local inizio
    inizio="$(date +%s)"
    if attendi 30 finestra_principale "$APP_A"; then
        dettaglio="tornato dopo $(( $(date +%s) - inizio )) s"
        return 0
    fi
    dettaglio="non e' tornato entro 30 s"
    return 1
}
verifica "4. il programma entra da solo e, chiuso, riparte" v_riparte

v_dati_separati() {
    local inserito in_a in_b
    inserito="$(sql "$DB_A" "INSERT INTO catasto.comune (nome, provincia, regione) VALUES ('Comune di Prova', 'XX', 'Prova') RETURNING 'fatto'" | head -n 1)"
    in_a="$(sql "$DB_A" "SELECT count(*) FROM catasto.comune WHERE nome='Comune di Prova'")"
    in_b="$(sql "$DB_B" "SELECT count(*) FROM catasto.comune WHERE nome='Comune di Prova'")"
    dettaglio="inserimento: $inserito; in A $in_a, in B $in_b"
    [ "$in_a" = 1 ] && [ "$in_b" = 0 ]
}
verifica "5. un dato inserito in una postazione non compare nell'altra" v_dati_separati

v_file() {
    local scaricato elenco fuga corpo_fuga
    docker exec "$APP_A" sh -c 'printf "contenuto di prova" > "$HOME/Documenti/Esportazioni Foliarium/prova.txt"'
    scaricato="$(curl -s --noproxy '*' -u "demo:$PW_A" "$BASE/prova-a/file/Esportazioni%20Foliarium/prova.txt")"
    elenco="$(curl -s --noproxy '*' -u "demo:$PW_A" "$BASE/prova-a/file/Esportazioni%20Foliarium/")"
    fuga="$(codice --path-as-is -u "demo:$PW_A" "$BASE/prova-a/file/..%2f..%2f..%2fetc/passwd")"
    corpo_fuga="$(curl -s --noproxy '*' --path-as-is -u "demo:$PW_A" "$BASE/prova-a/file/..%2f..%2f..%2fetc/passwd")"
    dettaglio="scaricato «$scaricato»; percorso ostile: $fuga"
    [ "$scaricato" = "contenuto di prova" ] &&
        contiene "$elenco" 'prova.txt' &&
        [ "$fuga" != 200 ] &&
        ! contiene "$corpo_fuga" 'root:'
}
verifica "6. un file esportato si scarica dalla pagina dei file; un percorso ostile no" v_file

v_portachiavi() {
    # Foliarium conserva nel portachiavi di sistema la chiave dei backup
    # cifrati, che sono l'opzione predefinita. In un container un portachiavi
    # non c'e': senza quello su file dell'immagine il backup dalla GUI fallisce.
    dettaglio="$(docker exec -w /opt/foliarium -e QT_QPA_PLATFORM=offscreen "$APP_A" python -c '
from foliarium.core.services import backup_crypto
chiave = backup_crypto.get_backup_key(create=True)
print("chiave di", len(chiave), "byte; riletta uguale:", backup_crypto.get_backup_key(create=False) == chiave)
' 2>&1 | tail -n 1)"
    [ "$dettaglio" = "chiave di 32 byte; riletta uguale: True" ]
}
verifica "7. il portachiavi della postazione funziona (serve ai backup cifrati)" v_portachiavi

v_porte() {
    local pubblicate proxy
    pubblicate="$(docker ps --format '{{.Names}} {{.Ports}}' | grep "^$DEMO_PREFISSO-" | grep -v "^$DEMO_PREFISSO-proxy " | grep -c -- '->')"
    proxy="$(docker ps --format '{{.Names}} {{.Ports}}' | grep "^$DEMO_PREFISSO-proxy " | grep -o '[0-9.:]*->' | tr '\n' ' ')"
    dettaglio="porte pubblicate dalle postazioni: $pubblicate; dal proxy: $proxy"
    [ "$pubblicate" = 0 ] && [ "$proxy" = "127.0.0.1:$PORTA-> " ]
}
verifica "8. solo il proxy pubblica porte" v_porte

v_reti_separate() {
    # Da una postazione l'altra non si raggiunge: non se ne risolve nemmeno
    # il nome.
    if docker exec "$APP_A" curl -s -o /dev/null --max-time 4 "http://app-prova-b:6080/"; then
        dettaglio="da A la postazione B risponde"
        return 1
    fi
    dettaglio="da A la postazione B non e' raggiungibile"
}
verifica "9. una postazione non raggiunge l'altra in rete" v_reti_separate

v_proxy_ricreato() {
    # I collegamenti del proxy alle reti delle postazioni si perdono quando
    # il container viene ricreato: demo.sh deve rifarli tutti.
    demo _proxy_su --force-recreate >/dev/null 2>&1 || { dettaglio="ricreazione del proxy fallita"; return 1; }
    local a b
    attendi 30 test "$(codice -u "demo:$PW_A" "$BASE/prova-a/")" = 200 || true
    a="$(codice -u "demo:$PW_A" "$BASE/prova-a/")"
    b="$(codice -u "demo:$PW_B" "$BASE/prova-b/")"
    dettaglio="dopo la ricreazione: A $a, B $b"
    [ "$a" = 200 ] && [ "$b" = 200 ]
}
verifica "10. ricreato il proxy, le postazioni restano raggiungibili" v_proxy_ricreato

# Un'immagine dello schermo presa dentro il container: c'e' anche quando la
# prova con il browser non si puo' fare.
docker exec "$APP_A" python /opt/foliarium-demo/cattura_schermo.py /tmp/schermo.png >/dev/null 2>&1 &&
    docker cp "$APP_A:/tmp/schermo.png" "$ESITO/schermo-nel-container.png" >/dev/null 2>&1

if node -e "require('playwright')" >/dev/null 2>&1; then
    v_browser() {
        NO_PROXY='*' no_proxy='*' node "$QUI/prova_browser.cjs" "$BASE" prova-a "$PW_A" "$ESITO" \
            > "$ESITO/prova-browser.txt" 2>&1
        local stato=$?
        dettaglio="$(tail -n 1 "$ESITO/prova-browser.txt")"
        [ "$stato" = 0 ] || sed 's/^/          /' "$ESITO/prova-browser.txt"
        return "$stato"
    }
    verifica "11. con un browser vero: credenziali, schermo collegato, dimensione che segue la finestra" v_browser
elif [ "${DEMO_PROVA_BROWSER:-}" = "1" ]; then
    esito FALLITO "11. prova con un browser vero" "richiesta (DEMO_PROVA_BROWSER=1) ma node o playwright non ci sono"
else
    esito SALTATA "11. prova con un browser vero" "node o playwright non disponibili"
fi

v_ripristino() {
    demo ripristina prova-a >/dev/null 2>&1 || { dettaglio="il comando ripristina e' fallito"; return 1; }
    local comune file accesso partite
    comune="$(sql "$DB_A" "SELECT count(*) FROM catasto.comune WHERE nome='Comune di Prova'")"
    partite="$(sql "$DB_A" "SELECT count(*) FROM catasto.partita")"
    file="$(codice -u "demo:$PW_A" "$BASE/prova-a/file/Esportazioni%20Foliarium/prova.txt")"
    accesso="$(codice -u "demo:$PW_A" "$BASE/prova-a/")"
    attendi 90 finestra_principale "$APP_A" || { dettaglio="dopo il ripristino il programma non e' ripartito"; return 1; }
    dettaglio="comune di prova: $comune; partite: $partite; file: $file; accesso con le stesse credenziali: $accesso"
    [ "$comune" = 0 ] && [ "${partite:-0}" -gt 0 ] 2>/dev/null && [ "$file" = 404 ] && [ "$accesso" = 200 ]
}
verifica "12. dopo il ripristino: dati e file inseriti spariti, archivio iniziale, stesse credenziali" v_ripristino

if [ "$fallite" -gt 0 ]; then
    salva_registri
fi

v_rimozione() {
    demo rimuovi prova-a --si >/dev/null 2>&1 || { dettaglio="rimuovi prova-a e' fallito"; return 1; }
    demo rimuovi prova-b --si >/dev/null 2>&1 || { dettaglio="rimuovi prova-b e' fallito"; return 1; }
    local container volumi reti file accesso
    container="$(docker ps -a --format '{{.Names}}' | grep -c "^$DEMO_PREFISSO-prova-")"
    volumi="$(docker volume ls -q | grep -c "^$DEMO_PREFISSO-prova-")"
    reti="$(docker network ls --format '{{.Name}}' | grep -c "^$DEMO_PREFISSO-prova-")"
    file="$(find "$DEMO_CARTELLA_DATI/postazioni" "$DEMO_CARTELLA_DATI/proxy" -type f 2>/dev/null | wc -l | tr -d ' ')"
    accesso="$(codice -u "demo:$PW_A" "$BASE/prova-a/")"
    dettaglio="container $container, volumi $volumi, reti $reti, file $file; l'indirizzo ora risponde $accesso"
    [ "$container" = 0 ] && [ "$volumi" = 0 ] && [ "$reti" = 0 ] && [ "$file" = 0 ] && [ "$accesso" = 404 ]
}
verifica "13. dopo la rimozione non resta nulla delle postazioni" v_rimozione

# ---------------------------------------------------------------------------
totale=$((superate + fallite))
echo
echo "$superate/$totale verifiche superate$( [ "$saltate" -gt 0 ] && echo " ($saltate saltate)" )"
[ "$fallite" = 0 ]
