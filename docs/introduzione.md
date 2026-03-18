# Introduzione a Foliarium

## Cos'è Foliarium

**Foliarium** è un'applicazione desktop sviluppata appositamente per l'Archivio di Stato di Savona per la gestione digitale del patrimonio documentale catastale storico. Permette di:

- Consultare e ricercare partite catastali, possessori e immobili storici
- Inserire nuovi record nel rispetto della struttura archivistica originale
- Generare report genealogici sulle successioni proprietarie
- Esportare i dati in formato PDF, Excel, CSV e ODT
- Importare dati massivi da file Excel/CSV o da fonti esterne (ISTAT, OpenStreetMap)
- Visualizzare statistiche e grafici sulla consistenza del patrimonio catastale

---

## Architettura del sistema

Foliarium è composta da tre livelli:

```
┌─────────────────────────────────┐
│   Interfaccia Grafica (PyQt6)   │  ← gui_main.py, gui_widgets.py
├─────────────────────────────────┤
│   Logica Applicativa (Python)   │  ← catasto_db_manager.py, app_utils.py
├─────────────────────────────────┤
│   Database (PostgreSQL 14+)     │  ← catasto_storico
└─────────────────────────────────┘
```

Il database `catasto_storico` contiene le seguenti entità principali:

| Entità | Descrizione |
|---|---|
| **Comuni** | Elenco dei comuni con dati catastali |
| **Possessori** | Proprietari storici dei beni |
| **Partite catastali** | Unità fiscale di riferimento |
| **Immobili** | Fabbricati e terreni associati a una partita |
| **Variazioni** | Volture e passaggi di proprietà |
| **Località** | Vie, borghi e frazioni del territorio |

---

## Requisiti di sistema

### Utente finale (workstation)

| Componente | Requisito minimo |
|---|---|
| Sistema operativo | Windows 10 (64-bit) o superiore |
| RAM | 4 GB (8 GB consigliati) |
| Spazio disco | 500 MB per l'applicazione |
| Risoluzione schermo | 1280×800 minima |
| Connessione | Rete locale verso il server PostgreSQL |

### Server database

| Componente | Requisito |
|---|---|
| Sistema operativo | Windows Server 2019+ o Linux |
| PostgreSQL | Versione 14 o superiore |
| RAM | 8 GB consigliati |
| Spazio disco | In base al volume dei dati storici |

---

## Struttura dell'interfaccia

L'interfaccia è organizzata in sezioni principali accessibili dalla barra laterale o dalle tab superiori:

| Sezione | Funzione |
|---|---|
| **Dashboard** | Statistiche generali e accesso rapido |
| **Consultazione** | Ricerca partite, possessori, immobili, documenti |
| **Inserimento** | Aggiunta di nuovi comuni, possessori, partite, immobili |
| **Esportazioni** | Export in PDF, Excel, CSV, ODT |
| **Reportistica** | Report genealogici, confronto partite, export ODT |
| **Statistiche** | Grafici di analisi del patrimonio |
| **Impostazioni** | Tema grafico, configurazione, gestione utenti |

---

## Convenzioni usate in questo manuale

!!! info "Nota informativa"
    Riquadri blu indicano informazioni aggiuntive utili.

!!! warning "Attenzione"
    Riquadri arancioni indicano operazioni che richiedono cautela.

!!! danger "Pericolo"
    Riquadri rossi indicano operazioni irreversibili.

> 📸 **Screenshot:** Le immagini segnaposto indicano dove verrà inserito lo screenshot definitivo.
