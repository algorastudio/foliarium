# REST API & Integrazioni esterne

Foliarium espone una REST API (FastAPI) per consentire integrazioni con
sistemi esterni (MCP server per Claude, automazioni Zapier, script di
backup/export, BI). L'API gira **localmente** sul PC dell'archivista
(`127.0.0.1:8765+`) ed è esposta solo finché l'app desktop è in esecuzione.

## Versioning

Tutti gli endpoint sono disponibili con il prefisso versionato:

- **`/api/v1/*`** — versione preferita, contratto stabile per integrazioni
- **`/api/*`** — alias legacy, mantenuto per il frontend React esistente

Documentazione interattiva:

| URL | Cosa contiene |
|---|---|
| `http://localhost:<porta>/api/v1/docs` | Swagger UI: prova gli endpoint dal browser |
| `http://localhost:<porta>/api/v1/redoc` | ReDoc: documentazione statica |
| `http://localhost:<porta>/api/v1/openapi.json` | Schema OpenAPI 3 (per generare client) |

La porta esatta cambia ad ogni avvio (allocata dinamicamente a partire
da 8765). La trovi nel log applicativo o nella status bar dell'app.

## Autenticazione

L'API accetta due metodi di autenticazione equivalenti:

### Sessione utente (`Authorization: Bearer …`)

Usata internamente dal frontend React di Foliarium. Token UUID
generato al login, valido 120 minuti, rinnovato a ogni richiesta.
Implicitamente ha **tutti gli scope**.

### Chiave API (`X-Foliarium-Api-Key: flr_…`)

Per **integrazioni esterne** (MCP, Zapier, script). Persistente in DB,
con scope granulari, revocabile dalla UI.

Generazione:

1. Avvia Foliarium e loggati come **amministratore**.
2. Apri **Impostazioni → Gestione Chiavi API…**
3. **Nuova chiave...**, dai un nome (es. *MCP server Marco*), seleziona
   gli scope (di default tutti i `read:*`), opzionalmente una scadenza.
4. **Crea chiave** → si apre il dialog con il segreto in chiaro
   (`flr_<32 hex>`). **Copialo subito**: non è più recuperabile.

!!! warning "Sicurezza"
    - La chiave in chiaro non è mai memorizzata in DB: si conserva solo
      lo SHA-256. Se la perdi, devi crearne una nuova.
    - Non condividere chiavi via email/chat in chiaro. Usa un password
      manager.
    - In caso di sospetta compromissione, **revoca subito** la chiave
      dalla stessa UI (effetto immediato).

## Scope disponibili

| Scope | Descrizione |
|---|---|
| `read:comuni` | Lettura elenco comuni |
| `read:partite` | Lettura partite catastali |
| `read:possessori` | Lettura possessori |
| `read:audit` | Lettura audit log |
| `read:dashboard` | Lettura statistiche dashboard |
| `read:genealogia` | Lettura albero genealogico partite |
| `read:timeline` | Lettura timeline variazioni |
| `write:partite` | Creazione/modifica partite |
| `write:possessori` | Creazione/modifica possessori |
| `read:*` | Wildcard: tutti gli scope di lettura |
| `*:*` | Accesso totale (riservato) |

## Esempi `curl`

```bash
# Variabili
API="http://localhost:8765/api/v1"
KEY="flr_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"

# Elenco comuni
curl -H "X-Foliarium-Api-Key: $KEY" "$API/comuni"

# Cerca partite di un comune con un certo possessore
curl -H "X-Foliarium-Api-Key: $KEY" \
     "$API/partite?comune_id=1&possessore=rossi"

# Dettagli partita
curl -H "X-Foliarium-Api-Key: $KEY" "$API/partite/42"

# Genealogia (predecessori/successori)
curl -H "X-Foliarium-Api-Key: $KEY" "$API/genealogia/42"
```

## Codici di errore

| Status | Significato |
|---|---|
| `401` | Chiave API mancante, non valida, scaduta o revocata |
| `403` | Chiave API valida ma senza lo scope richiesto |
| `404` | Risorsa inesistente (es. partita_id non trovato) |
| `503` | Database temporaneamente non disponibile (vedi log app) |
| `5xx` | Errore interno — esporta i log da *Help → Esporta log per supporto* |

## Audit

Ogni chiamata autenticata tramite chiave API viene tracciata nell'audit log
(visibile dalla sezione *Audit Log* dell'app) con username `api-key:<prefix>`
e l'IP del chiamante.

## Vedi anche

- [Integrazione con Claude (MCP server)](mcp.md)
- [Gestione utenti e ruoli](gestione-utenti.md)
