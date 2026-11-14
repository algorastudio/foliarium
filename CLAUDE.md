# CLAUDE.md — Foliarium · Archivio Catastale Storico

## Project overview

**Foliarium** is a desktop application for managing historical Italian cadastral records (archivio catastale storico). It allows archivists to search, insert, and export property records (partite catastali) and owners (possessori).

- **Current version:** 1.0.2
- **Author:** Marco Santoro / Algora Studio
- **Primary platform:** Windows 10+
- **Code/UI language:** Italian
- **Precedentemente noto come:** Meridiana (rinominato a Foliarium in v1.5.0)

---

## Tech stack

| Layer | Technology |
|---|---|
| Language | Python 3.12 |
| GUI | PyQt6 6.8.1 (WebEngine opzionale, non richiesto) |
| Database | PostgreSQL 14+ |
| DB driver | psycopg2-binary 2.9.10 |
| Data | pandas 2.3, numpy 2.3, openpyxl 3.1.5 |
| PDF export | fpdf2 2.8.3 |
| Auth/security | bcrypt 4.3.0, keyring 25.6.0 |
| Build | PyInstaller (`foliarium.spec`) + Inno Setup |
| CI/CD | GitHub Actions |
| Docs | MkDocs (Material theme) |

---

## Project structure

```
foliarium/
├── gui_main.py                   # Entry point — QMainWindow, navigazione, slot Qt (~2000 LOC)
├── gui_widgets.py                # Facade thin (178 LOC) → foliarium/ui/widgets/{comuni,dashboard,welcome} + altri re-export
├── search_widgets.py             # Facade thin (41 LOC) → foliarium/ui/widgets/search/
├── partita_workflow_widgets.py   # Facade thin (24 LOC) → foliarium/ui/widgets/workflow/
├── dialogs.py                    # Facade di re-export dialogs (implementati in foliarium/ui/dialogs/)
├── catasto_db_manager.py         # Facade DB — delega al package db/
├── app_utils.py                  # Helper IO/keyring/format + facade PDF/export (176 LOC, post-refactor)
├── app_paths.py                  # Path resolution & resource loading
├── config.py                     # Costanti, logging, APP_VERSION, assert_db_password_configured()
├── validators.py                 # Validatori campi form
│
├── foliarium/                    # Package principale (servizi + UI estratti)
│   ├── core/services/            # email.py, license.py, update_checker.py, demo_launcher.py, backup_crypto.py
│   ├── reporting/                # PDF reports (post-refactor Sprint 3.1)
│   │   └── pdf.py                # ModernCatastoPDF + PDFPartita/Possessore/Generic/Bulk
│   └── ui/
│       ├── top_bar.py, sidebar.py, command_palette.py, splash.py, effects.py
│       ├── errors.py             # show_user_error() — errori DB in italiano (Sprint 4.1)
│       ├── undo.py               # Annullamento ultima operazione reversibile (Sprint 4.3)
│       ├── import_progress.py    # Import di massa su QThread con Annulla (Sprint 4.2)
│       ├── theme.py              # Funzioni pure tema QSS (post-refactor Sprint 3.5)
│       ├── login_flow.py         # Connessione DB + login utente (post-refactor Sprint 3.6)
│       ├── startup.py            # Splash + EULA + license check (post-refactor Sprint 3.7)
│       ├── dialogs/              # entity.py, admin.py (+ LoginDialog), partita.py, import_.py, export_.py
│       ├── export/               # Wrapper GUI export (post-refactor Sprint 3.2)
│       │   ├── partita.py        # gui_esporta_partita_{json,csv,pdf}
│       │   └── possessore.py     # gui_esporta_possessore_{json,csv,pdf}
│       └── widgets/
│           ├── admin.py          # GestioneUtenti, AuditLog, Backup, TipiPossesso, Archivio
│           ├── insertion.py      # Form inserimento (Comune, Possessore, Localita, Partita)
│           ├── reporting.py      # Documenti, Esportazioni, Reportistica, Statistiche
│           ├── custom.py         # Widget condivisi, show_status_message, LazyLoadedWidget,
│           │                  # UnsavedFormMixin, FormDraftMixin, imposta_nomi_accessibili
│           ├── comuni.py         # ElencoComuniWidget + ComuniTableModel (Sprint 3.8)
│           ├── dashboard.py      # DashboardWidget + _DashboardLoaderWorker (Sprint 3.8)
│           ├── welcome.py        # WelcomeScreen (EULA) (Sprint 3.8)
│           ├── workflow/         # Widget workflow partite (post-refactor Sprint 3.3)
│           │   ├── registrazione_proprieta.py    # RegistrazioneProprietaWidget
│           │   ├── nuova_partita_wizard.py       # NuovaPartitaWizardWidget
│           │   └── operazioni_partita.py         # OperazioniPartitaWidget
│           └── search/           # Widget ricerca (post-refactor Sprint 3.4)
│               ├── partite.py    # Worker, model, proxy, card, widget
│               ├── immobili.py   # Model + RicercaAvanzataImmobiliWidget
│               └── fuzzy.py      # UnifiedFuzzySearchWidget + thread + model
│
├── db/                           # Database layer — 15 mixin via ereditarietà multipla
│   ├── base.py                   # DBConnectionBase: pool, _get_connection(), bulk_insert
│   ├── comuni.py, localita.py, possessori.py, partite.py, immobili.py
│   ├── variazioni.py, documenti.py, audit.py, utenti.py
│   ├── backup.py, stats.py, ricerca.py, io.py, archivio.py
│   ├── drafts.py                 # DBDraftsMixin (bozze wizard + moduli di inserimento semplice)
│   ├── api_keys.py               # DBApiKeysMixin (chiavi API per integrazioni esterne, MCP, ecc.)
│   └── models.py                 # Dataclass models
│
├── core/                         # Gestione sessione e autenticazione
│   ├── session_manager.py        # SessionManager (stato utente corrente)
│   └── auth_manager.py           # AuthManager (authn + permessi)
│
├── api/                          # REST API FastAPI (opzionale, per integrazioni esterne)
│   ├── main.py, server_thread.py
│   └── routes/                   # comuni, partite, possessori, audit, genealogia, ecc.
│
├── utils/
│   └── error_handlers.py         # Eccezioni custom (AuthenticationError, ecc.)
│
├── sql_scripts/                  # Script PostgreSQL (init + migrazioni)
│   └── migrations/               # Script di upgrade per DB già esistenti
├── styles/                       # Qt stylesheets (.qss)
├── resources/                    # Icone, immagini, EULA
├── tests/                        # Test suite (pytest)
│   ├── unit/                     # Unit test (validators, theme, db mixins, license, ecc.)
│   └── integration/              # Integration test (E2E, golden_path, DB live, GUI)
├── docs/                         # MkDocs documentation source
├── esportazioni/                 # Output directory (PDF, CSV)
├── docker/                       # Container
│   ├── postgres/                 # Immagine del database (stack web e demo): Dockerfile, init.sh
│   ├── demo/                     # Demo: il desktop nel browser, a postazioni (vedi sezione dedicata)
│   └── README.md                 # Stack web (FastAPI + React), con Dockerfile e docker-compose.yml in radice
├── .devcontainer/                # Dev container config (VS Code / Codespaces)
├── .github/workflows/            # CI/CD pipeline
├── foliarium.spec                # PyInstaller build spec (produzione)
├── setup_db.spec                 # PyInstaller build spec (setup_db.exe)
├── Foliarium_Installer.iss       # Installer Inno Setup (PostgreSQL incluso)
├── setup_database.bat / .py      # Init DB Windows / cross-platform
└── generate_license.py           # CLI: genera/ispeziona file .license
```

