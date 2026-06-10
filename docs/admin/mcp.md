# Integrazione con Claude — MCP Server

Foliarium include un **MCP server** (Model Context Protocol) che espone
l'archivio catastale come tool invocabili da **Claude Desktop** (e da
qualunque altro client MCP compatibile).

!!! tip "Prima volta? Usa la guida facile"
    Questa pagina è il riferimento tecnico completo. Se è la tua
    prima configurazione, segui prima la
    [guida rapida passo-passo](mcp-quickstart.md): è scritta in modo
    più discorsivo e include uno script di test che verifica la catena
    prima di passare a Claude Desktop.

Una volta configurato, puoi chiedere a Claude:

> *"Cerca tutte le partite del Comune di Savona intestate a Rossi e mostra
> la genealogia di quella attiva più recente."*

Claude userà i tool MCP per interrogare l'API e risponderà con i dati reali
dell'archivio.

## Cosa serve

| Componente | Versione | Note |
|---|---|---|
| Foliarium | ≥ 1.0.2 | con API server attivo |
| Claude Desktop | qualunque recente | scaricalo da [claude.com/download](https://claude.com/download) |
| Python 3.10+ | | per eseguire il server MCP |
| `mcp` (SDK Python) | ≥ 1.0 | `pip install mcp` |
| `httpx` | ≥ 0.27 | `pip install httpx` |

## Setup in 3 passi

### 1 · Genera una chiave API

1. Apri Foliarium e loggati come **amministratore**.
2. **Impostazioni → Gestione Chiavi API…**
3. **Nuova chiave...** — dai un nome (es. *Claude Desktop*), spunta gli
   scope desiderati (di default tutti i `read:*`), eventualmente scadenza.
4. **Crea chiave** → si apre un dialog con il segreto `flr_…`.
5. Clicca **Copia negli appunti**.

!!! warning "Il segreto è mostrato una sola volta"
    Salvalo subito in un password manager. Se lo perdi, devi creare
    una nuova chiave.

### 2 · Annota la porta dell'API

L'API gira sulla porta dinamica indicata nella status bar di Foliarium
all'avvio del frontend integrato (di default `8765`). Esempio:
`http://localhost:8765`.

### 3 · Configura Claude Desktop

Apri (o crea) il file di configurazione di Claude Desktop:

- **Windows:** `%APPDATA%\Claude\claude_desktop_config.json`
- **macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Linux:** `~/.config/Claude/claude_desktop_config.json`

Aggiungi (o estendi) la sezione `mcpServers`:

```json
{
  "mcpServers": {
    "foliarium": {
      "command": "C:\\Path\\to\\foliarium\\.venv\\Scripts\\python.exe",
      "args": ["-m", "mcp_server"],
      "cwd": "C:\\Path\\to\\foliarium",
      "env": {
        "FOLIARIUM_API_BASE_URL": "http://localhost:8765",
        "FOLIARIUM_API_KEY": "flr_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
      }
    }
  }
}
```

Sostituisci:

- `command` con il percorso assoluto al Python della **venv** del progetto.
  Su Windows è `<foliarium>\.venv\Scripts\python.exe`, su macOS/Linux
  `<foliarium>/.venv/bin/python`. **Non usare `"python"` senza percorso**:
  Claude Desktop userebbe il Python di sistema, che non ha installati
  `mcp` e `httpx` (sono solo nella venv) — risultato:
  `No module named mcp_server` o `No module named mcp`.
- `cwd` con il percorso assoluto della cartella di Foliarium (quella che
  contiene il modulo `mcp_server/`).
- `FOLIARIUM_API_BASE_URL` con l'URL corretto (vedi sezione "Porta di
  ascolto" in [api.md](api.md) per fissare la porta).
- `FOLIARIUM_API_KEY` con il segreto copiato al punto 1.

Riavvia Claude Desktop. Il tool icon (🔌) in basso a destra dovrebbe
mostrare "foliarium" come server connesso.

## Tool disponibili

| Tool | Cosa fa |
|---|---|
| `elenca_comuni` | Elenco completo dei comuni (id, nome, provincia) |
| `elenca_localita` | Località (vie, piazze) di un comune |
| `cerca_partite` | Ricerca partite per comune / numero / possessore / tipo immobile |
| `dettagli_partita` | Dettaglio completo di una partita |
| `cerca_possessori` | Ricerca full-text sui possessori |
| `dettagli_possessore` | Dati anagrafici di un possessore |
| `genealogia_partita` | Predecessori e successori di una partita |
| `timeline_partita` | Variazioni cronologiche di una partita |

## Esempi di prompt

```
Mostra tutte le partite del Comune di Savona con possessori di cognome Rossi
e per ognuna riporta il numero di immobili associati.
```

```
Trova la partita 1234 di Albenga e descrivimi tutta la sua genealogia,
inclusi i frazionamenti.
```

```
Cerca i possessori con cognome "Garibaldi" e per ognuno mostra in quante
partite compare come intestatario.
```

## Troubleshooting

### `No module named mcp_server` / `No module named mcp`

Il problema più comune al primo setup. Causa: il `command` nel JSON è
`"python"` (Python di sistema) invece del Python della venv di
progetto, dove sono installati `mcp` e `httpx`.

**Fix:** punta `command` direttamente al `python.exe` della venv:

```json
"command": "C:\\Users\\TUO\\foliarium\\.venv\\Scripts\\python.exe"
```

Verifica veloce da terminale:

```powershell
C:\Users\TUO\foliarium\.venv\Scripts\python.exe -m mcp_server
```

Deve emettere su stderr un messaggio
"Configurazione mancante: imposta FOLIARIUM_API_BASE_URL e
FOLIARIUM_API_KEY…" (perché stiamo lanciando senza env var). Se invece
dice `No module named mcp` esegui:

```powershell
C:\Users\TUO\foliarium\.venv\Scripts\pip install mcp httpx
```

### Claude non vede il server "foliarium"

- Verifica che il comando completo (con percorso venv) parta da
  terminale come spiegato sopra.
- Controlla che il `cwd` nel JSON punti alla cartella corretta (deve
  contenere la sotto-cartella `mcp_server/`).
- Su Windows ricorda i doppi backslash (`\\`) nei percorsi del JSON.

### Tutti i tool restituiscono "Chiave API non valida"

- La chiave è stata revocata o scaduta. Generane una nuova e aggiorna
  il `claude_desktop_config.json`.

### "Impossibile contattare http://localhost:…"

- L'app Foliarium non è in esecuzione (il server API parte solo dopo
  il login).
- La porta nel JSON è diversa da quella reale: se non hai fissato
  `[api] port` in `config.ini`, viene scelta dinamicamente a ogni
  riavvio. Vedi [api.md → Porta di ascolto](api.md#porta-di-ascolto).

### Un tool restituisce "Permesso negato (scope mancante)"

- La chiave API non include lo scope richiesto. Revocala e creane una
  nuova con scope più ampi (es. `read:*` per dare accesso a tutta la
  lettura).

## Sicurezza

- L'MCP server gira sul **tuo PC** e parla solo con `localhost`: i dati
  catastali non escono dalla macchina.
- La chiave API è memorizzata in chiaro nel `claude_desktop_config.json`:
  proteggi il file con permessi adeguati (`chmod 600` su macOS/Linux,
  cartella utente protetta su Windows).
- Genera chiavi con il **principio del minimo privilegio**: per un uso
  read-only basta `read:*`, non serve `*:*`.

## Vedi anche

- [REST API](api.md) — documentazione degli endpoint, esempi curl
- [Specifica Model Context Protocol](https://modelcontextprotocol.io/)
