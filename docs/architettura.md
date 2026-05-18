# Architettura di Foliarium

## Panoramica

Foliarium è un'applicazione desktop a due livelli (**client-server**):

```
┌─────────────────────────┐          ┌─────────────────────────┐
│   Client Desktop        │          │   Server Database       │
│                         │          │                         │
│   PyQt6 GUI             │  TCP/IP  │   PostgreSQL 14+        │
│   (gui_main, widgets,   │◄────────►│   Schema: catasto       │
│    dialogs, foliarium/) │ psycopg2 │                         │
│                         │   pool   │   Tabelle, viste,       │
│   Logica applicativa    │          │   funzioni, trigger,    │
│   (catasto_db_manager)  │          │   procedure CRUD        │
└─────────────────────────┘          └─────────────────────────┘
```

- **Client**: applicazione Python 3.12 / PyQt6 che si installa sulla postazione dell'operatore
- **Server**: database PostgreSQL centralizzato, accessibile da più client in rete

## Moduli Python

A partire dallo Sprint 3 del refactor (analisi six-hats), Foliarium è
organizzato come un piccolo numero di moduli root + package `foliarium/`
che contiene la maggior parte della logica UI estratta.

### Entry point e infrastruttura

| Modulo | Ruolo |
|---|---|
| `gui_main.py` | Entry point. `CatastoMainWindow` (`QMainWindow`), menu, navigazione, slot Qt. Delega login/startup/theme ai moduli sotto. |
| `config.py` | Costanti, lettura `config.ini`, logging globale con rotazione, `IS_TEST_ENV`, `IS_DEMO_MODE`, `assert_db_password_configured()`. |
| `app_paths.py` | Risoluzione path per dev / bundle PyInstaller (`BASE_DIR`, `EXE_DIR`, `APP_DATA_DIR`). |
| `app_utils.py` | Helper IO/keyring/format + facade re-export per PDF e GUI export (era 923 LOC, ora 176). |
| `validators.py` | `FieldValidator` con metodi statici (`required_text`, `email`, `data`, ecc.) e `ValidationResult` dataclass. |

### Accesso ai dati (`db/`, `catasto_db_manager.py`)

`CatastoDBManager` è un facade che eredita da 14 mixin per dominio:
`db/comuni.py`, `db/possessori.py`, `db/partite.py`, `db/immobili.py`,
`db/variazioni.py`, `db/documenti.py`, `db/audit.py`, `db/utenti.py`,
`db/backup.py`, `db/stats.py`, `db/ricerca.py`, `db/io.py`,
`db/archivio.py`, `db/localita.py`. La base condivisa
(`db/base.py`) gestisce il connection pool `psycopg2.pool`, il context
manager `_get_connection()` e il decorator `@db_handle_errors` che
traduce errori psycopg2 in eccezioni custom (`DBMError`,
`DBUniqueConstraintError`, `DBNotFoundError`, `DBDataError` —
definite in `catasto_exceptions.py`).

### Sessione e autenticazione (`core/`)

| Modulo | Classe | Funzione |
|---|---|---|
| `core/session_manager.py` | `SessionManager` | Stato dell'utente corrente: id, username, ruolo, display name, IP, timestamp login |
| `core/auth_manager.py` | `AuthManager` | Login con bcrypt, rate-limit anti brute-force in-memory, hash dummy anti user-enumeration (`_DUMMY_HASH`), verifica permessi |

### UI estratta — `foliarium/ui/`

Sequenza di avvio scomposta in moduli dedicati (Sprint 3.5–3.7):

| Modulo | Responsabilità |
|---|---|
| `foliarium/ui/theme.py` | Funzioni pure di tema QSS: `apply_stylesheet`, `apply_auto_theme`, `apply_initial_theme_from_settings`, `is_win11_style_available` |
| `foliarium/ui/login_flow.py` | `try_autoconnect_db`, `connect_db_with_dialog`, `ensure_db_connection`, `perform_user_login` |
| `foliarium/ui/startup.py` | `show_splash_screen`, `ensure_eula_accepted`, `validate_license_and_acquire_seat` |
| `foliarium/ui/top_bar.py` | `TopBarWidget` (header con titolo + chip licenza) |
| `foliarium/ui/sidebar.py` | `SidebarWidget` (navigazione) |
| `foliarium/ui/command_palette.py` | Palette comandi (Ctrl+K) |
| `foliarium/ui/splash.py` | `FoliariumSplashScreen` |

Widget UI raggruppati per dominio funzionale:

