# Guida rapida — Far parlare Claude con Foliarium

Questa è la versione "tutti i passi raccontati" per collegare **Claude
Desktop** all'archivio catastale Foliarium. Se sei alla prima volta,
seguila riga per riga: ogni passo va completato prima di passare al
successivo.

!!! tip "Quanto ci vuole?"
    Circa **15 minuti** la prima volta. Le volte successive: zero
    minuti — basta avere Foliarium aperto.

---

## Cosa stiamo facendo, in due parole

Foliarium ha al suo interno un piccolo "server" che parla via Internet
(sul tuo PC, in locale). Claude Desktop sa parlare con server di
questo tipo (si chiamano **MCP server**). In mezzo serve una **chiave
segreta** che dice a Foliarium "sì, questo Claude è autorizzato".

```
   Tu  ─→  Claude Desktop  ─→  server MCP di Foliarium  ─→  Database
                              (parla con la "chiave segreta")
```

Una volta collegato, puoi chiedere a Claude cose tipo:

> *"Trova tutte le partite di Savona intestate a Rossi e dimmi quale
> ha l'immobile più grande."*

e Claude risponderà con i dati veri del tuo archivio.

---

## Passo 1 — Apri Foliarium e accedi come amministratore

Avvia Foliarium normalmente e fai login con un account che ha ruolo
**Amministratore**. Solo gli admin possono generare chiavi API.

!!! tip "L'API parte da sola"
    Dalla v1.0.2 il server API si avvia in background **automaticamente
    dopo il login**, anche nella modalità classica. Non devi più
    scegliere modalità diverse né lanciare comandi.

---

## Passo 2 — Fissa la porta del server

Apri `config.ini` accanto a `Foliarium.exe` (o nella cartella del
progetto se sviluppi da sorgente) e aggiungi/verifica:

```ini
[api]
port = 8765
```

In alternativa puoi impostare la variabile d'ambiente
`FOLIARIUM_API_PORT=8765`.

!!! tip "Perché fissarla?"
    Senza una porta fissa, Foliarium ne sceglie una libera a ogni avvio.
    Se cambia, devi aggiornare manualmente il `claude_desktop_config.json`
    del passo 6. Fissandola una volta sola eviti il problema.

In alto a destra in Foliarium, dopo il login, vedi un piccolo indicatore
**● API: on (porta 8765)** in verde. Cliccaci sopra per leggere
l'URL completo. Ti serve nel passo 4.

---

## Passo 3 — Genera la chiave segreta

1. Dal menu in alto, vai su **Impostazioni → Gestione Chiavi API…**
2. Clicca **Nuova chiave...**
3. Compila:
    - **Nome identificativo**: scrivi qualcosa che riconoscerai poi
      (es. `Claude Desktop sul mio portatile`)
    - **Validità**: lasciala "Imposta scadenza" spuntata con la data di
      tra un anno. Così, anche se la chiave sfugge, scade da sola.
    - **Scope concessi**: lascia spuntati tutti i `read:*` che sono
      preselezionati. Sono "permessi di sola lettura": Claude potrà
      *leggere* l'archivio ma non *modificare* nulla.
4. Clicca **Crea chiave**.

Si aprirà una finestra con la chiave in chiaro, qualcosa tipo:

```
flr_a3b9c1d2e4f5a6b7c8d9e0f1a2b3c4d5
```

⚠️ **Cliccala una volta sola su "Copia negli appunti".**
Questa chiave non sarà più visibile dopo aver chiuso la finestra
(in archivio è memorizzata cifrata, non in chiaro).

Incollala subito in un posto sicuro — un password manager, o un appunto
salvato sul desktop. **Non condividerla via mail o chat.**

---

## Passo 4 — Verifica che tutto funzioni (script di test)

Prima di toccare Claude Desktop, controlliamo che la catena funzioni.
Apri un terminale (PowerShell su Windows, Terminale su macOS/Linux),
spostati nella cartella di Foliarium, e digita (sostituendo i due
valori):

=== "Windows (PowerShell)"

    ```powershell
    cd C:\Path\to\foliarium
    $env:FOLIARIUM_API_BASE_URL = "http://localhost:8765"
    $env:FOLIARIUM_API_KEY = "flr_la_tua_chiave_qui"
    python bin\test_mcp_e2e.py
    ```

=== "macOS / Linux"

    ```bash
    cd /path/to/foliarium
    export FOLIARIUM_API_BASE_URL=http://localhost:8765
    export FOLIARIUM_API_KEY=flr_la_tua_chiave_qui
    python bin/test_mcp_e2e.py
    ```

Lo script controlla in 4 step:

1. **Configurazione**: URL e chiave sono presenti.
2. **Connettività**: l'API risponde e la chiave è valida.
3. **8 tool MCP**: ognuno chiama l'API correttamente.
4. **Registrazione**: il server MCP espone tutti gli 8 tool.

