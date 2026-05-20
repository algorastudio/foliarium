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

---

## Script admin manuali

Gli script in `sql_scripts/admin/` **non** sono auto-applicati e vanno
eseguiti dal superuser quando serve (non sono migrazioni versionate).

### `05_fix_mv_ownership.sql` — ownership materialized view

PostgreSQL ≤ 16 richiede che `REFRESH MATERIALIZED VIEW` sia eseguito
dal **proprietario** della MV (non basta `GRANT`). Se le MV sono state
create da `postgres` durante il setup iniziale, ma la GUI si connette
con un utente applicativo dedicato, ogni refresh fallisce con
`InsufficientPrivilege`:

```
psycopg2.errors.InsufficientPrivilege:
permesso negato per la vista materializzata mv_immobili_per_tipologia
```

**Fix:** trasferire l'ownership di tutte le MV dello schema applicativo
all'utente che la GUI userà:

```bash
psql -U postgres -d catasto_storico \
     -v target_user=foliarium_app \
     -f sql_scripts/admin/05_fix_mv_ownership.sql
```

Variabile opzionale: `target_schema` (default `catasto`). Lo script è
idempotente: salta le MV già di proprietà dell'utente target e stampa
un report `MOVE`/`OK` per ognuna.

### `06_grant_app_user_privileges.sql` — privilegi utente applicativo

Le migrazioni successive al setup iniziale possono creare nuove tabelle
o sequenze senza riapplicare i `GRANT`. Il sintomo tipico è il fallimento
di pg_dump durante il backup:

```
pg_dump: errore: query fallita:
ERRORE: permesso negato per la sequenza audit_log_id_seq
```

**Fix:** concedere all'utente applicativo i privilegi su tutti gli
oggetti dello schema (esistenti) e impostare `ALTER DEFAULT PRIVILEGES`
per coprire quelli futuri:

```bash
psql -U postgres -d catasto_storico \
     -v target_user=foliarium \
     -f sql_scripts/admin/06_grant_app_user_privileges.sql
```

Lo script copre: schema (USAGE), tabelle (SELECT/INSERT/UPDATE/DELETE),
sequenze (USAGE/SELECT/UPDATE), funzioni (EXECUTE) — sia per l'utente
corrente che per `postgres` come role-creatore delle migrazioni future.
Stampa al termine una tabella di verifica dei privilegi sulle sequenze.

---

## Release tag-based

Foliarium pubblica le release in modo automatico quando viene
**pushato un tag** `X.Y.Z` o `vX.Y.Z` (vedi
`.github/workflows/pipeline_foliarium.yml`, job `create-release`).

Il flusso completo è:

1. **Preparazione changelog** — `python bin/release.py draft` genera
   la bozza della nuova sezione dal git log (commit dall'ultimo tag
   raggruppati per tipo: feat/fix/refactor/test/docs/ci/chore).
   Copiare la bozza in `docs/riferimento/changelog.md`, editare e
   accorpare.

2. **Bump versione** — aggiornare `APP_VERSION` in `config.py`.

3. **Commit** delle modifiche al changelog + config.py
   (es. `git commit -am "release: v1.0.2"`).

4. **Tag locale** — `python bin/release.py tag 1.0.2` crea il tag
   annotato dopo verifiche di coerenza (branch, APP_VERSION).

5. **Push del tag** — `git push origin 1.0.2` triggera il job
   `create-release` che:
   - aspetta i build job (windows/demo/unified/linux/macos);
   - estrae la sezione `## v1.0.2` dal changelog come note di release;
   - calcola SHA-256 di tutti gli asset;
   - crea/aggiorna la GitHub Release con asset + checksum.

### Comandi `bin/release.py`

| Comando | Scopo |
|---|---|
| `release.py version` | mostra versione attuale + suggerita |
| `release.py draft [--version X] [--force]` | stampa bozza changelog |
| `release.py tag X.Y.Z [--yes]` | crea il tag git locale |

---

## Pre-commit hooks

Foliarium include un `.pre-commit-config.yaml` che attiva tre gate
locali, allineati alla CI:

| Hook | Scope |
|---|---|
| `ruff` (F821/E9/F811) | nomi non definiti, errori di sintassi, redefinition |
| `check-api-drift` | confronto fra metodi `db/*.py` e chiamanti |
| `no-trailing-whitespace-py` | trailing whitespace sui `.py` |

### Setup

```bash
pip install pre-commit
pre-commit install
```

Da qui in poi ogni `git commit` esegue i hook sui file modificati.

### Esecuzione manuale

```bash
pre-commit run --all-files       # tutti i file del repo
pre-commit run --files db/comuni.py   # solo un file specifico
```

### Disattivazione temporanea

```bash
git commit --no-verify -m "..."
```

Da usare solo in emergenza; la CI eseguirà comunque gli stessi gate.
