#!/usr/bin/env python3
"""
prepare_demo_db.py — Script CI per preparare la cartella demo_data/

Eseguito durante la fase build-demo del pipeline GitHub Actions.
Richiede che la cartella pgsql/ (PostgreSQL portabile Windows) sia già
presente nella directory corrente.

Operazioni svolte:
  1. initdb  -> crea demo_data/ con superuser 'postgres' (trust locale)
  2. Avvia il server temporaneamente sulla porta 15432
  3. Crea ruolo 'demo_user' e DB 'catasto_storico'
  4. Esegue sql_scripts/02, 03, 05_demo_dataset.sql
  5. Crea utente applicativo 'demo' nella tabella utenti
  6. Ferma il server
  7. Rimuove postmaster.pid (se presente) per portabilità

Output: cartella demo_data/ pronta da includere nel bundle PyInstaller.

Uso (CI Windows):
  python prepare_demo_db.py --pgsql-dir pgsql

Uso (locale, test):
  python prepare_demo_db.py --pgsql-dir C:/pgsql14 --skip-if-exists
"""
from __future__ import annotations

import argparse
import io
import os
import platform
import shutil
import subprocess
import sys
import time
from pathlib import Path

# Force UTF-8 output on Windows (avoids cp1252 UnicodeEncodeError)
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
if sys.stderr.encoding and sys.stderr.encoding.lower() != "utf-8":
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

HERE = Path(__file__).parent

DEMO_PORT     = 15432
DEMO_DB_NAME  = "catasto_storico"
DEMO_ROLE     = "demo_user"
DEMO_ROLE_PWD = os.environ.get("DEMO_DB_PASS", "")
DEMO_APP_USER = "demo"
DEMO_APP_PWD  = os.environ.get("DEMO_LOGIN_PASS", DEMO_ROLE_PWD)
DATA_DIR      = HERE / "demo_data"

# Ordine di applicazione per il DB demo. Il dataset demo va in fondo,
# dopo schema, funzioni e feature aggiuntive. L'utente applicativo 'demo'
# viene creato a parte da create_app_demo_user() (vedi piu' giu').
# Da v1.0.0: lookup tipo_possesso/tipo_localita, soft-delete e tabella sessioni
# sono integrati in 02 e 07_user-management (vedi sql_scripts/README.md).
SQL_SCRIPTS = [
    HERE / "sql_scripts" / "schema"    / "01_tables.sql",
    HERE / "sql_scripts" / "functions" / "01_core.sql",
    HERE / "sql_scripts" / "functions" / "02_crud.sql",
    HERE / "sql_scripts" / "functions" / "03_workflow.sql",
    HERE / "sql_scripts" / "functions" / "04_search.sql",
    HERE / "sql_scripts" / "functions" / "05_reporting.sql",
    HERE / "sql_scripts" / "functions" / "06_audit.sql",
    HERE / "sql_scripts" / "functions" / "07_features.sql",
    HERE / "sql_scripts" / "admin"     / "01_users.sql",
    HERE / "sql_scripts" / "admin"     / "02_backup.sql",
    HERE / "sql_scripts" / "admin"     / "03_performance.sql",
    HERE / "sql_scripts" / "schema"    / "02_trigram_indexes.sql",  # CONCURRENTLY: fuori transazione
    HERE / "sql_scripts" / "demo"      / "demo_data.sql",
]

IS_WIN = platform.system() == "Windows"
EXE = ".exe" if IS_WIN else ""


def _exe(pg_bin: Path, name: str) -> Path:
    return pg_bin / f"{name}{EXE}"


def run(cmd: list, **kw) -> subprocess.CompletedProcess:
    print(f"  $ {' '.join(str(c) for c in cmd)}")
    return subprocess.run(cmd, check=True, **kw)


def run_psql(pg_bin: Path, sql: str, dbname: str = "postgres") -> None:
    """Esegue una stringa SQL tramite psql."""
    run([
        str(_exe(pg_bin, "psql")),
        "-h", "127.0.0.1", "-p", str(DEMO_PORT),
        "-U", "postgres",
        "-d", dbname,
        "-c", sql,
    ])


def run_psql_file(pg_bin: Path, sql_file: Path, dbname: str) -> None:
    """Esegue un file SQL tramite psql."""
    run([
        str(_exe(pg_bin, "psql")),
        "-h", "127.0.0.1", "-p", str(DEMO_PORT),
        "-U", "postgres",
        "-d", dbname,
        "-f", str(sql_file),
    ])


