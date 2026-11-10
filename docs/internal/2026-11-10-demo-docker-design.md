# Demo di Foliarium in Docker — documento di progetto

Data: 10/11/2026 · Stato: **in attesa di approvazione**

Questo documento descrive che cosa va costruito e perché. Non è un piano di
lavoro: il piano si scrive dopo l'approvazione.

Legenda delle decisioni:

- **[C]** deciso dal committente, nelle sue parole
- **[P]** proposta di chi scrive, non ancora contestata: va controllata
- **[V]** fatto verificato leggendo il codice, con il riferimento al file
- **[?]** non verificato: nessun container è stato avviato per scrivere
  questo documento (il daemon Docker non era attivo nella sessione)

---

## 1. Scopo

Una demo di Foliarium ospitata su un server del committente, che i clienti
provano dal browser senza installare nulla.

- **[C]** «gira su un mio server, la provano i clienti da browser»
- **[C]** il cliente «deve vedere il programma vero, con tutte le funzioni»
- **[C]** il cliente arriva «tramite un utente e delle credenziali
  prestabilite»

Il prodotto in vendita è l'applicazione desktop PyQt6. L'interfaccia web
(FastAPI + React) ha un aspetto diverso e non copre gestione utenti, backup,
import di massa, documenti e report PDF **[V]** (`api/routes/` non ha rotte
per queste funzioni). Per questo la demo mostra il desktop, non il web.

## 2. Obiettivi

1. Con le credenziali ricevute, il cliente apre un indirizzo HTTPS e si
   trova davanti a Foliarium desktop: già entrato, con il badge DEMO e un
   archivio dimostrativo caricato.
2. Tutte le funzioni dell'applicazione sono utilizzabili, comprese quelle
   di amministrazione. Quelle che passano da file (esportazioni, report
   PDF, import, backup) hanno un percorso praticabile dal browser.
3. Ogni **postazione** — una copia del programma con il suo database, il
   suo schermo e le sue credenziali — è indipendente dalle altre.
   Aggiungerne una è un comando.
4. Una postazione torna allo stato iniziale con un comando.
5. Verso internet è esposto solo HTTPS.
6. Una guida operativa permette al committente di installare, creare
   postazioni, ripristinarle e rimuoverle senza leggere il codice.
7. La CI verifica a ogni pull request che l'immagine si costruisce e che
   una postazione parte davvero.

## 3. Fuori dal perimetro

- **Stack web esistente** (`Dockerfile` e `docker-compose.yml` in radice).
  Resta com'è, tranne l'inizializzazione del database che condivide con la
  demo. È rotto e va trattato a parte: vedi §10.
- **Sessioni create a richiesta** per visitatori anonimi. Le credenziali le
  distribuisce il committente, che sa quanti clienti ha.
- **Caricamento di file dal PC del cliente.** Per provare l'import ci sono
  file d'esempio già presenti nella postazione.
- **Uso da telefono.** Un desktop remoto su schermo piccolo non è una demo
  credibile.
- **Dataset personalizzato per cliente.** Tutte le postazioni partono dallo
  stesso archivio dimostrativo.
- **API REST e integrazione MCP raggiungibili dall'esterno.** Nel container
  l'API ascolta solo in locale: il cliente può creare una chiave API dal
  programma, ma non usarla dal proprio PC.
- **Alta disponibilità e monitoraggio.**
- **Demo Windows** (`build_demo.bat`): vedi §10.

## 4. Che cosa renderebbe il risultato un fallimento

Anche se tecnicamente funzionasse:

- un cliente vede lo schermo o i dati di un altro cliente;
- la demo sembra rotta: scrivania vuota dopo aver chiuso la finestra,
  caratteri di ripiego che sfigurano l'interfaccia, pulsanti «Apri PDF»
  che non fanno nulla;
- il programma viene modificato in modo che la demo si comporti
  diversamente dal prodotto, o che il codice di produzione acquisisca
  scorciatoie pensate per la demo;
- PostgreSQL o VNC risultano raggiungibili da internet;
- credenziali di una postazione finiscono nel repository.

## 5. Stato attuale

### 5.1 Ciò che c'è già e si riusa

- **La GUI gira su Linux in un container.** Il devcontainer la avvia con
  `QT_QPA_PLATFORM=xcb` dietro noVNC **[V]** (`.devcontainer/`). Nel codice
  dell'interfaccia non risultano dipendenze da Windows, salvo un flag in
  `foliarium/core/services/update_checker.py:187` **[V]**.
