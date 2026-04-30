"""
tests/unit/test_utenti_mixin.py
================================
Unit test per db/utenti.py — DBUtentiMixin.
Marker: unit
"""
from __future__ import annotations

import logging
import pytest
import sys
import os
from unittest.mock import MagicMock, patch
import psycopg2
import psycopg2.errors

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
    m.logger = logging.getLogger("test_utenti")
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
# TestCreateUser
# ===========================================================================

@pytest.mark.unit
class TestCreateUser:

    def test_restituisce_true_su_successo(self, mgr):
        conn_cm, cur = make_mock_conn()
        with patch.object(mgr, "_get_connection", return_value=conn_cm):
            result = mgr.create_user(
                username="mario",
                password_hash="$2b$12$abc",
                nome_completo="Mario Rossi",
                email="mario@test.com",
                ruolo="operatore",
            )
        assert result is True

    def test_chiama_stored_procedure(self, mgr):
        conn_cm, cur = make_mock_conn()
        with patch.object(mgr, "_get_connection", return_value=conn_cm):
            mgr.create_user("mario", "$2b$12$abc", "Mario Rossi", "m@t.com", "operatore")
        cur.execute.assert_called_once()
        args, _ = cur.execute.call_args
        assert "crea_utente" in args[0]

    def test_solleva_dbunique_su_username_duplicato(self, mgr):
        from catasto_exceptions import DBUniqueConstraintError
        conn_cm, cur = make_mock_conn()
        cur.execute.side_effect = psycopg2.errors.UniqueViolation("duplicate key")
        with patch.object(mgr, "_get_connection", return_value=conn_cm):
            with pytest.raises(DBUniqueConstraintError):
                mgr.create_user("mario", "$2b$12$abc", "Mario Rossi", "m@t.com", "operatore")

    def test_solleva_dbmerror_su_db_error(self, mgr):
        from catasto_exceptions import DBMError
        with patch.object(mgr, "_get_connection", side_effect=psycopg2.OperationalError("connessione persa")):
            with pytest.raises(DBMError):
                mgr.create_user("mario", "$2b$12$abc", "Mario Rossi", "m@t.com", "operatore")


# ===========================================================================
# TestGetUserCredentials
# ===========================================================================

@pytest.mark.unit
class TestGetUserCredentials:

    def test_restituisce_dict_se_utente_trovato(self, mgr):
        user_data = {
            "id": 1, "username": "mario", "password_hash": "$2b$12$abc",
            "nome_completo": "Mario Rossi", "ruolo": "operatore", "attivo": True
        }
        conn_cm, cur = make_mock_conn(fetchone_val=user_data)
        with patch.object(mgr, "_get_connection", return_value=conn_cm):
            result = mgr.get_user_credentials("mario")
        assert isinstance(result, dict)
        assert result["username"] == "mario"

    def test_restituisce_none_se_utente_non_trovato(self, mgr):
        conn_cm, cur = make_mock_conn(fetchone_val=None)
        with patch.object(mgr, "_get_connection", return_value=conn_cm):
            result = mgr.get_user_credentials("nonexistent")
        assert result is None

    def test_restituisce_none_se_username_vuoto(self, mgr):
        result = mgr.get_user_credentials("")
        assert result is None

    def test_restituisce_none_su_db_error(self, mgr):
        with patch.object(mgr, "_get_connection", side_effect=Exception("DB giù")):
            result = mgr.get_user_credentials("mario")
        assert result is None


# ===========================================================================
# TestGetUtenti
# ===========================================================================

@pytest.mark.unit
class TestGetUtenti:

    def test_restituisce_lista_tutti_utenti(self, mgr):
        utenti = [
            {"id": 1, "username": "mario", "ruolo": "admin", "attivo": True},
            {"id": 2, "username": "luigi", "ruolo": "operatore", "attivo": False},
        ]
        conn_cm, cur = make_mock_conn(rows=utenti)
        with patch.object(mgr, "_get_connection", return_value=conn_cm):
            result = mgr.get_utenti()
        assert len(result) == 2

    def test_filtro_solo_attivi(self, mgr):
        conn_cm, cur = make_mock_conn(rows=[{"id": 1, "username": "mario", "attivo": True}])
        with patch.object(mgr, "_get_connection", return_value=conn_cm):
            result = mgr.get_utenti(solo_attivi=True)
        args, _ = cur.execute.call_args
        assert "attivo" in args[0].lower() or "TRUE" in str(args)

    def test_restituisce_lista_vuota_su_db_error(self, mgr):
        with patch.object(mgr, "_get_connection", side_effect=Exception("DB giù")):
            result = mgr.get_utenti()
        assert result == []


# ===========================================================================
# TestGetUtenteById
# ===========================================================================

