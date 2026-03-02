# Esportazioni

Il modulo **Esportazioni** di Meridiana permette di estrarre i dati dal database catastale in vari formati per consultazione offline, stampa istituzionale o rielaborazione in altri software.

> 📸 **Screenshot:** Sezione Esportazioni con menu a tendina tipo esportazione, filtro comune e pulsanti formato.

---

## Dati esportabili

| Categoria | Contenuto |
|---|---|
| **Elenco Possessori** | Tutti i possessori con paternità e numero partite associate |
| **Elenco Partite** | Riepilogo partite (attive e non) con totali possessori e immobili |
| **Elenco Immobili** | Fabbricati e terreni con natura, classificazione e località |
| **Elenco Località** | Vie, borgate e piazze configurate nel sistema |
| **Elenco Variazioni** | Storico passaggi di proprietà e volture catastali |
| **Report Consistenza Patrimoniale** | Raggruppamento immobili per possessore |

---

## Come eseguire un'esportazione

1. Vai alla sezione **Esportazioni** dalla barra di navigazione
2. Dal menu a tendina **"Tipo di Esportazione"** scegli la categoria
3. Dal menu **"Filtra per Comune"** seleziona il comune (oppure "Tutti i Comuni")
4. Fai clic sul pulsante del formato desiderato

> 📸 **Screenshot:** Procedura di esportazione passo-passo con il menu tipo e il pulsante PDF evidenziati.

---

## Formati supportati

### Esporta in CSV

Formato testo con separatore `;` (punto e virgola), compatibile con Excel e database governativi.

- Codifica: UTF-8
- Separatore colonne: `;`
- Estensione: `.csv`

### Esporta in Excel (.xlsx)

Formato nativo Excel con colonne etichettate. Consigliato per analisi e rielaborazione dei dati.

- Compatibile con Microsoft Excel 2007+, LibreOffice Calc, Google Sheets
- Estensione: `.xlsx`

### Esporta in PDF

Documento impaginato pronto per la stampa istituzionale.

- Intestazione automatica su ogni pagina
- Piè di pagina con numero di pagina e dicitura dell'Archivio di Stato
- Dati incolonnati in tabelle ad alta leggibilità
- Estensione: `.pdf`

### Esporta in ODT

Documento di testo in formato OpenDocument, modificabile con LibreOffice Writer.

- Compatibile con LibreOffice, Apache OpenOffice, Microsoft Word
- Conserva la struttura tabellare dei dati
- Estensione: `.odt`

---

## Archivio Completo (.xlsx) — Novità v1.4

Il pulsante **"Archivio Completo (.xlsx)"** genera un unico file Excel con **4 fogli** contenenti l'intero archivio catastale:

| Foglio | Contenuto |
|---|---|
| **Partite** | Tutte le partite catastali |
| **Possessori** | Tutti i possessori registrati |
| **Immobili** | Tutti i fabbricati e terreni |
| **Variazioni** | Tutto lo storico delle variazioni |

> 📸 **Screenshot:** File Excel aperto con 4 tab in basso: Partite, Possessori, Immobili, Variazioni.

!!! warning "Tempo di elaborazione"
    L'esportazione dell'archivio completo può richiedere alcuni minuti su database di grandi dimensioni. Non chiudere Meridiana durante l'operazione.

---

## Cartella di salvataggio

Per impostazione predefinita, Meridiana suggerisce di salvare i file nella cartella:

```
Documenti\Esportazioni Meridiana\
```

È comunque possibile scegliere una cartella diversa tramite la finestra di salvataggio standard di Windows.

---

## Log delle operazioni

Nella parte inferiore della schermata è presente un pannello **Log**. Dopo ogni esportazione compare un messaggio con:

- Tipo di esportazione eseguita
- Nome del file generato (cliccabile per aprirlo direttamente)
- Data e ora dell'operazione

> 📸 **Screenshot:** Pannello log con messaggio di successo e link cliccabile al file esportato.

!!! warning "File già aperto"
    Se il file di destinazione è già aperto in Excel o in un altro programma, l'esportazione fallirà con un errore di permessi. Chiudere il file prima di avviare una nuova esportazione.
