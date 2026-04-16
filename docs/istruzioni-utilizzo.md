# Guida di Implementazione del Sistema Catasto Storico

Questa guida fornisce le istruzioni passo-passo per implementare il sistema completo del Catasto Storico utilizzando PostgreSQL e pgAdmin.

## Sequenza di esecuzione

Per implementare correttamente il sistema, segui questa sequenza:

1. **Creazione del database**
   - Esegui lo script "1. Creazione del Database Catasto Storico"
   - Connettiti al nuovo database creato

2. **Creazione dello schema e delle tabelle**
   - Esegui lo script "2. Creazione dello Schema e delle Tabelle"
   - Questo script crea tutte le tabelle necessarie, i vincoli e gli indici

3. **Creazione delle funzioni e procedure**
   - Esegui lo script "3. Funzioni e Procedure"
   - Questo script crea trigger, funzioni di utilità, procedure e viste

4. **Inserimento dei dati di esempio**
   - Esegui lo script "4. Dati di Esempio"
   - I dati verranno inseriti senza errori grazie alla clausola ON CONFLICT

5. **Test del sistema**
   - Esegui lo script "5. Query di Test e Utilizzo" per verificare il corretto funzionamento

## Note importanti sull'utilizzo

### Transazioni

Quando lavori con le procedure, ricorda di usare sempre transazioni esplicite:

```sql
BEGIN;
CALL nome_procedura(parametri);
COMMIT;
```

In caso di errore, puoi annullare le modifiche con:
```sql
ROLLBACK;
```

### Utilizzo delle procedure principali

1. **Inserimento di un nuovo possessore**:
```sql
BEGIN;
CALL inserisci_possessore(
    'Comune',         -- comune_nome
    'Cognome Nome',   -- cognome_nome
    'fu Padre',       -- paternita
    'Nome completo',  -- nome_completo
    true              -- attivo
);
COMMIT;
```

2. **Creazione di una nuova partita con possessori**:
```sql
BEGIN;
CALL inserisci_partita_con_possessori(
    'Comune',             -- comune_nome
    numero_partita,       -- numero_partita
    'principale',         -- tipo
    '2025-04-01',         -- data_impianto
    ARRAY[1, 2, 3]        -- IDs dei possessori
);
COMMIT;
```

3. **Registrazione di una consultazione**:
```sql
BEGIN;
CALL registra_consultazione(
    CURRENT_DATE,                 -- data
    'Nome Richiedente',           -- richiedente
    'Documento ID',               -- documento_identita
    'Motivazione',                -- motivazione
    'Materiale consultato',       -- materiale_consultato
    'Funzionario autorizzante'    -- funzionario_autorizzante
);
COMMIT;
```

### Funzioni di ricerca

1. **Ricerca possessori per nome**:
```sql
SELECT * FROM cerca_possessori('Cognome');
```

2. **Immobili di un possessore**:
```sql
SELECT * FROM get_immobili_possessore(id_possessore);
```

3. **Viste per informazioni complete**:
```sql
-- Partite con possessori e numero immobili
SELECT * FROM v_partite_complete WHERE comune_nome = 'Comune';

-- Variazioni con contratti
SELECT * FROM v_variazioni_complete;
```

## Risoluzione dei problemi comuni

1. **Errore di duplicazione nel comune**: 
   - Lo script di inserimento dei dati di esempio utilizza `ON CONFLICT (nome) DO NOTHING` per evitare duplicazioni

2. **Errore nelle transazioni**:
   - Le procedure sono state corrette per rimuovere il COMMIT interno
   - Usa sempre BEGIN e COMMIT attorno alle chiamate delle procedure

3. **Query con errori di sintassi**:
   - Verifica che lo schema sia correttamente impostato con `SET search_path TO catasto;`

## Gestione in pgAdmin

In pgAdmin, puoi esplorare il database così:

1. **Struttura Database**: Schemas > catasto > Tables/Views/Functions
2. **Visualizzazione dati**: Clic destro su tabella > View/Edit Data > All Rows
3. **Diagramma ER**: Clic destro sul database > Generate ERD
4. **Esecuzione script**: Tools > Query Tool

## Prossimi sviluppi

Il sistema attualmente implementa il back-end completo con PostgreSQL. I prossimi sviluppi previsti sono:

1. **Interfaccia utente**: Sviluppo di un'interfaccia web o desktop
2. **Reportistica avanzata**: Creazione di report statistici specializzati
3. **Funzionalità di esportazione**: Esportazione dati in vari formati
4. **Gestione utenti**: Implementazione di un sistema di autenticazione e autorizzazione