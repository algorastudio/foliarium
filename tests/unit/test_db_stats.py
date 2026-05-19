"""
tests/unit/test_db_stats.py
===========================
Unit test del mixin DBStatsMixin (db/stats.py).

db/stats.py era una delle "aree fredde" (14% coverage post-Sprint 3.9).
Questi test mockano _get_connection e _try_with_cache per esercitare
il flusso di controllo principale di:

  - get_statistiche_comune       (legge mv_statistiche_comune)
  - get_dashboard_stats          (4 COUNT in singola query)
  - get_ultimi_inserimenti_dashboard
  - get_last_mv_refresh_timestamp / update_last_mv_refresh_timestamp
  - _get_base_tables_max_timestamp
  - _should_refresh_materialized_views

Non si testa refresh_materialized_views (apre QProgressDialog, fuori scope).
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest


pytestmark = pytest.mark.unit


@pytest.fixture
def mgr(tmp_path):
    """CatastoDBManager via __new__ senza pool."""
    import sys, os
    sys.path.insert(
        0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    )
    from catasto_db_manager import CatastoDBManager
    m = CatastoDBManager.__new__(CatastoDBManager)
    m.pool = None
    m.schema = "catasto"
    m.offline_mode = False
    m.offline_cache_timestamp = None
    m._cache_dir = tmp_path
    m.logger = logging.getLogger("test_db_stats")
    return m


def _make_conn(*, fetchone_val=None, fetchall_rows=None):
    cur = MagicMock()
    cur.fetchone.return_value = fetchone_val
    cur.fetchall.return_value = fetchall_rows or []

    cursor_cm = MagicMock()
    cursor_cm.__enter__ = MagicMock(return_value=cur)
    cursor_cm.__exit__ = MagicMock(return_value=False)

    conn = MagicMock()
    conn.cursor.return_value = cursor_cm

    conn_cm = MagicMock()
    conn_cm.__enter__ = MagicMock(return_value=conn)
    conn_cm.__exit__ = MagicMock(return_value=False)
    return conn_cm, cur


# ===========================================================================
# get_dashboard_stats
# ===========================================================================

class TestGetDashboardStats:

    def test_query_singola_aggrega_quattro_count(self, mgr):
        """4 COUNT in una sola query, ritorna dict con i 4 totali."""
        conn_cm, cur = _make_conn(fetchone_val={
            "total_comuni": 10, "total_partite": 50,
            "total_possessori": 30, "total_immobili": 100,
        })
        with patch.object(mgr, "_get_connection", return_value=conn_cm):
            stats = mgr.get_dashboard_stats()
        assert stats["total_comuni"] == 10
        assert stats["total_partite"] == 50
        assert stats["total_possessori"] == 30
        assert stats["total_immobili"] == 100

    def test_error_returns_zeros(self, mgr):
        """Qualsiasi exception → ritorna dict con zeri (best-effort)."""
        with patch.object(mgr, "_get_connection", side_effect=Exception("DB giu'")):
            stats = mgr.get_dashboard_stats()
        # Tutti zeri, non None
        assert stats == {
            "total_comuni": 0, "total_partite": 0,
            "total_possessori": 0, "total_immobili": 0,
        }


# ===========================================================================
# get_ultimi_inserimenti_dashboard
# ===========================================================================

class TestGetUltimiInserimentiDashboard:

    def test_struttura_ritorno_con_dati(self, mgr):
        """Ritorna dict con 3 chiavi: comuni, partite, possessori."""
        # Tre execute con tre fetchall differenti
        cur = MagicMock()
        cur.fetchall.side_effect = [
            [{"nome": "Genova", "provincia": "GE"}],
            [{"numero_partita": 100, "comune": "Savona"}],
            [{"cognome_nome": "Rossi", "nome_completo": "Rossi Mario"}],
        ]
        cursor_cm = MagicMock()
        cursor_cm.__enter__ = MagicMock(return_value=cur)
        cursor_cm.__exit__ = MagicMock(return_value=False)
        conn = MagicMock(); conn.cursor.return_value = cursor_cm
        conn_cm = MagicMock()
        conn_cm.__enter__ = MagicMock(return_value=conn)
        conn_cm.__exit__ = MagicMock(return_value=False)

        with patch.object(mgr, "_get_connection", return_value=conn_cm):
            result = mgr.get_ultimi_inserimenti_dashboard(limit=3)
        assert set(result.keys()) == {"comuni", "partite", "possessori"}
        assert len(result["comuni"]) == 1
        assert len(result["partite"]) == 1
        assert len(result["possessori"]) == 1

    def test_db_error_returns_empty_struct(self, mgr):
        """DB error → ritorna dict con liste vuote."""
        with patch.object(mgr, "_get_connection", side_effect=Exception("boom")):
            result = mgr.get_ultimi_inserimenti_dashboard()
        assert result == {"comuni": [], "partite": [], "possessori": []}


# ===========================================================================
# get_statistiche_comune (passa per _try_with_cache)
# ===========================================================================

class TestGetStatisticheComune:

    def test_delegates_to_try_with_cache(self, mgr):
        """_try_with_cache viene chiamato con il fetcher giusto."""
        with patch.object(
            mgr, "_try_with_cache",
            return_value=[{"comune": "Genova", "n_partite": 5}],
        ) as mock_cache:
            result = mgr.get_statistiche_comune()
        assert result == [{"comune": "Genova", "n_partite": 5}]
        assert mock_cache.called
        # Verifica che la cache key sia quella attesa
        args = mock_cache.call_args
        assert args[0][0] == "statistiche_comune"


# ===========================================================================
# Timestamp MV refresh
# ===========================================================================

class TestMVRefreshTimestamps:

    def test_get_last_mv_refresh_ritorna_datetime(self, mgr):
        ts = datetime(2026, 1, 1, 12, 0, 0)
        conn_cm, cur = _make_conn(fetchone_val=(ts,))
        with patch.object(mgr, "_get_connection", return_value=conn_cm):
            result = mgr.get_last_mv_refresh_timestamp()
        assert result == ts

    def test_get_last_mv_refresh_none_se_assente(self, mgr):
        conn_cm, cur = _make_conn(fetchone_val=None)
        with patch.object(mgr, "_get_connection", return_value=conn_cm):
            result = mgr.get_last_mv_refresh_timestamp()
        assert result is None

    def test_get_last_mv_refresh_db_error_none(self, mgr):
        with patch.object(mgr, "_get_connection", side_effect=Exception("boom")):
            result = mgr.get_last_mv_refresh_timestamp()
        assert result is None

    def test_update_last_mv_refresh_invoca_execute(self, mgr):
        conn_cm, cur = _make_conn()
        with patch.object(mgr, "_get_connection", return_value=conn_cm):
            mgr.update_last_mv_refresh_timestamp()
        # cur.execute deve essere stato chiamato (UPSERT in app_metadata)
        assert cur.execute.called


# ===========================================================================
# _should_refresh_materialized_views (logica di staleness)
# ===========================================================================

class TestShouldRefreshMaterializedViews:

    def test_refresh_se_last_timestamp_assente(self, mgr):
        """Senza timestamp registrato → refresh raccomandato."""
        with patch.object(mgr, "get_last_mv_refresh_timestamp", return_value=None):
            assert mgr._should_refresh_materialized_views() is True

    def test_no_refresh_se_dati_piu_vecchi_di_mv(self, mgr):
        """MV piu' recente delle tabelle → no refresh."""
        now = datetime.now(timezone.utc) if datetime.now(timezone.utc).tzinfo else datetime.now()
        mv_ts = now
        base_ts = now - timedelta(hours=1)
        with patch.object(mgr, "get_last_mv_refresh_timestamp", return_value=mv_ts), \
             patch.object(mgr, "_get_base_tables_max_timestamp", return_value=base_ts):
            assert mgr._should_refresh_materialized_views() is False

    def test_refresh_se_dati_piu_recenti_di_mv(self, mgr):
        """Tabelle base modificate dopo MV → refresh raccomandato."""
        now = datetime.now()
        mv_ts = now - timedelta(hours=2)
        base_ts = now - timedelta(minutes=5)
        with patch.object(mgr, "get_last_mv_refresh_timestamp", return_value=mv_ts), \
             patch.object(mgr, "_get_base_tables_max_timestamp", return_value=base_ts):
            assert mgr._should_refresh_materialized_views(min_interval_minutes=10) is True