### Convenzioni post-refactor (Sprint 3 — six-hats)

Diversi moduli root sono ora **facade thin** che re-esportano dai nuovi
package coesi. I consumer storici continuano a funzionare:

```python
# Vecchio import (ancora valido)
from search_widgets import RicercaPartiteWidget
from partita_workflow_widgets import NuovaPartitaWizardWidget
from app_utils import PDFPartita, gui_esporta_partita_pdf

# Nuovo import preferito
from foliarium.ui.widgets.search import RicercaPartiteWidget
from foliarium.ui.widgets.workflow import NuovaPartitaWizardWidget
from foliarium.reporting.pdf import PDFPartita
from foliarium.ui.export import gui_esporta_partita_pdf
```

**Riduzioni LOC** dopo lo Sprint 3:

| File | Prima | Dopo |
|---|---|---|
| `partita_workflow_widgets.py` | 2.209 | 24 |
| `search_widgets.py` | 1.841 | 41 |
| `gui_widgets.py` | 1.036 | 178 |
| `app_utils.py` | 923 | 176 |
| `gui_main.py` | 2.155 | 1.982 |

> `gui_main.py` è poi risalito a ~2.500 righe con lo Sprint 4 (protocolli
> UI, scorciatoie, barra di annullamento). È il prossimo candidato a
> un'estrazione: le sezioni "modifiche non salvate", "scorciatoie" e
> "annullamento" sono già coese e separabili.

---

## Key commands

```bash
# Run the application
python gui_main.py

# Run in demo mode (embedded PostgreSQL portabile)
python gui_main.py --demo

# Generate a license file for a client
python generate_license.py generate \
    --to "Archivio di Stato di Savona" \
    --type standard --seats 2 \
    --expiry 2027-12-31 --out savona.license

# Inspect a license file
python generate_license.py inspect savona.license

# Show hardware fingerprint of current machine
python generate_license.py fingerprint

# Generate HMAC-SHA256 key for license signing (foliarium.key)
python generate_key.py                    # Interactive menu
python generate_key.py --save-exe-dir     # Auto-save to EXE_DIR (next to Foliarium.exe)
python generate_key.py --save-base-dir    # Auto-save to BASE_DIR (project root)
python generate_key.py --env-var          # Print only HEX value (for environment variable)

# Run all tests
pytest

# Run by marker
pytest -m unit
pytest -m integration
pytest -m "not gui"          # skip GUI tests (e.g. in headless env)

# Build Windows executable
pyinstaller foliarium.spec

# Install dependencies
pip install -r requirements.txt
```

For CI-style local testing set these env vars before running pytest:
```bash
export CI=true
export DB_HOST=localhost DB_USER=postgres DB_PASS=postgres
export DB_NAME=catasto_storico DB_PORT=5432
export QT_QPA_PLATFORM=offscreen
```

---

## Architecture

- **Entry point:** `gui_main.py` creates the `QApplication` and `QMainWindow`, initialises logging (`config.setup_global_logging`), builds `TopBarWidget` + `SidebarWidget` + `QStackedWidget`, navigates with `navigate_to(page_name)`. La sequenza di avvio delega a moduli dedicati: `foliarium.ui.theme` (bootstrap stylesheet), `foliarium.ui.startup` (splash, EULA, licenza), `foliarium.ui.login_flow` (connessione DB + login utente).
- **DB layer:** `catasto_db_manager.py` — facade thin che eredita dai mixin in `db/`. `CatastoDBManager` espone tutti i metodi CRUD. Credentials are read from env vars (`DB_HOST`, `DB_USER`, `DB_PASS`, `DB_NAME`, `DB_PORT`) with fallback to defaults defined in `config.py`. Se la password manca in produzione, `config.assert_db_password_configured()` solleva `RuntimeError` invece di tentare un login silenzioso con password vuota. **TLS:** `DBConnectionBase._resolve_sslmode()` determina il `sslmode` libpq con precedenza valore esplicito → `config.ENV_DB_SSLMODE` (env `DB_SSLMODE` / `config.ini [database].sslmode`) → default per host (`prefer` in locale, `require` per host remoti, così le credenziali non viaggiano mai in chiaro su rete). Il valore effettivo è in `_main_db_conn_params["sslmode"]` e si propaga a pool e connessioni di manutenzione.
- **CI detection:** `config.IS_TEST_ENV` is `True` when `CI=true` or `GITHUB_ACTIONS=true`. Used to skip interactive prompts and adjust logging.
- **UI widget distribution** (post-refactor Sprint 3):
  - `gui_widgets.py` — facade thin (178 LOC) di re-export verso `foliarium/ui/widgets/{comuni,dashboard,welcome}` + altri
  - `foliarium/ui/widgets/comuni.py` — `ElencoComuniWidget` + `ComuniTableModel` + `_ComuniLoaderWorker` (Sprint 3.8)
  - `foliarium/ui/widgets/dashboard.py` — `DashboardWidget` + `_DashboardLoaderWorker` (Sprint 3.8)
  - `foliarium/ui/widgets/welcome.py` — `WelcomeScreen` (EULA splash) (Sprint 3.8)
  - `foliarium/ui/widgets/search/` — 3 file per famiglia: `partite.py`, `immobili.py`, `fuzzy.py`
  - `foliarium/ui/widgets/workflow/` — 3 file: `registrazione_proprieta.py`, `nuova_partita_wizard.py`, `operazioni_partita.py`
  - `foliarium/ui/widgets/insertion.py` — form inserimento (Comune, Possessore, Località, Partita)
  - `foliarium/ui/widgets/admin.py` — `GestioneUtentiWidget`, `AuditLogViewerWidget`, `BackupWidget`, `TipiPossessoWidget`, `ArchivioWidget`
  - `foliarium/ui/widgets/reporting.py` — `RicercaDocumentiWidget`, `EsportazioniWidget`, `ReportisticaWidget`, `StatisticheWidget`
