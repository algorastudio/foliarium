# CLAUDE.md — Foliarium · Archivio Catastale Storico

## Project overview

**Foliarium** is a desktop application for managing historical Italian cadastral records (archivio catastale storico), developed for the State Archive of Savona. It allows archivists to search, insert, and export property records (partite catastali) and owners (possessori).

- **Current version:** 1.6.0 (versione definitiva)
- **Author:** Marco Santoro
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
| Build | PyInstaller (`meridiana.spec`) + Inno Setup |
| CI/CD | GitHub Actions |
| Docs | MkDocs (Material theme) |

---

## Project structure

```
catasto/
├── gui_main.py              # Entry point — QMainWindow, app init
├── gui_widgets.py           # Main UI panels/widgets (re-export facade)
├── insertion_widgets.py     # Widget inserimento: Comune, Possessore, Località, Partita
├── admin_widgets.py         # Widget admin: Utenti, Audit, Backup, TipiLocalità, Periodi
├── reporting_widgets.py     # Widget report: Documenti, Esportazioni, Reportistica, Statistiche
├── import_dialogs.py        # Dialog import CSV/ISTAT/OSM per Comuni e Località
├── dialogs.py               # Dialog windows (tutti gli altri dialog)
├── catasto_db_manager.py    # Database layer — facade per il package db/
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
├── foliarium_demo.spec      # PyInstaller spec versione demo (include PG portabile)
├── Meridiana_Installer.iss  # Inno Setup installer script
├── demo_launcher.py         # Avvia/ferma PostgreSQL portabile (solo demo)
├── prepare_demo_db.py       # Script CI: initdb + schema + dati demo
├── demo_config.ini          # Credenziali DB demo + guida inizializzazione
├── license_manager.py       # Gestione licenze (fingerprint, validazione, seat rete)
├── generate_license.py      # CLI utility: genera/ispeziona file .license
└── update_checker.py        # Verifica e download automatico aggiornamenti
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

# Prepare demo_data/ locally (requires pgsql/ portable in project root)
python prepare_demo_db.py --pgsql-dir pgsql

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
- [x] **3. Ricerca full-text documenti storici** — `RicercaDocumentiWidget` in `gui_widgets.py`; sub-tab "Ricerca Documenti" in Consultazione; filtri: parole chiave titolo, tipo, anno da/a, ID partita

### Media priorità
- [x] **4. Import partite da Excel (.xlsx)** — `_insert_partite_records()` helper condiviso; `import_partite_from_xlsx()` legge xlsx con `openpyxl`; file dialog accetta `.csv` e `.xlsx`, smistamento per estensione
- [x] **5. Dashboard con grafici statistici** — tab "Grafici" in `StatisticheWidget` con `matplotlib` (FigureCanvasQTAgg): bar partite/comune, torta attive/inattive, bar variazioni/anno; `matplotlib>=3.9.0` aggiunto a `requirements.txt`
- [x] **6. Confronto versioni partita** — `ConfrontoPartiteDialog` in `dialogs.py`: diff visuale (verde=#C8E6C9 / rosso=#FFCDD2) su possessori e immobili; accesso da tab Genealogico in `ReportisticaWidget`

### Bassa priorità
- [x] **7. Modalità offline/cache** — `_try_with_cache()` in `CatastoDBManager`; cache JSON in `CACHE_DIR` (`%LOCALAPPDATA%/Meridiana/cache/`); wrappati `get_elenco_comuni_semplice()` e `get_statistiche_comune()`; barra rossa `offline_bar` in `gui_main.py` quando DB non raggiungibile
- [x] **8. Test coverage report** — `pytest-cov` + `pytest` aggiunti a `requirements.txt`; `pytest.ini` configurato con `--cov` su moduli principali (HTML+XML+terminal); `tests/unit/test_db_manager_unit.py` con 14 test unit per cache layer, import xlsx/csv, genealogia, app_paths (tutti green)
- [x] **9. Export report ODT** — pulsante "Esporta come ODT" in `ReportisticaWidget`; `_export_current_report_odt()` usa `odfpy` con stili titolo/corpo; `odfpy>=1.4.1` aggiunto a `requirements.txt`

---

## Changelog sessione corrente (v1.4.1.0)

Tutto il lavoro è sul branch `claude/summarize-dev-status-vDVnI`.

### Fix: Colonne CSV ISTAT (`dialogs.py`)

- Corretti i nomi colonna in `ISTATDownloadWorker`:
  - `COL_REGIONE`: `"Denominazione regione"` → `"Denominazione Regione"` (R maiuscola)
  - `COL_CODICE_CATASTALE`: `"Codice Catastale del Comune"` → `"Codice Catastale del comune"` (c minuscola)
  - `COL_PROVINCIA`: nome lunghissimo con `\n` → `"Sigla automobilistica"`

### Refactoring: rimozione duplicati e dead code (commit `refactor`)

- `app_utils.py`: rimossa prima definizione di `_get_default_export_path` (usava percorso relativo), rimossa `check_network_environment()` (mai chiamata), rimossi blocchi ridondanti `PDFPartita/PDFPossessore: pass`
- `catasto_db_manager.py`: rimossa prima definizione di `_resolve_executable_path` e prima definizione di `_search_variazioni_fuzzy_internal` (entrambi duplicati, seconda definizione è quella attiva)
- `custom_widgets.py`: rimosso import duplicato `from PyQt6.QtCore import Qt, QSettings, pyqtSlot`
- `gui_main.py`: rimosso `RicercaPartiteWidget` duplicato negli import; rimosso `from dialogs import CSVImportResultDialog, EulaDialog` duplicato
- Totale: -108 righe

### Feature: Import località da OpenStreetMap (`dialogs.py`)

- `OSMLocalitaWorker(QThread)` — interroga Overpass API (`https://overpass-api.de/api/interpreter`) con query `area["boundary"="administrative"]["admin_level"="8"]["name"="<comune>"]`; estrae strade (tag `highway`) e luoghi (tag `place`: hamlet, village, suburb, etc.); deduplica per nome; mappa tipo dalla prima parola del nome OSM
- `ImportLocalitaDialog` convertita in `QTabWidget` con 2 tab:
  - **"Da CSV"**: import da file CSV (funzionalità precedente)
  - **"Da OpenStreetMap"**: campo comune, checkbox strade/luoghi, progress bar indeterminata, preview tabella, pulsante importa
