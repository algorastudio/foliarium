# Foliarium — deployment Docker

Stack completo (PostgreSQL 14 + FastAPI + React) in due container orchestrati
da `docker compose`.

> Questa pagina riguarda l'interfaccia **web**. La demo che mostra ai clienti
> l'applicazione desktop dentro il browser è un'altra cosa e sta in
> [`docker/demo/`](demo/README.md).

## Quick start

Dalla root del repository:

```bash
# 1. Build e avvio (la prima volta scarica/build, ~5–10 min)
docker compose up -d --build

# 2. Tail dei log per verificare che tutto sia partito
docker compose logs -f app

# 3. Apri il browser su:
#    http://localhost:8765/
#
#    Login: admin, con la password indicata in ADMIN_PASSWORD
#    (se non la imposti vale `admin123`, adatta solo allo sviluppo).
```

## Comandi utili

```bash
# Stato dei servizi
docker compose ps

# Ricostruire e riavviare l'app dopo una modifica al codice Python, al
# frontend o a requirements-web.txt: il codice e' copiato nell'immagine,
# un semplice `docker compose restart app` non lo rilegge
docker compose up -d --build app

# Prova completa dello stack (vedi «Prova dello stack» sotto)
bash docker/prova-web.sh

# Connessione psql al DB nel container
docker compose exec db psql -U postgres catasto_storico

# Stop senza perdere i dati
docker compose down

# Stop e RESET completo (cancella il DB!)
docker compose down -v
```

## Configurazione via env

Le variabili sono definite in `docker-compose.yml` con default sensati.
Per personalizzare crea un `.env` nella root del repo:

```env
DB_NAME=catasto_storico
DB_USER=postgres
DB_PASS=cambiami_in_produzione
DB_SCHEMA=catasto
ADMIN_PASSWORD=cambiami_in_produzione   # password dell'utente applicativo `admin`
DB_HOST_PORT=5433     # porta esposta sull'host per accesso esterno al DB
APP_PORT=8765         # porta esposta sull'host per la web app
DB_SSLMODE=prefer     # TLS verso il database (vedi sotto)
```

`DB_SSLMODE` ha default `prefer` nel compose. Senza, l'applicazione
tratterebbe `db` come un host remoto e imporrebbe `require`
(`DBConnectionBase._resolve_sslmode`), ma il PostgreSQL del container non ha
certificati e la connessione fallirebbe. Il database qui è sulla rete interna
del compose: `prefer` usa TLS se il server lo offre.

## Persistenza

I dati PostgreSQL sono salvati nel volume nominato `foliarium_db_data`.
Per fare backup:

```bash
# Dump del DB
docker compose exec db pg_dump -U postgres catasto_storico > backup.sql

# Restore
docker compose exec -T db psql -U postgres catasto_storico < backup.sql
```

## Struttura immagini

- **`foliarium-app`** (basata su `python:3.12-slim-bookworm`), il solo
  backend web: niente PyQt6 né librerie Qt di sistema.
  - Stage 1: `node:22-alpine` builda il frontend React (`npm run build`).
  - Stage 2: installa `requirements-web.txt` (FastAPI, uvicorn, psycopg2,
    bcrypt) e copia i soli moduli dell'API — `api/`, `db/`, `core/`,
    `utils/`, `catasto_db_manager.py`, `config.py`, `app_paths.py`,
    `catasto_exceptions.py`, `validators.py` — più `frontend/dist/`. È lo
    stesso contenuto dell'artefatto che `main_foliarium.yml` pubblica su
    Azure, e `tests/unit/test_docker_web.py` impedisce ai due elenchi di
    divergere.
  - `app_utils.py` resta fuori di proposito: importa PyQt6, e `api/main.py`
    lo usa solo per leggere la password dal portachiavi quando `DB_PASS`
    manca. Nel container `DB_PASS` c'è sempre.
  - Gira come utente `foliarium`, senza privilegi.
  - Avvia `uvicorn api.main:create_app --factory --host 0.0.0.0 --port 8765`.
  - Healthcheck su `GET /` ogni 30s, in Python (l'immagine non ha curl).
  - `ARG BASE_IMAGE` / `FRONTEND_BASE_IMAGE` sostituiscono le immagini di
    base: servono solo dove le build escono da un proxy con una CA propria.

- **`foliarium-db`** (basata su `postgres:14-bookworm`):
  - Aggiunge il locale `it_IT.UTF-8`.
  - Copia `sql_scripts/` in `/opt/foliarium-sql/` e `init.sh` in
    `/docker-entrypoint-initdb.d/00-init.sh`.
  - Al primo avvio applica gli stessi script dell'installer, nello stesso
    ordine (`SQL_SCRIPTS` in `setup_database.py`); un test impedisce ai due
    elenchi di divergere.
  - Crea l'utente applicativo `admin` solo se riceve
    `FOLIARIUM_ADMIN_PASSWORD` (il compose la valorizza da `ADMIN_PASSWORD`).

## Prova dello stack

```bash
bash docker/prova-web.sh
```

Costruisce le immagini, avvia lo stack con `docker compose up --wait` e
verifica: servizi sani, frontend servito su `/` con i suoi asset, login di
`admin` (con una password generata per la prova, passata in
`ADMIN_PASSWORD`), lettura dei comuni dal database, rifiuto di una password
errata, assenza di PyQt6 nell'immagine, app senza privilegi. Alla fine
toglie container e volume. Il workflow `web_docker.yml` la esegue a ogni
pull request.

Il compose usa nomi fissi (`foliarium-db`, `foliarium-app`, volume
`foliarium_db_data`): se uno di questi esiste già, la prova si rifiuta di
partire invece di cancellare il database in uso.

## Troubleshooting

**Login fallito al primo accesso?** L'app parte solo quando il database ha
finito gli script di init (l'healthcheck di `db` passa da TCP, che postgres
apre solo a inizializzazione conclusa). Se il login fallisce comunque,
verifica che gli script siano andati a buon fine:
```bash
docker compose logs db | grep foliarium-init
```
Devi vedere `[foliarium-init] Setup completato.` e l'utente `admin` creato.

**L'app risponde 503?** Il pool DB non si è ancora connesso. L'app fa retry
per 60s; se fallisce verifica i log: `docker compose logs app | grep "Pool DB"`.

**`server does not support SSL, but SSL was required` nei log dell'app?**
`DB_SSLMODE` è stato impostato a `require` (o più restrittivo) mentre il
database del compose non ha TLS. Vedi «Configurazione via env».

**Voglio caricare dati di test?** L'archivio dimostrativo
(`sql_scripts/demo/demo_data.sql`) viene caricato all'inizializzazione, insieme
all'utente `demo`, se il servizio `db` riceve `FOLIARIUM_DEMO_PASSWORD`.
L'inizializzazione gira solo su un volume vuoto: su un database già creato
serve prima `docker compose down -v`, che **cancella i dati**.
