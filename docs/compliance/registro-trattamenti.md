# Registro delle attività di trattamento (RoPA)

> **BOZZA / TEMPLATE** — Registro ai sensi dell'art. 30 GDPR. Completare i campi
> tra `[…]`. Ogni attività di trattamento è descritta in una scheda.

## Dati del Titolare

- **Titolare**: [Denominazione], [indirizzo], [email/PEC]
- **DPO**: [nominativo / contatto, se nominato]
- **Data ultimo aggiornamento**: [data]

---

## Trattamento 1 — Gestione dell'archivio catastale storico

| Campo | Contenuto |
|---|---|
| **Finalità** | Conservazione, consultazione e aggiornamento delle partite catastali e dei dati dei possessori |
| **Categorie di interessati** | Possessori/proprietari storici (in prevalenza deceduti) ed eventuali possessori viventi |
| **Categorie di dati** | Nome, cognome, paternità; riferimenti a partite e immobili |
| **Base giuridica** | Art. 6.1.e (interesse pubblico) / 6.1.c (obbligo legale) |
| **Destinatari** | Personale autorizzato; [responsabili esterni] |
| **Trasferimenti extra-UE** | [Nessuno / specificare] |
| **Termine di conservazione** | Archiviazione nel pubblico interesse — [illimitato / specificare] |
| **Misure di sicurezza** | Cfr. [Misure di sicurezza](misure-sicurezza.md) |

## Trattamento 2 — Gestione degli utenti dell'applicazione

| Campo | Contenuto |
|---|---|
| **Finalità** | Autenticazione, autorizzazione e gestione dei permessi degli operatori |
| **Categorie di interessati** | Archivisti, amministratori, operatori |
| **Categorie di dati** | Username, nome completo, e-mail, ruolo, password (hash bcrypt) |
| **Base giuridica** | Art. 6.1.b (contratto) / 6.1.f (legittimo interesse) |
| **Destinatari** | Amministratori di sistema; [responsabili esterni] |
| **Trasferimenti extra-UE** | [Nessuno] |
| **Termine di conservazione** | Durata del rapporto + [periodo] |
| **Misure di sicurezza** | Hash bcrypt (cost 12), policy password, lockout anti brute-force |

## Trattamento 3 — Log di accesso e audit

| Campo | Contenuto |
|---|---|
| **Finalità** | Sicurezza, tracciabilità delle operazioni, accountability |
| **Categorie di interessati** | Utenti dell'applicazione |
| **Categorie di dati** | Identificativo utente, data/ora, operazione, tabella e record interessati |
| **Base giuridica** | Art. 6.1.c / 6.1.f |
| **Destinatari** | Amministratori |
| **Termine di conservazione** | [N giorni/mesi] — policy di retention configurabile |
| **Misure di sicurezza** | Accesso riservato agli amministratori; pulizia automatica oltre la soglia |

## Trattamento 4 — Backup del database

| Campo | Contenuto |
|---|---|
| **Finalità** | Continuità operativa e disaster recovery |
| **Categorie di interessati** | Tutti gli interessati dei trattamenti 1-3 |
| **Categorie di dati** | Copia integrale dei dati dell'archivio |
| **Base giuridica** | Art. 6.1.c / 6.1.f |
| **Termine di conservazione** | [Rotazione — es. ultimi N backup / N mesi] |
| **Misure di sicurezza** | Cifratura AES-256-GCM; chiave nel keyring di sistema |

---

*Aggiungere ulteriori schede per ogni nuovo trattamento (es. notifiche e-mail,
integrazioni API esterne).*
