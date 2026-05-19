#!/usr/bin/env python3
"""
bin/release.py — Helper CLI per preparare una nuova release Foliarium.

Six-hats post-piano opzione 3 (release process tag-based).

Il job `create-release` in `.github/workflows/pipeline_foliarium.yml`
si attiva automaticamente quando viene pushato un tag `X.Y.Z` o
`vX.Y.Z` e:

  1. Aspetta i build job (windows/demo/unified/linux/macos).
  2. Estrae le note di release dalla sezione `## v<version>` di
     `docs/riferimento/changelog.md`.
  3. Crea la GitHub Release con asset + checksum SHA-256.

Questo script aiuta a preparare il changelog PRIMA del tag:

    # Genera la bozza della prossima sezione changelog
    python bin/release.py draft

    # Mostra la versione attuale + suggerisce la prossima
    python bin/release.py version

    # Crea il tag git locale (richiede conferma)
    python bin/release.py tag 1.0.2

Lo script NON modifica il changelog automaticamente: stampa la bozza
su stdout, l'utente la incolla nel file e la edita prima del tag.

Convenzione: prefissi commit nello stile conventional commits
(`feat:`, `fix:`, `refactor:`, `test:`, `docs:`, `ci:`, `chore:`,
`style:`, `perf:`) vengono raggruppati per tipo nella bozza.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path
from typing import Dict, List, Optional, Tuple


PROJECT_ROOT = Path(__file__).resolve().parent.parent
CHANGELOG = PROJECT_ROOT / "docs" / "riferimento" / "changelog.md"
CONFIG_PY = PROJECT_ROOT / "config.py"


# Mappa prefisso commit → titolo sezione changelog
COMMIT_GROUPS: Dict[str, str] = {
    "feat":     "Funzionalita' nuove",
    "fix":      "Bug fix",
    "refactor": "Refactor",
    "perf":     "Performance",
    "test":     "Test",
    "docs":     "Documentazione",
    "ci":       "CI/CD",
    "style":    "Style / lint",
    "chore":    "Manutenzione",
    "build":    "Build",
    "revert":   "Revert",
}

# Ordine di display
GROUP_ORDER: List[str] = [
    "feat", "fix", "refactor", "perf",
    "test", "docs", "ci", "style", "chore", "build", "revert", "_other",
]


def _run(cmd: List[str]) -> str:
    """Esegue un comando git e ritorna stdout (stripped). Solleva su errore."""
    result = subprocess.run(
        cmd, cwd=PROJECT_ROOT, capture_output=True, text=True, check=False,
    )
    if result.returncode != 0:
        print(f"ERRORE: {' '.join(cmd)} fallito:", file=sys.stderr)
        print(result.stderr, file=sys.stderr)
        sys.exit(2)
    return result.stdout.strip()


def _get_current_version() -> str:
    """Legge APP_VERSION da config.py."""
    if not CONFIG_PY.is_file():
        return "?.?.?"
    text = CONFIG_PY.read_text(encoding="utf-8")
    m = re.search(r'^APP_VERSION\s*=\s*["\']([^"\']+)["\']', text, re.MULTILINE)
    return m.group(1) if m else "?.?.?"


def _get_last_tag() -> Optional[str]:
    """Ritorna l'ultimo tag annotato o None se non ce ne sono."""
    try:
        result = subprocess.run(
            ["git", "describe", "--tags", "--abbrev=0"],
            cwd=PROJECT_ROOT, capture_output=True, text=True, check=False,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except Exception:
        pass
    return None


def _suggest_next_version(current: str) -> str:
    """Bump patch della versione corrente. Es. 1.0.1 → 1.0.2."""
    parts = current.split(".")
    if len(parts) >= 3 and parts[-1].isdigit():
        parts[-1] = str(int(parts[-1]) + 1)
        return ".".join(parts)
    return current + "+1"


_COMMIT_PREFIX_RE = re.compile(
    r"^(?P<type>feat|fix|refactor|perf|test|docs|ci|style|chore|build|revert)"
    r"(?:\([^)]*\))?:\s*(?P<msg>.+)$",
    re.IGNORECASE,
)


def _classify_commits(since_ref: Optional[str]) -> Dict[str, List[str]]:
    """Ritorna { tipo: [messaggio, ...] } per i commit da since_ref a HEAD.

    Filtra fuori i merge commit (`Merge pull request ...`)."""
    if since_ref:
        range_spec = f"{since_ref}..HEAD"
    else:
        # Niente tag precedente: prendi tutti
        range_spec = "HEAD"

    log = _run(["git", "log", range_spec, "--no-merges", "--pretty=format:%s"])
    if not log.strip():
        return {}

    groups: Dict[str, List[str]] = defaultdict(list)
    for line in log.splitlines():
        m = _COMMIT_PREFIX_RE.match(line.strip())
        if m:
            t = m.group("type").lower()
            groups[t].append(m.group("msg").strip())
        else:
            groups["_other"].append(line.strip())
    return groups


def _format_changelog_section(version: str, groups: Dict[str, List[str]]) -> str:
    """Costruisce la sezione markdown della release."""
    today = date.today().isoformat()
    lines: List[str] = []
    lines.append(f"## v{version} — {today}")
    lines.append("")
    lines.append("<!-- Bozza generata da bin/release.py. Editare manualmente"
                 " prima del tag git: accorpare item simili, scrivere note"
                 " di alto livello, rimuovere il rumore. -->")
    lines.append("")

    for group in GROUP_ORDER:
        items = groups.get(group, [])
        if not items:
            continue
        title = COMMIT_GROUPS.get(group, "Altri commit")
        lines.append(f"### {title}")
        lines.append("")
        for msg in items:
            # Trasforma in bullet markdown
            lines.append(f"- {msg}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def cmd_version(args) -> int:
    current = _get_current_version()
    last_tag = _get_last_tag()
    suggested = _suggest_next_version(current)
    print(f"\nVersione attuale (config.py APP_VERSION): {current}")
    print(f"Ultimo tag git:                            {last_tag or '(nessuno)'}")
    print(f"Bump patch suggerito:                      {suggested}\n")
    return 0


def cmd_draft(args) -> int:
    last_tag = _get_last_tag()
    if not last_tag and not args.force:
        print("ATTENZIONE: nessun tag precedente trovato.")
        print("Lo script genererebbe la bozza con TUTTO lo storico — uso --force"
              " se davvero questo e' quello che vuoi.")
        return 2

    groups = _classify_commits(last_tag)
    if not groups:
        print(f"Nessun commit fra {last_tag} e HEAD.")
        return 0

    version = args.version or _suggest_next_version(_get_current_version())
    section = _format_changelog_section(version, groups)

    print(section)
    print("\n--- ISTRUZIONI ---")
    print(f"1. Copia il blocco sopra in {CHANGELOG.relative_to(PROJECT_ROOT)}")
    print(f"2. Edita: accorpa item simili, scrivi note di alto livello")
    print(f"3. Aggiorna APP_VERSION in config.py a {version}")
    print(f"4. Commit + push:  git commit -am 'release: v{version}'")
    print(f"5. Crea il tag:    python bin/release.py tag {version}")
    return 0


def cmd_tag(args) -> int:
    version = args.version
    if not re.match(r"^v?\d+\.\d+\.\d+$", version):
        print(f"ERRORE: '{version}' non e' una versione SemVer valida (X.Y.Z).",
              file=sys.stderr)
        return 2

    # Normalizza: il workflow accetta sia "1.0.2" che "v1.0.2"
    tag = version if version.startswith("v") else version

    # Sanity check: stiamo sul branch giusto?
    branch = _run(["git", "rev-parse", "--abbrev-ref", "HEAD"])
    if branch not in ("main", "master"):
        print(f"ATTENZIONE: il branch corrente e' '{branch}', non main/master.")
        if not args.yes:
            answer = input("Proseguire comunque? [y/N] ").strip().lower()
            if answer != "y":
                print("Annullato.")
                return 1

    # Sanity check: la versione e' coerente con config.py?
    config_version = _get_current_version()
    target_clean = version.lstrip("v")
    if config_version != target_clean and not args.yes:
        print(f"ATTENZIONE: config.py APP_VERSION='{config_version}' "
              f"ma stai taggando '{target_clean}'.")
        answer = input("Proseguire comunque? [y/N] ").strip().lower()
        if answer != "y":
            print("Annullato.")
            return 1

    # Crea il tag annotato
    message = f"Foliarium {tag}"
    print(f"Creazione tag annotato '{tag}' ('{message}')…")
    _run(["git", "tag", "-a", tag, "-m", message])
    print(f"\n✓ Tag '{tag}' creato.")
    print(f"\nProssimo step:  git push origin {tag}")
    print(f"  → triggera il workflow create-release su GitHub Actions.\n")
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("version", help="Mostra versione attuale + suggerita")

    p_draft = sub.add_parser(
        "draft", help="Genera bozza changelog dai commit dall'ultimo tag",
    )
    p_draft.add_argument(
        "--version", help="Versione target (default: bump patch di APP_VERSION)",
    )
    p_draft.add_argument(
        "--force", action="store_true",
        help="genera la bozza anche se non esistono tag precedenti",
    )

    p_tag = sub.add_parser("tag", help="Crea il tag git per la release")
    p_tag.add_argument("version", help="Versione (es. 1.0.2 o v1.0.2)")
    p_tag.add_argument(
        "--yes", "-y", action="store_true",
        help="non chiedere conferma (CI / scripting)",
    )

    args = parser.parse_args(argv)
    if args.cmd == "version":
        return cmd_version(args)
    if args.cmd == "draft":
        return cmd_draft(args)
    if args.cmd == "tag":
        return cmd_tag(args)
    return 2


if __name__ == "__main__":
    sys.exit(main())
