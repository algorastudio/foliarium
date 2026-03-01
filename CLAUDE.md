# CLAUDE.md — Meridiana · Archivio Catastale Storico

## Project overview

**Meridiana** is a desktop application for managing historical Italian cadastral records (archivio catastale storico), developed for the State Archive of Savona. It allows archivists to search, insert, and export property records (partite catastali) and owners (possessori).

- **Current version:** 1.3.0.0
- **Author:** Marco Santoro
- **Primary platform:** Windows 10+
- **Code/UI language:** Italian

---

## Tech stack

| Layer | Technology |
|---|---|
| Language | Python 3.12 |
| GUI | PyQt6 6.8.1 + PyQt6-WebEngine |
| Database | PostgreSQL 14+ |
| DB driver | psycopg2-binary 2.9.10 |
| Data | pandas 2.3, numpy 2.3, openpyxl 3.1.5 |
| PDF export | fpdf2 2.8.3 |
| Auth/security | bcrypt 4.3.0, keyring 25.6.0 |
| Build | PyInstaller (`meridiana.spec`) + Inno Setup |
| CI/CD | GitHub Actions |
| Docs | MkDocs (Material theme) |

---

## Project structure

```
catasto/
├── gui_main.py              # Entry point — QMainWindow, app init
├── gui_widgets.py           # All main UI panels/widgets (largest file)
├── dialogs.py               # Dialog windows
├── catasto_db_manager.py    # Database layer (CatastoDBManager class)
├── app_utils.py             # PDF/report utilities
├── app_paths.py             # Path resolution & resource loading
├── config.py                # App config, logging, env-var DB credentials
├── custom_widgets.py        # Reusable custom PyQt6 widgets
├── sql_scripts/             # PostgreSQL DDL, stored procedures, init scripts
├── styles/                  # Qt stylesheets (.qss) — 16 themes
├── resources/               # Icons, images, EULA
├── tests/                   # Test suite (pytest)
├── docs/                    # MkDocs documentation source
├── esportazioni/            # Export output directory (PDFs, CSVs)
├── .devcontainer/           # Dev container config (VS Code / Codespaces)
├── .github/workflows/       # CI/CD pipeline
├── meridiana.spec           # PyInstaller build spec
└── Meridiana_Installer.iss  # Inno Setup installer script
```

---

## Key commands

```bash
# Run the application
python gui_main.py

# Run all tests
pytest

# Run by marker
pytest -m unit
pytest -m integration
pytest -m "not gui"          # skip GUI tests (e.g. in headless env)

# Build Windows executable
pyinstaller meridiana.spec

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

- **Entry point:** `gui_main.py` creates the `QApplication` and `QMainWindow`, initialises logging (`config.setup_global_logging`), and loads the main window with panels from `gui_widgets.py`.
- **DB layer:** `catasto_db_manager.py` — `CatastoDBManager` class wraps all psycopg2 calls. Credentials are read from env vars (`DB_HOST`, `DB_USER`, `DB_PASS`, `DB_NAME`, `DB_PORT`) with fallback to defaults defined in `config.py`.
- **CI detection:** `config.IS_TEST_ENV` is `True` when `CI=true` or `GITHUB_ACTIONS=true`. Used to skip interactive prompts and adjust logging.
- **UI panels** (all in `gui_widgets.py`): DashboardWidget, RicercaPartiteWidget, RicercaAvanzataImmobiliWidget, InserimentoPossessoreWidget, EsportazioniWidget, ReportisticaWidget, GestioneUtentiWidget, AuditLogViewerWidget, BackupWidget.
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

This was a recurring issue fixed in commits `4ef1d7a` and `0ca39e0`. Always use the full three-part path `Module.EnumClass.Value`.

---

## Database

- **DB name:** `catasto_storico`
- **Default user:** `postgres`
- **Schema:** `public` (configurable via `SETTINGS_DB_SCHEMA`)
- Passwords are **not** stored in QSettings — keyring is used for secure storage.
- Init SQL scripts are in `sql_scripts/`; run them in order to initialise a fresh DB.

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

Pipeline: `.github/workflows/pipeline_meridiana.yml`

1. **Test job** (Ubuntu): spins up PostgreSQL 14, installs Qt6 system libs, runs pytest with `QT_QPA_PLATFORM=offscreen`, captures GUI screenshots as artifacts.
2. **Build job** (Windows, only if tests pass): runs PyInstaller, creates portable ZIP and Inno Setup installer, uploads as artifacts.

---

## Test suite

```
tests/
├── conftest.py                    # pytest fixtures (DB connection)
├── test_basic.py
├── catasto-test-database.py       # DB connection tests
├── catasto-test-gui.py            # GUI component tests
├── catasto-test-integration.py    # End-to-end integration tests
├── catasto-test-runner.py         # Test orchestration
├── take_screenshots.py            # CI screenshot capture
├── unit/                          # Unit tests
└── integration/                   # Integration tests
```

Pytest markers: `slow`, `integration`, `gui`, `unit`.
