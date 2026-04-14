"""
tests/unit/test_demo_launcher.py
=================================
Unit test per demo_launcher.py — risoluzione percorsi, avvio/arresto
PostgreSQL portabile, gestione directory scrivibili.

Tutti i test mockano subprocess e filesystem per essere offline e senza PostgreSQL.
"""

import json
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch, PropertyMock

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from demo_launcher import (
    DEMO_PG_PORT,
    DEMO_PG_SUPERUSER,
    EmbeddedPostgres,
    _bundle_root,
    _default_data_dir_source,
    _pgsql_bin,
    _writable_data_dir,
    is_embedded_available,
    start_demo_postgres,
    stop_demo_postgres,
)


# ===========================================================================
# Costanti
# ===========================================================================


@pytest.mark.unit
class TestConstants:
    def test_demo_port(self):
        assert DEMO_PG_PORT == 15432

    def test_demo_superuser(self):
        assert DEMO_PG_SUPERUSER == "postgres"


# ===========================================================================
# _bundle_root
# ===========================================================================


@pytest.mark.unit
class TestBundleRoot:
    def test_returns_path(self):
        root = _bundle_root()
        assert isinstance(root, Path)
        assert root.exists()

    def test_development_mode(self):
        """In sviluppo, _bundle_root e' la directory del file sorgente."""
        root = _bundle_root()
        assert (root / "demo_launcher.py").exists()

    @patch("demo_launcher.sys")
    def test_frozen_mode(self, mock_sys):
        mock_sys.frozen = True
        mock_sys.executable = "/opt/Foliarium_Demo/Foliarium_Demo"
        root = _bundle_root()
        assert root == Path("/opt/Foliarium_Demo")


# ===========================================================================
# _pgsql_bin
# ===========================================================================


@pytest.mark.unit
class TestPgsqlBin:
    def test_returns_none_if_missing(self):
        """Nel contesto di test, pgsql/ non esiste."""
        # Potrebbe ritornare None o un Path reale se pgsql/ e' presente
        result = _pgsql_bin()
        if result is not None:
            assert result.exists()

    @patch("demo_launcher._bundle_root")
    def test_returns_path_if_exists(self, mock_root, tmp_path):
        pg_bin = tmp_path / "pgsql" / "bin"
        pg_bin.mkdir(parents=True)
        mock_root.return_value = tmp_path
        result = _pgsql_bin()
        assert result == pg_bin

    @patch("demo_launcher._bundle_root")
    def test_returns_none_if_no_pgsql(self, mock_root, tmp_path):
        mock_root.return_value = tmp_path
        result = _pgsql_bin()
        assert result is None


# ===========================================================================
# _default_data_dir_source
# ===========================================================================


@pytest.mark.unit
class TestDefaultDataDirSource:
    def test_returns_path(self):
        result = _default_data_dir_source()
        assert isinstance(result, Path)
        assert result.name == "demo_data"


# ===========================================================================
# _writable_data_dir
# ===========================================================================


@pytest.mark.unit
class TestWritableDataDir:
    @patch("demo_launcher._default_data_dir_source")
    def test_writable_source_used_directly(self, mock_src, tmp_path):
        data_dir = tmp_path / "demo_data"
        data_dir.mkdir()
        mock_src.return_value = data_dir
        result = _writable_data_dir()
        assert result == data_dir

    @patch("demo_launcher.shutil.copytree")
    @patch("demo_launcher._default_data_dir_source")
    def test_readonly_falls_back_to_appdata(self, mock_src, mock_copytree, tmp_path):
        # Crea una dir sorgente che simula sola lettura
        data_dir = tmp_path / "demo_data"
        data_dir.mkdir()
        mock_src.return_value = data_dir

        # Rende la dir non scrivibile tramite il side_effect di touch
        original_touch = Path.touch

        def fake_touch(self_, *a, **kw):
            if "demo_data" in str(self_) and ".write_test" in str(self_):
                raise PermissionError("Read-only")
            return original_touch(self_, *a, **kw)

        with patch.object(Path, "touch", fake_touch):
            with patch.dict(os.environ, {"LOCALAPPDATA": str(tmp_path / "AppData")}, clear=False):
                result = _writable_data_dir()

        # Verifica che copytree sia stato chiamato
        assert mock_copytree.called


# ===========================================================================
# is_embedded_available
# ===========================================================================


@pytest.mark.unit
class TestIsEmbeddedAvailable:
    @patch("demo_launcher._default_data_dir_source")
    @patch("demo_launcher._pgsql_bin")
    def test_both_present(self, mock_bin, mock_data, tmp_path):
        mock_bin.return_value = tmp_path / "pgsql" / "bin"
        data_dir = tmp_path / "demo_data"
        data_dir.mkdir()
        mock_data.return_value = data_dir
        assert is_embedded_available()

    @patch("demo_launcher._default_data_dir_source")
    @patch("demo_launcher._pgsql_bin")
    def test_no_pgsql(self, mock_bin, mock_data, tmp_path):
        mock_bin.return_value = None
        data_dir = tmp_path / "demo_data"
        data_dir.mkdir()
        mock_data.return_value = data_dir
        assert not is_embedded_available()

    @patch("demo_launcher._default_data_dir_source")
    @patch("demo_launcher._pgsql_bin")
    def test_no_data(self, mock_bin, mock_data, tmp_path):
        mock_bin.return_value = tmp_path / "pgsql" / "bin"
        mock_data.return_value = tmp_path / "nonexistent"
        assert not is_embedded_available()


