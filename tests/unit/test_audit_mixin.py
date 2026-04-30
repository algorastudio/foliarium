"""
tests/unit/test_audit_mixin.py
===============================
Unit test per db/audit.py — DBAuditMixin.
Marker: unit
"""
from __future__ import annotations

import logging
import pytest
import sys
import os
from datetime import date, datetime
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


# ---------------------------------------------------------------------------
# Fixtures & helpers
# ---------------------------------------------------------------------------

@pytest.fixture
def mgr(tmp_path):
    from catasto_db_manager import CatastoDBManager
    m = CatastoDBManager.__new__(CatastoDBManager)
    m.pool = None
    m.schema = "catasto"
    m.offline_mode = False
    m.offline_cache_timestamp = None
    m._cache_dir = tmp_path
    m._pool_metrics = {
        "total_getconn": 0, "total_putconn": 0,
        "connection_errors": 0, "last_error_time": None,
    }
    m.logger = logging.getLogger("test_audit")
    return m


def make_mock_conn(rows=None, fetchone_val=None, rowcount=1):
    mock_cur = MagicMock()
    mock_cur.fetchall.return_value = rows if rows is not None else []
    mock_cur.fetchone.return_value = fetchone_val
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


# ===========================================================================
# TestSetSessionAppUser
# ===========================================================================

@pytest.mark.unit
class TestSetSessionAppUser:

    def test_restituisce_true_su_successo(self, mgr):
        conn_cm, cur = make_mock_conn()
        with patch.object(mgr, "_get_connection", return_value=conn_cm):
            result = mgr.set_session_app_user(user_id=1, client_ip="127.0.0.1")
        assert result is True

    def test_chiama_set_config_due_volte(self, mgr):
        conn_cm, cur = make_mock_conn()
        with patch.object(mgr, "_get_connection", return_value=conn_cm):
            mgr.set_session_app_user(user_id=5, client_ip="10.0.0.1")
        assert cur.execute.call_count == 2

    def test_accetta_none_user_id(self, mgr):
        conn_cm, cur = make_mock_conn()
        with patch.object(mgr, "_get_connection", return_value=conn_cm):
            result = mgr.set_session_app_user(user_id=None)
        assert result is True

    def test_restituisce_false_su_db_error(self, mgr):
        with patch.object(mgr, "_get_connection", side_effect=Exception("DB giù")):
            result = mgr.set_session_app_user(user_id=1)
        assert result is False

    def test_clear_chiama_set_con_none(self, mgr):
        with patch.object(mgr, "set_session_app_user", return_value=True) as mock_set:
            mgr.clear_session_app_user()
        mock_set.assert_called_once_with(user_id=None, client_ip=None)


# ===========================================================================
# TestGetAuditLog
# ===========================================================================

@pytest.mark.unit
class TestGetAuditLog:

    def test_senza_filtri_restituisce_lista(self, mgr):
        righe = [
            {"id": 1, "tabella": "partita", "operazione": "I"},
            {"id": 2, "tabella": "possessore", "operazione": "U"},
        ]
        conn_cm, cur = make_mock_conn(rows=righe)
        with patch.object(mgr, "_get_connection", return_value=conn_cm):
            result = mgr.get_audit_log()
        assert len(result) == 2

    def test_con_filtro_tabella(self, mgr):
        conn_cm, cur = make_mock_conn(rows=[{"id": 1, "tabella": "partita"}])
        with patch.object(mgr, "_get_connection", return_value=conn_cm):
            result = mgr.get_audit_log(tabella="partita")
        args, _ = cur.execute.call_args
        assert "partita" in str(args)

    def test_con_filtro_operazione_valida(self, mgr):
        conn_cm, cur = make_mock_conn(rows=[])
        with patch.object(mgr, "_get_connection", return_value=conn_cm):
            result = mgr.get_audit_log(operazione="I")
        args, _ = cur.execute.call_args
        assert "I" in str(args)

    def test_operazione_non_valida_ignorata(self, mgr):
        """Operazione non in [I, U, D] deve essere ignorata (non aggiunge WHERE)."""
        conn_cm, cur = make_mock_conn(rows=[])
        with patch.object(mgr, "_get_connection", return_value=conn_cm):
            result = mgr.get_audit_log(operazione="X")
        assert isinstance(result, list)

    def test_con_filtro_date(self, mgr):
        conn_cm, cur = make_mock_conn(rows=[])
        with patch.object(mgr, "_get_connection", return_value=conn_cm):
            result = mgr.get_audit_log(
                data_inizio=date(2024, 1, 1),
                data_fine=date(2024, 12, 31)
            )
        assert isinstance(result, list)

    def test_restituisce_lista_vuota_su_db_error(self, mgr):
        import psycopg2
        with patch.object(mgr, "_get_connection", side_effect=psycopg2.Error("db error")):
            result = mgr.get_audit_log()
        assert result == []

    def test_con_limite(self, mgr):
        conn_cm, cur = make_mock_conn(rows=[])
        with patch.object(mgr, "_get_connection", return_value=conn_cm):
            mgr.get_audit_log(limit=50)
        args, _ = cur.execute.call_args
        assert "50" in str(args) or 50 in str(args)


