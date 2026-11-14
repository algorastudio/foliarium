# Demo in Docker — piano di implementazione

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** una demo di Foliarium ospitata su un server, in cui ogni cliente
usa dal browser l'applicazione desktop vera, in una postazione sua.

**Architecture:** ogni postazione è un progetto Compose con due container:
`app` (GUI PyQt6 su schermo virtuale Xvnc, esposta via WebSocket) e `db`
(PostgreSQL con l'archivio dimostrativo). Un unico proxy Caddy termina
HTTPS, chiede le credenziali e instrada per percorso (`/<nome>/`). Uno
script Bash crea, ripristina e rimuove le postazioni.

**Tech Stack:** Docker + Compose, Debian bookworm, TigerVNC (Xvnc), openbox,
noVNC 1.3 (solo `core/rfb.js`), websockify, Caddy 2, PostgreSQL 16, Bash,
Python 3.12 (stdlib per i servizi di contorno), pytest, Playwright.

**Spec:** `docs/internal/2026-11-10-demo-docker-design.md`

## Global Constraints

- **Codice del prodotto:** l'unica modifica ammessa è in `db/backup.py`
  (Task 2). Se un altro file del prodotto sembra da toccare, ci si ferma e
  si chiede al committente.
- **Utente applicativo:** `demo`, ruolo `admin`, attivo.
- **Una sola coppia di credenziali:** utente `demo` e la stessa password
  sia all'ingresso (proxy) sia nel login di Foliarium.
- **Password generate:** 20 caratteri da `[A-Za-z0-9]`, mai scelte, mai nel
  repository. `docker/demo/postazioni/` e `docker/demo/demo.env` stanno in
  `.gitignore`.
- **Porte pubblicate:** solo quelle del proxy. `db` e `app` non pubblicano
  nulla sull'host.
- **Vietati nell'immagine:** browser web, caratteri Microsoft.
- **PostgreSQL:** stessa versione maggiore per server e client, da una sola
  variabile `PG_MAJOR` (demo: `16`, come il bundle Windows; il default di
  `docker/postgres/Dockerfile` resta `14` per lo stack web).
- **Lingua:** italiano per testi mostrati, commenti, nomi di script e
  messaggi di commit.
- **PyQt6:** enum sempre con percorso completo (`Qt.AlignmentFlag.AlignLeft`).
- **Date mostrate:** `dd/MM/yyyy` e `dd/MM/yyyy HH:mm`.
- **Commit:** uno per task, con le righe di attribuzione della sessione.

## Nomi condivisi fra i task

| Cosa | Valore |
|---|---|
| Immagini | `foliarium-demo-db:locale`, `foliarium-demo-app:locale` |
| Utente del container app | `foliarium`, uid 1000, home `/home/foliarium` |
| Codice del prodotto nell'immagine | `/opt/foliarium` |
| Strumenti della demo nell'immagine | `/opt/foliarium-demo/` |
| Porte interne di `app` | 5900 VNC (solo loopback), 6080 pagina + WebSocket, 6081 file |
| Cartella pubblicata per il download | `/home/foliarium/Documenti` |
| Cartella esportazioni | `/home/foliarium/Documenti/Esportazioni Foliarium` |
| Esempi per l'import | `/home/foliarium/Documenti/Esempi import` |
| Progetto Compose di una postazione | `foliarium-demo-<nome>` |
| Alias di rete di `app` | `app-<nome>` |
| Container del proxy | `foliarium-demo-proxy` |
| Titolo della finestra principale | `Foliarium — Archivio Catastale Storico` (`gui_main.py:174`) |

Variabili d'ambiente:

| Dove | Variabili |
|---|---|
| `db` | `POSTGRES_DB=catasto_storico`, `POSTGRES_USER=postgres`, `POSTGRES_PASSWORD`, `FOLIARIUM_ADMIN_PASSWORD` (facoltativa), `FOLIARIUM_DEMO_PASSWORD` (facoltativa) |
| `app` | `FOLIARIUM_DEMO=1`, `DEMO_DB_HOST=db`, `DEMO_DB_PORT=5432`, `DEMO_DB_NAME`, `DEMO_DB_USER`, `DEMO_DB_PASS` (già lette da `config.py:35-39`), `DEMO_SCHERMO` (default `1440x900`), `DEMO_SALTA_EULA` (default vuota) |
| `postazioni/<nome>.env` | `DEMO_NOME`, `DEMO_PASSWORD`, `DEMO_DB_PASS`, `DEMO_WS_TOKEN` |
| `demo.env` | `DEMO_DOMINIO` (vuoto = dietro un web server esistente), `DEMO_PORTA_LOCALE` (default `8080`), `PG_MAJOR` (default `16`), `DEMO_MEM_APP`, `DEMO_MEM_DB` |
| ambiente di `demo.sh` | `DEMO_CARTELLA_DATI` (dove stanno `demo.env` e `postazioni/`; default: la cartella dello script), `DEMO_BUILD_OPZIONI` (opzioni aggiunte a `docker build`) |

Indirizzi di una postazione: `/<nome>/` (pagina), `/<nome>/sessione.json`,
`/<nome>/ws/<token>` (WebSocket), `/<nome>/file/` (download).

## Review Focus

Condizioni che lo spec implica e che nessun criterio di accettazione
esercita. Ognuna ha il suo test nel task indicato.

1. **Il database non è pronto quando parte `app`.** In demo l'applicazione
   mostra un errore modale e resta lì: nessuno può premere OK. Atteso: la
   GUI parte solo a database pronto. → Task 4.
2. **Nome di postazione ostile** (`../x`, spazi, maiuscole, vuoto). Finisce
   in percorsi, nomi di progetto e configurazione del proxy. Atteso:
   rifiuto prima di toccare Docker o il disco. → Task 6.
3. **Percorso ostile sulla pagina dei file** (`..`, `%2e%2e`, link
   simbolici verso l'esterno). Atteso: 404, mai un file fuori dalla
   cartella. → Task 3.
4. **Il cliente chiude il programma o rifiuta l'EULA.** Atteso: il
   programma riparte, mai una scrivania vuota. → Task 4.
5. **Il proxy viene ricreato o il server riavviato.** I collegamenti di
   rete aggiunti a mano si perdono. Atteso: le postazioni restano
   raggiungibili. → Task 7.

## Verifica in un ambiente con proxy in uscita

Nelle sessioni cloud di Claude Code Docker funziona, ma le build non
raggiungono la rete da sole (dettagli in `/root/.ccr/README.md`). Il piano
lo prevede senza sporcare i file versionati:

- entrambi i Dockerfile accettano `ARG BASE_IMAGE`;
- `demo.sh costruisci` aggiunge alle build il contenuto di
  `DEMO_BUILD_OPZIONI` (es. `--network host --build-arg BASE_IMAGE=...
  --build-arg HTTPS_PROXY=...`);
- l'immagine di base locale con la CA del proxy e le sorgenti apt in HTTPS
  si costruisce fuori dal repository, nella cartella temporanea.

Il daemon si avvia con `dockerd &`. Chromium e Playwright sono già
installati.

---

### Task 1: Inizializzazione del database — elenco canonico, utente demo, dataset

**Files:**
- Modify: `docker/postgres/Dockerfile`
- Modify: `docker/postgres/init.sh` (riscrittura)
- Create: `sql_scripts/demo/demo_user.sql`
- Modify: `docker-compose.yml` (una riga d'ambiente nel servizio `db`)
- Modify: `docker/README.md` (sezioni login e dati di test)
- Test: `tests/unit/test_docker_db_init.py`

**Interfaces:**
- Consumes: `setup_database.SQL_SCRIPTS`, `setup_database.BOOTSTRAP_ADMIN_SCRIPT`.
- Produces: immagine `foliarium-demo-db:locale`; contratto d'ambiente di
  `db` (tabella sopra); l'array Bash `SCRIPTS=( ... )` in `init.sh`, un
  percorso per riga fra virgolette.

- [ ] **Step 1: Scrivere i test che falliscono**

```python
pytestmark = pytest.mark.unit
INIT = Path("docker/postgres/init.sh")

def _script_in_init() -> list[str]:
    corpo = re.search(r"SCRIPTS=\((.*?)\)", INIT.read_text(encoding="utf-8"), re.S).group(1)
    return re.findall(r'"([^"]+\.sql)"', corpo)

def test_elenco_coincide_con_setup_database():
    assert _script_in_init() == sdb.SQL_SCRIPTS

def test_ogni_script_esiste():
    for rel in _script_in_init() + [sdb.BOOTSTRAP_ADMIN_SCRIPT,
                                    "demo/demo_user.sql", "demo/demo_data.sql"]:
        assert (Path("sql_scripts") / rel).is_file(), rel

def test_bootstrap_admin_riceve_la_password():
    testo = INIT.read_text(encoding="utf-8")
    assert sdb.BOOTSTRAP_ADMIN_SCRIPT in testo
    assert "admin_password=" in testo

def test_utente_demo_riceve_la_password():
    testo = INIT.read_text(encoding="utf-8")
    assert "demo/demo_user.sql" in testo and "demo_password=" in testo
```

- [ ] **Step 2: Eseguirli e vederli fallire**

Run: `pytest tests/unit/test_docker_db_init.py -v --no-cov`
Expected: FAIL (`init.sh` elenca i nomi vecchi; `demo_user.sql` non esiste).

- [ ] **Step 3: `sql_scripts/demo/demo_user.sql`**

Sul modello di `sql_scripts/admin/04_bootstrap_admin.sql`. Differenze
decise: variabile psql `demo_password`; se manca, lo script **fallisce**
con `RAISE EXCEPTION` (non `\quit`, che esce con codice 0 ed è il motivo
per cui oggi l'utente admin non viene creato). Valori: `username='demo'`,
`nome_completo='Utente Demo'`, `email='demo@archivio.local'`,
`ruolo='admin'`, `attivo=TRUE`, hash con `crypt(..., gen_salt('bf', 12))`.
Idempotente con `WHERE NOT EXISTS`.

- [ ] **Step 4: `docker/postgres/Dockerfile`**

`ARG PG_MAJOR=14`, `ARG BASE_IMAGE=postgres:${PG_MAJOR}-bookworm`,
`FROM ${BASE_IMAGE}`. Il resto invariato.

- [ ] **Step 5: `docker/postgres/init.sh`**

- `SCRIPTS=( ... )` con i 12 percorsi di `setup_database.SQL_SCRIPTS`,
  nello stesso ordine. Uno script mancante è un **errore**, non un avviso.
- Se `FOLIARIUM_ADMIN_PASSWORD` non è vuota: bootstrap admin con
  `-v admin_password=...`.
- Se `FOLIARIUM_DEMO_PASSWORD` non è vuota: `demo/demo_user.sql` con
  `-v demo_password=...`, poi `demo/demo_data.sql`.
- Le password non compaiono mai nell'output.
- Ultima riga: `[foliarium-init] Setup completato.`

- [ ] **Step 6: Stack web — rendere vero ciò che il README promette**

In `docker-compose.yml`, servizio `db`:
`FOLIARIUM_ADMIN_PASSWORD: ${ADMIN_PASSWORD:-admin123}`.
In `docker/README.md`: il login predefinito cita `ADMIN_PASSWORD`; la
sezione «Voglio caricare dati di test» indica `FOLIARIUM_DEMO_PASSWORD` al
posto del file inesistente; un rimando a `docker/demo/README.md`.

- [ ] **Step 7: Test unitari verdi**

Run: `pytest tests/unit/test_docker_db_init.py -v --no-cov`
Expected: 4 passed.

- [ ] **Step 8: Verifica su un container vero (spec §8.1.2)**

```bash
docker build -f docker/postgres/Dockerfile --build-arg PG_MAJOR=16 \
  -t foliarium-demo-db:locale ${DEMO_BUILD_OPZIONI:-} .
docker run -d --name prova-db -e POSTGRES_DB=catasto_storico \
  -e POSTGRES_PASSWORD=x -e FOLIARIUM_DEMO_PASSWORD=Prova123 foliarium-demo-db:locale
# attendere «Setup completato» in `docker logs prova-db`, poi:
docker exec prova-db psql -U postgres -d catasto_storico -Atc \
  "SELECT ruolo, attivo FROM catasto.utente WHERE username='demo'"
docker exec prova-db psql -U postgres -d catasto_storico -Atc \
  "SELECT (SELECT count(*) FROM catasto.comune), (SELECT count(*) FROM catasto.partita)"
docker exec prova-db psql -U postgres -d catasto_storico -Atc \
  "SELECT count(*) FROM catasto.utente WHERE username='admin'"
```
Expected: `admin|t`; due conteggi maggiori di zero; `0` (nessun admin
senza `FOLIARIUM_ADMIN_PASSWORD`). `Prova123` non compare nei log.
Se il dataset richiede l'utente `admin`, crearlo con password casuale non
comunicata e annotarlo nel README (spec §9). Poi `docker rm -f prova-db`.

- [ ] **Step 9: Commit**

Messaggio: `L'inizializzazione Docker del database segue l'elenco canonico`.

---

### Task 2: Gli strumenti di backup si trovano anche fuori da Windows

**Files:**
- Modify: `db/backup.py` (righe 80, 139, 160, 283-285)
- Test: `tests/unit/test_backup_executables.py`

**Interfaces:**
- Produces: `db.backup._pg_tool_name(base: str, *, windows: Optional[bool] = None) -> str`

- [ ] **Step 1: Scrivere i test che falliscono**

```python
pytestmark = pytest.mark.unit

def test_su_windows_aggiunge_exe():
    assert _pg_tool_name("pg_dump", windows=True) == "pg_dump.exe"

def test_fuori_da_windows_nome_nudo():
    assert _pg_tool_name("pg_dump", windows=False) == "pg_dump"

def test_default_segue_la_piattaforma():
    atteso = "psql.exe" if os.name == "nt" else "psql"
    assert _pg_tool_name("psql") == atteso

@pytest.mark.skipif(os.name == "nt", reason="verifica il caso non Windows")
def test_resolve_trova_eseguibile_senza_suffisso(tmp_path, monkeypatch):
    finto = tmp_path / "pg_dump"; finto.write_text("#!/bin/sh\n"); finto.chmod(0o755)
    monkeypatch.setenv("PATH", str(tmp_path))
    mixin = DBBackupMixin.__new__(DBBackupMixin); mixin.logger = logging.getLogger("t")
    assert mixin._resolve_executable_path(None, _pg_tool_name("pg_dump")) == str(finto)

def test_nessun_exe_letterale_fuori_dalla_helper():
    sorgente = Path("db/backup.py").read_text(encoding="utf-8")
    corpo = sorgente.split("def _pg_tool_name", 1)[1].split("\ndef ", 1)[-1]
    assert '.exe"' not in corpo and ".exe'" not in corpo
```

- [ ] **Step 2: Eseguirli e vederli fallire**

Run: `pytest tests/unit/test_backup_executables.py -v --no-cov`
Expected: FAIL con `ImportError: cannot import name '_pg_tool_name'`.

- [ ] **Step 3: Implementare `_pg_tool_name` e usarla nei sei punti**

Funzione a livello di modulo, definita prima della classe. `windows=None`
significa `os.name == "nt"`. Il parametro esplicito esiste per i test:
modificare `os.name` a runtime rompe `pathlib`.

- [ ] **Step 4: Test verdi, e nessuna regressione**

Run: `pytest tests/unit/test_backup_executables.py tests/unit/test_db_mixins.py -v --no-cov`
Expected: tutti passati.

- [ ] **Step 5: Commit**

Messaggio: `Il backup trova gli strumenti PostgreSQL anche su Linux`.

---

### Task 3: Pagina di download delle esportazioni

**Files:**
- Create: `docker/demo/file_server.py` (solo libreria standard)
- Test: `tests/unit/test_demo_file_server.py` (carica il modulo per percorso
  con `importlib.util.spec_from_file_location`)

**Interfaces:**
- Produces:
  - `risolvi(radice: Path, percorso_url: str) -> Optional[Path]`
  - `pagina_elenco(radice: Path, cartella: Path) -> str`
  - `crea_server(radice: Path, porta: int, indirizzo: str = "0.0.0.0") -> ThreadingHTTPServer`
  - `main()`: legge `DEMO_FILE_RADICE` (default `~/Documenti`) e
    `DEMO_FILE_PORTA` (default `6081`).

Comportamento deciso:
- Solo `GET` e `HEAD`. Ogni altro metodo: 405.
- `risolvi` restituisce `None` (→ 404) se il percorso, **dopo**
  decodifica e risoluzione dei link simbolici, non sta dentro `radice`; se
  non esiste; se un suo componente comincia con `.`.
- Cartelle: pagina HTML in italiano, voci dalla più recente, con nome,
  dimensione leggibile e data `dd/MM/yyyy HH:mm`. Cartella vuota: testo
  `Nessun file esportato.`
- **Collegamenti relativi** (`href="nome%20file.pdf"`): la pagina è servita
  sotto `/<nome>/file/` e il proxy toglie il prefisso.
- File: `Content-Disposition: attachment; filename*=UTF-8''<nome>` e
  `X-Content-Type-Options: nosniff`.

- [ ] **Step 1: Scrivere i test che falliscono**

```python
@pytest.mark.parametrize("ostile", [
    "/../segreto.txt", "/%2e%2e/segreto.txt", "/a/../../segreto.txt",
    "//etc/passwd", "/..%2fsegreto.txt", "/.nascosto", "/a/.nascosto/x",
])
def test_percorsi_ostili_respinti(radice, ostile):
    assert fs.risolvi(radice, ostile) is None

def test_link_simbolico_verso_esterno_respinto(radice, tmp_path):
    (radice / "fuga").symlink_to(tmp_path / "segreto.txt")
    assert fs.risolvi(radice, "/fuga") is None

def test_nome_con_spazi_e_accenti(radice):
    (radice / "partita n° 12 città.pdf").write_bytes(b"%PDF")
    assert fs.risolvi(radice, "/partita%20n%C2%B0%2012%20citt%C3%A0.pdf").name == "partita n° 12 città.pdf"

def test_elenco_vuoto(radice):
    assert "Nessun file esportato." in fs.pagina_elenco(radice, radice)

def test_elenco_dal_piu_recente(radice):
    # due file con mtime diversi impostati con os.utime
    assert pagina.index("nuovo.pdf") < pagina.index("vecchio.pdf")

def test_elenco_usa_collegamenti_relativi(radice):
    assert 'href="/' not in fs.pagina_elenco(radice, radice)

def test_http_scarica_come_allegato(server):      # server su porta 0
    assert risposta.status == 200
    assert risposta.headers["Content-Disposition"].startswith("attachment")
    assert risposta.headers["X-Content-Type-Options"] == "nosniff"

def test_http_post_rifiutato(server):
    assert risposta.status == 405
```
La fixture `radice` crea `tmp_path/"esportazioni"` e, accanto,
`tmp_path/"segreto.txt"`.

- [ ] **Step 2: Eseguirli e vederli fallire**

Run: `pytest tests/unit/test_demo_file_server.py -v --no-cov`
Expected: FAIL (file inesistente).

- [ ] **Step 3: Implementare `docker/demo/file_server.py`**

- [ ] **Step 4: Test verdi**

Run: `pytest tests/unit/test_demo_file_server.py -v --no-cov`
Expected: tutti passati.

- [ ] **Step 5: Commit**

Messaggio: `Pagina di download per le esportazioni della demo`.

---

### Task 4: Immagine app — la GUI parte sullo schermo virtuale

**Files:**
- Create: `docker/demo/Dockerfile`
- Create: `docker/demo/Dockerfile.dockerignore`
- Create: `docker/demo/avvio.sh`, `docker/demo/controllo-salute.sh`
- Create: `docker/demo/openbox-rc.xml`
- Create: `docker/demo/cattura_schermo.py`
- Create: `docker/demo/web/index.html` (segnaposto: la pagina vera è del Task 6)

**Interfaces:**
- Consumes: immagine db (Task 1); `file_server.py` (Task 3).
- Produces: immagine `foliarium-demo-app:locale`; porte 6080 e 6081;
  `/opt/foliarium-demo/cattura_schermo.py <file.png>` (esce con 1 se lo
  schermo è di un solo colore); `/opt/foliarium-demo/controllo-salute.sh`.

Decisioni:

- **Dockerfile.** `ARG BASE_IMAGE=python:3.12-slim-bookworm`,
  `ARG PG_MAJOR=16`. Pacchetti: le librerie Qt già elencate nel
  `Dockerfile` in radice, più `tigervnc-standalone-server`, `openbox`,
  `novnc`, `websockify`, `x11-utils`, `xdg-utils`, `locales`, `tzdata`,
  `curl`, e `postgresql-client-${PG_MAJOR}` dal repository PGDG (stesso
  metodo di `.devcontainer/setup.sh`). `pip install -r requirements.txt`
  senza modifiche. `LANG=it_IT.UTF-8`, `TZ=Europe/Rome`,
  `QT_QPA_PLATFORM=xcb`, `DISPLAY=:1`, `FOLIARIUM_DEMO=1`. `USER foliarium`.
- **Contenuto copiato:** `gui_main.py` e tutti i moduli Python in radice,
  `foliarium/`, `db/`, `core/`, `api/`, `utils/`, `styles/`, `resources/`,
  `sql_scripts/`, `docs/`. Gli strumenti di `docker/demo/` vanno in
  `/opt/foliarium-demo/`, compresa la cartella `web/`, dentro la quale si
  crea il collegamento simbolico `novnc` → `/usr/share/novnc`.
- **`Dockerfile.dockerignore`** (ha precedenza su quello in radice):
  esclude `.git`, `tests`, `frontend`, `docs/internal`, i PDF e le
  presentazioni in `docs/`, `esportazioni`, `dist`, `build`, `config.ini`,
  `*.license`, `docker/demo/postazioni`, `docker/demo/demo.env`. **Non**
  esclude `docs/**/*.md` né `resources/`.
- **`avvio.sh`**, nell'ordine:
  1. prepara la home. L'applicazione propone di salvare in
     `<Documenti>/Esportazioni Foliarium` (`app_utils.py:81-91`), mentre
     `app_paths.ESPORTAZIONI_DIR` è `~/.foliarium/esportazioni`: perché
     tutto finisca nella cartella pubblicata, scrive
     `~/.config/user-dirs.dirs` con `XDG_DOCUMENTS_DIR="$HOME/Documenti"`,
     crea `Documenti/Esportazioni Foliarium` e fa di
     `~/.foliarium/esportazioni` un collegamento simbolico a quella.
     Con `DEMO_SALTA_EULA=1` registra l'EULA
     come accettata scrivendo `QSettings` con le costanti di `config.py`
     (`SETTINGS_EULA_ACCEPTED`, `EULA_VERSION`), organizzazione
     `AlgoraStudio`, applicazione `Foliarium`;
  2. `Xvnc :1 -geometry "${DEMO_SCHERMO:-1440x900}" -depth 24
     -SecurityTypes None -localhost -AlwaysShared -AcceptSetDesktopSize
     -rfbport 5900`, e attende lo schermo;
  3. openbox, `websockify --web /opt/foliarium-demo/web 6080
     127.0.0.1:5900`, `file_server.py`;
  4. **attende il database** con `pg_isready` su TCP verso
     `DEMO_DB_HOST:DEMO_DB_PORT` (l'immagine postgres ascolta su TCP solo a
     inizializzazione finita);
  5. ciclo: `python /opt/foliarium/gui_main.py`, pausa di 2 secondi,
     daccapo. Directory di lavoro: la home (quella del codice è in sola
     lettura);
  6. se Xvnc, openbox, websockify o il file server terminano, il container
     esce con errore e Docker lo riavvia.
- **`openbox-rc.xml`:** la finestra con titolo
  `Foliarium*Archivio Catastale Storico` nasce massimizzata; nessun menu
  sulla scrivania (clic destro e centrale sul fondo non fanno nulla); un
  solo desktop.
- **`controllo-salute.sh`:** esce 0 solo se esiste `/tmp/.X11-unix/X1`, la
  porta 6080 risponde e c'è un processo `gui_main.py`.

- [ ] **Step 1: Scrivere Dockerfile, dockerignore, i quattro script e la pagina segnaposto**

- [ ] **Step 2: Costruire**

Run: `docker build -f docker/demo/Dockerfile -t foliarium-demo-app:locale ${DEMO_BUILD_OPZIONI:-} .`
Expected: build riuscita. Poi:
`docker run --rm foliarium-demo-app:locale sh -c 'pg_dump --version; test -f /usr/share/novnc/core/rfb.js && echo novnc-ok; test -d /opt/foliarium/docs/internal || echo interni-esclusi'`
Expected: `pg_dump (PostgreSQL) 16.x`, `novnc-ok`, `interni-esclusi`.

- [ ] **Step 3: La GUI parte (spec §8.1.1)**

```bash
docker network create prova-rete
docker run -d --name db --network prova-rete -e POSTGRES_DB=catasto_storico \
  -e POSTGRES_PASSWORD=x -e FOLIARIUM_DEMO_PASSWORD=Prova123 foliarium-demo-db:locale
docker run -d --name prova-app --network prova-rete --init \
  -e DEMO_DB_HOST=db -e DEMO_DB_PORT=5432 -e DEMO_DB_NAME=catasto_storico \
  -e DEMO_DB_USER=postgres -e DEMO_DB_PASS=x -e DEMO_SALTA_EULA=1 \
  foliarium-demo-app:locale
# entro 120 s:
docker exec prova-app xwininfo -root -tree | grep -F 'Foliarium — Archivio Catastale Storico'
docker exec prova-app /opt/foliarium-demo/controllo-salute.sh && echo sano
docker exec prova-app python /opt/foliarium-demo/cattura_schermo.py /tmp/s.png
docker cp prova-app:/tmp/s.png "$SCRATCH/schermo-task4.png"
docker exec -w /opt/foliarium -e QT_QPA_PLATFORM=offscreen prova-app python -c \
  "from PyQt6.QtWidgets import QApplication; a=QApplication([]); from app_utils import _get_default_export_path as p; print(p('x.pdf'))"
```
Expected: la riga della finestra; `sano`; un PNG;
`/home/foliarium/Documenti/Esportazioni Foliarium/x.pdf`. **Aprire il PNG e
guardarlo:** finestra principale massimizzata, badge DEMO, dati visibili,
nessun errore modale. Se compare un errore di permessi su file nella
cartella del codice, la causa va cercata nella directory di lavoro.

- [ ] **Step 4: Review Focus 4 — il programma riparte**

Run: `docker exec prova-app pkill -f gui_main.py; sleep 25; docker exec prova-app xwininfo -root -tree | grep -c 'Archivio Catastale Storico'`
Expected: `1`.

- [ ] **Step 5: Senza `DEMO_SALTA_EULA` compare l'EULA**

Ricreare `prova-app` senza la variabile, catturare lo schermo e
guardarlo. Expected: schermata dell'EULA, non la finestra principale.

- [ ] **Step 6: Review Focus 1 — database in ritardo**

```bash
docker rm -f prova-app db
# stessi comandi `docker run` dello Step 3, ma in ordine inverso:
docker run -d --name prova-app ...   # prima l'app, senza database
sleep 20
docker exec prova-app sh -c 'pgrep -f gui_main.py || echo in-attesa'
docker run -d --name db ...          # poi il database
```
Expected: `in-attesa` (la GUI **non** è partita senza database); entro
120 s dall'avvio di `db` la finestra principale esiste.

- [ ] **Step 7: Misura della memoria (spec §8.1.5)**

Run: `docker stats --no-stream --format '{{.Name}} {{.MemUsage}}' prova-app db`
Annotare i due valori a riposo: servono al Task 6 per i limiti e al Task 9
per la guida. Poi rimuovere container e rete di prova.

- [ ] **Step 8: Commit**

Messaggio: `Immagine della demo: la GUI su uno schermo virtuale`.

---

### Task 5: Aspetto e file — caratteri, PDF, esempi per l'import

**Files:**
- Modify: `docker/demo/Dockerfile`
- Create: `docker/demo/fonts-foliarium.conf`
- Create: `docker/demo/visualizza_pdf.py`, `docker/demo/foliarium-pdf.desktop`
- Create: `docker/demo/esempi-import/comuni.csv`, `LEGGIMI.txt`
- Modify: `docker/demo/avvio.sh` (copia degli esempi in `Documenti/Esempi import`, se assenti)
- Test: `tests/unit/test_demo_esempi_import.py`

**Interfaces:**
- Produces: `python /opt/foliarium-demo/visualizza_pdf.py <file.pdf>`;
  associazione `application/pdf` → `foliarium-pdf.desktop`.

Decisioni:

- **Caratteri.** Pacchetti `fonts-liberation2`, `fonts-crosextra-carlito`,
  `fonts-open-sans`, `fonts-noto-core`, `fonts-noto-color-emoji`. Alias in
  `/etc/fonts/conf.d/60-foliarium.conf`:

  | Richiesto dai temi | Servito da |
  |---|---|
  | Segoe UI, Trebuchet MS | Open Sans |
  | Calibri | Carlito |
  | Arial | Liberation Sans |
  | Times New Roman | Liberation Serif |
  | Georgia, Palatino Linotype, Book Antiqua | Noto Serif |

- **PDF.** Niente pacchetto esterno: `qpdfview` porta 123 pacchetti.
  `visualizza_pdf.py` usa `QPdfView` di PyQt6 (`PyQt6.QtPdfWidgets`),
  modalità a più pagine, adattamento alla larghezza, titolo
  `<nome file> — Anteprima PDF`, pulsanti Chiudi, Zoom +, Zoom −. Se
  l'import di `PyQt6.QtPdfWidgets` fallisce nell'immagine, ripiego:
  pacchetto `xpdf` e associazione al suo `.desktop`.
- **Esempi.** `comuni.csv` nel formato di `docs/admin/import-massivo.md`
  (separatore `;`, intestazione
  `nome;provincia;regione;codice_catastale;data_istituzione;data_soppressione;note`),
  otto comuni liguri **assenti dal dataset demo**, così l'import produce
  inserimenti e non soli duplicati. `LEGGIMI.txt` spiega in tre righe a
  che cosa serve la cartella. Altri formati solo se l'applicazione offre
  un import corrispondente con formato documentato.

- [ ] **Step 1: Test degli esempi, che fallisce**

```python
def test_comuni_csv_ha_intestazione_documentata():
    righe = Path("docker/demo/esempi-import/comuni.csv").read_text(encoding="utf-8").splitlines()
    assert righe[0] == "nome;provincia;regione;codice_catastale;data_istituzione;data_soppressione;note"
    assert len(righe) == 9
    assert all(len(r.split(";")) == 7 for r in righe)

def test_comuni_csv_non_duplica_il_dataset_demo():
    demo = Path("sql_scripts/demo/demo_data.sql").read_text(encoding="utf-8")
    for riga in righe[1:]:
        assert f"'{riga.split(';')[0]}'" not in demo
```

- [ ] **Step 2: Vederlo fallire, creare i file, vederlo passare**

Run: `pytest tests/unit/test_demo_esempi_import.py -v --no-cov`

- [ ] **Step 3: Caratteri, visualizzatore e associazione nell'immagine; ricostruire**

- [ ] **Step 4: Verifiche nell'immagine**

```bash
docker run --rm foliarium-demo-app:locale sh -c '
  for f in "Segoe UI" Calibri Arial "Times New Roman" Georgia; do fc-match "$f" family; done
  xdg-mime query default application/pdf
  python -c "from PyQt6.QtPdfWidgets import QPdfView; print(\"qtpdf-ok\")"'
```
Expected: `Open Sans`, `Carlito`, `Liberation Sans`, `Liberation Serif`,
`Noto Serif`; `foliarium-pdf.desktop`; `qtpdf-ok`.

- [ ] **Step 5: Un PDF si apre davvero**

Con la postazione di prova del Task 4 avviata: generare un PDF con `fpdf2`
nella cartella esportazioni, poi
`docker exec prova-app xdg-open <file>` e, dopo 5 s,
`xwininfo -root -tree | grep -F 'Anteprima PDF'`.
Expected: la finestra esiste. Catturare lo schermo e guardarlo: testo
leggibile, caratteri non di ripiego, emoji non sostituite da riquadri.

- [ ] **Step 6: Gli esempi sono nella home**

Run: `docker exec prova-app ls '/home/foliarium/Documenti/Esempi import'`
Expected: `LEGGIMI.txt comuni.csv`.

- [ ] **Step 7: Commit**

Messaggio: `Demo: caratteri sostitutivi, anteprima PDF, esempi per l'import`.

---

### Task 6: Postazione, proxy e pagina dello schermo — `costruisci`, `crea`, `elenco`

**Files:**
- Create: `docker/demo/compose.postazione.yml`
- Create: `docker/demo/compose.proxy.yml`,
  `compose.proxy.pubblico.yml`, `compose.proxy.locale.yml`
- Create: `docker/demo/Caddyfile`
- Modify: `docker/demo/web/index.html`
- Create: `docker/demo/web/schermo.js`
- Create: `docker/demo/demo.sh`, `docker/demo/demo.env.example`
- Create: `docker/demo/prova_browser.cjs`
- Modify: `.gitignore` (`docker/demo/postazioni/`, `docker/demo/demo.env`,
  `docker/demo/prova-esito/`)
- Test: `tests/unit/test_demo_script.py`

**Interfaces:**
- Consumes: le due immagini; le porte 6080 e 6081.
- Produces: `demo.sh costruisci | crea <nome> | elenco`; codici d'uscita
  `0` riuscito, `2` uso o nome non valido, `3` postazione già esistente o
  inesistente, `1` altro; funzione interna `_proxy_su` (avvia il proxy e
  lo collega alla rete di **ogni** postazione esistente);
  `document.documentElement.dataset.stato` sulla pagina:
  `connessione` | `connesso` | `disconnesso`.

Decisioni:

- **Nome di postazione:** `^[a-z][a-z0-9-]{1,30}$`. Validato come prima
  cosa, prima di qualunque comando Docker o scrittura su disco.
- **`compose.postazione.yml`:** nessuna sezione `build` (le immagini le
  produce `costruisci`) e nessuna `ports`. `db`: volume `dati_db`,
  controllo di salute con `pg_isready -h 127.0.0.1`. `app`:
  `depends_on` db sano, volume `casa:/home/foliarium`, `init: true`,
  `cap_drop: [ALL]`, `security_opt: [no-new-privileges:true]`,
  `pids_limit: 512`, alias di rete `app-${DEMO_NOME}`, controllo di salute
  con `controllo-salute.sh`. Entrambi `restart: unless-stopped`. Limiti di
  memoria da `DEMO_MEM_APP` e `DEMO_MEM_DB`, con default pari al doppio
  del valore a riposo misurato nel Task 4, arrotondato ai 256 MB superiori.
- **Proxy.** Immagine `caddy:2-alpine`. `Caddyfile`: un solo sito
  `{$DEMO_SITO}` che importa `/etc/caddy/postazioni/*.caddy` e risponde 404
  a tutto il resto. Con `DEMO_DOMINIO` valorizzato: `DEMO_SITO` è il
  dominio e si usa `compose.proxy.pubblico.yml` (porte 80 e 443, volume per
  i certificati). Altrimenti `DEMO_SITO=http://:8080` e
  `compose.proxy.locale.yml` pubblica `127.0.0.1:${DEMO_PORTA_LOCALE}:8080`.
- **Frammento del proxy per una postazione** (`postazioni/<nome>.caddy`,
  generato da `crea`):
  - `/<nome>/ws/<token>` → **senza** richiesta di credenziali, riscritto
    in `/websockify` verso `app-<nome>:6080`;
  - `/<nome>` → redirezione a `/<nome>/`;
  - `/<nome>/sessione.json` → credenziali, `Cache-Control: no-store`,
    corpo `{"ws":"ws/<token>"}`;
  - `/<nome>/file/*` → credenziali, prefisso tolto, verso `app-<nome>:6081`;
  - `/<nome>/*` → credenziali, prefisso tolto, verso `app-<nome>:6080`.

  Il WebSocket non passa dalle credenziali Basic perché Safari
  storicamente non le invia in quella connessione, e Safari non è
  verificabile né qui né in CI. Lo protegge il token: 32 byte casuali in
  esadecimale, consegnati solo a chi si è autenticato. È il ripiego dello
  spec §8.1.3, adottato da subito.
- **`crea <nome>`:** genera password, password del database e token;
  scrive `postazioni/<nome>.env` (permessi 600) e `postazioni/<nome>.caddy`
  (hash da `caddy hash-password`); avvia la postazione; chiama `_proxy_su`;
  ricarica il proxy; stampa indirizzo, utente `demo` e password.
- **Pagina.** `schermo.js` importa `./novnc/core/rfb.js` (collegamento
  simbolico a `/usr/share/novnc`), legge `sessione.json`, apre il
  WebSocket con `resizeSession = true`. Il riquadro dello schermo ha
  dimensione minima 1024×600 (`gui_main.py:175`): sotto, scorre la pagina.
  Barra superiore sottile: `Foliarium — Demo`, collegamento
  `File esportati` (`./file/`, nuova scheda), pulsante `Schermo intero`.
  Alla disconnessione: messaggio `Collegamento interrotto`, pulsante
  `Riconnetti`, nuovo tentativo ogni 5 secondi.

- [ ] **Step 1: Test dello script, che falliscono (Review Focus 2)**

```python
pytestmark = pytest.mark.unit
SCRIPT = "docker/demo/demo.sh"

@pytest.mark.parametrize("nome", ["", "A", "Cliente", "../x", "a b", "a/b",
                                  "1cliente", "x", "a" * 32, "nome;rm", "-n"])
def test_nome_non_valido_rifiutato_senza_effetti(nome, tmp_path):
    esito = _esegui("crea", nome, cartella=tmp_path)   # PATH con un finto `docker` che registra le chiamate
    assert esito.returncode == 2
    assert "nome non valido" in esito.stderr.lower()
    assert not (tmp_path / "docker-chiamato").exists()
    assert list((tmp_path / "postazioni").glob("*")) == []

def test_senza_argomenti_mostra_i_cinque_comandi():
    esito = _esegui()
    assert esito.returncode == 2
    for comando in ("costruisci", "crea", "ripristina", "rimuovi", "elenco"):
        assert comando in esito.stderr

def test_sintassi_bash():
    assert subprocess.run(["bash", "-n", SCRIPT]).returncode == 0
```
`_esegui` lancia `bash docker/demo/demo.sh` con `DEMO_CARTELLA_DATI=tmp_path`
e, in testa al `PATH`, un finto `docker` che crea `tmp_path/docker-chiamato`.

- [ ] **Step 2: Vederli fallire**

Run: `pytest tests/unit/test_demo_script.py -v --no-cov`

- [ ] **Step 3: Compose, Caddyfile, `demo.env.example`, `.gitignore`, `demo.sh` con i tre comandi**

- [ ] **Step 4: Test unitari verdi**

Run: `pytest tests/unit/test_demo_script.py -v --no-cov`

- [ ] **Step 5: Pagina dello schermo**

- [ ] **Step 6: Due postazioni vere, modalità locale**

```bash
printf 'DEMO_DOMINIO=\nDEMO_PORTA_LOCALE=18080\nPG_MAJOR=16\n' > docker/demo/demo.env
bash docker/demo/demo.sh costruisci
bash docker/demo/demo.sh crea prova-a && bash docker/demo/demo.sh crea prova-b
B=http://127.0.0.1:18080
PW_A=$(grep ^DEMO_PASSWORD= docker/demo/postazioni/prova-a.env | cut -d= -f2)
curl -s -o /dev/null -w '%{http_code}\n' $B/prova-a/                      # 401
curl -s -o /dev/null -w '%{http_code}\n' -u demo:$PW_A $B/prova-a/        # 200
curl -s -o /dev/null -w '%{http_code}\n' -u demo:$PW_A $B/prova-b/        # 401
curl -s -u demo:$PW_A $B/prova-a/sessione.json                            # {"ws":"ws/<token>"}
curl -s -o /dev/null -w '%{http_code}\n' $B/prova-a/ws/sbagliato          # 404
docker ps --format '{{.Names}} {{.Ports}}' | grep -v proxy | grep -c -- '->'   # 0
```
Expected: i valori nei commenti. `bash docker/demo/demo.sh elenco` mostra
le due postazioni come attive.

La modalità con dominio non si può provare senza un nome DNS pubblico:
se ne valida almeno la configurazione.

Run: `docker run --rm -e DEMO_SITO=demo.example.it -v "$PWD/docker/demo/Caddyfile:/etc/caddy/Caddyfile:ro" -v "$PWD/docker/demo/postazioni:/etc/caddy/postazioni:ro" caddy:2-alpine caddy validate --config /etc/caddy/Caddyfile`
Expected: `Valid configuration`.

- [ ] **Step 7: Prova nel browser (spec §8.1.3, §8.1.4; accettazione 1)**

`prova_browser.cjs` (Playwright, `require('playwright')`), argomenti:
indirizzo base, nome, password, cartella degli esiti. Verifica:
1. senza credenziali la pagina risponde 401;
2. con `httpCredentials`, entro 60 s `dataset.stato === "connesso"`;
3. il canvas non è di un solo colore;
4. portando la finestra a 1280×800 e poi a 1600×900, entro 10 s la
   larghezza del canvas segue (±2 px);
5. a 800×500 il canvas resta largo almeno 1024;
6. salva `schermo-<nome>.png`.

Run: `node docker/demo/prova_browser.cjs http://127.0.0.1:18080 prova-a "$PW_A" "$SCRATCH"`
Expected: `6/6 verifiche superate`. **Aprire il PNG e guardarlo.**

- [ ] **Step 8: Commit**

Messaggio: `Demo: postazioni dietro un proxy, con lo schermo nel browser`.

---

### Task 7: `ripristina`, `rimuovi` e la prova completa

**Files:**
- Modify: `docker/demo/demo.sh`
- Create: `docker/demo/prova.sh`
- Modify: `tests/unit/test_demo_script.py`

**Interfaces:**
- Consumes: tutto il Task 6.
- Produces: `demo.sh ripristina <nome> | rimuovi <nome>`;
  `bash docker/demo/prova.sh` → esce 0 solo se ogni verifica passa, scrive
  esiti e immagini in `docker/demo/prova-esito/` (in `.gitignore`).

Decisioni:

- **`ripristina`:** ferma la postazione, elimina i volumi `dati_db` e
  `casa`, la riavvia con lo **stesso** file `.env`. Credenziali e token
  invariati.
- **`rimuovi`:** come sopra, più eliminazione di `.env` e `.caddy` e
  ricarica del proxy. Chiede conferma digitando il nome, salvo `--si`.
- Su una postazione inesistente entrambi escono con 3 e non toccano nulla.
  `crea` su un nome esistente esce con 3.
- **`prova.sh`:** usa la porta locale 18080 e i nomi `prova-a`, `prova-b`;
  salta `costruisci` se `DEMO_PROVA_SENZA_BUILD=1`; pulisce sempre in
  uscita (`trap`); imposta `DEMO_SALTA_EULA=1`; esegue la prova nel
  browser se `node` e `playwright` sono disponibili, e la **pretende** con
  `DEMO_PROVA_BROWSER=1`.

- [ ] **Step 1: Test che falliscono**

```python
@pytest.mark.parametrize("comando", ["ripristina", "rimuovi"])
def test_postazione_inesistente(comando, tmp_path):
    esito = _esegui(comando, "mai-creata", "--si", cartella=tmp_path)
    assert esito.returncode == 3
    assert not (tmp_path / "docker-chiamato").exists()

def test_crea_due_volte_stesso_nome(tmp_path):
    (tmp_path / "postazioni").mkdir(); (tmp_path / "postazioni" / "doppia.env").write_text("x")
    assert _esegui("crea", "doppia", cartella=tmp_path).returncode == 3
```

- [ ] **Step 2: Vederli fallire, implementare i due comandi, vederli passare**

Run: `pytest tests/unit/test_demo_script.py -v --no-cov`

- [ ] **Step 3: Scrivere `prova.sh`**

Verifiche, ognuna con una riga `OK`/`FALLITO` e un riepilogo finale:

| # | Verifica | Criterio |
|---|---|---|
| 1 | 401 senza credenziali, 200 con, 401 con quelle dell'altra | acc. 1 |
| 2 | utente `demo` attivo e `admin`; `comune` e `partita` non vuote | acc. 2 |
| 3 | `bcrypt.checkpw(password, hash)` vero, eseguito nel container app | spec §7.2.6 |
| 4 | finestra principale presente; dopo `pkill` torna entro 30 s | acc. 3 |
| 5 | un comune inserito in A non esiste in B | acc. 4 |
| 6 | un file in `Documenti/Esportazioni Foliarium` si scarica da `/file/`; percorso con `..%2f` → 404 | acc. 6 |
| 7 | dopo `ripristina prova-a`: comune e file spariti, credenziali valide | acc. 5 |
| 8 | nessuna porta pubblicata fuori dal proxy | acc. 7 |
| 9 | proxy ricreato con `--force-recreate` tramite `_proxy_su`: A e B rispondono 200 | Review Focus 5 |
| 10 | prova nel browser su A | acc. 1 |
| 11 | dal container `app` di A, `curl` verso `app-prova-b:6080` fallisce | spec §7.6 |
| 12 | dopo `rimuovi`: nessun container, volume o file della postazione | — |

- [ ] **Step 4: Eseguirla**

Run: `DEMO_PROVA_BROWSER=1 bash docker/demo/prova.sh`
Expected: `12/12 verifiche superate`, uscita 0. Poi
`docker ps -a | grep -c foliarium-demo` → `0`.

- [ ] **Step 5: Commit**

Messaggio: `Demo: ripristino e rimozione delle postazioni, con prova completa`.

---

### Task 8: La CI prova la demo a ogni pull request

**Files:**
- Create: `.github/workflows/demo_docker.yml`

**Interfaces:**
- Consumes: `docker/demo/prova.sh`.

Decisioni:

- Nome: `Demo Docker`. Trigger: `pull_request` verso `main`/`master`,
  `push` su `main`, `workflow_dispatch`. Nessun filtro per percorso: una
  modifica alla GUI può impedire l'avvio quanto una al Dockerfile.
- Un job `prova-demo`, `ubuntu-latest`, `timeout-minutes: 30`,
  `permissions: contents: read`.
- Passi: checkout; `shellcheck docker/demo/*.sh docker/postgres/init.sh`;
  Node 22; Playwright `1.63.0` installato in `$RUNNER_TEMP` e reso
  visibile con `NODE_PATH`, poi `playwright install --with-deps chromium`;
  `DEMO_PROVA_BROWSER=1 bash docker/demo/prova.sh`; in caso di fallimento,
  log dei container; **sempre** caricamento di `docker/demo/prova-esito/`
  come artefatto `Demo-Docker-Esito`.
- I test unitari dei Task 1, 2, 3, 5, 6 e 7 stanno in `tests/unit/` e li
  esegue già la pipeline esistente: qui non si ripetono.

- [ ] **Step 1: Scrivere il workflow**

- [ ] **Step 2: `shellcheck` in locale, se disponibile; altrimenti lo verifica la CI**

- [ ] **Step 3: Commit e push; leggere l'esito del job**

Expected: job verde; l'artefatto contiene `schermo-prova-a.png`.
**Scaricare e guardare l'immagine**: è il controllo dell'aspetto su una
macchina diversa da quella di sviluppo (spec, accettazione 8).

- [ ] **Step 4: La pipeline esistente resta verde (accettazione 9)**

---

### Task 9: Giro delle funzioni, guida operativa, documentazione

**Files:**
- Create: `docker/demo/README.md`
- Modify: `CLAUDE.md` (sezione «Demo in Docker», albero del progetto,
  elenco dei test)
- Modify: `docs/internal/2026-11-10-demo-docker-design.md` (esiti dei
  punti `[?]`)

- [ ] **Step 1: Verifiche dello spec §8.2, su una postazione avviata**

| Funzione | Come si verifica | Atteso |
|---|---|---|
| Backup | dal container `app`, chiamare la funzione di `db/backup.py` che il pulsante invoca, verso il `db` della postazione | file non vuoto; nessun errore di versione |
| Ripristino | stessa via, dal file appena creato | conteggi invariati |
| Portachiavi | `python -c "from app_utils import get_password_from_keyring as g; print(g('x','y'))"` | `None`, nessuna eccezione |
| Report PDF | generare un report dalla GUI e premere Apri | finestra `Anteprima PDF` |
| Import | importare `Documenti/Esempi import/comuni.csv` dalla GUI | otto comuni inseriti |
| Manuale (F1) | aprire il manuale e cercare `TIER1` | nessun risultato da `internal/` |

Le tre righe che passano dalla GUI si eseguono a mano nel browser, con
un'immagine dello schermo per ciascuna. Ogni funzione che non va si
classifica: correggibile in `docker/demo/` (si corregge), limite da
dichiarare (va nella guida), oppure richiede una modifica al prodotto
(**ci si ferma e si chiede**).

- [ ] **Step 2: `docker/demo/README.md`**

Sezioni, in quest'ordine: Requisiti del server · Prima installazione
(`demo.env`, `costruisci`) · Le postazioni (i cinque comandi, con
l'output atteso) · Che cosa comunicare al cliente (indirizzo, utente,
password, pagina dei file, cartella degli esempi) · Dietro un web server
esistente (esempio nginx **con le intestazioni di upgrade del WebSocket**)
· Aggiornare la demo · Ripristino periodico (riga di cron, commentata) ·
Risorse (valori misurati nel Task 4, quante postazioni per GB) · Limiti
noti · Diagnosi (dove sono i log, `prova.sh`).

Limiti noti da elencare: scorciatoie riservate al browser (Ctrl+W, Ctrl+T,
Ctrl+N); caratteri non identici a Windows; collegamenti esterni del
manuale che non si aprono; nessun caricamento di file dal PC del cliente;
API REST non raggiungibile dall'esterno; due persone sulla stessa
postazione condividono lo schermo; Safari non verificato; quanto emerso
allo Step 1.

- [ ] **Step 3: `CLAUDE.md`**

Sezione sul modello di «Installer Windows»: componenti, perché il desktop
e non il web, contratto d'ambiente di `init.sh`, perché il WebSocket usa
un token e non le credenziali Basic, perché l'elenco degli script è
duplicato e quale test lo sorveglia, come si esegue `prova.sh`.

- [ ] **Step 4: Aggiornare lo spec**

Ogni `[?]` dei §8.1 e §8.2 diventa `[V]` con l'esito, oppure resta `[?]`
con il motivo (Safari). I conteggi e le misure si riportano come rilevati.

- [ ] **Step 5: Suite completa**

Run: `pytest -m "unit" --no-cov -q`
Expected: nessun test fallito che prima passava.

- [ ] **Step 6: Commit e aggiornamento della pull request**

Messaggio: `Demo in Docker: guida operativa e limiti noti`. Titolo e
descrizione della pull request aggiornati: non contiene più il solo
documento di progetto.
