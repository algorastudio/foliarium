# Guida all'installazione di Foliarium

## Requisiti

### Requisiti hardware minimi

**Postazione client:**
- Processore: dual-core 2 GHz o superiore
- RAM: 4 GB minimo (8 GB consigliati)
- Spazio disco: 500 MB per l'applicazione
- Risoluzione schermo: 1280x720 minimo (1920x1080 consigliata)

**Server database:**
- Processore: quad-core 2 GHz o superiore
- RAM: 4 GB minimo (8 GB consigliati per archivi di grandi dimensioni)
- Spazio disco: variabile in base alla dimensione dell'archivio catastale
- Connessione di rete stabile tra client e server

### Requisiti software

**Client:**
- Sistema operativo: Windows 10/11 o Linux (Ubuntu 20.04+, Debian 11+, Fedora 35+)
- Python 3.12 (64-bit)
- PyQt6 6.8.1+

**Server:**
- PostgreSQL 14 o superiore (consigliato PostgreSQL 16+)
- Estensioni PostgreSQL: `uuid-ossp`, `pg_trgm` (opzionale: `system_stats`)
- Sistema operativo: qualsiasi sistema supportato da PostgreSQL

## Installazione rapida (Versione Portatile — consigliata per Windows)

Se vuoi provare Foliarium rapidamente senza installare PostgreSQL nel sistema:

1. Scarica i binari PostgreSQL ZIP da [EnterpriseDB](https://www.enterprisedb.com/download-postgresql-binaries) (Windows x86-64)
2. Estrai la cartella `pgsql` dentro `portable/`
3. Esegui **`portable\setup_primo_avvio.bat`** — configura tutto automaticamente
4. Da quel momento in poi, usa **`portable\avvia_foliarium.bat`** per avviare

Per i dettagli completi, consulta [portable/README_PORTABLE.md](../portable/README_PORTABLE.md).

---

## Installazione completa (passo-passo)

### 1. Installare PostgreSQL

#### Su Ubuntu/Debian:
```bash
sudo apt update
sudo apt install postgresql postgresql-contrib
```

#### Su Windows:
Scarica l'installer da [postgresql.org](https://www.postgresql.org/download/windows/) e segui la procedura guidata.

### 2. Creare il database

Esegui lo script di creazione del database (richiede privilegi superuser PostgreSQL):

```bash
sudo -u postgres psql -f database/01_creazione-database.sql
```

In alternativa, connettiti a PostgreSQL manualmente:

```bash
sudo -u postgres psql
```

```sql
CREATE USER foliarium_user WITH PASSWORD 'scegli_una_password_sicura';
CREATE DATABASE catasto_storico OWNER foliarium_user ENCODING 'UTF8';
GRANT ALL PRIVILEGES ON DATABASE catasto_storico TO foliarium_user;
\q
```

### 3. Installare Foliarium

```bash
git clone https://github.com/algorastudio/foliarium.git
cd foliarium
python -m venv venv
source venv/bin/activate  # Linux
# oppure: venv\Scripts\activate  # Windows
pip install -r requirements.txt
```

### 4. Inizializzare il database

Usa `setup_database.py` per creare il database, applicare tutti gli script SQL
e generare `config.ini` in un'unica operazione:

```bash
# Windows (PostgreSQL 17)
python setup_database.py --pg-bin "C:\Program Files\PostgreSQL\17\bin" --postgres-password <password_postgres>

# Linux / macOS (ricerca automatica)
python setup_database.py --pg-bin auto --postgres-password <password_postgres>
```

#### Opzioni principali

| Opzione | Default | Descrizione |
|---|---|---|
| `--pg-bin <path\|auto>` | — | Cartella `bin/` di PostgreSQL oppure `auto` |
| `--postgres-password` | *(vuoto)* | Password del superuser `postgres` |
| `--db-name` | `catasto_storico` | Nome del database |
| `--db-user` | `foliarium` | Ruolo PostgreSQL dell'applicazione |
| `--db-password` | *(generata)* | Password ruolo applicativo |
| `--admin-password` | *(generata)* | Password utente admin applicativo |
| `--port` | `5432` | Porta PostgreSQL |
| `--config-file` | `config.ini` | Percorso del file di configurazione da scrivere |

**Nota:** il file `config.ini` contiene credenziali ed è escluso dal controllo versione tramite `.gitignore`.

### 5. Avviare Foliarium

```bash
python gui_main.py
```

L'applicazione legge i parametri di connessione dal `config.ini` generato.
Al primo avvio accedere con le credenziali `admin / admin123` e cambiare
immediatamente la password.

## Struttura del progetto

```
foliarium/
├── gui_main.py                 # Entry point applicazione
├── setup_database.py           # Inizializzazione database (cross-platform)
├── catasto_db_manager.py       # Facade accesso database
├── app_paths.py                # Gestione percorsi applicazione
├── config.py                   # Configurazione e logging
├── app_utils.py                # Utility ed esportazioni
├── sql_scripts/                # Script SQL (schema, procedure, migrazioni)
├── foliarium/ui/               # Widget e dialoghi PyQt6
├── db/                         # Layer database (14 mixin)
└── docs/                       # Documentazione
```

## Aggiornamento

Per aggiornare Foliarium all'ultima versione:

```bash
cd foliarium
git pull origin main
pip install -r requirements.txt
```

Se necessario, esegui gli script SQL aggiornati per le migrazioni dello schema.

## Risoluzione problemi

### Errore di connessione al database
- Verifica che PostgreSQL sia in esecuzione: `sudo systemctl status postgresql`
- Controlla i parametri in `config.ini`
- Verifica che il firewall consenta la connessione sulla porta 5432
- Verifica che `pg_hba.conf` permetta connessioni dall'host del client

### Errore di avvio dell'interfaccia grafica
- Verifica che PyQt6 sia installato: `pip install PyQt6`
- Su Linux, potrebbe servire: `sudo apt install python3-pyqt6 libgl1`
- Per problemi con il display su Linux: verifica che `$DISPLAY` sia impostato oppure usa `QT_QPA_PLATFORM=offscreen` per test headless

### Errore estensioni PostgreSQL
- Le estensioni `uuid-ossp` e `pg_trgm` vanno installate con privilegi superuser
- Su Debian/Ubuntu: `sudo apt install postgresql-contrib`

## Supporto professionale

Per assistenza nell'installazione e configurazione, contatta **ALGORASTUDIO**:
- Email: santoromarco@gmail.com
- Sito: [algorastudio.it](https://algorastudio.it)