- **La modalità demo esiste.** Con `FOLIARIUM_DEMO=1` (`config.py:30`):
  - se non trova il PostgreSQL portabile, si collega al database indicato
    da `DEMO_DB_HOST/PORT/NAME/USER/PASS` (`config.py:35-39`,
    `gui_main.py:2389-2397`) **[V]**;
  - entra da sola come utente `demo`, se esiste ed è attivo; altrimenti
    apre il login normale (`gui_main.py:2422-2452`) **[V]**. L'ingresso
    automatico non verifica la password;
  - la licenza è sempre valida, senza file
    (`foliarium/core/services/license.py:353`) **[V]**;
  - mostra il badge DEMO (`foliarium/ui/top_bar.py:54`) e non controlla
    gli aggiornamenti (`update_checker.py:216`) **[V]**.
- **Il dataset dimostrativo esiste.** `sql_scripts/demo/demo_data.sql`:
  provincia di Savona, 1870–1985, circa 10 comuni, 120 possessori, 300
  partite, 600 immobili (cifre dichiarate nell'intestazione del file, non
  ricontate) **[V]**.
- **L'ordine canonico di inizializzazione** è l'elenco `SQL_SCRIPTS` in
  `setup_database.py:82-93`, più `admin/04_bootstrap_admin.sql` **[V]**.

### 5.2 Ciò che manca o non funziona

- **Nessuno script crea l'utente `demo`** **[V]**.
- **`docker/postgres/init.sh` è fermo alla struttura vecchia**: elenca i
  file in radice di `sql_scripts/`, due dei quali non esistono più
  (`19_creazione_tabella_sessioni.sql`, `20_feature_tipi_localita.sql`),
  mentre dalla v1.7.0 gli script stanno in sottocartelle **[V]**
  (`sql_scripts/README.md`).
- **Lo stesso script non crea alcun utente applicativo**: lancia il
  bootstrap senza `-v admin_password`, e in quel caso lo script esce prima
  dell'`INSERT` **[V]** (`sql_scripts/07a_bootstrap_admin.sql:24-29`).
- **Il dataset demo non viene caricato** dallo stack Docker **[V]**.
- **Il backup dalla GUI cerca `pg_dump.exe`** con `shutil.which`, anche su
  Linux, dove quel nome non esiste **[V]** (`db/backup.py:80,204`).
- **I caratteri richiesti dai temi non esistono su Linux**: Segoe UI,
  Calibri, Arial, Times New Roman, Georgia, Palatino Linotype **[V]**
  (`styles/*.qss`).
- **I file aperti con `QDesktopServices.openUrl`** (PDF generati,
  esportazioni, documenti allegati) hanno bisogno di un programma associato
  nel container **[V]** (9 punti, fra cui
  `foliarium/ui/widgets/reporting/reportistica.py:294`).
- **Non ci sono file d'esempio per l'import** nel repository **[V]**.
- **`.dockerignore` in radice esclude `docs/`, `*.md` e `*.pdf`** **[V]**.
  Il manuale interno (F1) legge `docs/`: l'immagine della demo ha bisogno
  di regole proprie.

## 6. Approcci considerati

### 6.1 Che cosa mostrare

| | Pro | Contro |
|---|---|---|
| Interfaccia web | nativa nel browser, leggera, più utenti insieme | aspetto diverso dal prodotto, funzioni mancanti |
| **Desktop nel browser** | il prodotto vero, tutte le funzioni | più pesante da ospitare, uno schermo per sessione |

**[C]** Scelto il desktop.

### 6.2 Come gestire più clienti

| | Clienti insieme | Dati | Lavoro |
|---|---|---|---|
| A. Una postazione | uno per volta | condivisi | minimo |
| **B. Più postazioni fisse** | uno per postazione | separati | poco più di A |
| C. Gateway con sessioni a richiesta | quanti ne regge il server | separati | molto di più |

**[C]** Scelta B, costruita partendo da A: si realizza una postazione sola
ma parametrizzata, e averne tre significa avviarla tre volte. C è stata
scartata perché risolve il problema di visitatori anonimi e numerosi, che
qui non esiste.

### 6.3 Come portare lo schermo nel browser **[P]**

- **noVNC su uno schermo X virtuale** — scelto. È lo stesso principio del
  devcontainer, quindi l'unico già visto funzionare con questa applicazione.
