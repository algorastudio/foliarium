# Changelog

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
