"""
tests/unit/test_db_charts.py
============================
Unit test del nuovo metodo DBStatsMixin.get_dashboard_charts_data().
Stesso pattern di mock di test_db_drafts.py.
"""
from __future__ import annotations

import logging
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
    m.logger = logging.getLogger("test_charts")
    return m


def _make_conn(fetch_sequence):
    """fetch_sequence è una lista di liste di righe (una per ogni query)."""
    mock_cur = MagicMock()
    mock_cur.fetchall.side_effect = list(fetch_sequence)
    mock_cursor_cm = MagicMock()
    mock_cursor_cm.__enter__ = MagicMock(return_value=mock_cur)
    mock_cursor_cm.__exit__ = MagicMock(return_value=False)
    mock_conn = MagicMock()
    mock_conn.cursor.return_value = mock_cursor_cm
    mock_conn_cm = MagicMock()
    mock_conn_cm.__enter__ = MagicMock(return_value=mock_conn)
    mock_conn_cm.__exit__ = MagicMock(return_value=False)
    return mock_conn_cm, mock_cur


class TestDashboardChartsData:

    def test_aggregates_all_series(self, mgr):
        fetch_seq = [
            # per_epoca
            [{"label": "Regno d'Italia (1861-1945)", "value": 120},
             {"label": "Repubblica (1946+)", "value": 80},
             {"label": "Regno di Sardegna (pre-1861)", "value": 30}],
            # per_tipo
            [{"label": "principale", "value": 200},
             {"label": "secondaria", "value": 30}],
            # per_stato
            [{"label": "attiva", "value": 180},
             {"label": "inattiva", "value": 50}],
            # top_comuni
            [{"label": "Genova", "value": 100},
             {"label": "Savona", "value": 60}],
        ]
        conn_cm, cur = _make_conn(fetch_seq)
        with patch.object(mgr, "_get_connection", return_value=conn_cm):
            data = mgr.get_dashboard_charts_data(top_comuni_limit=10)

        assert set(data.keys()) == {"per_epoca", "per_tipo", "per_stato", "top_comuni"}
        assert data["per_epoca"][0]["value"] == 120
        assert data["per_tipo"][0]["label"] == "Principale"  # capitalize
        assert data["per_stato"][1]["value"] == 50
        assert data["top_comuni"][0]["label"] == "Genova"

    def test_returns_empty_on_db_error(self, mgr):
        with patch.object(mgr, "_get_connection",
                          side_effect=Exception("DB giù")):
            data = mgr.get_dashboard_charts_data()
        assert data == {
            "per_epoca": [], "per_tipo": [],
            "per_stato": [], "top_comuni": [],
        }

    def test_top_comuni_limit_is_passed(self, mgr):
        # 4 query, ultima è top_comuni
        fetch_seq = [[], [], [], []]
        conn_cm, cur = _make_conn(fetch_seq)
        with patch.object(mgr, "_get_connection", return_value=conn_cm):
            mgr.get_dashboard_charts_data(top_comuni_limit=5)
        # L'ultima execute deve avere (5,) come params
        last_call = cur.execute.call_args_list[-1]
        assert last_call.args[1] == (5,)

    def test_capitalize_handles_none_label(self, mgr):
        fetch_seq = [
            [],  # per_epoca
            [{"label": None, "value": 10}],  # per_tipo: label NULL
            [],  # per_stato
            [],  # top_comuni
        ]
        conn_cm, cur = _make_conn(fetch_seq)
        with patch.object(mgr, "_get_connection", return_value=conn_cm):
            data = mgr.get_dashboard_charts_data()
        assert data["per_tipo"][0]["label"] == "N/d"
        assert data["per_tipo"][0]["value"] == 10
