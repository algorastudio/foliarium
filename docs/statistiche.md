# Statistiche e Grafici

La sezione **Statistiche** di Foliarium offre una visualizzazione grafica del patrimonio catastale attraverso grafici interattivi generati con matplotlib.

> 📸 **Screenshot:** Sezione Statistiche con tre grafici affiancati: barre per comune, torta stato, barre variazioni per anno.

---

## Accesso alla sezione

Fare clic sulla tab **Statistiche** nella barra di navigazione principale, quindi selezionare il sub-tab **Grafici**.

---

## Grafici disponibili

### 1. Partite per Comune (grafico a barre)

Mostra il numero di partite catastali per ciascun comune presente nel database.

> 📸 **Screenshot:** Grafico a barre verticali "Partite per Comune" con i comuni sull'asse X e il conteggio sull'asse Y.

**Utilizzo:** Confrontare la distribuzione del patrimonio catastale tra i diversi comuni dell'archivio.

---

### 2. Partite Attive / Non Attive (grafico a torta)

Mostra la proporzione tra partite ancora attive e partite chiuse/non attive.

> 📸 **Screenshot:** Grafico a torta con due settori: "Attive" (colore verde) e "Non attive" (colore grigio), con percentuali.

**Utilizzo:** Valutare la completezza del patrimonio catastale e identificare l'arco storico coperto.

---

### 3. Variazioni per Anno (grafico a barre)

Mostra il numero di variazioni (volture e passaggi di proprietà) registrate per ciascun anno.

> 📸 **Screenshot:** Grafico a barre orizzontali o verticali "Variazioni per Anno" con anni sull'asse e conteggio sul lato.

**Utilizzo:** Identificare i periodi storici con maggiore attività di trasferimento proprietario.

---

## Aggiornamento dei grafici

Fare clic su **Aggiorna Grafici** (o **Ricarica**) per rinfrescare i dati dal database. I grafici non si aggiornano automaticamente ma solo su richiesta esplicita dell'utente.

> 📸 **Screenshot:** Pulsante "Aggiorna Grafici" nella barra degli strumenti della sezione Statistiche.

---

## Interazione con i grafici

I grafici matplotlib supportano le interazioni standard:

| Azione | Effetto |
|---|---|
| **Zoom in/out** | Rotella del mouse sul grafico |
| **Panoramica** | Trascinamento con il tasto sinistro |
| **Ripristina vista** | Pulsante "Home" nella toolbar del grafico |
| **Salva immagine** | Pulsante "Salva" nella toolbar (PNG, PDF, SVG) |

> 📸 **Screenshot:** Toolbar matplotlib sotto il grafico con pulsanti Home, Pan, Zoom, Save.

---

## Statistiche testuali (Dashboard)

Nella tab **Dashboard** della sezione Statistiche sono disponibili anche i totali numerici:

| Metrica | Descrizione |
|---|---|
| Totale partite | Numero complessivo di partite nel database |
| Partite attive | Partite in stato "Attiva" |
| Totale possessori | Numero di possessori registrati |
| Totale immobili | Fabbricati + Terreni |
| Totale variazioni | Passaggi di proprietà registrati |
| Comuni presenti | Numero di comuni nell'archivio |

> 📸 **Screenshot:** Dashboard con riquadri numerici per le principali metriche catastali.
