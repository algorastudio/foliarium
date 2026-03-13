# Foliarium

**Gestionale per il Catasto Storico degli Archivi di Stato**

[![License: AGPL v3](https://img.shields.io/badge/License-AGPL_v3-blue.svg)](https://www.gnu.org/licenses/agpl-3.0)
[![publiccode.yml](https://img.shields.io/badge/publiccode-available-brightgreen)](publiccode.yml)

---

## Cos'è Foliarium

Foliarium è un software gestionale desktop per la gestione, consultazione e digitalizzazione del **catasto storico** presso gli Archivi di Stato italiani.

Sviluppato in **Python** con interfaccia grafica **PyQt5** e database centralizzato **PostgreSQL**, Foliarium consente agli operatori archivistici di gestire in modo efficiente l'intero patrimonio catastale storico.

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
- **Gestione utenti con ruoli e permessi**: profili differenziati (operatori, consultatori, amministratori) con login/logout e hashing bcrypt
- **Audit log**: registrazione automatica di tutte le operazioni di inserimento, modifica e cancellazione
- **Registrazione consultazioni**: registro delle consultazioni dell'archivio con richiedente e motivazione
- **Esportazioni**: export in CSV, PDF e JSON per partite e possessori, report di massa
- **Reportistica avanzata**: viste aggregate, statistiche per comune e periodo
- **Backup database**: sistema di backup integrato
- **Temi interfaccia**: supporto stili QSS personalizzabili
- **Importazione CSV**: importazione dati da file CSV con dialogo di anteprima
- **Ottimizzazione performance**: indici GIN, viste materializzate, connection pooling

---

## Stack tecnologico

| Componente | Tecnologia |
|---|---|
| Linguaggio | Python 3.8+ |
| Interfaccia grafica | PyQt5 |
| Database | PostgreSQL 13+ |
| Accesso dati | psycopg2 (connection pool) |
| Report PDF | fpdf2 |
| Sicurezza password | bcrypt + keyring |

---

## Struttura del progetto

```
foliarium/
├── main.py                    # Entry point dell'applicazione
├── setup_db.py                # Script inizializzazione database
├── requirements.txt           # Dipendenze Python
├── config.example.ini         # Configurazione di esempio
├── publiccode.yml             # Metadati per il software pubblico italiano
├── LICENSE                    # AGPL-3.0-or-later
├── CONTRIBUTING.md            # Linee guida per contribuire
├── .gitignore
├── src/                       # Codice sorgente Python
│   ├── __init__.py
│   ├── app_paths.py           # Gestione percorsi (base dir, risorse, stili, log)
│   ├── config.py              # Configurazione DB, logging, costanti interfaccia
│   ├── catasto_db_manager.py  # Logica accesso database PostgreSQL (CRUD, pool)
│   ├── gui_main.py            # Finestra principale PyQt5
│   ├── gui_widgets.py         # Widget interfaccia (dashboard, ricerca, inserimento)
│   ├── dialogs.py             # Dialoghi (import CSV, EULA, backup, configurazione DB)
│   ├── custom_widgets.py      # Widget personalizzati (tabelle, password, lazy loading)
│   └── app_utils.py           # Utility (IP locale, keyring, PDF, esportazioni)
├── database/                  # Script SQL per PostgreSQL
│   ├── 01_creazione-database.sql
│   ├── 02_creazione-schema-tabelle.sql
│   ├── 03_funzioni-procedure.sql
│   ├── 03b_expand_fuzzy_search.sql
│   ├── 05_query-test.sql
│   ├── 07_user-management.sql
│   ├── 08_advanced-reporting.sql
│   ├── 09_backup-system.sql
│   ├── 10_performance-optimization.sql
│   ├── 11_advanced-cadastral-features.sql
│   ├── 12_procedure_crud.sql
│   ├── crea_admin_interattivo.sql
│   └── demo_data.sql
├── docs/                      # Documentazione
│   ├── installazione.md
│   └── architettura.md
├── resources/                 # Risorse (icone, loghi, EULA)
├── styles/                    # Fogli di stile QSS
└── screenshots/               # Screenshot dell'applicazione
```

---

## Requisiti di sistema

### Client
- Sistema operativo: Windows 10/11 o Linux (Ubuntu 20.04+, Debian 11+)
- Python 3.8 o superiore
- PyQt5 (5.15+)

### Server database
- PostgreSQL 13 o superiore (consigliato 15+)
- Estensioni: `uuid-ossp`, `pg_trgm`
- Minimo 2 GB RAM dedicati
- Spazio disco in base alla dimensione dell'archivio catastale

---

## Installazione rapida

### 1. Clona il repository

```bash
git clone https://github.com/algorastudio/foliarium.git
cd foliarium
```

### 2. Crea un ambiente virtuale

```bash
python -m venv venv
source venv/bin/activate  # Linux
venv\Scripts\activate     # Windows
```

### 3. Installa le dipendenze

```bash
pip install -r requirements.txt
```

### 4. Configura il database

Crea il database PostgreSQL (richiede privilegi superuser):

```bash
sudo -u postgres psql -f database/01_creazione-database.sql
```

Poi copia e personalizza il file di configurazione:

```bash
cp config.example.ini config.ini
# Modifica config.ini con le credenziali del tuo database
```

### 5. Inizializza lo schema

```bash
python setup_db.py --host localhost --dbname catasto_storico --user postgres
```

Per caricare anche i dati demo:

```bash
python setup_db.py --host localhost --dbname catasto_storico --user postgres --demo
```

### 6. Avvia l'applicazione

```bash
python main.py
```

Per la guida completa, consulta [docs/installazione.md](docs/installazione.md).

---

## Documentazione

- [Guida all'installazione](docs/installazione.md)
- [Architettura del sistema](docs/architettura.md)

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

Foliarium è rilasciato sotto licenza [GNU Affero General Public License v3.0](LICENSE) (AGPL-3.0-or-later).

Questo significa che puoi liberamente usare, studiare, modificare e redistribuire il software, a condizione che ogni versione modificata sia rilasciata con la stessa licenza.

Per utilizzi con licenza commerciale diversa, contatta ALGORASTUDIO.

---

## Contribuire

I contributi sono benvenuti. Prima di contribuire, leggi le [linee guida per i contributi](CONTRIBUTING.md).

---

*Un progetto [ALGORASTUDIO](https://algorastudio.it) — Software per il patrimonio culturale italiano.*
