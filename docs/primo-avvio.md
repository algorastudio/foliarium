# Primo Avvio

## Avvio dell'applicazione

Per avviare Meridiana, fare doppio clic sull'icona **Meridiana.exe** sul desktop o nella cartella di installazione.

> 📸 **Screenshot:** Icona di Meridiana sul desktop di Windows.

---

## Schermata di benvenuto

Al primo avvio (o dopo un lungo periodo di inattività) compare la schermata di benvenuto con il logo Meridiana e un breve messaggio introduttivo.

> 📸 **Screenshot:** Schermata di benvenuto con logo Meridiana e pulsante "Continua".

---

## Login

### Inserimento credenziali

Nella schermata di login inserire:

- **Nome utente:** fornito dall'amministratore di sistema
- **Password:** la password assegnata all'account

> 📸 **Screenshot:** Finestra di login con campi utente/password e pulsante Accedi.

### Errori di connessione

Se il database non è raggiungibile, Meridiana mostra una barra rossa nella parte superiore della finestra con il messaggio **"Modalità offline"**. In questa modalità è possibile consultare i dati in cache ma non eseguire modifiche.

!!! warning "Modalità offline"
    In modalità offline le funzioni di inserimento, modifica ed esportazione aggiornata non sono disponibili. Contattare l'amministratore se il problema persiste.

---

## Finestra principale

Dopo il login viene mostrata la finestra principale di Meridiana.

> 📸 **Screenshot:** Finestra principale con toolbar superiore, barra laterale di navigazione e area contenuto centrale.

### Componenti dell'interfaccia

| Area | Descrizione |
|---|---|
| **Barra superiore** | Menu (File, Impostazioni, Aiuto), pulsanti rapidi |
| **Tab di navigazione** | Accesso alle sezioni: Consultazione, Inserimento, Esportazioni, Reportistica, Statistiche |
| **Area contenuto** | Pannello principale che cambia in base alla sezione selezionata |
| **Barra di stato** | Utente connesso, stato DB, messaggi di sistema |

---

## Navigazione tra le sezioni

Fare clic sulle tab nella barra superiore o sulle voci del menu laterale per passare da una sezione all'altra.

Le tab disponibili variano in base al **ruolo utente**:

| Ruolo | Tab disponibili |
|---|---|
| **Guest** | Consultazione, Reportistica |
| **Utente** | Consultazione, Inserimento, Esportazioni, Reportistica, Statistiche |
| **Amministratore** | Tutte le sezioni + Gestione Utenti + Backup + Audit Log |

---

## Selezione del tema grafico

Meridiana include 16 temi grafici selezionabili dal menu **Impostazioni → Cambia Tema Grafico**.

> 📸 **Screenshot:** Menu Impostazioni con sottomenu temi grafici espanso.

### Opzioni speciali

| Opzione | Descrizione |
|---|---|
| **Tema Automatico (Segue Sistema)** | Seleziona automaticamente tema scuro o chiaro in base alle impostazioni di Windows |
| **Stile Nativo Windows 11** | Usa lo stile nativo di Windows 11 (disponibile solo su Windows 11 con Qt 6.7+) |

!!! info "Tema scuro su Windows"
    Attivando il tema scuro in *Impostazioni di Windows → Personalizzazione → Colori*, Meridiana si adatta automaticamente se è attivo il "Tema Automatico".

---

## Timeout di sessione

Per sicurezza, Meridiana disconnette automaticamente l'utente dopo un periodo di inattività.

Quando la sessione sta per scadere compare un dialog di avviso con un countdown di 60 secondi:

- **Continua sessione** — riprende normalmente
- **Logout ora** — disconnette immediatamente
- Nessuna risposta entro 60 secondi → logout automatico

!!! info "Configurare il timeout"
    Il numero di minuti di inattività si configura da *Impostazioni → Timeout Sessione...*
    Il valore predefinito è **15 minuti**. Impostare **0** per disabilitare il timeout.

---

## Chiusura dell'applicazione

Per chiudere Meridiana usare:
- Il pulsante **X** in alto a destra della finestra
- Il menu **File → Esci**
- La combinazione di tasti **Alt+F4**

Se sono presenti operazioni in corso (import, export), verrà chiesta conferma prima di chiudere.