def wait_ready(pg_bin: Path, attempts: int = 30) -> bool:
    pg_isready = _exe(pg_bin, "pg_isready")
    for i in range(attempts):
        r = subprocess.run(
            [str(pg_isready), "-h", "127.0.0.1", "-p", str(DEMO_PORT)],
            capture_output=True,
        )
        if r.returncode == 0:
            return True
        print(f"    Attesa PostgreSQL... ({i+1}/{attempts})")
        time.sleep(1)
    return False


def make_pg_hba(data_dir: Path) -> None:
    """Sostituisce pg_hba.conf con una configurazione trust per connessioni locali."""
    hba = data_dir / "pg_hba.conf"
    hba.write_text(
        "# TYPE  DATABASE        USER            ADDRESS                 METHOD\n"
        "local   all             all                                     trust\n"
        "host    all             all             127.0.0.1/32            trust\n"
        "host    all             all             ::1/128                 trust\n",
        encoding="utf-8",
    )


def make_postgresql_conf(data_dir: Path, port: int) -> None:
    """Aggiunge/modifica le impostazioni minime in postgresql.conf."""
    conf = data_dir / "postgresql.conf"
    text = conf.read_text(encoding="utf-8") if conf.exists() else ""

    overrides = (
        f"\n# === Demo Foliarium (generato da prepare_demo_db.py) ===\n"
        f"port = {port}\n"
        f"listen_addresses = '127.0.0.1'\n"
        f"max_connections = 20\n"
        f"shared_buffers = 32MB\n"
        f"logging_collector = off\n"
        f"log_min_messages = warning\n"
    )
    conf.write_text(text + overrides, encoding="utf-8")


def generate_bcrypt_hash(password: str) -> str:
    """Genera un hash bcrypt della password per la tabella utenti."""
    try:
        import bcrypt
        return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    except ImportError:
        # Se bcrypt non è disponibile, restituisce un placeholder
        # (l'utente demo dovrà essere creato manualmente)
        print("  ATTENZIONE: bcrypt non disponibile, hash placeholder usato.")
        return "$2b$12$PLACEHOLDER_INSTALL_BCRYPT"


