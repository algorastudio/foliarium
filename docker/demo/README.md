# Demo di Foliarium in Docker

Una demo ospitata su un server: il cliente apre un indirizzo nel browser,
inserisce le credenziali che ha ricevuto e usa **l'applicazione desktop vera**,
con un archivio dimostrativo già caricato. Non installa nulla.

Ogni cliente riceve una **postazione**: una copia del programma con il suo
database, il suo schermo e le sue credenziali. Le postazioni non si vedono fra
loro. Un solo proxy, comune a tutte, gestisce HTTPS e l'accesso.

> Questa cartella non riguarda l'interfaccia web (FastAPI + React), che ha
> il suo stack in [`docker/README.md`](../README.md).

## Requisiti del server

- Linux con Docker Engine e il plugin Compose (`docker compose`). Provato
  con Docker 29 e Compose 5.
- Una copia di questo repository.
- **Disco:** circa 3 GB per le due immagini (2,3 GB il programma, 0,6 GB il
  database), più i dati delle postazioni.
- **Memoria:** vedi [Risorse](#risorse).
- Per l'accesso dall'esterno, una delle due:
  - un nome DNS che punti al server e le porte 80 e 443 libere;
  - un web server già presente che termini HTTPS (vedi
    [Dietro un web server esistente](#dietro-un-web-server-esistente)).

## Prima installazione

```bash
cd docker/demo
cp demo.env.example demo.env      # poi aprirlo e indicare il dominio
./demo.sh costruisci              # qualche minuto, la prima volta
```

`demo.env` contiene la configurazione del server e non va in git. Con
`DEMO_DOMINIO` valorizzato il proxy ottiene e rinnova da solo i certificati.

## Le postazioni

| Comando | Effetto |
|---|---|
| `./demo.sh crea <nome>` | crea una postazione e ne stampa indirizzo e credenziali |
| `./demo.sh elenco` | postazioni esistenti e loro stato |
| `./demo.sh ripristina <nome>` | la riporta allo stato iniziale; le credenziali non cambiano |
| `./demo.sh rimuovi <nome>` | la elimina con tutti i suoi dati (chiede conferma) |
| `./demo.sh costruisci` | ricostruisce le immagini dai sorgenti presenti sul server |

Il nome diventa parte dell'indirizzo: lettere minuscole, cifre e trattini,
da 2 a 31 caratteri, con una lettera all'inizio.

```text
$ ./demo.sh crea archivio-savona

Postazione «archivio-savona» creata.

  Indirizzo : https://demo.example.it/archivio-savona/
  Utente    : demo
  Password  : 9sH5WAug0UcmBfw0Kb1G

Le stesse credenziali valgono nel login di Foliarium.
File esportati: https://demo.example.it/archivio-savona/file/
```

La creazione richiede meno di un minuto. La password è generata a caso e
viene stampata solo qui; per rileggerla:

```bash
grep DEMO_PASSWORD postazioni/archivio-savona.env
```

Stati mostrati da `elenco`: **attiva**, **in avvio**, **non pronta** (il
programma non è partito o mostra un errore di database), **assente**.

Dopo un riavvio del server le postazioni tornano da sole, con i loro dati.

### Ripristino

`ripristina` cancella database, impostazioni del programma e file esportati
della postazione, e la fa ripartire dall'archivio dimostrativo iniziale. Va
usato fra un cliente e l'altro, o quando un cliente ha fatto danni: l'utente
`demo` è amministratore e può cancellare qualunque cosa.

Per farlo ogni notte, una riga di cron (qui commentata):

```cron
# 0 4 * * * /percorso/foliarium/docker/demo/demo.sh ripristina archivio-savona >> /var/log/foliarium-demo.log 2>&1
```

## Che cosa comunicare al cliente

- **Indirizzo, utente e password** stampati da `crea`.
- Al primo accesso il programma chiede di accettare il contratto di licenza,
  come dopo un'installazione vera.
- Il programma si usa come sul proprio PC. Il pulsante **Schermo intero**, in
  alto a destra, dà il risultato migliore.
- **Schermo consigliato: Full HD.** Su schermi più piccoli il programma viene
  rimpicciolito per restare tutto visibile.
- I file esportati (PDF, CSV, JSON, backup) si salvano nella cartella
  **Documenti** proposta dal programma e si scaricano da **File esportati**.
- Per provare l'importazione c'è un file pronto in
  `Documenti/Esempi import/comuni.csv`.
- Se esce dal programma (Logout), rientra con le stesse credenziali.

## Dietro un web server esistente

Se le porte 80 e 443 sono già occupate da un web server, in `demo.env` si
lascia vuoto `DEMO_DOMINIO`. Il proxy della demo ascolta allora solo su
`127.0.0.1`, alla porta `DEMO_PORTA_LOCALE`, e il web server esistente gli
inoltra il traffico dopo aver terminato HTTPS. `DEMO_INDIRIZZO_PUBBLICO`
serve solo a far stampare a `crea` l'indirizzo giusto.

Lo schermo viaggia su una connessione WebSocket: **il web server deve
inoltrare le intestazioni di upgrade**, altrimenti la pagina si apre ma resta
su «Collegamento in corso».

Esempio per nginx. Non è stato provato in questo progetto: la demo è stata
verificata collegandosi direttamente al proxy.

```nginx
map $http_upgrade $connection_upgrade {
    default upgrade;
    ''      close;
}

server {
    listen 443 ssl;
    server_name demo.example.it;
    # ssl_certificate e ssl_certificate_key: quelli già gestiti dal server

    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection $connection_upgrade;
        proxy_read_timeout 1h;   # lo schermo resta collegato a lungo
        proxy_buffering off;
    }
}
```

## Aggiornare la demo

```bash
git pull
./demo.sh costruisci
./demo.sh ripristina <nome>     # per ogni postazione
```

Le postazioni passano alla nuova versione quando vengono ripristinate.

Per togliere tutto: `rimuovi` per ogni postazione, poi
`./demo.sh _proxy_giu`, che ferma il proxy ed elimina i suoi certificati.

## Risorse

Misure prese durante lo sviluppo, su una macchina sola: vanno intese come
ordine di grandezza.

| | Programma | Database |
|---|---|---|
| A riposo | 245 MB | 50 MB |
| In uso (pagine aperte, manuale, anteprima PDF) | 300–420 MB | 50–85 MB |
| Limite predefinito | 1024 MB | 512 MB |

Il proxy occupa circa 15 MB. Conviene contare **mezzo GB per postazione in
uso**. I limiti sono un argine contro un processo impazzito, non un tetto
stretto: un programma chiuso dal sistema a metà dimostrazione costa più della
memoria. Si cambiano in `demo.env` (`DEMO_MEM_APP`, `DEMO_MEM_DB`).

## Sicurezza

- Dall'esterno risponde solo il proxy. Database e schermo delle postazioni
  non pubblicano porte.
- Ogni postazione ha una rete propria: da una non si raggiunge l'altra.
- `postazioni/*.env` contiene le **password in chiaro** (permessi 600). Il
  proxy riceve solo gli hash, in una cartella separata (`proxy/`).
- Le password sono generate, lunghe 20 caratteri: non vanno sostituite con
  password scelte a mano, perché l'accesso non limita i tentativi.
- L'immagine è fatta per collegarsi al database della sua postazione, sulla
  stessa macchina, **senza TLS**. Non va puntata a un database remoto.
- Il portachiavi del programma (chiave dei backup cifrati, password SMTP) è
  un file non cifrato dentro la postazione. Va bene per dati dimostrativi.
- L'immagine non contiene gli strumenti che firmano le licenze.

## Limiti noti

- **Scorciatoie da tastiera.** Quelle riservate al browser (Ctrl+W, Ctrl+T,
  Ctrl+N e simili) non arrivano al programma. F1 arriva; le altre non sono
  state provate una per una.
- **Appunti.** Copia e incolla fra il PC del cliente e il programma non
  funziona.
- **Caratteri.** Quelli di Windows sono sostituiti da caratteri liberi. Il
  testo è simile, non identico: Segoe UI non ha un equivalente libero con le
  stesse metriche.
- **File.** Il cliente non può caricare file dal proprio PC. Dal programma
  si aprono in anteprima solo i PDF; gli altri file si scaricano.
- **Collegamenti esterni** del manuale non si aprono: nel container non c'è
  un browser.
- **Stampa.** Non c'è una stampante: si esporta in PDF e si scarica.
- **API REST e integrazione MCP** non sono raggiungibili dall'esterno.
- **Due persone sulla stessa postazione** vedono e comandano lo stesso
  schermo.
- **«Dati delle statistiche non aggiornati»** ricompare dopo 24 ore: è il
  comportamento normale del programma, basta premere «Aggiorna Ora».
- **Non verificati:** Safari (la demo è costruita per non dipendere dal suo
  comportamento, ma non è stata provata lì); HTTPS con un dominio reale (ne
  è stata validata solo la configurazione); invio di posta e import da
  ISTAT, che richiedono l'uscita del server verso internet.

## Diagnosi

```bash
./demo.sh elenco
docker logs foliarium-demo-<nome>-app-1      # registro del programma
docker logs foliarium-demo-proxy             # registro del proxy

# Che cosa c'è sullo schermo della postazione, senza aprire un browser:
docker exec foliarium-demo-<nome>-app-1 python /opt/foliarium-demo/cattura_schermo.py /tmp/schermo.png
docker cp foliarium-demo-<nome>-app-1:/tmp/schermo.png .
```

`./prova.sh` crea due postazioni di prova, esegue tredici verifiche (accesso,
dati separati, riavvio del programma, download dei file, ripristino,
rimozione, e un browser vero se è installato Playwright) e toglie tutto. Usa
nomi e cartelle propri: **non tocca le postazioni esistenti**. È la stessa
prova che la CI esegue a ogni pull request.

## Come è fatta

```
                 internet
                    │ 443
              ┌─────▼──────┐
              │   proxy    │  Caddy: certificati, credenziali, instradamento
              └──┬──────┬──┘
        ┌────────▼─┐  ┌─▼────────┐
        │   app    │  │   app    │  Foliarium + schermo virtuale (Xvnc)
        └────┬─────┘  └────┬─────┘
        ┌────▼─────┐  ┌────▼─────┐
        │    db    │  │    db    │  PostgreSQL + archivio dimostrativo
        └──────────┘  └──────────┘
```

| File | A che cosa serve |
|---|---|
| `demo.sh` | gestione delle postazioni |
| `prova.sh`, `prova_browser.cjs` | prova completa |
| `Dockerfile`, `Dockerfile.dockerignore` | immagine del programma |
| `avvio.sh`, `controllo-salute.sh` | avvio e controllo di salute del container |
| `compose.postazione.yml` | una postazione (programma + database) |
| `compose.proxy*.yml`, `Caddyfile` | il proxy, nelle due modalità di esposizione |
| `web/` | la pagina che mostra lo schermo |
| `file_server.py` | la pagina «File esportati» |
| `visualizza_pdf.py` | anteprima dei PDF aperti dal programma |
| `fonts-foliarium.conf` | caratteri sostitutivi |
| `esempi-import/` | file d'esempio per l'importazione |
| `../postgres/` | immagine del database, condivisa con lo stack web |

Progetto e scelte: `docs/internal/2026-11-10-demo-docker-design.md`.
