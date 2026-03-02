# Guida Amministratore

Questa sezione è rivolta agli **amministratori di sistema** responsabili dell'installazione, configurazione e manutenzione di Meridiana.

!!! danger "Accesso riservato"
    Le funzioni descritte in questa sezione richiedono il ruolo **Amministratore** e conoscenze tecniche di PostgreSQL e Windows Server. Un uso scorretto può causare perdita di dati.

---

## Contenuto della sezione

| Pagina | Descrizione |
|---|---|
| [Installazione e Configurazione](installazione.md) | Prerequisiti, procedura di installazione, configurazione del database |
| [Gestione Utenti](gestione-utenti.md) | Creazione e modifica utenti, ruoli, audit log |
| [Backup e Ripristino](backup.md) | Backup manuale e automatico, procedura di ripristino |
| [Import Massivo](import-massivo.md) | Import da CSV, ISTAT, OpenStreetMap, Excel |

---

## Accesso alle funzioni amministrative

Le funzioni amministrative sono accessibili dalla barra di navigazione solo per gli utenti con ruolo **Amministratore**:

- **Gestione Utenti** — visibile solo agli amministratori
- **Backup** — visibile solo agli amministratori
- **Audit Log** — visibile solo agli amministratori
- **Impostazioni sistema** — configurazioni avanzate

> 📸 **Screenshot:** Barra di navigazione con le tab riservate all'amministratore evidenziate.

---

## Primo accesso come amministratore

Al primo avvio di Meridiana dopo l'installazione, effettuare il login con le credenziali di default impostate durante la configurazione iniziale, quindi:

1. Andare in **Gestione Utenti** → **Cambia Password** per modificare la password di default
2. Creare gli account per gli archivisti con ruolo appropriato
3. Verificare la connessione al database dalla schermata di stato

!!! warning "Cambiare la password di default"
    Non lasciare la password di default attiva in produzione. Cambiarla immediatamente dopo il primo accesso.
