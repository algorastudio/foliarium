"""
tests/unit/test_a_capo_linux.py
===============================
Gli script e i file di configurazione che girano dentro i container Linux
devono avere gli a capo Unix (LF) anche quando il repository è scaricato
con git per Windows.

Git per Windows, con l'impostazione più comune (``core.autocrlf=true``),
converte gli a capo in CRLF. Un ``init.sh`` così, copiato nell'immagine del
database, non parte: la riga ``#!/bin/bash\\r`` cerca un interprete che non
esiste («cannot execute: required file not found»), l'inizializzazione si
ferma e ``demo.sh crea`` fallisce con «container db is unhealthy». È
successo davvero provando la demo da Git Bash.

``.gitattributes`` impone LF a questi file qualunque sia l'impostazione di
chi scarica. Qui si interroga git stesso (``git check-attr``), che è ciò
che decide al momento del checkout.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest


pytestmark = pytest.mark.unit

RADICE = Path(__file__).resolve().parents[2]


def _file_versionati(*modelli: str) -> list[str]:
    esito = subprocess.run(
        ["git", "ls-files", "--", *modelli],
        cwd=RADICE, capture_output=True, text=True, check=True,
    )
    return [riga for riga in esito.stdout.splitlines() if riga]


def _eol(percorsi: list[str]) -> dict[str, str]:
    """Valore dell'attributo «eol» per ogni percorso, secondo git."""
    esito = subprocess.run(
        ["git", "check-attr", "eol", "--", *percorsi],
        cwd=RADICE, capture_output=True, text=True, check=True,
    )
    valori = {}
    for riga in esito.stdout.splitlines():
        percorso, _, valore = riga.rsplit(": ", 2)
        valori[percorso] = valore
    return valori


@pytest.fixture(autouse=True)
def _serve_git():
    if shutil.which("git") is None or not (RADICE / ".git").exists():
        pytest.skip("serve una copia git del repository")


def test_gli_script_della_shell_restano_con_a_capo_linux():
    script = _file_versionati("*.sh")
    assert "docker/postgres/init.sh" in script
    valori = _eol(script)
    sbagliati = {p: v for p, v in valori.items() if v != "lf"}
    assert not sbagliati, sbagliati


def test_i_file_che_finiscono_nei_container_restano_con_a_capo_linux():
    # Caddyfile, file .desktop, configurazioni, compose: letti dentro i
    # container o da Docker. Nessuno ha bisogno degli a capo di Windows.
    file_docker = _file_versionati("docker/")
    assert "docker/demo/Caddyfile" in file_docker
    valori = _eol(file_docker)
    sbagliati = {p: v for p, v in valori.items() if v != "lf"}
    assert not sbagliati, sbagliati


def test_gli_script_di_windows_non_sono_toccati():
    # I .bat girano su Windows: imporre LF non serve, e non si cambia ciò
    # che funziona.
    script_bat = _file_versionati("*.bat")
    assert script_bat
    valori = _eol(script_bat)
    assert all(v != "lf" for v in valori.values()), valori
