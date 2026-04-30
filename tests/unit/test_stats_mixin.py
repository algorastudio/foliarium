"""
tests/unit/test_stats_mixin.py
===============================
Unit test per db/stats.py — DBStatsMixin.
Stesso pattern: CatastoDBManager senza pool reale, _get_connection patchato.
Marker: unit
"""
from __future__ import annotations

import logging
import pytest
import sys
import os
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch, call

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


# ---------------------------------------------------------------------------
# Fixtures
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
        "total_getconn": 0,
        "total_putconn": 0,
        "connection_errors": 0,
        "last_error_time": None,
    }
    m.logger = logging.getLogger("test_stats")
    return m


def make_mock_conn(rows=None, fetchone_val=None):
    mock_cur = MagicMock()
    mock_cur.fetchall.return_value = rows if rows is not None else []
    mock_cur.fetchone.return_value = fetchone_val
    mock_cur.rowcount = 1

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
# TestGetStatisticheComune
# ===========================================================================

@pytest.mark.unit
class TestGetStatisticheComune:

    def test_restituisce_lista_da_db(self, mgr):
        righe = [
            {"comune": "Savona", "totale_partite": 100},
            {"comune": "Genova", "totale_partite": 200},
        ]
        conn_cm, cur = make_mock_conn(rows=righe)
        with patch.object(mgr, "_get_connection", return_value=conn_cm):
            result = mgr.get_statistiche_comune()
        assert isinstance(result, list)
        assert len(result) == 2

    def test_restituisce_lista_vuota_se_db_error(self, mgr):
        with patch.object(mgr, "_get_connection", side_effect=Exception("DB giù")):
            result = mgr.get_statistiche_comune()
        assert result == []

    def test_usa_cache_se_disponibile(self, mgr, tmp_path):
        """Se la cache è disponibile e il DB fallisce, usa la cache."""
        cached = [{"comune": "Savona", "totale_partite": 50}]
        mgr._save_cache("statistiche_comune", cached)
        with patch.object(mgr, "_get_connection", side_effect=Exception("offline")):
            result = mgr.get_statistiche_comune()
        assert result == cached


# ===========================================================================
# TestGetDashboardStats
# ===========================================================================

@pytest.mark.unit
class TestGetDashboardStats:

    def test_restituisce_dict_con_conteggi(self, mgr):
        row = {
            "total_comuni": 10,
            "total_partite": 500,
            "total_possessori": 300,
            "total_immobili": 800,
        }
        conn_cm, cur = make_mock_conn(fetchone_val=row)
        with patch.object(mgr, "_get_connection", return_value=conn_cm):
            result = mgr.get_dashboard_stats()
        assert result["total_comuni"] == 10
        assert result["total_partite"] == 500
        assert result["total_possessori"] == 300
        assert result["total_immobili"] == 800

    def test_restituisce_zeri_se_db_error(self, mgr):
        with patch.object(mgr, "_get_connection", side_effect=Exception("DB giù")):
            result = mgr.get_dashboard_stats()
        assert result["total_comuni"] == 0
        assert result["total_partite"] == 0
        assert result["total_possessori"] == 0
        assert result["total_immobili"] == 0

    def test_restituisce_zeri_se_nessuna_riga(self, mgr):
        conn_cm, cur = make_mock_conn(fetchone_val=None)
        with patch.object(mgr, "_get_connection", return_value=conn_cm):
            result = mgr.get_dashboard_stats()
        assert result["total_comuni"] == 0

    def test_ha_tutte_le_chiavi_attese(self, mgr):
        with patch.object(mgr, "_get_connection", side_effect=Exception("offline")):
            result = mgr.get_dashboard_stats()
        for key in ["total_comuni", "total_partite", "total_possessori", "total_immobili"]:
            assert key in result


# ===========================================================================
# TestGetUltimiInserimentiDashboard
# ===========================================================================

@pytest.mark.unit
class TestGetUltimiInserimentiDashboard:

    def test_restituisce_struttura_corretta(self, mgr):
        mock_cur = MagicMock()
        # Simula 3 chiamate a fetchall: comuni, partite, possessori
        mock_cur.fetchall.side_effect = [
            [{"nome": "Savona", "provincia": "SV"}],
            [{"numero_partita": 100, "comune": "Savona"}],
            [{"cognome_nome": "Rossi", "nome_completo": "Rossi Mario"}],
        ]

        mock_cursor_cm = MagicMock()
        mock_cursor_cm.__enter__ = MagicMock(return_value=mock_cur)
        mock_cursor_cm.__exit__ = MagicMock(return_value=False)
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor_cm
        mock_conn_cm = MagicMock()
        mock_conn_cm.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn_cm.__exit__ = MagicMock(return_value=False)

        with patch.object(mgr, "_get_connection", return_value=mock_conn_cm):
            result = mgr.get_ultimi_inserimenti_dashboard(limit=1)

        assert "comuni" in result
        assert "partite" in result
        assert "possessori" in result
        assert len(result["comuni"]) == 1

    def test_restituisce_struttura_vuota_se_db_error(self, mgr):
        with patch.object(mgr, "_get_connection", side_effect=Exception("offline")):
            result = mgr.get_ultimi_inserimenti_dashboard()
        assert result == {"comuni": [], "partite": [], "possessori": []}


