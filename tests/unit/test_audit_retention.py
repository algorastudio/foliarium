"""
tests/unit/test_audit_retention.py
==================================
Test del servizio di retention dei log di audit
(foliarium/core/services/audit_retention) e della query parametrizzata di
cleanup_audit_logs.
"""
from __future__ import annotations

import logging
from unittest.mock import MagicMock, patch

import pytest


pytestmark = pytest.mark.unit

ar = pytest.importorskip(
    "foliarium.core.services.audit_retention",
    reason="modulo audit_retention non importabile",
)


class _FakeSettings:
    """QSettings finto: store dict con value()/setValue() tipizzati."""

    def __init__(self, initial=None):
        self._d = dict(initial or {})

    def value(self, key, default=None, type=None):
        v = self._d.get(key, default)
        if type is int:
            try:
                return int(v)
            except (TypeError, ValueError):
                return int(default)
        return v

    def setValue(self, key, value):
        self._d[key] = value


# ─────────────────────────────────────────────────────────────────────
# get/set retention days
# ─────────────────────────────────────────────────────────────────────

class TestGetSetRetention:

    def test_default_is_zero(self):
        assert ar.get_retention_days(_FakeSettings()) == 0

    def test_roundtrip(self):
        s = _FakeSettings()
        ar.set_retention_days(365, s)
        assert ar.get_retention_days(s) == 365

    def test_negative_disables(self):
        s = _FakeSettings()
        ar.set_retention_days(-10, s)
        assert ar.get_retention_days(s) == 0

    def test_zero_means_disabled(self):
        s = _FakeSettings({"Audit/RetentionDays": 0})
        assert ar.get_retention_days(s) == 0


# ─────────────────────────────────────────────────────────────────────
# apply_retention
# ─────────────────────────────────────────────────────────────────────

class TestApplyRetention:

    def test_disabled_does_not_call_db(self):
        db = MagicMock()
        assert ar.apply_retention(db, 0) is None
        db.cleanup_audit_logs.assert_not_called()

    def test_negative_does_not_call_db(self):
        db = MagicMock()
        assert ar.apply_retention(db, -5) is None
        db.cleanup_audit_logs.assert_not_called()

    def test_applies_and_returns_count(self):
        db = MagicMock()
        db.cleanup_audit_logs.return_value = 42
        assert ar.apply_retention(db, 90) == 42
        db.cleanup_audit_logs.assert_called_once_with(90)

    def test_db_error_is_swallowed(self):
        db = MagicMock()
        db.cleanup_audit_logs.side_effect = RuntimeError("boom")
        # best-effort: non propaga, ritorna None
        assert ar.apply_retention(db, 30) is None


class TestRunStartupRetention:

    def test_runs_when_configured(self):
        db = MagicMock()
        db.cleanup_audit_logs.return_value = 3
        s = _FakeSettings({"Audit/RetentionDays": 180})
        assert ar.run_startup_retention(db, s) == 3
        db.cleanup_audit_logs.assert_called_once_with(180)

    def test_noop_when_disabled(self):
        db = MagicMock()
        s = _FakeSettings({"Audit/RetentionDays": 0})
        assert ar.run_startup_retention(db, s) is None
        db.cleanup_audit_logs.assert_not_called()


# ─────────────────────────────────────────────────────────────────────
# cleanup_audit_logs: query parametrizzata
# ─────────────────────────────────────────────────────────────────────

class TestCleanupAuditLogsParameterized:

    @pytest.fixture
    def mgr(self):
        from catasto_db_manager import CatastoDBManager
        m = CatastoDBManager.__new__(CatastoDBManager)
        m.schema = "catasto"
        m.logger = logging.getLogger("test_cleanup")
        return m

    def _conn(self, rowcount=5):
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

    def test_uses_bound_parameter_not_interpolation(self, mgr):
        conn_cm, cur = self._conn(rowcount=7)
        with patch.object(mgr, "_get_connection", return_value=conn_cm):
            deleted = mgr.cleanup_audit_logs(90)
        assert deleted == 7
        sql, params = cur.execute.call_args.args
        assert params == (90,)
        assert "%s" in sql
        assert "90" not in sql  # il valore non è interpolato nella stringa SQL

    def test_invalid_days_raises(self, mgr):
        from catasto_exceptions import DBDataError
        with pytest.raises(DBDataError):
            mgr.cleanup_audit_logs(-1)
