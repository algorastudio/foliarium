#!/usr/bin/env python3
"""
migrate_database.py — Applica le migration SQL su un DB Foliarium esistente.

Scansiona sql_scripts/migrations/*.sql e applica solo quelle non ancora
eseguite, tracciandole in una tabella catasto.schema_migrations.

NON usare su un DB appena creato con setup_database.py: le migration
servono solo a portare un DB già popolato a una versione più recente.
Lo schema fresco di setup_database.py contiene già tutte le feature.

Uso:
  python migrate_database.py --pg-bin auto --postgres-password postgres
  python migrate_database.py --pg-bin auto --postgres-password postgres --list
  python migrate_database.py --pg-bin auto --postgres-password postgres --apply-all
  python migrate_database.py --pg-bin auto --postgres-password postgres --apply add_soft_delete

Opzioni principali:
  --pg-bin PATH|auto     Cartella bin di PostgreSQL ('auto' = ricerca nel PATH)
  --postgres-password    Password del superuser postgres (default: vuota)
  --port                 Porta PostgreSQL (default: 5432)
  --db-name              Nome del database (default: catasto_storico)

Modalità:
  (nessun flag)          Mostra status + chiede conferma per ogni pending
  --list                 Mostra solo status, non applica nulla
  --apply-all            Applica tutte le pending in ordine alfabetico
  --apply NOME           Applica una singola migration specifica
"""
from __future__ import annotations

import argparse
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

DB_NAME_DEFAULT = "catasto_storico"
DEFAULT_PORT = 5432
SYSTEM = platform.system()
EXE = ".exe" if SYSTEM == "Windows" else ""

TRACKING_TABLE_DDL = """
CREATE SCHEMA IF NOT EXISTS catasto;
CREATE TABLE IF NOT EXISTS catasto.schema_migrations (
    name        TEXT PRIMARY KEY,
    applied_at  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    notes       TEXT
);
"""


def log(msg: str) -> None:
    print(f"  {msg}", flush=True)


def find_system_pgbin() -> Path | None:
    """Cerca psql nel PATH o nelle posizioni comuni su Windows."""
    found = shutil.which("psql")
    if found:
        return Path(found).parent
    if SYSTEM == "Windows":
        for ver in range(20, 13, -1):
            for base in [r"C:\Program Files\PostgreSQL", r"C:\Program Files (x86)\PostgreSQL"]:
                candidate = Path(base) / str(ver) / "bin"
                if (candidate / "psql.exe").exists():
                    return candidate
    return None


def psql_exe(pg_bin: Path) -> str:
    return str(pg_bin / f"psql{EXE}")


def psql_query(pg_bin: Path, port: int, db_name: str, password: str,
               sql: str) -> str:
    """Esegue una query e ritorna stdout (senza tabella headers)."""
    env = os.environ.copy()
    env["PGPASSWORD"] = password
    cmd = [psql_exe(pg_bin), "-h", "127.0.0.1", "-p", str(port),
           "-U", "postgres", "-d", db_name, "-tAc", sql]
    r = subprocess.run(cmd, env=env, capture_output=True, text=True, check=True)
    return r.stdout.strip()


def psql_run_file(pg_bin: Path, port: int, db_name: str, password: str,
                  sql_file: Path) -> tuple[bool, str]:
    """Esegue un file SQL via psql con ON_ERROR_STOP. Ritorna (ok, output)."""
    env = os.environ.copy()
    env["PGPASSWORD"] = password
    cmd = [psql_exe(pg_bin), "-h", "127.0.0.1", "-p", str(port),
           "-U", "postgres", "-d", db_name, "-v", "ON_ERROR_STOP=1",
           "-f", str(sql_file)]
    r = subprocess.run(cmd, env=env, capture_output=True, text=True)
    output = (r.stdout or "") + (r.stderr or "")
    return r.returncode == 0, output


def ensure_tracking_table(pg_bin: Path, port: int, db_name: str,
                          password: str) -> bool:
    """Crea catasto.schema_migrations se non esiste."""
    env = os.environ.copy()
    env["PGPASSWORD"] = password
    cmd = [psql_exe(pg_bin), "-h", "127.0.0.1", "-p", str(port),
           "-U", "postgres", "-d", db_name, "-v", "ON_ERROR_STOP=1",
           "-c", TRACKING_TABLE_DDL]
    r = subprocess.run(cmd, env=env, capture_output=True, text=True)
    if r.returncode != 0:
        log(f"ERRORE creazione schema_migrations: {r.stderr}")
        return False
    return True


def get_applied(pg_bin: Path, port: int, db_name: str, password: str) -> set[str]:
    """Ritorna l'insieme dei nomi di migration già applicate."""
    out = psql_query(pg_bin, port, db_name, password,
                     "SELECT name FROM catasto.schema_migrations ORDER BY name;")
    return {line.strip() for line in out.splitlines() if line.strip()}


def list_migrations(install_dir: Path) -> list[Path]:
    """Ritorna i file .sql in sql_scripts/migrations/ ordinati alfabeticamente."""
    mig_dir = install_dir / "sql_scripts" / "migrations"
    if not mig_dir.is_dir():
        return []
    return sorted(mig_dir.glob("*.sql"))


def record_applied(pg_bin: Path, port: int, db_name: str, password: str,
                   name: str) -> None:
    """Inserisce la migration nella tracking table."""
    env = os.environ.copy()
    env["PGPASSWORD"] = password
    cmd = [psql_exe(pg_bin), "-h", "127.0.0.1", "-p", str(port),
           "-U", "postgres", "-d", db_name, "-v", "ON_ERROR_STOP=1",
           "-c", f"INSERT INTO catasto.schema_migrations(name) VALUES ('{name}') "
                 f"ON CONFLICT (name) DO NOTHING;"]
    subprocess.run(cmd, env=env, capture_output=True, text=True, check=True)