def create_app_demo_user(pg_bin: Path) -> None:
    """
    Crea l'utente 'demo' nella tabella 'utenti' dell'applicazione.
    Usa ON CONFLICT DO NOTHING per idempotenza.
    """
    pwd_hash = generate_bcrypt_hash(DEMO_APP_PWD)
    # Escape apici singoli nell'hash (precauzione)
    pwd_hash_escaped = pwd_hash.replace("'", "''")

    sql = (
        f"SET search_path TO catasto, public; "
        f"INSERT INTO utente (username, password_hash, nome_completo, email, ruolo, attivo) "
        f"VALUES ('{DEMO_APP_USER}', '{pwd_hash_escaped}', 'Utente Demo', 'demo@foliarium.demo', 'admin', true) "
        f"ON CONFLICT (username) DO UPDATE SET "
        f"  password_hash = EXCLUDED.password_hash, "
        f"  attivo = true;"
    )
    run_psql(pg_bin, sql, dbname=DEMO_DB_NAME)
    print(f"  Utente applicativo '{DEMO_APP_USER}' creato/aggiornato.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepara demo_data/ per Foliarium Demo")
    parser.add_argument("--pgsql-dir", default="pgsql",
                        help="Directory radice di PostgreSQL portabile (default: pgsql/)")
    parser.add_argument("--skip-if-exists", action="store_true",
                        help="Salta se demo_data/ esiste già")
    parser.add_argument("--data-dir", default=str(DATA_DIR),
                        help=f"Cartella dati output (default: {DATA_DIR})")
    args = parser.parse_args()

    pg_root = Path(args.pgsql_dir).resolve()
    pg_bin  = pg_root / "bin"
    data_dir = Path(args.data_dir).resolve()

    if not pg_bin.exists():
        print(f"ERRORE: cartella bin non trovata in '{pg_root}'", file=sys.stderr)
        sys.exit(1)

    print(f"\n{'='*60}")
    print(f" Preparazione demo_data/ per Foliarium Demo")
    print(f"{'='*60}")
    print(f"  PostgreSQL bin : {pg_bin}")
    print(f"  Data dir       : {data_dir}")
    print(f"  Porta          : {DEMO_PORT}")

    # --- 1. initdb ---
    if data_dir.exists():
        if args.skip_if_exists:
            print(f"\n  demo_data/ già esistente, skip (--skip-if-exists).")
            return
        print(f"\n  Rimozione demo_data/ esistente...")
        shutil.rmtree(data_dir)

    print("\n[1/6] initdb — inizializzazione cluster PostgreSQL...")
    env = os.environ.copy()
    # Disabilita eventuali variabili PGDATA che potrebbero interferire
    env.pop("PGDATA", None)
    env["PGPASSWORD"] = ""
    run([
        str(_exe(pg_bin, "initdb")),
        "-D", str(data_dir),
        "-U", "postgres",
        "--locale=C",
        "--encoding=UTF8",
        "--no-instructions",
    ], env=env)

    # --- 2. Configura pg_hba.conf e postgresql.conf ---
    print("\n[2/6] Configurazione pg_hba.conf e postgresql.conf...")
    make_pg_hba(data_dir)
    make_postgresql_conf(data_dir, DEMO_PORT)

    # --- 3. Avvia il server ---
    pg_ctl  = _exe(pg_bin, "pg_ctl")
    log_file = data_dir / "pg_init.log"

    print(f"\n[3/6] Avvio PostgreSQL temporaneo sulla porta {DEMO_PORT}...")
    run([
        str(pg_ctl), "start",
        "-D", str(data_dir),
        "-l", str(log_file),
        "-w", "-t", "30",
        "-o", f"-p {DEMO_PORT} -h 127.0.0.1",
    ])

    if not wait_ready(pg_bin):
        print("ERRORE: PostgreSQL non risponde dopo l'avvio.", file=sys.stderr)
        sys.exit(1)
    print("  Server pronto.")

    try:
        # --- 4. Crea ruolo e database ---
        print(f"\n[4/6] Creazione ruolo '{DEMO_ROLE}' e database '{DEMO_DB_NAME}'...")
        run_psql(pg_bin,
            f"DO $$ BEGIN "
            f"  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname='{DEMO_ROLE}') THEN "
            f"    CREATE ROLE {DEMO_ROLE} LOGIN PASSWORD '{DEMO_ROLE_PWD}'; "
            f"  END IF; "
            f"END $$;")

        # Crea il DB se non esiste
        result = subprocess.run([
            str(_exe(pg_bin, "psql")),
            "-h", "127.0.0.1", "-p", str(DEMO_PORT),
            "-U", "postgres",
            "-d", "postgres",
            "-tc", f"SELECT 1 FROM pg_database WHERE datname='{DEMO_DB_NAME}'",
        ], capture_output=True, text=True)

        if "1" not in result.stdout:
            run_psql(pg_bin, f"CREATE DATABASE {DEMO_DB_NAME} OWNER postgres ENCODING 'UTF8';")
        else:
            print(f"  Database '{DEMO_DB_NAME}' già esistente.")

        # Permessi per demo_user
        run_psql(pg_bin,
            f"GRANT CONNECT ON DATABASE {DEMO_DB_NAME} TO {DEMO_ROLE};",
            dbname=DEMO_DB_NAME)

        # --- 5. Schema, procedure e dati demo ---
        print(f"\n[5/6] Esecuzione script SQL...")
        for sql_file in SQL_SCRIPTS:
            if sql_file.exists():
                print(f"  -> {sql_file.name}")
                run_psql_file(pg_bin, sql_file, DEMO_DB_NAME)
            else:
                print(f"  ATTENZIONE: {sql_file} non trovato, saltato.")

        # Grant su tabelle create dagli script
        run_psql(pg_bin,
            f"GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO {DEMO_ROLE}; "
            f"GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO {DEMO_ROLE};",
            dbname=DEMO_DB_NAME)

        # --- 6. Utente applicativo demo ---
        print(f"\n[6/6] Creazione utente applicativo '{DEMO_APP_USER}'...")
        create_app_demo_user(pg_bin)

    finally:
        # --- Ferma il server ---
        print("\n  Arresto server PostgreSQL temporaneo...")
        subprocess.run(
            [str(pg_ctl), "stop", "-D", str(data_dir), "-m", "fast"],
            capture_output=True,
        )

    # Rimuove postmaster.pid per portabilità (non deve essere presente al primo avvio)
    pid_file = data_dir / "postmaster.pid"
    if pid_file.exists():
        pid_file.unlink()
        print("  Rimosso postmaster.pid.")

    print(f"\n{'='*60}")
    print(f" demo_data/ pronta in: {data_dir}")
    print(f" Dimensione: {sum(f.stat().st_size for f in data_dir.rglob('*') if f.is_file()) // 1024 // 1024} MB")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
