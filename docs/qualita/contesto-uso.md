# Contesto d'uso — Foliarium (ISO 9241-11)

!!! danger "Documento incompleto per costruzione — leggere prima di usarlo"
    La ISO 9241-11 definisce l'usabilità come una proprietà della terna
    **prodotto — utenti — contesto**, non del solo prodotto. Il contesto
    d'uso non si deduce: **si rileva**, osservando e intervistando chi
    lavora.

    Quella rilevazione non è mai stata fatta. Questo documento è quindi una
    **base di partenza costruita da due fonti diverse**, e le tiene separate
    in modo visibile:

    - ▣ **Derivato** — ricavato dal codice, dallo schema o dalla
      documentazione. Verificabile da chiunque.
    - ◻ **Ipotesi** — plausibile ma **non rilevata**. Da confermare o
      smentire con gli utenti prima di poterla usare.

    **Nessuna voce ◻ può essere citata in una dichiarazione formale finché
    resta ◻.** Un contesto d'uso ipotizzato dallo sviluppatore è
    esattamente l'errore che la norma vuole evitare: descrive l'utente che
    il progettista immagina, non quello che esiste.

    Il §7 contiene la traccia per la rilevazione che converte le ◻ in ▣.

| | |
|---|---|
| **Prodotto** | Foliarium — Archivio Catastale Storico |
| **Versione** | 1.0.2 |
| **Data** | 12/09/2026 |
| **Riferimento** | ISO 9241-11:2018 — Usabilità: definizioni e concetti |
| **Stato** | Bozza da validare — nessuna rilevazione sul campo effettuata |

---

## 1. Sistema in esame

▣ Applicazione desktop per la gestione del patrimonio documentale catastale
storico: consultazione, ricerca, inserimento e conservazione di partite
catastali, possessori, immobili, località e variazioni di proprietà
(`docs/introduzione.md`).

▣ Il dominio temporale è dichiarato nello schema: tre periodi storici
precaricati — **Regno di Sardegna (1720-1861)**, **Regno d'Italia
(1861-1946)**, **Repubblica Italiana (dal 1946)**
(`sql_scripts/02_creazione-schema-tabelle.sql`). Il prodotto tratta quindi
documentazione che copre circa tre secoli.

---

## 2. Gruppi di utenti

### 2.1 Utenti diretti

I ruoli sono vincolati dallo schema: `CHECK (ruolo IN ('admin',
'archivista', 'consultatore'))` (`sql_scripts/07_user-management.sql`).

| Gruppo | Fonte | Può fare |
|---|---|---|
| **Amministratore** | ▣ | Tutto: in più gestione utenti, backup e ripristino, audit log, tabelle di sistema, operazioni sulle partite, archiviati |
| **Archivista** | ▣ | Consultazione, ricerca, **inserimento** e modifica, esportazioni, report, statistiche, import di massa |
| **Consultatore** | ▣ | Sola consultazione: ricerca, esportazioni, report, statistiche. **Nessun inserimento** |

▣ La ripartizione è applicata in `gui_main.py::update_ui_based_on_role`:
le voci di inserimento sono visibili solo ad amministratore e archivista,
la sezione di amministrazione solo all'amministratore.

!!! warning "Difetto rilevato durante la stesura"
    `core/session_manager.py::Role` definisce il terzo ruolo come
    `VISUALIZZATORE = "visualizzatore"`, ma lo schema e l'interfaccia usano
    `consultatore`. Di conseguenza `Role.permissions_for("consultatore")`
    restituisce un **insieme vuoto** e `Role.is_valid("consultatore")` è
    `False`.

    Oggi è latente — l'interfaccia non passa da `has_permission()` ma
    confronta direttamente le stringhe di ruolo — ma è un difetto reale,
    segnalato a parte. Finché non è risolto, **la tabella qui sopra
    descrive il comportamento dell'interfaccia, non quello della matrice
    dei permessi centralizzata.**

### 2.2 Caratteristiche degli utenti — tutte da rilevare

La norma chiede di caratterizzare ogni gruppo per conoscenze, competenze,
esperienza, formazione e attributi fisici. **Nessuno di questi dati esiste.**

| Caratteristica | Stato | Nota |
|---|---|---|
| Competenza nel dominio catastale | ◻ | Presumibilmente alta negli archivisti, ma il livello non è rilevato |
| Dimestichezza con strumenti informatici | ◻ | Ignota. È la variabile che più cambia le scelte di progetto |
| Formazione ricevuta sul prodotto | ◻ | Non è noto se esista un addestramento all'installazione |
| Frequenza d'uso | ◻ | Uso quotidiano continuativo e uso sporadico portano a esigenze opposte |
| Numero di utenti per installazione | ◻ | Le licenze prevedono `max_seats` (istanze simultanee in rete), ma il valore tipico non è noto |
| Età, vista, uso di tecnologie assistive | ◻ | Non rilevati. Rilevante: nessuno ha verificato l'applicazione con uno screen reader |

### 2.3 Utenti indiretti

