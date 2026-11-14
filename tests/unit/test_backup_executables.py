"""
tests/unit/test_backup_executables.py
=====================================
Il backup cerca gli strumenti di PostgreSQL (pg_dump, pg_restore, psql,
dropdb, createdb) con `shutil.which`. I nomi erano scritti con il suffisso
`.exe`, che fuori da Windows non esiste: su Linux il backup dalla GUI non
trovava mai nulla, anche con gli strumenti nel PATH.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

import pytest

from db.backup import DBBackupMixin, _pg_tool_name


pytestmark = pytest.mark.unit

SORGENTE = Path(__file__).resolve().parents[2] / "db" / "backup.py"


def test_su_windows_aggiunge_exe():
    assert _pg_tool_name("pg_dump", windows=True) == "pg_dump.exe"


def test_fuori_da_windows_nome_nudo():
    assert _pg_tool_name("pg_dump", windows=False) == "pg_dump"


def test_default_segue_la_piattaforma():
    atteso = "psql.exe" if os.name == "nt" else "psql"
    assert _pg_tool_name("psql") == atteso


@pytest.mark.skipif(os.name == "nt", reason="verifica il caso non Windows")
def test_resolve_trova_eseguibile_senza_suffisso(tmp_path, monkeypatch):
    finto = tmp_path / "pg_dump"
    finto.write_text("#!/bin/sh\n", encoding="utf-8")
    finto.chmod(0o755)
    monkeypatch.setenv("PATH", str(tmp_path))

    mixin = DBBackupMixin.__new__(DBBackupMixin)
    mixin.logger = logging.getLogger("test_backup_executables")

    trovato = mixin._resolve_executable_path(None, _pg_tool_name("pg_dump"))

    assert trovato == str(finto)


def test_nessun_exe_letterale_nella_classe():
    # Il suffisso deve stare in un punto solo, la helper: un nome scritto
    # a mano con `.exe` in un metodo riporterebbe il difetto su Linux.
    classe = SORGENTE.read_text(encoding="utf-8").split("class DBBackupMixin", 1)[1]
    assert '.exe"' not in classe
    assert ".exe'" not in classe
