#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Foliarium — Setup Database
Esegue gli script SQL in ordine per inizializzare il database PostgreSQL.

Autore: Marco Santoro — ALGORASTUDIO
Licenza: AGPL-3.0-or-later

Utilizzo:
    python setup_db.py [--host HOST] [--port PORT] [--dbname DBNAME]
                       [--user USER] [--password PASSWORD]

Lo script esegue i file SQL nella cartella database/ nell'ordine corretto.
Il file 01_creazione-database.sql va eseguito manualmente (richiede privilegi superuser).
"""

import os
import sys
import argparse
import getpass

try:
    import psycopg2
    from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
except ImportError:
    print("Errore: psycopg2 non installato. Esegui: pip install psycopg2-binary")
    sys.exit(1)


# Ordine di esecuzione degli script SQL (esclude 01 che crea il database stesso)
SQL_FILES_ORDER = [
    "02_creazione-schema-tabelle.sql",
    "03_funzioni-procedure.sql",
    "03b_expand_fuzzy_search.sql",
    "07_user-management.sql",
    "08_advanced-reporting.sql",
    "09_backup-system.sql",
    "10_performance-optimization.sql",
    "11_advanced-cadastral-features.sql",
    "12_procedure_crud.sql",
]


def get_database_dir():
    """Restituisce il percorso della cartella database/."""
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "database")


def execute_sql_file(cursor, filepath):
    """Esegue un singolo file SQL."""
    filename = os.path.basename(filepath)
    print(f"  Esecuzione: {filename} ... ", end="", flush=True)
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            sql = f.read()
        cursor.execute(sql)
        print("OK")
        return True
    except psycopg2.Error as e:
        print(f"ERRORE")
        print(f"    Dettaglio: {e.pgerror or e}")
        return False
    except FileNotFoundError:
        print(f"FILE NON TROVATO")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Inizializza il database Foliarium eseguendo gli script SQL."
    )
    parser.add_argument("--host", default="localhost", help="Host PostgreSQL (default: localhost)")
    parser.add_argument("--port", default="5432", help="Porta PostgreSQL (default: 5432)")
    parser.add_argument("--dbname", default="catasto_storico", help="Nome database (default: catasto_storico)")
    parser.add_argument("--user", default="postgres", help="Utente PostgreSQL (default: postgres)")
    parser.add_argument("--password", default=None, help="Password PostgreSQL (se omessa, verrà richiesta)")
    parser.add_argument("--demo", action="store_true", help="Carica anche i dati demo (demo_data.sql)")
    args = parser.parse_args()

    password = args.password
    if password is None:
        password = getpass.getpass(f"Password per {args.user}@{args.host}: ")

    db_dir = get_database_dir()

    print(f"\n{'='*60}")
    print(f"  Foliarium — Inizializzazione Database")
    print(f"{'='*60}")
    print(f"  Host:     {args.host}:{args.port}")
    print(f"  Database: {args.dbname}")
    print(f"  Utente:   {args.user}")
    print(f"{'='*60}\n")

    # Connessione al database
    try:
        conn = psycopg2.connect(
            host=args.host,
            port=args.port,
            dbname=args.dbname,
            user=args.user,
            password=password,
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
    except psycopg2.OperationalError as e:
        print(f"Errore di connessione al database: {e}")
        print(f"\nAssicurati che:")
        print(f"  1. PostgreSQL sia in esecuzione")
        print(f"  2. Il database '{args.dbname}' esista (crea con: psql -f database/01_creazione-database.sql)")
        print(f"  3. Le credenziali siano corrette")
        sys.exit(1)

    # Esecuzione degli script SQL in ordine
    print("Esecuzione script SQL:\n")
    errors = 0

    for sql_file in SQL_FILES_ORDER:
        filepath = os.path.join(db_dir, sql_file)
        if not execute_sql_file(cursor, filepath):
            errors += 1

    # Caricamento dati demo se richiesto
    if args.demo:
        print("\nCaricamento dati demo:\n")
        demo_path = os.path.join(db_dir, "demo_data.sql")
        if not execute_sql_file(cursor, demo_path):
            errors += 1

    # Chiusura connessione
    cursor.close()
    conn.close()

    # Riepilogo
    print(f"\n{'='*60}")
    if errors == 0:
        print("  Inizializzazione completata con successo!")
    else:
        print(f"  Inizializzazione completata con {errors} errore/i.")
        print("  Controlla i messaggi sopra per i dettagli.")
    print(f"{'='*60}\n")

    return 0 if errors == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