- Xpra (client HTML5): mostra le sole finestre dell'applicazione e sa
  trasferire file, ma è una tecnologia in più mai provata con Foliarium.
- Plugin VNC integrato in Qt: nessun server X, ma niente gestore di
  finestre, quindi dialoghi e finestre secondarie mal gestiti.

## 7. Progetto

### 7.1 Componenti

```
                 internet
                    │ 443 (HTTPS)
              ┌─────▼──────┐
              │   proxy    │  certificati, credenziali, instradamento
              └──┬──────┬──┘
     rete slot-1 │      │ rete slot-2
        ┌────────▼─┐  ┌─▼────────┐
        │   app    │  │   app    │  GUI + schermo virtuale + noVNC
        └────┬─────┘  └────┬─────┘
        ┌────▼─────┐  ┌────▼─────┐
        │    db    │  │    db    │  PostgreSQL, archivio dimostrativo
        └──────────┘  └──────────┘
```

- **Immagine app.** Python 3.12, librerie Qt, server X virtuale con VNC,
  gestore di finestre minimale, noVNC, client PostgreSQL, visualizzatore
  PDF, caratteri sostitutivi. Esegue `gui_main.py` dai sorgenti con
  `FOLIARIUM_DEMO=1`, come utente non privilegiato.
- **Immagine db.** Quella di `docker/postgres/`, con l'inizializzazione
  corretta (§7.4).
- **Proxy.** Uno solo per tutte le postazioni. **[P]** Caddy, perché
  ottiene e rinnova i certificati da solo e la configurazione di una
  postazione sta in poche righe.

### 7.2 Che cosa vede il cliente

1. Apre `https://<dominio>/<postazione>/`. Il browser chiede utente e
   password con la sua finestra standard. **[P]** Una pagina di accesso
   con il logo sarebbe più curata ma è lavoro in più, rimandabile: non
   cambia il resto del progetto.
2. Compare lo schermo del programma, grande quanto la finestra del
   browser, senza parametri da digitare.
3. Al primo avvio dopo una creazione o un ripristino accetta l'EULA, come
   nel prodotto. **[P]** Il comportamento non viene alterato per la demo.
4. È dentro come utente `demo`, ruolo `admin`. **[P]** «Tutte le funzioni»
   include quelle di amministrazione; il ripristino rimedia a qualunque
   danno.
5. Se chiude il programma, questo riparte da solo. Non resta mai una
   scrivania vuota.
6. Se esce dalla sessione (logout), compare il login di Foliarium, dove
   valgono le **stesse credenziali** usate all'ingresso. **[P]** L'utente è
   `demo` in entrambi i punti, con una password diversa per postazione: al
   cliente si comunica una coppia sola.
7. Se due persone aprono insieme la stessa postazione, vedono e comandano
   lo stesso schermo. **[P]** È accettato: serve a due colleghi dello
   stesso cliente che guardano insieme. Clienti diversi ricevono
   postazioni diverse.

### 7.3 File

- **Esportazioni e report.** Su Linux l'applicazione propone
  `~/.foliarium/esportazioni` **[V]** (`app_paths.py:57-65`). Quella
  cartella è pubblicata come pagina di download su
  `https://<dominio>/<postazione>/file/`, dietro le stesse credenziali.
  **[P]**
- **PDF.** I pulsanti che aprono un PDF mostrano il documento in un
  visualizzatore dentro lo schermo remoto. **[P]**
- **Import.** Una cartella di file CSV d'esempio, coerenti con i formati
  descritti in `docs/admin/import-massivo.md`, è raggiungibile dalle
  finestre «Apri». **[P]**
- **Backup e ripristino.** Funzionano dalla GUI contro il database della
  postazione. Richiede client e server PostgreSQL della stessa versione
  maggiore, e che la ricerca degli eseguibili non pretenda il suffisso
  `.exe` fuori da Windows. Quest'ultima è **l'unica modifica prevista al
  codice del prodotto**: piccola, con test, utile a chiunque usi Foliarium
  su Linux.

### 7.4 Database

- **Un PostgreSQL per postazione**, mai pubblicato sull'host. **[P]** Con
  poche postazioni l'isolamento completo vale più della memoria
  risparmiata condividendo un server.
- L'inizializzazione segue l'elenco canonico di `setup_database.py`.
  **[P]** L'elenco resta duplicato in `init.sh`, con un test che fallisce
  se i due divergono: estrarlo in un file comune toccherebbe il percorso
  dell'installer Windows, appena stabilizzato.
