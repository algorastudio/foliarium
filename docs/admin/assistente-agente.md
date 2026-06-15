# Assistente intelligente / Agente — analisi e roadmap

!!! note "Documento di discussione, non guida operativa"
    Questa pagina è un'analisi di prodotto: valuta **se e come** trasformare
    l'integrazione MCP esistente in un assistente/agente intelligente
    affiancato a Foliarium. Non descrive una funzionalità già rilasciata.
    Serve come base di discussione interna (Algora Studio) e con il cliente.

## Punto di partenza: cosa abbiamo già

Foliarium espone l'archivio in due strati pensati per le integrazioni:

- **REST API** (`api/`, FastAPI su `localhost`, doppia autenticazione
  sessione/API-key con scope granulari).
- **MCP server** (`mcp_server/`, 23 tool: lettura + scrittura "sicura" +
  scrittura distruttiva, con conferma esplicita `confirm=True`).

Questo è il **"corpo"** di un agente: la capacità di leggere e operare
sull'archivio in modo controllato. Manca solo il **"cervello"** (un modello
Claude che decide quali tool invocare) e una **UI**. Gran parte del lavoro
difficile — e rischioso — è già fatto.

## Il vincolo che decide l'architettura: i dati sono locali

L'API gira su `localhost` e PostgreSQL è sulla macchina dell'archivista.
Quindi **il loop dell'agente deve girare in locale** (nell'app o in un
processo sulla stessa macchina), usando l'API di Anthropic *solo come
modello*; i tool vengono eseguiti localmente.

!!! warning "I Managed Agents di Anthropic non sono adatti qui"
    L'opzione "agente gestito" (Anthropic ospita il loop e un container)
    **non può raggiungere `localhost:8765`**. La strada corretta è
    **SDK Anthropic + tool use con compute locale**.

Da tenere distinte **due chiavi**:

- `flr_…` — autorizza verso la *nostra* REST API (scope `read:*` / `write:*`).
- `ANTHROPIC_API_KEY` — autorizza verso il *modello* Claude (costo a consumo).

## Tre forme possibili dell'agente

Non si escludono: si possono stratificare nel tempo.

| | Embedded in-app | Agente locale indipendente | Claude Desktop |
|---|---|---|---|
| **Cosa vede l'utente** | Pannello "Assistente" dentro Foliarium | Processo a sé (CLI, tray, schedulato) | App separata già esistente |
| **Caso d'uso forte** | Consultazione + operazioni guidate | Automazioni non interattive (report notturni, controllo incongruenze) | Power-user / interno, subito |
| **Sforzo** | Medio | Basso-medio | Zero (già pronto) |
| **Riusa l'MCP?** | Sì (23 tool) | Sì | Sì |

**Claude Desktop è di fatto un MVP gratuito**: permette di validare se gli
archivisti trovano utile "parlare" con l'archivio, prima di investire
nell'embedded. Vale la pena metterlo in mano a 1-2 utenti reali e osservare
*cosa chiedono davvero* (consultazione vs operazioni).

## Costi del modello

Costo a token. Con `claude-opus-4-8`: ~$5 / milione token input,
~$25 / milione output. In pratica, per uso umano (non batch massivo):

- Una conversazione tipica = migliaia, non milioni, di token → **ordine dei
  centesimi a interazione**.
- Driver di costo: numero di tool call (i risultati rientrano in input a ogni
  giro), dimensione del system prompt, modello scelto.
- Leve di risparmio, in ordine di efficacia:
    - **`claude-sonnet-4-6`** (~$3/$15) per il grosso del traffico, tenendo
      Opus per i compiti difficili;
    - **prompt caching** del system prompt + elenco tool (stabili) → ~1/10 del
      costo dopo la prima volta;
    - **`effort` basso** per le risposte semplici.

**Conclusione:** per un'app desktop il costo modello è marginale. La domanda
vera non è "costa troppo?" ma **"chi lo paga e come si fattura?"**.

## Privacy e profilo legale — il nodo più serio

Distinzione fondamentale per un Archivio di Stato:

- **I dati restano in locale** (DB e API non si spostano).
- **Ma il testo della conversazione esce**: le domande dell'utente e i
  **risultati dei tool** (nomi di possessori, partite, dati catastali)
  vengono inviati all'API di Anthropic per l'elaborazione del modello.

Va affrontato esplicitamente, non assunto:

- **Zero Data Retention (ZDR)** lato Anthropic come opzione contrattuale (da
  verificare per il modello scelto).
- Possibilità di **limitare l'assistente alla sola lettura** per default, o
  una modalità "solo aggregati/metadati" che non invii nominativi.
- Disclaimer esplicito nell'EULA/contratto + probabile valutazione GDPR.
- L'alternativa "nessun dato esce mai" implicherebbe un **LLM locale on-prem**
  — altro ordine di complessità e qualità inferiore: ipotesi futura, non per
  ora.

Approccio consigliato: trattare la privacy come **feature configurabile**
(assistente attivabile dall'admin, scelta scope read-only/write, disclaimer su
cosa viene inviato), non come ostacolo.

## Sicurezza operativa — già coperta dall'esistente

Il lavoro fatto sull'MCP paga:

- **Scope delle API key** → un assistente con chiave `read:*` non può scrivere.
- **Gate `confirm=True`** → in un assistente embedded diventa un dialog Qt
  nativo prima di ogni scrittura. Pattern corretto: **l'LLM propone, l'umano
  dispone** — nessuna scrittura parte senza conferma.

## La decisione che sblocca le altre: proprietà della chiave Anthropic

| | Fornitore (Algora) | Bring-your-own-key (cliente) |
|---|---|---|
| **UX cliente** | Semplicissima | Setup più macchinoso |
| **Costo modello** | A carico del fornitore | A carico del cliente |
| **Privacy/responsabilità** | Dati del cliente sul *nostro* account Anthropic → contrattualmente pesante | Dati del cliente sul *loro* contratto → più difendibile per un ente pubblico |

Per un cliente "Archivio di Stato", **BYO-key è istintivamente più
difendibile** (i loro dati sul loro contratto), anche se meno comodo. Dipende
dal modello commerciale di Algora.

## Roadmap consigliata

1. **Validare con Claude Desktop** su utenti reali (zero sviluppo) → capire se
   chiedono lettura o scrittura.
2. **Decidere chiave + privacy** — è la decisione *bloccante*, non il codice.
3. Se confermato: **assistente embedded read-only** come primo incremento.
4. Solo dopo: **abilitazione scrittura con conferma** (dialog Qt sul gate
   `confirm`).
5. (Eventuale) **agente locale schedulato** per automazioni non interattive
   (es. report notturno di incongruenze).

## Come si aggancerebbe tecnicamente (sintesi)

L'SDK Python di Anthropic parla direttamente con un server MCP via stdio e
gestisce il loop di tool-use. In pratica: si lancia `python -m mcp_server`
come sottoprocesso, si passano i suoi tool al `tool_runner` del modello, e si
streamma la risposta nel pannello chat (in un worker thread, mai sul thread
della GUI). Gli stessi 23 tool MCP esistenti vengono riusati senza
duplicazione; il gate `confirm` si mappa su una conferma utente nativa.

## Vedi anche

- [REST API & Integrazioni](api.md)
- [Integrazione Claude (MCP, dettagli)](mcp.md)
- [Claude + Foliarium (guida rapida)](mcp-quickstart.md)
