"""
tests/unit/test_db_anonimizza_possessore.py
============================================
Unit test di DBPossessoriMixin.anonimizza_possessore (GDPR art. 17).
Pattern mock identico a test_db_api_keys.py: CatastoDBManager via __new__,
_get_connection patchato.
"""
from __future__ import annotations

import logging
from unittest.mock import MagicMock, patch

import pytest

from catasto_exceptions import DBDataError, DBMError
from db.possessori import POSSESSORE_ANONYMIZED_LABEL


pytestmark = pytest.mark.unit


@pytest.fixture
def mgr(tmp_path):
    from catasto_db_manager import CatastoDBManager
    m = CatastoDBManager.__new__(CatastoDBManager)
    m.pool = None
    m.schema = "catasto"
    m._main_db_conn_params = {
        "user": "postgres", "host": "localhost", "port": 5432,
        "dbname": "catasto_storico",
    }
    m.logger = logging.getLogger("test_anonimizza")
    return m


def _make_conn(rowcount=1):
    cur = MagicMock()
    cur.rowcount = rowcount
    cur_cm = MagicMock()
    cur_cm.__enter__ = MagicMock(return_value=cur)
    cur_cm.__exit__ = MagicMock(return_value=False)
    conn = MagicMock()
    conn.cursor.return_value = cur_cm
    conn_cm = MagicMock()
    conn_cm.__enter__ = MagicMock(return_value=conn)
    conn_cm.__exit__ = MagicMock(return_value=False)
    return conn_cm, cur


class TestAnonimizzaPossessore:

    def test_anonymizes_pii_fields(self, mgr):
        conn_cm, cur = _make_conn(rowcount=1)
        with patch.object(mgr, "_get_connection", return_value=conn_cm):
            ok = mgr.anonimizza_possessore(7, eseguito_da="admin")
        assert ok is True
        sql, params = cur.execute.call_args.args
        # nome_completo, cognome_nome, id (paternita azzerata via SQL NULL letterale)
        assert params == (f"{POSSESSORE_ANONYMIZED_LABEL} #7",
                          POSSESSORE_ANONYMIZED_LABEL, 7)
        assert "paternita = NULL" in sql
        assert "UPDATE" in sql and "possessore" in sql

    def test_uses_parameterized_query(self, mgr):
        conn_cm, cur = _make_conn(rowcount=1)
        with patch.object(mgr, "_get_connection", return_value=conn_cm):
            mgr.anonimizza_possessore(3)
        sql = cur.execute.call_args.args[0]
        # I valori personali passano come placeholder, non interpolati.
        assert "%s" in sql
        assert POSSESSORE_ANONYMIZED_LABEL not in sql

    def test_returns_false_when_id_absent(self, mgr):
        conn_cm, cur = _make_conn(rowcount=0)
        with patch.object(mgr, "_get_connection", return_value=conn_cm):
            ok = mgr.anonimizza_possessore(999)
        assert ok is False

    @pytest.mark.parametrize("bad_id", [0, -1, "5", None, 3.0])
    def test_invalid_id_raises(self, mgr, bad_id):
        with pytest.raises(DBDataError):
            mgr.anonimizza_possessore(bad_id)

    def test_db_error_wrapped(self, mgr):
        conn_cm, cur = _make_conn(rowcount=1)
        cur.execute.side_effect = RuntimeError("boom")
        with patch.object(mgr, "_get_connection", return_value=conn_cm):
            with pytest.raises(DBMError):
                mgr.anonimizza_possessore(7)