@pytest.mark.unit
class TestGetUtenteById:

    def test_restituisce_dict_se_trovato(self, mgr):
        utente = {"id": 5, "username": "mario", "ruolo": "admin"}
        conn_cm, cur = make_mock_conn(fetchone_val=utente)
        with patch.object(mgr, "_get_connection", return_value=conn_cm):
            result = mgr.get_utente_by_id(5)
        assert result["id"] == 5

    def test_restituisce_none_se_non_trovato(self, mgr):
        conn_cm, cur = make_mock_conn(fetchone_val=None)
        with patch.object(mgr, "_get_connection", return_value=conn_cm):
            result = mgr.get_utente_by_id(9999)
        assert result is None

    def test_restituisce_none_su_db_error(self, mgr):
        with patch.object(mgr, "_get_connection", side_effect=Exception("DB giù")):
            result = mgr.get_utente_by_id(1)
        assert result is None


# ===========================================================================
# TestResetUserPassword
# ===========================================================================

@pytest.mark.unit
class TestResetUserPassword:

    def test_restituisce_true_su_successo(self, mgr):
        conn_cm, cur = make_mock_conn(rowcount=1)
        with patch.object(mgr, "_get_connection", return_value=conn_cm):
            result = mgr.reset_user_password(utente_id=1, new_password_hash="$2b$12$new")
        assert result is True

    def test_restituisce_false_se_nessuna_riga_aggiornata(self, mgr):
        conn_cm, cur = make_mock_conn(rowcount=0)
        with patch.object(mgr, "_get_connection", return_value=conn_cm):
            result = mgr.reset_user_password(utente_id=999, new_password_hash="$2b$12$new")
        assert result is False

    def test_restituisce_false_su_db_error(self, mgr):
        with patch.object(mgr, "_get_connection", side_effect=Exception("DB giù")):
            result = mgr.reset_user_password(utente_id=1, new_password_hash="$2b$12$new")
        assert result is False


# ===========================================================================
# TestDeactivateActivateUser
# ===========================================================================

@pytest.mark.unit
class TestDeactivateActivateUser:

    def test_deactivate_chiama_update_con_false(self, mgr):
        with patch.object(mgr, "_update_user_active_status", return_value=True) as mock_update:
            mgr.deactivate_user(utente_id=1)
        mock_update.assert_called_once_with(1, False)

    def test_activate_chiama_update_con_true(self, mgr):
        with patch.object(mgr, "_update_user_active_status", return_value=True) as mock_update:
            mgr.activate_user(utente_id=1)
        mock_update.assert_called_once_with(1, True)

    def test_update_user_active_status_restituisce_true(self, mgr):
        conn_cm, cur = make_mock_conn(rowcount=1)
        with patch.object(mgr, "_get_connection", return_value=conn_cm):
            result = mgr._update_user_active_status(utente_id=1, nuovo_stato_attivo=True)
        assert result is True

    def test_update_user_active_status_restituisce_false_su_zero_rows(self, mgr):
        conn_cm, cur = make_mock_conn(rowcount=0)
        with patch.object(mgr, "_get_connection", return_value=conn_cm):
            result = mgr._update_user_active_status(utente_id=999, nuovo_stato_attivo=False)
        assert result is False


# ===========================================================================
# TestCheckPermission
# ===========================================================================

@pytest.mark.unit
class TestCheckPermission:

    def test_restituisce_true_se_permesso_presente(self, mgr):
        conn_cm, cur = make_mock_conn(fetchone_val={"permesso_nome": "view_reports"})
        with patch.object(mgr, "_get_connection", return_value=conn_cm):
            result = mgr.check_permission(utente_id=1, permesso_nome="view_reports")
        assert result is True

    def test_restituisce_false_se_permesso_assente(self, mgr):
        conn_cm, cur = make_mock_conn(fetchone_val=None)
        with patch.object(mgr, "_get_connection", return_value=conn_cm):
            result = mgr.check_permission(utente_id=1, permesso_nome="admin_only")
        assert result is False

    def test_restituisce_false_su_db_error(self, mgr):
        with patch.object(mgr, "_get_connection", side_effect=Exception("DB giù")):
            result = mgr.check_permission(utente_id=1, permesso_nome="view_reports")
        assert result is False


# ===========================================================================
# TestRegisterAccess
# ===========================================================================

@pytest.mark.unit
class TestRegisterAccess:

    def test_restituisce_stringa_session_id(self, mgr):
        conn_cm, cur = make_mock_conn()
        with patch.object(mgr, "_get_connection", return_value=conn_cm):
            result = mgr.register_access(user_id=1, action="LOGIN", esito=True, ip_address="127.0.0.1")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_restituisce_none_su_db_error(self, mgr):
        with patch.object(mgr, "_get_connection", side_effect=Exception("DB giù")):
            result = mgr.register_access(user_id=1, action="LOGIN", esito=True, ip_address=None)
        assert result is None
