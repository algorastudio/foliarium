# 📥 Esportazione Dati

Il modulo **Esportazioni** di Meridiana 1.3 permette di estrarre massivamente i dati dal database catastale per poterli consultare offline, stamparli o rielaborarli in altri software (come Microsoft Excel).

---

## 1. Tipi di Dati Esportabili
Attraverso l'interfaccia principale è possibile selezionare diverse categorie di dati da esportare:

* **Elenco Possessori:** Estrae tutti i possessori registrati, includendo la paternità e il numero di partite a loro associate.
* **Elenco Partite:** Un riepilogo di tutte le partite catastali (attive e inattive) con i totali dei possessori e degli immobili associati.
* **Elenco Immobili:** Dettaglio di fabbricati e terreni, completi di natura, classificazione e località.
* **Elenco Località:** La lista delle vie, borgate e piazze configurate nel sistema.
* **Elenco Variazioni:** Lo storico dei passaggi di proprietà e delle mutazioni catastali (volture).
* **Report Consistenza Patrimoniale:** Un report avanzato che raggruppa tutti gli immobili posseduti, divisi per singolo possessore.

---

## 2. Come effettuare un'esportazione

La procedura per esportare i dati è semplice e guidata:

1. Vai alla sezione **Esportazioni** dal menu principale.
2. Dal menu a tendina **"Tipo di Esportazione"**, scegli la categoria di dati che ti interessa.
3. Dal menu **"Filtra per Comune"**, seleziona il Comune di riferimento (oppure lascia "Tutti i Comuni" se l'opzione è disponibile).
4. Clicca sul pulsante corrispondente al formato desiderato (**CSV**, **XLS** o **PDF**).

!!! success "Cartella di Salvataggio Automatica"
    Per tenere in ordine il tuo lavoro, Meridiana ti proporrà automaticamente di salvare i file nella cartella **`Documenti > Esportazioni Meridiana`** del tuo computer. Potrai comunque scegliere una cartella diversa cliccando su "Sfoglia" nella finestra di salvataggio di Windows.

---

## 3. Formati Supportati

Meridiana 1.3 supporta tre formati di esportazione professionali:

### 📊 Esporta in Excel (.xlsx)
È il formato consigliato se hai bisogno di filtrare, ordinare o modificare i dati estratti. Il file viene generato in formato nativo Excel e organizza i dati in colonne con intestazioni chiare (es. ID, Nome, Natura Immobile).

### 📄 Esporta in PDF
Genera un documento impaginato e pronto per la stampa istituzionale. Il PDF include:
- Intestazione automatica su ogni pagina.
- Piè di pagina con numero di pagina e dicitura legale dell'Archivio di Stato.
- Dati incolonnati in tabelle ad alta leggibilità.

### 📝 Esporta in CSV
Formato di testo grezzo, utile se i dati devono essere importati in altri database governativi o software legacy. Il file utilizza il punto e virgola (`;`) come separatore di colonna.

---

## 4. Log delle Operazioni
Nella parte inferiore della schermata è presente una finestra di **Log**.
Ogni volta che completi un'esportazione, apparirà un messaggio verde con il link al file appena creato. **Cliccando sul link blu nel log**, il file PDF o Excel si aprirà automaticamente sul tuo schermo!

!!! warning "Attenzione ai file aperti"
    Se tenti di esportare un file (ad esempio `report_immobili.xlsx`) mentre lo stesso file è **già aperto** in Excel sul tuo computer, Meridiana ti avviserà con un errore di permessi. Assicurati di chiudere il documento prima di sovrascriverlo con una nuova esportazione.