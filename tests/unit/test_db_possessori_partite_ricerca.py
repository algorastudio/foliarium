"""
tests/unit/test_db_possessori_partite_ricerca.py
=================================================
Unit test per db/possessori.py, db/partite.py, db/ricerca.py.

Stesso pattern di test_db_mixins.py:
  - fixture `mgr` → CatastoDBManager senza pool reale
  - make_mock_conn() → factory mock connessione/cursore
  - patch _get_connection() in ogni test
"""

from __future__ import annotations

import csv
import logging
import os
import sys
import pytest
import psycopg2
from contextlib import contextmanager
from datetime import date
from unittest.mock import MagicMock, patch, call

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


# ---------------------------------------------------------------------------
# Fixture comune
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
    m._main_db_conn_params = {"user": "postgres", "host": "localhost", "port": 5432, "dbname": "catasto_storico"}
    m.logger = logging.getLogger("test_mixin")
    return m


# ---------------------------------------------------------------------------
# Helper mock connessione
# ---------------------------------------------------------------------------

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
# TestPossessoriMixin
# ===========================================================================

@pytest.mark.unit
class TestPossessoriMixin:

    def test_check_possessore_exists_trovato(self, mgr):
        """check_possessore_exists restituisce l'ID se il possessore esiste."""
        conn_cm, cur = make_mock_conn(fetchone_val={"id": 7})
        with patch.object(mgr, "_get_connection", return_value=conn_cm):
            result = mgr.check_possessore_exists("Rossi Mario")
        assert result == 7

    def test_check_possessore_exists_non_trovato(self, mgr):
        """check_possessore_exists restituisce None se non trovato."""
        conn_cm, cur = make_mock_conn(fetchone_val=None)
        with patch.object(mgr, "_get_connection", return_value=conn_cm):
            result = mgr.check_possessore_exists("Inesistente")
        assert result is None

    def test_check_possessore_exists_con_comune_id(self, mgr):
        """check_possessore_exists con comune_id usa query con AND comune_id."""
        conn_cm, cur = make_mock_conn(fetchone_val={"id": 3})
        with patch.object(mgr, "_get_connection", return_value=conn_cm):
            result = mgr.check_possessore_exists("Bianchi Giuseppe", comune_id=5)
        assert result == 3
        args, _ = cur.execute.call_args
        assert "comune_id" in args[0]

    def test_check_possessore_exists_db_error_propaga_eccezione(self, mgr):
        """In caso di errore DB, check_possessore_exists propaga l'eccezione."""
        with patch.object(mgr, "_get_connection", side_effect=Exception("DB giù")):
            with pytest.raises(Exception, match="DB giù"):
                mgr.check_possessore_exists("Rossi Mario")

    def test_create_possessore_restituisce_id(self, mgr):
        """create_possessore restituisce l'ID del nuovo possessore inserito."""
        conn_cm, cur = make_mock_conn(fetchone_val=(42,))
        with patch.object(mgr, "_get_connection", return_value=conn_cm):
            result = mgr.create_possessore(
                nome_completo="Rossi Mario",
                comune_riferimento_id=1,
                paternita="fu Giovanni",
                cognome_nome="Rossi Mario"
            )
        assert result == 42

    def test_create_possessore_unique_violation_solleva_dbunique(self, mgr):
        """create_possessore solleva DBUniqueConstraintError su violazione unicità."""
        from catasto_exceptions import DBUniqueConstraintError
        conn_cm, cur = make_mock_conn()
        cur.execute.side_effect = psycopg2.errors.UniqueViolation("dup key")
        with patch.object(mgr, "_get_connection", return_value=conn_cm):
            with pytest.raises(DBUniqueConstraintError):
                mgr.create_possessore("Rossi Mario", comune_riferimento_id=1)

    def test_create_possessore_db_error_solleva_dbmerror(self, mgr):
        """create_possessore solleva DBMError per altri errori DB."""
        from catasto_exceptions import DBMError
        conn_cm, cur = make_mock_conn()
        cur.execute.side_effect = psycopg2.OperationalError("connessione persa")
        with patch.object(mgr, "_get_connection", return_value=conn_cm):
            with pytest.raises(DBMError):
                mgr.create_possessore("Rossi Mario", comune_riferimento_id=1)

    def test_get_partite_per_possessore_restituisce_lista(self, mgr):
        """get_partite_per_possessore restituisce lista di partite."""
        righe = [
            {"id": 10, "numero_partita": 100, "comune_nome": "Savona"},
            {"id": 11, "numero_partita": 200, "comune_nome": "Cairo"},
        ]
        conn_cm, cur = make_mock_conn(rows=righe)
        with patch.object(mgr, "_get_connection", return_value=conn_cm):
            result = mgr.get_partite_per_possessore(possessore_id=5)
        assert len(result) == 2
        assert result[0]["numero_partita"] == 100

    def test_get_partite_per_possessore_id_non_valido_solleva(self, mgr):
        """get_partite_per_possessore con ID <= 0 solleva DBDataError."""
        from catasto_exceptions import DBDataError
        with pytest.raises(DBDataError):
            mgr.get_partite_per_possessore(possessore_id=0)

    def test_get_partite_per_possessore_db_error_propaga_eccezione(self, mgr):
        """get_partite_per_possessore propaga l'eccezione (non psycopg2) in caso di errore DB."""
        with patch.object(mgr, "_get_connection", side_effect=Exception("errore")):
            with pytest.raises(Exception, match="errore"):
                mgr.get_partite_per_possessore(possessore_id=1)

    def test_import_possessori_from_csv_successo(self, mgr, tmp_path):
        """import_possessori_from_csv con file valido restituisce successi."""
        csv_file = tmp_path / "possessori.csv"
        csv_file.write_text(
            "cognome_nome;nome_completo;paternita\n"
            "Rossi Mario;Rossi Mario fu Giovanni;fu Giovanni\n"
            "Bianchi Giuseppe;Bianchi Giuseppe;",
            encoding="utf-8"
        )
        # Mock: fetchone restituisce None (non esiste) poi (1,) come ID
        mock_cur = MagicMock()
        mock_cur.fetchone.side_effect = [None, (1,), None, (2,)]
        mock_cursor_cm = MagicMock()
        mock_cursor_cm.__enter__ = MagicMock(return_value=mock_cur)
        mock_cursor_cm.__exit__ = MagicMock(return_value=False)
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor_cm
        mock_conn_cm = MagicMock()
        mock_conn_cm.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn_cm.__exit__ = MagicMock(return_value=False)

        with patch.object(mgr, "_get_connection", return_value=mock_conn_cm):
            result = mgr.import_possessori_from_csv(str(csv_file), comune_id=1, comune_nome="Savona")
        assert len(result["success"]) == 2
        assert len(result["errors"]) == 0

    def test_import_possessori_from_csv_file_non_trovato(self, mgr):
        """import_possessori_from_csv con file inesistente solleva FileNotFoundError."""
        with pytest.raises((FileNotFoundError, IOError)):
            mgr.import_possessori_from_csv("/tmp/inesistente_xyz.csv", 1, "Savona")

    def test_import_possessori_from_csv_intestazioni_mancanti(self, mgr, tmp_path):
        """import_possessori_from_csv con intestazioni errate solleva IOError."""
        csv_file = tmp_path / "bad.csv"
        csv_file.write_text("nome;cognome\nMario;Rossi", encoding="utf-8")
        with pytest.raises(IOError):
            mgr.import_possessori_from_csv(str(csv_file), 1, "Savona")

    def test_get_possessori_per_partita_restituisce_lista(self, mgr):
        """get_possessori_per_partita restituisce lista di possessori."""
        righe = [{"id": 1, "nome_completo": "Rossi Mario", "titolo": "proprietario"}]
        conn_cm, cur = make_mock_conn(rows=righe)
        with patch.object(mgr, "_get_connection", return_value=conn_cm):
            result = mgr.get_possessori_per_partita(partita_id=10)
        assert len(result) == 1
        assert result[0]["nome_completo"] == "Rossi Mario"


