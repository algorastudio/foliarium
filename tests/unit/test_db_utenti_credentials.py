"""
tests/unit/test_db_utenti_credentials.py
========================================
``DBUtentiMixin.get_user_credentials`` deve distinguere l'utente inesistente
dall'errore di database.

``None`` significa una cosa sola: la query e' andata a buon fine e non ha
trovato l'utente. Un errore di connessione o di query si propaga come
``DBMError`` con la causa psycopg2 incatenata (``raise ... from e``), cosi'
che l'API possa rispondere 503 e la GUI possa mostrarlo con
``foliarium.ui.errors.show_user_error`` invece di «Username o password errati».
"""
from __future__ import annotations

import logging
from unittest.mock import MagicMock, patch

import psycopg2
import pytest

from catasto_exceptions import DBMError


pytestmark = pytest.mark.unit


@pytest.fixture
def mgr(tmp_path):
    from catasto_db_manager import CatastoDBManager

    m = CatastoDBManager.__new__(CatastoDBManager)
    m.pool = None
    m.schema = "catasto"
    m.offline_mode = False
    m.offline_cache_timestamp = None
    m._cache_dir = tmp_path
    m._main_db_conn_params = {
        "user": "postgres", "host": "localhost", "port": 5432,
        "dbname": "catasto_storico",
    }
    m._pool_metrics = {
        "total_getconn": 0, "total_putconn": 0, "connection_errors": 0,
        "peak_active": 0, "last_error_time": None,
    }
    m.logger = logging.getLogger("test_utenti_credentials")
    return m


def _connessione_con_riga(riga):
    cur = MagicMock()
    cur.fetchone.return_value = riga
    cur_cm = MagicMock()
    cur_cm.__enter__ = MagicMock(return_value=cur)
    cur_cm.__exit__ = MagicMock(return_value=False)
    conn = MagicMock()
    conn.cursor.return_value = cur_cm
    conn_cm = MagicMock()
    conn_cm.__enter__ = MagicMock(return_value=conn)
    conn_cm.__exit__ = MagicMock(return_value=False)
    return conn_cm, cur


class TestGetUserCredentials:

    def test_pool_non_inizializzato_solleva_dbmerror(self, mgr):
        # Il caso del bug: il pool non si e' mai inizializzato (es. TLS
        # richiesto da un server che non lo offre). Si usa il vero
        # _get_connection, non un mock.
        with pytest.raises(DBMError) as info:
            mgr.get_user_credentials("admin")

        assert isinstance(info.value.__cause__, psycopg2.Error)

    def test_errore_di_query_solleva_dbmerror_con_causa(self, mgr):
        conn_cm, cur = _connessione_con_riga(None)
        errore = psycopg2.ProgrammingError("relation catasto.utente does not exist")
        cur.execute.side_effect = errore

        with patch.object(type(mgr), "_get_connection", return_value=conn_cm):
            with pytest.raises(DBMError) as info:
                mgr.get_user_credentials("admin")

        assert info.value.__cause__ is errore

    def test_utente_inesistente_restituisce_none(self, mgr):
        conn_cm, _ = _connessione_con_riga(None)

        with patch.object(type(mgr), "_get_connection", return_value=conn_cm):
            assert mgr.get_user_credentials("nessuno") is None

    def test_utente_trovato_restituisce_dict(self, mgr):
        riga = {
            "id": 3, "username": "archivista", "password_hash": "$2b$...",
            "nome_completo": "Archivista", "ruolo": "editor", "attivo": True,
        }
        conn_cm, cur = _connessione_con_riga(riga)

        with patch.object(type(mgr), "_get_connection", return_value=conn_cm):
            risultato = mgr.get_user_credentials("archivista")

        assert risultato == riga
        assert isinstance(risultato, dict)
        cur.execute.assert_called_once()
        assert cur.execute.call_args[0][1] == ("archivista",)

    def test_username_vuoto_non_interroga_il_db(self, mgr):
        with patch.object(type(mgr), "_get_connection") as get_conn:
            assert mgr.get_user_credentials("") is None
        get_conn.assert_not_called()