# ===========================================================================
# EmbeddedPostgres
# ===========================================================================


@pytest.mark.unit
class TestEmbeddedPostgres:
    def test_initial_state(self):
        ep = EmbeddedPostgres()
        assert not ep.is_running
        assert ep.port == DEMO_PG_PORT

    @patch("demo_launcher._pgsql_bin", return_value=None)
    def test_start_no_pgsql(self, _mock):
        ep = EmbeddedPostgres()
        ok, err = ep.start()
        assert not ok
        assert "non trovato" in err.lower()

    @patch("demo_launcher._default_data_dir_source")
    @patch("demo_launcher._pgsql_bin")
    def test_start_no_data_dir(self, mock_bin, mock_data, tmp_path):
        pg_bin = tmp_path / "pgsql" / "bin"
        pg_bin.mkdir(parents=True)
        mock_bin.return_value = pg_bin
        mock_data.return_value = tmp_path / "nonexistent"

        ep = EmbeddedPostgres()
        ok, err = ep.start()
        assert not ok
        assert "dati demo" in err.lower()

    @patch("demo_launcher.subprocess.run")
    @patch("demo_launcher._writable_data_dir")
    @patch("demo_launcher._default_data_dir_source")
    @patch("demo_launcher._pgsql_bin")
    def test_start_success(self, mock_bin, mock_data_src, mock_writable, mock_run, tmp_path):
        pg_bin = tmp_path / "pgsql" / "bin"
        pg_bin.mkdir(parents=True)
        mock_bin.return_value = pg_bin

        data_dir = tmp_path / "demo_data"
        data_dir.mkdir()
        mock_data_src.return_value = data_dir
        mock_writable.return_value = data_dir

        # pg_ctl start returns 0
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stderr = ""
        mock_result.stdout = ""
        mock_run.return_value = mock_result

        ep = EmbeddedPostgres()
        # Mock _wait_ready per evitare di chiamare pg_isready
        with patch.object(ep, "_wait_ready", return_value=True):
            ok, err = ep.start()
        assert ok
        assert err == ""
        assert ep.is_running

    @patch("demo_launcher.subprocess.run")
    @patch("demo_launcher._writable_data_dir")
    @patch("demo_launcher._default_data_dir_source")
    @patch("demo_launcher._pgsql_bin")
    def test_start_pg_ctl_fails(self, mock_bin, mock_data_src, mock_writable, mock_run, tmp_path):
        pg_bin = tmp_path / "pgsql" / "bin"
        pg_bin.mkdir(parents=True)
        mock_bin.return_value = pg_bin

        data_dir = tmp_path / "demo_data"
        data_dir.mkdir()
        mock_data_src.return_value = data_dir
        mock_writable.return_value = data_dir

        mock_result = MagicMock()
        mock_result.returncode = 2
        mock_result.stderr = "FATAL: could not start"
        mock_result.stdout = ""
        mock_run.return_value = mock_result

        ep = EmbeddedPostgres()
        ok, err = ep.start()
        assert not ok
        assert "fallito" in err.lower()

    @patch("demo_launcher.subprocess.run")
    @patch("demo_launcher._writable_data_dir")
    @patch("demo_launcher._default_data_dir_source")
    @patch("demo_launcher._pgsql_bin")
    def test_start_timeout(self, mock_bin, mock_data_src, mock_writable, mock_run, tmp_path):
        import subprocess
        pg_bin = tmp_path / "pgsql" / "bin"
        pg_bin.mkdir(parents=True)
        mock_bin.return_value = pg_bin

        data_dir = tmp_path / "demo_data"
        data_dir.mkdir()
        mock_data_src.return_value = data_dir
        mock_writable.return_value = data_dir

        mock_run.side_effect = subprocess.TimeoutExpired("pg_ctl", 30)

        ep = EmbeddedPostgres()
        ok, err = ep.start()
        assert not ok
        assert "timeout" in err.lower()

    def test_stop_when_not_started(self):
        """Stop su un'istanza non avviata non deve lanciare eccezioni."""
        ep = EmbeddedPostgres()
        ep.stop()  # non deve fallire


# ===========================================================================
# start_demo_postgres / stop_demo_postgres (module-level)
# ===========================================================================


@pytest.mark.unit
class TestModuleLevelFunctions:
    @patch("demo_launcher.EmbeddedPostgres")
    def test_start_sets_env_vars(self, MockEP):
        instance = MagicMock()
        instance.start.return_value = (True, "")
        instance.port = 15432
        MockEP.return_value = instance

        ok, err = start_demo_postgres()
        assert ok
        assert os.environ.get("DEMO_DB_HOST") == "127.0.0.1"
        assert os.environ.get("DEMO_DB_PORT") == "15432"
        assert os.environ.get("DEMO_DB_NAME") == "catasto_storico"

    @patch("demo_launcher.EmbeddedPostgres")
    def test_start_failure(self, MockEP):
        instance = MagicMock()
        instance.start.return_value = (False, "Errore test")
        MockEP.return_value = instance

        ok, err = start_demo_postgres()
        assert not ok
        assert "Errore test" in err

    @patch("demo_launcher._embedded_pg", None)
    def test_stop_when_no_instance(self):
        """stop_demo_postgres con _embedded_pg=None non fallisce."""
        stop_demo_postgres()
