"""
tests/integration/test_funzioni_civico.py
=========================================
Le funzioni SQL che mostrano il civico di un immobile lo leggono da
`immobile.numero_civico`.

Dalla v1.7.0 il civico non sta piu' in `localita` ma in `immobile`, e il
tipo di localita' in `localita.tipologia_stradale`: le colonne
`localita.civico` e `localita.tipo_id` non esistono. Tre funzioni degli
script canonici le leggevano ancora e fallivano a ogni chiamata, su ogni
database creato dall'installer:

- `esporta_partita_json`, su cui poggiano le tre esportazioni di una partita
  dalla GUI (JSON, CSV, PDF);
- `genera_report_proprieta`, la pagina Reportistica;
- `ricerca_avanzata_immobili`.

Nessun test se ne accorgeva perche' la pipeline costruisce il database dei
test con i vecchi script numerati e poi applica la migrazione 20, che
corregge solo il report.

Qui il database viene creato con gli script dell'installer
(`setup_database.SQL_SCRIPTS`) fino a `functions/05_reporting.sql`: le tre
funzioni non dipendono dagli script successivi (utenti, audit, backup).

Verifica anche `sql_scripts/migrations/24_fix_funzioni_civico.sql`, che
ripara i database gia' esistenti.

Richiede `psql` nel PATH e un PostgreSQL raggiungibile su 127.0.0.1 come
`postgres` (DB_PORT, DB_PASS).
"""

from __future__ import annotations

import contextlib
import json
import os
import shutil
import subprocess
import uuid
from pathlib import Path

import psycopg2
import pytest

import setup_database as sdb
from catasto_db_manager import CatastoDBManager


pytestmark = pytest.mark.integration

RADICE = Path(__file__).resolve().parents[2]
SQL = RADICE / "sql_scripts"
MIGRAZIONE = SQL / "migrations" / "24_fix_funzioni_civico.sql"

# Gli script dell'installer che bastano a queste funzioni.
SCRIPT_NECESSARI = sdb.SQL_SCRIPTS[: sdb.SQL_SCRIPTS.index("functions/05_reporting.sql") + 1]

FUNZIONI = ("esporta_partita_json", "genera_report_proprieta", "ricerca_avanzata_immobili")

IN_CI = os.environ.get("CI") == "true" or os.environ.get("GITHUB_ACTIONS") == "true"


def _non_disponibile(motivo: str):
    """In CI l'assenza del server e' un errore, non un motivo per saltare."""
    if IN_CI:
        pytest.fail(motivo)
    pytest.skip(motivo)


@pytest.fixture(scope="module")
def server():
    host = os.environ.get("DB_HOST", "localhost")
    utente = os.environ.get("DB_USER", "postgres")
    if host not in ("localhost", "127.0.0.1") or utente != "postgres":
        _non_disponibile(
            "il database di prova si crea su 127.0.0.1 come 'postgres' "
            f"(DB_HOST={host}, DB_USER={utente})"
        )
    psql = shutil.which("psql")
    if psql is None:
        _non_disponibile("psql non trovato nel PATH")

    parametri = {
        "host": "127.0.0.1",
        "port": int(os.environ.get("DB_PORT", "5432")),
        "user": "postgres",
        "password": os.environ.get("DB_PASS", "testpassword"),
        "psql": psql,
    }
    try:
        _connetti(parametri, "postgres").close()
    except psycopg2.OperationalError as e:
        _non_disponibile(f"PostgreSQL non raggiungibile: {e}")
    return parametri


def _connetti(server: dict, dbname: str):
    # Lo stesso search_path che CatastoDBManager imposta su ogni connessione:
    # genera_report_proprieta usa nomi di tabella non qualificati.
    conn = psycopg2.connect(
        host=server["host"], port=server["port"], user=server["user"],
        password=server["password"], dbname=dbname,
        options="-c search_path=catasto,public",
    )
    conn.autocommit = True
    return conn


@contextlib.contextmanager
def _cursore(server: dict, dbname: str):
    """Cursore in autocommit; alla fine la connessione viene chiusa."""
    conn = _connetti(server, dbname)
    try:
        with conn.cursor() as cur:
            yield cur
    finally:
        conn.close()


