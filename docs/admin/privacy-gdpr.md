# Privacy e GDPR

Foliarium gestisce dati personali di possessori e utenti dell'applicazione.
Questa pagina descrive le funzioni a supporto degli adempimenti privacy
(Reg. UE 2016/679 — GDPR e D.Lgs. 196/2003).

!!! note "Archivio storico"
    Molti possessori presenti in un archivio catastale storico sono persone
    decedute: per loro il GDPR non si applica. Le funzioni seguenti riguardano
    soprattutto i possessori viventi e gli utenti dell'applicazione.

## Diritto di accesso e portabilità

I dati di un possessore possono essere esportati in formato strutturato (JSON)
dalla scheda del possessore (**Esporta**). L'export include l'anagrafica e le
partite/immobili collegati e può essere consegnato all'interessato che ne faccia
richiesta.

## Anonimizzazione (diritto di cancellazione)

Dalla finestra **Modifica Dati Possessore** è disponibile il pulsante
**Anonimizza (GDPR)**.

L'anonimizzazione sostituisce in modo **irreversibile** i dati personali
(nome, cognome, paternità) con un segnaposto, **mantenendo** il record e i suoi
collegamenti con le partite. Questo preserva l'integrità storica e referenziale
dell'archivio: la struttura delle proprietà resta consultabile, ma il dato
anagrafico non è più presente né recuperabile.

L'operazione richiede una doppia conferma (avviso + digitazione di `ANONIMIZZA`)
e viene registrata nel log applicativo con l'operatore che l'ha eseguita.

!!! warning "Base giuridica della conservazione"
    Prima di anonimizzare, valutare se sussiste una **base giuridica per
    conservare il dato** (es. obbligo di legge, interesse pubblico
    dell'archivio storico): in tal caso il diritto alla cancellazione può non
    applicarsi (art. 17, par. 3, GDPR). La decisione spetta al titolare del
    trattamento.

!!! danger "Irreversibilità"
    Dopo l'anonimizzazione i dati anagrafici originali **non sono recuperabili**.
    Se necessario per finalità di prova, esportare prima i dati del possessore.

## Retention dei log di audit

I log di audit registrano gli accessi e le modifiche ai dati. La loro
conservazione va limitata al tempo necessario: vedere la procedura di pulizia
periodica dei log nella sezione amministrativa.
