#!/bin/bash
# avvio.sh — punto d'ingresso del container della demo.
#
# Avvia, nell'ordine: lo schermo virtuale (Xvnc), il gestore di finestre, il
# ponte WebSocket che porta lo schermo al browser, la pagina di download dei
# file e infine Foliarium, che viene rilanciato ogni volta che termina.
#
# Se uno dei servizi di contorno muore, il container esce con errore e Docker
# lo riavvia: meglio una postazione che riparte di una rimasta a meta'.
set -euo pipefail

log() { echo "[avvio] $*" >&2; }

CODICE=/opt/foliarium
STRUMENTI=/opt/foliarium-demo
# Dimensione iniziale dello schermo, prima che un browser ne chieda un'altra.
# 1920x1080 e' quella a cui Foliarium appare come progettato: sotto i 1000
# pixel di altezza la pagina iniziale comprime i pulsanti delle azioni rapide.
SCHERMO="${DEMO_SCHERMO:-1920x1080}"
DOCUMENTI="$HOME/Documenti"
ESPORTAZIONI="$DOCUMENTI/Esportazioni Foliarium"

DEMO_DB_HOST="${DEMO_DB_HOST:-db}"
DEMO_DB_PORT="${DEMO_DB_PORT:-5432}"
export DEMO_DB_HOST DEMO_DB_PORT

# ---------------------------------------------------------------------------
# 1. Cartella personale
# ---------------------------------------------------------------------------
# Tutto cio' che il cliente salva deve finire nella cartella che la pagina di
# download pubblica, cioe' Documenti. L'applicazione usa due percorsi:
#   - le finestre «Salva con nome» propongono <Documenti>/Esportazioni
#     Foliarium (app_utils._get_default_export_path);
#   - app_paths.ESPORTAZIONI_DIR e' ~/.foliarium/esportazioni.
# Il primo si indirizza dichiarando a Qt dove sta Documenti; il secondo
# diventa un collegamento al primo. Il collegamento va creato PRIMA che
# qualcosa importi app_paths, che altrimenti crea la cartella vera.
mkdir -p "$HOME/.config" "$HOME/.foliarium" "$ESPORTAZIONI" "$XDG_RUNTIME_DIR"
chmod 700 "$XDG_RUNTIME_DIR"

cat > "$HOME/.config/user-dirs.dirs" <<'EOF'
XDG_DOCUMENTS_DIR="$HOME/Documenti"
XDG_DOWNLOAD_DIR="$HOME/Documenti"
XDG_DESKTOP_DIR="$HOME/Documenti"
EOF

if [ ! -e "$HOME/.foliarium/esportazioni" ]; then
    ln -s "$ESPORTAZIONI" "$HOME/.foliarium/esportazioni"
fi

# File d'esempio per provare l'import: il cliente non puo' caricarne di suoi.
# Si copiano solo se la cartella manca, per non sovrascrivere modifiche.
if [ ! -e "$DOCUMENTI/Esempi import" ]; then
    cp -r "$STRUMENTI/esempi-import" "$DOCUMENTI/Esempi import"
fi

if [ "${DEMO_SALTA_EULA:-}" = "1" ]; then
    # Registra l'EULA come accettata, con le stesse chiavi che scrive
    # l'applicazione (foliarium/ui/startup.py). Le costanti vengono lette da
    # config.py, cosi' un cambio di versione dell'EULA non rompe questo passo.
    (cd "$CODICE" && QT_QPA_PLATFORM=offscreen python - <<'PY'
from PyQt6.QtCore import QCoreApplication, QSettings
from config import EULA_VERSION, SETTINGS_EULA_ACCEPTED

app = QCoreApplication([])
QCoreApplication.setOrganizationName("AlgoraStudio")
QCoreApplication.setApplicationName("Foliarium")
impostazioni = QSettings()
impostazioni.setValue(SETTINGS_EULA_ACCEPTED, EULA_VERSION)
impostazioni.sync()
PY
    )
    log "EULA registrata come accettata (DEMO_SALTA_EULA=1)"
fi

