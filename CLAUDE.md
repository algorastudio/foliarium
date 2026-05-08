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
├── gui_main.py                   # Entry point — QMainWindow, app init, TopBarWidget, SidebarWidget
├── gui_widgets.py                # Facade UI — ElencoComuniWidget, DashboardWidget, WelcomeScreen + re-export hub
├── search_widgets.py             # Widget ricerca — RicercaPartiteWidget, RicercaAvanzataImmobiliWidget, UnifiedFuzzySearchWidget
├── partita_workflow_widgets.py   # Widget workflow — RegistrazioneProprietaWidget, NuovaPartitaWizardWidget, OperazioniPartitaWidget
├── dialogs.py                    # Facade di re-export dialogs (implementati in foliarium/ui/dialogs/)
├── catasto_db_manager.py         # Facade DB — delega al package db/
├── app_utils.py                  # PDF classes, export helpers, preview dialogs
├── app_paths.py                  # Path resolution & resource loading
├── config.py                     # Costanti, logging, APP_VERSION
├── validators.py                 # Validatori campi form
│
├── foliarium/                    # Package principale (servizi + UI estratti)
│   ├── core/services/            # email.py, license.py, update_checker.py, demo_launcher.py
│   └── ui/                       # top_bar.py, sidebar.py, command_palette.py, splash.py
│       ├── dialogs/              # entity.py, admin.py (+ LoginDialog), partita.py, import_.py, export_.py
│       └── widgets/              # admin.py (GestioneUtenti, Archivio, TipiPossesso)
│                                 # insertion.py (Comune, Possessore, Localita, Partita)
│                                 # reporting.py (Documenti, Esportazioni, Reportistica, Statistiche)
│                                 # custom.py (widget condivisi, show_status_message)
│
├── db/                           # Database layer — 14 mixin via ereditarietà multipla
│   ├── base.py                   # DBConnectionBase: pool, _get_connection(), bulk_insert
│   ├── comuni.py, localita.py, possessori.py, partite.py, immobili.py
│   ├── variazioni.py, documenti.py, audit.py, utenti.py
│   ├── backup.py, stats.py, ricerca.py, io.py, archivio.py
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
├── styles/                       # Qt stylesheets (.qss) — 16 temi
├── resources/                    # Icone, immagini, EULA
├── tests/                        # Test suite (pytest)
├── docs/                         # MkDocs documentation source
├── esportazioni/                 # Output directory (PDF, CSV)
├── .devcontainer/                # Dev container config (VS Code / Codespaces)
├── .github/workflows/            # CI/CD pipeline
├── foliarium.spec                # PyInstaller build spec (produzione)
├── foliarium_demo.spec           # PyInstaller build spec (demo portabile)
├── Foliarium_Unified_Installer.iss  # Inno Setup installer unificato
├── setup_database.bat / .py      # Init DB Windows / cross-platform
├── prepare_demo_db.py            # Script CI: initdb + schema + dati demo
├── generate_license.py           # CLI: genera/ispeziona file .license
└── demo_config.ini               # Guida + credenziali DB demo
```

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

# Prepare demo_data/ locally (requires pgsql/ portable in project root)
python prepare_demo_db.py --pgsql-dir pgsql

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

- **Entry point:** `gui_main.py` creates the `QApplication` and `QMainWindow`, initialises logging (`config.setup_global_logging`), builds `TopBarWidget` + `SidebarWidget` + `QStackedWidget`, navigates with `navigate_to(page_name)`.
- **DB layer:** `catasto_db_manager.py` — `CatastoDBManager` class wraps all psycopg2 calls. Credentials are read from env vars (`DB_HOST`, `DB_USER`, `DB_PASS`, `DB_NAME`, `DB_PORT`) with fallback to defaults defined in `config.py`.
- **CI detection:** `config.IS_TEST_ENV` is `True` when `CI=true` or `GITHUB_ACTIONS=true`. Used to skip interactive prompts and adjust logging.
- **UI widget distribution** (post-refactor v1.0.0):
  - `gui_widgets.py` — facade + `ElencoComuniWidget`, `DashboardWidget`, `WelcomeScreen`
  - `search_widgets.py` — `RicercaPartiteWidget`, `RicercaAvanzataImmobiliWidget`, `UnifiedFuzzySearchWidget`
  - `partita_workflow_widgets.py` — `RegistrazioneProprietaWidget`, `NuovaPartitaWizardWidget`, `OperazioniPartitaWidget`
  - `foliarium/ui/widgets/insertion.py` — form inserimento (Comune, Possessore, Località, Partita)
  - `foliarium/ui/widgets/admin.py` — `GestioneUtentiWidget`, `AuditLogViewerWidget`, `BackupWidget`, `TipiPossessoWidget`, `ArchivioWidget`
  - `foliarium/ui/widgets/reporting.py` — `RicercaDocumentiWidget`, `EsportazioniWidget`, `ReportisticaWidget`, `StatisticheWidget`
- **Themes:** QSS stylesheets in `styles/`. Loaded at runtime; 16 themes available (dark, light, business, ocean, nature, etc.).

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

---

## Dev container (VS Code / Codespaces)

```
noVNC desktop  → http://localhost:6080  (password: meridiana)
PostgreSQL     → localhost:5432
QT_QPA_PLATFORM=xcb  (set automatically inside container)
```

Run `bash .devcontainer/setup.sh` to initialise the DB and install dependencies after container creation.

---

## CI/CD (GitHub Actions)

Pipeline: `.github/workflows/pipeline_foliarium.yml`

1. **Test job** (Ubuntu): spins up PostgreSQL 14, installs Qt6 system libs, runs pytest with `QT_QPA_PLATFORM=offscreen`, captures GUI screenshots as artifacts.
2. **Build job** (Windows, only if tests pass): runs PyInstaller, creates portable ZIP and Inno Setup installer, uploads as artifacts.

---

## Test suite

```
tests/
├── conftest.py                    # pytest fixtures (DB connection)
├── test_basic.py
├── unit/                          # Unit tests (pytest -m unit)
└── integration/                   # Integration tests (pytest -m integration)
```

Pytest markers: `slow`, `integration`, `gui`, `unit`.

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
