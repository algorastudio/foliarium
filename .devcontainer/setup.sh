#!/usr/bin/env bash
# Setup automatico per GitHub Codespaces – Meridiana Catasto Storico
set -euo pipefail

# ── Colori per output ──────────────────────────────────────────────────────────
GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
step()  { echo -e "\n${GREEN}==>${NC} $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $*"; }
die()   { echo -e "${RED}[ERR ]${NC} $*" >&2; exit 1; }

# ── 1. PostgreSQL 14 via PGDG ─────────────────────────────────────────────────
step "[1/5] Installazione PostgreSQL 14"
sudo apt-get update -y -q
sudo apt-get install -y -q gnupg curl

# Aggiunge il repository ufficiale PGDG (più affidabile della devcontainer feature)
curl -fsSL https://www.postgresql.org/media/keys/ACCC4CF8.asc \
    | sudo gpg --dearmor -o /usr/share/keyrings/postgresql-keyring.gpg
echo "deb [signed-by=/usr/share/keyrings/postgresql-keyring.gpg] \
    https://apt.postgresql.org/pub/repos/apt bookworm-pgdg main" \
    | sudo tee /etc/apt/sources.list.d/pgdg.list > /dev/null

sudo apt-get update -y -q
sudo apt-get install -y -q postgresql-14 postgresql-client-14

# Configura autenticazione trust per localhost (dev environment)
sudo bash -c 'cat > /etc/postgresql/14/main/pg_hba.conf <<HBA
# Autenticazione locale – trust per sviluppo (Codespaces)
local   all   all                trust
host    all   all   127.0.0.1/32 trust
host    all   all   ::1/128      trust
HBA'

# Avvia PostgreSQL e verifica
sudo service postgresql start
pg_isready -h localhost -U postgres -q \
    || die "PostgreSQL non si è avviato correttamente"

echo "  PostgreSQL $(psql -h localhost -U postgres -Atc 'SELECT version()' | cut -d' ' -f1-2)"

# ── 2. Librerie di sistema per Qt6 ────────────────────────────────────────────
step "[2/5] Installazione librerie di sistema per Qt6"
sudo apt-get install -y -q \
    libegl1 libgl1 libnss3 libnspr4 \
    libxkbcommon-x11-0 \
    libxcb-icccm4 libxcb-image0 libxcb-keysyms1 \
    libxcb-randr0 libxcb-render-util0 \
    libxcb-xinerama0 libxcb-xfixes0 \
    libpq-dev

# ── 3. Dipendenze Python ──────────────────────────────────────────────────────
step "[3/5] Installazione dipendenze Python"

# Rileva venv creato da VS Code / Codespaces, altrimenti usa il Python globale
if [[ -n "${VIRTUAL_ENV:-}" ]]; then
    PIP="$VIRTUAL_ENV/bin/pip"
    PYTHON="$VIRTUAL_ENV/bin/python"
else
    PIP="pip"
    PYTHON="python"
fi

"$PIP" install --quiet --upgrade pip
"$PIP" install --quiet -r requirements.txt
"$PIP" install --quiet -r tests/requirements-test.txt

echo "  Python: $($PYTHON --version)"
echo "  Pip:    $($PIP --version)"

# ── 4. Inizializzazione database ──────────────────────────────────────────────
step "[4/5] Inizializzazione database"

DB="${PGDATABASE:-catasto_storico}"

# Crea il database se non esiste
psql -h localhost -U postgres -tc \
    "SELECT 1 FROM pg_database WHERE datname='$DB'" \
    | grep -q 1 \
    || psql -h localhost -U postgres -c "CREATE DATABASE \"$DB\";"

run_sql() {
    local f="$1"
    if [[ -f "$f" ]]; then
        echo "  Applico: $f"
        psql -h localhost -U postgres -d "$DB" -f "$f" \
            --on-error-stop -q 2>&1 \
            | grep -v "^NOTICE\|^SET\|^CREATE\|^ALTER\|^INSERT\|^DO" || true
    else
        warn "Script non trovato, salto: $f"
    fi
}

run_sql sql_scripts/02_creazione-schema-tabelle.sql
run_sql sql_scripts/03_funzioni-procedure.sql
run_sql sql_scripts/07_user-management.sql
run_sql sql_scripts/07a_bootstrap_admin.sql

# ── Completato ─────────────────────────────────────────────────────────────────
step "[5/5] Setup completato"
cat <<'EOF'

  ┌─────────────────────────────────────────────────┐
  │  Meridiana – Catasto Storico è pronto!          │
  │                                                 │
  │  Avvia l'app GUI:                               │
  │    python gui_main.py                           │
  │                                                 │
  │  Esegui i test:                                 │
  │    python -m pytest tests/                      │
  │                                                 │
  │  Desktop nel browser (porta 6080):              │
  │    password: meridiana                          │
  └─────────────────────────────────────────────────┘

EOF
