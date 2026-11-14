"""
tests/unit/test_spec_manuale.py
===============================
foliarium.spec deve impacchettare il manuale in linea.

HelpViewerDialog legge i .md da ``BASE_DIR/docs`` e la navigazione da
``BASE_DIR/mkdocs.yml``; nel bundle PyInstaller ``BASE_DIR`` e' ``_internal/``.
Se lo spec non li mette in ``datas``, nel programma installato Aiuto ->
Manuale e F1 si aprono vuoti, e nessun altro test se ne accorge: girano
tutti dai sorgenti, dove docs/ c'e' sempre.

Lo spec viene eseguito con Analysis/PYZ/EXE/COLLECT finti che si limitano a
registrare ``datas``: il test non richiede PyInstaller e non costruisce nulla.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

pytestmark = pytest.mark.unit

RADICE = Path(__file__).resolve().parents[2]
SPEC = RADICE / "foliarium.spec"
DOCS = RADICE / "docs"


def _datas_dello_spec() -> list:
    catturati: dict = {}

    def _analysis(scripts, **kwargs):
        catturati.update(kwargs)
        return SimpleNamespace(pure=[], zipped_data=[], scripts=[],
                               binaries=[], zipfiles=[], datas=[])

    def _niente(*_args, **_kwargs):
        return SimpleNamespace()

    namespace = {
        "__name__": "__main__",
        "SPECPATH": str(RADICE),
        "Analysis": _analysis,
        "PYZ": _niente,
        "EXE": _niente,
        "COLLECT": _niente,
    }
    # Lo spec e' Python: PyInstaller lo esegue esattamente cosi'.
    exec(compile(SPEC.read_text(encoding="utf-8"), str(SPEC), "exec"), namespace)  # noqa: S102
    return catturati["datas"]


def _percorsi_nel_bundle(datas) -> set:
    """Percorsi (relativi a _internal/) dei file che finiscono nel bundle.

    Una voce di datas puo' essere un file o una cartella intera: il test
    guarda il risultato, non il modo in cui lo spec lo esprime.
    """
    percorsi = set()
    for sorgente, destinazione in datas:
        src = Path(sorgente)
        if not src.is_absolute():
            src = RADICE / src
        dest = Path(destinazione)
        if src.is_dir():
            for f in src.rglob("*"):
                if f.is_file():
                    percorsi.add((dest / f.relative_to(src)).as_posix())
        elif src.is_file():
            percorsi.add((dest / src.name).as_posix())
    return percorsi


@pytest.fixture(scope="module")
def bundle() -> set:
    return _percorsi_nel_bundle(_datas_dello_spec())


def _pagine_della_nav(voci) -> list:
    pagine = []
    for voce in voci:
        if isinstance(voce, str):
            pagine.append(voce)
        elif isinstance(voce, dict):
            for valore in voce.values():
                if isinstance(valore, str):
                    pagine.append(valore)
                elif isinstance(valore, list):
                    pagine.extend(_pagine_della_nav(valore))
    return pagine


def test_mkdocs_yml_accanto_a_docs(bundle):
    # help_viewer lo cerca in DOCS_DIR.parent, cioe' alla radice di _internal/.
    assert "mkdocs.yml" in bundle


def test_tutte_le_pagine_del_manuale_sono_nel_bundle(bundle):
    attese = {
        f"docs/{md.relative_to(DOCS).as_posix()}"
        for md in DOCS.rglob("*.md")
        if md.relative_to(DOCS).parts[0] != "internal"
    }
    assert attese, "docs/ non contiene pagine: il test non verificherebbe nulla"
    assert sorted(attese - bundle) == []


def test_ogni_voce_della_navigazione_e_nel_bundle(bundle):
    cfg = yaml.safe_load((RADICE / "mkdocs.yml").read_text(encoding="utf-8"))
    pagine = _pagine_della_nav(cfg["nav"])
    assert pagine
    assert sorted(p for p in pagine if f"docs/{p}" not in bundle) == []


def test_docs_internal_non_e_nel_bundle(bundle):
    # Documenti di progetto, non destinati ai clienti.
    assert sorted(p for p in bundle if p.startswith("docs/internal/")) == []
