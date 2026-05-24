# Primo Avvio

## Avvio dell'applicazione

Per avviare Foliarium, fare doppio clic sull'icona **Foliarium.exe** sul desktop o nella cartella di installazione.

> 📸 **Screenshot:** Icona di Foliarium sul desktop di Windows.

---

## Schermata di benvenuto

Al primo avvio (o dopo un lungo periodo di inattività) compare la schermata di benvenuto con il logo Foliarium e un breve messaggio introduttivo.

> 📸 **Screenshot:** Schermata di benvenuto con logo Foliarium e pulsante "Continua".

---

## Login

### Inserimento credenziali

Nella schermata di login inserire:

- **Nome utente:** fornito dall'amministratore di sistema
- **Password:** la password assegnata all'account

> 📸 **Screenshot:** Finestra di login con campi utente/password e pulsante Accedi.

### Errori di connessione

Se il database non è raggiungibile, Foliarium mostra una barra rossa nella parte superiore della finestra con il messaggio **"Modalità offline"**. In questa modalità è possibile consultare i dati in cache ma non eseguire modifiche.

!!! warning "Modalità offline"
    In modalità offline le funzioni di inserimento, modifica ed esportazione aggiornata non sono disponibili. Contattare l'amministratore se il problema persiste.

---

## Finestra principale

Dopo il login viene mostrata la finestra principale di Foliarium con una **barra superiore (top bar)** e una **barra laterale (sidebar)** per la navigazione.

> 📸 **Screenshot:** Finestra principale con top bar superiore, sidebar laterale e area contenuto centrale.

### Componenti dell'interfaccia

| Area | Descrizione |
|---|---|
| **Barra superiore (Top Bar)** | Logo Foliarium, titolo pagina corrente, indicatore stato DB, nome utente, ruolo, eventuale chip scadenza licenza, pulsante logout |
| **Barra laterale (Sidebar)** | Menu di navigazione verticale con bottoni per le sezioni disponibili in base al ruolo |
| **Area contenuto** | Pannello principale che cambia al clic su un bottone della sidebar |
| **Barra di stato** | Messaggi di sistema, conferme di salvataggio e notifiche temporanee (non bloccanti) |

> 💡 **Da v1.0.1**: i messaggi di conferma (salvataggi, modifiche, eliminazioni) compaiono nella barra di stato in basso anziché in dialog modali, per non interrompere il flusso di lavoro. Gli errori e le richieste di conferma rimangono in dialog dedicati.

> 💡 **Chip scadenza licenza**: se la licenza è in scadenza, accanto al nome utente compare un'indicazione colorata (arancione ≤ 30 giorni, rosso ≤ 7 giorni). Aprire *Impostazioni → Gestione Licenza…* per i dettagli.

---

## Navigazione tra le sezioni

Fare clic sui bottoni nella **barra laterale sinistra** per passare da una sezione all'altra. I bottoni disponibili variano in base al **ruolo utente**:

| Ruolo | Sezioni disponibili |
|---|---|
| **Guest** | Consultazione, Reportistica |
| **Utente** | Consultazione, Inserimento, Esportazioni, Reportistica, Statistiche |
| **Amministratore** | Tutte le sezioni + Gestione Utenti + Backup + Audit Log |

### Shortcut da tastiera

- **Ctrl+K**: Apre la **command palette** — una finestra di ricerca rapida che permette di passare a qualsiasi pagina dell'applicazione digitando parte del nome. Naviga con le frecce, conferma con Invio, chiudi con Esc.
- **Ctrl+1...9**: Navigazione rapida ai bottoni della sidebar (in ordine)
- **F5**: Aggiorna i dati della pagina corrente
- **F1**: Apre il manuale utente integrato

---

## Selezione del tema grafico

Foliarium include 16 temi grafici selezionabili dal menu **Impostazioni → Cambia Tema Grafico**.

> 📸 **Screenshot:** Menu Impostazioni con sottomenu temi grafici espanso.

### Opzioni speciali

| Opzione | Descrizione |
|---|---|
| **Tema Automatico (Segue Sistema)** | Seleziona automaticamente tema scuro o chiaro in base alle impostazioni di Windows |
| **Stile Nativo Windows 11** | Usa lo stile nativo di Windows 11 (disponibile solo su Windows 11 con Qt 6.7+) |

!!! info "Tema scuro su Windows"
    Attivando il tema scuro in *Impostazioni di Windows → Personalizzazione → Colori*, Foliarium si adatta automaticamente se è attivo il "Tema Automatico".

---

## Timeout di sessione

