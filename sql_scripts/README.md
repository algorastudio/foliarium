# sql_scripts/

Script SQL per inizializzare PostgreSQL e applicare le feature successive.

## Casistica "partenza da zero"

Il flusso obbligatorio per un'installazione vergine è:

1. **Generare una password admin** (l'installer lo fa via Pascal randomicamente,
   `setup_database.py` lo accetta via `--admin-password`).
2. **Creare il database** ed eseguire **tutti** gli script in ordine numerico.
3. **Eseguire `07a_bootstrap_admin.sql`** passando la password come variabile
   psql. Senza questo step **non sarà possibile loggarsi** al primo avvio.

Questo è esattamente quello che fanno `setup_database.bat`, `setup_database.py`
e `prepare_demo_db.py`.

## Ordine di applicazione (fresh install)

| # | File | Cosa fa |
|---|------|---------|
| 01 | `01_creazione-database.sql` | `CREATE DATABASE catasto_storico` (gestito già dal bat) |
| 02 | `02_creazione-schema-tabelle.sql` | Schema base: tutte le tabelle e indici |
| 03 | `03_funzioni-procedure.sql` | Funzioni / procedure di base |
| 03b | `03b_expand_fuzzy_search.sql` | Funzioni di ricerca fuzzy (estensione) |
| 07 | `07_create_tipo_possesso_table.sql` | Lookup `tipo_possesso` |
| 07 | `07_soft_delete_archiviazione.sql` | Colonne `archiviato`/`archiviato_il` |
| 07 | `07_user-management.sql` | Schema `utente` + ruoli |
| 08 | `08_advanced-reporting.sql` | Materialized views + procedure di reporting |
| 09 | `09_backup-system.sql` | Tabella `backup_registro` + procedure |
| 10 | `10_performance-optimization.sql` | Procedure VACUUM/REINDEX |
| 11 | `11_advanced-cadastral-features.sql` | `nome_storico`, `documento_storico`, ALTER `localita.periodo_id` |
| 12 | `12_procedure_crud.sql` | Procedure CRUD per immobili / variazioni / contratti |
| 13 | `13_workflow_integrati.sql` | Procedure workflow complessi (registrazione proprietà, passaggi) |
| 14 | `14_report_functions.sql` | Funzioni di generazione report (genealogico, proprietà, ecc.) |
| 15 | `15_integration_audit_users.sql` | Integrazione audit-utenti |
| 16 | `16_advanced_search.sql` | Funzioni di ricerca avanzata possessori |
| 17 | `17_funzione_ricerca_immobili.sql` | Funzione di ricerca avanzata immobili |
| 18 | `18_funzioni_trigger_audit.sql` | Trigger di audit su tutte le tabelle |
| 19 | `19_creazione_tabella_sessioni.sql` | Tabella `sessioni_accesso` |
| 20 | `20_feature_tipi_localita.sql` | Lookup `tipo_localita` |
| 07 | `07_create_trigram_indexes.sql` | Indici GIN trigram (in fondo: `CONCURRENTLY` non si può mettere dentro una transazione) |
| **07a** | **`07a_bootstrap_admin.sql`** | **Crea l'utente `admin` con la password passata via `-v admin_password='...'`** |

Per il setup demo (`prepare_demo_db.py`) viene applicato anche
`05_demo_dataset.sql` come ultimo passo (dopo schema + feature).

## Variabili psql per `07a_bootstrap_admin.sql`

```bash
psql ... \
  -v admin_password="'mia_password_robusta'" \
  -v admin_email="'admin@mio-archivio.it'" \
  -f 07a_bootstrap_admin.sql
```

L'hash bcrypt è generato dinamicamente via estensione `pgcrypto` (l'estensione
viene creata dallo script stesso). Il prefisso `$2a` prodotto da pgcrypto è
compatibile con la libreria Python `bcrypt` usata dall'app.

Se `admin_password` non è passata, il default è `admin123` (solo per dev).

## Migrazioni per DB esistenti (`migrations/`)

Script che modificano la struttura di un DB già popolato. **Non vanno mai
applicati su un DB fresco** (perché creato già con la struttura corretta).

| File | Cosa fa | Quando applicarlo |
|------|---------|-------------------|
| `migrations/06_migrate_civico_to_nome.sql` | Concatena `civico` nel `nome` di `localita`, droppa la colonna | Solo su DB v ≤ 1.6.0 dove `localita.civico` esiste ancora |
| `migrations/10_migrate_drop_tipo_id.sql` | Rimuove `tipo_id` da `localita` (lookup table superata) | Solo su DB v ≤ 1.6.0 |

Per applicarne una: `psql -d catasto_storico -f migrations/<file>.sql`.

## Note

- Tutti i fresh-install avvengono via `setup_database.bat`/`.py` o
  `prepare_demo_db.py`. Non eseguire gli script SQL a mano se non per debug.
- L'ordine sopra è identico a quello hardcoded in `SQL_SCRIPTS` dei due file
  Python di setup. Se cambi un nome qui, aggiorna anche quelli.
- `00_svuota_dati.sql` è un'utility per svuotare le tabelle di test, non parte
  del flusso di install.
