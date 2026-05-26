# Domande Frequenti (FAQ)

## Connessione e accesso

### Non riesco ad accedere — compare "Database non raggiungibile"

Verificare che:
1. Il server PostgreSQL sia avviato (Servizi Windows → `postgresql-x64-14`)
2. Le variabili d'ambiente `DB_HOST`, `DB_PORT` siano corrette
3. Non ci siano firewall che bloccano la porta 5432
4. Le credenziali `DB_USER` e `DB_PASS` siano corrette

Se il database è su un server remoto, verificare la connettività di rete:
```
ping <indirizzo-server>
telnet <indirizzo-server> 5432
```

---

### Ho dimenticato la password — come la recupero?

Le password sono memorizzate con hashing bcrypt e non sono recuperabili. Chiedere all'**amministratore** di reimpostare la password dal pannello **Gestione Utenti**.

---

### Foliarium si avvia in "Modalità offline" — cosa significa?

Significa che Foliarium non riesce a raggiungere il database PostgreSQL. In questa modalità:
- I dati in cache locale (ultima sessione) sono accessibili in sola lettura
- Le funzioni di inserimento, modifica ed esportazione aggiornata sono disabilitate

Verificare la connessione al database (vedi sopra).

---

## Interfaccia e temi

### Come cambio il tema grafico?

Menu **Impostazioni → Cambia Tema Grafico** → selezionare uno dei 16 temi disponibili.

### Il tema non si aggiorna dopo il cambio

Alcune modifiche al tema richiedono il riavvio dell'applicazione. Chiudere e riaprire Foliarium.

### Su un altro PC i colori del tema sono diversi o illeggibili

Da v1.0.2 il tema viene applicato sopra lo stile base **Fusion** in modo
forzato all'avvio: ciò garantisce che la palette risulti identica su
qualunque PC, indipendentemente dallo stile Qt nativo del sistema
(`windowsvista`, `windows11`, GTK, …). Se sei su una versione precedente
e i colori risultano illeggibili, aggiorna a v1.0.2 o seleziona
manualmente uno dei temi da **Impostazioni → Cambia Tema Grafico**.

Se nei log compare l'avviso `Unknown property text-shadow`, anche questo
è stato risolto in v1.0.2 con la pulizia di alcune regole QSS non
supportate da Qt.

### Non vedo le tab "Gestione Utenti" e "Backup"

Queste tab sono visibili solo agli utenti con ruolo **Amministratore**. Verificare il ruolo dell'account in uso con l'amministratore.

---

## Ricerca e consultazione

### La ricerca non trova risultati anche se i dati esistono

Verificare che:
- Il **comune** selezionato nel filtro sia corretto
- I filtri aggiuntivi non stiano escludendo i risultati
- Lo stato della partita (Attiva/Non attiva) sia impostato su "Tutte"

Provare a cancellare tutti i filtri e cercare solo per numero partita.

### La ricerca fuzzy restituisce troppi risultati irrilevanti

Aumentare la **soglia di similarità** allo slider (portarla a 80–90%). Una soglia più alta richiede corrispondenze più precise.

---

## Inserimento e importazione

### Durante l'import CSV compare "Errore: colonna non trovata"

Verificare che le intestazioni del CSV corrispondano esattamente al template. Scaricare il template aggiornato con **Scarica Template** e reimpostare le intestazioni.

### Il CSV è stato creato con Excel e i caratteri accentati sono errati

Excel su Windows salva spesso i CSV in formato ANSI (Windows-1252) invece di UTF-8. Aprire il file con Notepad, fare *File → Salva con nome → Codifica: UTF-8*.

### "Errore di permessi" durante l'esportazione Excel

Il file `.xlsx` di destinazione è probabilmente aperto in Excel. Chiuderlo prima di avviare l'esportazione.

---

## Supporto tecnico

### Come invio i log al supporto Algora?

Dal menu in alto selezionare **Help → Esporta log per supporto (.zip)...**:
viene chiesto dove salvare l'archivio (default: cartella Documenti, nome con
timestamp). Il file `.zip` risultante contiene tutti i log applicativi (compresi
i log ruotati) e può essere allegato direttamente a una mail per
**info@algorastudio.it**.

In alternativa i log sono leggibili manualmente in
`%LOCALAPPDATA%\AlgoraStudio\Foliarium\` (file `foliarium_session.log` in
radice, file `logs\foliarium_gui.log` + rotazioni nella sotto-cartella).

!!! info "Cosa contiene l'archivio"
    L'archivio include solo i log applicativi (`foliarium_gui.log*`). Non
    contiene dati del database, credenziali o licenze.

---

## Performance

### Foliarium è lenta ad avviarsi

Il primo avvio può richiedere più tempo per inizializzare la connessione al database. Se il problema persiste:
- Verificare le prestazioni del server PostgreSQL
- Esportare i log con **Help → Esporta log per supporto (.zip)...** e inviarli ad Algora Studio

### I grafici nella sezione Statistiche non si caricano

Fare clic su **Aggiorna Grafici**. Se il problema persiste verificare che `matplotlib` sia installato correttamente:
```bash
pip install "matplotlib>=3.9.0"
```

---

## Build e installazione (per tecnici)

### PyInstaller genera un eseguibile che non si avvia

Verificare che il file `foliarium.spec` sia aggiornato con tutti i data files e i hidden imports. Controllare il log di avvio in:
```
%LOCALAPPDATA%\Foliarium\logs\
```

### L'installer Inno Setup non trova l'eseguibile

Eseguire prima `pyinstaller foliarium.spec` e verificare che `dist/Foliarium/Foliarium.exe` esista prima di compilare l'installer.

### L'installer si blocca con "DeleteFile fallito; codice 5" su una DLL di PostgreSQL

Il servizio `FoliariumDB` è ancora in esecuzione da una installazione
precedente e tiene bloccato il file. Il fix automatico è incluso dalla
versione 1.6.0 — se stai reinstallando una versione più vecchia, apri
PowerShell come amministratore ed esegui:

```powershell
net stop FoliariumDB
taskkill /F /IM postgres.exe
```

Poi clicca **Riprova** nell'errore.

### Dopo l'installazione l'app non trova `config.ini` o `foliarium.license`

Dalla versione 1.6.0 l'app cerca questi file **accanto a `Foliarium.exe`**
(es. `C:\Program Files (x86)\Foliarium\`). Se stai usando una versione
precedente puoi copiarli manualmente nella sottocartella `_internal\`
come workaround, oppure aggiornare all'ultima versione.

---

## Domande sul manuale

### Dove trovo le istruzioni per installare Foliarium su un nuovo PC?

Consultare la sezione [Installazione e Configurazione](../admin/installazione.md) nella Guida Amministratore.

### Come faccio a generare il backup del database?

Consultare la sezione [Backup e Ripristino](../admin/backup.md).