Per sicurezza, Foliarium disconnette automaticamente l'utente dopo un periodo di inattività.

Quando la sessione sta per scadere compare un dialog di avviso con un countdown di 60 secondi:

- **Continua sessione** — riprende normalmente
- **Logout ora** — disconnette immediatamente
- Nessuna risposta entro 60 secondi → logout automatico

!!! info "Configurare il timeout"
    Il numero di minuti di inattività si configura da *Impostazioni → Timeout Sessione...*
    Il valore predefinito è **15 minuti**. Impostare **0** per disabilitare il timeout.

---

## Modalità Demo

La versione Demo è una build portabile che include PostgreSQL già configurato con dati
dimostrativi. Non richiede installazione né un database esterno.

### Avvio della versione demo

1. Estrarre `Foliarium_Demo_*_Portabile.zip` in qualsiasi cartella
2. Fare doppio clic su **`Foliarium_Demo.exe`**
3. Attendere il dialog **"Avvio database demo"** (3–5 secondi)
4. L'applicazione si apre con login automatico come utente `demo`

> 📸 **Screenshot:** Dialog di avvio con barra di avanzamento "Avvio database demo in corso..."

Un badge arancione **DEMO** compare nella barra superiore per indicare la modalità attiva.

!!! info "Dati inclusi nella demo"
    La demo contiene dati dimostrativi della Provincia di Savona (1870–1985):
    ~300 partite catastali e 120 possessori. I dati sono di sola lettura e non
    rappresentano archivi reali.

!!! warning "Chiusura corretta"
    Chiudere sempre la demo con il pulsante **X** o **File → Esci**, non
    terminando il processo dal Task Manager. In caso contrario PostgreSQL potrebbe
    non fermarsi correttamente.

---

## Licenza

Al primo avvio (versione completa), Foliarium verifica la presenza di un file di licenza
valido. Senza licenza valida l'applicazione non si avvia.

### Dove posizionare il file di licenza

Copiare il file **`foliarium.license`** ricevuto da Algora Studio nella stessa cartella
dell'eseguibile (`Foliarium.exe`) oppure configurare il percorso da
*Impostazioni → Gestione Licenza…*

### Dialog Gestione Licenza

Accessibile da **Impostazioni → Gestione Licenza…**, mostra:

| Campo | Descrizione |
|---|---|
| **Stato** | Valida / Non valida / Scaduta |
| **Intestata a** | Nome ente/organizzazione |
| **Tipo** | Standard / Enterprise |
| **Scadenza** | Data di scadenza o "Perpetua" |
| **Seat attivi** | Istanze in uso / massimo consentito (licenze di rete) |
| **ID hardware** | Fingerprint del computer (per licenze vincolate all'hardware) |

Il pulsante **"Copia ID hardware"** copia il fingerprint negli appunti per inviarlo
ad Algora Studio e ricevere una licenza vincolata al PC.

!!! info "Licenze di rete (multi-seat)"
    Le licenze Enterprise con più seat usano una cartella condivisa UNC per
    coordinare le istanze attive. Configurare il percorso UNC da
    *Impostazioni → Gestione Licenza…*

---

## Menu Help — Supporto e diagnostica

Il menu **Help** in alto raccoglie tutte le funzioni di assistenza:

| Voce | Funzione |
|---|---|
| **Visualizza Manuale Utente...** (F1) | Apre il manuale integrato (questo documento) |
| **Esporta log per supporto (.zip)...** | Crea un archivio ZIP con tutti i log applicativi, pronto da allegare a una mail |
| **Informazioni su Foliarium / EULA...** | Versione, licenza e contratto EULA |

### Esportare i log per il supporto tecnico

Quando il supporto Algora chiede di inviare i log, basta selezionare
**Help → Esporta log per supporto (.zip)...**: viene proposto un nome
predefinito con timestamp (es. `foliarium_logs_20260524_153012.zip`) e
una destinazione nella cartella **Documenti**. Confermando, l'app
comprime tutti i file di `%LOCALAPPDATA%\Foliarium\logs\` (incluse le
rotazioni storiche) in un unico archivio da allegare a una mail per
**info@algorastudio.it**.

L'archivio contiene **solo** i log applicativi: nessun dato del
database, nessuna credenziale, nessuna licenza.

---

## Chiusura dell'applicazione

Per chiudere Foliarium usare:
- Il pulsante **X** in alto a destra della finestra
- Il menu **File → Esci**
- La combinazione di tasti **Alt+F4**

Se sono presenti operazioni in corso (import, export), verrà chiesta conferma prima di chiudere.
