# Reportistica

La sezione **Reportistica** di Foliarium consente di generare report genealogici, visualizzare l'albero delle successioni proprietarie, confrontare versioni diverse di una partita ed esportare i risultati in formato ODT.

> 📸 **Screenshot:** Sezione Reportistica con tab Genealogico, Confronto, Report Testo.

---

## Report Genealogico (testo)

### Accesso

Andare in **Reportistica** → tab **Genealogico** → pulsante **Genera Report Genealogico**.

### Contenuto del report

Il report genealogico testuale include:

- Dati della partita di riferimento (numero, comune, data impianto)
- Lista dei possessori originali
- Catena delle variazioni (volture) in ordine cronologico
- Partite di provenienza e di destinazione per ogni variazione
- Sintesi del percorso proprietario

> 📸 **Screenshot:** Report genealogico testuale nella finestra di visualizzazione con pulsante "Esporta ODT".

---

## Albero Genealogico

### Accesso

Dalla tab **Genealogico** fare clic su **Visualizza Albero Genealogico**, oppure dal **Dettaglio Partita** fare clic su **Albero Genealogico**.

> 📸 **Screenshot:** Finestra Albero Genealogico con struttura ad albero e pannello dettaglio a destra.

### Struttura visuale

L'albero mostra la partita centrale e le sue relazioni:

| Elemento | Colore | Descrizione |
|---|---|---|
| Partita corrente | Grigio/neutro | La partita di riferimento |
| Predecessori | Blu chiaro | Partite da cui deriva (provenienza) |
| Successori | Verde chiaro | Partite generate da questa (destinazione) |

### Colonne dell'albero

- Numero partita · Comune · Possessori · Data impianto · Tipo variazione

### Pannello dettaglio

Selezionando un nodo dell'albero, il pannello laterale mostra i dati completi di quella partita.

### Pulsante "Apri Report Testo"

Genera il report genealogico testuale della partita selezionata nell'albero.

---

## Confronto Partite (diff)

### Accesso

Dalla tab **Confronto** in Reportistica, selezionare due partite e fare clic su **Confronta**.

> 📸 **Screenshot:** Finestra Confronto Partite con differenze evidenziate in verde (aggiunto) e rosso (rimosso).

### Cosa viene confrontato

Il confronto evidenzia le differenze tra due versioni o partite correlate su:

| Sezione | Descrizione |
|---|---|
| **Possessori** | Possessori presenti in una partita ma non nell'altra |
| **Immobili** | Fabbricati/terreni aggiunti o rimossi |

### Codifica colori

| Colore | Significato |
|---|---|
| Verde (`#C8E6C9`) | Elemento presente solo nella partita B (aggiunto) |
| Rosso (`#FFCDD2`) | Elemento presente solo nella partita A (rimosso) |
| Bianco | Elemento comune a entrambe le partite |

---

## Esportazione report in ODT

### Accesso

Fare clic su **Esporta come ODT** nel pannello del report genealogico testuale.

### Utilizzo

1. Generare prima il report con **Genera Report Genealogico**
2. Fare clic su **Esporta come ODT**
3. Scegliere la cartella di destinazione
4. Il file `.odt` viene aperto automaticamente se LibreOffice è installato

> 📸 **Screenshot:** Finestra di salvataggio file ODT con cartella "Esportazioni Foliarium" preselezionata.

!!! info "Formato ODT"
    Il formato ODT (OpenDocument Text) è compatibile con LibreOffice Writer, Apache OpenOffice e Microsoft Word. È il formato consigliato per la conservazione istituzionale.
