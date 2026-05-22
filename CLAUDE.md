# CLAUDE.md — Foliarium · Archivio Catastale Storico

## Project overview

**Foliarium** is a desktop application for managing historical Italian cadastral records (archivio catastale storico). It allows archivists to search, insert, and export property records (partite catastali) and owners (possessori).

- **Current version:** 1.0.1
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
│   ├── core/services/            # email.py, license.py, update_checker.py, demo_launcher.py
│   ├── reporting/                # PDF reports (post-refactor Sprint 3.1)
│   │   └── pdf.py                # ModernCatastoPDF + PDFPartita/Possessore/Generic/Bulk
│   └── ui/
│       ├── top_bar.py, sidebar.py, command_palette.py, splash.py, effects.py
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
│           ├── custom.py         # Widget condivisi, show_status_message, LazyLoadedWidget
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
│   ├── drafts.py                 # DBDraftsMixin (bozze wizard Nuova Partita + Registrazione Proprietà)
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
- **DB layer:** `catasto_db_manager.py` — facade thin che eredita dai mixin in `db/`. `CatastoDBManager` espone tutti i metodi CRUD. Credentials are read from env vars (`DB_HOST`, `DB_USER`, `DB_PASS`, `DB_NAME`, `DB_PORT`) with fallback to defaults defined in `config.py`. Se la password manca in produzione, `config.assert_db_password_configured()` solleva `RuntimeError` invece di tentare un login silenzioso con password vuota.
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
- **Themes:** QSS stylesheets in `styles/`. Funzioni pure in `foliarium/ui/theme.py`: `apply_stylesheet`, `apply_auto_theme`, `apply_initial_theme_from_settings`, `is_win11_style_available`.

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
- **Auto-apply migrazioni idempotenti:** `db/base.py::_apply_pending_schema_migrations()` viene invocata a ogni init pool e applica silenziosamente migrazioni sicure (es. schema v1.6.1, indici UNIQUE sulle MV, vista `v_audit_dettagliato` — equivalente di `migrations/19_create_v_audit_dettagliato.sql`, tabella `partita_draft` — equivalente di `migrations/21_create_partita_draft.sql`). Best-effort, non bloccante.
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
│   └── test_widget_modules.py          # smoke test re-export facade
└── integration/                   # Integration tests (pytest -m integration)
    ├── test_e2e.py                     # E2E DB layer (richiede Postgres live)
    ├── test_gui_smoke.py               # smoke widget GUI via pytest-qt
    ├── test_gui_widgets.py
    └── test_golden_path.py             # E2E headless del flusso critico
                                        # comune → possessore → partita →
                                        # variazione → export PDF (Sprint 2)
```

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
