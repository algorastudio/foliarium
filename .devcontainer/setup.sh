#!/usr/bin/env bash
# Setup automatico per GitHub Codespaces – Meridiana Catasto Storico
set -euo pipefail

# ── Colori per output ──────────────────────────────────────────────────────────
GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
step()  { echo -e "\n${GREEN}==>${NC} $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $*"; }
die()   { echo -e "${RED}[ERR ]${NC} $*" >&2; exit 1; }

# ── 1. Librerie di sistema per Qt6 ────────────────────────────────────────────
step "[1/4] Installazione librerie di sistema per Qt6"
sudo apt-get update -y -q
sudo apt-get install -y -q \
    libegl1 libgl1 libnss3 libnspr4 \
    libxkbcommon-x11-0 \
    libxcb-icccm4 libxcb-image0 libxcb-keysyms1 \
    libxcb-randr0 libxcb-render-util0 \
    libxcb-xinerama0 libxcb-xfixes0 \
    postgresql-client libpq-dev

# ── 2. Dipendenze Python ──────────────────────────────────────────────────────
step "[2/4] Installazione dipendenze Python"

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

# ── 3. Attesa PostgreSQL ──────────────────────────────────────────────────────
step "[3/4] Inizializzazione database"
echo "  Attendo che PostgreSQL sia pronto..."
for i in $(seq 1 30); do
    pg_isready -h localhost -U postgres -q && break
    sleep 1
done
pg_isready -h localhost -U postgres -q || die "PostgreSQL non risponde dopo 30s"

export PGPASSWORD="${PGPASSWORD:-postgres}"

# Crea il database se non esiste
DB="${PGDATABASE:-catasto_storico}"
psql -h localhost -U postgres -tc \
    "SELECT 1 FROM pg_database WHERE datname='$DB'" \
    | grep -q 1 \
    || psql -h localhost -U postgres -c "CREATE DATABASE \"$DB\";"

# ── 4. Applica gli script SQL in ordine ───────────────────────────────────────
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
step "[4/4] Setup completato"
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