- Per la demo, in più: creazione dell'utente `demo` (nuovo script accanto
  a `demo_data.sql`, sul modello del bootstrap dell'amministratore) e
  caricamento del dataset. Le due aggiunte si attivano con variabili
  d'ambiente, così la stessa immagine serve anche lo stack web.
- L'applicazione si collega come proprietario del database della sua
  postazione. **[P]** Le migrazioni automatiche all'avvio richiedono
  permessi di modifica dello schema, e il database è usa e getta.

### 7.5 Postazioni e comandi

Uno script di gestione sul server, con cinque operazioni:

| Comando | Effetto |
|---|---|
| `costruisci` | costruisce le immagini dai sorgenti presenti sul server |
| `crea <nome>` | genera le credenziali, avvia app e db, registra la postazione nel proxy, stampa indirizzo e credenziali |
| `ripristina <nome>` | cancella database, esportazioni e impostazioni del programma, riavvia: stato iniziale, stesse credenziali |
| `rimuovi <nome>` | ferma tutto, cancella dati e configurazione |
| `elenco` | postazioni esistenti e loro stato |

- **[P]** Le immagini si costruiscono sul server da una copia del
  repository, senza pubblicarle su un registro: nessun segreto in più da
  gestire. Aggiornare la demo a una nuova versione significa aggiornare la
  copia, eseguire `costruisci` e poi `ripristina` sulle postazioni.
- Database, esportazioni e impostazioni del programma sopravvivono al
  riavvio del server; li cancella solo `ripristina` o `rimuovi`.
- Le credenziali sono **generate, mai scelte**: lunghe e casuali, così un
  attacco a tentativi non è praticabile anche senza limite di frequenza.
  Nel proxy ne resta solo l'hash.
- I file di configurazione delle postazioni stanno sul server, in una
  cartella esclusa da git.
- **[P]** Il ripristino è manuale. Renderlo periodico è una riga di cron,
  documentata ma non attivata.

### 7.6 Rete e sicurezza

- Solo il proxy pubblica porte.
- **Due modalità di esposizione**, scelte da una variabile: con un dominio
  dedicato il proxy gestisce i certificati sulle porte 80/443; se il server
  ha già un web server su quelle porte, il proxy ascolta solo in locale e
  quello esistente gli inoltra il traffico.
- Una postazione non raggiunge in rete nessun'altra postazione.
- Container senza privilegi: utente non root, nessuna capability, limiti
  di memoria, CPU e processi. Nessun accesso al socket di Docker.
- Nessun browser nel container: il cliente non ha modo di navigare dal
  server. Di conseguenza i collegamenti a siti esterni presenti nel
  manuale non si aprono: limite accettato, da dichiarare nella guida.
- **[P]** L'uscita verso internet resta consentita: gli import da fonti
  esterne (ISTAT, OpenStreetMap, citati in `docs/introduzione.md`)
  presumibilmente ne hanno bisogno **[?]**.

### 7.7 Aspetto

- Caratteri liberi sostitutivi, con alias verso i nomi richiesti dai temi.
  Niente caratteri Microsoft, per ragioni di licenza. **Il testo non sarà
  identico al pixel a quello su Windows**: Segoe UI non ha un equivalente
  libero con le stesse metriche.
- Lingua e fuso orario italiani.
- La finestra principale occupa tutto lo schermo; dialoghi e finestre
  secondarie restano sopra.

### 7.8 Dove stanno i file

```
docker/
├── postgres/              esistente: Dockerfile, init.sh (da correggere)
└── demo/
    ├── Dockerfile         immagine app
    ├── Dockerfile.dockerignore
    ├── (avvio, gestore finestre, caratteri)
    ├── compose della postazione e del proxy
    ├── script di gestione
    ├── esempi-import/
    └── README.md          guida operativa
sql_scripts/demo/          + script dell'utente demo
```

La guida operativa sta in `docker/demo/README.md` e **non** nel manuale
MkDocs: è per chi ospita la demo, non per l'archivista. `CLAUDE.md` riceve
una sezione dedicata.

## 8. Verifica

### 8.1 Da accertare prima di tutto il resto

Sono le ipotesi su cui poggia il progetto e che nessuno ha ancora visto
funzionare. Se una cade, il progetto va rivisto prima di procedere.

1. **[?]** L'immagine si costruisce e la GUI parte sullo schermo virtuale.
2. **[?]** L'inizializzazione con l'elenco canonico più il dataset demo va
   a buon fine su PostgreSQL 14.