- **Reporting:** classi PDF in `foliarium/reporting/pdf.py` (estratte da `app_utils.py` nello Sprint 3.1). Wrapper GUI di export in `foliarium/ui/export/{partita,possessore}.py`.
- **Themes:** QSS stylesheets in `styles/`. Funzioni pure in `foliarium/ui/theme.py`: `apply_stylesheet`, `apply_auto_theme`, `apply_initial_theme_from_settings`, `is_win11_style_available`, `is_dark_theme`. Quest'ultima serve ai contenuti HTML renderizzati dentro l'app (il manuale nel `QTextBrowser`), che il QSS di Qt non raggiunge: senza, il manuale resterebbe bianco anche in tema scuro.
- **Credenziali di connessione:** `foliarium/ui/login_flow.py` le risolve chiave per chiave con precedenza **QSettings > `config.ini` / env var > default**. `config.ENV_DB_*` incorpora gia' la precedenza `config.ini` > env > default (`config.py`), quindi in `login_flow` serve solo come fallback di ogni `settings.value()`. Senza questo fallback, al primo avvio dopo l'installazione QSettings e' vuota e l'archivista dovrebbe ridigitare a mano credenziali che l'installer ha gia' scritto in `config.ini` accanto all'eseguibile. La password segue l'ordine QSettings > keyring > `config.ini`, ma quella di `config.ini` viene usata **solo se host, porta, database e utente risolti coincidono con quelli configurati** (`_targets_configured_server`): con QSettings che punta altrove sarebbe la credenziale di un altro server. Il `DBConfigDialog` di fallback riceve gli stessi parametri risolti come `initial_config`.
- **Sessione utente:** il logout **non chiude l'applicazione** — `handle_logout()` azzera la sessione (`_clear_session_state()`) e riapre `LoginDialog` riusando il pool DB. Di conseguenza `perform_initial_setup()` può essere eseguito più volte nella stessa sessione: scorciatoie, segnale `colorSchemeChanged` e timer del seat di licenza sono registrati una sola volta (guardie esplicite). Se il login viene annullato, allora l'applicazione si chiude.
- **Supporto/diagnostica:** menu **Help → Esporta log per supporto (.zip)...** invoca `gui_main.MainWindow._esporta_log_zip` che delega a `app_utils.create_logs_archive(destination_path) -> (n_file, size_bytes)`. La helper scopre le cartelle di log via `app_utils._discover_log_directories()` (cumulativa di `QStandardPaths.AppLocalDataLocation`, della sua sotto-cartella `logs/` e della legacy `app_paths.LOG_DIR`) e comprime in uno zip `ZIP_DEFLATED` tutti i file `*.log` / `*.log.N` (rotazioni). Dedup per path canonico, solleva `FileNotFoundError` se nessun file di log esiste. Il path reale su Windows (con `OrganizationName="AlgoraStudio"` + `ApplicationName="Foliarium"`) è `%LOCALAPPDATA%\AlgoraStudio\Foliarium\` (root: `foliarium_session.log`; sotto-cartella `logs/`: `foliarium_gui.log` + rotazioni).

---

## Convenzioni UI (revisione euristica — Sprint 4)

Una valutazione dell'interfaccia rispetto alle 10 euristiche di Nielsen ha
prodotto quattro protocolli trasversali. Le pagine vi partecipano **per duck
typing**, non per ereditarietà: i widget di inserimento derivano da
`LazyLoadedWidget`, quelli di workflow da `QWidget`, e una pagina che non
implementa un metodo semplicemente non partecipa.

### 1. Errori comprensibili — `foliarium/ui/errors.py`

Non mostrare mai `str(e)` di un'eccezione del layer DB in un `QMessageBox`:
l'archivista leggerebbe `duplicate key value violates unique constraint
"partita_unique_numero_suffisso_comune"`.

```python
from foliarium.ui.errors import show_user_error

try:
    self.db_manager.aggiungi_comune(...)
except Exception as e:
    show_user_error(self, "Inserimento comune", e, logger=self.logger)
```

`describe_error()` risale la catena `__cause__` fino all'errore psycopg2
(il decoratore `db_handle_errors` rilancia con `raise ... from e`, quindi
`pgcode` resta disponibile), mappa il codice SQLSTATE in una frase italiana
e un suggerimento, e lascia il testo tecnico nei "Dettagli" con un pulsante
che apre l'esportazione dei log. Per estendere la copertura: aggiungere
voci a `_SQLSTATE_MESSAGES` (codici) o `_CONSTRAINT_MESSAGES` (vincoli noti
dello schema, messaggio più preciso del generico 23505).

### 2. Modifiche non salvate

`navigate_to()` e `closeEvent()` interrogano la pagina prima di lasciarla.
Metodi opzionali:

| Metodo | Effetto |
|---|---|
| `has_unsaved_changes() -> bool` | obbligatorio per essere interrogata |
| `save_pending_changes() -> bool` | abilita "Salva bozza" nel dialogo |
| `discard_pending_changes()` | azzera dopo lo scarto |

I wizard usano il proprio flag `_dirty`; i moduli di inserimento usano
`UnsavedFormMixin`, che confronta i campi con uno scatto preso a form
pulito (`mark_form_clean()`), così un default precompilato non viene
scambiato per lavoro dell'utente. **La soglia è alta di proposito**: del
testo digitato basta da solo, ma per le sole selezioni ne servono due — un
avviso che scatta a vuoto insegna a ignorarlo.

`mark_form_clean()` va chiamata dopo il caricamento iniziale dei menu a
tendina, dopo "Pulisci campi" e dopo un salvataggio riuscito.

### 3. Bozze dei moduli — `FormDraftMixin`

Riusa `catasto.partita_draft` (nata per i wizard) serializzando i campi per
nome di attributo. Il modulo dichiara:

```python
class InserimentoComuneWidget(FormDraftMixin, UnsavedFormMixin, LazyLoadedWidget):
    _DRAFT_KIND = FORM_KIND_INSERIMENTO_COMUNE   # da db/drafts.py
    _DRAFT_ETICHETTA = "Comune"
