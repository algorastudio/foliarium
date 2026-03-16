# Changelog

Tutte le modifiche rilevanti a Foliarium sono documentate in questo file.

Il formato segue [Keep a Changelog](https://keepachangelog.com/it/1.1.0/),
e il progetto adotta il [Versionamento Semantico](https://semver.org/lang/it/).

---

## [1.0.0] — 2026-03-16

### Aggiunto
- Dashboard con statistiche aggregate su comuni, partite, possessori e immobili
- Ricerca fuzzy unificata su partite, possessori, immobili, variazioni e contratti (pg_trgm)
- Ricerca avanzata immobili con filtri per natura, classificazione, località e comune
- Gestione completa partite catastali: inserimento, modifica, relazioni principale/secondarie, suffissi, provenienza
- Gestione possessori: anagrafica con paternità, quote, titoli di possesso, comproprietà
- Gestione immobili: natura, consistenza, classificazione, piani, vani, località associate
- Variazioni e contratti: vendite, successioni, frazionamenti, divisioni con notaio e repertorio
- Gestione periodi storici (Regno di Sardegna, Regno d'Italia, Repubblica)
- Gestione tipi località (via, piazza, salita, ecc.)
- Sistema utenti con ruoli e permessi differenziati (operatori, consultatori, amministratori)
- Login/logout con hashing password bcrypt
- Audit log automatico di tutte le operazioni (INSERT, UPDATE, DELETE)
- Registro consultazioni archivio con richiedente e motivazione
- Esportazioni in CSV, PDF e JSON per partite e possessori, report di massa
- Reportistica avanzata con viste aggregate e statistiche per comune e periodo
- Sistema di backup database integrato
- Supporto temi interfaccia tramite fogli di stile QSS personalizzabili
- Importazione dati da file CSV con dialogo di anteprima
- Indici GIN per ricerca fuzzy, viste materializzate, connection pooling PostgreSQL
- Versione portatile per Windows (PostgreSQL embedded, avvio con doppio clic)
- Compatibilità PyInstaller per distribuzione come eseguibile singolo
- `publiccode.yml` per la pubblicazione nel Catalogo del Riuso della PA italiana
- Documentazione in italiano e inglese (installazione, architettura)
- Licenza duale: AGPL-3.0-or-later (open source) + licenza commerciale

[1.0.0]: https://github.com/algorastudio/foliarium/releases/tag/v1.0.0
