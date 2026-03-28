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
- Python 3.8 o superiore
- PyQt5 (5.15+)

**Server:**
- PostgreSQL 13 o superiore (consigliato PostgreSQL 15+)
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

### 4. Configurare la connessione al database

Copia il file di configurazione di esempio:

```bash
cp config.example.ini config.ini
```

Modifica `config.ini` con i dati del tuo database:

```ini
[database]
host = localhost
port = 5432
database = catasto_storico
user = foliarium_user
password = scegli_una_password_sicura

[application]
language = it
theme = default
log_level = INFO
```

**Nota:** il file `config.ini` contiene credenziali ed è escluso dal controllo versione tramite `.gitignore`.

### 5. Inizializzare lo schema del database

Esegui lo script di setup che crea lo schema, le tabelle, le funzioni, le viste e gli indici:

```bash
python setup_db.py --host localhost --dbname catasto_storico --user postgres
```

Lo script eseguirà in ordine tutti i file SQL dalla cartella `database/` (escluso `01_creazione-database.sql` che va eseguito al passo 2).

Per caricare anche i dati demo (utili per test e valutazione):

```bash
python setup_db.py --host localhost --dbname catasto_storico --user postgres --demo
```

### 6. Creare l'utente amministratore

Esegui lo script SQL di creazione admin in PostgreSQL:

```bash
psql -h localhost -d catasto_storico -U postgres -f database/crea_admin_interattivo.sql
```

### 7. Avviare Foliarium

```bash
python main.py
```

L'applicazione si connetterà al database usando i parametri configurati. Al primo avvio verrà mostrato il dialogo di configurazione connessione dove è possibile inserire o modificare i parametri di connessione.

## Struttura del progetto

```
foliarium/
├── main.py                     # Entry point applicazione
├── setup_db.py                 # Inizializzazione database
├── src/                        # Codice sorgente Python
│   ├── app_paths.py            # Gestione percorsi applicazione
│   ├── config.py               # Configurazione e logging
│   ├── catasto_db_manager.py   # Accesso database PostgreSQL
│   ├── gui_main.py             # Finestra principale
│   ├── gui_widgets.py          # Widget interfaccia
│   ├── dialogs.py              # Dialoghi
│   ├── custom_widgets.py       # Widget personalizzati
│   └── app_utils.py            # Utility e funzioni di esportazione
├── database/                   # Script SQL
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
- Verifica che PyQt5 sia installato: `pip install PyQt5`
- Su Linux, potrebbe servire: `sudo apt install python3-pyqt5 python3-pyqt5.qtwebengine`
- Per problemi con il display su Linux: verifica che `$DISPLAY` sia impostato

### Errore estensioni PostgreSQL
- Le estensioni `uuid-ossp` e `pg_trgm` vanno installate con privilegi superuser
- Su Debian/Ubuntu: `sudo apt install postgresql-contrib`

## Supporto professionale

Per assistenza nell'installazione e configurazione, contatta **ALGORASTUDIO**:
- Email: santoromarco@gmail.com
- Sito: [algorastudio.it](https://www.algorastudio.it)
