# Security Policy

## Versioni supportate

| Versione | Supportata          |
|----------|---------------------|
| 1.0.x    | :white_check_mark:  |

## Segnalazione di vulnerabilità

**Non aprire issue pubbliche per segnalare vulnerabilità di sicurezza.**

Se hai individuato una vulnerabilità in Foliarium, ti chiediamo di segnalarla
in modo responsabile (Responsible Disclosure) contattando direttamente il
team di sviluppo:

**Email:** santoromarco@gmail.com
**Oggetto:** `[SECURITY] Foliarium — <breve descrizione>`

### Cosa includere nella segnalazione

- Descrizione della vulnerabilità e del suo potenziale impatto
- Passaggi per riprodurre il problema (proof of concept, se disponibile)
- Versione di Foliarium e sistema operativo in uso
- Eventuali patch o suggerimenti per la risoluzione

### Tempi di risposta

- Conferma di ricezione entro **48 ore**
- Valutazione preliminare entro **5 giorni lavorativi**
- Aggiornamento sullo stato di risoluzione entro **30 giorni**

### Processo di divulgazione

1. La segnalazione viene ricevuta e confermata
2. Il team verifica la vulnerabilità e determina la gravità
3. Viene sviluppata e testata una correzione
4. La correzione viene rilasciata in una nuova versione
5. La vulnerabilità viene resa pubblica dopo il rilascio della patch, con credito al ricercatore (se desiderato)

## Note di sicurezza per l'installazione

- Il file `config.ini` (contenente le credenziali del database) è escluso dal
  repository tramite `.gitignore` e non deve mai essere committato o condiviso.
- Le password degli utenti applicativi sono memorizzate con hash **bcrypt**.
- Le credenziali di connessione al database sono gestite tramite il **keyring**
  del sistema operativo.
- L'audit log registra automaticamente tutte le operazioni con utente,
  timestamp e indirizzo IP.
- Si raccomanda di limitare l'accesso alla porta PostgreSQL (5432) tramite
  firewall e di utilizzare connessioni cifrate (SSL) in ambienti di produzione.

## Responsabile della sicurezza

**ALGORASTUDIO** — Marco Santoro
Email: santoromarco@gmail.com
