#!/usr/bin/env bash
# ============================================================================
# install.sh — Script di installazione Foliarium per Linux e macOS
#
# Uso:
#   chmod +x install.sh
#   sudo ./install.sh                     # Installazione completa
#   sudo ./install.sh --install-dir /opt/foliarium
#   ./install.sh --skip-service           # Senza registrazione servizio
#   sudo ./install.sh --uninstall         # Disinstallazione
#
# Prerequisiti:
#   - Python 3.10+ con pip
#   - Pacchetto tarball Foliarium estratto nella directory corrente
#   - Diritti sudo per registrare il servizio di sistema
# ============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
INSTALL_DIR="${INSTALL_DIR:-$SCRIPT_DIR}"
PG_VERSION="14.13"
SYSTEM="$(uname -s)"

# Colori per output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log()   { echo -e "  ${GREEN}✓${NC} $1"; }
warn()  { echo -e "  ${YELLOW}⚠${NC} $1"; }
error() { echo -e "  ${RED}✗${NC} $1" >&2; }

# ============================================================================
# Verifica prerequisiti
# ============================================================================
check_prerequisites() {
    echo ""
    echo "========================================"
    echo " Foliarium — Verifica prerequisiti"
    echo "========================================"

    # Python
    if command -v python3 &>/dev/null; then
        PY="python3"
        log "Python3 trovato: $($PY --version)"
    elif command -v python &>/dev/null; then
        PY="python"
        log "Python trovato: $($PY --version)"
    else
        error "Python 3.10+ richiesto ma non trovato."
        error "Installare con: sudo apt install python3  (Ubuntu/Debian)"
        error "                brew install python3       (macOS)"
        exit 1
    fi

    # setup_database.py
    if [[ ! -f "$INSTALL_DIR/setup_database.py" ]]; then
        error "setup_database.py non trovato in $INSTALL_DIR"
        error "Assicurarsi di eseguire lo script dalla directory di installazione."
        exit 1
    fi
}

# ============================================================================
# Download PostgreSQL portabile (se non presente)
# ============================================================================
download_postgresql() {
    if [[ -d "$INSTALL_DIR/pgsql/bin" ]]; then
        log "PostgreSQL già presente in pgsql/"
        return
    fi

    echo ""
    echo "[Download] PostgreSQL $PG_VERSION portabile..."

    local pg_url=""
    local pg_archive=""

    if [[ "$SYSTEM" == "Linux" ]]; then
        pg_url="https://get.enterprisedb.com/postgresql/postgresql-${PG_VERSION}-1-linux-x64-binaries.tar.gz"
        pg_archive="pg_portable.tar.gz"
    elif [[ "$SYSTEM" == "Darwin" ]]; then
        # macOS: prova Homebrew prima, poi download manuale
        if command -v brew &>/dev/null; then
            log "Installazione PostgreSQL via Homebrew..."
            brew install postgresql@14 2>/dev/null || true
            local brew_pg="$(brew --prefix postgresql@14 2>/dev/null || echo "")"
            if [[ -n "$brew_pg" && -d "$brew_pg/bin" ]]; then
                mkdir -p "$INSTALL_DIR/pgsql"
                ln -sf "$brew_pg/bin" "$INSTALL_DIR/pgsql/bin"
                ln -sf "$brew_pg/lib" "$INSTALL_DIR/pgsql/lib"
                ln -sf "$brew_pg/share" "$INSTALL_DIR/pgsql/share"
                log "PostgreSQL collegato da Homebrew: $brew_pg"
                return
            fi
        fi
        pg_url="https://get.enterprisedb.com/postgresql/postgresql-${PG_VERSION}-1-osx-binaries.zip"
        pg_archive="pg_portable.zip"
    fi

    if [[ -z "$pg_url" ]]; then
        error "Piattaforma '$SYSTEM' non supportata per il download automatico."
        error "Installare PostgreSQL manualmente e copiare in $INSTALL_DIR/pgsql/"
        exit 1
    fi

    log "Download da: $pg_url"
    if command -v wget &>/dev/null; then
        wget -q --show-progress -O "$pg_archive" "$pg_url"
    elif command -v curl &>/dev/null; then
        curl -L --progress-bar -o "$pg_archive" "$pg_url"
    else
        error "wget o curl necessario per il download."
        exit 1
    fi

    log "Estrazione..."
    if [[ "$pg_archive" == *.tar.gz ]]; then
        tar xzf "$pg_archive" -C "$INSTALL_DIR"
    else
        unzip -q "$pg_archive" -d "$INSTALL_DIR"
    fi
    rm -f "$pg_archive"

    # Pulizia componenti non necessari
    rm -rf "$INSTALL_DIR/pgsql/pgAdmin 4" \
           "$INSTALL_DIR/pgsql/include" \
           "$INSTALL_DIR/pgsql/doc" \
           "$INSTALL_DIR/pgsql/symbols" 2>/dev/null || true

    if [[ -x "$INSTALL_DIR/pgsql/bin/pg_ctl" ]]; then
        log "PostgreSQL pronto in pgsql/"
    else
        error "Estrazione fallita: pgsql/bin/pg_ctl non trovato."
        exit 1
    fi
}

# ============================================================================
# Installazione
# ============================================================================
install() {
    check_prerequisites
    download_postgresql

    echo ""
    echo "========================================"
    echo " Foliarium — Inizializzazione Database"
    echo "========================================"

    # Esegue lo script Python di setup
    $PY "$INSTALL_DIR/setup_database.py" \
        --install-dir "$INSTALL_DIR" \
        "$@"
}

# ============================================================================
# Disinstallazione
# ============================================================================
uninstall() {
    check_prerequisites

    echo ""
    echo "========================================"
    echo " Foliarium — Disinstallazione"
    echo "========================================"

    $PY "$INSTALL_DIR/setup_database.py" \
        --install-dir "$INSTALL_DIR" \
        --uninstall
}

# ============================================================================
# Main
# ============================================================================
main() {
    local do_uninstall=false
    local extra_args=()

    for arg in "$@"; do
        case "$arg" in
            --uninstall)
                do_uninstall=true
                ;;
            --install-dir=*)
                INSTALL_DIR="${arg#*=}"
                ;;
            --install-dir)
                # Gestito dal prossimo argomento
                ;;
            *)
                extra_args+=("$arg")
                ;;
        esac
    done

    if $do_uninstall; then
        uninstall
    else
        install "${extra_args[@]}"
    fi
}

main "$@"
