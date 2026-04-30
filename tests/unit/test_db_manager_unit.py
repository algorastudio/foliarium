"""
Unit test per CatastoDBManager — metodi senza connessione DB reale.
Marker: unit
"""
import json
import pytest
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch, mock_open


# ---------------------------------------------------------------------------
# Fixture: istanza CatastoDBManager senza pool attivo
# ---------------------------------------------------------------------------

@pytest.fixture
def mgr(tmp_path):
    """CatastoDBManager con pool=None e cache su cartella temporanea."""
    import sys, os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    from catasto_db_manager import CatastoDBManager
    m = CatastoDBManager.__new__(CatastoDBManager)
    m.pool = None
    m.schema = "catasto"
    m.offline_mode = False
    m.offline_cache_timestamp = None
    m._cache_dir = tmp_path
    import logging
    m.logger = logging.getLogger("test_db_manager")
    m._pool_metrics = {
        "total_getconn": 0,
        "total_putconn": 0,
        "connection_errors": 0,
        "last_error_time": None,
    }
    return m


# ---------------------------------------------------------------------------
# Test cache layer
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestCacheLayer:

    def test_save_and_load_cache(self, mgr):
        """_save_cache e _load_cache devono persistere e recuperare dati."""
        data = [{"id": 1, "nome": "Genova"}, {"id": 2, "nome": "Savona"}]
        mgr._save_cache("comuni_test", data)
        loaded, ts = mgr._load_cache("comuni_test")
        assert loaded == data
        assert ts is not None

    def test_load_cache_missing_key(self, mgr):
        """_load_cache deve restituire (None, None) se il file non esiste."""
        data, ts = mgr._load_cache("chiave_inesistente_xyz")
        assert data is None
        assert ts is None

    def test_try_with_cache_online(self, mgr):
        """Se fetch_fn riesce, _try_with_cache salva in cache e offline_mode=False."""
        expected = [1, 2, 3]
        result = mgr._try_with_cache("test_online", lambda: expected)
        assert result == expected
        assert mgr.offline_mode is False
        cached, _ = mgr._load_cache("test_online")
        assert cached == expected

    def test_try_with_cache_fallback(self, mgr):
        """Se fetch_fn fallisce e la cache esiste, restituisce la cache e imposta offline_mode."""
        mgr._save_cache("test_fallback", ["dati_cached"])
        def _fail():
            raise ConnectionError("DB giù")
        result = mgr._try_with_cache("test_fallback", _fail)
        assert result == ["dati_cached"]
        assert mgr.offline_mode is True
        assert mgr.offline_cache_timestamp is not None

    def test_try_with_cache_no_fallback_raises(self, mgr):
        """Se fetch_fn fallisce e non c'è cache, deve rilanciare l'eccezione."""
        def _fail():
            raise RuntimeError("errore grave")
        with pytest.raises(RuntimeError):
            mgr._try_with_cache("chiave_vuota_xyz", _fail)

    def test_cache_file_none_when_no_dir(self, mgr):
        """Se _cache_dir è None, _cache_file restituisce None senza errori."""
        mgr._cache_dir = None
        assert mgr._cache_file("qualsiasi") is None

    def test_save_cache_noop_when_no_dir(self, mgr):
        """_save_cache non solleva eccezioni se _cache_dir è None."""
        mgr._cache_dir = None
        mgr._save_cache("k", [1, 2, 3])  # non deve sollevare


# ---------------------------------------------------------------------------
# Test import partite — parsing CSV
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestImportPartiteCSV:

    def test_csv_parsing_missing_headers(self, mgr, tmp_path):
        """import_partite_from_csv deve sollevare IOError se mancano colonne."""
        csv_file = tmp_path / "bad.csv"
        csv_file.write_text("numero_partita;stato\n1;attiva\n", encoding="utf-8")
        with pytest.raises(IOError, match="Intestazioni mancanti"):
            mgr.import_partite_from_csv(str(csv_file), 1, "Genova")

    def test_xlsx_missing_headers(self, mgr, tmp_path):
        """import_partite_from_xlsx deve sollevare IOError se mancano colonne."""
        import openpyxl
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.append(["numero_partita", "stato"])  # mancano data_impianto e tipo
        ws.append([1, "attiva"])
        xlsx_file = tmp_path / "bad.xlsx"
        wb.save(str(xlsx_file))
        with pytest.raises(IOError, match="Intestazioni mancanti"):
            mgr.import_partite_from_xlsx(str(xlsx_file), 1, "Genova")


# ---------------------------------------------------------------------------
# Test get_genealogia_partita — validazione parametri
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestGetGenealogia:

    def test_invalid_id_raises_value_error(self, mgr):
        """get_genealogia_partita deve sollevare ValueError per ID non validi."""
        with pytest.raises(ValueError):
            mgr.get_genealogia_partita(0)
        with pytest.raises(ValueError):
            mgr.get_genealogia_partita(-1)
        with pytest.raises(ValueError):
            mgr.get_genealogia_partita("abc")  # type: ignore

    def test_no_pool_raises_db_error(self, mgr):
        """Con pool=None get_genealogia_partita solleva DBMError (pool non inizializzato)."""
        from catasto_exceptions import DBMError
        with pytest.raises(DBMError):
            mgr.get_genealogia_partita(1)


# ---------------------------------------------------------------------------
# Test app_paths
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestAppPaths:

    def test_cache_dir_exists(self):
        """CACHE_DIR deve essere creata automaticamente all'import."""
        from app_paths import CACHE_DIR
        assert CACHE_DIR.exists()
        assert CACHE_DIR.is_dir()

    def test_esportazioni_dir_exists(self):
        from app_paths import ESPORTAZIONI_DIR
        assert ESPORTAZIONI_DIR.exists()

    def test_get_resource_path_returns_path(self):
        from app_paths import get_resource_path
        p = get_resource_path("Logo_foliarium_1.png")
        assert str(p).endswith("Logo_foliarium_1.png")