def _psql_file(server: dict, dbname: str, percorso: Path) -> None:
    """Applica un file SQL fermandosi al primo errore."""
    r = subprocess.run(
        [server["psql"], "-X", "-q", "-h", server["host"], "-p", str(server["port"]),
         "-U", server["user"], "-d", dbname, "-v", "ON_ERROR_STOP=1", "-f", str(percorso)],
        env=dict(os.environ, PGPASSWORD=server["password"],
                 PGOPTIONS="-c client_min_messages=error"),
        capture_output=True, text=True,
    )
    assert r.returncode == 0, f"{percorso.name}: {r.stderr}"


def _crea_database(server: dict) -> str:
    nome = f"foliarium_civico_{uuid.uuid4().hex[:10]}"
    with _cursore(server, "postgres") as cur:
        cur.execute(f'CREATE DATABASE "{nome}" ENCODING \'UTF8\' TEMPLATE template0')
    for script in SCRIPT_NECESSARI:
        _psql_file(server, nome, SQL / script)
    return nome


def _elimina_database(server: dict, nome: str) -> None:
    with _cursore(server, "postgres") as cur:
        cur.execute(f'DROP DATABASE IF EXISTS "{nome}" WITH (FORCE)')


def _popola(server: dict, dbname: str) -> dict:
    """
    Una partita con tre immobili in Via Roma: uno al civico 17/A, uno senza
    civico (NULL) e uno con il civico vuoto, come lo puo' lasciare un modulo
    compilato a meta'.
    """
    with _cursore(server, dbname) as cur:
        cur.execute(
            "INSERT INTO catasto.comune (nome, provincia, regione) "
            "VALUES ('Comune Prova', 'SV', 'Liguria') RETURNING id"
        )
        comune_id = cur.fetchone()[0]
        cur.execute(
            "INSERT INTO catasto.localita (comune_id, nome, tipologia_stradale) "
            "VALUES (%s, 'Roma', 'Via') RETURNING id",
            (comune_id,),
        )
        localita_id = cur.fetchone()[0]
        cur.execute(
            "INSERT INTO catasto.partita (comune_id, numero_partita, tipo, stato, data_impianto) "
            "VALUES (%s, 4242, 'principale', 'attiva', DATE '1950-01-01') RETURNING id",
            (comune_id,),
        )
        partita_id = cur.fetchone()[0]
        immobili = {}
        for natura, civico in (("Casa di abitazione", "17/A"), ("Magazzino", None), ("Orto", "")):
            cur.execute(
                "INSERT INTO catasto.immobile (partita_id, localita_id, numero_civico, natura) "
                "VALUES (%s, %s, %s, %s) RETURNING id",
                (partita_id, localita_id, civico, natura),
            )
            immobili[natura] = cur.fetchone()[0]
    return {"comune_id": comune_id, "partita_id": partita_id, "immobili": immobili}


@pytest.fixture(scope="module")
def archivio(server):
    """Database creato dagli script dell'installer, con una partita di prova."""
    nome = _crea_database(server)
    try:
        yield {"dbname": nome, **_popola(server, nome)}
    finally:
        _elimina_database(server, nome)


def _esporta(server: dict, archivio: dict) -> dict:
    with _cursore(server, archivio["dbname"]) as cur:
        cur.execute("SELECT catasto.esporta_partita_json(%s)", (archivio["partita_id"],))
        dati = cur.fetchone()[0]
    return dati if isinstance(dati, dict) else json.loads(dati)


def _report(server: dict, archivio: dict) -> str:
    with _cursore(server, archivio["dbname"]) as cur:
        cur.execute("SELECT catasto.genera_report_proprieta(%s)", (archivio["partita_id"],))
        return cur.fetchone()[0]


def _ricerca(server: dict, archivio: dict) -> dict:
    with _cursore(server, archivio["dbname"]) as cur:
        cur.execute(
            "SELECT id_immobile, localita_nome, civico, localita_tipo "
            "FROM catasto.ricerca_avanzata_immobili(p_comune_id => %s)",
            (archivio["comune_id"],),
        )
        return {r[0]: r[1:] for r in cur.fetchall()}


class TestFunzioniSQL:

    def test_l_esportazione_riporta_il_civico_dell_immobile(self, server, archivio):
        dati = _esporta(server, archivio)

        per_id = {imm["id"]: imm for imm in dati["immobili"]}
        imm = archivio["immobili"]
        assert per_id[imm["Casa di abitazione"]]["civico"] == "17/A"
        assert per_id[imm["Magazzino"]]["civico"] is None
        assert per_id[imm["Casa di abitazione"]]["localita_nome"] == "Roma"
        assert dati["partita"]["numero_partita"] == 4242

    def test_il_report_mostra_il_civico_accanto_alla_localita(self, server, archivio):
        report = _report(server, archivio)

        assert "Localita: Roma, 17/A (Via)" in report
        # Senza civico, o con il civico vuoto, nessuna virgola sospesa.
        assert report.count("Localita: Roma (Via)") == 2
        assert "Roma, (Via)" not in report

    def test_la_ricerca_riporta_civico_e_tipo_di_localita(self, server, archivio):
        righe = _ricerca(server, archivio)

        imm = archivio["immobili"]
        assert righe[imm["Casa di abitazione"]] == ("Roma", "17/A", "Via")
        assert righe[imm["Magazzino"]] == ("Roma", None, "Via")


