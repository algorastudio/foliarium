# Installazione e Configurazione

## Installer unificato (raccomandato) — Windows

Dalla versione **1.6.0** è disponibile un **installer unificato** che
include tutto il necessario: applicazione Foliarium, PostgreSQL 14
embedded, script di inizializzazione database e scorciatoie nel
menu Start. **Non è più necessario installare PostgreSQL separatamente.**

### Procedura

1. Scaricare `Foliarium_1.6.0_Unified_Setup.exe` dalle Release GitHub
2. Eseguire come **amministratore** (richiesto per registrare il servizio Windows)
3. Seguire la procedura guidata (Next → Install)
4. Attendere la fase "Configurazione database in corso…" (30–60 s)
5. Al termine viene mostrata la password admin temporanea (`admin / admin123`)

Durante l'installazione vengono eseguite automaticamente tutte le fasi:

1. Estrazione dei binari PostgreSQL in `C:\Program Files (x86)\Foliarium\pgsql\`
2. `initdb` del cluster in `C:\ProgramData\Foliarium\pg_data\`
3. Generazione password casuale (16 caratteri) per l'utente `foliarium`
4. Configurazione `pg_hba.conf` con `scram-sha-256`
5. Registrazione del servizio Windows `FoliariumDB` (avvio automatico)
6. Esecuzione degli script SQL di schema, procedure, user management
7. Creazione utente admin applicativo (`admin / admin123`)
8. Scrittura di `config.ini` accanto a `Foliarium.exe`

!!! warning "Cambia la password admin al primo accesso"
    La password di default `admin123` è generata per comodità dell'installazione.
    **Deve essere cambiata immediatamente** al primo accesso tramite
    *Impostazioni → Cambia Password*.

!!! info "Porte di rete"
    L'installer verifica se la porta 5432 è occupata. Se lo è, prova
    automaticamente 5433 e poi 5434. La porta effettiva viene salvata
    in `config.ini` nella cartella di installazione.

### Posizione file critici

| File / cartella | Percorso |
|-----------------|----------|
| Eseguibile | `C:\Program Files (x86)\Foliarium\Foliarium.exe` |
| `config.ini` | `C:\Program Files (x86)\Foliarium\config.ini` |
| `foliarium.license` (da fornire) | `C:\Program Files (x86)\Foliarium\foliarium.license` |
| Dati DB | `C:\ProgramData\Foliarium\pg_data\` |
| Log app | `%LOCALAPPDATA%\Foliarium\logs\` |
| Log installer DB | `C:\Program Files (x86)\Foliarium\setup_database.log` |
| Cache offline | `%LOCALAPPDATA%\Foliarium\cache\` |

### Disinstallazione

Usare *Pannello di controllo → Programmi e funzionalità* o lo
shortcut *Disinstalla Foliarium* nel menu Start. L'uninstaller ferma
il servizio `FoliariumDB`, lo deregistra e rimuove tutti i file,
incluso il database (`pg_data/`).

!!! warning "Backup prima di disinstallare"
    La disinstallazione elimina **tutti i dati** del database.
    Effettuare un backup da *Sistema → Backup* prima di procedere.

---

## Installazione manuale da sorgente (sviluppo)

### Prerequisiti

| Software | Versione | Scarica da |
|---|---|---|
| Python | 3.12 (64-bit) | python.org |
| PostgreSQL | 14 o superiore | postgresql.org |
| Git (opzionale) | qualsiasi | git-scm.com |

### Dipendenze Python

```bash
pip install -r requirements.txt
```

Le dipendenze principali includono:

```
PyQt6==6.8.1
psycopg2-binary==2.9.10
pandas==2.3.0
fpdf2==2.8.3
bcrypt==4.3.0
keyring==25.6.0
matplotlib>=3.9.0
odfpy>=1.4.1
openpyxl==3.1.5
```

---

### Clone e setup

```bash
# 1. Clonare il repository
git clone <url-repository> catasto
cd catasto

# 2. Creare e attivare il virtual environment
python -m venv .venv
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # Linux/Mac

# 3. Installare le dipendenze
pip install -r requirements.txt