▣ Esiste una categoria di persone che **non usa il software ma ne subisce
gli effetti**: i richiedenti esterni. La funzione "Registrazione
Consultazione" raccoglie nome del richiedente, documento d'identità e
motivazione (`foliarium/ui/widgets/reporting/consultazione.py`).

Sono presumibilmente ricercatori, professionisti, eredi o cittadini che
chiedono all'archivio una ricerca. ◻ Il loro profilo, e che cosa ricevono
in concreto, non sono rilevati: è l'archivista a mediare.

▣ Il loro trattamento dati è normato: la documentazione GDPR è in
`docs/compliance/` — **modelli da validare legalmente**, non documenti
adottati.

---

## 3. Obiettivi degli utenti

La norma distingue l'obiettivo (il risultato voluto) dal compito (come lo si
raggiunge). Gli obiettivi si ricavano solo dagli utenti; qui se ne possono
solo *inferire* dalle funzioni esistenti.

| Obiettivo inferito | Da quale funzione | Stato |
|---|---|---|
| Rispondere a una richiesta di consultazione esterna | Ricerca partite/possessori + registrazione consultazione + export PDF | ◻ |
| Ricostruire la storia proprietaria di un bene | Genealogia e timeline della partita | ◻ |
| Riversare in digitale un fondo cartaceo | Inserimento, wizard, import di massa da CSV/Excel | ◻ |
| Verificare la consistenza del patrimonio | Statistiche, reportistica | ◻ |
| Garantire la conservazione del dato | Backup, ripristino, audit log | ◻ |

!!! note "Perché sono tutte ◻"
    Sono inferenze dalle funzioni presenti: dicono che cosa il prodotto
    *permette*, non che cosa gli utenti *vogliono*. La differenza è la
    ragione d'essere di questo documento. Il divario fra le due cose è
    precisamente ciò che un test con utenti reali fa emergere — e che
    oggi, per Foliarium, nessuno conosce.

---

## 4. Compiti

▣ Il flusso critico è codificato e protetto da un test end-to-end:
comune → possessore → partita → variazione → export PDF
(`tests/integration/test_golden_path.py`).

▣ Compiti supportati dall'interfaccia, per gruppo:

| Compito | Amministratore | Archivista | Consultatore |
|---|---|---|---|
| Ricerca (semplice, avanzata, fuzzy) | ✓ | ✓ | ✓ |
| Esportazioni e report | ✓ | ✓ | ✓ |
| Inserimento e modifica | ✓ | ✓ | — |
| Import di massa CSV/Excel, ISTAT, OSM | ✓ | ✓ | — |
| Registrazione consultazione esterna | ✓ | ✓ | — |
| Gestione utenti, backup, audit, archiviati | ✓ | — | — |

**Non rilevati:** ◻ frequenza relativa dei compiti, ◻ durata tipica di una
sessione, ◻ quali compiti generano più errori o richieste di assistenza,
◻ quali vengono svolti in parallelo o interrotti a metà.

!!! info "Un indizio dal codice, non una misura"
    L'esistenza delle bozze (`FormDraftMixin`) e della guardia sulle
    modifiche non salvate presuppone che **l'inserimento venga interrotto
    di frequente**. È un'assunzione ragionevole per il lavoro d'archivio,
    ma resta un'assunzione del progettista: nessuno l'ha verificata.

---

## 5. Risorse

| Risorsa | Stato | Dettaglio |
|---|---|---|
| Fonte dei dati | ◻ | Registri cartacei, scansioni, fogli di calcolo preesistenti? Determina se il collo di bottiglia è la digitazione o la lettura del documento |
| Tempo disponibile per record | ◻ | Non rilevato |
| Documentazione a disposizione | ▣ | 29 pagine pubblicate (nav di `mkdocs.yml`), manuale integrato con ricerca, aiuto contestuale per schermata (F1) |
| Assistenza | ▣ | Esportazione dei log per il supporto in un archivio ZIP (menu Help) |
| Formazione | ◻ | Non è noto se sia prevista |

---

## 6. Ambiente

### 6.1 Ambiente tecnico

▣ Interamente derivato da `docs/introduzione.md` e `docs/installazione.md`:

| Elemento | Valore |
|---|---|
| Sistema operativo (workstation) | Windows 10 64-bit o superiore |
| RAM | 4 GB minimo, 8 GB consigliati |
| Risoluzione schermo | **1280×800 minima** |
| Connessione | Rete locale verso il server PostgreSQL |
| Server | PostgreSQL 14+, Windows Server 2019+ o Linux |

▣ **Architettura client-server su rete locale**, non applicazione isolata:
più postazioni lavorano sullo stesso archivio contemporaneamente. Da qui
discendono tre scelte di progetto documentate altrove: l'annullamento
limitato alle operazioni con inverso esatto, il `sslmode` a `require` per
gli host remoti, e l'audit log con sessione utente propagata al database.

▣ **Degrado previsto:** se il database non risponde l'applicazione entra in
modalità offline con cache locale (`db/base.py`, `offline_mode`), segnalata
da una barra dedicata. Implica che la rete **non è considerata affidabile**.

