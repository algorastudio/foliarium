# Architettura di Foliarium

## Panoramica

Foliarium è un'applicazione desktop a due livelli (**client-server**):

```
┌─────────────────────────┐          ┌─────────────────────────┐
│   Client Desktop        │          │   Server Database       │
│                         │          │                         │
│   PyQt5 GUI             │  TCP/IP  │   PostgreSQL 13+        │
│   (gui_main, widgets,   │◄────────►│   Schema: catasto       │
│    dialogs)             │ psycopg2 │                         │
│                         │   pool   │   Tabelle, viste,       │
│   Logica applicativa    │          │   funzioni, trigger,    │
│   (catasto_db_manager)  │          │   procedure CRUD        │
└─────────────────────────┘          └─────────────────────────┘
```

- **Client**: applicazione Python/PyQt5 che si installa sulla postazione dell'operatore
- **Server**: database PostgreSQL centralizzato, accessibile da più client in rete

## Moduli Python

### `main.py` — Entry point
Punto di ingresso dell'applicazione. Configura i metadati Qt (`QCoreApplication`), avvia il logging e crea la finestra principale.

### `src/config.py` — Configurazione
Gestisce le impostazioni dell'applicazione: connessione al database (host, porta, nome, utente, schema), costanti dell'interfaccia (etichette colonne), flag ambiente CI/CD e configurazione del logging con rotazione dei file.

### `src/app_paths.py` — Gestione percorsi
Risolve i percorsi dell'applicazione sia in ambiente di sviluppo che in un eseguibile PyInstaller. Definisce le directory per risorse statiche (`resources/`, `styles/`) e per i dati utente dinamici (log, esportazioni).

### `src/catasto_db_manager.py` — Accesso al database
Classe `CatastoDBManager`: gestisce tutte le operazioni verso PostgreSQL tramite connection pool (`psycopg2.pool`). Include operazioni CRUD per tutte le entità (comuni, partite, possessori, immobili, località, variazioni, contratti), gestione utenti e permessi, audit log, backup e ricerca fuzzy. Definisce eccezioni personalizzate (`DBMError`, `DBUniqueConstraintError`, `DBNotFoundError`, `DBDataError`).

### `src/gui_main.py` — Finestra principale
Classe `CatastoMainWindow`: finestra principale con barra dei menu, barra di stato e area centrale a schede (`QTabWidget`). Gestisce la connessione al database, il login utente, il caricamento dei widget e la navigazione tra le sezioni.

### `src/gui_widgets.py` — Widget interfaccia
Contiene tutti i widget principali dell'interfaccia:

| Widget | Funzione |
|---|---|
| `DashboardWidget` | Panoramica con statistiche |
| `ElencoComuniWidget` | Lista e gestione dei comuni |
| `RicercaPartiteWidget` | Ricerca partite catastali |
| `RicercaAvanzataImmobiliWidget` | Ricerca immobili con filtri |
| `UnifiedFuzzySearchWidget` | Ricerca fuzzy unificata |
| `InserimentoComuneWidget` | Inserimento nuovo comune |
| `InserimentoPossessoreWidget` | Inserimento nuovo possessore |
| `InserimentoPartitaWidget` | Inserimento nuova partita |
| `InserimentoLocalitaWidget` | Inserimento nuova località |
| `RegistrazioneProprietaWidget` | Registrazione legami possessore-partita |
| `OperazioniPartitaWidget` | Operazioni su partite esistenti |
| `EsportazioniWidget` | Esportazione dati (CSV, PDF, JSON) |
| `ReportisticaWidget` | Report avanzati |
| `StatisticheWidget` | Statistiche aggregate |
| `GestioneUtentiWidget` | Amministrazione utenti e ruoli |
| `AuditLogViewerWidget` | Visualizzatore registro audit |
| `BackupWidget` | Gestione backup database |
| `RegistraConsultazioneWidget` | Registrazione consultazioni archivio |
| `GestionePeriodiStoriciWidget` | Gestione periodi storici |
| `GestioneTipiLocalitaWidget` | Gestione tipologie stradali |

### `src/dialogs.py` — Dialoghi
Finestre di dialogo per operazioni specifiche: configurazione database, importazione CSV, EULA, modifica entità (comuni, possessori, immobili, località, periodi storici), selezione entità, dettagli partita, creazione utente, promemoria backup.

### `src/custom_widgets.py` — Widget personalizzati
Widget riutilizzabili: `ImmobiliTableWidget` (tabella immobili preconfigurata), `QPasswordLineEdit` (campo password), `LazyLoadedWidget` (classe base per il caricamento differito dei dati al primo accesso).

### `src/app_utils.py` — Utility
Funzioni di supporto: rilevamento IP locale, gestione password con keyring, generazione report PDF (classi `PDFPartita`, `PDFPossessore`, `GenericTextReportPDF`, `BulkReportPDF`), funzioni di esportazione (`gui_esporta_partita_pdf/json/csv`, `gui_esporta_possessore_pdf/json/csv`).

## Schema del database

Lo schema risiede nello schema PostgreSQL `catasto` e comprende le seguenti tabelle principali:

```
periodo_storico          Periodi storici (Regno di Sardegna, Regno d'Italia, Repubblica)
comune                   Anagrafica comuni con codice catastale e periodo di riferimento
registro_partite         Registri delle partite per comune e anno
registro_matricole       Registri delle matricole per comune e anno
partita                  Partite catastali (numero, suffisso, stato, tipo, date)
possessore               Possessori/proprietari con paternità
partita_possessore       Relazione N:M tra partite e possessori (titolo, quota)
localita                 Località/indirizzi (tipologia stradale, civico)
immobile                 Immobili (natura, piani, vani, consistenza, classificazione)
partita_relazione        Relazioni tra partite principali e secondarie
variazione               Variazioni di proprietà (vendita, successione, divisione, ecc.)
contratto                Contratti associati alle variazioni (notaio, repertorio)
consultazione            Registro consultazioni dell'archivio
audit_log                Log automatico delle operazioni (INSERT, UPDATE, DELETE)
app_metadata             Metadati applicazione (chiave-valore)
utente                   Utenti applicazione (da script 07)
permesso                 Permessi disponibili
utente_permesso          Associazione utenti-permessi
```

### Estensioni PostgreSQL utilizzate
- `uuid-ossp` — generazione UUID
- `pg_trgm` — ricerca fuzzy con trigrammi (indici GIN)

### Viste principali
- `v_partite_complete` — join completo partite-comuni-possessori con conteggio immobili
- `v_variazioni_complete` — join variazioni-partite-contratti con dati origine/destinazione

## Sicurezza

- Le password degli utenti applicativi sono memorizzate con hash **bcrypt**
- Il salvataggio delle password di connessione al database è gestito tramite **keyring** del sistema operativo
- Il file `config.ini` (con credenziali) è escluso dal repository tramite `.gitignore`
- L'audit log registra automaticamente tutte le modifiche ai dati con utente, timestamp e IP
- Il sistema di permessi consente di limitare l'accesso alle funzionalità per ruolo

## Compatibilità PyInstaller

Il modulo `app_paths.py` gestisce la risoluzione dei percorsi sia in ambiente di sviluppo che all'interno di un eseguibile creato con PyInstaller (`sys._MEIPASS`), rendendo possibile la distribuzione come singolo file eseguibile.
