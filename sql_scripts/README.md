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
| 02 | `02_creazione-schema-tabelle.sql` | Schema base: tabelle, indici, lookup `tipo_possesso`/`tipo_localita`, colonne soft-delete |
| 03 | `03_funzioni-procedure.sql` | Funzioni / procedure di base |
| 03b | `03b_expand_fuzzy_search.sql` | Funzioni di ricerca fuzzy (estensione) |
| 07 | `07_user-management.sql` | Schema `utente`, ruoli, permessi e tabella `sessioni_accesso` |
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
| 07 | `07_create_trigram_indexes.sql` | Indici GIN trigram (in fondo: `CONCURRENTLY` non si può mettere dentro una transazione) |
| **07a** | **`07a_bootstrap_admin.sql`** | **Crea l'utente `admin` con la password passata via `-v admin_password='...'`** |

Per il setup demo (`prepare_demo_db.py`) viene applicato anche
`05_demo_dataset.sql` come ultimo passo (dopo schema + feature).

### Cosa è stato consolidato in v1.0.0

Quattro micro-script di estensione precedentemente separati sono stati
inglobati nei due script principali per ridurre il numero di file e
chiarire la struttura del fresh install. Le versioni originali sono
state spostate in `migrations/` con un nome parlante per chi deve
aggiornare un DB già esistente:

| Confluito in (fresh install) | Migrazione (DB esistenti) | Cosa contiene |
|------------------------------|---------------------------|---------------|
| `02_creazione-schema-tabelle.sql` | `migrations/add_tipo_possesso.sql` | Lookup `tipo_possesso` + 8 valori di default |
| `02_creazione-schema-tabelle.sql` | `migrations/add_soft_delete.sql` | Colonne `archiviato`/`archiviato_il` + indici |
| `07_user-management.sql`          | `migrations/add_sessioni_accesso.sql` | Tabella `sessioni_accesso` (FK su `utente`) |
| `02_creazione-schema-tabelle.sql` | `migrations/add_tipo_localita.sql` | Lookup `tipo_localita` + 4 valori di default |

In v1.0.0 è stato anche **rimosso da `07_user-management.sql`** il blocco
che creava un utente `admin` con hash bcrypt hardcoded (`admin123`): quel
blocco vinceva la corsa contro `07a_bootstrap_admin.sql` e impediva
all'installer di iniettare la password generata casualmente.

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
| `migrations/add_soft_delete.sql` | Aggiunge `archiviato`/`archiviato_il` a comune, localita, partita, possessore | DB ante v1.0.0 senza colonne soft-delete |
| `migrations/add_tipo_possesso.sql` | Crea lookup `tipo_possesso` + 8 default | DB ante v1.0.0 senza la lookup |
| `migrations/add_sessioni_accesso.sql` | Crea tabella `sessioni_accesso` | DB ante v1.0.0 senza la tabella |
| `migrations/add_tipo_localita.sql` | Crea lookup `tipo_localita` + 4 default | DB ante v1.0.0 senza la lookup |

Per applicarne una: `psql -d catasto_storico -f migrations/<file>.sql`.

## Note

- Tutti i fresh-install avvengono via `setup_database.bat`/`.py` o
  `prepare_demo_db.py`. Non eseguire gli script SQL a mano se non per debug.
- L'ordine sopra è identico a quello hardcoded in `SQL_SCRIPTS` dei due file
  Python di setup. Se cambi un nome qui, aggiorna anche quelli.
- `00_svuota_dati.sql` è un'utility per svuotare le tabelle di test, non parte
  del flusso di install.
