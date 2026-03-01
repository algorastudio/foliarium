# CLAUDE.md — Meridiana · Archivio Catastale Storico

## Project overview

**Meridiana** is a desktop application for managing historical Italian cadastral records (archivio catastale storico), developed for the State Archive of Savona. It allows archivists to search, insert, and export property records (partite catastali) and owners (possessori).

- **Current version:** 1.3.1.0
- **Author:** Marco Santoro
- **Primary platform:** Windows 10+
- **Code/UI language:** Italian

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

---

## Changelog sessione corrente (v1.3.0.0)

Tutto il lavoro è sul branch `claude/summarize-dev-status-vDVnI`.

### Migrazione PyQt6 completata
- Corretti **tutti** gli enum non-namespaced in `gui_widgets.py`, `dialogs.py`, `catasto_db_manager.py`, `app_utils.py`, `tests/catasto-test-gui.py` (>80 istanze)
- Pattern fisso: `Qt.AlignLeft` → `Qt.AlignmentFlag.AlignLeft`, `QTableWidget.NoEditTriggers` → `QAbstractItemView.EditTrigger.NoEditTriggers`, ecc.
- `QStyleFactory` è in `PyQt6.QtWidgets`, **non** in `PyQt6.QtGui`

### Nuove feature introdotte

**1. Auto dark/light mode** (`gui_main.py`, `config.py`)
- Menu *Impostazioni → Cambia Tema Grafico → Tema Automatico (Segue Sistema)*
- Usa `QGuiApplication.styleHints().colorScheme()` + segnale `colorSchemeChanged`
- Costanti: `SETTINGS_UI_AUTO_THEME`, `AUTO_THEME_DARK="dark_mode_stylesheet.qss"`, `AUTO_THEME_LIGHT="meridiana_styles.qss"`

**2. Stile nativo Windows 11** (`gui_main.py`, `config.py`)
- Menu *Impostazioni → Cambia Tema Grafico → Stile Nativo Windows 11*
- Appare solo se `"windows11" in QStyleFactory.keys()` (Qt 6.7+)
- `app.setStyle("windows11")` + pulizia QSS; `_reset_app_style()` ripristina Fusion prima di applicare QSS
- Costante: `SETTINGS_UI_WIN11_STYLE`; le 3 modalità (Win11/Auto/QSS) si escludono a vicenda

**3. HiDPI audit** (`gui_widgets.py`, `dialogs.py`, `gui_main.py`)
- Rimossi tutti i `setFixed*` (19 istanze) → sostituiti con `setMinimum*`
- `WelcomeScreen`: `setFixedSize(1024,768)` → `setMinimumSize(800,600)` + `resize(1024,768)`
- `QSplitter.setSizes([N,M])` → `setStretchFactor()` proporzionale

**4. QPdfDocument sostituisce WebEngine** (`dialogs.py`)
- `DocumentViewerDialog._load_pdf()` usa `QPdfDocument` + `QPdfView` con toolbar zoom (−/+/Adatta)
- WebEngine commentato in `requirements.txt` (risparmio ~80 MB installer)
- `WEB_ENGINE_AVAILABLE` flag in `gui_widgets.py` e `custom_widgets.py` per uso futuro web

**5. Logo SVG** (`app_paths.py`, `gui_main.py`, `gui_widgets.py`)
- `get_logo_svg_path(dark=False)` in `app_paths.py` → `"logo meridiana.svg"` o `"meridiana_dark.svg"`
- `WelcomeScreen` usa `QSvgWidget` (sempre nitido su HiDPI), fallback PNG se QtSvgWidgets non disponibile
- Logo scelto automaticamente in base al tema dark/light del sistema

---

## Changelog sessione corrente (v1.3.1.0)

Tutto il lavoro è sul branch `claude/summarize-dev-status-vDVnI`.

### Feature: Import comuni e località da CSV / ISTAT