- `closeEvent` ferma il worker OSM se in esecuzione
- Tipi OSM supportati: Via, Viale, Corso, Piazza, Vicolo, Largo, Salita, Calata, Contrada, Borgata, Regione, Frazione, Strada, Traversa, Passaggio, Località

### Feature: 4 pulsanti uniformi nei widget di inserimento (`gui_widgets.py`, `gui_main.py`)

Ogni tab di inserimento ora ha 4 pulsanti in un unico `QHBoxLayout`:
**[Inserisci] [Pulisci Campi] [Importa CSV] [Scarica template]**

- **`InserimentoComuneWidget`**: aggiunto segnale `import_csv_requested = pyqtSignal()`; rimpiazzato layout a 2 pulsanti con 4; aggiunto `_scarica_template_csv()` (template: `nome;provincia;regione;codice_catastale;data_istituzione;data_soppressione;note`)
- **`InserimentoPossessoreWidget`**: rimosso QGroupBox "Azioni Aggiuntive" (import + info separati); consolidato in riga unica 4 pulsanti; aggiunto `_scarica_template_csv()` (template: `cognome_nome;nome_completo;paternita`)
- **`InserimentoLocalitaWidget`**: aggiunto segnale `import_csv_requested`; aggiunto pulsante Pulisci Campi, Importa CSV, Scarica template; aggiunti metodi `_pulisci_campi()` e `_scarica_template_csv()` (template: `nome;tipo;civico`)
- **`InserimentoPartitaWidget`**: rimosso QGroupBox "Importazione Massiva"; rimosso `manual_actions_layout` dal `form_layout`; aggiunto layout 4 pulsanti dopo `form_group`; aggiunto `_scarica_template_csv()` (template: `comune_nome;numero_partita;suffisso_partita;data_impianto;tipo_partita;numero_provenienza;stato`)
- **`gui_main.py`**: aggiunte connessioni `inserimento_comune_widget_ref.import_csv_requested.connect(self._import_comuni)` e `inserimento_localita_widget_ref.import_csv_requested.connect(self._import_localita)` (i metodi `_import_*` già esistevano)

---

### Note tecniche
- Venv progetto in `U:/catasto/.venv/` (Python 3.13)
- Per abilitare Long Paths su Windows serve privilegi admin; alternativa: usare Python da percorso corto `C:\Python312\`
- Terminale integrato VS Code: impostare "Command Prompt" come default (`terminal.integrated.defaultProfile.windows`)
- Overpass API: gratuita, nessuna chiave API richiesta; rate limit ~1 req/s; endpoint: `https://overpass-api.de/api/interpreter`

---

## Changelog sessione corrente (v1.4.2.0)

Tutto il lavoro è sul branch `claude/summarize-dev-status-vDVnI`.

### Miglioramenti UI/UX (`gui_widgets.py`, `gui_main.py`)

**Helper globali aggiunti in `gui_widgets.py`:**
- `_PROVINCE_ITALIANE` — lista 107 sigle province italiane
- `_set_field_error(widget, has_error)` — bordatura rossa CSS su campo non valido
- `_show_status_message(message, timeout_ms)` — messaggio status bar senza dipendenza circolare

**Tabelle di ricerca:**
- `RicercaPartiteWidget`: `setSortingEnabled(True)`, menu contestuale tasto destro (Apri Dettagli / Copia Numero / Copia ID), etichetta conteggio risultati, sorting guard in `do_search()`
- `RicercaAvanzataImmobiliWidget`: etichetta conteggio risultati, sorting guard
- `RicercaDocumentiWidget`: sorting abilitato, sorting guard in `_popola_tabella()`
- Sostituiti tutti i `QMessageBox.information("N risultati trovati")` con aggiornamento label

**Form di inserimento (tutti e 4 i widget):**
- Label con asterisco HTML `<b>*</b>` per campi obbligatori
- `_set_field_error` nella validazione + reset automatico `textChanged`/`currentIndexChanged`
- `QCompleter` su campo Provincia (107 sigle, case-insensitive, inline)
- `_show_status_message` al posto di `QMessageBox.information` per i successi

**Navigazione e shortcut:**
- `Ctrl+1..N` per navigare tra i tab
- `F5` per ricaricare il tab corrente (`_handle_f5_refresh`)
- Auto-focus sul primo campo quando si entra in un tab di inserimento (`_set_focus_first_field`)

