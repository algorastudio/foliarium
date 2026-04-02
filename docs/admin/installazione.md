# Installazione e Configurazione

## Prerequisiti

### Software richiesto

| Software | Versione | Scarica da |
|---|---|---|
| Python | 3.12 (64-bit) | python.org |
| PostgreSQL | 14 o superiore | postgresql.org |
| Git (opzionale) | qualsiasi | git-scm.com |

### Dipendenze Python

Installare le dipendenze con:

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

## Installazione tramite installer (Windows)

1. Eseguire **Foliarium_Setup_v1.5exe** come amministratore
2. Seguire la procedura guidata
3. Al termine, configurare la connessione al database (vedi sezione successiva)

> 📸 **Screenshot:** Procedura guidata di installazione Foliarium con barra di avanzamento.

---

## Installazione manuale (sorgente)

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

## Configurazione del database

### Creazione del database

Aprire pgAdmin o psql e creare il database:

```sql
CREATE DATABASE catasto_storico;
```

### Esecuzione degli script SQL

Eseguire gli script nella cartella `sql_scripts/` nell'ordine indicato:

```
1. Creazione del Database Catasto Storico
2. Creazione dello Schema e delle Tabelle
3. Funzioni e Procedure
4. Dati di Esempio (opzionale)
5. Query di Test e Utilizzo (verifica)
```

In pgAdmin: *Tools → Query Tool*, aprire ciascun file ed eseguire.

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
DB_USER=meridiana_user
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
noVNC desktop → http://localhost:6080 (password: meridiana)
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

### Build Demo portabile

La build demo include PostgreSQL 14 portabile e i dati dimostrativi. Viene prodotta
automaticamente dal pipeline CI (`build-demo`), ma può essere generata localmente:

```bash
# 1. Scarica e posiziona PostgreSQL 14 portabile in pgsql/
#    (EnterpriseDB binaries: https://www.enterprisedb.com/download-postgresql-binaries)

# 2. Prepara il database demo (initdb + schema + dati Savona)
python prepare_demo_db.py --pgsql-dir pgsql

# 3. Compila il bundle demo
pyinstaller foliarium_demo.spec

# 4. Crea lo ZIP portabile
Compress-Archive -Path dist\Foliarium_Demo\* -DestinationPath Foliarium_Demo_Portabile.zip
```

Il bundle `dist/Foliarium_Demo/` contiene:
- `Foliarium_Demo.exe` — eseguibile principale
- `pgsql/` — binari PostgreSQL 14 portabili
- `demo_data/` — cluster PostgreSQL pre-inizializzato con dati Savona

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
