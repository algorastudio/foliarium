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
        "demo/demo_statistiche.sql",
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


class TestOrdineDegliScript:
    """
    `functions/06_audit.sql` crea una vista e una chiave esterna su
    `catasto.utente`, tabella che nasce in `admin/01_users.sql`: quest'ultimo
    deve precederlo. Per un periodo l'elenco li aveva nell'ordine inverso:
    l'installer, che eseguiva psql senza ON_ERROR_STOP, non creava ne' la
    vista ne' la chiave esterna e non lo segnalava; `init.sh` aggirava il
    difetto applicando lo script due volte.

    Questi test sorvegliano l'ordine sulla carta. La prova vera, su un
    PostgreSQL reale, e' tests/integration/test_schema_database_nuovo.py.
    """

    def test_gli_utenti_precedono_l_audit(self):
        ordine = sdb.SQL_SCRIPTS
        audit = (SQL / "functions" / "06_audit.sql").read_text(encoding="utf-8")
        # Se un giorno l'audit non dipendesse piu' da `utente`, l'ordine
        # tornerebbe libero e questo test andrebbe tolto, non aggirato.
        assert "catasto.utente" in audit
        assert ordine.index("admin/01_users.sql") < ordine.index("functions/06_audit.sql")

    def test_gli_utenti_seguono_le_funzioni_di_base(self):
        # 01_users.sql aggancia a `utente` il trigger che usa
        # update_modified_column(), definita in functions/01_core.sql.
        ordine = sdb.SQL_SCRIPTS
        utenti = (SQL / "admin" / "01_users.sql").read_text(encoding="utf-8")
        assert "update_modified_column()" in utenti
        assert ordine.index("functions/01_core.sql") < ordine.index("admin/01_users.sql")

    def test_nessuno_script_viene_applicato_due_volte(self):
        assert len(set(sdb.SQL_SCRIPTS)) == len(sdb.SQL_SCRIPTS)
        testo = INIT.read_text(encoding="utf-8")
        assert "DA_RIPETERE" not in testo

    def test_init_non_tollera_errori(self):
        # Ogni invocazione di psql deve fermarsi al primo errore: e' cio'
        # che fa emergere subito uno script fuori posto.
        righe = [
            riga for riga in INIT.read_text(encoding="utf-8").splitlines()
            if re.search(r"\bpsql\b", riga) and not riga.lstrip().startswith("#")
        ]
        assert righe, "init.sh non invoca piu' psql?"
        for riga in righe:
            assert "ON_ERROR_STOP=1" in riga, riga


def test_dopo_il_dataset_si_aggiornano_le_statistiche():
    # Le viste materializzate nascono a tabelle vuote: senza un aggiornamento
    # dopo il caricamento, le pagine di statistica della demo sarebbero vuote
    # e la barra «dati non aggiornati» partirebbe dal 01/01/2000.
    testo = INIT.read_text(encoding="utf-8")
    assert "demo/demo_statistiche.sql" in testo
    assert testo.index("demo/demo_data.sql") < testo.index("demo/demo_statistiche.sql")


def test_il_database_usa_il_fuso_orario_italiano():
    # Applicazione e database devono vedere la stessa ora: le date che il
    # database scrive (accessi, audit) vengono mostrate senza conversione.
    dockerfile = (RADICE / "docker" / "postgres" / "Dockerfile").read_text(encoding="utf-8")
    assert "TZ=Europe/Rome" in dockerfile