| Sottocartella | Contenuto |
|---|---|
| `foliarium/ui/widgets/insertion.py` | `InserimentoComuneWidget`, `InserimentoPossessoreWidget`, `InserimentoLocalitaWidget`, `InserimentoPartitaWidget` |
| `foliarium/ui/widgets/admin.py` | `GestioneUtentiWidget`, `AuditLogViewerWidget`, `BackupWidget`, `TipiPossessoWidget`, `ArchivioWidget`, `TabelleDiSistemaWidget` |
| `foliarium/ui/widgets/reporting.py` | `RicercaDocumentiWidget`, `EsportazioniWidget`, `ReportisticaWidget`, `StatisticheWidget`, `RegistraConsultazioneWidget` |
| `foliarium/ui/widgets/custom.py` | `LazyLoadedWidget`, `QPasswordLineEdit`, `StatCard`, `show_status_message`, helper condivisi |
| `foliarium/ui/widgets/comuni.py` | `ElencoComuniWidget`, `ComuniTableModel`, `_ComuniLoaderWorker` (Sprint 3.8) |
| `foliarium/ui/widgets/dashboard.py` | `DashboardWidget`, `_DashboardLoaderWorker` (Sprint 3.8) |
| `foliarium/ui/widgets/welcome.py` | `WelcomeScreen` — EULA splash (Sprint 3.8) |
| `foliarium/ui/widgets/search/` | `partite.py`, `immobili.py`, `fuzzy.py` — un file per famiglia di ricerca (Sprint 3.4) |
| `foliarium/ui/widgets/workflow/` | `registrazione_proprieta.py`, `nuova_partita_wizard.py`, `operazioni_partita.py` (Sprint 3.3) |
| `foliarium/ui/csv_export.py` | 5 helper di export CSV (Sprint 3.9) |
| `foliarium/ui/dialogs/` | `entity.py`, `admin.py`, `partita.py`, `import_.py`, `export_.py` |

### API contract — `foliarium/protocols.py`

Sette `typing.Protocol` `@runtime_checkable` che descrivono la superficie d'uso di `CatastoDBManager` dal punto di vista dei consumer (widget + test): `ComuneOpsProtocol`, `PossessoreOpsProtocol`, `PartitaOpsProtocol`, `ImmobileOpsProtocol`, `LocalitaOpsProtocol`, `AuditOpsProtocol` + `DBManagerProtocol` (unione). I widget possono annotare `db: DBManagerProtocol` senza importare `CatastoDBManager` (rompe i cicli di import e permette type checking dei consumer).

### Tooling sviluppatore — `bin/`

| Script | Ruolo |
|---|---|
| `bin/check_api_drift.py` | Gate anti-drift: incrocia metodi DB definiti con chiamate `db.X()` nei consumer. Exit 1 se trova metodi chiamati ma non definiti. Pensato per pre-commit hook o CI gate. |
| `bin/migrate.py` | CLI minimale per applicare/ispezionare migrazioni SQL. Comandi: `status`, `up`, `up --dry-run`, `up --file <X>`. Usa la tabella `catasto.schema_version` per tracking. Vedi *Migrazioni Schema*. |

### Reportistica e export

- `foliarium/reporting/pdf.py` — classi PDF: `ModernCatastoPDF` (base con palette istituzionale, header banda blu, footer paginazione, `cover_block`, `section_title`, `info_block`, `styled_table`), `PDFPartita`, `PDFPossessore`, `GenericTextReportPDF` (Courier), `BulkReportPDF` (landscape, header ripetuto).
- `foliarium/ui/export/partita.py` — wrapper GUI: `gui_esporta_partita_{json,csv,pdf}` con dialog di anteprima.
- `foliarium/ui/export/possessore.py` — analoghi per i possessori.

### Servizi (`foliarium/core/services/`)

| Modulo | Ruolo |
|---|---|
| `license.py` | `LicenseManager`: validazione file `.license` HMAC-SHA256, hardware fingerprint, gestione seat di rete con TTL |
| `email.py` | Notifiche SMTP (creazione/modifica utenti, login) |
| `update_checker.py` | Verifica aggiornamenti remoti |
| `demo_launcher.py` | Avvio PostgreSQL embedded portatile per modalità `--demo` |

### REST API (opzionale, `api/`)

API FastAPI per integrazioni esterne: `api/main.py` espone la factory
`create_app()`, `api/server_thread.py` permette di farla girare in un
thread separato all'interno dell'app desktop. Routes in
`api/routes/`: `comuni`, `partite`, `possessori`, `audit`,
`genealogia`, ecc.

## Schema del database

