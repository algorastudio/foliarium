# Guida all'installazione di Foliarium

Questa guida descrive un'installazione **da zero**, passo passo, a partire da una
macchina su cui non è presente nulla (né Python, né PostgreSQL, né Foliarium).

Scegli il percorso adatto al tuo caso:

| Percorso | Quando usarlo |
|---|---|
| **A — Installer Windows** | Postazione di lavoro Windows, utente finale |
| **B — Portatile Windows** | Valutazione rapida, chiavetta USB, nessuna installazione di sistema |
| **C — Da sorgenti** | Sviluppo, Linux/macOS, server di archivio |

---

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

- Sistema operativo: Windows 10/11 o Linux (Ubuntu 22.04+, Debian 12+, Fedora 38+)
- Python 3.12 (64-bit) — solo se si esegue dai sorgenti
- PyQt6 6.8.1

**Server:**

- PostgreSQL 14 o superiore (consigliato PostgreSQL 16+)
- Estensioni PostgreSQL: `uuid-ossp`, `pg_trgm`, `pgcrypto`
  (tutte incluse in `postgresql-contrib`)
- Sistema operativo: qualsiasi sistema supportato da PostgreSQL

---

## Percorso A — Installer Windows (utente finale)

1. Scarica `Foliarium_Setup_x.y.z.exe` dalla pagina Releases.
2. Esegui l'installer **come amministratore**: copia i file, esegue
   `setup_database.bat` (che a sua volta chiama `setup_database.py`) e registra
   il servizio Windows `FoliariumDB`.
3. Al termine l'installer mostra le credenziali generate: annotale.
   Il file `config.ini` viene scritto accanto a `Foliarium.exe`.
4. Copia il file di licenza `foliarium.license` ricevuto da Algora Studio nella
   cartella di installazione, accanto a `Foliarium.exe`.
5. Avvia **Foliarium.exe** e accedi con l'utente `admin` e la password mostrata
   dall'installer. **Cambiala subito** da *Gestione Utenti*.

I dati del cluster PostgreSQL finiscono in `%ProgramData%\Foliarium\pg_data`
(non in `Program Files`: `initdb` non può scrivere lì).

Dettagli su percorsi, porte e disinstallazione nella
[guida amministratore](admin/installazione.md).

---

## Percorso B — Versione portatile (Windows)

Non installa nulla nel sistema, a parte Python.