```

`wizard_kind` tiene separate le liste per tipo di modulo. Alla ripresa i
`QComboBox` si ritrovano per dato e, in mancanza, per testo: una lista
ripopolata in ordine diverso non perde la scelta. Il salvataggio passa dal
dialogo delle modifiche non salvate — nei moduli c'è solo "Riprendi
bozza…", perché una barra con cinque pulsanti non ne regge due in più.
`gui_main.setup_pages()` assegna `utente_id` ai moduli: senza, le bozze
finirebbero fra quelle orfane, visibili a chiunque.

### 4. Annullamento — `foliarium/ui/undo.py`

**Non un `QUndoStack`, e la scelta è deliberata.** Le operazioni sono già
scritte su un database condiviso: annullare la quinta azione a ritroso
mezz'ora dopo sovrascriverebbe il lavoro di un altro archivista. Quindi
una sola azione per volta, scadenza di due minuti, azzerata al cambio
utente.

```python
from foliarium.ui.undo import registra_azione_annullabile

self.db_manager.archivia_comune(comune_id)
registra_azione_annullabile(
    f"Comune «{nome}» archiviato",
    lambda: self.db_manager.ripristina_comune(comune_id),
    al_termine=self.load_data,
)
```

Sono annullabili **solo le operazioni che hanno già un inverso esatto nel
layer DB** (archiviazione e ripristino). Aggiornamenti ed eliminazioni
definitive restano fuori: il primo richiederebbe di conservare lo stato
precedente per intero, il secondo per definizione non ha inverso. La
sicurezza in multi-utente arriva dallo schema: `ripristina_*` filtra sullo
stato di partenza (`WHERE id = %s AND archiviato`), quindi un annullamento
tardivo fallisce con un errore esplicito invece di sovrascrivere.

### Scorciatoie da tastiera

`CatastoMainWindow._SHORTCUTS` è l'unica fonte sia per i `QShortcut` sia
per la finestra di riepilogo (Help → Scorciatoie, `Ctrl+/`), così l'elenco
mostrato non può divergere da quello attivo. Il quarto campo della tupla
marca le voci che hanno già la scorciatoia su una `QAction` di menu:
registrarne una seconda la renderebbe ambigua per Qt, che in quel caso
**non attiva nulla**.

`Ctrl+S` cerca sulla pagina corrente, in ordine, `save_pending_changes()`
(bozza) e `trigger_primary_action()` (salvataggio vero del modulo).

### Import di massa

Gli import CSV/Excel girano in un `QThread` con avanzamento e Annulla
(`foliarium.ui.import_progress.esegui_import_con_progresso`). Il layer DB
accetta `progress_cb(elaborate, totali)` e interrompe il ciclo se
restituisce `False`. **L'annullamento è parziale per costruzione**: ogni
riga ha il suo SAVEPOINT, quindi le righe già inserite restano. Il
risultato porta la chiave `interrotto` e la UI lo dichiara all'utente
(`_avvisa_se_import_interrotto`).

### Altre convenzioni

- **Date:** sempre `config.DATE_DISPLAY_FORMAT` (`dd/MM/yyyy`) e
  `DATETIME_DISPLAY_FORMAT` nei `QDateEdit`, mai un letterale ISO. Un test
  di regressione lo verifica su tutto il codice.
- **Conferme di successo:** status bar (`show_status_message`), non
  `QMessageBox`. Il modale è per le decisioni irreversibili.
- **Campi obbligatori:** `_check_required()` in `insertion.py` marca i
  campi, li elenca nella status bar e dà il focus al primo mancante —
  prima i moduli si limitavano a colorare il bordo e uscire in silenzio.
- **Accessibilità:** ogni campo ha un nome accessibile
  (`imposta_nomi_accessibili`), perché le etichette sono `QLabel` separate
  in rich text che Qt non associa al campo. I pulsanti hanno mnemonics
  senza lettere ripetute nello stesso modulo. `setTabOrder` **non** serve:
  l'ordine di tabulazione segue già quello visivo, verificato da un test.
- **Aiuto contestuale:** `CatastoMainWindow._AIUTO_CONTESTUALE` mappa
  `page_name` → documento di `docs/`, così F1 apre la sezione giusta.
  `HelpViewerDialog` ha una ricerca su tutti i `.md`; i link dei risultati
  usano lo schema `foliarium-doc:` perché puntano alla radice di `docs/` e
  non al documento che li contiene.
- **Manuale nel pacchetto:** `HelpViewerDialog` legge `BASE_DIR/docs` e
  `BASE_DIR/mkdocs.yml`, cioè `_internal/` nel bundle. `foliarium.spec` li
  aggiunge a `datas` con `_datas_manuale()` (solo i `.md`); senza, il
  manuale del programma installato si apre vuoto. `docs/internal/`
  (documenti di progetto) è escluso sia dal pacchetto sia dalla ricerca e
  dall'albero di ripiego (`documenti_del_manuale()` in `help_viewer.py`).
  `tests/unit/test_spec_manuale.py` esegue lo spec con `Analysis` finta e
  verifica il risultato: lo spec non deve importare PyInstaller, perché il
  job di test della CI non lo installa.

---

## Critical PyQt6 convention

**All enums MUST be fully namespaced.** PyQt6 removed the Qt4/Qt5 shorthand.

```python
# CORRECT
Qt.AlignmentFlag.AlignLeft
Qt.ItemFlag.ItemIsSelectable
QSizePolicy.Policy.Expanding
QFont.Weight.Bold

