# Migrazioni Schema

Foliarium gestisce l'evoluzione dello schema database con un framework
leggero introdotto nella v1.0.1: la CLI `bin/migrate.py` + la tabella
`catasto.schema_version`. Non sostituisce alembic — è un sistema
deliberatamente minimo per uso interno.

## Quando serve

- **Installazione nuova**: tutto lo schema base viene creato da
  `setup_database.py` o dall'installer unificato. Le migrazioni servono
  per aggiornamenti successivi senza dover ricreare il DB.
- **Upgrade Foliarium**: dopo aver aggiornato l'eseguibile / sorgenti,
  applicare le migrazioni introdotte dalla nuova versione.
- **Bug fix lato schema**: alcune patch correggono funzioni / viste
  PostgreSQL bacate (vedi `20_fix_report_function_civico.sql`); senza
  applicarle, certe operazioni falliscono a runtime.

## Comandi

Tutti i comandi usano le stesse env var di connessione dell'applicazione
(`DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASS`).

### Mostrare lo stato

```bash
python bin/migrate.py status
```

Esempio output:

```
Migrazioni in sql_scripts/migrations:

  ✓ 00_schema_version_table.sql                          applicata
  ✓ 06_migrate_civico_to_nome.sql                        applicata
  ✓ 19_create_v_audit_dettagliato.sql                    applicata
  · 20_fix_report_function_civico.sql                    PENDENTE

Totale: 3/4 applicate.
```

### Applicare le pending

```bash
python bin/migrate.py up
```

Applica tutte le migrazioni non ancora registrate in
`catasto.schema_version`, in ordine alfabetico. Ogni script viene
eseguito in una transazione separata; se uno fallisce, lo stop è
immediato e il rollback è automatico (gli script già applicati restano).

### Dry-run

```bash
python bin/migrate.py up --dry-run
```

Mostra cosa verrebbe applicato (filename + checksum) senza eseguire
SQL. Utile prima di un deploy in produzione.

### Migrazione singola

```bash
python bin/migrate.py up --file 20_fix_report_function_civico.sql
```

Forza l'esecuzione di un file specifico (deve essere già in
`sql_scripts/migrations/`).

## Convenzioni

### Naming

```
NN_descrizione_breve.sql
```

- `NN` — numero progressivo zero-padded a 2 cifre (`00`, `01`, …, `99`).
  Per oltre 99 migrazioni usare 3 cifre.
- `descrizione_breve` — snake_case, max ~40 caratteri.
- `.sql` obbligatorio (gli altri file vengono ignorati dalla CLI).

L'ordinamento è alfabetico, quindi `19_X.sql` viene prima di
`20_Y.sql`. Migrazioni "ex-novo" inserite a posteriori devono usare un
numero successivo al massimo già applicato.

### Contenuto degli script

Ogni script deve essere **idempotente** (sicuro da rieseguire) e
**transazionalmente coerente**:

- Usare `CREATE TABLE IF NOT EXISTS`, `CREATE OR REPLACE VIEW`,
  `CREATE OR REPLACE FUNCTION`, `ALTER TABLE … ADD COLUMN IF NOT EXISTS`.
- Per inserimenti di dati lookup: `INSERT … ON CONFLICT DO NOTHING`.
- Per DDL che non supportano `IF NOT EXISTS` (es. constraint): wrap in
  `DO $$ BEGIN … EXCEPTION WHEN duplicate_object … END $$;`.

### Bootstrap della tabella

Al primo run su un DB privo di `catasto.schema_version`, `bin/migrate.py`
applica automaticamente `00_schema_version_table.sql` che:

1. Crea la tabella `(id, filename UNIQUE, applied_at, checksum, note)`.
2. **Backfill**: marca come "applicate" le migrazioni note già presenti
   nello schema (rileva indicatori: vista `v_audit_dettagliato`, colonna
   `archiviato` su `comune`, tabella `tipo_possesso`).

Questo evita di ri-applicare migrazioni già attive su DB esistenti.

## Auto-apply (best-effort)

`db/base.py::_apply_pending_schema_migrations()` applica
**silenziosamente** alcune migrazioni a ogni init pool dell'applicazione:

- Schema v1.6.1 (rimozione `tipo_id`, incorporazione `civico` in `nome`).
- Indici UNIQUE sulle materialized view (richiesti per
  `REFRESH MATERIALIZED VIEW CONCURRENTLY`).
- Vista `catasto.v_audit_dettagliato`.

Questo meccanismo **coesiste** con la CLI: le auto-migrations sono casi
specifici hardcoded, mentre `bin/migrate.py` gestisce qualsiasi `.sql`
nella cartella. Best-effort: errori di auto-apply sono loggati a debug
e non bloccano l'avvio.

## Pipeline CI

Il workflow `.github/workflows/pipeline_foliarium.yml` applica le
migrazioni critiche dopo l'init DB nel job di test:

```yaml
psql -h localhost -U postgres -d catasto_storico \
  -f sql_scripts/migrations/20_fix_report_function_civico.sql
```

Quando si aggiunge una nuova migrazione che è necessaria per i test in
CI, aggiungere uno step `psql ... -f ...` analogo (o, in alternativa,
aggiungere `python bin/migrate.py up` come step unico).

## Rollback

Le migrazioni Foliarium **non hanno rollback automatico**. Se uno
script causa problemi:

1. Identificare il problema dai log (PostgreSQL log o
   `%LOCALAPPDATA%\Foliarium\logs\`).
2. Scrivere uno script di "anti-migration" (es. `21_rollback_20.sql`)
   con i DDL inversi.
3. Applicarlo via `bin/migrate.py up --file 21_rollback_20.sql`.
4. Manualmente rimuovere la riga corrispondente da
   `catasto.schema_version` se si vuole permettere la riapplicazione.

Per scenari più complessi (DB di produzione, dati a rischio): backup
prima della migration via *Sistema → Backup* nell'applicazione, poi
restore se la migrazione causa problemi.