# ===========================================================================
# TestPartiteMixin
# ===========================================================================

@pytest.mark.unit
class TestPartiteMixin:

    def test_create_partita_restituisce_id(self, mgr):
        """create_partita restituisce l'ID della nuova partita."""
        conn_cm, cur = make_mock_conn(fetchone_val=(99,))
        with patch.object(mgr, "_get_connection", return_value=conn_cm):
            result = mgr.create_partita(
                comune_id=1,
                numero_partita=100,
                tipo="principale",
                stato="attiva",
                data_impianto=date(1900, 1, 1)
            )
        assert result == 99

    def test_create_partita_dati_mancanti_solleva_dbdata(self, mgr):
        """create_partita con dati mancanti solleva DBDataError."""
        from catasto_exceptions import DBDataError
        with pytest.raises(DBDataError):
            mgr.create_partita(
                comune_id=0,
                numero_partita=0,
                tipo="",
                stato="",
                data_impianto=None
            )

    def test_create_partita_unique_violation(self, mgr):
        """create_partita solleva DBUniqueConstraintError su duplicato."""
        from catasto_exceptions import DBUniqueConstraintError
        conn_cm, cur = make_mock_conn()
        cur.execute.side_effect = psycopg2.errors.UniqueViolation("dup")
        with patch.object(mgr, "_get_connection", return_value=conn_cm):
            with pytest.raises(DBUniqueConstraintError):
                mgr.create_partita(1, 100, "principale", "attiva", date(1900, 1, 1))

    def test_insert_partite_records_lista_vuota(self, mgr):
        """_insert_partite_records con lista vuota restituisce success=[], errors=[]."""
        result = mgr._insert_partite_records([], comune_id=1, comune_nome="Savona")
        assert result == {"success": [], "errors": []}

    def test_insert_partite_records_inserimento_ok(self, mgr):
        """_insert_partite_records con record valido restituisce un successo."""
        records = [{"numero_partita": "100", "data_impianto": "1900-01-01",
                    "stato": "attiva", "tipo": "principale"}]
        mock_cur = MagicMock()
        # SAVEPOINT, SELECT (no duplicato=None), INSERT, RELEASE SAVEPOINT
        mock_cur.fetchone.side_effect = [None, (42,)]
        mock_cursor_cm = MagicMock()
        mock_cursor_cm.__enter__ = MagicMock(return_value=mock_cur)
        mock_cursor_cm.__exit__ = MagicMock(return_value=False)
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor_cm
        mock_conn_cm = MagicMock()
        mock_conn_cm.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn_cm.__exit__ = MagicMock(return_value=False)

        with patch.object(mgr, "_get_connection", return_value=mock_conn_cm):
            result = mgr._insert_partite_records(records, comune_id=1, comune_nome="Savona")
        assert len(result["success"]) == 1
        assert len(result["errors"]) == 0

    def test_insert_partite_records_duplicato_va_in_errori(self, mgr):
        """_insert_partite_records con partita già esistente mette la riga in errors."""
        records = [{"numero_partita": "100", "data_impianto": "1900-01-01",
                    "stato": "attiva", "tipo": "principale"}]
        mock_cur = MagicMock()
        # SAVEPOINT ok, SELECT restituisce riga (duplicato), ROLLBACK TO SAVEPOINT
        mock_cur.fetchone.return_value = (1,)  # duplicato trovato
        mock_cursor_cm = MagicMock()
        mock_cursor_cm.__enter__ = MagicMock(return_value=mock_cur)
        mock_cursor_cm.__exit__ = MagicMock(return_value=False)
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor_cm
        mock_conn_cm = MagicMock()
        mock_conn_cm.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn_cm.__exit__ = MagicMock(return_value=False)

        with patch.object(mgr, "_get_connection", return_value=mock_conn_cm):
            result = mgr._insert_partite_records(records, comune_id=1, comune_nome="Savona")
        assert len(result["errors"]) == 1
        assert len(result["success"]) == 0

    def test_get_partite_by_comune_restituisce_lista(self, mgr):
        """get_partite_by_comune restituisce lista di partite per il comune."""
        righe = [
            {"id": 1, "numero_partita": 100, "stato": "attiva"},
            {"id": 2, "numero_partita": 200, "stato": "inattiva"},
        ]
        conn_cm, cur = make_mock_conn(rows=righe)
        with patch.object(mgr, "_get_connection", return_value=conn_cm):
            result = mgr.get_partite_by_comune(comune_id=1)
        assert len(result) == 2

    def test_get_partite_by_comune_db_error_propaga_eccezione(self, mgr):
        """get_partite_by_comune propaga l'eccezione (non psycopg2) in caso di errore DB."""
        with patch.object(mgr, "_get_connection", side_effect=Exception("errore")):
            with pytest.raises(Exception, match="errore"):
                mgr.get_partite_by_comune(comune_id=1)

    def test_get_partita_details_trovata(self, mgr):
        """get_partita_details restituisce dict con i dettagli della partita."""
        conn_cm, cur = make_mock_conn(fetchone_val={
            "id": 5, "numero_partita": 100, "stato": "attiva", "comune_nome": "Savona"
        })
        with patch.object(mgr, "_get_connection", return_value=conn_cm):
            result = mgr.get_partita_details(partita_id=5)
        assert result is not None
        assert result["numero_partita"] == 100

    def test_get_partita_details_non_trovata_solleva_dbnotfound(self, mgr):
        """get_partita_details solleva DBNotFoundError se la partita non esiste."""
        from catasto_exceptions import DBNotFoundError
        conn_cm, cur = make_mock_conn(fetchone_val=None)
        with patch.object(mgr, "_get_connection", return_value=conn_cm):
            with pytest.raises(DBNotFoundError):
                mgr.get_partita_details(partita_id=9999)

    def test_import_partite_from_csv_intestazioni_errate(self, mgr, tmp_path):
        """import_partite_from_csv con intestazioni errate solleva IOError."""
        csv_file = tmp_path / "bad.csv"
        csv_file.write_text("colonna_a;colonna_b\nval1;val2", encoding="utf-8")
        with pytest.raises(IOError):
            mgr.import_partite_from_csv(str(csv_file), comune_id=1, comune_nome="Savona")

    def test_import_partite_from_csv_file_valido(self, mgr, tmp_path):
        """import_partite_from_csv con file corretto chiama _insert_partite_records."""
        csv_file = tmp_path / "partite.csv"
        csv_file.write_text(
            "numero_partita;data_impianto;stato;tipo\n100;1900-01-01;attiva;principale\n",
            encoding="utf-8"
        )
        with patch.object(mgr, "_insert_partite_records", return_value={"success": [{}], "errors": []}) as mock_ins:
            result = mgr.import_partite_from_csv(str(csv_file), comune_id=1, comune_nome="Savona")
        mock_ins.assert_called_once()
        assert len(result["success"]) == 1

    def test_get_genealogia_partita_restituisce_struttura(self, mgr):
        """get_genealogia_partita restituisce dizionario con chiavi partita/predecessori/successori."""
        # Il metodo usa fetchall() con una CTE che include la colonna 'relazione'
        rows = [
            {
                "id": 1, "numero_partita": 100, "suffisso_partita": None,
                "tipo": "Principale", "stato": "Attiva",
                "data_impianto": None, "data_chiusura": None,
                "comune_nome": "Savona", "possessori": "Rossi Mario",
                "tipo_variazione": None, "data_variazione": None,
                "nominativo_riferimento": None,
                "relazione": "centrale",
            }
        ]
        conn_cm, cur = make_mock_conn(rows=rows)
        with patch.object(mgr, "_get_connection", return_value=conn_cm):
            result = mgr.get_genealogia_partita(partita_id=1)
        assert result is not None
        assert "partita" in result
        assert "predecessori" in result
        assert "successori" in result

    def test_get_genealogia_partita_non_trovata_solleva_dbnotfound(self, mgr):
        """get_genealogia_partita solleva DBNotFoundError se la partita non esiste."""
        from catasto_exceptions import DBNotFoundError
        conn_cm, cur = make_mock_conn(rows=[])
        with patch.object(mgr, "_get_connection", return_value=conn_cm):
            with pytest.raises(DBNotFoundError):
                mgr.get_genealogia_partita(partita_id=9999)

    def test_search_partite_restituisce_lista(self, mgr):
        """search_partite restituisce lista di risultati."""
        righe = [{"id": 1, "numero_partita": 100, "comune_nome": "Savona"}]
        conn_cm, cur = make_mock_conn(rows=righe)
        with patch.object(mgr, "_get_connection", return_value=conn_cm):
            result = mgr.search_partite(numero_partita=100)
        assert isinstance(result, list)

    def test_get_partita_data_for_export_id_non_valido_solleva_valueerror(self, mgr):
        """get_partita_data_for_export con ID non valido solleva ValueError."""
        with pytest.raises(ValueError):
            mgr.get_partita_data_for_export(partita_id=-1)

    def test_get_partita_data_for_export_ok(self, mgr):
        """get_partita_data_for_export restituisce i dati dal DB."""
        conn_cm, cur = make_mock_conn(fetchone_val={"partita_data": {"id": 1, "numero": 100}})
        with patch.object(mgr, "_get_connection", return_value=conn_cm):
            result = mgr.get_partita_data_for_export(partita_id=1)
        assert result is not None
        assert result["numero"] == 100