3. **[?]** La connessione WebSocket di noVNC passa attraverso
   l'autenticazione del proxy **su Safari**. Storicamente Safari non invia
   le credenziali Basic nelle connessioni WebSocket. Ripiego previsto:
   l'indirizzo del WebSocket contiene un segreto lungo, consegnato solo
   dopo l'autenticazione.
4. **[?]** Lo schermo si ridimensiona con la finestra del browser.
5. **[?]** Memoria occupata da una postazione, a riposo e in uso: decide
   quante ne regge il server e i limiti da impostare.

### 8.2 Da controllare funzione per funzione

- **[?]** Backup e ripristino dalla GUI.
- **[?]** Apertura dei PDF generati.
- **[?]** Finestre di impostazione che salvano password nel portachiavi di
  sistema: nel container non c'è un portachiavi.
- **[?]** Scorciatoie da tastiera: quelle riservate al browser (Ctrl+W,
  Ctrl+T, Ctrl+N) non arrivano al programma. Vanno elencate nella guida.

### 8.3 Criteri di accettazione

1. Senza credenziali l'indirizzo della postazione risponde 401; con le
   credenziali compare il programma.
2. Nel database della postazione esiste l'utente `demo`, attivo, con ruolo
   `admin`, e le tabelle del dataset non sono vuote.
3. Il programma entra da solo e, chiuso, riparte.
4. Un dato inserito in una postazione non compare in un'altra.
5. Dopo `ripristina`, un dato inserito in precedenza non c'è più e le
   credenziali funzionano ancora.
6. Un'esportazione fatta dal programma si scarica dalla pagina dei file.
7. Dall'esterno rispondono solo le porte del proxy.
8. La CI costruisce le immagini, avvia una postazione, verifica i punti
   1, 2, 3 e 5 e allega un'immagine dello schermo, così l'aspetto si
   controlla senza avere un server.
9. La suite di test esistente resta verde.

## 9. Lasciato a chi costruisce

- Scelta dei pacchetti: server VNC, gestore di finestre, visualizzatore
  PDF, caratteri.
- Meccanismo di riavvio del programma e controllo di salute del container.
- Come il proxy apprende una nuova postazione senza interrompere le altre.
- Meccanismo di isolamento di rete fra postazioni.
- Come far coincidere la cartella pubblicata con quella proposta dalle
  finestre «Salva con nome», se le varie funzioni non usano la stessa.
- Contenuto dei file d'esempio per l'import.
- Dipendenze Python dell'immagine: **[P]** `requirements.txt` così com'è,
  per non avere un terzo elenco da tenere allineato; si riduce solo se la
  build fallisce o l'immagine risulta ingestibile.
- Se creare anche l'utente `admin` nelle postazioni: solo se il dataset lo
  richiede, e in quel caso con password casuale non comunicata.
- Valori dei limiti di risorse, dopo la misura al punto 8.1.5.

## 10. Trovato per strada, da trattare a parte

Non fanno parte di questo lavoro, ma sono guasti reali emersi leggendo il
codice.

1. **La build dello stack web fallisce.** `Dockerfile:62-64` copia
   `custom_widgets.py`, `email_service.py`, `license_manager.py` e
   `update_checker.py`, che in radice non esistono più **[V]**. Non copia
   `utils/` e `validators.py`, che il deploy Azure include come necessari
   (`.github/workflows/main_foliarium.yml`). Installa tutto
   `requirements.txt` e le librerie Qt, mentre all'API basta
   `requirements-web.txt`.
2. **`docker/README.md` descrive cose non vere**: il login
   `admin / admin123` e il caricamento di
   `sql_scripts/04_dati-esempio_modificato.sql`, file che non esiste
   **[V]**. La correzione di `init.sh` prevista qui risolve la prima metà.
3. **`build_demo.bat` non può funzionare**: esce se non trova `main.py` e
   poi invoca `foliarium_demo.spec`; nessuno dei due è nel repository
   **[V]**.
4. **`sql_scripts/README.md` cita `prepare_demo_db.py`**, che non esiste
   **[V]**.
5. **La ricerca del manuale interno indicizza `docs/internal/`**
   (`foliarium/ui/dialogs/admin/help_viewer.py:403`, `rglob` senza
   esclusioni) **[V]**: i rapporti interni, e questo stesso documento,
   compaiono fra i risultati di F1. L'immagine della demo esclude quella
   cartella; il problema generale resta.