◻ **Non rilevati:** risoluzione realmente in uso (1280×800 è il minimo
dichiarato, non il tipico), dimensione e numero degli schermi, qualità
effettiva della rete, presenza di uno scanner o di un secondo monitor per
il documento cartaceo.

### 6.2 Ambiente fisico

**Interamente ◻.** Nessun dato su illuminazione, rumore, postazione,
compresenza del documento cartaceo sulla scrivania, interruzioni dovute al
pubblico. Per un lavoro che consiste nel trascrivere un registro cartaceo
guardando uno schermo, queste condizioni non sono dettagli: la serie
**ISO 9241-5xx** se ne occupa specificamente.

### 6.3 Ambiente organizzativo

| Aspetto | Stato | Nota |
|---|---|---|
| Installazioni multi-postazione | ▣ | Le licenze hanno `max_seats` — istanze simultanee consentite in rete |
| Tipologie di licenza | ▣ | `demo`, `standard`, `enterprise` |
| Struttura gerarchica | ◻ | Chi assegna i ruoli, chi valida il lavoro inserito, chi risponde di un errore |
| Vincoli normativi sull'ente | ◻ | Obblighi di conservazione e accesso propri degli archivi di Stato |
| Pressione sui tempi | ◻ | Esiste una scadenza di progetto sulla digitalizzazione? |

---

## 7. Traccia per la rilevazione

Questa è la parte operativa del documento: le domande che convertono le ◻
in ▣. Bastano 3-5 archivisti, in sessioni di circa un'ora, **presso la loro
postazione** — perché metà delle risposte sull'ambiente fisico si ottengono
guardando, non chiedendo.

**Sul lavoro (obiettivi e compiti)**

1. Mi descriva l'ultima giornata di lavoro con Foliarium: che cosa ha fatto, in quale ordine?
2. Qual è la richiesta che riceve più spesso dall'esterno? Quanto le porta via?
3. Che cosa fa più volte al giorno? E che cosa ha fatto una volta sola da quando esiste il programma?
4. Che cosa la fa smettere a metà di un inserimento?
5. C'è qualcosa che continua a fare fuori da Foliarium — su carta, in Excel, a mano? Perché?

**Sulle persone**

6. Da quanto tempo lavora in archivio? E con questo programma?
7. Ha ricevuto una formazione, o ha imparato usandolo?
8. Quante persone usano Foliarium qui? Lavorate sugli stessi fondi?
9. Usa ingrandimento del testo, contrasto elevato o altri ausili?

**Sull'ambiente**

10. *(osservare)* Dov'è il documento cartaceo mentre digita? Quanti schermi ha? Che risoluzione?
11. Quante volte viene interrotto in un'ora?
12. La rete o il database le hanno mai dato problemi? Che cosa ha fatto?

**Sui punti critici**

13. Mi mostri l'ultima volta che il programma ha fatto qualcosa che non si aspettava.
14. C'è una cosa che le fa perdere tempo ogni volta?
15. Se potesse cambiare una cosa sola, quale?

!!! tip "Come usare gli esiti"
    Le risposte a 1-5 riscrivono i §3 e §4; quelle a 6-9 il §2.2; le 10-12
    il §6; le 13-15 alimentano direttamente la revisione dell'interfaccia.
    A quel punto si può misurare l'usabilità come la norma la definisce —
    **efficacia, efficienza e soddisfazione su compiti specificati** — e
    affiancare un punteggio SUS per avere un numero confrontabile fra
    versioni.

---

## 8. Effetto sugli altri documenti di qualità

Finché questo documento resta in bozza:

| Documento | Conseguenza |
|---|---|
| `iso9241-110.md` | I principi **1 (adeguatezza al compito)** e **7 (coinvolgimento)** non possono superare `◐`: entrambi presuppongono un contesto d'uso rilevato |
| `iso25010.md` | La sotto-caratteristica *appropriatezza funzionale* resta `◐`; l'intera caratteristica *usabilità* è dichiarata senza la base che la norma richiede |
| ISO 9241-210 | Non applicabile: la prima delle quattro attività del ciclo è proprio "comprendere e specificare il contesto d'uso" |
| ISO/IEC 25051 | La *descrizione del prodotto* deve dichiarare gli utenti previsti e i limiti d'uso: senza rilevazione, quella dichiarazione non è verificabile |

**Colmare questa lacuna sblocca le altre quattro.** È il motivo per cui, fra
le lacune dichiarate nei documenti di qualità, la rilevazione del contesto
d'uso ha la precedenza su tutte quelle che riguardano l'usabilità.

---

## Manutenzione di questo documento

Va aggiornato **appena esistono dati reali**, sostituendo le voci ◻ con
quanto rilevato e citando la fonte (data della sessione, numero di
partecipanti, ruolo). Fino ad allora, ogni uso esterno deve riportare lo
stato "bozza da validare" presente in testa.

Le voci ◻ non vanno cancellate per far sembrare il documento più completo:
sono l'elenco esatto di ciò che non si sa.