def apply_migration(pg_bin: Path, port: int, db_name: str, password: str,
                    sql_file: Path) -> bool:
    """Applica una migration e la registra in tracking."""
    name = sql_file.stem
    log(f"→ Applicando: {sql_file.name}")
    ok, output = psql_run_file(pg_bin, port, db_name, password, sql_file)
    if not ok:
        log(f"ERRORE applicando {sql_file.name}:")
        for line in output.splitlines():
            print(f"    {line}")
        return False
    record_applied(pg_bin, port, db_name, password, name)
    log("   OK — registrata in schema_migrations")
    return True


def show_status(migrations: list[Path], applied: set[str]) -> None:
    """Mostra lo stato di tutte le migration."""
    print(f"\n{'Migration':<40} Status")
    print("-" * 60)
    for f in migrations:
        marker = "✓ applicata" if f.stem in applied else "  pending"
        print(f"  {f.name:<38} {marker}")
    pending_count = sum(1 for f in migrations if f.stem not in applied)
    print(f"\n  Totale: {len(migrations)} migration, {pending_count} pending\n")


def confirm(prompt: str) -> bool:
    """Yes/no prompt; 'y' o 's' o invio = Yes, altro = No."""
    try:
        ans = input(f"{prompt} [Y/n] ").strip().lower()
    except EOFError:
        return False
    return ans in ("", "y", "yes", "s", "si")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Applica migration SQL su un DB Foliarium esistente",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Esempi:\n"
            "  python migrate_database.py --pg-bin auto --postgres-password postgres\n"
            "  python migrate_database.py --pg-bin auto --list\n"
            "  python migrate_database.py --pg-bin auto --apply-all --postgres-password postgres\n"
            "  python migrate_database.py --pg-bin auto --apply add_soft_delete --postgres-password postgres"
        ),
    )
    parser.add_argument("--pg-bin", default="auto",
                        help="Cartella bin di PostgreSQL ('auto' = cerca nel PATH)")
    parser.add_argument("--postgres-password", default="",
                        help="Password del superuser postgres (default: vuota)")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT,
                        help=f"Porta PostgreSQL (default: {DEFAULT_PORT})")
    parser.add_argument("--db-name", default=DB_NAME_DEFAULT,
                        help=f"Nome del database (default: {DB_NAME_DEFAULT})")
    parser.add_argument("--install-dir", default=None,
                        help="Directory del progetto (default: directory di questo script)")
    parser.add_argument("--list", action="store_true",
                        help="Mostra status delle migration senza applicare nulla")
    parser.add_argument("--apply-all", action="store_true",
                        help="Applica tutte le pending senza chiedere conferma")
    parser.add_argument("--apply", default=None, metavar="NOME",
                        help="Applica solo la migration con questo nome (senza .sql)")
    args = parser.parse_args()

    # Risolvi pg_bin
    if args.pg_bin.lower() == "auto":
        pg_bin = find_system_pgbin()
        if pg_bin is None:
            print("ERRORE: PostgreSQL non trovato nel PATH né nelle posizioni standard.")
            return 1
    else:
        pg_bin = Path(args.pg_bin)
    if not (pg_bin / f"psql{EXE}").exists():
        print(f"ERRORE: psql non trovato in '{pg_bin}'")
        return 1

    install_dir = Path(args.install_dir) if args.install_dir else Path(__file__).parent
    install_dir = install_dir.resolve()

    print(f"\n{'='*60}")
    print(f" Foliarium — Gestione Migration ({SYSTEM})")
    print(f"{'='*60}")
    log(f"PostgreSQL bin: {pg_bin}")
    log(f"Database:       {args.db_name} su 127.0.0.1:{args.port}")
    log(f"Migrations:     {install_dir / 'sql_scripts' / 'migrations'}")

    migrations = list_migrations(install_dir)
    if not migrations:
        log("Nessuna migration trovata in sql_scripts/migrations/")
        return 0

    if not ensure_tracking_table(pg_bin, args.port, args.db_name,
                                  args.postgres_password):
        return 1

    try:
        applied = get_applied(pg_bin, args.port, args.db_name,
                              args.postgres_password)
    except subprocess.CalledProcessError as e:
        log(f"ERRORE connessione a '{args.db_name}': {e.stderr or e}")
        log("Verificare --pg-bin, --postgres-password, --db-name.")
        return 1

    show_status(migrations, applied)

    if args.list:
        return 0

    # Modalità --apply NOME
    if args.apply:
        target = next((f for f in migrations if f.stem == args.apply), None)
        if target is None:
            log(f"ERRORE: migration '{args.apply}' non trovata.")
            return 1
        if target.stem in applied:
            log(f"'{args.apply}' è già stata applicata. Skip.")
            return 0
        if apply_migration(pg_bin, args.port, args.db_name,
                           args.postgres_password, target):
            return 0
        return 1

    # Modalità --apply-all o interattiva
    pending = [f for f in migrations if f.stem not in applied]
    if not pending:
        log("Tutte le migration sono già applicate. Nulla da fare.")
        return 0

    success = 0
    failed = 0
    for f in pending:
        if not args.apply_all:
            if not confirm(f"Applicare '{f.name}'?"):
                log(f"Skipped: {f.name}")
                continue
        if apply_migration(pg_bin, args.port, args.db_name,
                           args.postgres_password, f):
            success += 1
        else:
            failed += 1
            log("Interrotto a causa dell'errore. Risolvere prima di proseguire.")
            break

    print(f"\n{'='*60}")
    log(f"Migration applicate con successo: {success}")
    if failed:
        log(f"Migration fallite: {failed}")
    print(f"{'='*60}\n")

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
