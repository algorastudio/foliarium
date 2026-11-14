"""
tests/unit/test_db_base_connessione_persa.py
============================================
``DBConnectionBase._get_connection`` quando il server chiude la connessione.

Nel ramo d'errore, se anche il rollback fallisce, ``_get_connection`` chiude
il pool (``close_pool`` imposta ``self.pool = None``). Il ``finally`` non deve
poi restituire la connessione a un pool che non c'è più: l'``AttributeError``
che ne uscirebbe prenderebbe il posto dell'errore psycopg2, e i chiamanti che
intercettano ``psycopg2.Error`` non lo riconoscerebbero (l'API rispondeva 500
invece di 503 alla prima richiesta dopo la caduta del database).
"""
from __future__ import annotations

import logging
from unittest.mock import MagicMock

import psycopg2
import pytest


pytestmark = pytest.mark.unit


def _pool_con_connessione_caduta():
    """Pool finto la cui connessione è stata chiusa dal server."""
    cur = MagicMock()
    cur.execute.side_effect = psycopg2.OperationalError(
        "SSL connection has been closed unexpectedly"
    )
    cur_cm = MagicMock()
    cur_cm.__enter__ = MagicMock(return_value=cur)
    cur_cm.__exit__ = MagicMock(return_value=False)
    conn = MagicMock()
    conn.cursor.return_value = cur_cm
    conn.rollback.side_effect = psycopg2.InterfaceError(
        "connection already closed"
    )
    pool = MagicMock()
    pool.getconn.return_value = conn
    return pool


@pytest.fixture
def mgr():
    from catasto_db_manager import CatastoDBManager
    m = CatastoDBManager.__new__(CatastoDBManager)
    m.schema = "catasto"
    m.application_name = "test"
    m.logger = logging.getLogger("test_db_base_connessione_persa")
    m._pool_metrics = {
        "total_getconn": 0, "total_putconn": 0, "connection_errors": 0,
        "peak_active": 0, "last_error_time": None,
    }
    m.pool = _pool_con_connessione_caduta()
    return m


def test_errore_originale_si_propaga_dopo_la_chiusura_del_pool(mgr):
    pool = mgr.pool
    with pytest.raises(psycopg2.OperationalError, match="closed unexpectedly"):
        with mgr._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
    # Il pool è stato chiuso e la connessione non gli è stata restituita.
    assert mgr.pool is None
    pool.closeall.assert_called_once()
    pool.putconn.assert_not_called()


def test_connessione_restituita_al_pool_se_resta_aperto(mgr):
    """Caso ordinario: errore di query con rollback riuscito."""
    pool = mgr.pool
    conn = pool.getconn.return_value
    conn.rollback.side_effect = None
    with pytest.raises(psycopg2.OperationalError):
        with mgr._get_connection() as c:
            with c.cursor() as cur:
                cur.execute("SELECT 1")
    assert mgr.pool is pool
    pool.putconn.assert_called_once_with(conn)
