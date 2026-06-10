#!/bin/bash
# Apply soft delete migration to an existing database

DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"
DB_NAME="${DB_NAME:-catasto_storico}"
DB_USER="${DB_USER:-postgres}"

echo "Applying migration: soft delete archiviazione..."
echo "Target: $DB_USER@$DB_HOST:$DB_PORT/$DB_NAME"
echo

# Execute migration script
psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -f sql_scripts/07_soft_delete_archiviazione.sql

if [ $? -eq 0 ]; then
    echo
    echo "✓ Migration completed successfully!"
    echo
    echo "Verifying schema changes..."
    psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "\d catasto.partita" | grep archiviato
    echo
    echo "You can now restart Foliarium. RicercaPartiteWidget should work correctly."
else
    echo
    echo "✗ Migration failed. Check error messages above."
    exit 1
fi
