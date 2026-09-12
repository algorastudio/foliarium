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
├── .devcontainer/                # Dev container config (VS Code / Codespaces)
├── .github/workflows/            # CI/CD pipeline
├── foliarium.spec                # PyInstaller build spec (produzione)
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
- **Auto-apply migrazioni idempotenti:** `db/base.py::_apply_pending_schema_migrations()` viene invocata a ogni init pool e applica silenziosamente migrazioni sicure (es. schema v1.6.1, indici UNIQUE sulle MV, vista `v_audit_dettagliato` — equivalente di `migrations/19_create_v_audit_dettagliato.sql`, tabella `partita_draft` — equivalente di `migrations/21_create_partita_draft.sql`, tabella `api_keys` — equivalente di `migrations/22_create_api_keys.sql`). Best-effort, non bloccante.

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

## Test suite

```
tests/
├── conftest.py                    # pytest fixtures (db_manager, clean_db, sample_data)
├── test_basic.py
├── unit/                          # Unit tests (pytest -m unit)
│   ├── test_validators_exceptions.py   # 474 LOC, validators centralizzati
│   ├── test_db_*.py                    # mixin DB (comuni, partite, possessori, ricerca)
│   ├── test_db_base_audit_view.py      # _ensure_audit_view (auto-apply vista)
│   ├── test_license_manager.py         # LicenseManager + HMAC
│   ├── test_theme.py                   # foliarium/ui/theme.py (post-Sprint 3.5)
│   ├── test_login_flow.py              # foliarium/ui/login_flow.py (post-Sprint 3.6)
│   ├── test_startup.py                 # foliarium/ui/startup.py (post-Sprint 3.7)
│   ├── test_demo_launcher.py, test_update_checker.py, test_email_service.py
│   ├── test_widget_modules.py          # smoke test re-export facade
│   ├── test_ui_feedback.py             # campi obbligatori, tooltip sidebar,
│   │                                   # formati data, aiuto contestuale,
│   │                                   # ricerca manuale, accessibilità (Sprint 4)
│   ├── test_error_messages.py          # traduzione SQLSTATE → italiano (Sprint 4)
│   ├── test_unsaved_and_shortcuts.py   # UnsavedFormMixin, scorciatoie,
│   │                                   # cronologia Alt+←, import con Annulla
│   └── test_undo_and_drafts.py         # annullamento, bozze dei moduli,
│                                       # regressioni eventFilter / singleton
└── integration/                   # Integration tests (pytest -m integration)
    ├── test_e2e.py                     # E2E DB layer (richiede Postgres live)
    ├── test_gui_smoke.py               # smoke widget GUI via pytest-qt
    ├── test_gui_widgets.py
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