# ===========================================================================
# TestSearchMixin
# ===========================================================================

@pytest.mark.unit
class TestSearchMixin:

    def test_ricerca_avanzata_immobili_senza_filtri(self, mgr):
        """ricerca_avanzata_immobili_gui senza filtri restituisce lista."""
        righe = [{"id_immobile": 1, "numero_partita": 100, "comune_nome": "Savona"}]
        conn_cm, cur = make_mock_conn(rows=righe)
        with patch.object(mgr, "_get_connection", return_value=conn_cm):
            result = mgr.ricerca_avanzata_immobili_gui()
        assert isinstance(result, list)
        assert len(result) == 1

    def test_ricerca_avanzata_immobili_con_filtro_comune(self, mgr):
        """ricerca_avanzata_immobili_gui con comune_id aggiunge clausola WHERE."""
        conn_cm, cur = make_mock_conn(rows=[])
        with patch.object(mgr, "_get_connection", return_value=conn_cm):
            mgr.ricerca_avanzata_immobili_gui(comune_id=3)
        args, _ = cur.execute.call_args
        assert "comune_id" in args[0]

    def test_ricerca_avanzata_immobili_con_filtro_natura(self, mgr):
        """ricerca_avanzata_immobili_gui con natura_search aggiunge ILIKE."""
        conn_cm, cur = make_mock_conn(rows=[])
        with patch.object(mgr, "_get_connection", return_value=conn_cm):
            mgr.ricerca_avanzata_immobili_gui(natura_search="fabbricato")
        args, _ = cur.execute.call_args
        assert "ILIKE" in args[0] or "ilike" in args[0].lower()

    def test_ricerca_avanzata_immobili_db_error_solleva_dbmerror(self, mgr):
        """ricerca_avanzata_immobili_gui solleva DBMError in caso di errore OperationalError."""
        from catasto_exceptions import DBMError
        import psycopg2
        with patch.object(mgr, "_get_connection", side_effect=psycopg2.OperationalError("err")):
            with pytest.raises(DBMError):
                mgr.ricerca_avanzata_immobili_gui()

    def test_search_all_entities_fuzzy_restituisce_dict(self, mgr):
        """search_all_entities_fuzzy restituisce dict con chiavi per tipo entità."""
        conn_cm, cur = make_mock_conn(rows=[])
        with patch.object(mgr, "_get_connection", return_value=conn_cm):
            result = mgr.search_all_entities_fuzzy("Savona")
        assert isinstance(result, dict)
        assert "possessore" in result
        assert "localita" in result
        assert "immobile" in result

    def test_search_all_entities_fuzzy_risultati(self, mgr):
        """search_all_entities_fuzzy include i risultati trovati per ogni tipo."""
        riga = [{"entity_id": 1, "display_text": "Rossi Mario", "similarity_score": 0.8}]
        conn_cm, cur = make_mock_conn(rows=riga)
        with patch.object(mgr, "_get_connection", return_value=conn_cm):
            result = mgr.search_all_entities_fuzzy("Rossi")
        # Almeno uno dei tipi ha risultati
        total = sum(len(v) for v in result.values())
        assert total > 0

    def test_search_all_entities_fuzzy_pool_error_propaga_eccezione(self, mgr):
        """search_all_entities_fuzzy propaga PoolError in caso di errore pool."""
        with patch.object(mgr, "_get_connection", side_effect=psycopg2.pool.PoolError("pool esaurito")):
            with pytest.raises(psycopg2.pool.PoolError):
                mgr.search_all_entities_fuzzy("test")

    def test_search_all_entities_fuzzy_flag_disabilitati(self, mgr):
        """search_all_entities_fuzzy con tutti i flag a False non esegue query."""
        conn_cm, cur = make_mock_conn(rows=[])
        with patch.object(mgr, "_get_connection", return_value=conn_cm):
            result = mgr.search_all_entities_fuzzy(
                "test",
                search_possessori=False,
                search_localita=False,
                search_immobili=False,
                search_variazioni=False,
                search_contratti=False,
                search_partite=False,
            )
        # Nessuna query interna eseguita
        cur.execute.assert_not_called()
        # Tutte le liste vuote
        assert all(len(v) == 0 for v in result.values())

    def test_verify_gin_indices_restituisce_dict(self, mgr):
        """verify_gin_indices restituisce un dict con stato."""
        righe = [{"schemaname": "catasto", "tablename": "possessore", "indexname": "idx_gin"}]
        conn_cm, cur = make_mock_conn(rows=righe)
        with patch.object(mgr, "_get_connection", return_value=conn_cm):
            result = mgr.verify_gin_indices()
        assert isinstance(result, dict)
        assert "status" in result

    def test_verify_gin_indices_db_error_propaga_eccezione(self, mgr):
        """verify_gin_indices propaga l'eccezione in caso di errore DB."""
        with patch.object(mgr, "_get_connection", side_effect=Exception("errore")):
            with pytest.raises(Exception, match="errore"):
                mgr.verify_gin_indices()
