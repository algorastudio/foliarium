# Changelog

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
