# Foliarium

**Gestionale per il Catasto Storico degli Archivi di Stato**

[![License: AGPL v3](https://img.shields.io/badge/License-AGPL_v3-blue.svg)](https://www.gnu.org/licenses/agpl-3.0)
[![publiccode.yml](https://img.shields.io/badge/publiccode-available-brightgreen)](publiccode.yml)

---

## Cos'è Foliarium

Foliarium è un software gestionale desktop per la gestione, consultazione e digitalizzazione del **catasto storico** presso gli Archivi di Stato italiani.

Sviluppato in **Python 3.12** con interfaccia grafica **PyQt6** e database centralizzato **PostgreSQL**, Foliarium consente agli operatori archivistici di gestire in modo efficiente l'intero patrimonio catastale storico.

> Nato dall'esperienza diretta con l'Archivio di Stato di Savona.

---

## Funzionalità principali

- **Dashboard**: panoramica con statistiche su comuni, partite, possessori e immobili registrati
- **Ricerca fuzzy avanzata**: ricerca unificata su partite, possessori, immobili, variazioni e contratti con supporto trigrammi (pg_trgm)
- **Ricerca avanzata immobili**: filtri per natura, classificazione, località e comune
- **Gestione partite catastali**: inserimento, modifica, relazioni tra partite principali/secondarie, suffissi, provenienza
- **Gestione possessori**: anagrafica con paternità, quote, titoli di possesso, comproprietà
- **Gestione immobili**: natura, consistenza, classificazione, piani, vani, località associate
- **Variazioni e contratti**: vendite, successioni, frazionamenti, divisioni con notaio e repertorio
- **Gestione periodi storici**: suddivisione per epoca (Regno di Sardegna, Regno d'Italia, Repubblica)
- **Gestione tipi località**: tipologie stradali (via, piazza, salita, ecc.)
- **Gestione utenti con ruoli e permessi**: profili differenziati (operatori, consultatori, amministratori) con login/logout, hashing bcrypt, rate-limit anti brute-force e protezione anti user-enumeration
- **Audit log**: registrazione automatica di tutte le operazioni di inserimento, modifica e cancellazione
- **Registrazione consultazioni**: registro delle consultazioni dell'archivio con richiedente e motivazione
- **Esportazioni**: export in CSV, PDF e JSON per partite e possessori, report di massa
- **Reportistica avanzata**: viste aggregate, statistiche per comune e periodo
- **Backup database**: sistema di backup integrato
- **Temi interfaccia**: stylesheet QSS multipli (chiaro, scuro, alto contrasto, pergamena, ecc.)
- **Importazione CSV**: importazione dati da file CSV con dialogo di anteprima
- **Ottimizzazione performance**: indici GIN, viste materializzate, connection pooling
- **Modalità demo embedded**: avvio con PostgreSQL portabile (`--demo`) per valutazione senza installazione
- **REST API opzionale**: server FastAPI per integrazioni esterne (`api/`)
- **Sistema licenze**: file `.license` firmati HMAC-SHA256 con vincoli per scadenza, hardware fingerprint e seat di rete

---

## Stack tecnologico

| Componente | Tecnologia |
|---|---|
| Linguaggio | Python 3.12 |
| Interfaccia grafica | PyQt6 6.8.1 |
| Database | PostgreSQL 14+ |
| Accesso dati | psycopg2-binary 2.9.10 (connection pool) |
| Elaborazione dati | pandas 2.3, numpy 2.3, openpyxl 3.1.5 |
| Report PDF | fpdf2 2.8.3 |
| Sicurezza password | bcrypt 4.3 + keyring 25.6 |
| API REST (opzionale) | FastAPI, uvicorn |
| Build pacchetto | PyInstaller + Inno Setup |
| Documentazione | MkDocs Material |

---

## Struttura del progetto

```
foliarium/
├── gui_main.py                   # Entry point — QMainWindow, app init
├── gui_widgets.py                # Facade UI + widget principali (Dashboard, Elenco comuni)
├── search_widgets.py             # Widget di ricerca (partite, immobili, fuzzy unificata)
├── partita_workflow_widgets.py   # Workflow partite (registrazione, wizard, operazioni)
├── dialogs.py                    # Facade dialoghi (impl. in foliarium/ui/dialogs/)
├── catasto_db_manager.py         # Facade DB — delega al package db/
├── app_utils.py                  # Helper PDF, esportazioni, IP locale
├── app_paths.py                  # Risoluzione path (BASE_DIR, EXE_DIR, APP_DATA_DIR)
├── config.py                     # Costanti, logging, lettura config.ini
├── validators.py                 # Validatori centralizzati per form e logica
│
├── foliarium/                    # Package principale (servizi + UI estratti)
│   ├── core/services/            # email, license, update_checker, demo_launcher
│   └── ui/                       # top_bar, sidebar, command_palette, splash
│       ├── dialogs/              # entity, admin, partita, import_, export_
│       └── widgets/              # admin, insertion, reporting, custom
│
├── db/                           # Database layer (mixin per dominio)
│   ├── base.py                   # DBConnectionBase: pool, error handler, transazioni
│   ├── comuni.py, localita.py, possessori.py, partite.py, immobili.py
│   ├── variazioni.py, documenti.py, audit.py, utenti.py
│   ├── backup.py, stats.py, ricerca.py, io.py, archivio.py
│   └── models.py                 # Dataclass models
│
├── core/                         # Gestione sessione e autenticazione
│   ├── session_manager.py        # SessionManager (stato utente corrente)
│   └── auth_manager.py           # AuthManager (login + permessi, rate-limit)
│
├── api/                          # REST API FastAPI (opzionale)
│   ├── main.py, server_thread.py
│   └── routes/                   # comuni, partite, possessori, audit, genealogia...
│
├── utils/
│   └── error_handlers.py         # Eccezioni custom (AuthenticationError, ecc.)
│
├── sql_scripts/                  # Script PostgreSQL
│   ├── 01_creazione-database.sql, 02_…, … 18_funzioni_trigger_audit.sql
│   └── migrations/               # Upgrade script per DB esistenti
│
├── tests/                        # Test suite pytest (unit/, integration/)
├── styles/                       # Fogli di stile QSS
├── resources/                    # Icone, immagini, EULA
├── docs/                         # Documentazione MkDocs
├── esportazioni/                 # Output PDF/CSV
├── .devcontainer/                # Dev container per VS Code / Codespaces
├── .github/workflows/            # CI/CD GitHub Actions
├── foliarium.spec                # PyInstaller spec (build produzione)
├── setup_database.bat / .py      # Inizializzazione DB
├── generate_license.py           # CLI per generare/ispezionare file .license
├── generate_key.py               # CLI per generare la chiave HMAC di firma licenze
└── requirements.txt              # Dipendenze Python (versioni pinnate)
```

---

## Requisiti di sistema

### Client
- Sistema operativo: Windows 10/11 (target principale) o Linux (Ubuntu 22.04+, Debian 12+)
- Python **3.12** (se si esegue dai sorgenti)
- PyQt6 6.8.1

### Server database
- PostgreSQL **14 o superiore**
- Estensioni: `uuid-ossp`, `pg_trgm`
- Minimo 2 GB RAM dedicati
- Spazio disco proporzionale alla dimensione dell'archivio catastale

---

## Installazione rapida

> **Per provare Foliarium senza installare nulla:** scarica la versione demo embedded (PostgreSQL portabile incluso) dalla pagina Releases ed esegui `Foliarium.exe --demo`.

### 1. Clona il repository

```bash
git clone https://github.com/algorastudio/foliarium.git
cd foliarium
```

### 2. Crea un ambiente virtuale

```bash
python -m venv venv
source venv/bin/activate     # Linux / macOS
venv\Scripts\activate        # Windows
```

### 3. Installa le dipendenze

```bash
pip install -r requirements.txt
```

### 4. Configura il database

Crea il database PostgreSQL (richiede privilegi superuser):

```bash
sudo -u postgres psql -f sql_scripts/01_creazione-database.sql
```

Copia il template di configurazione e personalizzalo con le credenziali del tuo PostgreSQL:

```bash
cp config.example.ini config.ini
# Modifica config.ini con host, dbname, user, password
```

In alternativa puoi usare variabili d'ambiente (`DB_HOST`, `DB_USER`, `DB_PASS`, `DB_NAME`, `DB_PORT`).
Se non viene fornita una password in modalità non-demo, Foliarium aprirà il dialogo di configurazione manuale all'avvio.

### 5. Inizializza lo schema

```bash
python setup_database.py
```

### 6. Avvia l'applicazione

```bash
python gui_main.py
```

Per la modalità demo (PostgreSQL portabile, autologin):

```bash
python gui_main.py --demo
```

---

## Comandi utili

```bash
# Esecuzione test (richiede DB attivo)
pytest                       # tutti i test
pytest -m unit               # solo unit test
pytest -m "not gui"          # salta test GUI (utile in CI headless)

# Generare un file licenza per un cliente
python generate_license.py generate \
    --to "Archivio di Stato di Savona" \
    --type standard --seats 2 \
    --expiry 2027-12-31 --out savona.license

# Ispezionare un file licenza
python generate_license.py inspect savona.license

# Generare la chiave HMAC per la firma delle licenze (una volta per ambiente)
python generate_key.py --save-exe-dir   # salva accanto a Foliarium.exe
python generate_key.py --env-var        # stampa solo l'HEX per FOLIARIUM_LICENSE_KEY

# Build dell'eseguibile Windows
pyinstaller foliarium.spec               # build produzione

# Documentazione
mkdocs serve                             # anteprima locale
```

Per un'esecuzione in ambiente CI/headless:

```bash
export CI=true
export DB_HOST=localhost DB_USER=postgres DB_PASS=postgres
export DB_NAME=catasto_storico DB_PORT=5432
export QT_QPA_PLATFORM=offscreen
pytest
```

---

## Documentazione

- [Guida all'installazione](docs/installazione.md) *(se presente)*
- Documentazione completa: `mkdocs serve` o vedi cartella `docs/`

---

## Contesto e destinatari

Foliarium è progettato per:

- **Archivi di Stato** che gestiscono fondi catastali storici
- **Comuni e Province** con archivi catastali da digitalizzare
- **Aziende di digitalizzazione** che partecipano a gare PNRR per la digitalizzazione del patrimonio archivistico
- **Ricercatori e storici** che necessitano di consultare registri catastali storici

Il software risponde ai requisiti dei progetti di digitalizzazione finanziati con fondi **PNRR Missione 1, Componente 3** — "Turismo e Cultura 4.0".

---

## Servizi professionali

Foliarium è software libero. Per supporto professionale, personalizzazioni, formazione e servizi di integrazione:

**ALGORASTUDIO**
- Email: santoromarco@gmail.com
- Sito: [algorastudio.it](https://algorastudio.it)

Servizi disponibili:
- Installazione e configurazione presso la vostra sede
- Personalizzazione e adattamento alle specificità del vostro archivio
- Migrazione dati da sistemi esistenti
- Formazione per operatori e amministratori
- Contratti di manutenzione e supporto tecnico

---

## Licenza

Foliarium è disponibile con **due modelli di licenza**:

### Licenza Open Source (AGPL-3.0-or-later)

[![License: AGPL v3](https://img.shields.io/badge/License-AGPL_v3-blue.svg)](LICENSE)

Uso gratuito per enti pubblici e privati, **a condizione** che eventuali modifiche al codice
vengano rilasciate pubblicamente sotto la stessa licenza AGPL-3.0-or-later.
Testo completo: [LICENSE](LICENSE)

### Licenza Commerciale

Per chi necessita di:
- personalizzazioni proprietarie non divulgabili
- integrazioni con sistemi terzi riservati
- SLA garantiti e supporto prioritario
- utilizzo in ambienti che non possono rispettare i vincoli AGPL

è disponibile una **licenza commerciale** che non impone l'obbligo di pubblicare
le modifiche. Contatta ALGORASTUDIO per un preventivo.

**Email:** santoromarco@gmail.com

---

## Contribuire

I contributi sono benvenuti. Prima di contribuire, leggi le [linee guida](CONTRIBUTING.md)
e il [Contributor License Agreement](CLA.md).

---

*Un progetto [ALGORASTUDIO](https://algorastudio.it) — Software per il patrimonio culturale italiano.*