Se vedi alla fine:

```
✓ Tutto funziona. La catena è pronta per Claude Desktop.
```

→ vai al passo 5. Altrimenti lo script ti dice cosa c'è che non va
(chiave sbagliata, porta diversa, app non avviata…) e cosa fare.

---

## Passo 5 — Installa Claude Desktop

Scarica e installa da [claude.com/download](https://claude.com/download).
Esiste per Windows, macOS e Linux. Avvialo almeno una volta e fai
login con il tuo account Anthropic (anche gratuito va bene per i
test).

---

## Passo 6 — Configura Claude Desktop

Claude Desktop legge la lista dei server MCP da un file di
configurazione. Bisogna creare/modificare quel file e dirgli "ehi,
c'è anche Foliarium".

### Trova il file giusto

| Sistema | Percorso |
|---|---|
| Windows | `%APPDATA%\Claude\claude_desktop_config.json` |
| macOS | `~/Library/Application Support/Claude/claude_desktop_config.json` |
| Linux | `~/.config/Claude/claude_desktop_config.json` |

Per andarci velocemente:

- **Windows**: premi `Win+R`, scrivi `%APPDATA%\Claude` e premi Invio.
- **macOS**: in Finder premi `Cmd+Shift+G` e incolla
  `~/Library/Application Support/Claude`.

Se il file `claude_desktop_config.json` non c'è, **crealo tu** (con
Notepad / TextEdit / qualunque editor di testo). Se c'è già, aprilo
e ci aggiungeremo una sezione.

### Incolla questo contenuto

Se il file è **vuoto / appena creato**, incolla tutto:

```json
{
  "mcpServers": {
    "foliarium": {
      "command": "python",
      "args": ["-m", "mcp_server"],
      "cwd": "C:\\Path\\to\\foliarium",
      "env": {
        "FOLIARIUM_API_BASE_URL": "http://localhost:8765",
        "FOLIARIUM_API_KEY": "flr_la_tua_chiave_qui"
      }
    }
  }
}
```

Se il file **c'era già** e aveva altri server MCP, aggiungi solo la
voce `"foliarium": { … }` dentro `"mcpServers": { … }`.

### Sostituisci 3 cose

1. **`"cwd"`** → la cartella **dove hai Foliarium installato**.
   Su Windows ricorda di mettere `\\` (doppia barra) al posto di `\`.
   Esempio reale: `"C:\\Program Files\\Foliarium"` oppure
   `"C:\\Users\\Marco\\foliarium-source"`.
2. **`FOLIARIUM_API_BASE_URL`** → l'URL del passo 2 (la porta giusta!).
3. **`FOLIARIUM_API_KEY`** → la chiave segreta del passo 3.

Salva il file.

---

## Passo 7 — Riavvia Claude Desktop

Chiudi Claude Desktop **completamente** (tasto destro sull'icona nella
barra delle applicazioni → Esci) e riaprilo.

In basso a destra nella finestra di chat dovresti vedere una piccola
icona a forma di **spina/presa elettrica** 🔌. Cliccaci: dovrebbe
comparire `foliarium` tra i server connessi con un pallino verde.

---

## Passo 8 — Prova!

Apri una nuova chat e prova un prompt come:

> "Mostrami l'elenco completo dei comuni nell'archivio Foliarium."

Claude ti dirà "sto usando il tool `elenca_comuni`…" e ti risponderà
con i tuoi comuni veri. 🎉

Altri prompt da provare:

- "Quante partite ha il comune di Albenga? Mostrane qualcuna."
- "Cerca i possessori di cognome Garibaldi e dimmi a quante partite
  sono associati."
- "Trovami la partita numero 123 di Savona, descrivimi gli immobili e
  la genealogia."

---

## Se qualcosa non va

| Sintomo | Cosa fare |
|---|---|
| Claude non vede il server "foliarium" | Esegui di nuovo `python bin\test_mcp_e2e.py` — se passa, l'errore è nel `claude_desktop_config.json` (di solito il `cwd` o le virgolette). |
| Tutti i tool dicono "Chiave API non valida" | La chiave è scaduta o l'hai revocata. Torna al passo 3 e generane una nuova. |
| "Impossibile contattare http://localhost:…" | Foliarium non è aperto oppure la porta nel JSON non corrisponde a quella vera (cambia ad ogni avvio!). |
| "Permesso negato (scope mancante)" | La chiave non ha lo scope giusto. Revocala e creane una nuova con `read:*` spuntato. |

Per problemi più seri: esporta i log da **Help → Esporta log per
supporto (.zip)…** e mandali a info@algorastudio.it.

---

## E ora?

- Vuoi i dettagli tecnici? Leggi la versione completa in
  [Integrazione Claude (MCP)](mcp.md).
- Vuoi capire l'API REST per scriverci sopra script Python o
  integrazioni Zapier? Vedi [REST API & Integrazioni](api.md).