# 4. Avviare l'applicazione
python gui_main.py
```

---

## Configurazione manuale del database (solo sorgente)

!!! note "Solo per installazioni da sorgente"
    L'installer unificato (sezione precedente) **inizializza
    automaticamente** il database. Questa sezione serve solo a chi
    installa Foliarium da sorgente o utilizza un PostgreSQL preesistente.

### Script automatico `setup_database.py`

Il modo più rapido per inizializzare il database è usare lo script incluso,
che crea il database, esegue tutti gli script SQL nell'ordine corretto e
scrive il file `config.ini`.

**Utilizzo base (PostgreSQL 17 già installato su Windows):**

```powershell
python setup_database.py --pg-bin "C:\Program Files\PostgreSQL\17\bin" --postgres-password <password_postgres>
```

**Ricerca automatica del PostgreSQL nel PATH:**

```powershell
python setup_database.py --pg-bin auto --postgres-password <password_postgres>
```

#### Opzioni disponibili

| Opzione | Default | Descrizione |
|---|---|---|
| `--pg-bin <path\|auto>` | — | Percorso `bin/` di PostgreSQL, oppure `auto` per ricerca automatica |
| `--postgres-password` | *(vuoto)* | Password del superuser `postgres` |
| `--db-name` | `catasto_storico` | Nome del database da creare |
| `--db-user` | `foliarium` | Ruolo PostgreSQL dell'applicazione |
| `--db-password` | *(generata)* | Password per il ruolo applicativo (generata casualmente se omessa) |
| `--admin-password` | *(generata)* | Password utente admin applicativo |
| `--port` | `5432` | Porta PostgreSQL |
| `--config-file` | `config.ini` | Percorso/nome del file di configurazione da scrivere |

**Esempio con opzioni personalizzate:**

```powershell
python setup_database.py `
    --pg-bin "C:\Program Files\PostgreSQL\17\bin" `
    --postgres-password postgres `
    --db-name archivio_savona `
    --db-user archivio_user `
    --admin-password AdminSicuro2025 `
    --config-file archivio_savona.ini
```

!!! info "Risultato"
    Al termine lo script stampa le credenziali generate e il percorso
    del file di configurazione scritto. Conservare questi dati in luogo sicuro.

### Creazione manuale del database

In alternativa allo script, aprire pgAdmin o psql e creare il database:

```sql
CREATE DATABASE catasto_storico;
```

### Esecuzione manuale degli script SQL

Eseguire gli script nella cartella `sql_scripts/` nell'ordine indicato:

```
1. Creazione del Database Catasto Storico
2. Creazione dello Schema e delle Tabelle
3. Funzioni e Procedure
4. Dati di Esempio (opzionale)
5. Query di Test e Utilizzo (verifica)
```

In pgAdmin: *Tools → Query Tool*, aprire ciascun file ed eseguire.

### Migrazioni post-installazione

Dopo aver eseguito gli script base, applicare le migrazioni pendenti:

```bash
python bin/migrate.py status   # mostra cosa e' applicato vs pendente
python bin/migrate.py up       # applica tutte le pending
```

Vedi la guida dedicata *Migrazioni Schema* per il dettaglio (naming
convention, tracking via `catasto.schema_version`, rollback).

!!! info "Vista audit applicata automaticamente"
    Dalla v1.0.1 la vista `catasto.v_audit_dettagliato` (necessaria al
    visualizzatore Audit Log) viene **creata automaticamente** al primo
    avvio se mancante (`db/base.py::_ensure_audit_view`). I DB
    inizializzati prima dello script `18_funzioni_trigger_audit.sql`
    non richiedono più migrazione manuale.

### Configurazione credenziali

Foliarium legge le credenziali del database dalle **variabili d'ambiente** di Windows:

| Variabile | Default | Descrizione |
|---|---|---|
| `DB_HOST` | `localhost` | Indirizzo del server PostgreSQL |
| `DB_USER` | `postgres` | Utente del database |
| `DB_PASS` | *(vuoto)* | Password del database |
| `DB_NAME` | `catasto_storico` | Nome del database |
| `DB_PORT` | `5432` | Porta TCP |

#### Impostazione variabili su Windows

**Metodo 1: Dialog GUI di Foliarium**
Andare in *Impostazioni → Configura Connessione Database* e inserire i dati nella finestra.

**Metodo 2: Variabili d'ambiente di sistema**
1. Aprire *Pannello di Controllo → Sistema → Impostazioni di sistema avanzate*
2. Fare clic su **Variabili d'ambiente**
3. Aggiungere le variabili nella sezione "Variabili di sistema"

**Metodo 3: File `.env` nella cartella dell'applicazione**

```ini
DB_HOST=192.168.1.100
DB_USER=foliarium
DB_PASS=password_sicura
DB_NAME=catasto_storico
DB_PORT=5432
```

!!! warning "Sicurezza password"
    Le password non vengono mai salvate in QSettings. Vengono memorizzate nel **keyring di Windows** (Gestione credenziali) oppure lette dalla variabile d'ambiente. Non inserire password in file di testo non cifrati in ambienti di produzione.

---

## Abilitazione Long Paths (Windows)

Su Windows 10/11, i percorsi file possono essere limitati a 260 caratteri. Per abilitare i percorsi lunghi:

**Metodo 1: Group Policy (richiede privilegi admin)**
1. Aprire `gpedit.msc`
2. Navigare su *Configurazione Computer → Modelli Amministrativi → Sistema → File System*
3. Abilitare *"Enable Win32 long paths"*

**Metodo 2: Registro di sistema**
```powershell
# Eseguire come Amministratore
New-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Control\FileSystem" `
  -Name "LongPathsEnabled" -Value 1 -PropertyType DWORD -Force
