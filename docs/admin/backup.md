# Backup e Ripristino

La sezione **Backup** di Foliarium consente di eseguire backup del database catastale e di ripristinarlo in caso di necessità. È accessibile solo agli utenti con ruolo Amministratore.

> 📸 **Screenshot:** Sezione Backup con pulsanti Backup Manuale, Pianifica Backup, Ripristina, e log backup recenti.

!!! danger "Backup regolari obbligatori"
    Il database catastale contiene dati storici irreproducibili. Si raccomanda di eseguire backup giornalieri automatici e di conservare almeno gli ultimi 7 backup.

---

## Backup manuale

1. Andare in **Backup** dalla barra di navigazione
2. Fare clic su **Esegui Backup Ora**
3. Scegliere la cartella di destinazione (o confermare quella predefinita)
4. Attendere il completamento

Foliarium esegue un `pg_dump` del database e salva il file `.backup` con la data nel nome:

```
foliarium_backup_2026-03-02_14-30-00.backup
```

> 📸 **Screenshot:** Finestra di progresso backup con barra di avanzamento e messaggio di completamento.

---

## Cifratura del backup (consigliata)

Nella sezione Backup è disponibile l'opzione **"Cifra il file di backup"** (attiva
per impostazione predefinita). Quando attiva, al termine del `pg_dump` Foliarium
cifra il file con **AES-256-GCM** e rimuove la copia in chiaro, producendo un file
con estensione `.enc` (es. `..._backup.dump.enc`).

La **chiave di cifratura** (256 bit) viene generata automaticamente alla prima
cifratura e custodita nel **keyring di sistema** della macchina (Gestione
credenziali di Windows), sotto il servizio `Foliarium_BackupKey`. Il file `.enc`
è quindi inutilizzabile se sottratto (USB, disco, copia di rete) senza accesso al
keyring di quella macchina.

Il **ripristino** di un file `.enc` è trasparente: Foliarium rileva la cifratura,
decifra il backup in un file temporaneo, esegue il ripristino e poi rimuove il
temporaneo.

!!! danger "Conserva la chiave di backup"
    Se il keyring della macchina viene perso (reinstallazione del sistema, cambio
    PC, profilo utente eliminato) **i backup cifrati non sono più ripristinabili**.
    Per il disaster recovery usa **Esporta chiave...** (vedi sotto) e conserva il
    file insieme alla passphrase in un luogo protetto e separato dai backup.

### Esporta / importa la chiave di cifratura

Nella sezione Backup, accanto all'opzione di cifratura, sono disponibili due pulsanti:

- **Esporta chiave...** — salva una copia della chiave in un file `.key` **protetto
  da passphrase** (la chiave non viene mai scritta in chiaro: è incapsulata con una
  chiave derivata dalla passphrase tramite *scrypt* + AES-256-GCM). Conserva il file
  e la passphrase in luoghi sicuri e separati dai backup.
- **Importa chiave...** — su una nuova macchina (o dopo una reinstallazione),
  ripristina la chiave nel keyring a partire dal file `.key` e dalla relativa
  passphrase. Se sulla macchina esiste già una chiave, l'app chiede conferma prima
  di sovrascriverla (operazione che renderebbe non ripristinabili i backup cifrati
  con la chiave precedente).

Procedura tipica di disaster recovery: installa Foliarium sulla nuova macchina →
**Importa chiave...** con il file e la passphrase salvati → ripristina il backup `.enc`.

!!! note "Cancellazione sicura"
    La rimozione del file in chiaro dopo la cifratura è *best-effort*: su unità
    SSD/flash la sovrascrittura non è garantita. Per una protezione completa si
    raccomanda comunque la cifratura dell'intero disco (BitLocker).

---

## Cartella backup predefinita

Il backup viene salvato nella cartella configurata nelle impostazioni. Il percorso predefinito è:

```
C:\Users\[utente]\Documents\Foliarium Backup\
```

Modificabile da *Impostazioni → Cartella Backup*.

---

## Backup automatico pianificato

1. Andare in **Backup** → fare clic su **Pianifica Backup**
2. Configurare:
   - **Frequenza:** Giornaliera / Settimanale / Mensile
   - **Orario:** ora di esecuzione (es. 23:00)
   - **Cartella destinazione:** percorso locale o di rete
   - **Numero di backup da conservare:** es. 7 (i più vecchi vengono eliminati automaticamente)
3. Fare clic su **Salva Pianificazione**

> 📸 **Screenshot:** Finestra pianificazione backup con selezione frequenza e orario.

!!! info "Backup su rete"
    Per backup su unità di rete (NAS, server), inserire il percorso UNC (es. `\\server\backup\foliarium\`). Assicurarsi che l'utente di Windows abbia i permessi di scrittura sulla cartella.

---

## Log dei backup

La schermata Backup mostra un log degli ultimi backup eseguiti con:

- Data e ora
- Dimensione del file
- Percorso del file
- Esito (Successo / Errore)

> 📸 **Screenshot:** Tabella log backup con colonne Data, Percorso, Dimensione, Esito.

---

## Verifica dell'integrità

Fare clic su **Verifica Backup** per controllare che il file di backup selezionato sia leggibile e non corrotto. L'operazione non modifica il database.

---

## Ripristino

!!! danger "Operazione irreversibile"
    Il ripristino sovrascrive TUTTI i dati presenti nel database con quelli del backup. Questa operazione non può essere annullata. Eseguire un backup del database corrente prima di procedere.

### Procedura di ripristino

1. Andare in **Backup** → fare clic su **Ripristina da Backup**
2. Selezionare il file `.backup` da ripristinare
3. Leggere attentamente l'avviso e fare clic su **Confermo, procedi**
4. Attendere il completamento del ripristino
5. Riavviare Foliarium

> 📸 **Screenshot:** Dialog di conferma ripristino con avviso in rosso e campo di conferma testuale.

---

## Backup di emergenza tramite pgAdmin

In caso di malfunzionamento di Foliarium, è possibile eseguire il backup direttamente tramite pgAdmin:

1. Aprire pgAdmin e connettersi al server
2. Espandere *Databases → catasto_storico*
3. Clic destro → **Backup...**
4. Scegliere formato **Custom** e selezionare la cartella di destinazione
5. Fare clic su **Backup**

---

## Promemoria backup

Si consiglia di pianificare:

| Frequenza | Tipo |
|---|---|
| **Giornaliero** | Backup incrementale automatico (ore 23:00) |
| **Settimanale** | Backup completo su supporto esterno (venerdì) |
| **Mensile** | Copia su supporto rimovibile conservato offline |
