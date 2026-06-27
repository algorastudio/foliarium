# Valutazione d'impatto sulla protezione dei dati (DPIA)

> **BOZZA / TEMPLATE** — Schema di DPIA ai sensi dell'art. 35 GDPR.
> La DPIA è **obbligatoria** solo quando il trattamento può presentare un
> **rischio elevato** per i diritti e le libertà degli interessati. Verificare
> con il DPO se è dovuta nel caso concreto.

## 1. Valutazione preliminare di necessità

Indicare se ricorrono i criteri che rendono obbligatoria la DPIA (cfr. Linee
guida WP248 e elenco del Garante):

- [ ] Valutazione/scoring sistematico
- [ ] Trattamento su larga scala
- [ ] Monitoraggio sistematico
- [ ] Dati di categorie particolari (art. 9) — *non applicabile a Foliarium*
- [ ] Altro: [specificare]

**Esito preliminare**: la DPIA è ☐ necessaria ☐ non necessaria — motivazione:
[…].

*(Per un archivio catastale storico, con soli dati anagrafici e in prevalenza
relativi a persone decedute, il rischio elevato è spesso da escludere; motivare
comunque la decisione.)*

## 2. Descrizione sistematica del trattamento

- **Natura, ambito, contesto e finalità**: [descrizione]
- **Categorie di dati e interessati**: cfr. [Registro dei trattamenti](registro-trattamenti.md)
- **Flussi e archiviazione**: applicazione desktop + database PostgreSQL;
  backup cifrati; eventuale API locale per integrazioni.

## 3. Necessità e proporzionalità

- Le finalità sono determinate, esplicite e legittime: [sì/no, motivare]
- Minimizzazione dei dati: trattati solo i dati necessari (no codice fiscale,
  no categorie particolari)
- Limitazione della conservazione: retention dei log configurata; dati storici
  conservati per finalità di pubblico interesse

## 4. Identificazione e valutazione dei rischi

| Rischio | Probabilità | Impatto | Misure di mitigazione |
|---|---|---|---|
| Accesso non autorizzato ai dati | [B/M/A] | [B/M/A] | Autenticazione bcrypt, controllo accessi, scope API |
| Esfiltrazione di un backup | [B/M/A] | [B/M/A] | Cifratura AES-256-GCM dei backup |
| Intercettazione su rete (DB remoto) | [B/M/A] | [B/M/A] | TLS obbligatorio (`sslmode=require`) |
| Modifica/cancellazione non tracciata | [B/M/A] | [B/M/A] | Audit log + retention |
| Conservazione eccessiva | [B/M/A] | [B/M/A] | Retention configurabile; anonimizzazione su richiesta |

## 5. Misure per affrontare i rischi

Cfr. [Misure di sicurezza](misure-sicurezza.md). Indicare misure aggiuntive
eventualmente necessarie: [...].

## 6. Esito e consultazione

- **Rischio residuo**: [accettabile / da mitigare ulteriormente]
- **Consultazione del DPO**: [data, parere]
- **Eventuale consultazione preventiva del Garante (art. 36)**: [necessaria?]

---

*Documento da riesaminare periodicamente e a ogni modifica significativa del
trattamento. Data: [data]. Versione: [x.y].*
