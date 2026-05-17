#!/usr/bin/env python3
"""
bin/check_api_drift.py — Rileva drift fra API DB e chiamanti.

Risolve il pattern di bug visto durante lo Sprint 3.9 six-hats: dopo i
rebrand v1.5.0+ alcuni test e widget chiamano metodi DB con nome
rinominato (es. get_partita_by_id → get_partita_details,
get_all_comuni → get_all_comuni_details, ricerca_avanzata_possessori_gui
rimosso, ecc.) senza che AST/syntax check li veda perche' sono accessi
attributo dinamico.

Lo script:
  1. Costruisce l'inventario dei metodi pubblici definiti in db/*.py +
     catasto_db_manager.py + core/*.py (i 3 layer su cui i consumer
     dipendono).
  2. Scansiona tutti i file Python del progetto e estrae le chiamate
     'NAME.metodo(' dove NAME e' uno degli alias noti del DB manager
     (db, db_manager, self.db_manager, clean_db, sample_data['db'],
     self.db, mgr, manager).
  3. Per ogni chiamata, verifica che il metodo esista nell'inventario.
  4. Stampa un report dei drift + ritorna exit code 1 se trovati.

Uso:
    python bin/check_api_drift.py          # report umano
    python bin/check_api_drift.py --quiet  # solo exit code

Pensato per essere eseguito da un pre-commit hook o da CI come gate
non-bloccante per evitare regressioni silenti sui chiamanti.
"""

from __future__ import annotations

import argparse
import ast
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Dict, Iterator, List, Set, Tuple


# Alias dell'oggetto CatastoDBManager nei test/widget. Espandere se il
# codebase introduce nuovi nomi standard.
DB_ALIASES: Set[str] = {
    "db",
    "db_manager",
    "clean_db",
    "manager",
    "mgr",
}

# File da scansionare per inventario API (sorgenti delle classi DB)
INVENTORY_GLOBS: List[str] = [
    "db/*.py",
    "catasto_db_manager.py",
    "core/*.py",
]

# File da scansionare per i chiamanti
CALLERS_GLOBS: List[str] = [
    "tests/**/*.py",
    "gui_main.py",
    "gui_widgets.py",
    "search_widgets.py",
    "partita_workflow_widgets.py",
    "dialogs.py",
    "foliarium/**/*.py",
    "api/**/*.py",
]

# File da escludere dall'inventario (definiscono metodi dummy, non DB)
INVENTORY_EXCLUDE: Set[str] = {
    "db/models.py",  # dataclass, non mixin
}


def collect_method_inventory(project_root: Path) -> Set[str]:
    """Estrae nomi di metodi pubblici e privati definiti in DB / core mixin."""
    inventory: Set[str] = set()
    for pattern in INVENTORY_GLOBS:
        for fp in project_root.glob(pattern):
            if str(fp.relative_to(project_root)) in INVENTORY_EXCLUDE:
                continue
            try:
                tree = ast.parse(fp.read_text(encoding="utf-8"))
            except (SyntaxError, UnicodeDecodeError):
                continue
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    # Includiamo metodi privati (_xxx) ma non dunder (__xxx__)
                    if not (node.name.startswith("__") and node.name.endswith("__")):
                        inventory.add(node.name)
    return inventory


# Pattern di chiamata: <alias>.<metodo>(
# Esempi che matchano:
#   db.aggiungi_comune(
#   self.db_manager.get_partita_details(
#   clean_db.create_possessore(
# Lookbehind `(?<![\w])` evita falsi positivi tipo `_license_manager.X()`
# (matcha 'manager' dentro a un identificatore piu' lungo).
_CALL_RE = re.compile(
    r"(?<![\w])(?:self\.)?(?P<alias>"
    + "|".join(re.escape(a) for a in sorted(DB_ALIASES, key=len, reverse=True))
    + r")\s*\.\s*(?P<method>[a-zA-Z_][a-zA-Z0-9_]*)\s*\("
)

