"""
tests/unit/test_db_base_audit_fk.py
===================================
Unit test della sanatoria che crea la chiave esterna
audit_log.app_user_id -> utente.id sui database che non ce l'hanno
(db/base.py::_ensure_audit_user_fk).

Qui si verifica la logica dei rami con una connessione simulata, come in
test_db_base_audit_view.py. Il comportamento su un PostgreSQL vero (righe
orfane, NOT VALID, ON DELETE SET NULL) sta in
tests/integration/test_schema_database_nuovo.py.
"""
from __future__ import annotations

import logging
from unittest.mock import MagicMock, patch

import psycopg2
import pytest


pytestmark = pytest.mark.unit


@pytest.fixture
def mgr(tmp_path):
    """CatastoDBManager senza pool, logger reale."""
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
    m.logger = logging.getLogger("test_audit_fk")
    return m


def _make_conn(*, vincolo_presente: bool, tabelle: int = 2, fallisce: str | None = None):
    """
    Connessione simulata.

    vincolo_presente  esito della ricerca in pg_constraint
    tabelle           quante fra audit_log e utente esistono
    fallisce          frammento di SQL la cui esecuzione solleva psycopg2.Error
    """
    cur = MagicMock()
    cur.fetchone.return_value = (1,) if vincolo_presente else None
    cur.rowcount = tabelle

    def execute(sql, *args):
        if fallisce and fallisce in sql:
            raise psycopg2.Error(f"errore simulato su: {fallisce}")

    cur.execute.side_effect = execute

    cursor_cm = MagicMock()
    cursor_cm.__enter__ = MagicMock(return_value=cur)
    cursor_cm.__exit__ = MagicMock(return_value=False)
    conn = MagicMock()
    conn.cursor.return_value = cursor_cm
    conn_cm = MagicMock()
    conn_cm.__enter__ = MagicMock(return_value=conn)
    conn_cm.__exit__ = MagicMock(return_value=False)
    return conn_cm, conn, cur


def _eseguite(cur) -> list[str]:
    return [c.args[0] for c in cur.execute.call_args_list]


class TestEnsureAuditUserFk:

    def test_non_fa_nulla_se_il_vincolo_esiste(self, mgr):
        conn_cm, _, cur = _make_conn(vincolo_presente=True)
        with patch.object(mgr, "_get_connection", return_value=conn_cm):
            mgr._ensure_audit_user_fk()

        eseguite = _eseguite(cur)
        assert any("pg_constraint" in q for q in eseguite)
        assert not any("ALTER TABLE" in q for q in eseguite)

    def test_non_fa_nulla_se_manca_una_delle_due_tabelle(self, mgr):
        conn_cm, _, cur = _make_conn(vincolo_presente=False, tabelle=1)
        with patch.object(mgr, "_get_connection", return_value=conn_cm):
            mgr._ensure_audit_user_fk()

        assert not any("ALTER TABLE" in q for q in _eseguite(cur))

    def test_crea_il_vincolo_senza_convalida_e_poi_lo_convalida(self, mgr):
        conn_cm, _, cur = _make_conn(vincolo_presente=False)
        with patch.object(mgr, "_get_connection", return_value=conn_cm):
            mgr._ensure_audit_user_fk()

        eseguite = _eseguite(cur)
        crea = [q for q in eseguite if "ADD CONSTRAINT" in q]
        assert len(crea) == 1
        assert "catasto.audit_log" in crea[0]
        assert "REFERENCES catasto.utente(id)" in crea[0]
        assert "ON DELETE SET NULL" in crea[0]
        # NOT VALID: la creazione non deve dipendere dallo storico.
        assert crea[0].rstrip().endswith("NOT VALID")

        convalida = [q for q in eseguite if "VALIDATE CONSTRAINT" in q]
        assert len(convalida) == 1
        assert eseguite.index(crea[0]) < eseguite.index(convalida[0])

    def test_l_attesa_del_lock_e_limitata(self, mgr):
        # Senza limite l'avvio resterebbe fermo dietro la transazione di
        # un collega che sta scrivendo sull'archivio.
        conn_cm, _, cur = _make_conn(vincolo_presente=False)
        with patch.object(mgr, "_get_connection", return_value=conn_cm):
            mgr._ensure_audit_user_fk()

        eseguite = _eseguite(cur)
        limite = next(i for i, q in enumerate(eseguite) if "lock_timeout" in q)
        crea = next(i for i, q in enumerate(eseguite) if "ADD CONSTRAINT" in q)
        assert "SET LOCAL" in eseguite[limite]
        assert limite < crea

    def test_con_righe_orfane_il_vincolo_resta_e_lo_storico_non_si_tocca(self, mgr, caplog):
        conn_cm, conn, cur = _make_conn(vincolo_presente=False, fallisce="VALIDATE CONSTRAINT")
        with caplog.at_level(logging.WARNING, logger="test_audit_fk"):
            with patch.object(mgr, "_get_connection", return_value=conn_cm):
                mgr._ensure_audit_user_fk()

        eseguite = _eseguite(cur)
        # Si torna al savepoint: la creazione del vincolo non va persa.
        assert "SAVEPOINT convalida_fk_audit" in eseguite
        assert eseguite[-1] == "ROLLBACK TO SAVEPOINT convalida_fk_audit"
        conn.rollback.assert_not_called()
        # Il registro di audit non viene riscritto.
        assert not any(q.lstrip().upper().startswith(("UPDATE", "DELETE")) for q in eseguite)
        assert "senza convalida" in caplog.text

    def test_se_la_creazione_fallisce_non_tenta_la_convalida(self, mgr, caplog):
        conn_cm, conn, cur = _make_conn(vincolo_presente=False, fallisce="ADD CONSTRAINT")
        with caplog.at_level(logging.WARNING, logger="test_audit_fk"):
            with patch.object(mgr, "_get_connection", return_value=conn_cm):
                mgr._ensure_audit_user_fk()

        conn.rollback.assert_called_once()
        assert not any("VALIDATE CONSTRAINT" in q for q in _eseguite(cur))
        # Il messaggio deve dire a chi legge il log come rimediare.
        assert "23_add_fk_audit_log_utente.sql" in caplog.text

    def test_un_errore_di_connessione_non_blocca_l_avvio(self, mgr):
        with patch.object(mgr, "_get_connection", side_effect=Exception("DB giù")):
            mgr._ensure_audit_user_fk()  # non deve sollevare

    def test_fa_parte_delle_migrazioni_applicate_all_avvio(self, mgr):
        passi = [
            "_apply_v161_localita_migration", "_ensure_mv_ownership",
            "_ensure_mv_unique_indexes", "_ensure_audit_view",
            "_ensure_audit_user_fk", "_ensure_partita_draft_table",
            "_ensure_api_keys_table",
        ]
        chiamati: list[str] = []
        with patch.multiple(
            mgr, **{p: MagicMock(side_effect=lambda p=p: chiamati.append(p)) for p in passi}
        ):
            mgr._apply_pending_schema_migrations()

        assert "_ensure_audit_user_fk" in chiamati
        # Dopo la vista: entrambe presuppongono audit_log e utente.
        assert chiamati.index("_ensure_audit_view") < chiamati.index("_ensure_audit_user_fk")