@pytest.fixture(scope="module")
def gestore(server, archivio):
    """Il gestore del database che usa l'applicazione, collegato all'archivio di prova."""
    m = CatastoDBManager(
        host=server["host"], port=server["port"], user=server["user"],
        password=server["password"], dbname=archivio["dbname"],
    )
    assert m.initialize_main_pool()
    yield m
    m.close_pool()


class TestPercorsoDellApplicazione:
    """Le stesse funzioni chiamate come le chiama la GUI."""

    def test_i_dati_per_le_esportazioni_della_partita(self, gestore, archivio):
        # Ne dipendono le esportazioni JSON, CSV e PDF (foliarium/ui/export/partita.py).
        dati = gestore.get_partita_data_for_export(archivio["partita_id"])

        civici = {imm["id"]: imm["civico"] for imm in dati["immobili"]}
        assert civici[archivio["immobili"]["Casa di abitazione"]] == "17/A"

    def test_il_report_della_pagina_reportistica(self, gestore, archivio):
        report = gestore.genera_report_proprieta(archivio["partita_id"])
        assert "Localita: Roma, 17/A (Via)" in report


class TestMigrazione24:
    """
    I database gia' esistenti hanno le versioni rotte delle tre funzioni.
    La migrazione le sostituisce con le definizioni degli script canonici,
    cosi' un database riparato e uno nuovo restano identici.
    """

    @pytest.fixture
    def da_riparare(self, server):
        """
        Archivio in cui le tre funzioni sono sostituite da versioni che
        falliscono, con la stessa firma: come su un database creato prima
        della correzione. Restituisce anche le definizioni canoniche.
        """
        nome = _crea_database(server)
        try:
            dati = {"dbname": nome, **_popola(server, nome)}
            with _cursore(server, nome) as cur:
                canoniche = _definizioni(cur)
                for funzione in FUNZIONI:
                    cur.execute(
                        "SELECT pg_get_function_arguments(oid), pg_get_function_result(oid) "
                        "FROM pg_proc WHERE proname = %s "
                        "AND pronamespace = 'catasto'::regnamespace",
                        (funzione,),
                    )
                    argomenti, risultato = cur.fetchone()
                    cur.execute(
                        f"CREATE OR REPLACE FUNCTION catasto.{funzione}({argomenti}) "
                        f"RETURNS {risultato} LANGUAGE plpgsql AS $$ BEGIN "
                        f"RAISE EXCEPTION 'column l.civico does not exist'; END $$"
                    )
            yield dati, canoniche
        finally:
            _elimina_database(server, nome)

    def test_ripara_le_funzioni_e_le_rende_identiche_a_un_database_nuovo(self, server, da_riparare):
        archivio, canoniche = da_riparare
        with pytest.raises(psycopg2.Error):
            _esporta(server, archivio)

        _psql_file(server, archivio["dbname"], MIGRAZIONE)

        with _cursore(server, archivio["dbname"]) as cur:
            assert _definizioni(cur) == canoniche
        assert _esporta(server, archivio)["immobili"]
        assert "Localita: Roma, 17/A (Via)" in _report(server, archivio)
        assert _ricerca(server, archivio)

    def test_si_puo_rieseguire(self, server, da_riparare):
        archivio, canoniche = da_riparare
        _psql_file(server, archivio["dbname"], MIGRAZIONE)
        _psql_file(server, archivio["dbname"], MIGRAZIONE)

        with _cursore(server, archivio["dbname"]) as cur:
            assert _definizioni(cur) == canoniche


def _definizioni(cur) -> dict:
    cur.execute(
        "SELECT proname, pg_get_functiondef(oid) FROM pg_proc "
        "WHERE proname = ANY(%s) AND pronamespace = 'catasto'::regnamespace",
        (list(FUNZIONI),),
    )
    definizioni = dict(cur.fetchall())
    assert set(definizioni) == set(FUNZIONI)
    return definizioni