# ===========================================================================
# TestLogAppEvent
# ===========================================================================

@pytest.mark.unit
class TestLogAppEvent:

    def test_esegue_insert(self, mgr):
        conn_cm, cur = make_mock_conn()
        with patch.object(mgr, "_get_connection", return_value=conn_cm):
            mgr.log_app_event(user_id=1, session_id="sess1", event_type="EXPORT", details="CSV export")
        cur.execute.assert_called_once()

    def test_non_solleva_eccezione_su_db_error(self, mgr):
        """log_app_event è best-effort e non deve propagare eccezioni."""
        with patch.object(mgr, "_get_connection", side_effect=Exception("DB giù")):
            # Should not raise
            mgr.log_app_event(user_id=1, session_id=None, event_type="LOGIN", details=None)

    def test_accetta_parametri_none(self, mgr):
        conn_cm, cur = make_mock_conn()
        with patch.object(mgr, "_get_connection", return_value=conn_cm):
            mgr.log_app_event(user_id=None, session_id=None, event_type="TEST", details=None)
        cur.execute.assert_called_once()


# ===========================================================================
# TestGetRecentSessionLogs
# ===========================================================================

@pytest.mark.unit
class TestGetRecentSessionLogs:

    def test_restituisce_lista(self, mgr):
        righe = [{"id": 1, "user_id": 1, "action": "LOGIN"}]
        conn_cm, cur = make_mock_conn(rows=righe)
        with patch.object(mgr, "_get_connection", return_value=conn_cm):
            result = mgr.get_recent_session_logs(limit=5)
        assert isinstance(result, list)
        assert len(result) == 1

    def test_restituisce_lista_vuota_su_errore(self, mgr):
        with patch.object(mgr, "_get_connection", side_effect=Exception("DB giù")):
            result = mgr.get_recent_session_logs()
        assert result == []


# ===========================================================================
# TestSetAuditSessionVariables
# ===========================================================================

@pytest.mark.unit
class TestSetAuditSessionVariables:

    def test_restituisce_true_su_successo(self, mgr):
        conn_cm, cur = make_mock_conn()
        with patch.object(mgr, "_get_connection", return_value=conn_cm):
            result = mgr.set_audit_session_variables(app_user_id=1, session_id="sess1")
        assert result is True

    def test_restituisce_false_su_db_error(self, mgr):
        with patch.object(mgr, "_get_connection", side_effect=Exception("DB error")):
            result = mgr.set_audit_session_variables(app_user_id=1, session_id="s1")
        assert result is False

    def test_clear_restituisce_true(self, mgr):
        conn_cm, cur = make_mock_conn()
        with patch.object(mgr, "_get_connection", return_value=conn_cm):
            result = mgr.clear_audit_session_variables()
        assert result is True


# ===========================================================================
# TestCloseUserSession
# ===========================================================================

@pytest.mark.unit
class TestCloseUserSession:

    def test_restituisce_true_su_successo(self, mgr):
        conn_cm, cur = make_mock_conn(rowcount=1)
        with patch.object(mgr, "_get_connection", return_value=conn_cm):
            result = mgr.close_user_session("session-abc")
        assert result is True

    def test_restituisce_false_su_db_error(self, mgr):
        with patch.object(mgr, "_get_connection", side_effect=Exception("DB giù")):
            result = mgr.close_user_session("session-abc")
        assert result is False


# ===========================================================================
# TestSearchConsultazioni
# ===========================================================================

@pytest.mark.unit
class TestSearchConsultazioni:

    def test_senza_filtri_restituisce_lista(self, mgr):
        righe = [{"id": 1, "richiedente": "Mario Rossi"}]
        conn_cm, cur = make_mock_conn(rows=righe)
        with patch.object(mgr, "_get_connection", return_value=conn_cm):
            result = mgr.search_consultazioni()
        assert isinstance(result, list)
        assert len(result) == 1

    def test_con_filtro_date(self, mgr):
        conn_cm, cur = make_mock_conn(rows=[])
        with patch.object(mgr, "_get_connection", return_value=conn_cm):
            result = mgr.search_consultazioni(
                data_inizio=date(2024, 1, 1),
                data_fine=date(2024, 12, 31)
            )
        assert isinstance(result, list)

    def test_restituisce_lista_vuota_su_errore(self, mgr):
        with patch.object(mgr, "_get_connection", side_effect=Exception("DB error")):
            result = mgr.search_consultazioni()
        assert result == []


# ===========================================================================
# TestCleanupAuditLogs
# ===========================================================================

@pytest.mark.unit
class TestCleanupAuditLogs:

    def test_restituisce_righe_eliminate(self, mgr):
        conn_cm, cur = make_mock_conn(fetchone_val=(42,))
        with patch.object(mgr, "_get_connection", return_value=conn_cm):
            result = mgr.cleanup_audit_logs(days_to_keep=90)
        assert isinstance(result, int)

    def test_restituisce_zero_su_errore(self, mgr):
        with patch.object(mgr, "_get_connection", side_effect=Exception("DB giù")):
            result = mgr.cleanup_audit_logs(days_to_keep=90)
        assert result == 0