# ---------------------------------------------------------------------------
# 2. Schermo virtuale
# ---------------------------------------------------------------------------
# Nessuna autenticazione VNC: la porta ascolta solo in locale e chi arriva dal
# browser e' gia' stato autenticato dal proxy. -AlwaysShared: due persone che
# aprono la stessa postazione vedono lo stesso schermo. Il ridimensionamento
# chiesto dal client (AcceptSetDesktopSize) e' attivo di default.
rm -f /tmp/.X1-lock /tmp/.X11-unix/X1
Xvnc :1 -geometry "$SCHERMO" -depth 24 \
    -SecurityTypes None -localhost -AlwaysShared \
    -rfbport 5900 -desktop "Foliarium Demo" &
PID_SCHERMO=$!

for _ in $(seq 1 100); do
    [ -S /tmp/.X11-unix/X1 ] && break
    sleep 0.2
done
if [ ! -S /tmp/.X11-unix/X1 ]; then
    log "ERRORE: lo schermo virtuale non e' partito"
    exit 1
fi

# Fondo dello schermo: il grigio chiaro dell'applicazione al posto del nero,
# che attorno alla finestra dell'EULA o di un dialogo sembrerebbe un guasto.
xsetroot -solid "#eef0f6" || log "avviso: colore di fondo non impostato"

# ---------------------------------------------------------------------------
# 3. Servizi di contorno
# ---------------------------------------------------------------------------
openbox --config-file "$STRUMENTI/openbox-rc.xml" &
PID_FINESTRE=$!

websockify --web "$STRUMENTI/web" 6080 127.0.0.1:5900 &
PID_PONTE=$!

DEMO_FILE_RADICE="$DOCUMENTI" python "$STRUMENTI/file_server.py" &
PID_FILE=$!

# ---------------------------------------------------------------------------
# 4-5. Foliarium, rilanciato ogni volta che termina
# ---------------------------------------------------------------------------
# In modalita' demo, se il database non risponde l'applicazione mostra un
# errore modale e aspetta che qualcuno prema OK: su un server nessuno lo
# fara'. Per questo si attende il database PRIMA di ogni lancio.
#
# L'immagine postgres, mentre applica gli script iniziali, ascolta solo sul
# socket Unix: quando risponde via TCP l'inizializzazione e' conclusa.
attendi_database() {
    local avvisato=0
    until pg_isready -q -h "$DEMO_DB_HOST" -p "$DEMO_DB_PORT" -t 3; do
        if [ "$avvisato" = 0 ]; then
            log "in attesa del database su $DEMO_DB_HOST:$DEMO_DB_PORT..."
            avvisato=1
        fi
        sleep 2
    done
}

ciclo_programma() {
    while true; do
        attendi_database
        log "avvio di Foliarium"
        # Directory di lavoro: la cartella personale. Quella del codice e' in
        # sola lettura per questo utente.
        (cd "$HOME" && exec python "$CODICE/gui_main.py") || true
        log "Foliarium e' terminato: riparte fra 2 secondi"
        sleep 2
    done
}
ciclo_programma &
PID_CICLO=$!

# ---------------------------------------------------------------------------
# 6. Sorveglianza
# ---------------------------------------------------------------------------
arresta() {
    log "arresto"
    kill "$PID_CICLO" "$PID_FILE" "$PID_PONTE" "$PID_FINESTRE" "$PID_SCHERMO" 2>/dev/null || true
    pkill -f "$CODICE/gui_main.py" 2>/dev/null || true
    exit "${1:-0}"
}
trap 'arresta 0' TERM INT

# wait -n ritorna appena UNO dei processi elencati termina. Fra questi c'e'
# il ciclo che rilancia il programma: se morisse lui, nessuno farebbe piu'
# ripartire Foliarium e la postazione resterebbe accesa con la scrivania
# vuota. Uscendo, Docker riavvia il container.
wait -n "$PID_SCHERMO" "$PID_FINESTRE" "$PID_PONTE" "$PID_FILE" "$PID_CICLO" || true
log "ERRORE: un servizio della postazione e' terminato; il container esce"
arresta 1
