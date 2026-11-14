# sql_scripts/

Script SQL per inizializzare PostgreSQL per Foliarium.
Struttura riorganizzata in v1.7.0: sottocartelle per tema invece di un unico flat layout.

## Struttura

```
sql_scripts/
├── schema/
│   ├── 01_tables.sql          # Tabelle, vincoli, indici base, lookup, audit_log
│   └── 02_trigram_indexes.sql # Indici GIN trigram CONCURRENTLY (ultimo passo)
├── functions/
│   ├── 01_core.sql            # Funzioni core: trigger timestamp, inserimento base, viste
│   ├── 02_crud.sql            # Procedure CRUD: aggiorna_immobile, duplica_partita, ecc.
│   ├── 03_workflow.sql        # Workflow integrati: registra_nuova_proprieta, passaggi, ecc.
│   ├── 04_search.sql          # Ricerca fuzzy (trigram) + ricerca avanzata possessori/immobili
│   ├── 05_reporting.sql       # Viste materializzate + funzioni di reporting
│   ├── 06_audit.sql           # Trigger audit, log_audit_trigger_function, FK audit→utente
│   └── 07_features.sql        # Feature avanzate: nomi storici, documenti, genealogia
├── admin/
│   ├── 01_users.sql           # Schema utente, permessi, sessioni
│   ├── 02_backup.sql          # Registro backup e procedure
│   ├── 03_performance.sql     # VACUUM/REINDEX procedure
│   └── 04_bootstrap_admin.sql # Crea utente admin (richiede -v admin_password)
├── demo/
│   └── demo_data.sql          # Dataset demo (solo ambienti demo/test)
├── utils/
│   ├── truncate_data.sql      # Svuota le tabelle (utility sviluppo)
│   └── validate_install.sql   # Validazione post-installazione (non parte del flusso)
└── migrations/                # Script per aggiornare DB già esistenti (vedi sotto)
```

## Flusso fresh install

Eseguito automaticamente da `setup_database.py` (installer) e da
`docker/postgres/init.sh` (container). L'elenco vive in
`setup_database.SQL_SCRIPTS`; `init.sh` ne tiene una copia, e
`tests/unit/test_docker_db_init.py` fallisce se le due divergono.

| # | File | Cosa fa |
|---|------|---------|
| 1 | `schema/01_tables.sql` | Schema completo: tutte le tabelle, indici, lookup, audit_log |
| 2 | `functions/01_core.sql` | Trigger timestamp, funzioni inserimento base, viste riepilogo |
| 3 | `functions/02_crud.sql` | Procedure CRUD per immobili, variazioni, contratti, duplicazione |
| 4 | `functions/03_workflow.sql` | Workflow complessi: registrazione proprietà, passaggi, frazionamenti |
| 5 | `functions/04_search.sql` | Ricerca fuzzy trigram + ricerca avanzata possessori e immobili |
| 6 | `functions/05_reporting.sql` | Materialized views statistiche + funzioni report testuali |
| 7 | `admin/01_users.sql` | Tabelle utente/permesso/sessioni + funzioni autenticazione app |
| 8 | `functions/06_audit.sql` | Trigger audit su tutte le tabelle, vista `v_audit_dettagliato`, FK audit_log→utente |
| 9 | `functions/07_features.sql` | Feature avanzate: genealogia, documenti storici, statistiche periodo |
| 10 | `admin/02_backup.sql` | Tabella backup_registro + procedure |
| 11 | `admin/03_performance.sql` | Procedure VACUUM/REINDEX |
| 12 | `schema/02_trigram_indexes.sql` | **Indici GIN CONCURRENTLY** — deve stare fuori transazione |
| — | `admin/04_bootstrap_admin.sql` | **Separato**: crea utente admin (richiede `-v admin_password`) |

**L'ordine non segue le cartelle, e non per caso.** `admin/01_users.sql` sta
fra le funzioni perché crea `catasto.utente`: `functions/06_audit.sql` ci
costruisce sopra la vista `v_audit_dettagliato` e la chiave esterna
`fk_audit_log_app_user_id_utente`, quindi deve venire dopo. A sua volta
`01_users.sql` usa `update_modified_column()`, definita in
`functions/01_core.sql`. Fino alla v1.0.2 i due script erano invertiti e il
setup, senza alcun avviso, non creava né la vista (che l'applicazione
ricreava poi all'avvio) né la chiave esterna (vedi
`migrations/23_add_fk_audit_log_utente.sql`).

Su un database nuovo l'elenco si applica senza errori con
`psql -v ON_ERROR_STOP=1`: è il modo in cui lo eseguono sia `init.sh` sia
`setup_database.py`, ed è verificato da
`tests/integration/test_schema_database_nuovo.py`.

Nei container, con `FOLIARIUM_DEMO_PASSWORD` impostata, `init.sh` applica
anche `demo/demo_user.sql`, `demo/demo_data.sql` e
`demo/demo_statistiche.sql`.

## Variabili psql per `admin/04_bootstrap_admin.sql`

```bash
psql -d catasto_storico \
  -v admin_password="mia_password_robusta" \
  -v admin_email="admin@mio-archivio.it" \
  -f admin/04_bootstrap_admin.sql
```

Se `admin_password` non è passata, il default è `admin123` (solo per dev/demo).

## Migrazioni per DB esistenti (`migrations/`)

Script da applicare **solo su DB già popolati** che aggiornano da versioni precedenti.
**Non vanno mai applicati su un DB fresco** (già creato con la struttura corretta).

| File | Cosa fa | Quando applicarlo |
|------|---------|-------------------|
| `migrations/06_migrate_civico_to_nome.sql` | Concatena `civico` nel `nome` di `localita` | DB v ≤ 1.6.0 |
| `migrations/10_migrate_drop_tipo_id.sql` | Rimuove `tipo_id` da `localita` | DB v ≤ 1.6.0 |
| `migrations/11_migrate_civico_to_immobile.sql` | Sposta civico da `localita.nome` a `immobile.numero_civico` | DB v ≤ 1.6.9 |
| `migrations/add_soft_delete.sql` | Aggiunge colonne soft-delete | DB ante v1.0.0 |
| `migrations/add_tipo_possesso.sql` | Crea lookup `tipo_possesso` | DB ante v1.0.0 |
| `migrations/add_sessioni_accesso.sql` | Crea tabella `sessioni_accesso` | DB ante v1.0.0 |
| `migrations/add_tipo_localita.sql` | Crea lookup `tipo_localita` | DB ante v1.0.0 |
| `migrations/23_add_fk_audit_log_utente.sql` | Crea la chiave esterna `audit_log.app_user_id → utente.id` (`ON DELETE SET NULL`) senza riscrivere il registro | DB creati da `setup_database.py` fino alla v1.0.2. L'applicazione la applica da sola all'avvio: a mano serve solo se il ruolo del database non può modificare le tabelle |

Per applicarne una: `psql -d catasto_storico -f migrations/<file>.sql`.

## Note

- I vecchi file numerati (`02_creazione-schema-tabelle.sql`, `03_funzioni-procedure.sql`, ecc.)
  sono mantenuti per compatibilità ma **non fanno più parte del flusso di install**.
  Verranno rimossi in una release futura.
- `utils/truncate_data.sql` è un'utility per svuotare le tabelle di test: non fa parte
  del flusso di installazione.
- `utils/validate_install.sql` contiene query di verifica post-installazione.
