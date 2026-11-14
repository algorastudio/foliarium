"""
tests/unit/test_versione_coerente.py
====================================
Il numero di versione del programma compare in più file, e ciascuno finisce
in un posto diverso:

- ``config.APP_VERSION``: mostrato nel programma e confrontato con l'ultima
  release di GitHub dall'aggiornamento automatico;
- ``Foliarium_Installer.iss`` (``MyAppVersion``): nome del file
  dell'installer e versione registrata da Windows;
- ``version.txt``: proprietà di ``Foliarium.exe`` (Esplora risorse →
  Proprietà → Dettagli);
- ``mkdocs.yml``: titolo del manuale;
- il changelog: il job ``create-release`` della pipeline ne estrae la
  sezione ``## vX.Y.Z`` come note della release.

La procedura di rilascio aggiornava solo ``config.py``: per questo
``version.txt`` era rimasto alla 1.0.1 mentre il programma diceva 1.0.2.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest


pytestmark = pytest.mark.unit

RADICE = Path(__file__).resolve().parents[2]


def _leggi(nome: str) -> str:
    return (RADICE / nome).read_text(encoding="utf-8")


def _versione_app() -> str:
    trovata = re.search(r'^APP_VERSION\s*=\s*"([^"]+)"', _leggi("config.py"), re.M)
    assert trovata, "APP_VERSION non trovata in config.py"
    return trovata.group(1)


def _tupla(versione: str) -> tuple[int, int, int, int]:
    maggiore, minore, correzione = (int(parte) for parte in versione.split("."))
    return (maggiore, minore, correzione, 0)


def test_la_versione_ha_la_forma_attesa():
    assert re.fullmatch(r"\d+\.\d+\.\d+", _versione_app())


def test_l_installer_ha_la_stessa_versione():
    trovata = re.search(r'#define MyAppVersion "([^"]+)"', _leggi("Foliarium_Installer.iss"))
    assert trovata and trovata.group(1) == _versione_app()


def test_le_proprieta_dell_eseguibile_hanno_la_stessa_versione():
    testo = _leggi("version.txt")
    versione = _versione_app()
    attesa = str(_tupla(versione)).replace(" ", "")
    for campo in ("filevers", "prodvers"):
        trovata = re.search(rf"{campo}=(\([^)]*\))", testo)
        assert trovata and trovata.group(1).replace(" ", "") == attesa, campo
    for campo in ("FileVersion", "ProductVersion"):
        trovata = re.search(rf"StringStruct\('{campo}', '([^']+)'\)", testo)
        assert trovata and trovata.group(1) == versione, campo


def test_il_titolo_del_manuale_ha_la_stessa_versione():
    trovata = re.search(r"^site_name:.*?(\d+\.\d+\.\d+)\s*$", _leggi("mkdocs.yml"), re.M)
    assert trovata and trovata.group(1) == _versione_app()


def test_il_changelog_ha_la_sezione_della_versione():
    # Stessa regola del job create-release: "^## v<versione> " seguito da
    # uno spazio. Senza, la release esce con un testo generico.
    versione = re.escape(_versione_app())
    assert re.search(rf"^## v{versione} ", _leggi("docs/riferimento/changelog.md"), re.M)
