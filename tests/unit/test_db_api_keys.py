"""
tests/unit/test_db_api_keys.py
==============================
Unit test del mixin DBApiKeysMixin (db/api_keys.py).
Pattern mock identico a test_db_drafts.py / test_db_base_audit_view.py:
CatastoDBManager istanziato via __new__, _get_connection patchato.
"""
from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest


pytestmark = pytest.mark.unit


@pytest.fixture
def mgr(tmp_path):
    import sys
    import os
    sys.path.insert(
        0,
        os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        ),
    )
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
    m.logger = logging.getLogger("test_api_keys")
    return m


def _make_conn(*, fetchone_seq=None, fetchall_value=None, rowcount=None,
               dict_cursor_fetchone=None):
    mock_cur = MagicMock()
    if fetchone_seq is not None:
        mock_cur.fetchone.side_effect = list(fetchone_seq)
    if dict_cursor_fetchone is not None:
        mock_cur.fetchone.return_value = dict_cursor_fetchone
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


# ─────────────────────────────────────────────────────────────────────
# create_api_key
# ─────────────────────────────────────────────────────────────────────

class TestCreateApiKey:

    def test_returns_id_and_plaintext_starting_with_prefix(self, mgr):
        conn_cm, cur = _make_conn(fetchone_seq=[(42,)])
        with patch.object(mgr, "_get_connection", return_value=conn_cm):
            new_id, plaintext = mgr.create_api_key(
                name="mcp-server",
                scopes=["read:partite", "read:possessori"],
                created_by=1,
            )
        assert new_id == 42
        assert plaintext.startswith("flr_")
        # 4 (prefix) + 32 hex = 36 chars
        assert len(plaintext) == 36

    def test_stores_sha256_hash_not_plaintext(self, mgr):
        conn_cm, cur = _make_conn(fetchone_seq=[(1,)])
        with patch.object(mgr, "_get_connection", return_value=conn_cm):
            _, plaintext = mgr.create_api_key(
                name="k", scopes=[], created_by=None,
            )
        # Verifico che il param key_hash dell'INSERT sia lo SHA-256 del plaintext
        insert_call = cur.execute.call_args
        params = insert_call.args[1]
        # Tupla (name, key_hash, prefix, scopes, created_by, expires_at, rate_limit)
        stored_hash = params[1]
        expected = hashlib.sha256(plaintext.encode("utf-8")).hexdigest()
        assert stored_hash == expected
        assert plaintext not in str(params)  # plaintext non presente

    def test_prefix_matches_first_12_chars_of_plaintext(self, mgr):
        conn_cm, cur = _make_conn(fetchone_seq=[(1,)])
        with patch.object(mgr, "_get_connection", return_value=conn_cm):
            _, plaintext = mgr.create_api_key(
                name="k", scopes=[], created_by=None,
            )
        params = cur.execute.call_args.args[1]
        prefix = params[2]
        assert prefix == plaintext[:12]
        assert prefix.startswith("flr_")

    def test_empty_name_raises(self, mgr):
        with pytest.raises(ValueError, match="name"):
            mgr.create_api_key(name="", scopes=[], created_by=None)
        with pytest.raises(ValueError, match="name"):
            mgr.create_api_key(name="   ", scopes=[], created_by=None)

    def test_none_scopes_raises(self, mgr):
        with pytest.raises(ValueError, match="scopes"):
            mgr.create_api_key(name="k", scopes=None, created_by=None)


# ─────────────────────────────────────────────────────────────────────
# validate_api_key
# ─────────────────────────────────────────────────────────────────────

