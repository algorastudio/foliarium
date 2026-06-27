# Misure tecniche e organizzative di sicurezza

> **BOZZA / TEMPLATE** — Descrizione delle misure ai sensi dell'art. 32 GDPR.
> Le misure **tecniche** elencate riflettono funzionalità implementate in
> Foliarium; le misure **organizzative** tra `[…]` vanno definite dal Titolare.

## Misure tecniche (implementate nel software)

### Controllo degli accessi e autenticazione
- Password degli utenti memorizzate come **hash bcrypt** (cost 12), mai in
  chiaro; verifica a tempo costante.
- **Policy password**: minimo 10 caratteri con lettere maiuscole, minuscole e
  cifre; rifiuto delle password comuni.
- **Protezione anti brute-force**: blocco temporaneo dell'account dopo ripetuti
  tentativi falliti; hash dummy per prevenire l'enumerazione degli utenti.
- **Ruoli e permessi** differenziati (amministratore / utente / visualizzatore).

### Sicurezza dell'interfaccia di integrazione (API)
- API esposta solo su **localhost** (`127.0.0.1`).
- Doppia autenticazione (sessione utente / chiave API).
- **Scope granulari** applicati a ogni endpoint (lettura/scrittura per risorsa).
- **Rate limiting** per chiave API.
- Chiavi API memorizzate come **hash SHA-256** (mai in chiaro), con scadenza e
  revoca.

### Protezione dei dati in transito e a riposo
- **TLS** verso il database PostgreSQL: obbligatorio (`sslmode=require`) per gli
  host remoti, così le credenziali e i dati non transitano in chiaro su rete.
- **Backup cifrati** con AES-256-GCM; chiave a 256 bit custodita nel **keyring
  di sistema** ed esportabile in modo protetto da passphrase per il disaster
  recovery.

### Tracciabilità e minimizzazione
- **Registro di audit** delle operazioni (chi, quando, cosa) accessibile ai soli
  amministratori.
- **Retention configurabile** dei log di audit (pulizia automatica oltre la
  soglia impostata).
- **Anonimizzazione** in-place dei dati di un possessore su richiesta, ove non
  sussista una base giuridica di conservazione.

### Robustezza applicativa
- Query parametrizzate verso il database (prevenzione SQL injection).
- Assenza di deserializzazione insicura; comandi di sistema eseguiti senza shell.

## Misure organizzative (a cura del Titolare)

- [ ] Nomina degli **autorizzati** al trattamento e istruzioni scritte.
- [ ] Nomina dei **responsabili del trattamento** (art. 28) per fornitori
  esterni (assistenza, hosting), con accordo scritto.
- [ ] Politica di **gestione delle credenziali** (forza, rotazione, revoca al
  cessare del rapporto).
- [ ] **Cifratura dell'intero disco** (es. BitLocker) sulle macchine che
  ospitano dati o backup.
- [ ] Procedura di **backup e disaster recovery** documentata, con conservazione
  sicura e separata della chiave di cifratura dei backup.
- [ ] Politica di **retention** dei dati e dei log definita e applicata.
- [ ] **Formazione** del personale sulla protezione dei dati.
- [ ] Procedura di gestione del **data breach** (notifica entro 72 ore, art. 33).
- [ ] **Code-signing** (firma Authenticode) degli eseguibili distribuiti.

## Riesame

Le misure sono riesaminate periodicamente e a ogni modifica significativa.
Data: [data]. Versione: [x.y].