```

**Alternativa:** Installare Python da un percorso corto (es. `C:\Python312\`) invece che da Microsoft Store.

---

## Verifica dell'installazione

Dopo la configurazione, avviare Foliarium e verificare:

1. Il login funziona correttamente
2. La barra di stato mostra "Database: Connesso"
3. La sezione Consultazione mostra l'elenco dei comuni
4. Una semplice ricerca restituisce risultati

---

## Dev Container (VS Code / Codespaces)

Per sviluppo o test in ambiente isolato:

```
noVNC desktop → http://localhost:6080 (password: foliarium)
PostgreSQL    → localhost:5432
QT_QPA_PLATFORM=xcb (impostato automaticamente)
```

Dopo la creazione del container eseguire:

```bash
bash .devcontainer/setup.sh
```

---

## Build dell'eseguibile

### Build standard (versione completa)

```bash
pyinstaller foliarium.spec
```

L'eseguibile viene generato in `dist/Foliarium/`. Per creare l'installer Windows usare
**Inno Setup** con lo script `Foliarium_Installer.iss`.

### Piattaforme distribuite

A partire dalla v1.0.2 il pipeline pubblica solo le 3 build effettivamente in uso:

| Build | Artifact | Trigger |
|---|---|---|
| `build-windows` | `Foliarium_Portabile.zip` + Inno Setup `.exe` | tag `*.*.*` |
| `build-linux` | tarball portabile | tag `*.*.*` |
| `build-macos` | zip portabile | tag `*.*.*` |

Le precedenti varianti `build-demo` (con PostgreSQL portabile) e `build-unified` (installer
combinato Foliarium+PostgreSQL+DB init in un singolo `.exe`) sono state rimosse: non erano
in produzione e rallentavano il ciclo di release senza valore commerciale.

---

## Gestione della licenza

### File di licenza

Foliarium richiede un file **`foliarium.license`** nella cartella dell'eseguibile
(o nel percorso configurato da *Impostazioni → Gestione Licenza…*).

Per generare una licenza per un cliente:

```bash
python generate_license.py generate \
    --to "Archivio di Stato di Savona" \
    --type standard \
    --seats 2 \
    --expiry 2027-12-31 \
    --out foliarium.license
```

Per vincolare la licenza a un hardware specifico (PC singolo):

```bash
# Prima mostrare il fingerprint del PC del cliente
python generate_license.py fingerprint

# Poi generare la licenza con --hardware
python generate_license.py generate \
    --to "Comune di Albenga" \
    --type standard \
    --seats 1 \
    --hardware a1b2c3d4e5f6a7b8 \
    --out albenga.license
```

### Verifica di un file .license esistente

```bash
python generate_license.py inspect foliarium.license
```

### Licenze multi-seat (rete)

Per installazioni con più istanze simultanee (tipo Enterprise), configurare
una cartella condivisa UNC accessibile da tutti i PC:

1. Creare una cartella condivisa, es. `\\SERVER\Foliarium\`
2. In ogni installazione: *Impostazioni → Gestione Licenza… → Cartella condivisa UNC*
3. Il coordinamento dei seat avviene automaticamente con TTL 120 s
