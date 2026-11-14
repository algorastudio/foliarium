"""
tests/unit/test_db_base_pool_assente.py
=======================================
``_get_connection`` e ``transaction`` distinguono il pool mai inizializzato
dal pool esaurito.

Il pool resta ``None`` quando ``initialize_main_pool`` fallisce: database
irraggiungibile, TLS richiesto e non offerto, credenziali errate. Prima il
caso passava da ``PoolError`` e finiva nel ramo «pool esaurito», con log ed
eccezione che parlavano di connessioni al massimo: chi leggeva il log cercava
un problema di carico invece che di collegamento.
"""
from __future__ import annotations

import logging
from unittest.mock import MagicMock

import psycopg2
import psycopg2.pool
import pytest

from catasto_exceptions import DBMError


pytestmark = pytest.mark.unit

METODI = ["_get_connection", "transaction"]

ERRORE_TLS = "server does not support SSL, but SSL was required"


@pytest.fixture
def mgr(tmp_path):
    from catasto_db_manager import CatastoDBManager

    m = CatastoDBManager.__new__(CatastoDBManager)
    m.pool = None
    m.last_connection_error = None
    m.schema = "catasto"
    m.offline_mode = False
    m.offline_cache_timestamp = None
    m._cache_dir = tmp_path
    m._max_conn_pool = 10
    m._main_db_conn_params = {
        "user": "postgres", "host": "localhost", "port": 5432,
        "dbname": "catasto_storico",
    }
    m._pool_metrics = {
        "total_getconn": 0, "total_putconn": 0, "connection_errors": 0,
        "peak_active": 0, "last_error_time": None,
    }
    m.logger = logging.getLogger("test_db_base_pool_assente")
    return m


def _apri(mgr, metodo):
    """Entra ed esce dal context manager; restituisce l'eccezione sollevata."""
    with pytest.raises(psycopg2.OperationalError) as info:
        with getattr(mgr, metodo)():
            pass
    return info.value


def _catena(exc):
    anelli = []
    while exc is not None and exc not in anelli:
        anelli.append(exc)
        exc = exc.__cause__ or exc.__context__
    return anelli


def _log_errori(caplog):
    return "\n".join(
        r.getMessage() for r in caplog.records if r.levelno >= logging.ERROR
    )


@pytest.mark.parametrize("metodo", METODI)
class TestPoolMaiInizializzato:

    def test_eccezione_di_collegamento_non_di_esaurimento(self, mgr, metodo):
        errore = _apri(mgr, metodo)

        assert "non stabilito" in str(errore)
        assert "massimo delle connessioni" not in str(errore)
        # Senza PoolError nella catena, foliarium.ui.errors lo classifica
        # come collegamento interrotto e non come pool esaurito.
        assert not any(
            isinstance(a, psycopg2.pool.PoolError) for a in _catena(errore)
        )

    def test_log_parla_di_collegamento(self, mgr, metodo, caplog):
        caplog.set_level(logging.ERROR, logger=mgr.logger.name)

        _apri(mgr, metodo)

        log = _log_errori(caplog)
        assert "non stabilito" in log
        assert "esaurito" not in log

    def test_cita_l_errore_dell_inizializzazione(self, mgr, metodo, caplog):
        # Come lo lascia initialize_main_pool quando la connessione fallisce.
        mgr.last_connection_error = {"pgcode": "08001", "pgerror": ERRORE_TLS}
        caplog.set_level(logging.ERROR, logger=mgr.logger.name)

        errore = _apri(mgr, metodo)

        assert ERRORE_TLS in str(errore)
        assert ERRORE_TLS in _log_errori(caplog)


def test_il_messaggio_non_si_annida_a_ogni_chiamata(mgr):
    """db_handle_errors scrive str(e) in last_connection_error.

    Se il messaggio citasse anche quella stringa, ogni chiamata fallita
    includerebbe il messaggio della precedente.
    """
    from db.base import db_handle_errors

    @db_handle_errors
    def leggi(self):
        with self._get_connection():
            pass

    mgr.last_connection_error = {"pgcode": "08001", "pgerror": ERRORE_TLS}
    messaggi = []
    for _ in range(3):
        with pytest.raises(DBMError) as info:
            leggi(mgr)
        messaggi.append(str(info.value.__cause__))

    for messaggio in messaggi:
        assert messaggio.count("non stabilito") == 1


class TestPoolEsaurito:
    """Il ramo del pool esaurito resta com'era."""

    @pytest.fixture
    def esaurito(self, mgr):
        mgr.pool = MagicMock()
        mgr.pool.getconn.side_effect = psycopg2.pool.PoolError(
            "connection pool exhausted"
        )
        return mgr

    @pytest.mark.parametrize("metodo", METODI)
    def test_eccezione_resta_legata_al_pool(self, esaurito, metodo):
        errore = _apri(esaurito, metodo)

        assert "non stabilito" not in str(errore)
        assert any(
            isinstance(a, psycopg2.pool.PoolError) for a in _catena(errore)
        )
        esaurito.pool.putconn.assert_not_called()

    def test_get_connection_parla_di_connessioni_al_massimo(
            self, esaurito, caplog):
        caplog.set_level(logging.ERROR, logger=esaurito.logger.name)

        errore = _apri(esaurito, "_get_connection")

        assert "massimo delle connessioni" in str(errore)
        assert "esaurito" in _log_errori(caplog)
