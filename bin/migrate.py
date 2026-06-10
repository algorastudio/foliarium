#!/usr/bin/env python3
"""
bin/migrate.py — CLI minimale per applicare/ispezionare migrazioni SQL.

Six-hats analisi D.12. Sostituisce l'approccio attuale (script SQL
applicati manualmente + `db/base.py::_apply_pending_schema_migrations`
hardcoded) con un framework leggero versionato basato sulla tabella
`catasto.schema_version`.

NON sostituisce alembic — e' un sistema lean per uso interno foliarium.
Pensato per:
  - tracciare cosa e' stato applicato (vs idempotenza best-effort)
  - applicare nuove migrazioni in ordine, una volta sola
  - mostrare lo stato dello schema con un comando

Esempi:

    # Mostra le migrazioni applicate/pendenti
    python bin/migrate.py status

    # Applica tutte le migrazioni pendenti (in ordine alfabetico)
    python bin/migrate.py up

    # Dry-run: mostra cosa applicherebbe senza eseguire
    python bin/migrate.py up --dry-run

    # Applica solo una migrazione specifica
    python bin/migrate.py up --file 19_create_v_audit_dettagliato.sql

Configurazione: usa le stesse env DB_HOST/USER/PASS/NAME/PORT
dell'applicazione. Lo script si auto-bootstrap creando
sql_scripts/migrations/00_schema_version_table.sql al primo run.

Convenzione naming: `<numero|nome>_descrizione.sql` (zero-padded per
ordinamento alfabetico). Es. `19_create_v_audit_dettagliato.sql`,
`20_add_indici_geografici.sql`, ...
"""

from __future__ import annotations

import argparse
import hashlib
import os
import sys
from pathlib import Path
from typing import List, Optional, Set, Tuple


MIGRATIONS_DIR = Path(__file__).resolve().parent.parent / "sql_scripts" / "migrations"
BOOTSTRAP_FILE = "00_schema_version_table.sql"


def _db_params() -> dict:
    return {
        "host": os.environ.get("DB_HOST", "localhost"),
        "port": int(os.environ.get("DB_PORT", "5432")),
        "dbname": os.environ.get("DB_NAME", "catasto_storico"),
        "user": os.environ.get("DB_USER", "postgres"),
        "password": os.environ.get("DB_PASS", ""),
    }


def _connect():
    """Apre connessione psycopg2 (lazy import per non forzare la dep in test)."""
    try:
        import psycopg2
    except ImportError:
        print("ERRORE: psycopg2 non installato. pip install psycopg2-binary",
              file=sys.stderr)
        sys.exit(2)
    return psycopg2.connect(**_db_params())


def _list_migration_files() -> List[Path]:
    """Tutti i file .sql in sql_scripts/migrations/, ordinati."""
    if not MIGRATIONS_DIR.is_dir():
        return []
    return sorted(MIGRATIONS_DIR.glob("*.sql"))


def _file_checksum(path: Path) -> str:
    """SHA256 dei bytes del file (12 caratteri abbreviati)."""
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()[:12]


def _ensure_schema_version_table(conn) -> None:
    """Applica il bootstrap se la tabella non esiste."""
    bootstrap_path = MIGRATIONS_DIR / BOOTSTRAP_FILE
    if not bootstrap_path.is_file():
        print(f"ATTENZIONE: {bootstrap_path} non trovato — skip bootstrap.",
              file=sys.stderr)
        return
    with conn.cursor() as cur:
        cur.execute(
            "SELECT 1 FROM information_schema.tables "
            "WHERE table_schema = 'catasto' AND table_name = 'schema_version'"
        )
        if cur.fetchone():
            return
    print(f"  → bootstrap: {BOOTSTRAP_FILE}")
    with conn.cursor() as cur:
        cur.execute(bootstrap_path.read_text(encoding="utf-8"))
    conn.commit()


def _applied_filenames(conn) -> Set[str]:
    with conn.cursor() as cur:
        cur.execute("SELECT filename FROM catasto.schema_version")
        return {row[0] for row in cur.fetchall()}


def cmd_status(args) -> int:
    """Mostra applicate vs pendenti."""
    files = _list_migration_files()
    if not files:
        print(f"Nessun file .sql in {MIGRATIONS_DIR}.")
        return 0

    with _connect() as conn:
        _ensure_schema_version_table(conn)
        applied = _applied_filenames(conn)

    print(f"\nMigrazioni in {MIGRATIONS_DIR.relative_to(Path.cwd()) if MIGRATIONS_DIR.is_relative_to(Path.cwd()) else MIGRATIONS_DIR}:\n")
    for f in files:
        flag = "✓" if f.name in applied else "·"
        status_lbl = "applicata" if f.name in applied else "PENDENTE"
        print(f"  {flag} {f.name:<55s} {status_lbl}")
    print(f"\nTotale: {len(applied)}/{len(files)} applicate.\n")
    return 0


def _apply_file(conn, path: Path, dry_run: bool) -> Tuple[bool, Optional[str]]:
    """Esegue lo script SQL + registra in schema_version. Ritorna (ok, error_msg)."""
    sql = path.read_text(encoding="utf-8")
    checksum = _file_checksum(path)
    if dry_run:
        print(f"  [dry-run] applicherebbe {path.name} (checksum {checksum})")
        return True, None
    try:
        with conn.cursor() as cur:
            cur.execute(sql)
            # Registra solo se non e' il bootstrap (gia' auto-registrato)
            if path.name != BOOTSTRAP_FILE:
                cur.execute(
                    "INSERT INTO catasto.schema_version (filename, checksum) "
                    "VALUES (%s, %s) ON CONFLICT (filename) DO NOTHING",
                    (path.name, checksum),
                )
        conn.commit()
        return True, None
    except Exception as e:
        conn.rollback()
        return False, str(e)


def cmd_up(args) -> int:
    """Applica le migrazioni pendenti."""
    files = _list_migration_files()
    if not files:
        print(f"Nessun file .sql in {MIGRATIONS_DIR}.")
        return 0

    with _connect() as conn:
        _ensure_schema_version_table(conn)
        applied = _applied_filenames(conn)

        if args.file:
            target = MIGRATIONS_DIR / args.file
            if not target.is_file():
                print(f"ERRORE: {target} non trovato.", file=sys.stderr)
                return 2
            files = [target]

        pending = [f for f in files if f.name not in applied]
        if not pending:
            print("Nessuna migrazione pendente.")
            return 0

        print(f"\n{len(pending)} migrazione/i pendente/i:\n")
        for f in pending:
            print(f"  → {f.name}")
            ok, err = _apply_file(conn, f, args.dry_run)
            if not ok:
                print(f"    ✗ ERRORE: {err}", file=sys.stderr)
                return 1
            elif not args.dry_run:
                print("    ✓ applicata")
    print()
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("status", help="Mostra migrazioni applicate vs pendenti")

    p_up = sub.add_parser("up", help="Applica migrazioni pendenti")
    p_up.add_argument("--dry-run", action="store_true",
                      help="non eseguire, mostra solo cosa farebbe")
    p_up.add_argument("--file", help="applica solo questo file specifico")

    args = parser.parse_args(argv)
    if args.cmd == "status":
        return cmd_status(args)
    if args.cmd == "up":
        return cmd_up(args)
    return 2


if __name__ == "__main__":
    sys.exit(main())