class TestValidateApiKey:

    def test_rejects_invalid_prefix(self, mgr):
        # Non chiama nemmeno il DB
        with patch.object(mgr, "_get_connection") as mock_conn:
            assert mgr.validate_api_key("xxx_invalid") is None
            assert mgr.validate_api_key("") is None
            assert mgr.validate_api_key(None) is None
            mock_conn.assert_not_called()

    def test_returns_none_if_hash_not_in_db(self, mgr):
        conn_cm, cur = _make_conn(dict_cursor_fetchone=None)
        with patch.object(mgr, "_get_connection", return_value=conn_cm):
            result = mgr.validate_api_key("flr_" + "a" * 32)
        assert result is None

    def test_returns_none_if_revoked(self, mgr):
        revoked_row = {
            "id": 1, "name": "k", "prefix": "flr_aaaaaaaa",
            "scopes": ["read:partite"], "created_by": 1,
            "created_by_username": "u", "created_by_ruolo": "admin",
            "expires_at": None,
            "revoked_at": datetime.now(timezone.utc),
            "rate_limit_per_min": 60,
        }
        conn_cm, cur = _make_conn(dict_cursor_fetchone=revoked_row)
        with patch.object(mgr, "_get_connection", return_value=conn_cm):
            result = mgr.validate_api_key("flr_" + "a" * 32)
        assert result is None

    def test_returns_none_if_expired(self, mgr):
        expired_row = {
            "id": 1, "name": "k", "prefix": "flr_aaaaaaaa",
            "scopes": [], "created_by": None,
            "created_by_username": None, "created_by_ruolo": None,
            "expires_at": datetime.now(timezone.utc) - timedelta(days=1),
            "revoked_at": None,
            "rate_limit_per_min": 60,
        }
        conn_cm, cur = _make_conn(dict_cursor_fetchone=expired_row)
        with patch.object(mgr, "_get_connection", return_value=conn_cm):
            result = mgr.validate_api_key("flr_" + "a" * 32)
        assert result is None

    def test_returns_principal_dict_on_valid_key(self, mgr):
        valid_row = {
            "id": 7, "name": "mcp-client", "prefix": "flr_a3b9c1d2",
            "scopes": ["read:partite"], "created_by": 1,
            "created_by_username": "marco", "created_by_ruolo": "admin",
            "expires_at": None, "revoked_at": None,
            "rate_limit_per_min": 60,
        }
        conn_cm, cur = _make_conn(dict_cursor_fetchone=valid_row)
        with patch.object(mgr, "_get_connection", return_value=conn_cm):
            result = mgr.validate_api_key("flr_" + "a" * 32)
        assert result is not None
        assert result["id"] == 7
        assert result["name"] == "mcp-client"
        assert result["scopes"] == ["read:partite"]
        assert result["created_by"] == 1
        assert result["created_by_username"] == "marco"
        # Side effect: aggiornamento last_used_at (seconda execute)
        assert any(
            "last_used_at" in c.args[0]
            for c in cur.execute.call_args_list
        )


# ─────────────────────────────────────────────────────────────────────
# revoke_api_key
# ─────────────────────────────────────────────────────────────────────

class TestRevokeApiKey:

    def test_returns_true_when_row_affected(self, mgr):
        conn_cm, cur = _make_conn(rowcount=1)
        with patch.object(mgr, "_get_connection", return_value=conn_cm):
            result = mgr.revoke_api_key(42)
        assert result is True
        sql = cur.execute.call_args.args[0]
        assert "revoked_at = NOW()" in sql
        assert "revoked_at IS NULL" in sql  # idempotenza

    def test_returns_false_when_already_revoked(self, mgr):
        conn_cm, cur = _make_conn(rowcount=0)
        with patch.object(mgr, "_get_connection", return_value=conn_cm):
            result = mgr.revoke_api_key(42)
        assert result is False


# ─────────────────────────────────────────────────────────────────────
# list_api_keys
# ─────────────────────────────────────────────────────────────────────

class TestListApiKeys:

    def test_default_excludes_revoked(self, mgr):
        conn_cm, cur = _make_conn(fetchall_value=[])
        with patch.object(mgr, "_get_connection", return_value=conn_cm):
            mgr.list_api_keys()
        sql = cur.execute.call_args.args[0]
        assert "revoked_at IS NULL" in sql

    def test_include_revoked_true_skips_filter(self, mgr):
        conn_cm, cur = _make_conn(fetchall_value=[])
        with patch.object(mgr, "_get_connection", return_value=conn_cm):
            mgr.list_api_keys(include_revoked=True)
        sql = cur.execute.call_args.args[0]
        assert "revoked_at IS NULL" not in sql

    def test_returns_list_of_dicts(self, mgr):
        rows = [
            {"id": 1, "name": "k1", "prefix": "flr_aaaa1111",
             "scopes": [], "created_by": None,
             "created_by_username": None,
             "created_at": datetime.now(), "expires_at": None,
             "revoked_at": None, "last_used_at": None,
             "rate_limit_per_min": 60},
        ]
        conn_cm, cur = _make_conn(fetchall_value=rows)
        with patch.object(mgr, "_get_connection", return_value=conn_cm):
            result = mgr.list_api_keys()
        assert len(result) == 1
        assert result[0]["id"] == 1
        assert result[0]["prefix"] == "flr_aaaa1111"