### Feature: Notifiche email automatiche (`email_service.py`, `config.py`, `dialogs.py`, `gui_main.py`, `gui_widgets.py`)

**`email_service.py`** (nuovo file):
- `EmailService` — legge config da `QSettings` + password da `keyring` (`Meridiana_SMTP`); `is_configured()`, `send()`, 4 template: `notify_account_created`, `notify_password_changed`, `notify_role_changed`, `notify_login`
- `EmailWorker(QThread)` — invio email non-bloccante; segnale `result = pyqtSignal(bool, str)`
- Supporta STARTTLS (`smtplib.SMTP`) e SMTP_SSL

**`config.py`** (+10 costanti):
- `SETTINGS_SMTP_ENABLED/HOST/PORT/USER/USE_TLS/FROM_ADDR`
- `SETTINGS_EMAIL_ON_CREATE/ON_PASSWD/ON_ROLE/ON_LOGIN`

**`dialogs.py`** — `SMTPSettingsDialog`:
- QGroupBox "Server SMTP": host, porta, TLS, utente, password (QPasswordLineEdit), mittente
- QGroupBox "Notifiche attive": 4 checkbox per tipo evento
- Pulsante "Test connessione" → `EmailWorker` con feedback verde/rosso in-dialog
- `_load_settings()` da QSettings + keyring; `_save_and_accept()` salva tutto

**`gui_main.py`**:
- Voce menu *Impostazioni → Notifiche Email...* → apre `SMTPSettingsDialog`
- Notifica login in `perform_initial_setup()` (solo se `SETTINGS_EMAIL_ON_LOGIN` abilitato e utente ha email)

**`gui_widgets.py`** — `GestioneUtentiWidget`:
- `crea_nuovo_utente()` → `notify_account_created` con dati da `CreateUserDialog`
- `modifica_utente_selezionato()` → `notify_role_changed` se ruolo cambiato
- `reset_password_utente_selezionato()` → `notify_password_changed` con lookup `get_utente_by_id`
- Worker tenuto vivo con `self._email_workers` list (evita garbage collection)


---

## Changelog sessione corrente (v1.4.3.0)

Tutto il lavoro e sul branch `claude/summarize-dev-status-vDVnI`.

### Feature: Scarica CSV dati esistenti (`catasto_db_manager.py`, `gui_main.py`, `gui_widgets.py`)

Abilita il flusso completo **scarica → modifica → reimporta** per tutte e 4 le entita di inserimento.
Il CSV scaricato usa esattamente le stesse colonne del template di import (compatibilita round-trip garantita).

**`catasto_db_manager.py`** — 4 nuovi metodi:
- `get_comuni_export_csv()` — restituisce lista dict con campi `nome;provincia;regione;codice_catastale;data_istituzione;data_soppressione;note`
- `get_localita_export_csv(comune_id)` — campi `nome;tipo;civico`
- `get_possessori_export_csv()` — campi `cognome_nome;nome_completo;paternita`
- `get_partite_export_csv()` — campi `numero_partita;data_impianto;stato;tipo`

**`gui_main.py`**:
- Helper `_scarica_csv(data, fieldnames, default_filename)` — salva lista dict come CSV con `;` via QFileDialog
- Helper `_seleziona_comune_per_csv(entita)` — QInputDialog per selezione comune (usato da localita)
- 4 handler `_scarica_csv_comuni/localita/possessori/partite()`
- 4 nuove voci menu *File*: "Scarica CSV Comuni", "Scarica CSV Localita...", "Scarica CSV Possessori...", "Scarica CSV Partite..."

**`gui_widgets.py`**:
- Segnale `scarica_csv_requested` nei 4 widget di inserimento
- Pulsante "Scarica CSV" aggiunto tra "Importa CSV" e "Scarica template" (barra ora a 5 pulsanti)
- Segnali connessi agli handler di `gui_main.py`

### Feature: Manuale utente integrato (`HelpViewerDialog`) (`dialogs.py`, `app_paths.py`, `gui_main.py`, `requirements.txt`)

Viewer del manuale embedded nell'app senza WebEngine ne server MkDocs.

**`app_paths.py`**:
- `get_doc_path(relative_path=)` — risolve percorso in `DOCS_DIR` (gia definita come `BASE_DIR / docs`)

**`dialogs.py`** — `HelpViewerDialog(QDialog)`:
- `QSplitter` orizzontale: albero navigazione (sinistra) + `QTextBrowser` contenuto (destra)
- Albero costruito dalla sezione `nav` di `mkdocs.yml` tramite PyYAML; fallback a scansione ricorsiva `docs/`
- Categorie in **grassetto**, foglie con `UserRole = percorso .md relativo`
- Rendering: `markdown` lib con estensioni `tables, fenced_code, toc, admonition, nl2br` + CSS inline (stile indigo professionale)
- Navigazione back/forward con cronologia interna
- Link interni .md risolti relativamente alla pagina corrente
- Link http/https aperti in `QDesktopServices`
- `_sync_tree()` sincronizza la selezione albero alla pagina corrente (anche su back/forward)
- Shortcut F1 su voce menu *Help → Visualizza Manuale Utente...*

**`gui_main.py`**:
- `_apri_manuale_utente()` semplificato: apre `HelpViewerDialog(self).exec()`
- `show_manual_action.setShortcut(QKeySequence(F1))`

