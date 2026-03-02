# Gestione Utenti

La sezione **Gestione Utenti** è accessibile solo agli utenti con ruolo Amministratore e permette di creare, modificare e disattivare gli account utente di Meridiana.

> 📸 **Screenshot:** Sezione Gestione Utenti con lista utenti, pulsanti Crea/Modifica/Disattiva.

---

## Ruoli utente

Meridiana implementa tre livelli di accesso:

| Ruolo | Accesso |
|---|---|
| **Guest** | Solo lettura: Consultazione e Reportistica. Non può inserire o modificare dati. |
| **Utente** | Accesso completo alle funzioni operative: Consultazione, Inserimento, Esportazioni, Reportistica, Statistiche. |
| **Amministratore** | Accesso a tutte le sezioni incluse: Gestione Utenti, Backup, Audit Log, Impostazioni sistema. |

---

## Creazione di un nuovo utente

1. Andare in **Gestione Utenti** → fare clic su **Nuovo Utente**
2. Compilare i campi:
   - **Nome utente** (username): stringa alfanumerica, case-insensitive
   - **Nome completo**: nome visualizzato nell'interfaccia
   - **Ruolo**: Guest / Utente / Amministratore
   - **Password**: minimo 8 caratteri
3. Fare clic su **Salva**

> 📸 **Screenshot:** Dialog di creazione nuovo utente con campi username, nome completo, ruolo, password.

!!! info "Password sicura"
    Le password vengono memorizzate con hashing bcrypt. Non è possibile recuperare una password dimenticata: è necessario reimpostarla dall'account amministratore.

---

## Modifica utente

1. Selezionare l'utente nella lista
2. Fare clic su **Modifica**
3. Modificare i campi desiderati (nome, ruolo, password)
4. Fare clic su **Salva**

---

## Reimpostazione password

1. Selezionare l'utente
2. Fare clic su **Reimposta Password**
3. Inserire la nuova password e confermarla
4. Comunicare la nuova password all'utente

!!! warning "L'utente deve cambiare la password"
    Si consiglia di informare l'utente di cambiare la password al prossimo accesso tramite *Impostazioni → Cambia Password*.

---

## Disattivazione utente

!!! danger "Operazione irreversibile con effetti immediati"
    Disattivare un utente termina immediatamente qualsiasi sessione attiva.

1. Selezionare l'utente
2. Fare clic su **Disattiva**
3. Confermare l'operazione

L'utente disattivato non potrà più effettuare il login. I dati inseriti dall'utente non vengono eliminati.

---

## Audit Log

La sezione **Audit Log** registra automaticamente tutte le operazioni significative eseguite dagli utenti:

| Evento registrato | Dettagli |
|---|---|
| Login / Logout | Utente, data, ora, indirizzo IP |
| Inserimento record | Tipo entità, ID, utente |
| Modifica record | Tipo entità, ID, campi modificati, utente |
| Eliminazione | Tipo entità, ID, utente |
| Export dati | Tipo esportazione, comune, utente |
| Import massivo | Tipo import, n° record, utente |

> 📸 **Screenshot:** Audit Log con tabella eventi, filtri per data/utente/tipo operazione.

### Filtri Audit Log

| Filtro | Descrizione |
|---|---|
| Utente | Filtra le operazioni di un utente specifico |
| Tipo operazione | Login, Inserimento, Modifica, Eliminazione, Export |
| Data (da/a) | Intervallo di date |

### Esportazione Audit Log

Il log può essere esportato in CSV per archiviazione o invio all'ufficio competente: fare clic su **Esporta Log CSV**.
