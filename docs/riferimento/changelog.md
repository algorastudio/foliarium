# Changelog

## v1.5.3 — Marzo 2026

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