# Pattern per sample_data['db'].method(  → estrarre method
_SAMPLE_DATA_DB_RE = re.compile(
    r"sample_data\[\s*['\"]db['\"]\s*\]\s*\.\s*(?P<method>[a-zA-Z_][a-zA-Z0-9_]*)\s*\("
)


def collect_caller_uses(project_root: Path) -> Dict[str, List[Tuple[Path, int]]]:
    """Ritorna { metodo_chiamato: [(file, lineno), ...] }."""
    uses: Dict[str, List[Tuple[Path, int]]] = defaultdict(list)
    for pattern in CALLERS_GLOBS:
        for fp in project_root.glob(pattern):
            if fp.is_dir():
                continue
            # Skip inventory files (un metodo definito non e' un drift)
            rel = str(fp.relative_to(project_root))
            if any(fp.match(g) for g in INVENTORY_GLOBS):
                continue
            try:
                text = fp.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
            for lineno, line in enumerate(text.splitlines(), start=1):
                # Skip righe di commento o stringhe ovvie (best-effort)
                stripped = line.lstrip()
                if stripped.startswith("#"):
                    continue
                for m in _CALL_RE.finditer(line):
                    uses[m.group("method")].append((fp, lineno))
                for m in _SAMPLE_DATA_DB_RE.finditer(line):
                    uses[m.group("method")].append((fp, lineno))
    return uses


# Falsi positivi noti — metodi che NON sono di CatastoDBManager ma di
# stdlib / Qt che lo script potrebbe matchare per via dell'alias.
FALSE_POSITIVES: Set[str] = {
    # Threading / Qt object methods (qualcuno usa 'manager' come variabile generica)
    "exec", "exec_", "show", "close", "hide", "raise_",
    "deleteLater", "isRunning", "start", "wait", "quit",
    "setStyleSheet", "setObjectName", "setWindowTitle",
    # Comuni metodi Python stdlib su strutture dati
    "copy", "get", "keys", "values", "items", "update",
    "append", "extend", "pop", "remove", "clear",
    "format", "join", "split", "strip", "replace",
}


def find_drifts(
    inventory: Set[str], uses: Dict[str, List[Tuple[Path, int]]],
) -> Dict[str, List[Tuple[Path, int]]]:
    """Ritorna solo le chiamate a metodi non presenti nell'inventario."""
    drifts: Dict[str, List[Tuple[Path, int]]] = {}
    for method, occurrences in uses.items():
        if method in FALSE_POSITIVES:
            continue
        if method in inventory:
            continue
        drifts[method] = occurrences
    return drifts


def format_report(
    drifts: Dict[str, List[Tuple[Path, int]]], project_root: Path,
) -> str:
    if not drifts:
        return "✓ Nessun drift API rilevato fra chiamanti e DB layer.\n"

    lines: List[str] = []
    lines.append(f"✗ Drift API rilevato: {len(drifts)} metodi chiamati ma non definiti.\n")
    for method in sorted(drifts):
        occurrences = drifts[method]
        lines.append(f"\n  {method}  ({len(occurrences)} chiamata{'e' if len(occurrences) != 1 else ''})")
        for fp, lineno in occurrences[:5]:  # max 5 esempi per metodo
            rel = fp.relative_to(project_root)
            lines.append(f"      {rel}:{lineno}")
        if len(occurrences) > 5:
            lines.append(f"      ... e altre {len(occurrences) - 5} occorrenze")
    lines.append("")
    return "\n".join(lines)


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--quiet", action="store_true",
        help="non stampare il report, solo exit code",
    )
    parser.add_argument(
        "--root", type=Path, default=None,
        help="root del progetto (default: rilevata da __file__)",
    )
    args = parser.parse_args(argv)

    project_root = args.root or Path(__file__).resolve().parent.parent
    if not (project_root / "db").is_dir():
        print(f"ERRORE: {project_root} non sembra una root foliarium (manca db/)",
              file=sys.stderr)
        return 2

    inventory = collect_method_inventory(project_root)
    uses = collect_caller_uses(project_root)
    drifts = find_drifts(inventory, uses)

    if not args.quiet:
        print(format_report(drifts, project_root))

    return 1 if drifts else 0


if __name__ == "__main__":
    sys.exit(main())