Lo schema risiede nello schema PostgreSQL `catasto` (configurabile via
`SETTINGS_DB_SCHEMA`) e comprende le seguenti tabelle principali:

```
periodo_storico          Periodi storici (Regno di Sardegna, Regno d'Italia, Repubblica)
comune                   Anagrafica comuni con codice catastale e periodo di riferimento
registro_partite         Registri delle partite per comune e anno
registro_matricole       Registri delle matricole per comune e anno
partita                  Partite catastali (numero, suffisso, stato, tipo, date)
possessore               Possessori/proprietari con paternità
partita_possessore       Relazione N:M tra partite e possessori (titolo, quota)
localita                 Località/indirizzi (tipologia stradale, civico)
immobile                 Immobili (natura, piani, vani, consistenza, classificazione)
partita_relazione        Relazioni tra partite principali e secondarie
variazione               Variazioni di proprietà (vendita, successione, divisione, ecc.)
contratto                Contratti associati alle variazioni (notaio, repertorio)
consultazione            Registro consultazioni dell'archivio
audit_log                Log automatico delle operazioni (INSERT, UPDATE, DELETE)
app_metadata             Metadati applicazione (chiave-valore)
utente                   Utenti applicazione (da script 07)
permesso                 Permessi disponibili
utente_permesso          Associazione utenti-permessi
```

### Estensioni PostgreSQL utilizzate
- `uuid-ossp` — generazione UUID
- `pg_trgm` — ricerca fuzzy con trigrammi (indici GIN)

### Viste principali
- `v_partite_complete` — join completo partite-comuni-possessori con conteggio immobili
- `v_variazioni_complete` — join variazioni-partite-contratti con dati origine/destinazione

## Sicurezza

- Le password degli utenti applicativi sono memorizzate con hash **bcrypt** (cost 12)
- `AuthManager` implementa **rate-limit in-memory** (5 tentativi → lockout 15 minuti) e usa un **hash dummy precomputato** per normalizzare i tempi di risposta del login e prevenire user enumeration tramite timing attack
- Il salvataggio delle password di connessione al database è gestito tramite **keyring** del sistema operativo; **mai** persistite in QSettings
- Il file `config.ini` (con credenziali) è escluso dal repository tramite `.gitignore`
- Se la password DB manca in produzione, `config.assert_db_password_configured()` solleva `RuntimeError` invece di tentare un login silenzioso con password vuota
- L'audit log registra automaticamente tutte le modifiche ai dati con utente, timestamp e IP
- Il sistema di permessi consente di limitare l'accesso alle funzionalità per ruolo
- Il file `.license` è firmato con **HMAC-SHA256**; la chiave non è hardcoded ma letta da `FOLIARIUM_LICENSE_KEY` o da un file `foliarium.key` in `EXE_DIR`

## Backward compatibility (post-refactor Sprint 3)

Alcuni moduli root sono diventati facade thin che re-esportano dai
nuovi package. **Tutti gli import storici continuano a funzionare**:

```python
# Equivalenti (entrambi validi)
from search_widgets import RicercaPartiteWidget
from foliarium.ui.widgets.search import RicercaPartiteWidget

from partita_workflow_widgets import NuovaPartitaWizardWidget
from foliarium.ui.widgets.workflow import NuovaPartitaWizardWidget

from app_utils import PDFPartita, gui_esporta_partita_pdf
from foliarium.reporting.pdf import PDFPartita
from foliarium.ui.export import gui_esporta_partita_pdf
```

I nuovi import sono preferiti per nuovo codice. I facade sono mantenuti
per evitare PR ad alto blast-radius sui consumer storici.

## Compatibilità PyInstaller

Il modulo `app_paths.py` gestisce la risoluzione dei percorsi sia in
ambiente di sviluppo che all'interno di un eseguibile creato con
PyInstaller. Distingue tre directory:

| Tipo file | Posizione | Costante |
|---|---|---|
| Risorse bundled (icone, .qss, .md, .svg) | `_internal/` | `BASE_DIR` |
| File utente / installer (`config.ini`, `.license`, `foliarium.key`) | Accanto all'exe | `EXE_DIR` |
| Dati scrivibili (log, cache, esportazioni) | `%LOCALAPPDATA%\Foliarium` | `APP_DATA_DIR` |

`app_paths.get_exe_dir()` ritorna `Path(sys.executable).parent` quando
l'app è frozen (PyInstaller), `Path(__file__).parent` altrimenti.

Lo spec `foliarium.spec` produce un bundle **onedir** standard; lo spec
`foliarium_demo.spec` include anche PostgreSQL portatile per la
modalità demo (`Foliarium.exe --demo`).
