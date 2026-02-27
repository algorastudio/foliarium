#!/usr/bin/env bash
# Script di configurazione automatica per GitHub Codespaces
set -e

echo "=== [1/4] Installazione librerie di sistema per Qt6 ==="
sudo apt-get update -y -q
sudo apt-get install -y -q \
    libegl1 libgl1 libnss3 libnspr4 \
    libxkbcommon-x11-0 libxcb-icccm4 libxcb-image0 \
    libxcb-keysyms1 libxcb-randr0 libxcb-render-util0 \
    libxcb-xinerama0 libxcb-xfixes0 postgresql-client

echo "=== [2/4] Installazione dipendenze Python ==="
pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt
pip install --quiet -r tests/requirements-test.txt

echo "=== [3/4] Inizializzazione database di sviluppo ==="
# Attende che PostgreSQL sia pronto
until pg_isready -h localhost -U postgres; do
    echo "  Attendo PostgreSQL..."
    sleep 1
done

# Crea il database se non esiste
psql -h localhost -U postgres -tc \
    "SELECT 1 FROM pg_database WHERE datname='catasto_storico'" \
    | grep -q 1 || psql -h localhost -U postgres -c \
    "CREATE DATABASE catasto_storico;"

psql -h localhost -U postgres -d catasto_storico \
    -f sql_scripts/02_creazione-schema-tabelle.sql
psql -h localhost -U postgres -d catasto_storico \
    -f sql_scripts/03_funzioni-procedure.sql

echo "=== [4/4] Setup completato ==="
echo ""
echo "  Per avviare l'applicazione GUI:"
echo "    python gui_main.py"
echo ""
echo "  Per eseguire i test:"
echo "    python -m pytest tests/"
echo ""
echo "  Per aprire il desktop nel browser:"
echo "    Porta 6080 → Apri nel browser (password: meridiana)"
