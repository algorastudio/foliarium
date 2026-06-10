# Status Report: Sviluppo Applicazione "Foliarium"

**Versione analizzata**: v1.0.2
**Data del report**: 2026-05-21
**Stack analizzato**: Python 3.12, PyQt6 (Desktop), PostgreSQL 14+, REST API (FastAPI) [escluso React e Django per esplicita richiesta]

---

## 1. Architettura Generale e Stato dello Sviluppo

Il progetto **Foliarium** (Archivio Catastale Storico) si presenta maturo, strutturato e ben organizzato, giunto alla sua **versione 1.0.2**. Le componenti fondamentali dello sviluppo sono completate.

Dall'analisi del codebase, si evince un intenso lavoro di "refactoring strutturale" (definito "Sprint 3 six-hats") terminato recentemente, che ha notevolmente migliorato la solidità dell'applicazione:
- **Separazione delle responsabilità:** Le enormi classi storiche ("god-objects") sono state rifattorizzate e distribuite organicamente nel package `foliarium/ui` e `foliarium/core/services`. Moduli unici come `app_utils.py` sono passati da 923 a 176 LOC, delegando logiche di UI, report PDF ed export CSV a moduli dedicati.
- **Data Access Layer frammentato:** L'enorme gestore database `CatastoDBManager` è stato segmentato con l'uso di "mixin" per dominio (`db/comuni.py`, `db/partite.py`, ecc.) e si aggancia ad una base comune (`db/base.py`) che gestisce il connection pool e il mapping con eccezioni custom.
- **Contract Type-Checking:** Sono stati implementati "API Contracts" con il modulo `foliarium/protocols.py` usando `typing.Protocol`, che garantiscono l'affidabilità delle implementazioni.
- **Componenti e integrazioni:** Il software prevede il supporto per gestione Utenti (Login crittografato), dashboard, sistema multi-periodo-storico, e un layer REST API opzionale con FastAPI.

## 2. Bug Riscontrati e Criticità Tecniche

Durante l'analisi del repository e l'esecuzione degli strumenti di test, sono emersi i seguenti bug e problematiche:

1. **Bug nei Test E2E / Insuccesso della Pipeline (CI):**
   Attualmente, lanciando i test tramite `pytest`, l'intera suite fallisce a causa del seguente errore:
   ```
   psycopg2.OperationalError: Il database è al massimo delle connessioni attive. Attendere un momento e riprovare l'operazione.
   (Connection refused su porta 5432 localhost)
   ```
   *Causa:* I test dipendono da un'istanza viva di PostgreSQL (con le relative tabelle) invece di simulare il database o di avviare sistematicamente una base dati epimera (es. via docker-compose durante la CI).
   *Conseguenza:* La copertura ("test coverage") registrata durante l'ultimo run CI è crollata ad appena il **4.04%** (o 23% in altri run), ampiamente sotto il "gate" minimo richiesto del 35%. L'intera Pipeline CI è attualmente esposta a fallimenti costanti.

2. **Gestione del Connection Pool in `reconnect_pool_if_needed`:**
   Mentre gran parte del codice che gestisce transazioni fa uso corretto del context manager `_get_connection()`, in scenari di indisponibilità prolungata il meccanismo di retry è debole e affoga log di fallimento quando `self.pool` è nullo e il database host non è raggiungibile.

3. **Mancanza di psycopg2 nel setup dei test base:**
   Senza installare preliminarmente le librerie di base (es. nel virtual env), i moduli richiamano immediatamente `psycopg2` causando blocco nell'inizializzazione del test via Pytest.

## 3. Suggerimenti e Miglioramenti Proposti

### Relativi al Testing (Priorità Alta)
- **Containerizzazione dei Test (Testcontainers):** Poiché l'architettura non prevede mock espliciti del layer DB, si suggerisce di utilizzare librerie come `testcontainers-python` per sollevare e distruggere automaticamente un'istanza PostgreSQL per la test suite. Questo eliminerà l'errore "Connection refused".
- **Disaccoppiamento con Mock:** Si consiglia di creare finti implementatori (`MockDBManager`) rispettanti le classi `Protocol` presenti in `foliarium/protocols.py` così da testare i widget della UI in completo isolamento rispetto al database, per ristabilire e far salire il coverage target oltre il 35%.

### Relativi al Database e Prestazioni
- **Robustezza del Retry Loop:** Rafforzare la logica all'interno di `initialize_main_pool` (usato sia dalla GUI che dall'app FastAPI). Attualmente l'app FastAPI implementa un retry per ~60 secondi (cfr. `api/main.py`), ma la logica GUI è sensibile a crash istantanei. Si consiglia un meccanismo di wait-and-retry globale.
- **Tool di Migrazione (`bin/migrate.py`):** Il tool lean di migrazione è ottimo, ma andrebbe considerato un wrapper formale per le transazioni DDL, in modo da avere rollback sicuri qualora l'esecuzione di script SQL complessi fallisca a metà.

### Suggerimenti per la Documentazione
- Aggiungere documentazione specifica ("on-boarding") che spieghi nel dettaglio agli sviluppatori come lanciare la test-suite localmente usando il server PostgreSQL configurato in `docker-compose.yml`.

---
*Report autogenerato al termine dell'esplorazione del repository.*
