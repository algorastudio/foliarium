#!/usr/bin/env bash
# avvia_server.sh — Avvia il server web Foliarium (Linux/macOS)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# Legge web.ini
read_ini() {
    local key="$1"
    grep -E "^\s*${key}\s*=" web.ini 2>/dev/null \
        | head -1 | sed 's/.*=\s*//' | tr -d '\r' | xargs
}

DB_HOST="$(read_ini host | head -1)"
DB_PORT="$(read_ini port | head -1)"
DB_NAME="$(read_ini name)"
DB_USER="$(read_ini user)"
DB_PASS="$(read_ini password)"
SRV_HOST="$(grep -A5 '\[server\]' web.ini | read_ini host || echo '0.0.0.0')"
SRV_PORT="$(grep -A5 '\[server\]' web.ini | read_ini port || echo '8000')"

# Valori di fallback
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"
SRV_HOST="${SRV_HOST:-0.0.0.0}"
SRV_PORT="${SRV_PORT:-8000}"

# Verifica build frontend
if [ ! -f "frontend/dist/index.html" ]; then
    echo "[AVVISO] Frontend non compilato. Esegui prima:"
    echo "  cd frontend && npm install && npm run build"
    exit 1
fi

export DB_HOST DB_PORT DB_NAME DB_USER DB_PASS

echo ""
echo " ================================================"
echo "  Foliarium Web — Server in esecuzione"
echo ""
echo "  Database : ${DB_HOST}:${DB_PORT}/${DB_NAME}"
echo "  Indirizzo: http://${SRV_HOST}:${SRV_PORT}"
echo ""
echo "  Aprire nel browser: http://localhost:${SRV_PORT}"
echo "  Per fermare: Ctrl+C"
echo " ================================================"
echo ""

python3 -m uvicorn api.main:create_app \
    --factory \
    --host "$SRV_HOST" \
    --port "$SRV_PORT"