# WRONG (will raise AttributeError at runtime)
Qt.AlignLeft
Qt.ItemIsSelectable
QSizePolicy.Expanding
QFont.Bold
```

Always use the full three-part path `Module.EnumClass.Value`.

---

## Database

- **DB name:** `catasto_storico`
- **Default user:** `postgres`
- **Schema:** `public` (configurable via `SETTINGS_DB_SCHEMA`)
- Passwords are **not** stored in QSettings — keyring is used for secure storage.
- Init SQL scripts are in `sql_scripts/`; run in order for a fresh DB.
- Upgrade scripts for existing DBs are in `sql_scripts/migrations/`.
- **Auto-apply migrazioni idempotenti:** `db/base.py::_apply_pending_schema_migrations()` viene invocata a ogni init pool e applica silenziosamente migrazioni sicure (es. schema v1.6.1, indici UNIQUE sulle MV, vista `v_audit_dettagliato` — equivalente di `migrations/19_create_v_audit_dettagliato.sql`, tabella `partita_draft` — equivalente di `migrations/21_create_partita_draft.sql`, tabella `api_keys` — equivalente di `migrations/22_create_api_keys.sql`, chiave esterna `audit_log.app_user_id → utente.id` — equivalente di `migrations/23_add_fk_audit_log_utente.sql`). Best-effort, non bloccante.
- **La sanatoria della chiave esterna di audit non riscrive il registro.** `_ensure_audit_user_fk()` crea il vincolo `NOT VALID` e poi tenta la convalida: se esistono righe di utenti già eliminati (l'applicazione permette di eliminarli) la convalida fallisce, il vincolo resta e quelle righe conservano l'identificativo. Non «semplificare» azzerandole con un `UPDATE`: è una decisione sullo storico che spetta a una persona, e la migrazione 23 spiega come. `lock_timeout` di 5 secondi perché `ALTER TABLE` attende chi sta scrivendo su `audit_log`.

## REST API & integrazioni esterne

- **FastAPI** in `api/` esposta con doppio prefisso: `/api/v1/*` (versione preferita, contratto stabile per integrazioni esterne) e `/api/*` (legacy, mantenuto per il frontend React esistente). Swagger UI: `/api/v1/docs`, OpenAPI JSON: `/api/v1/openapi.json`.
- **Avvio:** `APIServerThread` in `api/server_thread.py` esegue `uvicorn` su `127.0.0.1:<porta-dinamica>` (default 8765+). Lanciato dal flusso WebViewWindow di `gui_main.py`.
- **Dual auth** (`api/deps.py`):
  - `Authorization: Bearer <token>` → sessione utente in-memory (TTL 120 min, `api/auth.py`). Implicitamente ha scope `*:*`.
  - `X-Foliarium-Api-Key: flr_<32 hex>` → chiave API persistente in `catasto.api_keys`. Scope granulari (es. `read:partite`, `write:partite`, wildcard `read:*` / `*:*`).
  - `get_current_session` (storica) accetta entrambi i metodi. Per scope-check granulare: `Depends(require_scope("read:partite"))`.
- **Gestione chiavi API** (mixin `db/api_keys.py`):
  - `create_api_key(name, scopes, created_by, expires_at=None, rate_limit_per_min=60) -> (id, plaintext)` — il plaintext (`flr_<32 hex>`) è restituito una sola volta; in DB si memorizza solo lo SHA-256 + prefix.
  - `validate_api_key(plaintext) -> Optional[dict]` — verifica hash, scadenza, revoca; aggiorna `last_used_at`.
  - `list_api_keys(include_revoked=False)`, `revoke_api_key(id)`.
- **Admin UI** (`foliarium/ui/dialogs/admin/api_keys.py`): voce **Impostazioni → Gestione Chiavi API…** (solo admin) apre `ApiKeysDialog` (tabella chiavi con stati Attiva/Revocata/Scaduta), `CreateApiKeyDialog` (form con scope checkbox + scadenza opzionale), `NewKeyResultDialog` (mostra il plaintext una sola volta con bottone "Copia"). Slot in `gui_main.MainWindow._apri_gestione_api_keys` con guard ruolo admin.

## MCP server (`mcp_server/`)

Package top-level che espone l'API REST come tool MCP (Model Context Protocol)
invocabili da **Claude Desktop** e altri client MCP.

- `mcp_server/server.py` — `FastMCP("foliarium")` con 23 tool su tre famiglie:
  - **lettura** (sola lettura, scope `read:*`): `elenca_comuni`, `elenca_localita`, `cerca_partite`, `dettagli_partita`, `cerca_possessori`, `dettagli_possessore`, `genealogia_partita`, `timeline_partita`, `elenca_immobili`, `statistiche_dashboard`, `analytics_dashboard`, `registro_audit`, `riepilogo_audit`.
  - **scrittura "sicura"** (scope `write:*`): `crea_comune`, `crea_possessore`, `crea_partita`, `aggiungi_immobile`, `aggiungi_variazione`, `aggiungi_possessore_a_partita`.
  - **scrittura distruttiva** (scope `write:*`): `aggiorna_partita`, `rimuovi_immobile`, `rimuovi_variazione`, `rimuovi_possessore_da_partita`.
  - **Conferma esplicita:** tutti i tool di scrittura accettano `confirm: bool = False`. Senza `confirm=True` restituiscono un'anteprima testuale dell'operazione e **non** chiamano l'API (`_needs_confirm` in `server.py`). Protegge da scritture accidentali da prompt ambigui.
- `mcp_server/client.py` — `FoliariumApiClient` (httpx sync) con header `X-Foliarium-Api-Key`. Primitiva `_get` per le letture e `_send` (POST/PATCH/DELETE) per le scritture; il 204 (No Content delle DELETE) viene mappato in `{"ok": True}`. Mappa 401/403/404/5xx in `FoliariumApiError` con messaggi umani (suggerisce "Genera nuova chiave da Gestione Chiavi API…", "Esporta log per supporto", ecc.).
- `mcp_server/__main__.py` — entry point `python -m mcp_server`, stdio mode (default Claude Desktop).
- Configurazione via env: `FOLIARIUM_API_BASE_URL` + `FOLIARIUM_API_KEY`.
- Documentazione utente: `docs/admin/api.md` (REST API + esempi curl) e `docs/admin/mcp.md` (guida Claude Desktop con esempio `claude_desktop_config.json`).
- **Avvisi schema:** `db/base.py::check_missing_migrations()` rileva colonne / tabelle critiche mancanti (`soft_delete`, `tipo_possesso`) e `gui_main._check_db_schema_migrations` mostra un avviso non bloccante.

---

## Dev container (VS Code / Codespaces)

```
noVNC desktop  → http://localhost:6080  (password: foliarium-dev)
PostgreSQL     → localhost:5432
QT_QPA_PLATFORM=xcb  (set automatically inside container)
```

Run `bash .devcontainer/setup.sh` to initialise the DB and install dependencies after container creation.

---

## CI/CD (GitHub Actions)

Pipeline: `.github/workflows/pipeline_foliarium.yml`

1. **Test job** (Ubuntu): spins up PostgreSQL 14, installs Qt6 system libs, runs pytest with `QT_QPA_PLATFORM=offscreen`, captures GUI screenshots as artifacts.
2. **Build job** (Windows, only if tests pass): runs PyInstaller, creates portable ZIP and Inno Setup installer, uploads as artifacts.

### Trigger

| Evento | Job eseguiti |
|---|---|
| `push` a `main`/`master`/branch-allowlist | test + tutti i build |
| `push` di un tag `*.*.*` | test + build + create-release |
| `pull_request` verso `main`/`master` | solo test (build skippati via `if: github.event_name != 'pull_request'`) |
| `workflow_dispatch` | tutti i job |

---

## Installer Windows (PostgreSQL incluso)

`Foliarium_Installer.iss` produce un installer che **crea il database
durante l'installazione**: nessun passaggio manuale, nessun PostgreSQL da
installare a parte. Tre ingredienti, preparati dalla pipeline in
`dist/Foliarium/` prima di invocare `iscc`:

| Ingrediente | Da dove |
|---|---|
| `Foliarium.exe` + `_internal/` | `pyinstaller foliarium.spec` |
| `setup_db.exe` | `pyinstaller setup_db.spec` |
| `pgsql/` (~120 MB) | binari EnterpriseDB, scaricati e potati dalla CI |

- **Versione di PostgreSQL:** `PG_BUNDLE_VERSION` nel workflow, unico punto.
  Lo ZIP EnterpriseDB pesa 822 MB estratti, di cui 673 di solo pgAdmin 4:
  lo step scarta `pgAdmin 4`, `doc`, `include`, `StackBuilder` e `symbols`,
  poi verifica che i sette eseguibili usati dal codice e le estensioni
  `pg_trgm`, `pgcrypto`, `uuid-ossp` ci siano. (`system_stats` **non** c'è:
  gli script di schema la creano dentro un `DO` block che la salta.)
- **Perché `setup_db.exe` è separato:** l'installer non può assumere Python
  sulla macchina del cliente. Usa solo la libreria standard, pesa 7 MB.
  Gli script SQL **non** vi sono impacchettati: restano risorsa del bundle
  principale (`_internal/sql_scripts`), e `resolve_sql_dir()` li cerca lì.
- **`[Code]` dell'installer:** esegue `setup_db.exe`, distingue i casi in
  cui non può riuscire (componente assente, `pgsql/` assente, porte 5432-34
  occupate) e rimanda a `setup_database.log`. **Nessuna `[UninstallRun]`:**
  i suoi parametri vengono fissati durante l'*installazione*, quindi un
  `{code:...}` che dipende dalla risposta alla disinstallazione verrebbe
  valutato troppo presto. La rimozione sta in `CurUninstallStepChanged`.
- **Disinstallazione:** il servizio `FoliariumDB` va rimosso sempre
  (altrimenti resta registrato puntando a eseguibili cancellati); i dati
  solo se l'utente risponde «Sì» alla domanda, che ha «No» preselezionato.
  `setup_database.py --uninstall --keep-data` è il caso conservativo.
- **Credenziali:** la password di `admin` è generata a caso e in DB resta
  solo l'hash bcrypt. `--credentials-out` la scrive in `PRIMO-ACCESSO.txt`,
  che l'installer apre a fine installazione.
- **Log:** `log()` scrive anche su file (`--log-file`, default
  `setup_database.log` nella cartella di installazione) perché l'installer
  esegue il setup con la console nascosta. Le password passate a
  `register_secret()` vi compaiono come `***`: il file resta sul disco del
  cliente e la documentazione invita ad allegarlo alle segnalazioni.
- **Ordine degli script:** `setup_database.SQL_SCRIPTS` è l'elenco, e
  **non segue le cartelle**: `admin/01_users.sql` sta prima di
  `functions/06_audit.sql`, che costruisce una vista e una chiave esterna
  su `catasto.utente`. Fino alla v1.0.2 erano invertiti e la chiave esterna
  non veniva creata, senza alcun avviso. `docker/postgres/init.sh` ne tiene
  una copia identica.
- **Rigore di psql:** `apply_sql_scripts()` usa `ON_ERROR_STOP` **solo se
  il database è stato creato in questa esecuzione**. L'installer riesegue
  il setup a ogni installazione, anche sopra un archivio esistente, e gli
  script non sono idempotenti: riapplicati producono 38 errori innocui,
  quasi tutti «already exists». Renderlo rigoroso sempre impedirebbe di
  reinstallare. In entrambi i casi gli errori di psql finiscono nel log
  (prima l'output era catturato e scartato). Il database dei test della
  pipeline è costruito con i vecchi script numerati, non con questo
  elenco: lo sorveglia `tests/integration/test_schema_database_nuovo.py`,
  che lo applica a un database vuoto con la funzione dell'installer.
- **Validazione:** il job `valida-installer` compila l'installer contro un
  `dist/` fittizio e gira **anche sulle pull request**, dove il build vero è
  escluso. Senza, un errore di sintassi nell'installer si scoprirebbe solo
  dopo il merge su `main`.

---

## Demo in Docker (desktop nel browser)

`docker/demo/` ospita su un server una demo che i clienti provano dal
browser, con credenziali distribuite da chi la gestisce. Guida operativa:
`docker/demo/README.md`. Progetto e scelte, con ciò che è stato verificato e
ciò che no: `docs/internal/2026-11-10-demo-docker-design.md`.

- **Perché il desktop e non il web:** la demo deve mostrare il prodotto che
  il cliente installerà. L'interfaccia web non copre gestione utenti, backup,
  import di massa e report PDF. Quindi l'applicazione PyQt6 gira nel
  container su uno schermo virtuale (Xvnc) e arriva al browser via WebSocket.
- **Postazioni:** una postazione è un progetto Compose con due container
  (`app`, `db`) su una rete propria; ogni cliente ne riceve una. Un solo
  proxy Caddy pubblica porte, chiede le credenziali e instrada per percorso
  (`/<nome>/`). `demo.sh` le crea, ripristina e rimuove.
- **Riuso della modalità demo:** con `FOLIARIUM_DEMO=1` l'applicazione si
  collega al database indicato da `DEMO_DB_*` ed entra da sola come utente
  `demo` (`config.py`, blocco «MODALITÀ DEMO» di `gui_main.py`). L'utente lo
  crea `sql_scripts/demo/demo_user.sql`; la password è la stessa
  dell'ingresso dal browser.
- **Unica modifica al codice del prodotto:** `db/backup._pg_tool_name`. I
  nomi degli strumenti PostgreSQL erano scritti con `.exe`, che fuori da
  Windows non esiste.

Cose non ovvie, da non «semplificare»:

- **`docker/postgres/init.sh`** applica gli stessi script di
  `setup_database.SQL_SCRIPTS`, nello stesso ordine: l'elenco è duplicato e
  `test_docker_db_init.py` fallisce se i due divergono. Ogni script è
  applicato una volta sola e il primo errore ferma l'inizializzazione: è
  ciò che fa emergere subito uno script fuori posto. Variabili:
  `FOLIARIUM_ADMIN_PASSWORD` crea l'utente admin, `FOLIARIUM_DEMO_PASSWORD`
  crea `demo` e carica l'archivio.
- **`avvio.sh` attende il database prima di ogni lancio.** In demo, se la
  connessione fallisce, l'applicazione mostra un errore modale e aspetta un
  clic che su un server nessuno darà. Il programma viene rilanciato quando
  termina; `controllo-salute.sh` considera non sana anche una postazione il
  cui processo esiste ma mostra un errore «Demo — …».
- **`DB_SSLMODE=prefer`** nell'immagine: per un host diverso da localhost
  `_resolve_sslmode` impone `require`, ma il database della postazione è un
  container sulla stessa macchina, senza certificati.
- **Portachiavi su file** (`keyrings.alt`): il backup cifrato è l'opzione
  predefinita e tiene la chiave nel portachiavi di sistema, che in un
  container non c'è.
- **Il WebSocket dello schermo non chiede le credenziali Basic**: Safari
  storicamente non le invia in quella connessione. Lo protegge un token nel
  percorso, che la pagina riceve da `sessione.json` solo dopo essersi
  autenticata (funzione `frammento` in `demo.sh`).
- **Configurazione del proxy con soli blocchi `handle`:** Caddy ordina le
  direttive per tipo prima che per percorso, e mescolarle a `handle_path`
  farebbe vincere una regola generica su una specifica.
- **Schermo remoto minimo 1280×960** (`web/schermo.js`): sotto i 960 pixel
  di altezza la pagina iniziale comprime i pulsanti fino a renderli
  illeggibili. In una finestra più piccola lo schermo viene rimpicciolito.
  Per farlo si sostituisce un metodo interno di noVNC 1.3; se mancasse,
  resta il comportamento originale.
- **`postazioni/` e `proxy/` sono cartelle distinte:** la prima contiene le
  password in chiaro; la seconda, l'unica che il proxy monta, ne contiene
  solo gli hash. **Ma contiene in chiaro il token dello schermo**, che per lo
  schermo vale quanto la password: nessuna delle due è leggibile da altri
  utenti (700/600 e 750/640). Il proxy gira senza capability e legge i
  frammenti perché riceve come gruppo quello di chi esegue `demo.sh`
  (`group_add`): non vanno resi leggibili a tutti per «farlo funzionare».
- **`ripristina` conserva le credenziali, `ripristina --nuove-credenziali`
  le cambia.** La seconda forma serve quando la postazione passa a un altro
  cliente: chi l'ha usata conosce password e token, e rientrerebbe nella
  sessione di chi viene dopo.
- **In `cmd_crea` ogni passo è seguito da `|| annulla_creazione`**, e
  `_proxy_su` esce sempre con `return`. Una `trap ERR` non basta: senza
  `set -E` non vale dentro le funzioni chiamate, e con `set -E` leggerebbe
  la variabile locale `nome` di `_proxy_su`, che scorre le altre postazioni.
- **Limiti di CPU calcolati da `demo.sh`:** Docker rifiuta un limite
  superiore ai processori presenti, quindi il predefinito non può stare
  scritto nel file Compose.
- **`Dockerfile.dockerignore` è una lista di ammissione** e i moduli in
  radice sono copiati per elenco: `generate_key.py` e `generate_license.py`
  non devono entrare in un'immagine pubblica. Un modulo nuovo in radice va
  aggiunto al `COPY`.
- **Negli script con `pipefail` mai `comando | grep -q`:** grep esce al
  primo riscontro, il comando a monte riceve SIGPIPE e la pipe risulta
  fallita anche se il testo c'era. In CI una verifica falliva così con la
  finestra a schermo; un test lo vieta.

**Prova:** `bash docker/demo/prova.sh` crea due postazioni vere, esegue
sedici verifiche (con un browser vero se c'è Playwright) e toglie tutto. Usa
`DEMO_PREFISSO=foliarium-prova` e una cartella dati temporanea, quindi non
tocca postazioni esistenti. Il workflow `demo_docker.yml` la esegue a ogni
pull request e pubblica le immagini dello schermo come artefatto.

**Build dietro un proxy in uscita** (sessioni cloud): entrambi i Dockerfile
accettano `BASE_IMAGE`, e `demo.sh costruisci` aggiunge alle build
`DEMO_BUILD_OPZIONI_DB` / `DEMO_BUILD_OPZIONI_APP`. Nulla di questo va
scritto nei file versionati.

---

## Test suite

```
tests/
├── conftest.py                    # pytest fixtures (db_manager, clean_db, sample_data)
├── test_basic.py
├── unit/                          # Unit tests (pytest -m unit)
│   ├── test_validators_exceptions.py   # 474 LOC, validators centralizzati
│   ├── test_db_*.py                    # mixin DB (comuni, partite, possessori, ricerca)
│   ├── test_db_base_audit_view.py      # _ensure_audit_view (auto-apply vista)
│   ├── test_db_base_audit_fk.py        # _ensure_audit_user_fk (chiave esterna audit → utente)
│   ├── test_setup_database.py          # helper dell'installer: log, psql rigoroso/tollerante
│   ├── test_license_manager.py         # LicenseManager + HMAC
│   ├── test_theme.py                   # foliarium/ui/theme.py (post-Sprint 3.5)
│   ├── test_login_flow.py              # foliarium/ui/login_flow.py (post-Sprint 3.6)
│   ├── test_startup.py                 # foliarium/ui/startup.py (post-Sprint 3.7)
│   ├── test_demo_launcher.py, test_update_checker.py, test_email_service.py
│   ├── test_widget_modules.py          # smoke test re-export facade
│   ├── test_ui_feedback.py             # campi obbligatori, tooltip sidebar,
│   │                                   # formati data, aiuto contestuale,
│   │                                   # ricerca manuale, accessibilità (Sprint 4)
│   ├── test_spec_manuale.py            # foliarium.spec impacchetta docs/*.md +
│   │                                   # mkdocs.yml, senza docs/internal/
│   ├── test_error_messages.py          # traduzione SQLSTATE → italiano (Sprint 4)
│   ├── test_unsaved_and_shortcuts.py   # UnsavedFormMixin, scorciatoie,
│   │                                   # cronologia Alt+←, import con Annulla
│   ├── test_undo_and_drafts.py         # annullamento, bozze dei moduli,
│   │                                   # regressioni eventFilter / singleton
│   ├── test_backup_executables.py      # nomi degli strumenti PostgreSQL per piattaforma
│   ├── test_docker_db_init.py          # init.sh ↔ setup_database.SQL_SCRIPTS
│   └── test_demo_*.py                  # demo in Docker: demo.sh e configurazione del proxy,
│                                       # pagina dei file, anteprima PDF, esempi di import
└── integration/                   # Integration tests (pytest -m integration)
    ├── test_e2e.py                     # E2E DB layer (richiede Postgres live)
    ├── test_gui_smoke.py               # smoke widget GUI via pytest-qt
    ├── test_gui_widgets.py
    ├── test_schema_database_nuovo.py   # SQL_SCRIPTS su un database vuoto, con la
    │                                   # funzione dell'installer e ON_ERROR_STOP;
    │                                   # sanatoria della chiave esterna di audit
    └── test_golden_path.py             # E2E headless del flusso critico
                                        # comune → possessore → partita →
                                        # variazione → export PDF (Sprint 2)
```

**Dipendenze dei test:** oltre a `requirements.txt` servono `pytest`,
`pytest-qt`, `pytest-cov` e le librerie Qt di sistema (`libegl1`, `libgl1`,
`libxkbcommon0`, `libdbus-1-3`, `libfontconfig1` su Debian/Ubuntu). Senza
`fastapi` e `mcp` i test di `test_api_*.py` e `test_mcp_server.py` falliscono
con `ModuleNotFoundError`: è un problema d'ambiente, non del codice.

**Pytest markers:**
- `unit` — unit test puri (rapidi)
- `integration` — richiedono DB live e/o GUI
- `gui` — richiedono `QApplication` (QT_QPA_PLATFORM=offscreen in CI)
- `slow` — test lenti (esclusi da run rapidi)
- `golden_path` — happy-path da proteggere assolutamente da regressioni

**Coverage** (`pytest.ini` + `.coveragerc`):
i file GUI (`gui_main`, `gui_widgets`, `search_widgets`, `partita_workflow_widgets`,
`dialogs`) sono **esclusi** dal `--cov` perché richiedono interazione utente +
DB live e i numeri risulterebbero fuorvianti. La coverage misurata copre
`db/`, `core/`, `validators.py`, `app_utils.py`, `foliarium/` e moduli simili.

---

## Qualità del prodotto

`docs/qualita/iso25010.md` — autovalutazione rispetto alle 8 caratteristiche
del modello **ISO/IEC 25010:2011**, con evidenze puntuali (file, test,
funzioni) e un elenco esplicito delle lacune. Serve per le griglie tecniche
delle gare pubbliche e come preparazione a un'eventuale valutazione
**ISO/IEC 25051** (l'unico standard della famiglia su cui esiste una
certificazione di prodotto: 25010 è un modello, non uno schema certificabile).

Il documento cita numeri rilevati a una data precisa (copertura, numero di
test, righe di codice): **vanno rimisurati a ogni revisione, non copiati.**
Le lacune dichiarate al §9 — fra cui l'assenza di un test del ciclo
backup → restore e di misure di prestazioni — sono parte del documento:
toglierle senza averle colmate lo renderebbe inutilizzabile.

`docs/qualita/iso9241-110.md` — autovalutazione rispetto ai sette **principi
di interazione della ISO 9241-110:2020**: la formulazione normativa degli
stessi concetti che le euristiche di Nielsen esprimono in modo informale.
Sta *dentro* la casella "Usabilità" della 25010 e la riempie di dettaglio.
Due principi restano `◐` — adeguatezza al compito e coinvolgimento — per
la stessa ragione: **si verificano solo con utenti reali**, nessun lavoro
sul codice li porta a presidiati. Il documento dichiara inoltre che la
**9241-210** (progettazione centrata sull'utente) non è applicata: è una
norma di processo e servirebbero le evidenze del ciclo, che non esistono.

`docs/qualita/contesto-uso.md` — contesto d'uso secondo **ISO 9241-11**:
utenti, obiettivi, compiti, risorse, ambiente. È **deliberatamente
incompleto** e marca ogni voce come ▣ derivata dal codice o ◻ ipotesi non
rilevata. Le ◻ non vanno cancellate per far sembrare il documento
completo: sono l'elenco esatto di ciò che non si sa, e il §7 contiene la
traccia di intervista che le converte. Colmare questa lacuna sblocca gli
altri documenti: senza contesto d'uso rilevato, due principi della
9241-110 non possono superare `◐`, la 9241-210 non è applicabile e la
descrizione del prodotto per la 25051 non è verificabile.

Vale per tutti e tre i documenti: la denominazione dei principi va allineata
al testo della norma acquistata prima di qualsiasi uso formale, e i
conteggi vanno rimisurati con i pattern dichiarati. Alla stesura del
documento 9241 tre numeri del 25010 (classi `QThread`, usi di `SAVEPOINT`,
punti di `rollback`) si sono rivelati imprecisi e sono stati corretti in
entrambi: è esattamente il motivo per cui i numeri non vanno copiati.

---

## PyInstaller paths (onedir bundle)

In a PyInstaller `onedir` bundle there are two distinct roots:

| Tipo di file | Dove si trova | Costante |
|---|---|---|
| Risorse bundled (icone, .qss, .md, .svg) | `_internal/` | `BASE_DIR` (`app_paths.BASE_DIR`) |
| File utente / installer (`config.ini`, `.license`) | Accanto all'exe | `EXE_DIR` (`app_paths.EXE_DIR`) |
| Dati scrivibili (log, cache, esportazioni) | `%LOCALAPPDATA%\Foliarium` | `APP_DATA_DIR` |

`app_paths.get_exe_dir()` returns `Path(sys.executable).parent` when frozen, `Path(__file__).parent` otherwise.

---

## License Management

### HMAC-SHA256 Key (`foliarium.key`)

The license system signs `.license` files with HMAC-SHA256. The signing key is loaded from:

1. **Environment variable** `FOLIARIUM_LICENSE_KEY` (priority)
2. **File** `foliarium.key` next to `Foliarium.exe` (EXE_DIR)

**Generate the key:**

```bash
# Interactive menu (recommended)
python generate_key.py

# Auto-save next to exe
python generate_key.py --save-exe-dir

# Print HEX value only (for env vars)
python generate_key.py --env-var
```

**Security rules:**

- ✅ Generate **once per environment** (dev, staging, prod)
- ✅ Store in secure location (env var or restricted file)
- ✅ **Never commit** `foliarium.key` to Git (add to `.gitignore`)
- ✅ Backup securely (if lost, all `.license` files become invalid)
- ❌ Never hardcode the key in source code
- ❌ Never share via email/chat

**If compromised:**

- Generate a new key immediately
- All existing `.license` files must be re-signed with the new key
- Notify clients to update their license files

### License File Generation

```bash
# Generate a .license file for a client
python generate_license.py generate \
    --to "Archivio di Stato di Savona" \
    --type standard \
    --seats 2 \
    --expiry 2027-12-31 \
    --out savona.license
```

**License types:** `demo`, `standard`, `enterprise`

The `.license` file is JSON-signed (signature field is HMAC-SHA256 of all other fields).

`LicenseManager.validate()` verifies:
- Signature validity
- Hardware ID match (if bound to a specific machine)
- Expiry date
- Network seat limits (concurrent instances)
