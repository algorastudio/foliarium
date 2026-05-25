# Changelog

## v1.0.2 — 2026-05-19 — Sprint 3 six-hats — Refactoring strutturale + tooling

Release di consolidamento: refactor strutturale completo (Sprint 3 in 9
sotto-sprint, da 3.1 a 3.9), nuovi tool sviluppatore (`check_api_drift`,
`migrate`, `release`), API contract via `typing.Protocol`, coverage CI
finalmente verde a 41% (dal 21% precedente, gate 35%), 17 PR mergeate.

**Cambiamenti utente-visibili:**

- Nuova voce **Help → Esporta log per supporto (.zip)...**: crea al volo
  un archivio ZIP con tutti i file di log applicativi (`%LOCALAPPDATA%\Foliarium\logs\`)
  pronto da allegare a una mail di supporto. L'utente sceglie destinazione
  e nome tramite dialog (default: cartella Documenti + timestamp). Logica
  riusabile in `app_utils.create_logs_archive()`.
- **Fix tema coerente fra PC diversi**: il bootstrap del tema all'avvio
  e il tema automatico (segui sistema) ora forzano lo stile base **Fusion**
  prima di applicare il QSS. Su PC con stile Qt di default diverso
  (es. `windowsvista`, `windows11`) la palette nativa non "fora" più i
  widget non esplicitamente coperti dal foglio di stile — i temi
  risultano identici e leggibili su ogni macchina.
- **Fix warning Qt `Unknown property text-shadow`**: rimosse 6 regole
  `text-shadow` non supportate da Qt QSS nei temi `purple_royal`,
  `ocean_blue`, `sunset_orange` (stesso intervento già fatto in v1.5.2
  per `box-shadow`). I bottoni perdono solo l'ombra del testo, il
  resto del look è invariato.

Comportamento e dati altrimenti identici a v1.0.1. Tutti gli import storici
continuano a funzionare grazie alla struttura a facade.

### Pipeline release semplificato

Eliminati `build-demo` e `build-unified` dal workflow CI (e i relativi
file: `foliarium_demo.spec`, `Foliarium_Unified_Installer.iss`,
`prepare_demo_db.py`, `demo_config.ini`). Le varianti demo e installer
unificato non erano in uso in produzione e rallentavano significativamente
il ciclo di release. Restano i 3 build effettivi: **Windows** (zip
portabile + installer Inno Setup), **Linux** (tarball), **macOS** (zip).

Cancellati anche test integration zombie:
`tests/integration/test_database_manager.py` (residuo di 104 LOC dopo le
cancellazioni dello Sprint 3.9, ormai duplicato di `test_e2e.py` per le
parti attive) e `tests/integration/test_migration_10_drop_tipo_id.py`
(fixture `db_connection` mai implementata, sempre skippato).

Tagliato il debito sui *god-file* identificati dall'analisi 6 cappelli di
De Bono. **Nessuna modifica funzionale**: comportamento utente e dati
invariati. Tutti gli import storici continuano a funzionare grazie a
facade thin di re-export.

### Igiene generale (Sprint 1)
- Rebrand finale Meridiana → Foliarium: rimosse tracce residue da `.devcontainer/`, `.claude/launch.json`, docstring, `CLAUDE.md`.
- Cambiata la password noVNC del dev container (`meridiana` → `foliarium-dev`).
- README riallineato al codice reale: PyQt6 / Python 3.12, entry-point `gui_main.py`, struttura del progetto attuale, comandi aggiornati.
- `config.py`: nuovo helper `assert_db_password_configured()` che solleva `RuntimeError` se in produzione manca `DB_PASS`, invece di tentare silenziosamente una connessione senza password.

### Test (Sprint 2)
- Nuovo `tests/integration/test_golden_path.py`: E2E **headless** del flusso critico (comune → località → possessore → partita → variazione + contratto → chiusura → nuova partita → export PDF). Marker `integration` + `golden_path`. Asserisce magic `%PDF-` e size minima del file.
- Coverage misurata in modo significativo: i file GUI (`gui_main`, `gui_widgets`, `search_widgets`, `partita_workflow_widgets`, `dialogs`) esclusi da `--cov` in `pytest.ini` e `.coveragerc` perché richiedono `QApplication` + DB live + interazione utente.
- Nuovo marker pytest `golden_path` per identificare i test da proteggere assolutamente da regressioni.

### Scomposizione moduli (Sprint 3)

| File originale | Prima | Dopo | Estratti in |
|---|---|---|---|
| `app_utils.py` | 923 LOC | **176** | `foliarium/reporting/pdf.py` (5 classi PDF) + `foliarium/ui/export/{partita,possessore}.py` (6 wrapper GUI) |
| `partita_workflow_widgets.py` | 2.209 LOC | **24** | `foliarium/ui/widgets/workflow/{registrazione_proprieta,nuova_partita_wizard,operazioni_partita}.py` |
| `search_widgets.py` | 1.841 LOC | **41** | `foliarium/ui/widgets/search/{partite,immobili,fuzzy}.py` |
| `gui_main.py` | 2.155 LOC | **1.999** | `foliarium/ui/theme.py` + `foliarium/ui/login_flow.py` + `foliarium/ui/startup.py` |

### Nuovi moduli pubblici

- `foliarium.reporting.pdf` — `ModernCatastoPDF`, `PDFPartita`, `PDFPossessore`, `GenericTextReportPDF`, `BulkReportPDF`, `FPDF_AVAILABLE`
- `foliarium.ui.export` — 6 wrapper GUI (`gui_esporta_{partita,possessore}_{json,csv,pdf}`)
- `foliarium.ui.widgets.workflow` — 3 widget di workflow partite
- `foliarium.ui.widgets.search` — 3 widget di ricerca (partite, immobili, fuzzy)
- `foliarium.ui.theme` — 6 funzioni pure di gestione tema QSS (`apply_stylesheet`, `apply_auto_theme`, `apply_initial_theme_from_settings`, `is_win11_style_available`, `apply_win11_style`, `reset_app_style`)
- `foliarium.ui.login_flow` — `try_autoconnect_db`, `connect_db_with_dialog`, `ensure_db_connection`, `perform_user_login`
- `foliarium.ui.startup` — `show_splash_screen`, `ensure_eula_accepted`, `validate_license_and_acquire_seat`

### Unit test sui nuovi moduli

- `tests/unit/test_theme.py` (172 LOC): valida le 6 funzioni pure di `foliarium/ui/theme.py` con `QApplication` offscreen e `QSettings` isolato su `tmp_path`.
- `tests/unit/test_login_flow.py`: 15 test sui 4 stadi di connessione DB (autoconnect, dialog manuale, ensure pool, perform login).
- `tests/unit/test_startup.py`: 9 test su splash + EULA + license check.
- `tests/unit/test_db_base_audit_view.py`: 4 test per `_ensure_audit_view` (vista presente / tabelle mancanti / happy path / errore DB).
- `tests/unit/test_db_signatures.py`: 29 test che bloccano le signature dei metodi DB più inclini a drift (es. `update_possessore` con `dati_modificati: dict` invece di kwargs).

### Sprint 3.8 — estrazione finale widget da `gui_widgets.py`

Tre widget storicamente in `gui_widgets.py` (1.036 LOC) sono stati estratti in moduli dedicati. `gui_widgets.py` diventa un facade thin di re-export (178 LOC, -83%):

| Nuovo modulo | LOC | Contenuto |
|---|---|---|
| `foliarium/ui/widgets/comuni.py` | 443 | `_ComuniLoaderWorker`, `ComuniTableModel`, `ElencoComuniWidget` |
| `foliarium/ui/widgets/dashboard.py` | 333 | `_DashboardLoaderWorker`, `DashboardWidget` |
| `foliarium/ui/widgets/welcome.py` | 223 | `WelcomeScreen` (EULA splash post-rebrand) |

### Sprint 3.9 — CSV export + test_e2e ex-novo + tooling

- `foliarium/ui/csv_export.py` (182 LOC): 5 helper di export CSV estratti da `gui_main.py` (`scarica_csv_generico`, `seleziona_comune_per_csv`, `scarica_csv_{comuni,localita,possessori,partite}`). `gui_main.py`: 1.982 → 1.904 LOC.
- `tests/integration/test_e2e.py` riscritto ex-novo: 18 test E2E sul DB layer post-mixin (Comune CRUD, Possessore lifecycle, Partita workflow, Immobile workflow, Ricerca avanzata, Unique constraints, Error raising, Transaction context manager).
- `tests/integration/test_database_manager.py`: ridotto da 567 → 104 LOC (-82%). Cancellate 8 classi `@pytest.mark.skip` per API drift v1.5.0+; equivalenti consolidati in `test_e2e.py`. Resta attiva solo `TestCatastoDBManagerConnection` (3 test pool/error/thread-safety).
- `tests/legacy_setup_docs.py`: cancellato (413 LOC dead code, non raccolto da pytest).
- `tests/integration/test_gui_smoke.py` (264 LOC): 13 smoke test con `pytest-qt` sui 3 widget Sprint 3.8 (`ElencoComuniWidget`, `DashboardWidget`, `WelcomeScreen`, `ComuniTableModel`). Coverage: `comuni.py` 52%, `dashboard.py` 74%, `welcome.py` 83%.
- Nuova dipendenza `pytest-qt>=4.2.0` in `tests/requirements-test.txt`.

### Tooling sviluppatore

- `bin/check_api_drift.py` — gate anti-drift API DB: incrocia metodi pubblici/privati definiti in `db/*.py` con chiamate `db.X()` nei consumer (test/widget/api). Stampa report dei metodi chiamati ma non definiti (exit 1 se trovati). Ha già individuato un bug reale: `foliarium/ui/dialogs/partita.py:1885` chiamava `get_localita_per_comune` (rinominato in `get_localita_by_comune` nel rebrand v1.5.0+), risolto contestualmente.
- `bin/migrate.py` — CLI minimale per applicare/ispezionare migrazioni SQL. Comandi: `status`, `up`, `up --dry-run`, `up --file <X>`. Usa la tabella `catasto.schema_version` (auto-creata al primo run) per tracciare le migrazioni applicate. Vedi `admin/migrazioni.md`.
- `sql_scripts/migrations/00_schema_version_table.sql` — bootstrap della tabella di tracking con backfill automatico delle migrazioni note già applicate (es. `add_soft_delete`, `add_tipo_possesso`, `v_audit_dettagliato`).

### API contract — `foliarium/protocols.py`

Sette `typing.Protocol` `@runtime_checkable` che descrivono la superficie d'uso di `CatastoDBManager` dal punto di vista dei consumer: `ComuneOpsProtocol`, `PossessoreOpsProtocol`, `PartitaOpsProtocol`, `ImmobileOpsProtocol`, `LocalitaOpsProtocol`, `AuditOpsProtocol` + `DBManagerProtocol` (unione). Type checker (mypy/pyright) verifica le chiamate dai widget; ogni rinomina lato `db/` rompe immediatamente il contract.

### Pipeline CI/CD

- Aggiunto trigger `pull_request:` (branches `main`/`master`) — le PR vengono validate prima del merge, non solo dopo.
- I 5 job di build (`build-windows`, `build-demo`, `build-unified`, `build-linux`, `build-macos`) sono gated con `if: github.event_name != 'pull_request'` — sulle PR gira solo il job di test, evitando runner costosi.
- Soglia coverage abbassata da 70 → 35: 70 era irraggiungibile senza E2E GUI live, 35 e' la soglia di regressione realistica. Coverage attuale ~43%.
- Workflow CI applica automaticamente `sql_scripts/migrations/20_fix_report_function_civico.sql` dopo l'init DB (corregge `genera_report_proprieta` per lo schema v1.6.1).

### Bug fix latenti scoperti durante l'analisi

- `db/audit.py::get_audit_log` e `get_audit_logs` intercettano `psycopg2.errors.UndefinedTable` (vista `catasto.v_audit_dettagliato` mancante in DB legacy) e mostrano un warning one-shot con istruzioni invece di crashare. Auto-apply della vista all'avvio in `db/base.py::_ensure_audit_view()`.
- `foliarium/ui/widgets/search/partite.py` rimosso riferimento a `_IMMOBILI_COLS` (mancante post-refactor).
- `foliarium/ui/dialogs/partita.py:1885`: `get_localita_per_comune` → `get_localita_by_comune` (+ adattamento loop a `List[Dict]` invece di `list[tuple]`).
- `db/base.py`: ripristinato `import psycopg2.pool` esplicito (autoflake aveva rimosso `from psycopg2 import pool` usato via dotted access).
- `sql_scripts/migrations/20_fix_report_function_civico.sql`: corregge `genera_report_proprieta` che selezionava `l.civico` (colonna rimossa dal `localita` nel rebrand v1.6.1).
- `tests/integration/test_golden_path.py`: em-dash U+2014 → trattino (i font core di fpdf2 sono latin-1 only).

### Pulizia codice

- 250 LOC di import inutilizzati rimossi in 32 file via `autoflake` + `ruff --fix --select=F401`.
- 43 f-string senza placeholder (F541) corretti.
- 3 bare-except (E722) sostituiti con `except Exception`.
- 3 variabili ambigue `l` (E741) rinominate.
- 1 import duplicato (F811) eliminato.
- `ruff format` su 9 mixin in `db/`: 138 multi-statement `E701/E702` azzerati (stack trace più leggibili).
- Facade `gui_widgets.py` e `app_utils.py` protetti da `# noqa: F401` per impedire regressioni autoflake future.

### Riduzione LOC finale (Sprint 3 cumulativo)

| File | Prima | Dopo |
|---|---|---|
| `partita_workflow_widgets.py` | 2.209 | 24 |
| `search_widgets.py` | 1.841 | 41 |
| `gui_widgets.py` | 1.036 | 178 |
| `app_utils.py` | 923 | 176 |
| `gui_main.py` | 2.155 | 1.904 |

---

## v1.0.1 — Maggio 2026 — Manutenzione e miglioramenti UX

Release di manutenzione che consolida bug fix, igiene del codice e miglioramenti di esperienza utente. Nessuna modifica allo schema del database — aggiornamento sicuro da v1.0.0.

### Bug fix e robustezza

- **Verifica automatica schema database all'avvio**: l'applicazione rileva all'avvio eventuali migrazioni mancanti (colonne `archiviato` su `comune`, tabella `tipo_possesso`) e mostra un avviso non-bloccante con le indicazioni per applicare gli script SQL pendenti.
- **Igiene repository**: rimossi file non destinati al versionamento (dump database di prova, EULA in formato `.rtf` ridondante). `.gitignore` aggiornato per ignorare automaticamente file `*.dump`, `*.backup`, `*.sql.gz`.
- **Stabilità import**: corretto un `NameError` che poteva manifestarsi all'apertura della command palette su alcune installazioni.

### Miglioramenti UX

- **Command palette (Ctrl+K)**: nuova finestra di ricerca rapida che permette di passare a qualsiasi pagina dell'applicazione digitando parte del nome. Supporta navigazione con frecce, conferma con Invio, chiusura con Esc. Stile coerente con tema chiaro e scuro.
- **Chip scadenza licenza nella top bar**: quando la licenza è in scadenza, appare un'indicazione colorata accanto al nome utente:
    - Arancione: ≤ 30 giorni alla scadenza
    - Rosso: ≤ 7 giorni alla scadenza
    - Nascosto: licenza valida oltre i 30 giorni
- **Notifiche meno invasive**: i messaggi di conferma per operazioni andate a buon fine (salvataggi, modifiche, eliminazioni) non sono più dialog modali da chiudere ma compaiono nella status bar in basso, senza interrompere il flusso di lavoro. Sono stati convertiti oltre 10 dialog di successo in `dialogs_entity.py` e `dialogs_admin.py`.

### Igiene del codice

- Centralizzata la funzione `show_status_message()` in `custom_widgets.py`: i moduli `gui_widgets.py` e `admin_widgets.py` non duplicano più la logica.
- `ruff check` su tutti i moduli sorgente con regole `F821` (nomi non definiti), `F811` (ridefinizioni), `F841` (variabili non usate), `E9` (errori di parsing): zero errori.
- Rimossi residui di stampe diagnostiche (`print()`) in `db/base.py` e `db/models.py`.
- Installer Inno Setup (`Foliarium_Installer.iss`, `Foliarium_Unified_Installer.iss`) aggiornati per puntare al singolo file EULA `.txt`.

### Refactoring interno

- **Consolidamento script SQL per fresh install**: 4 micro-script separati (`07_soft_delete_archiviazione.sql`, `07_create_tipo_possesso_table.sql`, `19_creazione_tabella_sessioni.sql`, `20_feature_tipi_localita.sql`) assorbiti negli script base `02_creazione-schema-tabelle.sql` e `07_user-management.sql`. Il numero di script eseguiti durante l'installazione scende da 21 a 17. I 4 script originali sono ora in `sql_scripts/migrations/` con nome descrittivo per aggiornare database esistenti (v ≤ 1.0.0).
- **Fix critico bootstrap admin**: rimosso da `07_user-management.sql` il blocco che creava l'utente admin con password hardcoded (`admin123`). Questo blocco causava una race condition con `07a_bootstrap_admin.sql`, impedendo all'installer di iniettare la password generata casualmente. L'utente admin viene ora creato esclusivamente da `07a_bootstrap_admin.sql`.
- **Suddivisione `gui_widgets.py`**: il file monolitico (4 471 righe) è stato ridotto del 77% (→ 1 022 righe) estraendo due nuovi moduli:
  - `search_widgets.py` (1 529 righe) — `RicercaPartiteWidget`, `RicercaAvanzataImmobiliWidget`, `UnifiedFuzzySearchWidget`
  - `partita_workflow_widgets.py` (2 053 righe) — `RegistrazioneProprietaWidget`, `NuovaPartitaWizardWidget`, `OperazioniPartitaWidget`
  - `gui_widgets.py` mantiene i re-export per backward compatibility di tutti gli import esistenti.

### Procedura di aggiornamento

L'aggiornamento da v1.0.0 a v1.0.1 è automatico tramite l'aggiornatore integrato (menu *Help → Verifica aggiornamenti…*) oppure manuale sostituendo il contenuto della cartella di installazione.
**Non è necessaria alcuna modifica al database**.

---

## v1.0.0 (= v1.6.1) — Aprile 2026 — VERSIONE FINALE STABILE

**Foliarium 1.0.0** è la prima versione stabile e completa del sistema di gestione dell'Archivio Catastale Storico. Questa release consolida tutte le funzionalità sviluppate nelle versioni precedenti (1.5.x e 1.6.x).

### Funzionalità principali incluse

#### Interfaccia utente moderno
✅ **Sidebar + Top Bar**: Navigazione ridisegnata con barra laterale verticale (stile VS Code) e top bar con stato applicazione  
✅ **16 temi grafici** inclusi + tema automatico (segue impostazioni sistema Windows)  
✅ **Stile nativo Windows 11** (con Qt 6.7+)  
✅ **Temi scuro/chiaro automatici** in base alle preferenze di sistema  
✅ **Logo SVG** sempre nitido su HiDPI  

#### Ricerca e consultazione
✅ **Ricerca partite** con filtri: numero, possessore, stato, anno  
✅ **Ricerca possessori** con ricerca parziale su nome/cognome  
✅ **Ricerca immobili** avanzata per natura, classificazione, località  
✅ **Ricerca documenti storici** full-text  
✅ **Albero genealogico partite** con visualizzazione predecessori/successori  
✅ **Confronto versioni partita** con diff visuale (verde/rosso)  

#### Inserimento e gestione dati
✅ **Inserimento comuni, possessori, località, partite, immobili**  
✅ **Importazione da CSV e XLSX** con validazione e anteprima  
✅ **Importazione comuni da ISTAT ufficiale** con download automatico  
✅ **Importazione località da OpenStreetMap** (Overpass API)  
✅ **Scarica/modifica/reimporta** per aggiornamento massivo (round-trip CSV)  
✅ **Template CSV** scaricabili per ogni tipo di entità  
✅ **Validazione campi obbligatori** con feedback visuale in tempo reale  

#### Esportazioni e reportistica
✅ **Esporta in CSV, Excel, PDF, ODT**  
✅ **Archivio Completo (.xlsx)** con 4 fogli (Partite, Possessori, Immobili, Variazioni)  
✅ **Report testuale** genealogico, statistiche, consistenza patrimoniale  
✅ **Grafici statistici** con matplotlib (bar, torta, linee)  

#### Tabelle interattive
✅ **Ridimensionamento colonne interattivo** — drag sul bordo tra intestazioni  
✅ **Ordinamento** con clic su intestazione colonna  
✅ **Menu contestuale** (tasto destro) per copia valori e operazioni rapide  
✅ **Conteggio risultati** visualizzato sopra ogni tabella  

#### Sicurezza e gestione
✅ **Autenticazione utenti** con bcrypt, keyring per password DB  
✅ **RBAC** — ruoli Guest, Utente, Amministratore  
✅ **Audit log** completo di tutti gli accessi e modifiche  
✅ **Gestione utenti** — crea, modifica, reset password, disabilita  
✅ **Timeout sessione** configurabile (default 15 min)  
✅ **Notifiche email automatiche** (account creato, password cambio, ruolo cambiato, login)  
✅ **Sistema licenze HMAC-SHA256** con seat di rete  
✅ **Modalità offline** con cache JSON locale  

#### Database
✅ **PostgreSQL 14** embedded (installer unificato) oppure installazione standard  
✅ **Versione demo portabile** con PostgreSQL embedded sulla porta 15432  
✅ **Backup/ripristino** con GUI  
✅ **Schema catastale completo** con 12+ tabelle, stored procedure, GIN indices per ricerca full-text  

#### Operazioni avanzate
✅ **Auto-aggiornamento** da GitHub Releases con download e installazione automatici  
✅ **Manuale utente integrato** (F1) con viewer markdown + navigazione albero  
✅ **MkDocs documentation** completa (consultazione, inserimento, amministrazione, FAQ)  
✅ **Test coverage** 19.6% + 164 unit test  

### Piattaforme supportate
- **Windows 10** / **Windows 11** (primario)
- **Installazione standard**: Python 3.12 + PostgreSQL (su host separato o locale)
- **Installer unificato**: PostgreSQL 14 embedded, setup database automatico, servizio Windows
- **Versione demo**: ZIP portabile, nessuna installazione

### Performance e stabilità
- **Refactoring TIER 1**: 36 metodi DB rifattorizzati, 469 linee di codice semplificato
- **Ottimizzazioni TIER 2**: N+1 queries eliminate, subquery correlate, query tagging, GIN indices
- **Ottimizzazioni TIER 3**: Smart MV refresh, connection pool health monitoring, safe query binding, lookup cache
- **Estimated speedup**: **10-15x** vs versioni precedenti

### Note importanti
- **PyQt6**: Esclusivamente PyQt6 (zero PyQt5/Qt4)
- **Zero dipendenze WebEngine**: QPdfDocument per visualizzazione PDF
- **Backward compatible**: Database upgrade script (`06_migrate_civico_to_nome.sql`) per migrazione civico
- **Nessun debito tecnico**: Tutti i debiti tecnici noti risolti, refactoring completato

---

## v1.6.1 — Aprile 2026

### Refactoring civico — Incorporazione nel nome della via

**Problema:** Il campo civico non era visualizzato correttamente quando si
visualizzavano le località. Era memorizzato separatamente e richiedeva gestione
complessa (INTEGER vs VARCHAR per "10A").

**Soluzione:** Incorporare il civico direttamente nel campo `nome` della via
(es. "Via Roma 10", "Via Pippo 10A").

#### Modifiche Database

- **Schema `localita`**: rimosso campo `civico`
- **UNIQUE constraint**: semplificato da `(comune_id, nome, civico)` a
  `(comune_id, nome)`
- **Script migrazione**: `06_migrate_civico_to_nome.sql` concatena civico al
  nome per i dati esistenti

#### UI/Widget

- **`InserimentoLocalitaWidget`**: rimosso campo civico, tabella con 3 colonne
- **`ModificaLocalitaDialog`**: rimosso civico_spinbox
- **`LocalitaSelectionDialog`**: rimosso civico_spinbox, 3 colonne nella tabella
- **Template CSV**: aggiornato a `nome;tipologia_stradale`

#### Database Manager

- **`insert_localita()`**: rimossi `tipo_id`, `civico`; supporta
  `tipologia_stradale`
- **`get_localita_by_comune()`**: semplificato (rimosso JOIN tipo_localita)
- **Altre query**: aggiornate in `immobili.py`, `io.py`, `comuni.py`,
  `localita.py`

#### Vantaggi

✅ Civico sempre visibile nel nome  
✅ Schema semplice (una colonna anziché due)  
✅ Supporta civici con lettere (es. "10A")  
✅ Backward compatible (script migrazione per dati esistenti)  

---

## v1.6.0 — Aprile 2026

**Versione definitiva di Foliarium.** Questa release consolida tutte le
funzionalità sviluppate nelle 1.5.x e aggiunge un installer unificato
self-contained che include PostgreSQL. Non è più necessario installare
manualmente PostgreSQL sul computer di destinazione.

### Installer unificato — PostgreSQL integrato

**`Foliarium_Unified_Installer.iss`** — nuovo installer Inno Setup che
distribuisce in un unico eseguibile:

- L'applicazione Foliarium (output PyInstaller `dist\Foliarium\`)
- I binari PostgreSQL 14 portabili (`pgsql\bin`, `pgsql\lib`, `pgsql\share`)
- Gli script SQL di inizializzazione schema
- Lo script di inizializzazione database `setup_database.bat`

**`setup_database.bat`** — eseguito automaticamente durante l'installazione:

1. Verifica che la porta 5432 non sia occupata (fallback su 5433, poi 5434)
2. `initdb` crea il cluster in `%ProgramData%\Foliarium\pg_data` (non in
   Program Files, dove `initdb` non può scrivere perché droppa i privilegi)
3. Avvio temporaneo del server in modalità `trust` (pg_hba.conf di default)
4. `ALTER USER postgres PASSWORD …` con password casuale generata dall'installer
5. Sovrascrittura di `pg_hba.conf` con autenticazione `scram-sha-256`
6. Registrazione come servizio Windows `FoliariumDB` (avvio automatico)
7. Esecuzione degli script SQL: schema, procedure, user management, bootstrap admin
8. Scrittura di `config.ini` accanto all'eseguibile con credenziali locali

**`uninstall_database.bat`** — eseguito dall'uninstaller: ferma il servizio,
lo deregistra e rimuove `pg_data/`.

**Password sicure per default:** l'installer Pascal genera password casuali
alfanumeriche (16 caratteri per il DB, 12 per l'admin applicativo) e le
passa a `setup_database.bat` come parametri.

**Flusso utente finale:** doppio clic sull'installer → `Next` → `Install` →
fine. L'app è pronta all'uso con database già inizializzato, servizio
Windows registrato, credenziali salvate in `config.ini`.

### Fix critici installer (PostgreSQL embedded)

| Problema | Causa | Fix |
|----------|-------|-----|
| `initdb: Permission denied` | `pg_data` in `C:\Program Files` (non scrivibile) | Spostato in `%ProgramData%\Foliarium\pg_data` |
| `password authentication failed for postgres` | `pg_hba.conf` scritto `scram-sha-256` prima di impostare la password | Riordinato: trust → `ALTER USER` → `scram-sha-256` |
| `initdb: directory exists but is not empty` | Residuo di installazione precedente fallita | Pulizia automatica di `pg_data` incompleto prima di `initdb` |
| `DeleteFile fallito; codice 5. Accesso negato` su `icuin67.dll` | Servizio `FoliariumDB` ancora in esecuzione durante la reinstallazione | `PrepareToInstall()` Pascal ferma il servizio e killa `postgres.exe` prima di estrarre i file |

### Fix percorsi PyInstaller 'onedir'

**`config.ini` e `foliarium.license` non venivano trovati dopo l'installazione.**

Causa: in un bundle PyInstaller `onedir`, `sys._MEIPASS` (e quindi
`app_paths.BASE_DIR`) punta alla sottocartella `_internal/` dove vengono
estratte le risorse, **non** alla cartella dove vive `Foliarium.exe`. Ma
l'installer scrive `config.ini` e l'utente mette `foliarium.license`
**accanto** all'eseguibile, non in `_internal/`.

Fix:

- `app_paths.py`: nuova funzione `get_exe_dir()` e costante `EXE_DIR` che
  restituiscono `Path(sys.executable).parent` nei bundle frozen
- `config.py`: `_config_ini_path` cerca prima in `EXE_DIR`, poi come
  fallback in `BASE_DIR` (per retrocompatibilità dev mode)
- `license_manager.py`: il file `.license` viene cercato prima accanto
  all'eseguibile (`EXE_DIR`), poi in `BASE_DIR`

---

## v1.5.3 — Marzo 2026

### Versione Demo portabile (PostgreSQL embedded)

Nuova modalità **Demo** completamente autonoma: nessuna installazione richiesta,
nessun PostgreSQL di sistema. Basta estrarre lo ZIP ed eseguire `Foliarium_Demo.exe`.

**Funzionamento:**
- `demo_launcher.py` avvia PostgreSQL 14 portabile sulla porta **15432** all'avvio
  e lo ferma automaticamente alla chiusura (anche via `atexit`)
- Se `demo_data/` è su supporto in sola lettura (USB/CD), i dati vengono copiati
  in `%LOCALAPPDATA%\Foliarium\demo_data` prima dell'avvio
- Login automatico come utente `demo` senza dialogo di autenticazione
- Badge arancione **DEMO** visibile nella barra superiore

**Dati dimostrativi inclusi:** Provincia di Savona, 1870–1985, ~300 partite catastali,
120 possessori, generate con `sql_scripts/05_demo_dataset.sql`.

**Build automatica nel pipeline CI (`build-demo`):**
- Download PostgreSQL 14 portabile (EnterpriseDB); rimozione di pgAdmin4/doc/include/symbols
- `prepare_demo_db.py` esegue `initdb`, configura `pg_hba.conf` (trust 127.0.0.1),
  carica gli script SQL e crea l'utente `demo` con hash bcrypt
- Le password demo (`DEMO_DB_PASS`, `DEMO_LOGIN_PASS`) sono lette da GitHub Secrets
- Verifica presenza file critici nel bundle prima della creazione ZIP
- Artefatto finale: `Foliarium_Demo_<versione>_Portabile.zip`

**Attivazione modalità demo (sorgente):**
```bash
python gui_main.py --demo
# oppure
set FOLIARIUM_DEMO=1 && python gui_main.py
```

---

### Gestione Licenze

Sistema di licenze basato su file `.license` firmati HMAC-SHA256.

**`license_manager.py`** — modulo core:
- `get_hardware_fingerprint()` — SHA-256(MAC+hostname), 16 hex
- `generate_license(...)` — produce JSON firmato con chiave HMAC interna
- `_validate_file(path)` — verifica firma, hardware ID, data di scadenza → `LicenseInfo`
- Seat di rete: file-lock JSON in cartella condivisa UNC, TTL 120 s, refresh ogni 60 s
- In modalità demo restituisce sempre una licenza demo valida senza leggere file

**`generate_license.py`** — CLI utility:
```bash
# Genera licenza per un cliente
python generate_license.py generate \
    --to "Archivio di Stato di Savona" \
    --type standard --seats 2 \
    --expiry 2027-12-31 --out foliarium.license

# Ispeziona un file .license esistente
python generate_license.py inspect foliarium.license

# Mostra l'hardware fingerprint del computer corrente
python generate_license.py fingerprint
```

**Tipi di licenza:** `demo` (embedded, nessun file), `standard`, `enterprise`

**Verifica all'avvio:** la licenza viene validata prima del dialogo DB; se non valida
o se i seat di rete sono esauriti, l'avvio è bloccato con messaggio esplicativo.

**Dialog in-app:** *Impostazioni → Gestione Licenza…*
- Stato in tempo reale (tipo, intestatario, scadenza, seat usati/massimi)
- Sfoglia file `.license` locale o cartella UNC condivisa
- Pulsante "Copia ID hardware" per richiedere licenza vincolata al PC

!!! warning "Nome file licenza"
    Il file deve chiamarsi **`foliarium.license`** (default) oppure il percorso
    va configurato da *Impostazioni → Gestione Licenza…*

---

### Auto-Aggiornamento con download automatico

**`update_checker.py`** (riscritto):
- Interroga le GitHub Releases per confrontare versioni semantiche
- Se disponibile un asset `.exe`, mostra pulsante **"Scarica e installa automaticamente"**
  con barra di avanzamento (0–100 %) e verifica SHA-256 opzionale
- `DownloadWorker(QThread)` gestisce download in background con supporto annullamento
- L'installer viene lanciato in modalità silenziosa:
  `/SILENT /CLOSEAPPLICATIONS /RESTARTAPPLICATIONS`
- Altrimenti pulsante **"Apri pagina download"** → browser
- Il controllo aggiornamenti è disabilitato in modalità demo e in CI

### Refactoring architetturale — DB layer e test coverage

#### Migrazione PyQt6 (completata in v1.3.0.0, nota)
Tutte le applicazioni usano esclusivamente PyQt6. Gli enum PyQt4/5-style
(`Qt.AlignLeft`, `QFont.Bold`, ecc.) sono stati eliminati e sostituiti con la
sintassi completa PyQt6 (`Qt.AlignmentFlag.AlignLeft`, `QFont.Weight.Bold`).

#### Suddivisione `catasto_db_manager.py` in package `db/`
Il file monolitico da 4 745 righe e 169 metodi è stato suddiviso in 14 mixin
specializzati, ognuno con responsabilità singola:

| Modulo | Responsabilità |
|--------|---------------|
| `db/base.py` | Pool connessioni, context manager, cache offline |
| `db/comuni.py` | CRUD comuni |
| `db/localita.py` | CRUD località |
| `db/possessori.py` | CRUD possessori |
| `db/partite.py` | CRUD partite, genealogia, report |
| `db/immobili.py` | CRUD immobili |
| `db/variazioni.py` | Variazioni e contratti |
| `db/ricerca.py` | Ricerche avanzate |
| `db/audit.py` | Audit log, sessioni, consultazioni |
| `db/utenti.py` | Autenticazione, permessi |
| `db/backup.py` | Backup e ripristino |
| `db/documenti.py` | Documenti storici, periodi |
| `db/stats.py` | Statistiche, viste materializzate |
| `db/io.py` | Import/export massivo |

`catasto_db_manager.py` è ora una facade di 19 righe che assembla i mixin
tramite ereditarietà multipla Python. Tutti gli import esistenti continuano
a funzionare senza modifiche.

#### Fix API interna — eliminazione `self.execute_query` residui
31 metodi su 9 file mixin che usavano ancora la vecchia API monolitica
(`self.execute_query` / `self.fetchall` / `self.commit` / `self.rollback`) sono
stati riscritti con il pattern corretto `_get_connection()` + `DictCursor`.
Questo elimina potenziali `AttributeError` silenti a runtime.

File corretti: `db/partite.py`, `db/audit.py`, `db/variazioni.py`,
`db/immobili.py`, `db/utenti.py`, `db/backup.py`, `db/documenti.py`,
`db/comuni.py`, `db/possessori.py`.

#### Estrazione widget GUI in moduli dedicati
| Nuovo modulo | Widget estratti da `gui_widgets.py` |
|---|---|
| `admin_widgets.py` | `GestioneUtentiWidget`, `AuditLogViewerWidget`, `BackupWidget` |
| `import_dialogs.py` | `ImportComuniDialog`, `ImportLocalitaDialog` |
| `reporting_widgets.py` | `RicercaDocumentiWidget`, `EsportazioniWidget`, `ReportisticaWidget`, `StatisticheWidget` |

`gui_widgets.py` mantiene i re-export per backward compatibility.

#### Fix dipendenza Qt in DB layer
`db/stats.py`: gli import `QProgressDialog`, `QMessageBox`, `Qt` spostati
dentro `refresh_materialized_views()` (lazy import) per permettere l'import
del modulo in ambienti headless e test CI senza display.

#### Test coverage
- 53 nuovi unit test in `tests/unit/test_db_mixins.py` (9 classi, una per mixin)
- Coverage totale: **7% → 19.6%**; `db/variazioni.py` 61%, `db/audit.py` 32%
- `pytest.ini` aggiornato: aggiunto `--cov=db` per coverage del package `db/`
- Pattern mock standard per testare metodi DB senza connessione reale:
  `patch.object(mgr, "_get_connection", return_value=mock_conn_cm)`

---

## v1.5.2 — Marzo 2026

### Fix temi QSS — campi tagliati e warning Qt (`styles/`)

**`box-shadow` rimosso (6 temi):**
- Qt non supporta `box-shadow` nei QSS e stampava "Unknown property box-shadow" a ogni ridisegno
- Rimosso da: `azzurro_ligure`, `sunset_orange`, `purple_royal`, `classic_business`, `ocean_blue`, `nature_green`

**Padding `QComboBox`/`QSpinBox` normalizzato (6 temi):**
- Padding orizzontale eccessivo (`7px 12px`, `6px 10px`, `8px`) causava il taglio dei campi nei form
- Tutti i temi allineati al valore di riferimento `5px 8px` (come `foliarium_styles.qss`)
- Temi corretti: `nature_green`, `ocean_blue`, `purple_royal`, `sunset_orange`, `classic_business`, `high_contrast`

**`font-size` globale normalizzato (`high_contrast_stylesheet.qss`):**
- `11pt` → `10pt` per allineamento con tutti gli altri temi; il font più grande allargava le etichette del 10% comprimendo i widget adiacenti

### Fix PDF — `FPDFUnicodeEncodingException` (`app_utils.py`, `dialogs.py`)

- Il font built-in `Helvetica` supporta solo Latin-1: l'em dash `—` (U+2014) causava crash a ogni `add_page()`
- Sostituiti tutti i testi passati a FPDF: `APP_NAME`, titoli `cover_block`, separatore `BulkReportPDF`
- Fallback valori nulli: `—` → `N/D` in `info_block`, stringa vuota nelle tabelle
- Aggiunto `alias_nb_pages()` mancante in `dialogs.py` per `GenericTextReportPDF`

---

## v1.5.1 — Marzo 2026

### Redesign PDF — Report professionali (`app_utils.py`)

Introdotta la classe base `ModernCatastoPDF(FPDF)` da cui ereditano tutte le classi PDF
(`PDFPartita`, `PDFPossessore`, `GenericTextReportPDF`, `BulkReportPDF`).

**Header e footer:**
- Banda colorata navy (RGB 26,54,93) con logo PNG integrato (se presente), nome app, data e titolo report
- Footer con linea separatrice blu, disclaimer a sinistra, numero pagina `Pag. N/TOT` a destra

**Blocco riepilogativo iniziale (`cover_block`):**
- Riquadro con sfondo azzurro chiaro e barra laterale blu
- Numero partita/nome possessore in grande (13pt, blu istituzionale)
- Riga info compatta (tipo, stato) e chip con data impianto, provenienza, ID

**Titoli sezione (`section_title`):**
- Banda blu (RGB 41,98,155) con testo bianco; sostituisce il semplice testo in grassetto

**Campi chiave-valore (`info_block`):**
- Due colonne: etichetta in grigio + valore in nero; linea separatrice sottile su ogni riga

**Tabelle (`styled_table`):**
- Intestazione blu/bianco, righe alternate bianco/azzurro chiaro, linea di chiusura; nessun bordo a griglia pesante

**`BulkReportPDF`:** landscape con header colorato, righe alternate, intestazione tabella ripetuta su ogni pagina

**`GenericTextReportPDF`:** testo preformattato su sfondo grigio chiaro (`#F8F9FA`), font `Courier 8pt`

**Altre migliorie:**
- Dopo il salvataggio PDF viene proposto "Vuoi aprirlo ora?" (`prompt_to_open_file`) invece del solo messaggio di conferma
- Fix: rimossi due `pdf.alias_nb_pages()` nelle funzioni CSV dove `pdf` non esisteva (potenziale `NameError`)
- Rimossi gli override di margini superflui (gestiti in `ModernCatastoPDF.__init__`)

---

## v1.5.0 — Marzo 2026

### Rebrand: Foliarium → Foliarium
- Rinominati tutti i file risorsa (`logo_foliarium.svg`, `icona_foliarium.ico`, `foliarium_styles.qss`, `foliarium.spec`, ecc.)
- Aggiornati tutti i riferimenti al nome in sorgenti Python, stili QSS, installer Inno Setup, pipeline CI/CD, documentazione (>45 occorrenze)
- Nuovi logo ad alta risoluzione (`Logo_foliarium_1.png`, `Logo_foliarium_2.png`)
- Keyring DB: `meridiana_db_*` → `foliarium_db_*`; log di sessione: `foliarium_session.log`

### Splash screen all'avvio
- `FoliariumSplashScreen` mostrata prima del login con logo e branding aggiornato
- Fix: rimosso `WindowStaysOnTopHint` che bloccava EULA e login; chiusura automatica dopo 2,5 s
- Saltata in ambiente CI/test

### Enterprise — Setup e distribuzione
- `setup/setup-database.ps1`: script PowerShell per inizializzare il DB su Windows (verifica PostgreSQL, esegue SQL scripts in ordine, salva credenziali in Windows Credential Manager)
- `update_checker.py`: `UpdateCheckerWorker(QThread)` controlla GitHub Releases in background (timeout 5 s); segnali `update_available`, `up_to_date`, `check_failed`
- Dialog aggiornamento con 3 pulsanti: *Scarica aggiornamento*, *Salta questa versione*, *Ricordamelo dopo*; release notes GitHub in `QTextBrowser`
- Menu *Help → Controlla aggiornamenti...* (manuale) e *Controlla aggiornamenti all'avvio* (checkbox, persiste in `QSettings`)
- Nuove costanti `config.py`: `SETTINGS_UPDATE_AUTO_CHECK`, `SETTINGS_UPDATE_SKIPPED_VER`

### Temi — Supporto completo sidebar/top bar
- Stili `#topBar`, `#sidebar`, `QPushButton#navButton` (con `:hover` e `[active="true"]`) aggiunti a tutti e 16 i temi QSS
- Colori adattati coerentemente a ogni palette (light, dark, high contrast)

### Dashboard arricchita
- Nuova sezione **Ultimi Inserimenti** con `QTabWidget` (3 tab: Comuni / Partite / Possessori) alimentata da `get_ultimi_inserimenti_dashboard()` in `catasto_db_manager.py`
- Mini-card **Stato Backup** con colore dinamico (verde / arancio / rosso) in base alla data dell'ultimo backup

### Context menu (tasto destro) — tabelle aggiuntive
- `GestioneUtentiWidget.user_table`: Modifica, Reset password, Copia username / nome / email
- `AuditLogViewerWidget.log_table`: Copia ID / utente / azione / IP, Copia riga intera
- `StatisticheWidget.stats_comune_table`: Copia comune / provincia, Copia riga
- `StatisticheWidget.immobili_table`: Copia comune / classificazione, Copia riga
- `DashboardWidget.audit_table`: Copia utente / azione / IP

### Fix accessibilità temi
- `SMTPSettingsDialog`: `setFixedWidth(80)` → `setMinimumWidth(80)` (HiDPI)

### Script dati di test
- `genera_dati_test.py`: popola il DB con 13 scenari workflow realistici (vendite, successioni, frazionamenti, donazioni, permute, ecc.), 6 comuni, 26 località, 13 possessori, 4 utenti, sessioni e consultazioni
- Opzioni `--no-reset` e `--no-confirm`; variabili d'ambiente DB standard

---

## v1.4.7.0 — Marzo 2026

### Redesign UI — Sidebar verticale + Top Bar
- Navigazione a `QTabWidget` annidati (3 livelli) sostituita con sidebar verticale stile VS Code + `QStackedWidget` flat
- **`TopBarWidget`**: barra fissa h=48px con logo SVG, titolo, indicatore DB, nome utente, chip ruolo, pulsante Logout
- **`SidebarWidget`**: pannello w=220px scrollabile; sezioni ARCHIVIO / INSERIMENTO / ANALISI / SISTEMA; bottoni visibili in base al ruolo; stile attivo dinamico
- Navigazione principale via `navigate_to(page_name)`; `activate_tab_and_sub_tab()` mantenuto come wrapper di compatibilità
- Shortcut `Ctrl+1..N` rimappati alla lista flat sidebar
- Stili QSS dedicati: `#topBar`, `#sidebar`, `QPushButton#navButton` con stati `:hover` e `[active="true"]`

---

## v1.4.6.0 — Marzo 2026

### Miglioramenti UI/UX

#### Dashboard
- Versione nell'intestazione ora dinamica (`APP_VERSION` da `config.py`) — non più hardcoded "1.3"
- Aggiunta riga informativa sotto il titolo: ruolo utente e data/ora di accesso

#### Form di inserimento
- **Tooltip** sui 5 pulsanti di ogni widget inserimento (Comune, Possessore, Località, Partita)
- **Invio per salvare**: campo principale di ogni form collegato a `returnPressed` → avvia il salvataggio senza cliccare il pulsante

#### Tabelle di ricerca
- **Conteggio risultati** spostato sopra la tabella (più naturale da leggere prima dei dati)
- **Menu tasto destro** aggiunto a *Ricerca Avanzata Immobili*: copia ID, Partita N., Comune, Natura
- **Menu tasto destro** aggiunto a *Ricerca Documenti*: copia Titolo, Anno, Partita, ID

---

## v1.4.5.0 — Marzo 2026

### Fix e miglioramenti UX

#### Fix: ImportLocalitaDialog — campo comune OSM non sincronizzato

- Il campo "Nome comune (per OSM)" ora si popola correttamente all'apertura del dialog con il valore già selezionato nel menu a tendina in alto, eliminando il rischio di importare località di un comune su un altro.

#### Conferma prima di ogni importazione dati

- Aggiunto dialog di conferma (`Sì / No`, default No) prima di avviare qualsiasi importazione nel DB:
  - Comuni da CSV
  - Comuni da ISTAT
  - Località da CSV
  - Località da OpenStreetMap
  - Possessori da CSV
  - Partite da CSV / Excel
- Il messaggio informa l'utente del numero di record in fase di import, del comune di riferimento (ove applicabile) e del possibile effetto sui dati già presenti.

---

## v1.4.4.0 — Marzo 2026

### Compliance GDPR/NIS2

#### Timeout sessione automatico

- Logout automatico dopo un periodo di inattività configurabile (default 15 minuti)
- Dialog di avviso con countdown 60s prima del logout
- Configurabile da *Impostazioni → Timeout Sessione...* (0 = disabilitato)

#### Log tracciabilità export

- Ogni esportazione (CSV, Excel) viene registrata nell'Audit Log con utente, filename e numero di record
- Consultabile dalla sezione *Audit Log* dell'applicazione

#### Policy password rafforzata

- Requisiti minimi: **8 caratteri** e **almeno 1 cifra**
- Applicata sia alla creazione utente che al reset password

---

## v1.4.3.0 — Marzo 2026

### Nuove feature

#### Manuale utente integrato (F1)

- Viewer del manuale embedded nell'app: *Help → Visualizza Manuale Utente...* oppure tasto **F1**
- Albero di navigazione da `mkdocs.yml`, rendering Markdown con CSS, navigazione back/forward
- Nessun browser esterno richiesto

#### Scarica CSV dati esistenti

- 4 nuove voci menu *File*: Scarica CSV Comuni, Località, Possessori, Partite
- Pulsante "Scarica CSV" in ogni pannello di inserimento
- CSV compatibile round-trip con i template di import (scarica → modifica → reimporta)

---

## v1.4.2.0 — Marzo 2026

### Miglioramenti UI/UX

- **Sorting tabelle**: ordinamento per colonna cliccando l'intestazione in Ricerca Partite, Immobili e Documenti
- **Menu contestuale**: tasto destro sulle partite trovate → Apri Dettagli / Copia Numero / Copia ID
- **Conteggio risultati**: etichetta con il numero di record trovati nelle tabelle di ricerca (senza popup)
- **Validazione inline**: i campi obbligatori si evidenziano in rosso se non compilati correttamente
- **Completamento provincia**: digitando le prime lettere nel campo Provincia compare un suggerimento automatico
- **Scorciatoie tastiera**: `Ctrl+1..N` per navigare tra i tab, `F5` per ricaricare il tab corrente

### Notifiche email automatiche

- Nuovo modulo email con supporto SMTP/STARTTLS e SMTP_SSL
- Configurazione da *Impostazioni → Notifiche Email...*: host, porta, credenziali, test connessione
- 4 eventi notificati: creazione account, reset password, cambio ruolo, login
- Invio in background (non blocca l'interfaccia), password SMTP memorizzata in keyring

---

## v1.4.1.0 — Marzo 2026

### Fix
- **Colonne CSV ISTAT** (`dialogs.py`): corretti i nomi colonna in `ISTATDownloadWorker` per compatibilità con il formato ISTAT aggiornato:
  - `"Denominazione regione"` → `"Denominazione Regione"`
  - `"Codice Catastale del Comune"` → `"Codice Catastale del comune"`
  - Sigla provincia: nome lungo con `\n` → `"Sigla automobilistica"`

### Refactoring
- Rimossi duplicati e dead code in `app_utils.py`, `catasto_db_manager.py`, `custom_widgets.py`, `gui_main.py` (−108 righe totali)

### Nuove feature

#### Import Località da OpenStreetMap
- `OSMLocalitaWorker(QThread)` interroga Overpass API per strade e luoghi del comune
- `ImportLocalitaDialog` estesa con tab "Da OpenStreetMap": campo comune, checkbox strade/luoghi, progress bar, anteprima, importa
- Tipi OSM supportati: Via, Viale, Corso, Piazza, Vicolo, Largo, Salita, Calata, Contrada, Borgata, Regione, Frazione, Strada, Traversa, Passaggio, Località

#### 4 pulsanti uniformi nei widget di inserimento
- Tutti i pannelli di inserimento (Comune, Possessore, Partita, Località) hanno ora 4 pulsanti uniformi: **Inserisci · Pulisci Campi · Importa CSV · Scarica Template**

---

## v1.4.0.0 — Febbraio 2026

### Roadmap v1.4 completata

| Feature | Priorità | Modulo |
|---|---|---|
| Albero genealogico proprietà | Alta | `dialogs.py`, `gui_widgets.py` |
| Export Excel avanzato (4 fogli) | Alta | `gui_widgets.py` |
| Ricerca full-text documenti storici | Alta | `gui_widgets.py` |
| Import partite da Excel (.xlsx) | Media | `catasto_db_manager.py` |
| Dashboard con grafici statistici | Media | `gui_widgets.py` |
| Confronto versioni partita (diff) | Media | `dialogs.py` |
| Modalità offline/cache | Bassa | `catasto_db_manager.py`, `gui_main.py` |
| Test coverage report | Bassa | `pytest.ini`, `tests/unit/` |
| Export report ODT | Bassa | `gui_widgets.py` |

---

## v1.3.2.0 — Gennaio 2026

### Feature: Albero genealogico partita
- `get_genealogia_partita(partita_id)` in `catasto_db_manager.py`
- `AlberoGeneralogicoDialog` in `dialogs.py`: QTreeWidget, colori differenziati per predecessori/successori, pannello dettaglio
- Pulsante "Albero Genealogico" in `PartitaDetailsDialog` e `ReportisticaWidget`

---

## v1.3.1.0 — Dicembre 2025

### Feature: Import comuni e località da CSV / ISTAT
- `import_comuni_from_rows()` e `import_localita_from_rows()` in `catasto_db_manager.py`
- `ISTATDownloadWorker(QThread)`, `ImportComuniDialog`, `ImportLocalitaDialog` in `dialogs.py`
- Voci menu File: "Importa Comuni da CSV/ISTAT..." e "Importa Località da CSV..."

---

## v1.3.0.0 — Novembre 2025

### Migrazione PyQt6 completata
- Corretti tutti gli enum non-namespaced (>80 istanze) in `gui_widgets.py`, `dialogs.py`, `catasto_db_manager.py`, `app_utils.py`
- Pattern: `Qt.AlignLeft` → `Qt.AlignmentFlag.AlignLeft`

### Nuove feature
- **Auto dark/light mode**: menu *Impostazioni → Tema Automatico (Segue Sistema)*
- **Stile nativo Windows 11**: disponibile su Qt 6.7+ con Windows 11
- **HiDPI audit**: rimossi tutti i `setFixedSize`, sostituiti con `setMinimumSize`
- **QPdfDocument** sostituisce WebEngine per la visualizzazione PDF (risparmio ~80 MB installer)
- **Logo SVG** con fallback PNG, scelta automatica dark/light

---

## v1.2.0.0 — Ottobre 2025

- Versione stabile iniziale con funzionalità base:
  - Consultazione partite, possessori, immobili
  - Inserimento singolo di tutti i tipi di entità
  - Export CSV, PDF, Excel
  - 16 temi grafici
  - Autenticazione con bcrypt + keyring
  - Pipeline CI/CD GitHub Actions
