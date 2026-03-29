# Foliarium

**Gestionale per il Catasto Storico degli Archivi di Stato**

[![License: Commercial](https://img.shields.io/badge/License-Commercial-gold.svg)](LICENSE)
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
├── LICENSE                    # Licenza commerciale proprietaria
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
│   ├── 00_svuota_dati.sql             # Reset dati del database
│   ├── 01_creazione-database.sql      # Creazione database e estensioni
│   ├── 02_creazione-schema-tabelle.sql # Schema e tabelle principali
│   ├── 03_funzioni-procedure.sql      # Funzioni e stored procedure
│   ├── 03_funzioni-procedure_def.sql  # Definizioni procedure aggiuntive
│   ├── 03b_expand_fuzzy_search.sql    # Espansione ricerca fuzzy (trigrammi)
│   ├── 04_dati-esempio_modificato.sql # Dati di esempio
│   ├── 04_dati_stress_test.sql        # Dati per stress test
│   ├── 04b_dati_test_realistici.sql   # Dati di test realistici
│   ├── 05_query-test.sql              # Query di test
│   ├── 05_query-test_aggiornato.sql   # Query di test aggiornate
│   ├── 07_user-management.sql         # Gestione utenti e permessi
│   ├── 07a_bootstrap_admin.sql        # Creazione utente admin iniziale
│   ├── 08_advanced-reporting.sql      # Reportistica avanzata
│   ├── 09_backup-system.sql           # Sistema di backup
│   ├── 10_performance-optimization.sql # Indici e ottimizzazioni
│   ├── 11_advanced-cadastral-features.sql # Funzionalità catastali avanzate
│   ├── 12_procedure_crud.sql          # Procedure CRUD
│   ├── 13_workflow_integrati.sql      # Workflow integrati
│   ├── 14_report_functions.sql        # Funzioni di reportistica
│   ├── 15_integration_audit_users.sql # Integrazione audit e utenti
│   ├── 16_advanced_search.sql         # Ricerca avanzata
│   ├── 17_funzione_ricerca_immobili.sql # Ricerca immobili
│   ├── 18_funzioni_trigger_audit.sql  # Trigger per audit log
│   ├── 19_creazione_tabella_sessioni.sql # Tabella sessioni utente
│   ├── 20_feature_tipi_localita.sql   # Tipologie località
│   ├── crea_admin_interattivo.sql     # Script interattivo creazione admin
│   ├── demo_data.sql                  # Dati dimostrativi (località liguri)
│   ├── drop_db.sql                    # Eliminazione database
│   ├── execute_fuzzy_expansion.sql    # Esecuzione espansione fuzzy
│   ├── expand_fuzzy_search.sql        # Configurazione ricerca fuzzy
│   ├── meridiana.spec                 # File spec (legacy)
│   └── script x cancellare db1.txt    # Note cancellazione DB
├── docs/                      # Documentazione
│   ├── installazione.md
│   └── architettura.md
├── portable/                  # Versione portatile (no installazione)
│   ├── setup_primo_avvio.bat  # Configurazione iniziale automatica
│   ├── avvia_foliarium.bat    # Avvio applicazione + PostgreSQL
│   ├── arresta_foliarium.bat  # Arresto PostgreSQL
│   └── README_PORTABLE.md     # Istruzioni versione portatile
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

> **Versione portatile per Windows:** se vuoi provare Foliarium senza installare PostgreSQL, consulta la [guida portatile](portable/README_PORTABLE.md). Basta scaricare i binari PostgreSQL, un doppio clic e sei operativo.

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

Foliarium è distribuito esclusivamente con **licenza commerciale proprietaria**.
La licenza è richiesta per tutti i soggetti: aziende private, enti pubblici, Pubblica Amministrazione e istituti di ricerca.

La licenza include:
- supporto tecnico dedicato
- SLA garantiti su richiesta
- personalizzazioni su misura

Per un preventivo contatta ALGORASTUDIO.

**Email:** santoromarco@gmail.com

---

## Contribuire

I contributi sono benvenuti. Prima di contribuire, leggi le [linee guida](CONTRIBUTING.md)
e il [Contributor License Agreement](CLA.md).

---

*Un progetto [ALGORASTUDIO](https://algorastudio.it) — Software per il patrimonio culturale italiano.*