**`requirements.txt`**: aggiunto `markdown>=3.4`


---

## Changelog sessione corrente (v1.5.0)

Tutto il lavoro è sul branch `claude/summarize-dev-status-vDVnI`.

### Feature: Redesign UI — Sidebar + Top Bar (`gui_main.py`, `styles/meridiana_styles.qss`)

Sostituita la navigazione a QTabWidget annidati (3 livelli) con una sidebar verticale stile VS Code + QStackedWidget flat.

**Nuove classi in `gui_main.py`:**
- `TopBarWidget(QFrame)` — barra fissa h=48px: logo SVG + titolo | [spacer] | indicatore DB | nome utente | chip ruolo | [Logout]
  - `update_user_info(nome, ruolo, db_connected, db_name)` — aggiorna tutti i label
  - `set_logout_enabled(bool)` — abilita/disabilita il pulsante logout
- `SidebarWidget(QWidget)` — pannello w=220px scrollabile
  - `build_nav(is_admin, fuzzy_available)` — costruisce bottoni e label sezione in base al ruolo
  - `set_active(page_name)` — applica stile attivo al bottone selezionato
  - `set_button_visible(page_name, visible)` — mostra/nasconde bottoni per ruolo
  - `get_page_names()` — lista ordinata pagine per shortcut Ctrl+N

**Refactoring `CatastoMainWindow`:**
- `initUI()`: rimosso `QTabWidget`, aggiunti `TopBarWidget` + `SidebarWidget` + `QStackedWidget`; rimosso `create_status_bar_content()`
- `setup_tabs()` → `setup_pages()`: tutte le pagine aggiunte direttamente a `self.stack`; `_page_index` dict mappa `page_name → indice stack`
- `navigate_to(page_name)`: nuovo metodo principale di navigazione (sostituisce tab switching)
- `activate_tab_and_sub_tab()`: mantenuto come wrapper di compatibilità con mapping `(main_tab, sub_tab) → page_name`
- `_on_stack_changed(index)`: lazy loading su cambio pagina stack
- `update_ui_based_on_role()`: usa `sidebar.set_button_visible()` invece di `tabs.setTabEnabled()`
- `handle_logout()`: aggiorna `top_bar`, svuota `self.stack`
- `_check_backup_reminder()`: usa `navigate_to("backup")`
- `_handle_partita_creata_per_operazioni()`: usa `navigate_to("operazioni")`
- `_handle_f5_refresh()`: opera su `self.stack.currentWidget()`
- Shortcut `Ctrl+1..N`: rimappati ai bottoni sidebar flat
- Titolo finestra: `"Meridiana — Archivio Catastale Storico"`

**`styles/meridiana_styles.qss`:** aggiunti stili `#topBar`, `#appTitle`, `#dbIndicator`, `#userLabel`, `#roleChip[role=*]`, `#logoutButton`, `#sidebar`, `#sectionLabel`, `QPushButton#navButton` (con stati `:hover` e `[active="true"]`), `QStackedWidget`.

---

## Changelog sessione corrente (v1.4.6.0)

Tutto il lavoro è sul branch `claude/summarize-dev-status-vDVnI`.

### Miglioramenti UI/UX (`gui_widgets.py`, `config.py`)

**Dashboard:**
- `APP_VERSION` aggiunta in `config.py` e importata in `gui_widgets.py`; header non più hardcoded "1.3"
- Riga secondaria sotto il titolo: ruolo utente + data/ora corrente (font piccolo, colore grigio)

**Form di inserimento (tutti e 4 i widget):**
- `setToolTip()` sui 5 pulsanti di ogni widget (Inserisci/Salva, Pulisci Campi, Importa CSV, Scarica CSV, Scarica template)
- `returnPressed` collegato al metodo di salvataggio sul campo principale di ogni form:
  - Comuni → `codice_catastale_edit`
  - Possessori → `nome_completo_edit`
  - Località → `nome_edit`
  - Partite → `suffisso_edit`

**Tabelle di ricerca:**
- `result_count_label` spostata sopra la tabella in `RicercaPartiteWidget` e `RicercaAvanzataImmobiliWidget`
- Menu contestuale (tasto destro) aggiunto a `RicercaAvanzataImmobiliWidget`: copia ID Immobile, Partita N., Comune, Natura
- Menu contestuale aggiunto a `RicercaDocumentiWidget`: copia Titolo, Anno, Partita, ID documento

---

## Changelog sessione corrente (v1.4.5.0)

Tutto il lavoro è sul branch `claude/summarize-dev-status-vDVnI`.

### Fix: ImportLocalitaDialog — campo OSM non sincronizzato (`dialogs.py`)

- `_build_ui()`: aggiunta chiamata a `_on_comune_changed()` dopo la costruzione dei tab, così `_osm_comune_edit` viene popolato correttamente all'apertura del dialog con il valore già selezionato nel combo.

### Conferma prima di ogni import dati (`dialogs.py`, `gui_main.py`)

- `QMessageBox.question` (default **No**) aggiunto in 6 punti:
  - `ImportComuniDialog._importa_csv()` — comuni da CSV
  - `ImportComuniDialog._importa_istat()` — comuni da ISTAT
  - `ImportLocalitaDialog._importa_csv()` — località da CSV
  - `ImportLocalitaDialog._importa_osm()` — località da OSM
  - `gui_main._import_possessori_csv()` — possessori da CSV
  - `gui_main._import_partite_csv()` — partite da CSV/xlsx
