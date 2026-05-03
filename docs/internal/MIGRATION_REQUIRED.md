# Database Migration Required: Soft Delete System

## Problem

Your RicercaPartiteWidget is experiencing freezing and layout issues because the database schema is missing the **soft delete (archiviazione) columns** that the application code now expects.

All the code fixes have been implemented and committed to the branch:
- ✅ RicercaPartiteWidget converted to QTableWidget (no more freeze)
- ✅ Interactive column resizing implemented
- ✅ Search results limited to 500 with truncation message
- ✅ Archived items filtered from searches

But the database hasn't been updated yet.

## Root Cause

When the search_partite() method runs:

```sql
SELECT ... FROM catasto.partita p 
WHERE NOT p.archiviato  -- ← This column doesn't exist in your DB yet!
```

The query fails because the `archiviato` column is missing, causing silent errors and the UI to freeze.

## Solution

Execute the migration script on your PostgreSQL database:

### Windows Users

1. Open Command Prompt or PowerShell
2. Navigate to the Foliarium folder
3. Run:
   ```cmd
   apply_migration.bat
   ```

Or manually:
   ```cmd
   psql -U postgres -d catasto_storico -f sql_scripts\07_soft_delete_archiviazione.sql
   ```

### Linux/macOS Users

1. Open Terminal
2. Navigate to the Foliarium folder
3. Run:
   ```bash
   bash apply_migration.sh
   ```

Or manually:
   ```bash
   psql -U postgres -d catasto_storico -f sql_scripts/07_soft_delete_archiviazione.sql
   ```

### If PostgreSQL Credentials Are Different

Set environment variables before running the script:

**Windows (CMD):**
```cmd
set DB_HOST=your_host
set DB_PORT=5432
set DB_NAME=catasto_storico
set DB_USER=your_username
apply_migration.bat
```

**Linux/macOS (Bash):**
```bash
export DB_HOST=your_host
export DB_PORT=5432
export DB_NAME=catasto_storico
export DB_USER=your_username
bash apply_migration.sh
```

## What the Migration Does

The script `07_soft_delete_archiviazione.sql` adds the following to your database:

1. **New columns for Comuni, Partite, Località:**
   - `archiviato` (BOOLEAN, default FALSE)
   - `archiviato_il` (TIMESTAMP)
   
2. **Index on `archiviato` column** for query performance

3. **For Possessori:**
   - Adds `archiviato_il` column (uses existing `attivo` column)

No existing data is deleted or modified — all values default to unarchived.

## After Migration

Once complete:

1. **Restart Foliarium**
2. **RicercaPartiteWidget should load instantly** without freezing
3. **New "Archivio" tab appears** in the sidebar for managing archived items
4. **Soft delete context menu** appears on records (right-click → Archivia)

## Verification

After running the migration, verify it worked:

```sql
\d catasto.partita
```

You should see:
```
 archiviato      | boolean              | not null default false
 archiviato_il   | timestamp without... |
```

## If the Migration Fails

### Error: "column 'archiviato' already exists"

This means the migration was already applied. Just restart Foliarium.

### Error: "permission denied"

Your PostgreSQL user doesn't have ALTER TABLE permission. Ask your database administrator, or connect as a superuser:

```cmd
psql -U postgres -d catasto_storico -f sql_scripts\07_soft_delete_archiviazione.sql
```

### Error: "could not connect to server"

PostgreSQL isn't running. Start your PostgreSQL service:

**Windows (if installed as service):**
```cmd
net start PostgreSQL14
```

**Windows (if portable):**
Open the PostgreSQL service in Services app and click Start.

**Linux:**
```bash
sudo systemctl start postgresql
```

## Timeline

- All code fixes → committed to branch on 2026-05-01
- Database schema → **needs migration on your machine**
- Expected to be fully functional after migration

## Questions?

Consult the logs if something goes wrong:
- Windows: `%LOCALAPPDATA%\Foliarium\logs\`
- Linux/macOS: `~/.local/share/Foliarium/logs/`
