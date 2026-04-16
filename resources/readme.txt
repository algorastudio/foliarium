# Sistema di Gestione Catasto Storico

## 📋 Panoramica del Progetto

Il Sistema di Gestione Catasto Storico è una soluzione completa per la digitalizzazione, gestione e consultazione dei registri catastali storici italiani. Il progetto integra un database PostgreSQL avanzato con un'applicazione desktop Python/PyQt5, offrendo strumenti per archiviazione, ricerca, analisi e reportistica di dati catastali storici.

---

## 🏗️ Architettura del Sistema

### Backend (PostgreSQL)
- **Schema dedicato**: `catasto` con tabelle normalizzate
- **Sistema di audit**: Tracciamento completo di tutte le modifiche
- **Funzioni avanzate**: Procedure stored per operazioni complesse
- **Ricerca fuzzy**: Indici GIN per ricerche testuali avanzate
- **Backup automatizzati**: Sistema integrato di backup e restore

### Frontend (Python/PyQt5)
- **Interfaccia desktop**: Applicazione nativa per Windows/Linux/Mac
- **Gestione multi-utente**: Sistema di autenticazione e permessi
- **Reportistica**: Generazione di report PDF e Excel
- **Ricerca avanzata**: Interfaccia intuitiva per ricerche complesse

---

## 📁 Struttura del Progetto

```
catasto-storico/
├── app_utils.py
├── catasto_db_manager.py
├── config.py
├── custom_widgets.py
├── dialogs.py
├── gui_main.py
├── gui_widgets.py
├── requirements.txt
├── backup/
├── docs/
├── diagrammi/
├── esportazioni/
├── resources/
├── sql_scripts/
├── styles/
├── tests/
└── readme-catasto-storico.md
```

- **/backup**: Dump e backup del database
- **/docs**: Documentazione utente e tecnica
- **/diagrammi**: Diagrammi ER e di flusso
- **/esportazioni**: Report e dati esportati
- **/resources**: Risorse grafiche e file statici
- **/sql_scripts**: Script SQL per schema, funzioni, dati esempio
- **/styles**: Fogli di stile per la GUI
- **/tests**: Test automatici

---

## 🛠️ Requisiti di Sistema

- **Python**: >= 3.11
- **PostgreSQL**: >= 15
- **PyQt5**: per l'interfaccia grafica
- **Altri moduli**: vedi [requirements.txt](requirements.txt)

---

## 🚀 Installazione

### 1. Configurazione Database

```bash
# Creare il database
createdb catasto_storico

# Eseguire gli script in ordine
psql -d catasto_storico -f sql_scripts/02_creazione-schema-tabelle.sql
psql -d catasto_storico -f sql_scripts/14_report_functions.sql
# ... altri script secondo la documentazione
```

### 2. Configurazione Applicazione

```bash
# Clonare il repository
git clone [url-repository]
cd catasto-storico

# Installare dipendenze
pip install -r requirements.txt

# Configurare connessione database
# Modificare le credenziali in config.py o nel modulo di gestione DB
```

### 3. Avvio Applicazione

```bash
python gui_main.py
```

---

## 📊 Modello Dati

### Entità Principali

- **Comuni**: Anagrafica dei comuni con gestione storica dei nomi
- **Possessori**: Persone fisiche e giuridiche proprietarie
- **Partite Catastali**: Unità di proprietà con numerazione storica
- **Immobili**: Beni immobili (terreni, fabbricati) con caratteristiche
- **Località**: Vie, contrade, borghi con riferimenti storici
- **Variazioni**: Trasferimenti di proprietà e modifiche catastali
- **Contratti**: Atti notarili collegati alle variazioni
- **Consultazioni**: Log delle consultazioni archivistiche

Per dettagli, vedi i diagrammi ER in [diagrammi/catasto-er-diagram-ufficiale.mermaid](diagrammi/catasto-er-diagram-ufficiale.mermaid).

---

## 💡 Funzionalità Principali

### Gestione Dati
- Inserimento, modifica e cancellazione di comuni, possessori, partite, immobili
- Import/export dati in formato CSV, Excel, PDF
- Backup e restore automatizzati

### Ricerca e Consultazione
- Ricerca fuzzy multi-entità
- Filtri avanzati per periodo storico
- Visualizzazione gerarchica delle proprietà
- Timeline delle variazioni di proprietà

### Reportistica
- Report proprietà per possessore
- Albero genealogico delle proprietà
- Statistiche catastali per periodo
- Esportazione PDF e Excel

### Amministrazione
- Gestione utenti e permessi
- Log delle operazioni (audit trail)
- Monitoraggio performance
- Manutenzione database

---

## 🔍 Esempi d'Uso

### Ricerca Possessore
```python
# Nella GUI: Tab Ricerca → Possessori
# Inserire: "Ross*" per trovare tutti i Rossi, Rossini, ecc.
```

### Registrazione Variazione
```python
# Menu: Registrazioni → Nuova Variazione Proprietà
# Selezionare: Partita origine, destinazione, tipo, data
```

### Generazione Report
```python
# Menu: Report → Albero Genealogico
# Selezionare: Partita catastale e periodo
```

---

## 🔧 Manutenzione

### Backup Periodici
```bash
# Script automatico (schedulare con cron)
./database/scripts/backup_catasto.sh
```

### Ottimizzazione Database
```sql
-- Eseguire mensilmente
VACUUM ANALYZE catasto.*;
REINDEX SCHEMA catasto;
```

### Pulizia Log
```sql
-- Rimuovere log più vecchi di 1 anno
DELETE FROM catasto.system_log 
WHERE created_at < CURRENT_DATE - INTERVAL '1 year';
```

---

## 📈 Sviluppi Futuri

- Integrazione GIS per mappe catastali
- OCR per digitalizzazione automatica documenti
- API REST per integrazioni esterne
- Versione web responsive
- Machine learning per riconoscimento scrittura
- Analisi predittive su valori immobiliari

---

## 📄 Licenza

Questo progetto è distribuito sotto licenza MIT. Vedi il file LICENSE per dettagli.

---

## 📞 Supporto

- [Guida Utente](docs/istruzioni-utilizzo.md)
- Email: supporto@catasto-storico.it

---

**Versione**: 1.0.0  
**Ultimo aggiornamento**: Giugno 2025  
**Mantenuto da**: Team Sviluppo Catasto