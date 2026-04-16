# Ricerca Avanzata

Foliarium offre due modalità di ricerca avanzata: la **ricerca fuzzy unificata** per trovare possessori e partite con nomi approssimativi, e la **ricerca full-text documenti** per esplorare il contenuto dell'archivio documentale.

---

## Ricerca Fuzzy Unificata

### Cos'è la ricerca fuzzy

La ricerca fuzzy permette di trovare risultati anche quando il termine cercato contiene errori di battitura, varianti ortografiche o trascrizioni approssimative — frequenti nei documenti storici del catasto.

**Esempio:** cercando "Rossi Giovani" si trovano anche "Rossi Giovanni" e "Rosso Giovanni".

### Accesso

Selezionare **Ricerca Avanzata** → tab **Ricerca Fuzzy** dalla barra di navigazione principale.

> 📸 **Screenshot:** Pannello ricerca fuzzy con campo di testo, slider soglia e tab risultati Possessori/Partite.

### Parametri

| Parametro | Descrizione |
|---|---|
| **Termine di ricerca** | Testo da cercare (nome, cognome, numero partita) |
| **Soglia similarità** | Percentuale minima di corrispondenza (default: 70%) |
| **Cerca in** | Possessori / Partite / Entrambi |

### Soglia di similarità

Lo slider della soglia controlla quanto devono essere simili i risultati:

- **90–100%:** solo corrispondenze quasi esatte
- **70–89%:** permette piccole variazioni (consigliato)
- **50–69%:** ricerca molto permissiva, possibili falsi positivi

### Risultati

I risultati vengono mostrati in due tab distinte:

- **Possessori trovati:** Nome, Paternità, Comune, Punteggio similarità
- **Partite trovate:** Numero, Comune, Possessori, Punteggio similarità

> 📸 **Screenshot:** Risultati ricerca fuzzy con colonna "Similarità %" evidenziata.

Fare doppio clic su un risultato per aprire il dettaglio completo.

---

## Ricerca Avanzata Immobili

### Accesso

Selezionare **Ricerca Avanzata** → tab **Immobili**.

### Filtri combinabili

| Filtro | Tipo | Descrizione |
|---|---|---|
| Comune | Menu | Filtra per comune |
| Natura | Menu | Fabbricato / Terreno / Tutti |
| Classificazione | Testo | Ricerca parziale nella classificazione |
| Località | Testo | Via o borgata di ubicazione |
| Reddito dominicale (da/a) | Numerico | Intervallo di valori |
| Anno impianto partita (da/a) | Data | Filtro sulle partite collegate |

> 📸 **Screenshot:** Ricerca avanzata immobili con più filtri attivi contemporaneamente.

!!! info "Filtri combinati"
    Tutti i filtri si combinano con la logica AND: vengono mostrati solo gli immobili che soddisfano **tutti** i criteri selezionati.

---

## Ricerca Full-text Documenti

### Accesso

Selezionare **Consultazione** → tab **Documenti**.

### Utilizzo

1. Inserire le parole chiave nel campo **Cerca nel titolo**
2. Opzionalmente filtrare per **Tipo documento**, **Anno (da/a)** e **ID Partita**
3. Premere **Cerca** o Invio

> 📸 **Screenshot:** Pannello ricerca documenti con risultati che evidenziano il termine cercato nel titolo.

### Risultati

La tabella mostra: Titolo · Tipo · Anno · Partita collegata · Note.

Fare doppio clic su un documento per visualizzare i dettagli completi e la partita associata.
