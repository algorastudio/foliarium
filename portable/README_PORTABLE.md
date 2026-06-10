# Foliarium — Versione Portatile

Questa cartella contiene gli script per eseguire Foliarium con PostgreSQL portatile, **senza installare nulla** nel sistema (a parte Python).

## Requisiti

- **Windows 10/11**
- **Python 3.8+** ([download](https://www.python.org/downloads/)) — assicurati di spuntare "Add Python to PATH"

## Preparazione (una sola volta)

### 1. Scarica PostgreSQL portatile

1. Vai su [EnterpriseDB - Download PostgreSQL Binaries](https://www.enterprisedb.com/download-postgresql-binaries)
2. Scarica la versione **Windows x86-64** (ZIP)
3. Estrai l'archivio: al suo interno troverai una cartella `pgsql`
4. Copia l'intera cartella `pgsql` dentro `portable/`, in modo da avere:

```
foliarium/
└── portable/
    ├── pgsql/              ← cartella PostgreSQL (da scaricare)
    │   ├── bin/
    │   ├── lib/
    │   └── share/
    ├── setup_primo_avvio.bat
    ├── avvia_foliarium.bat
    ├── arresta_foliarium.bat
    └── README_PORTABLE.md
```

### 2. Primo avvio

Doppio clic su **`setup_primo_avvio.bat`**

Lo script eseguirà automaticamente:
- Inizializzazione del cluster PostgreSQL (cartella `pgdata`)
- Creazione del database `catasto_storico`
- Installazione delle dipendenze Python
- Creazione dello schema e delle tabelle
- (Opzionale) Caricamento dei dati dimostrativi

## Uso quotidiano

| Azione | Script |
|--------|--------|
| Avviare Foliarium | `avvia_foliarium.bat` |
| Arrestare PostgreSQL | `arresta_foliarium.bat` |

**`avvia_foliarium.bat`** avvia PostgreSQL, lancia Foliarium, e alla chiusura dell'app chiede se arrestare anche il database.

## Note tecniche

- PostgreSQL gira sulla porta **5433** (non 5432) per non confliggere con eventuali installazioni esistenti
- I dati del database sono in `portable/pgdata/`
- I log di PostgreSQL sono in `portable/pg_log.txt`
- L'autenticazione è impostata su `trust` (nessuna password) — adatto solo per uso locale
- Il file `config.ini` viene creato automaticamente al primo avvio

## Backup dei dati

Per fare un backup completo del database:

```
portable\pgsql\bin\pg_dump.exe -U postgres -p 5433 catasto_storico > backup.sql
```

Per ripristinare:

```
portable\pgsql\bin\psql.exe -U postgres -p 5433 -d catasto_storico -f backup.sql
```

## Spostare su un altro PC

1. Copia l'intera cartella `foliarium/`
2. Sul nuovo PC serve solo Python installato
3. Esegui `avvia_foliarium.bat` — il database è già configurato nella cartella `pgdata`
