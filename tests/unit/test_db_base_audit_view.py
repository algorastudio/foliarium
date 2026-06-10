"""
tests/unit/test_db_base_audit_view.py
=====================================
Unit test del meccanismo di auto-applicazione della vista
catasto.v_audit_dettagliato (db/base.py::_ensure_audit_view).

Riproduce lo stesso pattern di mock di test_db_mixins.py: CatastoDBManager
istanziato via __new__ senza pool, _get_connection patchato per simulare
cursore + risposta.
"""
from __future__ import annotations

import logging
from unittest.mock import MagicMock, patch

import pytest


pytestmark = pytest.mark.unit


@pytest.fixture
def mgr(tmp_path):
    """CatastoDBManager senza pool, logger reale."""
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
    m.logger = logging.getLogger("test_audit_view")
    return m


def _make_conn(*, fetchone_seq=None, rowcount=None):
    """Costruisce mock connessione + cursore. fetchone_seq alimenta le
    successive chiamate a cur.fetchone(); rowcount imposta un valore
    costante su cur.rowcount."""
    mock_cur = MagicMock()
    if fetchone_seq is not None:
        mock_cur.fetchone.side_effect = list(fetchone_seq)
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


class TestEnsureAuditView:

    def test_skips_when_view_already_exists(self, mgr):
        """Se la prima query trova la vista, ritorna senza CREATE VIEW."""
        # fetchone[0] = vista presente
        conn_cm, cur = _make_conn(fetchone_seq=[(1,)])
        with patch.object(mgr, "_get_connection", return_value=conn_cm):
            mgr._ensure_audit_view()
        executed = [c.args[0] for c in cur.execute.call_args_list]
        # Solo la SELECT su information_schema.views — niente CREATE VIEW
        assert any("information_schema.views" in q for q in executed)
        assert not any(q.upper().startswith("CREATE OR REPLACE VIEW") for q in executed)

    def test_skips_when_underlying_tables_missing(self, mgr):
        """Se audit_log o utente non esistono, non tenta la CREATE."""
        # fetchone[0] = vista assente; rowcount=1 → solo una tabella delle due
        conn_cm, cur = _make_conn(fetchone_seq=[None], rowcount=1)
        with patch.object(mgr, "_get_connection", return_value=conn_cm):
            mgr._ensure_audit_view()
        executed = [c.args[0] for c in cur.execute.call_args_list]
        assert not any("CREATE OR REPLACE VIEW" in q for q in executed)

    def test_creates_view_when_missing_and_tables_present(self, mgr):
        """Vista assente + audit_log + utente presenti → CREATE eseguita."""
        # fetchone = None (vista assente), rowcount=2 (entrambe le tabelle)
        conn_cm, cur = _make_conn(fetchone_seq=[None], rowcount=2)
        with patch.object(mgr, "_get_connection", return_value=conn_cm):
            mgr._ensure_audit_view()
        executed = [c.args[0] for c in cur.execute.call_args_list]
        create_calls = [q for q in executed if "CREATE OR REPLACE VIEW" in q]
        assert len(create_calls) == 1
        # Lo schema corretto deve comparire nel CREATE
        assert "catasto.v_audit_dettagliato" in create_calls[0]
        assert "FROM catasto.audit_log al" in create_calls[0]

    def test_does_not_raise_on_db_error(self, mgr):
        """Errore in _get_connection deve essere catturato (best-effort)."""
        with patch.object(mgr, "_get_connection", side_effect=Exception("DB giù")):
            # Non deve sollevare
            mgr._ensure_audit_view()