- Ogni messaggio mostra N record, comune di riferimento (ove applicabile) e avviso su dati già presenti.

---

## Changelog sessione corrente (v1.4.4.0)

Tutto il lavoro e sul branch `claude/summarize-dev-status-vDVnI`.

### Compliance GDPR/NIS2 (`config.py`, `catasto_db_manager.py`, `gui_main.py`, `gui_widgets.py`, `dialogs.py`)

**Session timeout (inattivita):**
- `config.py`: `SETTINGS_SESSION_TIMEOUT = "Security/SessionTimeoutMinutes"` (default 15, 0=disabilitato)
- `gui_main.py`: `QTimer` + `eventFilter` su `QApplication`; resetta su MouseMove/Click/KeyPress/Wheel
- Dialog countdown 60s con "Continua"/"Logout"; avvio dopo login, stop al logout
- Voce menu *Impostazioni → Timeout Sessione...* per configurare i minuti (`_configura_timeout_sessione()`)

**Log tracciabilita export:**
- `catasto_db_manager.py`: `log_app_event(user_id, session_id, event_type, details)` — scrive su `audit_log` (best-effort)
- `gui_main.py`: log in `_scarica_csv()` dopo salvataggio riuscito (copre tutti e 4 gli handler CSV)
- `gui_widgets.py`: log in `EsportazioniWidget._handle_export_csv()` e `_handle_export_xls()`

**Policy password:**
- `dialogs.py`: `_validate_password_strength(password) -> (bool, str)` — minimo 8 caratteri + 1 cifra
- `dialogs.py`: `CreateUserDialog.handle_create_user()` usa il nuovo validator (era min 6, nessun requisito cifra)
- `gui_widgets.py`: `reset_password_utente_selezionato()` usa il nuovo validator con importazione locale

### Documentazione aggiornata (`docs/`)
- `docs/index.md`: versione aggiornata a 1.4.4.0
- `docs/riferimento/changelog.md`: aggiunte sezioni v1.4.2.0, v1.4.3.0, v1.4.4.0
- `docs/admin/gestione-utenti.md`: aggiornati requisiti password, aggiunte note notifiche email
- `docs/primo-avvio.md`: aggiunta sezione "Timeout di sessione"

---

## Changelog sessione corrente (v1.5.3)

Tutto il lavoro è sul branch `claude/improve-foliarium-system-5aDC6`.

### Nota: migrazione PyQt6 (completata in v1.3.0.0)

L'applicazione usa **esclusivamente PyQt6**. Tutti gli enum sono nella forma
a tre parti obbligatoria:

```python
# CORRETTO (PyQt6)
Qt.AlignmentFlag.AlignLeft
Qt.ItemFlag.ItemIsSelectable
QSizePolicy.Policy.Expanding
QFont.Weight.Bold

# ERRATO (PyQt4/5 — genera AttributeError a runtime)
Qt.AlignLeft
Qt.ItemIsSelectable
QFont.Bold
```

### Refactoring: suddivisione `catasto_db_manager.py` in package `db/`

Il file monolitico (4 745 righe, 169 metodi) è stato suddiviso in 14 mixin
tramite ereditarietà multipla Python (MRO). `catasto_db_manager.py` è ora
una facade di 19 righe:

```python
class CatastoDBManager(
    DBComuniMixin, DBLocalitaMixin, DBPossessoriMixin,
    DBPartiteMixin, DBImmobiliMixin, DBVariazioniMixin,
    DBSearchMixin, DBAuditMixin, DBUtentiMixin,
    DBBackupMixin, DBDocumentiMixin, DBStatsMixin,
    DBIOMixin, DBConnectionBase,
):
    pass
```

Pattern corretto per ogni metodo DB (commit/rollback automatici):

```python
with self._get_connection() as conn:
    with conn.cursor(cursor_factory=DictCursor) as cur:
        cur.execute(query, params)
        return [dict(row) for row in cur.fetchall()]
```

### Fix: eliminazione `self.execute_query` residui (`db/` package)

31 metodi su 9 file mixin usavano ancora la vecchia API della classe
monolitica (`self.execute_query`, `self.fetchall`, `self.commit`,
`self.rollback`). Tutti riscritti con il pattern `_get_connection()`.

File corretti: `db/partite.py` (6), `db/audit.py` (6+1 close_user_session),
`db/variazioni.py` (6), `db/immobili.py` (2+1 delete_immobile),
`db/utenti.py` (1), `db/backup.py` (3), `db/documenti.py` (2),
`db/comuni.py` (1 completo riscrittura registra_comune_nel_db),
`db/possessori.py` (1).