# ===========================================================================
# TestGetLastMvRefreshTimestamp
# ===========================================================================

@pytest.mark.unit
class TestGetLastMvRefreshTimestamp:

    def test_restituisce_datetime_se_trovato(self, mgr):
        ts = datetime(2024, 1, 15, 10, 30)
        conn_cm, cur = make_mock_conn(fetchone_val=(ts,))
        with patch.object(mgr, "_get_connection", return_value=conn_cm):
            result = mgr.get_last_mv_refresh_timestamp()
        assert result == ts

    def test_restituisce_none_se_nessuna_riga(self, mgr):
        conn_cm, cur = make_mock_conn(fetchone_val=None)
        with patch.object(mgr, "_get_connection", return_value=conn_cm):
            result = mgr.get_last_mv_refresh_timestamp()
        assert result is None

    def test_restituisce_none_se_undefined_table(self, mgr):
        import psycopg2.errors
        with patch.object(mgr, "_get_connection", side_effect=psycopg2.errors.UndefinedTable("table missing")):
            result = mgr.get_last_mv_refresh_timestamp()
        assert result is None

    def test_restituisce_none_su_errore_generico(self, mgr):
        with patch.object(mgr, "_get_connection", side_effect=Exception("generic error")):
            result = mgr.get_last_mv_refresh_timestamp()
        assert result is None


# ===========================================================================
# TestShouldRefreshMaterializedViews
# ===========================================================================

@pytest.mark.unit
class TestShouldRefreshMaterializedViews:

    def test_restituisce_true_se_mai_aggiornate(self, mgr):
        with patch.object(mgr, "get_last_mv_refresh_timestamp", return_value=None):
            result = mgr._should_refresh_materialized_views(min_interval_minutes=10)
        assert result is True

    def test_restituisce_true_se_troppo_tempo_passato(self, mgr):
        old_ts = datetime.utcnow() - timedelta(hours=1)
        with patch.object(mgr, "get_last_mv_refresh_timestamp", return_value=old_ts):
            with patch.object(mgr, "_get_base_tables_max_timestamp", return_value=None):
                result = mgr._should_refresh_materialized_views(min_interval_minutes=10)
        assert result is True

    def test_restituisce_false_se_recente(self, mgr):
        recent_ts = datetime.utcnow() - timedelta(seconds=30)
        with patch.object(mgr, "get_last_mv_refresh_timestamp", return_value=recent_ts):
            with patch.object(mgr, "_get_base_tables_max_timestamp", return_value=None):
                result = mgr._should_refresh_materialized_views(min_interval_minutes=10)
        assert result is False


# ===========================================================================
# TestGetBaseTablesMaxTimestamp
# ===========================================================================

@pytest.mark.unit
class TestGetBaseTablesMaxTimestamp:

    def test_restituisce_datetime(self, mgr):
        ts = datetime(2024, 3, 1)
        conn_cm, cur = make_mock_conn(fetchone_val=(ts,))
        with patch.object(mgr, "_get_connection", return_value=conn_cm):
            result = mgr._get_base_tables_max_timestamp()
        assert result == ts

    def test_restituisce_none_se_nessuna_riga(self, mgr):
        conn_cm, cur = make_mock_conn(fetchone_val=None)
        with patch.object(mgr, "_get_connection", return_value=conn_cm):
            result = mgr._get_base_tables_max_timestamp()
        assert result is None

    def test_restituisce_none_su_errore(self, mgr):
        with patch.object(mgr, "_get_connection", side_effect=Exception("DB giù")):
            result = mgr._get_base_tables_max_timestamp()
        assert result is None


# ===========================================================================
# TestUpdateLastMvRefreshTimestamp
# ===========================================================================

@pytest.mark.unit
class TestUpdateLastMvRefreshTimestamp:

    def test_chiama_execute(self, mgr):
        conn_cm, cur = make_mock_conn()
        with patch.object(mgr, "_get_connection", return_value=conn_cm):
            mgr.update_last_mv_refresh_timestamp()
        cur.execute.assert_called_once()

    def test_non_solleva_eccezione_su_db_error(self, mgr):
        with patch.object(mgr, "_get_connection", side_effect=Exception("DB giù")):
            # Should not raise
            mgr.update_last_mv_refresh_timestamp()