**`catasto_db_manager.py`**
- `import_comuni_from_rows(rows: List[Dict]) -> Dict` — batch insert comuni con SAVEPOINT per riga; campi obbligatori: nome, provincia, regione; opzionali: codice_catastale, data_istituzione, data_soppressione, note
- `import_localita_from_rows(comune_id, rows: List[Dict]) -> Dict` — batch insert località; risolve tipo (stringa) → tipo_id via lookup in-memory; fallback su "Altro"

**`dialogs.py`**
- `ISTATDownloadWorker(QThread)` — scarica CSV ISTAT ufficiale in background (`urllib.request`), mappa colonne → schema locale, filtro per sigla provincia
- `ImportComuniDialog` — due tab: *Da file CSV* (template scaricabile, preview 20 righe, import) e *Da ISTAT* (download con progress bar, preview, import)
- `ImportLocalitaDialog` — selezione comune da ComboBox, template CSV scaricabile, preview, import
- `_mostra_risultati_import()` — helper per dialog riepilogo successi/errori

**`gui_main.py`**
- 2 nuove voci menu *File*: "Importa Comuni da CSV/ISTAT..." e "Importa Località da CSV..."
- Handler `_import_comuni()` (con refresh `ElencoComuniWidget`) e `_import_localita()`

### Feature: Albero genealogico partita (v1.3.2.0)

**`catasto_db_manager.py`**
- `get_genealogia_partita(partita_id) -> Dict` — 3 query: partita centrale, predecessori (variazione.partita_destinazione_id), successori (variazione.partita_origine_id)

**`dialogs.py`**
- `AlberoGeneralogicoDialog` — QTreeWidget 5 colonne, QSplitter con QTextBrowser dettaglio, colori differenziati root/predecessori/successori, pulsante "Apri Report Testo"
- `PartitaDetailsDialog`: pulsante "Albero Genealogico" + handler `_apri_albero_genealogico()`

**`gui_widgets.py`**
- `ReportisticaWidget`: bottone "Visualizza Albero Genealogico" affiancato a "Genera Report Genealogico", handler `_apri_albero_genealogico()`

---

## Roadmap v1.4 (da "Feature proposte per Meridiana v1.4.pdf")

### Alta priorità
- [x] **1. Albero genealogico proprietà** — implementato in v1.3.2.0
- [x] **2. Export Excel avanzato** — bottone "Archivio Completo (.xlsx)" in `EsportazioniWidget`; handler `_handle_export_xlsx_completo()` con `pd.ExcelWriter` + 4 fogli (Partite, Possessori, Immobili, Variazioni)
- [ ] **3. Ricerca full-text documenti storici** — `search_historical_documents()` esiste nel DB manager; creare `RicercaDocumentiWidget` con filtri tipo/data/parole chiave

### Media priorità
- [ ] **4. Import partite da Excel (.xlsx)** — estendere `import_partite_from_csv` con supporto `.xlsx` via `openpyxl`
- [ ] **5. Dashboard con grafici statistici** — aggiungere grafici `QChart` (PyQt6) o `matplotlib` a `StatisticheWidget`: partite per comune, variazioni per anno, stato attivo/chiuso
- [ ] **6. Confronto versioni partita** — diff visuale (verde/rosso) tra due periodi storici: immobili aggiunti/rimossi, cambio possessori

### Bassa priorità
- [ ] **7. Modalità offline/cache** — SQLite o JSON locale quando DB non raggiungibile
- [ ] **8. Test coverage report** — completare marker `unit`/`integration`, aggiungere `pytest-cov`, badge README
- [ ] **9. Export report ODT** — alternativa PDF con `odfpy` per documenti modificabili

---

### Note tecniche
- Venv progetto in `U:/catasto/.venv/` (Python 3.13)
- Per abilitare Long Paths su Windows serve privilegi admin; alternativa: usare Python da percorso corto `C:\Python312\`
- Terminale integrato VS Code: impostare "Command Prompt" come default (`terminal.integrated.defaultProfile.windows`)