Rimossi anche:
- 3 log di debug temporanei da `db/partite.py`
- Tutti i `logger.xxx()` bare → `self.logger.xxx()` in tutti i mixin
- `self.cursor`, `self.pool.getconn()`, `self.get_connection()`,
  `self.release_connection()` (tutti riferimenti all'API vecchia)

### Fix: dipendenza Qt in `db/stats.py`

Gli import `QProgressDialog`, `QMessageBox`, `Qt` spostati dentro
`refresh_materialized_views()` (lazy import). Il modulo può ora essere
importato in ambienti headless (test CI) senza che Qt sia disponibile.

### Estrazione widget GUI in moduli dedicati

`gui_widgets.py` (originale >7 000 righe) ridotto estraendo:

| Nuovo modulo | Widget |
|---|---|
| `admin_widgets.py` | `GestioneUtentiWidget`, `AuditLogViewerWidget`, `BackupWidget` |
| `import_dialogs.py` | `ImportComuniDialog`, `ImportLocalitaDialog` |
| `reporting_widgets.py` | `RicercaDocumentiWidget`, `EsportazioniWidget`, `ReportisticaWidget`, `StatisticheWidget` |

`gui_widgets.py` mantiene i re-export per backward compatibility degli import
esistenti.

### Fix runtime emersi durante il refactoring

| Errore | File | Soluzione |
|--------|------|-----------|
| `NameError: CatastoDBManager` | `admin_widgets.py` | `from __future__ import annotations` |
| `NameError: Tuple` | `import_dialogs.py` | Aggiunto `Tuple` agli import typing |
| `NameError: QStyle, QProgressDialog, pd` | `reporting_widgets.py` | Aggiunti import mancanti |
| `AttributeError: execute_query` | `db/documenti.py` | Riscritto con `_get_connection()` |
| `DatatypeMismatch civico` | `db/ricerca.py` + SQL | `civico INTEGER` → `VARCHAR` nella SP + riscrittura come query diretta |
| `AttributeError: civico_spinbox_nuova` | `dialogs.py` | Rimosso riferimento al spinbox in modalità selezione |

### Test coverage (`tests/unit/test_db_mixins.py`)

Nuovo file con **53 unit test** suddivisi in 9 classi (una per mixin).
Ogni test patcha `_get_connection()` con un mock connection:

```python
conn_cm, cur = make_mock_conn(rows=[{"id": 1, "nome": "Savona"}])
with patch.object(mgr, "_get_connection", return_value=conn_cm):
    result = mgr.get_comuni()
assert len(result) == 2
```

Coverage totale: **7% → 19.6%**

| Mixin | Coverage |
|-------|---------|
| `db/variazioni.py` | 61% |
| `db/audit.py` | 32% |
| `db/immobili.py` | 38% |
| `db/comuni.py` | 29% |
| `db/backup.py` | 29% |

`pytest.ini`: aggiunto `--cov=db`.

### Documentazione aggiornata

- `docs/index.md`: versione → 1.5.3
- `docs/riferimento/changelog.md`: aggiunta sezione v1.5.3 con dettaglio refactoring
- `CLAUDE.md`: aggiornato a v1.5.3, aggiunta nota PyQt6, aggiunto changelog sessione

### Debiti tecnici noti

Nessun debito tecnico aperto. Tutti i debiti precedenti sono stati risolti:

| Debito | Risolto in |
|--------|-----------|
| `db/base.py` import Qt massivi | commit `bcf65bd` |
| `gui_widgets.py` estrazione widget inserimento | `insertion_widgets.py` (commit `3fc3af7`) |
| Test coverage `db/possessori`, `db/partite`, `db/ricerca` | `test_db_possessori_partite_ricerca.py` (commit `3fc3af7`) |

---

## Changelog sessione corrente (v1.5.3 — demo + licenze + aggiornamenti)

Tutto il lavoro è sul branch `claude/create-demo-version-qUbik`.

### Feature: Versione Demo portabile (PostgreSQL embedded)

**`demo_launcher.py`** (nuovo):
- `start_demo_postgres()` — avvia `pg_ctl` sulla porta 15432, attende `pg_isready`
- `stop_demo_postgres()` — arresto fast, chiamato da `closeEvent` e da `atexit`
- `is_embedded_available()` — verifica presenza di `pgsql/` e `demo_data/` nel bundle
- Fallback scrittura: se `demo_data/` è in sola lettura (USB/CD), copia in `%LOCALAPPDATA%\Foliarium\demo_data`
- Porta dedicata 15432 — non interferisce con PostgreSQL di produzione sulla 5432

**`prepare_demo_db.py`** (nuovo, script CI):
- `initdb` con superuser `postgres`, locale C, encoding UTF-8
- Modifica `pg_hba.conf` (trust 127.0.0.1) e `postgresql.conf` (porta, shared_buffers)
- Crea ruolo `demo_user` e database `catasto_storico`
- Esegue `02_creazione-schema-tabelle.sql`, `03_funzioni-procedure.sql`, `05_demo_dataset.sql`
- Inserisce utente applicativo `demo` con hash bcrypt in tabella `utenti`
- Rimuove `postmaster.pid` per portabilità
- Uso: `python prepare_demo_db.py --pgsql-dir pgsql`

**`foliarium_demo.spec`** (aggiornato):
- Include `pgsql/bin`, `pgsql/lib`, `pgsql/share` e `demo_data/` nel COLLECT
- Runtime hook inietta `FOLIARIUM_DEMO=1` prima di qualsiasi import
- Gestisce assenza di `pgsql/` o `demo_data/` con warning (build non bloccante)

**`gui_main.py`** — modalità demo:
- `IS_DEMO_MODE`: rileva `--demo` CLI o `FOLIARIUM_DEMO=1` env var
- Badge arancione **DEMO** nella top bar
- Dialog di attesa con progress bar durante avvio PostgreSQL embedded
- Login automatico come utente `demo` (senza dialogo)
- `closeEvent`: chiama `demo_launcher.stop_demo_postgres()`

**Pipeline CI `build-demo`** (aggiornato):
- Scarica PostgreSQL 14 portabile da EnterpriseDB, rimuove pgAdmin4/doc/include/symbols
- Esegue `prepare_demo_db.py` per creare `demo_data/`
- Verifica presenza file critici nel bundle prima dello ZIP
- Produce `Foliarium_Demo_<versione>_Portabile.zip` (~150 MB)

**Flusso utente finale:**
1. Estrarre ZIP in qualsiasi cartella → doppio clic su `Foliarium_Demo.exe`
2. Dialog "Avvio database demo" (~3-5 s) → login automatico → app pronta
3. Dati dimostrativi: Provincia di Savona, 1870-1985, ~300 partite, 120 possessori
4. Chiusura: PostgreSQL si ferma automaticamente

### Feature: Gestione Licenze

**`license_manager.py`** (nuovo):
- `get_hardware_fingerprint()` — SHA-256(MAC+hostname), 16 hex
- `generate_license(...)` — produce JSON firmato HMAC-SHA256
- `_validate_file(path)` — verifica firma, hardware ID, scadenza → `LicenseInfo`
- Seat di rete: file-lock JSON in cartella condivisa UNC, TTL 2 min, refresh ogni 60 s
- `LicenseManager` — facade: `validate()`, `acquire_seat()`, `release_seat()`, `refresh_seat()`
- Demo mode: restituisce sempre licenza demo valida senza leggere file

**`generate_license.py`** (nuovo, CLI utility):
- `generate` — crea file `.license` per un cliente (`--to`, `--type`, `--seats`, `--expiry`, `--hardware`, `--bind-local`)
- `inspect` — mostra stato e validità di un file `.license`
- `fingerprint` — mostra MAC, hostname e ID hardware del computer corrente

**`dialogs.py`** — `LicenseDialog`:
- Stato licenza in tempo reale (validità, intestatario, tipo, seat, scadenza, hardware ID)
- Sfoglia file `.license`, configura cartella condivisa UNC per seat di rete
- Pulsante "Copia ID hardware" → clipboard per richiedere una licenza
- Accesso: *Impostazioni → Gestione Licenza…*

**`gui_main.py`** — verifica all'avvio:
- `LicenseManager.validate()` prima del dialogo DB — blocca se non valida
- `acquire_seat()` — blocca se seat di rete esauriti
- `release_seat()` al `closeEvent` e al logout
- Timer refresh seat ogni 60 s (`QTimer`)

### Feature: Auto-Aggiornamento con download automatico

**`update_checker.py`** (riscritto):
- Chiama GitHub API, confronta versioni semantiche
- Dialog aggiornato con note di rilascio (prime 3 righe del body) e pulsanti:
  - **"Scarica e installa automaticamente"** (solo se asset `.exe` trovato)
  - **"Apri pagina download"** → browser
- `DownloadWorker(QThread)`: progress bar 0–100%, gestione annullamento
- Verifica SHA-256 opzionale (file `.sha256` accanto all'installer su GitHub)
- Lancia installer Inno Setup con `/SILENT /CLOSEAPPLICATIONS /RESTARTAPPLICATIONS`
- Demo e test env saltano il controllo aggiornamenti

### File aggiunti/modificati

| File | Tipo | Note |
|------|------|------|
| `demo_launcher.py` | Nuovo | PostgreSQL embedded lifecycle |
| `prepare_demo_db.py` | Nuovo | Script CI inizializzazione DB demo |
| `generate_license.py` | Nuovo | CLI utility licenze |
| `license_manager.py` | Nuovo | Core licenze |
| `foliarium_demo.spec` | Nuovo | Build spec demo |
| `demo_config.ini` | Nuovo | Guida + credenziali demo |
| `update_checker.py` | Modificato | Auto-download + progress |
| `config.py` | Modificato | Costanti demo/licenza, porta 15432 |
| `gui_main.py` | Modificato | Integrazione demo + licenza |
| `dialogs.py` | Modificato | `LicenseDialog` aggiunto |
| `.gitignore` | Modificato | `pgsql/`, `demo_data/`, `*.license` |
| `pipeline_foliarium.yml` | Modificato | Job `build-demo` completo |

---

## Changelog sessione corrente (v1.6.0 — installer unificato + fix PyInstaller)

Tutto il lavoro è sul branch `claude/analyze-dev-progress-sPWUb`.

### Feature: Installer unificato Foliarium + PostgreSQL embedded

**`Foliarium_Unified_Installer.iss`** (nuovo) — installer Inno Setup che
distribuisce in un unico eseguibile: app Foliarium (output PyInstaller) +
binari PostgreSQL 14 portabili (`pgsql\bin`, `pgsql\lib`, `pgsql\share`) +
script SQL + `setup_database.bat`. Sostituisce la procedura manuale di
installazione di PostgreSQL sul PC di destinazione.

**`setup_database.bat`** (nuovo) — eseguito automaticamente dall'installer
nelle 8 fasi:
1. Verifica porta 5432 (fallback 5433/5434)
2. `initdb` in `%ProgramData%\Foliarium\pg_data` (NON in Program Files)
3. Avvio temporaneo in `trust` + `ALTER USER postgres PASSWORD`
4. Sovrascrittura `pg_hba.conf` con `scram-sha-256`
5. Registrazione servizio Windows `FoliariumDB` (auto-start)
6. Avvio servizio + `pg_isready` loop
7. Esecuzione script SQL (schema, procedure, user management, bootstrap admin)
8. Scrittura `config.ini` con credenziali generate casualmente

**`uninstall_database.bat`** (nuovo) — ferma e deregistra il servizio,
rimuove `%ProgramData%\Foliarium\pg_data`.

**`setup_database.py`** (nuovo) — variante cross-platform per sviluppo
Linux/macOS; reimplementa le stesse operazioni con Python puro.

**Password generate casualmente dall'installer Pascal:** 16 caratteri
alfanumerici per il DB, 12 per l'admin applicativo, passati come
parametri a `setup_database.bat`.

### Fix: errori emersi durante il debug dell'installer

| # | Errore | Causa | Fix | Commit |
|---|--------|-------|-----|--------|
| 1 | `initdb: Permission denied` | `pg_data` in `C:\Program Files` non scrivibile perché `initdb` droppa i privilegi | Spostato in `%ProgramData%\Foliarium\pg_data` | `e691897` |
| 2 | Hang su "il server è stato avviato" | `pg_hba.conf` scritto `scram-sha-256` prima del primo `ALTER USER` → psql non poteva autenticarsi | Riordinato: trust-start → `ALTER USER` → riscrittura hba → restart | `82c9dbd` |
| 3 | `initdb: directory exists but is not empty` | Residuo di `pg_data` da installazione precedente fallita | Aggiunta pulizia automatica con `taskkill /F /IM postgres.exe` + `rmdir /s /q` | `385c11d` |
| 4 | `DeleteFile fallito; codice 5. Accesso negato` su `icuin67.dll` | Servizio `FoliariumDB` ancora in esecuzione durante la reinstallazione | `PrepareToInstall()` Pascal ferma `FoliariumDB` e killa `postgres.exe` prima dell'estrazione | `77da8ca` |

### Fix: percorsi PyInstaller 'onedir' (EXE_DIR vs BASE_DIR)

Problema: in un bundle PyInstaller `onedir`, `sys._MEIPASS` =
`app_paths.BASE_DIR` punta alla sottocartella `_internal/` dove vengono
estratte le risorse interne, **NON** alla cartella dove vive
`Foliarium.exe`. Ma `config.ini` (scritto dall'installer) e
`foliarium.license` (fornito dal cliente) stanno accanto all'eseguibile.
Risultato: l'app non trovava né le credenziali DB né il file di licenza.

Fix (commit `4c56506`):
- **`app_paths.py`**: nuova funzione `get_exe_dir()` e costante `EXE_DIR`:
  ```python
  def get_exe_dir():
      if getattr(sys, 'frozen', False):
          return Path(sys.executable).parent  # Foliarium.exe folder
      else:
          return Path(__file__).parent

  EXE_DIR = get_exe_dir()
  ```
- **`config.py`**: `_config_ini_path` ora cerca prima in `EXE_DIR`, poi
  come fallback in `BASE_DIR` (per retrocompatibilità dev mode).
- **`license_manager.py`**: `LicenseManager.__init__` cerca il file
  `.license` prima in `EXE_DIR`, poi in `BASE_DIR`, poi usa il percorso
  atteso (`EXE_DIR`) per il messaggio di errore.

### Regola generale per file esterni in PyInstaller onedir

| Tipo di file | Dove si trova | Usare |
|--------------|---------------|-------|
| Risorse bundled (icone, .qss, .md, .svg) | `_internal/` | `BASE_DIR` |
| File utente / installer (`config.ini`, `.license`) | Accanto all'exe | `EXE_DIR` |
| Dati scrivibili (log, cache, esportazioni) | `%LOCALAPPDATA%\Foliarium` | `APP_DATA_DIR` |

### File aggiunti/modificati (v1.6.0 — sessione installer)

| File | Tipo | Note |
|------|------|------|
| `Foliarium_Unified_Installer.iss` | Nuovo | Installer Inno Setup unificato |
| `setup_database.bat` | Nuovo | Script batch inizializzazione DB (Windows) |
| `setup_database.py` | Nuovo | Script Python cross-platform (Linux/macOS) |
| `uninstall_database.bat` | Nuovo | Script batch disinstallazione |
| `app_paths.py` | Modificato | Aggiunti `get_exe_dir()` + `EXE_DIR` |
| `config.py` | Modificato | `_config_ini_path` usa `EXE_DIR` |
| `license_manager.py` | Modificato | Cerca `.license` prima in `EXE_DIR` |

### Documentazione aggiornata

- `docs/riferimento/changelog.md`: sezione v1.6.0 arricchita con installer
  unificato, fix critici, fix PyInstaller
- `CLAUDE.md`: titolo corretto a "Foliarium" (da "Meridiana"), versione
  marcata come "definitiva", aggiunto questo changelog di sessione

### Stato finale v1.6.0

Foliarium 1.6.0 è la **versione definitiva**. Include tutto lo stack:
- App PyQt6 completamente funzionante
- PostgreSQL 14 embedded (produzione) o portabile (demo)
- Installer unificato Windows self-contained
- Sistema licenze HMAC-SHA256 + seat di rete
- Auto-aggiornamento da GitHub Releases
- 16 temi, dark/light automatico, UI sidebar + top bar
- Coverage test 19.6% + 164 unit test complessivi
- Documentazione MkDocs completa, manuale utente integrato (F1)

Nessun debito tecnico noto.
