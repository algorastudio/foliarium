"""
tests/integration/test_schema_database_nuovo.py
===============================================
Applica `setup_database.SQL_SCRIPTS` a un database vuoto, su un PostgreSQL
vero, con la stessa funzione che usa l'installer e in modalita' rigorosa
(`psql -v ON_ERROR_STOP=1`).

Perche' esiste. Il database dei test viene costruito dalla pipeline con i
vecchi script numerati, non con l'elenco dell'installer: per questo un
errore nell'ordine di `SQL_SCRIPTS` (`functions/06_audit.sql` applicato
prima di `admin/01_users.sql`, da cui dipende) e' rimasto invisibile. La
chiave esterna `audit_log.app_user_id -> utente.id` non veniva creata e
nessun test se ne accorgeva.

Verifica anche la sanatoria dei database gia' installati senza quella
chiave: `DBConnectionBase._ensure_audit_user_fk()` e la migrazione
`sql_scripts/migrations/23_add_fk_audit_log_utente.sql`.

Richiede `psql` nel PATH e un server raggiungibile su 127.0.0.1 come
`postgres` (DB_PORT, DB_PASS): sono i parametri fissi dell'installer.
"""

from __future__ import annotations

import contextlib
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
MIGRAZIONE = SQL / "migrations" / "23_add_fk_audit_log_utente.sql"
VINCOLO = "fk_audit_log_app_user_id_utente"

IN_CI = os.environ.get("CI") == "true" or os.environ.get("GITHUB_ACTIONS") == "true"


def _non_disponibile(motivo: str):
    """In CI l'assenza del server e' un errore, non un motivo per saltare:
    questo test e' l'unico a sorvegliare l'elenco dell'installer."""
    if IN_CI:
        pytest.fail(motivo)
    pytest.skip(motivo)


@pytest.fixture(scope="module")
def server():
    """Parametri del server, nella forma che l'installer sa usare."""
    host = os.environ.get("DB_HOST", "localhost")
    utente = os.environ.get("DB_USER", "postgres")
    if host not in ("localhost", "127.0.0.1") or utente != "postgres":
        _non_disponibile(
            "setup_database.py si collega solo a 127.0.0.1 come 'postgres' "
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
        "pg_bin": Path(psql).parent,
    }
    try:
        _connetti(parametri, "postgres").close()
    except psycopg2.OperationalError as e:
        _non_disponibile(f"PostgreSQL non raggiungibile: {e}")
    return parametri


