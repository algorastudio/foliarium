# Import Massivo

Foliarium supporta l'importazione di grandi quantità di dati da fonti esterne. Tutte le funzioni di import massivo sono accessibili dal menu **File** nella barra superiore o dai pulsanti **Importa CSV** nei pannelli di inserimento.

---

## Import Comuni da CSV

### Accesso

**File → Importa Comuni da CSV/ISTAT...** → tab **Da file CSV**

### Procedura

1. Fare clic su **Scarica Template CSV** per ottenere il file con le intestazioni corrette
2. Compilare il file CSV con i dati dei comuni
3. Tornare in Foliarium e fare clic su **Sfoglia** per selezionare il file
4. Verificare l'anteprima (prime 20 righe)
5. Fare clic su **Importa**

### Formato CSV comuni

```
nome;provincia;regione;codice_catastale;data_istituzione;data_soppressione;note
Savona;SV;Liguria;I480;1872-01-01;;Capoluogo di provincia
Cairo Montenotte;SV;Liguria;B369;;;
```

| Colonna | Obbligatoria | Formato |
|---|---|---|
| nome | Sì | Testo |
| provincia | Sì | Sigla 2 lettere (es. SV) |
| regione | Sì | Nome regione |
| codice_catastale | No | Codice Belfiore (es. I480) |
| data_istituzione | No | YYYY-MM-DD |
| data_soppressione | No | YYYY-MM-DD o vuoto |
| note | No | Testo libero |

### Gestione errori

Al termine dell'importazione viene mostrato un riepilogo con:
- N° comuni importati con successo
- N° errori con dettaglio riga e messaggio

I comuni già presenti (stesso nome e provincia) vengono saltati senza errore.

---

## Import Comuni da ISTAT

### Accesso

**File → Importa Comuni da CSV/ISTAT...** → tab **Da ISTAT**

### Procedura

1. Inserire la **sigla provincia** (es. `SV`) per filtrare i risultati
2. Fare clic su **Scarica da ISTAT** — Foliarium scarica automaticamente il file ufficiale ISTAT
3. Attendere il download (può richiedere qualche secondo)
4. Verificare l'anteprima dei comuni trovati
5. Fare clic su **Importa**

> 📸 **Screenshot:** Dialog Import da ISTAT con campo provincia, barra di avanzamento e anteprima tabella.

!!! info "Connessione richiesta"
    Il download ISTAT richiede una connessione a Internet. Il file viene scaricato dall'endpoint ufficiale ISTAT e non è necessaria alcuna registrazione o chiave API.

---

## Import Località da CSV

### Accesso

**File → Importa Località da CSV...** → tab **Da CSV**

### Procedura

1. Selezionare il **comune** di riferimento dal menu a tendina
2. Scaricare il template CSV
3. Compilare e importare

### Formato CSV località

```
nome;tipo;civico
Via Roma;Via;
Piazza Martiri della Libertà;Piazza;1
Borgata Lavagnola;Borgata;
```

| Colonna | Obbligatoria | Valori tipo accettati |
|---|---|---|
| nome | Sì | Testo |
| tipo | Sì | Via, Viale, Corso, Piazza, Vicolo, Largo, Salita, Calata, Contrada, Borgata, Regione, Frazione, Strada, Traversa, Passaggio, Località, Altro |
| civico | No | Numero o vuoto |

---

## Import Località da OpenStreetMap

### Accesso

**File → Importa Località da CSV...** → tab **Da OpenStreetMap**

### Procedura

1. Inserire il **nome del comune** nel campo di ricerca (es. "Savona")
2. Selezionare le opzioni:
   - ☑ **Includi strade** (tag `highway` di OSM)
   - ☑ **Includi luoghi** (tag `place`: hamlet, village, suburb, ecc.)
3. Fare clic su **Scarica da OpenStreetMap**
4. Attendere il completamento (barra di avanzamento indeterminata)
5. Verificare l'anteprima
6. Fare clic su **Importa**

> 📸 **Screenshot:** Dialog Import da OpenStreetMap con campo comune, checkbox e barra di avanzamento.

!!! info "Overpass API"
    Foliarium usa l'API pubblica Overpass (`overpass-api.de`) per interrogare i dati OpenStreetMap. Il servizio è gratuito e non richiede chiavi API. Rispettare il rate limit (~1 richiesta/secondo).

---

## Import Partite da Excel/CSV

### Accesso

Sezione **Inserimento** → tab **Partita** → pulsante **Importa CSV**

Il dialog accetta sia file `.csv` che `.xlsx`.

### Formato Excel/CSV partite

| Colonna | Obbligatoria | Descrizione |
|---|---|---|
| comune_nome | Sì | Nome del comune (deve esistere nel DB) |
| numero_partita | Sì | Numero progressivo |
| suffisso_partita | No | Es. "bis", "ter" |
| data_impianto | Sì | YYYY-MM-DD |
| tipo_partita | Sì | principale / derivata / voltura |
| numero_provenienza | No | N. partita di origine |
| stato | Sì | attiva / non_attiva |

### Modalità Excel multi-foglio

Se il file `.xlsx` contiene più fogli, Foliarium utilizza il **primo foglio** per le partite. Assicurarsi che il primo foglio contenga i dati corretti.

---

## Import Possessori da CSV

### Accesso

Sezione **Inserimento** → tab **Possessore** → pulsante **Importa CSV**

### Formato CSV possessori

```
cognome_nome;nome_completo;paternita
Rossi Giovanni;Giovanni Rossi;fu Pietro
Bianchi Maria;;fu Carlo
```

---

## Riepilogo errori di importazione

Al termine di ogni operazione di import, Foliarium mostra una finestra di riepilogo:

| Informazione | Descrizione |
|---|---|
| Record importati | N° record inseriti con successo |
| Record saltati | N° record già presenti o duplicati |
| Errori | N° errori con dettaglio riga e messaggio |

> 📸 **Screenshot:** Finestra riepilogo importazione con tabella successi/errori e pulsante "Chiudi".

!!! warning "Importazione parziale"
    In caso di errori su alcune righe, le righe precedenti già importate con successo NON vengono annullate. Foliarium usa SAVEPOINT per isolare gli errori riga per riga.