1. Installa **Python 3.12** da [python.org](https://www.python.org/downloads/),
   spuntando *"Add Python to PATH"*.
2. Scarica i binari PostgreSQL ZIP da
   [EnterpriseDB](https://www.enterprisedb.com/download-postgresql-binaries)
   (Windows x86-64).
3. Estrai l'archivio e copia la cartella `pgsql` dentro `portable/`, così da
   ottenere `portable\pgsql\bin\`.
4. Doppio clic su **`portable\setup_primo_avvio.bat`**: inizializza il cluster in
   `portable\pgdata`, crea `catasto_storico`, installa le dipendenze Python,
   applica lo schema e (opzionalmente) i dati dimostrativi.
5. Da quel momento in poi avvia con **`portable\avvia_foliarium.bat`** e arresta
   il database con **`portable\arresta_foliarium.bat`**.

PostgreSQL portatile gira sulla porta **5433** (per non confliggere con
installazioni esistenti) e usa autenticazione `trust`: adatto solo a uso locale.
Dettagli completi in [portable/README_PORTABLE.md](../portable/README_PORTABLE.md).

---

## Percorso C — Installazione da sorgenti (passo passo)

### 1. Installare Python 3.12

**Ubuntu / Debian:**

```bash
sudo apt update
sudo apt install python3.12 python3.12-venv python3-pip git
```

**Windows:** scarica l'installer 64-bit da
[python.org](https://www.python.org/downloads/) e spunta *"Add Python to PATH"*.

Verifica: `python3 --version` (Windows: `python --version`) deve stampare `3.12.x`.

### 2. Installare PostgreSQL

**Ubuntu / Debian:**

```bash
sudo apt install postgresql postgresql-contrib
sudo systemctl enable --now postgresql
```

**Windows:** scarica l'installer da
[postgresql.org](https://www.postgresql.org/download/windows/) e segui la
procedura guidata. Annota la password scelta per il superuser `postgres`:
servirà al passo 5.

Verifica che il server risponda:

```bash
pg_isready -h 127.0.0.1 -p 5432
```

> **Password del superuser su Linux.** Su Ubuntu/Debian l'utente `postgres` usa
> per default l'autenticazione `peer` e non ha password. Poiché
> `setup_database.py` si connette in TCP su `127.0.0.1`, imposta una password:
>
> ```bash
> sudo -u postgres psql -c "ALTER USER postgres PASSWORD 'postgres';"
> ```
>
> e assicurati che `pg_hba.conf` contenga
> `host all all 127.0.0.1/32 scram-sha-256`.

### 3. Clonare il repository

```bash
git clone https://github.com/algorastudio/foliarium.git
cd foliarium
```

### 4. Creare l'ambiente virtuale e installare le dipendenze

```bash
python3 -m venv venv
source venv/bin/activate          # Linux / macOS
# venv\Scripts\activate           # Windows

pip install --upgrade pip
pip install -r requirements.txt
```

Su Linux servono anche alcune librerie di sistema per Qt6:

```bash
sudo apt install libgl1 libegl1 libxkbcommon-x11-0 libdbus-1-3
```

### 5. Inizializzare il database

`setup_database.py` fa **tutto in un colpo solo**: crea il ruolo applicativo e il
database, applica tutti gli script SQL nell'ordine corretto, crea l'utente
amministratore dell'applicazione e scrive `config.ini`.

```bash
# Linux / macOS (ricerca automatica dei binari PostgreSQL nel PATH)
python setup_database.py --pg-bin auto --postgres-password <password_di_postgres>

# Windows (indicando la cartella bin di PostgreSQL 17)
python setup_database.py --pg-bin "C:\Program Files\PostgreSQL\17\bin" --postgres-password <password_di_postgres>
```

> **`--pg-bin` è obbligatorio in questo scenario.** Senza `--pg-bin` lo script
> parte in *modalità bundle* e cerca un PostgreSQL portabile in `./pgsql/bin`
> (quello incluso nell'installer). Con un PostgreSQL di sistema già in esecuzione
> serve sempre `--pg-bin <path|auto>`.

#### Opzioni principali

| Opzione | Default | Descrizione |
|---|---|---|
| `--pg-bin <path\|auto>` | — | Cartella `bin/` di PostgreSQL oppure `auto` |
| `--postgres-password` | *(vuoto)* | Password del superuser `postgres` |
| `--db-name` | `catasto_storico` | Nome del database |
| `--db-user` | `foliarium` | Ruolo PostgreSQL dell'applicazione |
| `--db-password` | *(generata)* | Password del ruolo applicativo |
| `--admin-password` | *(generata)* | Password dell'utente `admin` applicativo |
| `--port` | `5432` | Porta PostgreSQL |
| `--config-file` | `config.ini` | Percorso del file di configurazione da scrivere |
| `--uninstall` | — | Rimuove servizio, dati e `config.ini` |

> **Annota la password admin stampata a fine setup.** Se non passi
> `--admin-password`, lo script ne **genera una casuale** e la stampa nel
> riepilogo finale (`Utente admin: admin / <password>`). Non è recuperabile in
> seguito. Per sceglierla in anticipo:
>
> ```bash
> python setup_database.py --pg-bin auto \
>     --postgres-password <password_postgres> \
>     --admin-password <password_admin_scelta_da_te>
> ```

Il file `config.ini` generato accanto allo script contiene le credenziali ed è
escluso dal controllo versione tramite `.gitignore`. La sezione `[database]`
usa le chiavi `host`, `port`, `dbname`, `user`, `password` — attenzione: la
chiave è `dbname`, non `database`.

In alternativa a `config.ini` puoi usare le variabili d'ambiente `DB_HOST`,
`DB_NAME`, `DB_USER`, `DB_PASS`, `DB_PORT`. L'ordine di precedenza è
**`config.ini` → variabili d'ambiente → default**.

### 6. Configurare la licenza

Foliarium in modalità normale **non si avvia senza una licenza valida**: allo
startup `validate_license_and_acquire_seat()` verifica la firma HMAC-SHA256 del
file `foliarium.license` e termina il processo se manca o non è valida.

**Se hai ricevuto la licenza da Algora Studio**, copia `foliarium.license` nella
cartella del progetto (accanto a `gui_main.py`) — oppure indicane il percorso da
*Impostazioni → Gestione Licenza…* dopo il primo avvio riuscito.

**Se stai allestendo un ambiente tuo** (sviluppo, test interni), genera prima la
chiave di firma e poi la licenza:

```bash
# 1. Chiave HMAC di firma — una sola volta per ambiente
python generate_key.py --save-base-dir     # crea foliarium.key nella root del progetto

# 2. File di licenza firmato con quella chiave
python generate_license.py generate \
    --to "Archivio di prova" \
    --type standard --seats 1 \
    --expiry 2027-12-31 \
    --out foliarium.license

# 3. Verifica
python generate_license.py inspect foliarium.license
```

> **Non committare mai `foliarium.key`.** La chiave firma tutte le licenze
> dell'ambiente: se la perdi, ogni file `.license` esistente diventa invalido; se
> viene compromessa va rigenerata e tutte le licenze vanno rifirmate. In
> alternativa al file puoi esportarla come variabile d'ambiente
> `FOLIARIUM_LICENSE_KEY`, che ha la precedenza sul file.

### 7. Avviare Foliarium

```bash
python gui_main.py
```

Al primo avvio: accetta l'EULA, poi accedi con l'utente `admin` e la password
definita al passo 5. **Cambiala subito** da *Gestione Utenti*.

Per un giro di prova senza licenza c'è la modalità demo, che salta la validazione
della licenza e fa login automatico:

```bash
python gui_main.py --demo
```

Il PostgreSQL embedded della demo esiste solo nel pacchetto demo distribuito
(cartelle `pgsql/` e `demo_data/` nel bundle); dai sorgenti la modalità demo usa
comunque il database configurato in `config.ini`.

### 8. Verificare l'installazione

```bash
# Le tabelle dello schema catasto sono presenti?
psql -h 127.0.0.1 -U foliarium -d catasto_storico -c "\dt catasto.*" | head

# L'utente admin applicativo è stato creato?
psql -h 127.0.0.1 -U foliarium -d catasto_storico \
     -c "SELECT username, ruolo, attivo FROM catasto.utente;"
```

Facoltativo, per una verifica più completa:

```bash
psql -h 127.0.0.1 -U foliarium -d catasto_storico -f sql_scripts/utils/validate_install.sql
```

Dall'applicazione, i segnali che tutto è a posto sono: login riuscito, indicatore
"Database: Connesso" nella barra superiore, elenco comuni popolato in
Consultazione.

---

## Cosa fa esattamente `setup_database.py`

Utile per capire cosa è successo, o per rifare i passi a mano in caso di problemi.
Gli script vengono applicati in quest'ordine su un database fresco:

| # | Script | Contenuto |
|---|---|---|
| 1 | `schema/01_tables.sql` | Tabelle, vincoli, indici base, lookup, `audit_log` |
| 2 | `functions/01_core.sql` | Trigger timestamp, funzioni di inserimento, viste |
| 3 | `functions/02_crud.sql` | Procedure CRUD (immobili, variazioni, duplicazione) |
| 4 | `functions/03_workflow.sql` | Workflow: registrazione proprietà, passaggi, frazionamenti |
| 5 | `functions/04_search.sql` | Ricerca fuzzy trigram + ricerca avanzata |
| 6 | `functions/05_reporting.sql` | Viste materializzate + funzioni di report |
| 7 | `functions/06_audit.sql` | Trigger di audit su tutte le tabelle |
| 8 | `functions/07_features.sql` | Genealogia, documenti storici, statistiche |
| 9 | `admin/01_users.sql` | Utenti applicativi, permessi, sessioni |
| 10 | `admin/02_backup.sql` | Registro backup e procedure |
| 11 | `admin/03_performance.sql` | Procedure VACUUM/REINDEX |
| 12 | `schema/02_trigram_indexes.sql` | Indici GIN `CONCURRENTLY` (fuori transazione) |
| — | `admin/04_bootstrap_admin.sql` | Utente `admin` (richiede `-v admin_password`) |

Al termine lo script assegna i privilegi al ruolo applicativo e gli trasferisce
l'ownership delle materialized view (necessaria per `REFRESH MATERIALIZED VIEW`).

Gli script in `sql_scripts/migrations/` servono **solo** per aggiornare database
già esistenti: non vanno mai applicati su un'installazione fresca.

---

## Aggiornamento

```bash
cd foliarium
git pull origin main
source venv/bin/activate
pip install -r requirements.txt
python gui_main.py
```

All'avvio, `db/base.py` applica automaticamente le migrazioni di schema
idempotenti e sicure. Le migrazioni non automatiche restano in
`sql_scripts/migrations/` e vanno applicate manualmente (vedi
`sql_scripts/README.md` per la tabella "quando applicarlo").

---

## Disinstallazione

```bash
python setup_database.py --uninstall     # servizio + dati + config.ini
```

Su Windows esiste anche `uninstall_database.bat`. La disinstallazione
**cancella i dati del database**: fai prima un backup con `pg_dump`.

---

## Risoluzione problemi

### "Password del database non configurata" all'avvio

In modalità non-demo Foliarium rifiuta di connettersi con password vuota
(`config.assert_db_password_configured()`). Verifica che `config.ini` sia nella
cartella giusta e contenga `[database] password = ...`, oppure imposta `DB_PASS`.

### `psql: could not connect to server` durante il setup

- Il servizio è attivo? `sudo systemctl status postgresql` oppure `pg_isready`
- La porta è quella giusta? Usa `--port` se PostgreSQL non è su 5432
- Il superuser richiede password? Passa `--postgres-password`
- `pg_hba.conf` consente connessioni TCP da `127.0.0.1`?

### `FATAL: password authentication failed for user "foliarium"`

`config.ini` e il ruolo PostgreSQL sono fuori sincrono (tipico se il setup è stato
rilanciato: il ruolo esiste già e la password **non** viene riscritta). Allinea:

```bash
sudo -u postgres psql -c "ALTER USER foliarium PASSWORD 'password_di_config_ini';"
```

### Non ricordo la password di `admin`

Rilancia solo il bootstrap dopo aver rimosso l'utente (lo script è idempotente e
non tocca un `admin` già esistente):

```bash
psql -h 127.0.0.1 -U foliarium -d catasto_storico \
     -c "DELETE FROM catasto.utente WHERE username = 'admin';"
psql -h 127.0.0.1 -U foliarium -d catasto_storico \
     -v admin_password="nuova_password" -v admin_email="admin@archivio.local" \
     -f sql_scripts/admin/04_bootstrap_admin.sql
```

### "Licenza non valida" e l'app si chiude

- Il file si chiama esattamente `foliarium.license` ed è accanto all'eseguibile
  (o a `gui_main.py` dai sorgenti)?
- È stato firmato con la stessa chiave (`foliarium.key` /
  `FOLIARIUM_LICENSE_KEY`) che l'installazione sta usando?
- Non è scaduto? Controlla con `python generate_license.py inspect`.
- È vincolato a un altro PC? Confronta con `python generate_license.py fingerprint`.

### Errore di avvio dell'interfaccia grafica

- PyQt6 è installato nel venv attivo? `pip show PyQt6`
- Su Linux: `sudo apt install libgl1 libegl1 libxkbcommon-x11-0`
- Server headless senza X/Wayland: usa `QT_QPA_PLATFORM=offscreen` per i soli
  test automatici

### Errore sulle estensioni PostgreSQL

`uuid-ossp`, `pg_trgm` e `pgcrypto` richiedono privilegi superuser e il pacchetto
`postgresql-contrib`:

```bash
sudo apt install postgresql-contrib
```

### Esportare i log per il supporto

Dall'applicazione: **Help → Esporta log per supporto (.zip)…**. L'archivio
contiene solo i log applicativi — nessun dato del database, nessuna credenziale.

---

## Supporto professionale

Per assistenza nell'installazione e configurazione, contatta **ALGORASTUDIO**:

- Email: santoromarco@gmail.com
- Sito: [algorastudio.it](https://algorastudio.it)
