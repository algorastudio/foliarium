"""
tests/unit/test_docker_db_init.py
=================================
L'inizializzazione del database nei container (`docker/postgres/init.sh`)
deve applicare gli stessi script, nello stesso ordine, dell'installer
(`setup_database.SQL_SCRIPTS`).

L'elenco e' duplicato di proposito: estrarlo in un file comune toccherebbe
il percorso dell'installer Windows. Questo test e' cio' che impedisce ai
due elenchi di divergere in silenzio, come era gia' successo: `init.sh`
era rimasto ai nomi precedenti la riorganizzazione in sottocartelle.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

import setup_database as sdb


pytestmark = pytest.mark.unit

RADICE = Path(__file__).resolve().parents[2]
INIT = RADICE / "docker" / "postgres" / "init.sh"
SQL = RADICE / "sql_scripts"


def _array(nome: str) -> list[str]:
    """Percorsi elencati nell'array Bash `NOME=( ... )` di init.sh."""
    testo = INIT.read_text(encoding="utf-8")
    corpo = re.search(rf"^{nome}=\((.*?)\)", testo, re.S | re.M).group(1)
    return re.findall(r'"([^"]+\.sql)"', corpo)


def _script_in_init() -> list[str]:
    return _array("SCRIPTS")


def test_elenco_coincide_con_setup_database():
    assert _script_in_init() == sdb.SQL_SCRIPTS


def test_ogni_script_esiste():
    previsti = _script_in_init() + [
        sdb.BOOTSTRAP_ADMIN_SCRIPT,
        "demo/demo_user.sql",
        "demo/demo_data.sql",
    ]
    for rel in previsti:
        assert (SQL / rel).is_file(), rel


def test_bootstrap_admin_riceve_la_password():
    # Senza `-v admin_password=...` lo script di bootstrap esce prima
    # dell'INSERT e l'utente non viene creato.
    testo = INIT.read_text(encoding="utf-8")
    assert sdb.BOOTSTRAP_ADMIN_SCRIPT in testo
    assert "admin_password=" in testo


def test_utente_demo_riceve_la_password():
    testo = INIT.read_text(encoding="utf-8")
    assert "demo/demo_user.sql" in testo
    assert "demo_password=" in testo


class TestScriptDaRipetere:
    """
    `functions/06_audit.sql` crea una vista e una chiave esterna su
    `catasto.utente`, tabella che nasce in `admin/01_users.sql`: nell'elenco
    canonico viene DOPO. L'installer esegue psql senza ON_ERROR_STOP, quindi
    quelle due istruzioni falliscono in silenzio. `init.sh` e' rigoroso:
    applica lo script al suo posto tollerando l'errore, poi lo ripete alla
    fine, quando la tabella esiste.
    """

    def test_sono_dichiarati(self):
        assert _array("DA_RIPETERE") == ["functions/06_audit.sql"]

    def test_appartengono_all_elenco_canonico(self):
        assert set(_array("DA_RIPETERE")) <= set(sdb.SQL_SCRIPTS)

    def test_la_ripetizione_serve_ancora(self):
        # Se un giorno l'ordine dell'installer viene corretto, questo test
        # fallisce: e' il segnale per togliere DA_RIPETERE da init.sh.
        ordine = sdb.SQL_SCRIPTS
        assert ordine.index("functions/06_audit.sql") < ordine.index("admin/01_users.sql")
        audit = (SQL / "functions" / "06_audit.sql").read_text(encoding="utf-8")
        assert "catasto.utente" in audit
