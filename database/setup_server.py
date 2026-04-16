import os
import psycopg2
import sys
import getpass  # Per richiedere la password in modo sicuro

# --- CONFIGURAZIONE ---
# Informazioni per la connessione amministrativa
DB_HOST = "localhost"
DB_PORT = "5432"
DB_NAME_TARGET = "catasto_storico"  # Il database da configurare
DB_USER_ADMIN = "postgres"  # L'utente che ha i permessi per creare/modificare

# Ordine di esecuzione degli script SQL di base (verranno sempre eseguiti)
BASE_SQL_SCRIPTS = [
    "sql_scripts/02_creazione-schema-tabelle.sql",
    "sql_scripts/03_funzioni-procedure_def.sql",
    "sql_scripts/07_user-management.sql",
    "sql_scripts/19_creazione_tabella_sessioni.sql",
    "sql_scripts/18_funzioni_trigger_audit.sql",
    "sql_scripts/08_advanced-reporting.sql",
    "sql_scripts/09_backup-system.sql",
    "sql_scripts/10_performance-optimization.sql",
    "sql_scripts/11_advanced-cadastral-features.sql",
    "sql_scripts/12_procedure_crud.sql",
    "sql_scripts/13_workflow_integrati.sql",
    "sql_scripts/14_report_functions.sql",
    "sql_scripts/15_integration_audit_users.sql",
    "sql_scripts/16_advanced_search.sql",
    "sql_scripts/17_funzione_ricerca_immobili.sql",
    "sql_scripts/20_feature_tipi_localita.sql"
]

# Definizione degli script opzionali
SCRIPT_SVUOTA_DATI = "sql_scripts/00_svuota_dati.sql"
SCRIPT_STRESS_TEST = "sql_scripts/04_dati_stress_test.sql"


def bootstrap_database(clear_data=False, load_stress_test=False):
    """
    Orchestra la configurazione del database eseguendo gli script SQL.
    :param clear_data: Se True, svuota i dati prima del setup.
    :param load_stress_test: Se True, carica i dati per lo stress test.
    """
    conn = None

    # Costruisce la lista di script da eseguire dinamicamente
    scripts_to_run = list(BASE_SQL_SCRIPTS)  # Crea una copia della lista base

    if load_stress_test:
        scripts_to_run.append(SCRIPT_STRESS_TEST)

    if clear_data:
        scripts_to_run.insert(0, SCRIPT_SVUOTA_DATI)

    try:
        admin_password = getpass.getpass(
            f"Inserire la password per l'utente amministratore '{DB_USER_ADMIN}': "
        )

        print(f"\nTentativo di connessione al database '{DB_NAME_TARGET}' su {DB_HOST}...")
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            dbname=DB_NAME_TARGET,
            user=DB_USER_ADMIN,
            password=admin_password
        )
        cursor = conn.cursor()

        print("\n--- Inizio esecuzione script di bootstrap ---")
        print("Verranno eseguiti i seguenti script in ordine:")
        for i, script in enumerate(scripts_to_run, 1):
            print(f"  {i}. {script}")
        print("-------------------------------------------")

        for sql_file in scripts_to_run:
            print(f"-> Esecuzione di: {sql_file}...")
            if not os.path.exists(sql_file):
                print(f"   ERRORE: File non trovato: {sql_file}", file=sys.stderr)
                raise FileNotFoundError(f"Il file '{sql_file}' non esiste nella posizione specificata.")

            with open(sql_file, 'r', encoding='utf-8') as f:
                sql_content = f.read()
                if not sql_content.strip():
                    print("   AVVISO: Il file è vuoto, lo salto.")
                    continue
                cursor.execute(sql_content)

        conn.commit()
        print("\n--- Bootstrap completato con successo! ---")
        print("Tutte le modifiche sono state salvate permanentemente nel database.")

    except FileNotFoundError as e:
        print(f"\nERRORE CRITICO: {e}", file=sys.stderr)
        print("Processo interrotto.", file=sys.stderr)
        if conn:
            conn.rollback()
    except psycopg2.Error as e:
        print(f"\nERRORE DI DATABASE: {e}", file=sys.stderr)
        print("Rollback in corso... Nessuna modifica è stata salvata.", file=sys.stderr)
        if conn:
            conn.rollback()
    except Exception as e:
        print(f"\nERRORE INASPETTATO: {e}", file=sys.stderr)
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()
            print("\nConnessione al database chiusa.")


if __name__ == '__main__':
    print("--- SCRIPT DI BOOTSTRAP DEL DATABASE CATASTO STORICO ---")
    print("\nATTENZIONE: Questo script configura un database GIÀ ESISTENTE.")
    print(f"Assicurarsi che il database '{DB_NAME_TARGET}' sia stato creato prima di procedere.")
    print("Comando SQL di esempio: CREATE DATABASE catasto_storico OWNER postgres;\n")

    # --- Interazione con l'utente per le opzioni ---
    scelta_svuota = input(">> Vuoi CANCELLARE TUTTI I DATI dalle tabelle prima del setup? (s/n): ").lower()
    do_clear_data = scelta_svuota == 's'

    if do_clear_data:
        print("\n   /!\\ ATTENZIONE: CONFERMA CANCELLAZIONE DATI /!\\")
        print("   Questa operazione è irreversibile e rimuoverà tutti i dati.")
        conferma = input("   Sei assolutamente sicuro? Scrivi 'si' per confermare: ").lower()
        if conferma != 'si':
            print("Cancellazione annullata.")
            do_clear_data = False

    scelta_stress = input("\n>> Vuoi caricare i dati di STRESS TEST (da '04_dati_stress_test.sql')? (s/n): ").lower()
    do_load_stress = scelta_stress == 's'

    print("\nRIEPILOGO DELLE OPERAZIONI:")
    print(f"  - Cancellazione di tutti i dati esistenti: {'Sì' if do_clear_data else 'No'}")
    print(f"  - Caricamento dati per stress test:      {'Sì' if do_load_stress else 'No'}")
    
    choice = input("\nProcedere con il bootstrap usando queste impostazioni? (s/n): ")
    if choice.lower() == 's':
        bootstrap_database(clear_data=do_clear_data, load_stress_test=do_load_stress)
    else:
        print("Operazione annullata dall'utente.")