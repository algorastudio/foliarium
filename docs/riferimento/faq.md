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

### Meridiana si avvia in "Modalità offline" — cosa significa?

Significa che Meridiana non riesce a raggiungere il database PostgreSQL. In questa modalità:
- I dati in cache locale (ultima sessione) sono accessibili in sola lettura
- Le funzioni di inserimento, modifica ed esportazione aggiornata sono disabilitate

Verificare la connessione al database (vedi sopra).

---

## Interfaccia e temi

### Come cambio il tema grafico?

Menu **Impostazioni → Cambia Tema Grafico** → selezionare uno dei 16 temi disponibili.

### Il tema non si aggiorna dopo il cambio

Alcune modifiche al tema richiedono il riavvio dell'applicazione. Chiudere e riaprire Meridiana.

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

## Performance

### Meridiana è lenta ad avviarsi

Il primo avvio può richiedere più tempo per inizializzare la connessione al database. Se il problema persiste:
- Verificare le prestazioni del server PostgreSQL
- Controllare i log (`config.py` → cartella log) per messaggi di errore

### I grafici nella sezione Statistiche non si caricano

Fare clic su **Aggiorna Grafici**. Se il problema persiste verificare che `matplotlib` sia installato correttamente:
```bash
pip install "matplotlib>=3.9.0"
```

---

## Build e installazione (per tecnici)

### PyInstaller genera un eseguibile che non si avvia

Verificare che il file `meridiana.spec` sia aggiornato con tutti i data files e i hidden imports. Controllare il log di avvio in:
```
%LOCALAPPDATA%\Meridiana\logs\
```

### L'installer Inno Setup non trova l'eseguibile

Eseguire prima `pyinstaller meridiana.spec` e verificare che `dist/Meridiana/Meridiana.exe` esista prima di compilare l'installer.

---

## Domande sul manuale

### Dove trovo le istruzioni per installare Meridiana su un nuovo PC?

Consultare la sezione [Installazione e Configurazione](../admin/installazione.md) nella Guida Amministratore.

### Come faccio a generare il backup del database?

Consultare la sezione [Backup e Ripristino](../admin/backup.md).
