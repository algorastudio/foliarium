"""
tests/unit/test_db_drafts.py
============================
Unit test del mixin DBDraftsMixin (db/drafts.py) e dell'auto-applicazione
della tabella catasto.partita_draft (db/base.py::_ensure_partita_draft_table).

Riproduce il pattern mock di test_db_base_audit_view.py: CatastoDBManager
istanziato via __new__ senza pool, _get_connection patchato.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest


pytestmark = pytest.mark.unit


@pytest.fixture
def mgr(tmp_path):
    import sys, os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
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
    m.logger = logging.getLogger("test_drafts")
    return m


def _make_conn(*, fetchone_seq=None, fetchall_value=None, rowcount=None):
    mock_cur = MagicMock()
    if fetchone_seq is not None:
        mock_cur.fetchone.side_effect = list(fetchone_seq)
    if fetchall_value is not None:
        mock_cur.fetchall.return_value = fetchall_value
    if rowcount is not None:
        mock_cur.rowcount = rowcount
    mock_cursor_cm = MagicMock()
    mock_cursor_cm.__enter__ = MagicMock(return_value=mock_cur)
    mock_cursor_cm.__exit__ = MagicMock(return_value=False)
    mock_conn = MagicMock()
    mock_conn.cursor.return_value = mock_cursor_cm
    mock_conn_cm = MagicMock()
    mock_conn_cm.__enter__ = MagicMock(return_value=mock_conn)
    mock_conn_cm.__exit__ = MagicMock(return_value=False)
    return mock_conn_cm, mock_cur


# ──────────────────────────────────────────────────────────────────────
# _ensure_partita_draft_table
# ──────────────────────────────────────────────────────────────────────

class TestEnsurePartitaDraftTable:

    def test_skips_when_table_exists(self, mgr):
        # fetchone[0] = tabella già presente
        conn_cm, cur = _make_conn(fetchone_seq=[(1,)])
        with patch.object(mgr, "_get_connection", return_value=conn_cm):
            mgr._ensure_partita_draft_table()
        executed = [c.args[0] for c in cur.execute.call_args_list]
        assert any("information_schema.tables" in q for q in executed)
        assert not any("CREATE TABLE" in q for q in executed)

    def test_creates_table_with_fk_when_utente_present(self, mgr):
        # fetchone: tabella assente, poi utente presente
        conn_cm, cur = _make_conn(fetchone_seq=[None, (1,)])
        with patch.object(mgr, "_get_connection", return_value=conn_cm):
            mgr._ensure_partita_draft_table()
        executed = [c.args[0] for c in cur.execute.call_args_list]
        creates = [q for q in executed if "CREATE TABLE" in q]
        assert len(creates) == 1
        assert "catasto.partita_draft" in creates[0]
        # FK presente solo quando utente esiste
        assert "REFERENCES catasto.utente(id)" in creates[0]

    def test_creates_table_without_fk_when_utente_missing(self, mgr):
        # fetchone: tabella assente, utente assente
        conn_cm, cur = _make_conn(fetchone_seq=[None, None])
        with patch.object(mgr, "_get_connection", return_value=conn_cm):
            mgr._ensure_partita_draft_table()
        executed = [c.args[0] for c in cur.execute.call_args_list]
        creates = [q for q in executed if "CREATE TABLE" in q]
        assert len(creates) == 1
        assert "REFERENCES" not in creates[0]

    def test_does_not_raise_on_error(self, mgr):
        with patch.object(mgr, "_get_connection", side_effect=Exception("DB giù")):
            mgr._ensure_partita_draft_table()  # non deve sollevare


# ──────────────────────────────────────────────────────────────────────
# save_partita_draft
# ──────────────────────────────────────────────────────────────────────

class TestSavePartitaDraft:

    def test_insert_returns_new_id(self, mgr):
        conn_cm, cur = _make_conn(fetchone_seq=[{"id": 42}])
        with patch.object(mgr, "_get_connection", return_value=conn_cm):
            new_id = mgr.save_partita_draft(
                utente_id=7,
                titolo="Test bozza",
                payload={"a": 1, "b": [1, 2]},
            )
        assert new_id == 42
        executed = [c.args[0] for c in cur.execute.call_args_list]
        assert any("INSERT INTO catasto.partita_draft" in q for q in executed)
        # Il payload JSON deve essere passato come stringa serializzata
        params = cur.execute.call_args_list[0].args[1]
        assert params[0] == 7
        assert params[1] == "Test bozza"
        payload_arg = json.loads(params[2])
        assert payload_arg == {"a": 1, "b": [1, 2]}

    def test_update_when_draft_id_given(self, mgr):
        conn_cm, cur = _make_conn(fetchone_seq=[{"id": 99}])
        with patch.object(mgr, "_get_connection", return_value=conn_cm):
            ret = mgr.save_partita_draft(
                utente_id=7,
                titolo="Aggiornata",
                payload={"x": 1},
                draft_id=99,
            )
        assert ret == 99
        executed = [c.args[0] for c in cur.execute.call_args_list]
        assert any("UPDATE catasto.partita_draft" in q for q in executed)
        assert not any("INSERT INTO catasto.partita_draft" in q for q in executed)

    def test_update_not_found_raises(self, mgr):
        from catasto_exceptions import DBNotFoundError
        conn_cm, cur = _make_conn(fetchone_seq=[None])
        with patch.object(mgr, "_get_connection", return_value=conn_cm):
            with pytest.raises(DBNotFoundError):
                mgr.save_partita_draft(
                    utente_id=7,
                    titolo="x",
                    payload={},
                    draft_id=1234,
                )


# ──────────────────────────────────────────────────────────────────────
# list / load / delete
# ──────────────────────────────────────────────────────────────────────

class TestListLoadDelete:

    def test_list_filters_by_user(self, mgr):
        rows = [
            {"id": 1, "titolo": "A", "app_version": "1.0", "created_at": None, "updated_at": None},
            {"id": 2, "titolo": "B", "app_version": "1.0", "created_at": None, "updated_at": None},
        ]
        conn_cm, cur = _make_conn(fetchall_value=rows)
        with patch.object(mgr, "_get_connection", return_value=conn_cm):
            res = mgr.list_partita_drafts(utente_id=7)
        assert len(res) == 2
        executed = [c.args[0] for c in cur.execute.call_args_list]
        assert any("utente_id = %s" in q for q in executed)

    def test_list_orphans_when_user_none(self, mgr):
        conn_cm, cur = _make_conn(fetchall_value=[])
        with patch.object(mgr, "_get_connection", return_value=conn_cm):
            mgr.list_partita_drafts(utente_id=None)
        executed = [c.args[0] for c in cur.execute.call_args_list]
        assert any("utente_id IS NULL" in q for q in executed)

    def test_load_returns_payload_as_dict(self, mgr):
        row = {
            "id": 5, "utente_id": 7, "titolo": "T",
            "payload": {"step": 2, "comune": {"id": 1, "nome": "Genova"}},
            "app_version": "1.0",
            "created_at": datetime(2026, 1, 1),
            "updated_at": datetime(2026, 1, 2),
        }
        conn_cm, cur = _make_conn(fetchone_seq=[row])
        with patch.object(mgr, "_get_connection", return_value=conn_cm):
            full = mgr.load_partita_draft(5, utente_id=7)
        assert full["id"] == 5
        assert full["payload"]["step"] == 2
        assert full["payload"]["comune"]["nome"] == "Genova"

    def test_load_handles_string_payload(self, mgr):
        """Se psycopg2 ritorna il JSONB come stringa, viene parsato."""
        row = {
            "id": 5, "utente_id": 7, "titolo": "T",
            "payload": '{"step": 1}',
            "app_version": None,
            "created_at": None,
            "updated_at": None,
        }
        conn_cm, cur = _make_conn(fetchone_seq=[row])
        with patch.object(mgr, "_get_connection", return_value=conn_cm):
            full = mgr.load_partita_draft(5)
        assert full["payload"] == {"step": 1}

    def test_load_not_found_raises(self, mgr):
        from catasto_exceptions import DBNotFoundError
        conn_cm, cur = _make_conn(fetchone_seq=[None])
        with patch.object(mgr, "_get_connection", return_value=conn_cm):
            with pytest.raises(DBNotFoundError):
                mgr.load_partita_draft(404, utente_id=7)

    def test_delete_returns_true_when_rows_affected(self, mgr):
        conn_cm, cur = _make_conn(rowcount=1)
        with patch.object(mgr, "_get_connection", return_value=conn_cm):
            ok = mgr.delete_partita_draft(7, utente_id=3)
        assert ok is True

    def test_delete_returns_false_when_nothing(self, mgr):
        conn_cm, cur = _make_conn(rowcount=0)
        with patch.object(mgr, "_get_connection", return_value=conn_cm):
            ok = mgr.delete_partita_draft(7, utente_id=3)
        assert ok is False
