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

# Restart solo dell'app (dopo modifiche al codice Python)
docker compose restart app

# Rebuild completo dell'immagine app (dopo modifiche a requirements / frontend)
docker compose up -d --build app

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
```

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

- **`foliarium-app`** (basata su `python:3.12-slim-bookworm`):
  - Stage 1: `node:22-alpine` builda il frontend React (`vite build`).
  - Stage 2: copia `frontend/dist/`, codice Python, `requirements.txt`.
  - Avvia `uvicorn api.main:create_app --factory --host 0.0.0.0 --port 8765`.
  - Healthcheck su `GET /` ogni 30s.

- **`foliarium-db`** (basata su `postgres:14-bookworm`):
  - Aggiunge il locale `it_IT.UTF-8`.
  - Copia `sql_scripts/` in `/opt/foliarium-sql/` e `init.sh` in
    `/docker-entrypoint-initdb.d/00-init.sh`.
  - Al primo avvio applica gli stessi script dell'installer, nello stesso
    ordine (`SQL_SCRIPTS` in `setup_database.py`); un test impedisce ai due
    elenchi di divergere.
  - Crea l'utente applicativo `admin` solo se riceve
    `FOLIARIUM_ADMIN_PASSWORD` (il compose la valorizza da `ADMIN_PASSWORD`).

## Troubleshooting

**Login fallito al primo accesso?** Aspetta che gli script SQL di init siano
completati (la prima volta possono richiedere ~30–60s). Verifica con:
```bash
docker compose logs db | grep foliarium-init
```
Devi vedere `[foliarium-init] Setup completato.` e l'utente `admin` creato.

**L'app risponde 503?** Il pool DB non si è ancora connesso. L'app fa retry
per 60s; se fallisce verifica i log: `docker compose logs app | grep "Pool DB"`.

**Voglio caricare dati di test?** L'archivio dimostrativo
(`sql_scripts/demo/demo_data.sql`) viene caricato all'inizializzazione, insieme
all'utente `demo`, se il servizio `db` riceve `FOLIARIUM_DEMO_PASSWORD`.
L'inizializzazione gira solo su un volume vuoto: su un database già creato
serve prima `docker compose down -v`, che **cancella i dati**.