def _connetti(server: dict, dbname: str):
    conn = psycopg2.connect(
        host=server["host"], port=server["port"], user=server["user"],
        password=server["password"], dbname=dbname,
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


def _crea_database(server: dict) -> str:
    # Un nome diverso da `catasto_storico`: gli script non devono dipendere
    # dal nome del database (opzione --db-name, variabile POSTGRES_DB).
    nome = f"foliarium_prova_{uuid.uuid4().hex[:10]}"
    with _cursore(server, "postgres") as cur:
        cur.execute(f'CREATE DATABASE "{nome}" ENCODING \'UTF8\' TEMPLATE template0')
    return nome


def _elimina_database(server: dict, nome: str) -> None:
    with _cursore(server, "postgres") as cur:
        cur.execute(f'DROP DATABASE IF EXISTS "{nome}" WITH (FORCE)')


@pytest.fixture(scope="module")
def database_installato(server):
    """Un database appena creato dall'elenco dell'installer. Sola lettura."""
    nome = _crea_database(server)
    try:
        sdb.apply_sql_scripts(
            server["pg_bin"], server["port"], SQL, nome, server["password"],
            database_nuovo=True,
        )
        yield nome
    finally:
        _elimina_database(server, nome)


@pytest.fixture
def database_senza_chiave(server):
    """
    Un database come lo lasciava l'installer fino alla v1.0.2: completo,
    ma senza la chiave esterna audit_log -> utente e senza la vista.
    """
    nome = _crea_database(server)
    try:
        sdb.apply_sql_scripts(
            server["pg_bin"], server["port"], SQL, nome, server["password"],
            database_nuovo=True,
        )
        with _cursore(server, nome) as cur:
            cur.execute(f"ALTER TABLE catasto.audit_log DROP CONSTRAINT {VINCOLO}")
            cur.execute("DROP VIEW catasto.v_audit_dettagliato")
        yield nome
    finally:
        _elimina_database(server, nome)


def _vincolo(server: dict, dbname: str):
    """(azione alla cancellazione, convalidato) oppure None se manca."""
    with _cursore(server, dbname) as cur:
        cur.execute(
            "SELECT confdeltype::text, convalidated FROM pg_constraint "
            "WHERE conname = %s AND conrelid = 'catasto.audit_log'::regclass",
            (VINCOLO,),
        )
        return cur.fetchone()


def _nuovo_utente(cur, username: str) -> int:
    cur.execute(
        "INSERT INTO catasto.utente (username, password_hash, nome_completo, email, ruolo) "
        "VALUES (%s, 'x', %s, %s, 'archivista') RETURNING id",
        (username, username, f"{username}@prova.local"),
    )
    return cur.fetchone()[0]


def _riga_di_audit(cur, app_user_id: int) -> int:
    cur.execute(
        "INSERT INTO catasto.audit_log (tabella, operazione, record_id, utente, app_user_id) "
        "VALUES ('comune', 'I', 1, 'prova', %s) RETURNING id",
        (app_user_id,),
    )
    return cur.fetchone()[0]


def _app_user_id(cur, audit_id: int):
    cur.execute("SELECT app_user_id FROM catasto.audit_log WHERE id = %s", (audit_id,))
    return cur.fetchone()[0]


def _gestore(server: dict, dbname: str) -> CatastoDBManager:
    return CatastoDBManager(
        host=server["host"], port=server["port"], user=server["user"],
        password=server["password"], dbname=dbname,
    )


class TestElencoDellInstaller:

    def test_si_applica_senza_errori_a_un_database_vuoto(self, database_installato):
        # La fixture applica l'elenco in modalita' rigorosa: se un'istruzione
        # qualunque fallisce, solleva e il test non arriva qui.
        assert database_installato

    def test_crea_la_vista_di_audit(self, server, database_installato):
        with _cursore(server, database_installato) as cur:
            cur.execute(
                "SELECT 1 FROM information_schema.views "
                "WHERE table_schema = 'catasto' AND table_name = 'v_audit_dettagliato'"
            )
            assert cur.fetchone() is not None

    def test_crea_la_chiave_esterna_audit_utente(self, server, database_installato):
        # 'n' = ON DELETE SET NULL
        assert _vincolo(server, database_installato) == ("n", True)

    def test_il_search_path_vale_per_il_database_creato(self, server, database_installato):
        # `ALTER DATABASE catasto_storico` scritto per esteso lasciava senza
        # search_path un database con un altro nome: gli script che non
        # qualificano gli oggetti li creavano in `public`.
        with _cursore(server, database_installato) as cur:
            cur.execute("SHOW search_path")
            assert cur.fetchone()[0].replace(" ", "") == "catasto,public"
            cur.execute(
                "SELECT n.nspname FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace "
                "WHERE p.proname = 'vacuum_analyze_catasto_schema'"
            )
            assert [r[0] for r in cur.fetchall()] == ["catasto"]

    def test_eliminando_un_utente_le_sue_righe_di_audit_restano(self, server, database_installato):
        with _cursore(server, database_installato) as cur:
            utente_id = _nuovo_utente(cur, f"u_{uuid.uuid4().hex[:8]}")
            audit_id = _riga_di_audit(cur, utente_id)

            cur.execute("DELETE FROM catasto.utente WHERE id = %s", (utente_id,))

            assert _app_user_id(cur, audit_id) is None

    def test_il_bootstrap_crea_l_amministratore(self, server, database_installato):
        sdb.run_psql_file(
            server["pg_bin"], server["port"], SQL / sdb.BOOTSTRAP_ADMIN_SCRIPT,
            dbname=database_installato, password=server["password"],
            variables={"admin_password": "Prova-123456", "admin_email": "admin@prova.local"},
        )
        with _cursore(server, database_installato) as cur:
            cur.execute("SELECT ruolo FROM catasto.utente WHERE username = 'admin'")
            assert cur.fetchone() == ("admin",)


class TestSanatoriaDeiDatabaseGiaInstallati:
    """
    I database creati dall'installer fino alla v1.0.2 non hanno la chiave
    esterna. La sanatoria non riscrive il registro di audit: le righe di
    utenti gia' eliminati conservano il loro identificativo, e il vincolo
    viene creato NOT VALID (vale per le righe nuove e per le eliminazioni
    future).
    """

    def test_all_avvio_l_applicazione_crea_la_chiave(self, server, database_senza_chiave):
        assert _vincolo(server, database_senza_chiave) is None

        gestore = _gestore(server, database_senza_chiave)
        try:
            assert gestore.initialize_main_pool() is True
        finally:
            gestore.close_pool()

        assert _vincolo(server, database_senza_chiave) == ("n", True)

    def test_ripetere_la_sanatoria_non_fa_nulla(self, server, database_senza_chiave):
        gestore = _gestore(server, database_senza_chiave)
        try:
            gestore.initialize_main_pool()
            gestore._ensure_audit_user_fk()
            gestore._ensure_audit_user_fk()
        finally:
            gestore.close_pool()

        assert _vincolo(server, database_senza_chiave) == ("n", True)

    def test_le_righe_di_utenti_gia_eliminati_non_vengono_toccate(self, server, database_senza_chiave):
        with _cursore(server, database_senza_chiave) as cur:
            eliminato = _nuovo_utente(cur, "eliminato")
            presente = _nuovo_utente(cur, "presente")
            orfana = _riga_di_audit(cur, eliminato)
            viva = _riga_di_audit(cur, presente)
            # Senza la chiave esterna la riga resta a puntare nel vuoto.
            cur.execute("DELETE FROM catasto.utente WHERE id = %s", (eliminato,))
            assert _app_user_id(cur, orfana) == eliminato

        gestore = _gestore(server, database_senza_chiave)
        try:
            gestore.initialize_main_pool()
        finally:
            gestore.close_pool()

        # Vincolo presente ma non convalidato: lo storico non e' riscritto.
        assert _vincolo(server, database_senza_chiave) == ("n", False)
        with _cursore(server, database_senza_chiave) as cur:
            assert _app_user_id(cur, orfana) == eliminato
            # Da qui in avanti il vincolo lavora come su un database nuovo.
            cur.execute("DELETE FROM catasto.utente WHERE id = %s", (presente,))
            assert _app_user_id(cur, viva) is None
            with pytest.raises(psycopg2.errors.ForeignKeyViolation):
                _riga_di_audit(cur, 999_999)

    def test_la_migrazione_manuale_equivale_a_quella_automatica(self, server, database_senza_chiave):
        def applica():
            env = dict(os.environ, PGPASSWORD=server["password"])
            return subprocess.run(
                [str(server["pg_bin"] / "psql"), "-X", "-h", server["host"],
                 "-p", str(server["port"]), "-U", server["user"],
                 "-d", database_senza_chiave, "-v", "ON_ERROR_STOP=1",
                 "-f", str(MIGRAZIONE)],
                env=env, capture_output=True, text=True,
            )

        with _cursore(server, database_senza_chiave) as cur:
            eliminato = _nuovo_utente(cur, "eliminato")
            orfana = _riga_di_audit(cur, eliminato)
            cur.execute("DELETE FROM catasto.utente WHERE id = %s", (eliminato,))

        primo = applica()
        assert primo.returncode == 0, primo.stderr
        assert _vincolo(server, database_senza_chiave) == ("n", False)
        with _cursore(server, database_senza_chiave) as cur:
            assert _app_user_id(cur, orfana) == eliminato

        # Rieseguibile.
        secondo = applica()
        assert secondo.returncode == 0, secondo.stderr
        assert _vincolo(server, database_senza_chiave) == ("n", False)

    def test_la_migrazione_manuale_convalida_se_non_ci_sono_righe_orfane(self, server, database_senza_chiave):
        env = dict(os.environ, PGPASSWORD=server["password"])
        r = subprocess.run(
            [str(server["pg_bin"] / "psql"), "-X", "-h", server["host"],
             "-p", str(server["port"]), "-U", server["user"],
             "-d", database_senza_chiave, "-v", "ON_ERROR_STOP=1",
             "-f", str(MIGRAZIONE)],
            env=env, capture_output=True, text=True,
        )
        assert r.returncode == 0, r.stderr
        assert _vincolo(server, database_senza_chiave) == ("n", True)
