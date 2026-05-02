# Inserimento Dati

La sezione **Inserimento** permette di aggiungere nuovi record al database catastale. È consigliabile seguire l'ordine logico: Comune → Possessore → Partita → Immobile.

> 📸 **Screenshot:** Sezione Inserimento con le sotto-tab: Comune, Possessore, Partita, Immobile, Località.

---

## Ordine consigliato

```
1. Inserisci il Comune (se non presente)
2. Inserisci il Possessore
3. Inserisci la Partita catastale (collega il Possessore)
4. Inserisci gli Immobili della Partita
5. Inserisci la Località (se non presente)
```

---

## Pulsanti uniformi nei pannelli di inserimento

Tutti i pannelli di inserimento espongono **5 pulsanti** nella parte inferiore, per un flusso di lavoro completo:

| Pulsante | Funzione |
|---|---|
| **Inserisci / Salva** | Salva il record nel database |
| **Pulisci Campi** | Azzera tutti i campi del modulo |
| **Importa CSV** | Apre la finestra di importazione massiva da file |
| **Scarica CSV** | Scarica i dati esistenti (comuni, possessori, etc.) in formato CSV per la modifica massiva |
| **Scarica Template** | Scarica il file CSV di esempio con le intestazioni corrette |

### Flusso di lavoro round-trip: Scarica → Modifica → Reimporta

Foliarium supporta un flusso di lavoro efficiente per aggiornare i dati in massa:

1. **Scarica CSV** — esporta i dati esistenti (es. tutti i comuni, tutti i possessori)
2. Modifica il file CSV in Excel, LibreOffice Calc o un editor di testo
3. **Importa CSV** — reimporta il file modificato (con conferma prima di salvare)

Il file scaricato usa esattamente le stesse colonne del template di import, garantendo compatibilità totale.

---

## Inserimento Comune

### Campi

| Campo | Obbligatorio | Descrizione |
|---|---|---|
| Nome | Sì | Nome del comune |
| Provincia | Sì | Sigla provinciale (es. SV) |
| Regione | Sì | Nome della regione |
| Codice catastale | No | Codice Belfiore del Comune |
| Data istituzione | No | Data di istituzione del comune |
| Data soppressione | No | Eventuale data di soppressione |
| Note | No | Annotazioni libere |

> 📸 **Screenshot:** Modulo inserimento comune con i campi compilati.

---

## Inserimento Possessore

### Campi

| Campo | Obbligatorio | Descrizione |
|---|---|---|
| Cognome e Nome | Sì | Es. "Rossi Giovanni" |
| Nome completo | No | Nome esteso o variante d'archivio |
| Paternità | No | Es. "fu Pietro" |

> 📸 **Screenshot:** Modulo inserimento possessore.

!!! info "Formato paternità"
    Inserire la paternità nel formato "fu [Nome]" (es. "fu Giuseppe") per rispettare la convenzione archivistica storica.

---

## Inserimento Partita

### Campi

| Campo | Obbligatorio | Descrizione |
|---|---|---|
| Comune | Sì | Selezionare dalla lista |
| Numero partita | Sì | Numero progressivo |
| Suffisso | No | Lettera o numero aggiuntivo (es. "bis") |
| Data impianto | Sì | Data di apertura della partita |
| Tipo partita | Sì | Principale / Derivata / Voltura |
| Numero provenienza | No | Numero della partita di origine |
| Stato | Sì | Attiva / Non attiva |

Dopo il salvataggio è possibile collegare i possessori alla partita dalla finestra di dettaglio.

> 📸 **Screenshot:** Modulo inserimento partita con menu a tendina per il comune.

---

## Inserimento Immobile

### Campi

| Campo | Obbligatorio | Descrizione |
|---|---|---|
| Partita | Sì | Selezionare la partita di appartenenza |
| Natura | Sì | Fabbricato / Terreno |
| Classificazione | No | Categoria catastale |
| Classe | No | Classe di redditività |
| Consistenza | No | Vani, are, ecc. |
| Località | No | Via o borgata di ubicazione |
| Reddito dominicale | No | Reddito in lire storiche |
| Reddito agrario | No | Solo per terreni |
| Note | No | Annotazioni libere |

> 📸 **Screenshot:** Modulo inserimento immobile con selezione natura (Fabbricato/Terreno).

---

## Inserimento Località

### Campi

| Campo | Obbligatorio | Descrizione |
|---|---|---|
| Nome | Sì | Nome della via o borgata |
| Tipo | Sì | Via, Viale, Corso, Piazza, Borgata, ecc. |
| Numero civico | No | Numero di riferimento |

> 📸 **Screenshot:** Modulo inserimento località con menu a tendina per il tipo.

---

## Import CSV

Per importare dati in blocco da un file CSV:

1. Fare clic su **Importa CSV** nel pannello di inserimento desiderato
2. Selezionare il file `.csv` dalla finestra di dialogo
3. Verificare l'anteprima delle prime 20 righe
4. Fare clic su **Importa** per avviare l'inserimento

### Template CSV

Fare clic su **Scarica Template** per ottenere un file CSV con le intestazioni corrette. Aprirlo con Excel o un editor di testo, compilare i dati e salvarlo in formato CSV UTF-8.

| Entità | Colonne template |
|---|---|
| Comune | `nome;provincia;regione;codice_catastale;data_istituzione;data_soppressione;note` |
| Possessore | `cognome_nome;nome_completo;paternita` |
| Partita | `comune_nome;numero_partita;suffisso_partita;data_impianto;tipo_partita;numero_provenienza;stato` |
| Immobile | `partita_id;natura;classificazione;classe;consistenza;localita;reddito_dominicale;reddito_agrario;note` |
| Località | `nome;tipo;civico` |

!!! warning "Formato date nel CSV"
    Inserire le date nel formato `YYYY-MM-DD` (es. `1922-03-15`). Formati diversi possono causare errori di importazione.
