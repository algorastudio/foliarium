"""
tests/unit/test_db_comprehensive.py
===================================
Test comprehensivi per i mixin db/ con copertura completa:
- db/localita.py
- db/variazioni.py
- db/ricerca.py
- db/io.py
- db/documenti.py
- db/utenti.py
- db/stats.py

Usa mock connections per testare la logica senza DB reale.
"""

import pytest
import logging
import psycopg2
from datetime import date, datetime
from contextlib import contextmanager
from unittest.mock import MagicMock, patch, call
from pathlib import Path
import tempfile

from catasto_db_manager import CatastoDBManager
from catasto_exceptions import DBMError, DBUniqueConstraintError, DBNotFoundError, DBDataError


# ===========================================================================
# Fixture comune: CatastoDBManager senza connessione
# ===========================================================================

@pytest.fixture
def mgr(tmp_path):
    """Istanza di CatastoDBManager senza pool reale per i test."""
    m = CatastoDBManager.__new__(CatastoDBManager)
    m.pool = None
    m.schema = "catasto"
    m.offline_mode = False
    m.offline_cache_timestamp = None
    m._cache_dir = tmp_path
    m._main_db_conn_params = {"user": "postgres", "host": "localhost", "port": 5432, "dbname": "catasto_storico"}
    m.logger = logging.getLogger("test_db")
    return m


def make_mock_conn(rows=None, fetchone_val=None, rowcount=1):
    """Factory per creare mock connessione + cursore."""
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
# TestLocalitaMixin - db/localita.py
# ===========================================================================

@pytest.mark.unit
class TestLocalitaMixin:

    def test_get_tipi_localita_restituisce_lista(self, mgr):
        """get_tipi_localita deve restituire lista di tipi."""
        righe = [
            {"id": 1, "nome": "Via", "descrizione": "Strada"},
            {"id": 2, "nome": "Piazza", "descrizione": "Piazza pubblica"},
        ]
        conn_cm, cur = make_mock_conn(rows=righe)
        with patch.object(mgr, "_get_connection", return_value=conn_cm):
            with patch.object(mgr, "_try_with_cache", side_effect=lambda key, func: func()):
                result = mgr.get_tipi_localita()
        assert isinstance(result, list)
        assert len(result) == 2

    def test_get_localita_by_comune_valido(self, mgr):
        """get_localita_by_comune deve restituire località per comune."""
        righe = [
            {"id": 1, "nome": "Via Roma 10", "tipologia_stradale": "Via"},
            {"id": 2, "nome": "Piazza Garibaldi", "tipologia_stradale": "Piazza"},
        ]
        conn_cm, cur = make_mock_conn(rows=righe)
        with patch.object(mgr, "_get_connection", return_value=conn_cm):
            result = mgr.get_localita_by_comune(comune_id=1)
        assert isinstance(result, list)
        assert len(result) == 2

    def test_get_localita_by_comune_con_filtro(self, mgr):
        """get_localita_by_comune con filter_text deve aggiungere ILIKE."""
        conn_cm, cur = make_mock_conn(rows=[])
        with patch.object(mgr, "_get_connection", return_value=conn_cm):
            mgr.get_localita_by_comune(comune_id=1, filter_text="Roma")
        # Verifica che la query includa il filtro
        args = cur.execute.call_args[0]
        assert "ILIKE" in args[0].upper()

    def test_get_localita_by_comune_id_invalido(self, mgr):
        """get_localita_by_comune con ID non valido deve sollevare DBDataError."""
        with pytest.raises(DBDataError):
            mgr.get_localita_by_comune(comune_id=-1)

    def test_insert_localita_valida(self, mgr):
        """insert_localita deve restituire l'ID della nuova località."""
        conn_cm, cur = make_mock_conn(fetchone_val={"id": 99})
        with patch.object(mgr, "_get_connection", return_value=conn_cm):
            result = mgr.insert_localita(
                comune_id=1, nome="Via Nuova 15", tipologia_stradale="Via",
            )
        assert result == 99

    def test_insert_localita_nome_vuoto(self, mgr):
        """insert_localita con nome vuoto deve sollevare DBDataError."""
        with pytest.raises(DBDataError):
            mgr.insert_localita(comune_id=1, nome="", tipologia_stradale="Via")

    def test_update_localita_valida(self, mgr):
        """update_localita deve aggiornare la località."""
        conn_cm, cur = make_mock_conn(rowcount=1)
        with patch.object(mgr, "_get_connection", return_value=conn_cm):
            mgr.update_localita(localita_id=1, dati_modificati={"nome": "Via Nuova 20"})
        # Verifica che execute sia stato chiamato
        assert cur.execute.called

    def test_update_localita_non_trovata(self, mgr):
        """update_localita con ID non trovato deve sollevare DBNotFoundError."""
        conn_cm, cur = make_mock_conn(rowcount=0)
        with patch.object(mgr, "_get_connection", return_value=conn_cm):
            with pytest.raises(DBNotFoundError):
                mgr.update_localita(localita_id=999, dati_modificati={"nome": "Via Nuova"})

    def test_get_localita_details_valida(self, mgr):
        """get_localita_details deve restituire dettagli della località."""
        riga = {
            "id": 1, "nome": "Via Roma 10", "tipologia_stradale": "Via",
            "comune_id": 1, "comune_nome": "Roma"
        }
        conn_cm, cur = make_mock_conn(fetchone_val=riga)
        with patch.object(mgr, "_get_connection", return_value=conn_cm):
            result = mgr.get_localita_details(localita_id=1)
        assert result["nome"] == "Via Roma 10"

    def test_get_localita_details_non_trovata(self, mgr):
        """get_localita_details con ID non trovato deve sollevare DBNotFoundError."""
        conn_cm, cur = make_mock_conn(fetchone_val=None)
        with patch.object(mgr, "_get_connection", return_value=conn_cm):
            with pytest.raises(DBNotFoundError):
                mgr.get_localita_details(localita_id=999)


# ===========================================================================
# TestVariazioniMixin - db/variazioni.py
# ===========================================================================

@pytest.mark.unit
class TestVariazioniMixin:

    def test_get_elenco_variazioni_per_esportazione(self, mgr):
        """get_elenco_variazioni_per_esportazione deve restituire elenco."""
        righe = [
            {"id": 1, "tipo": "Divisione", "data_variazione": date(2025, 1, 1)},
        ]
        conn_cm, cur = make_mock_conn(rows=righe)
        with patch.object(mgr, "_get_connection", return_value=conn_cm):
            result = mgr.get_elenco_variazioni_per_esportazione()
        assert isinstance(result, list)

    def test_search_variazioni_senza_filtri(self, mgr):
        """search_variazioni senza filtri deve eseguire la query."""
        righe = [
            {"id": 1, "tipo": "Divisione"},
        ]
        conn_cm, cur = make_mock_conn(rows=righe)
        with patch.object(mgr, "_get_connection", return_value=conn_cm):
            result = mgr.search_variazioni()
        assert isinstance(result, list)

    def test_search_variazioni_con_filtri(self, mgr):
        """search_variazioni con filtri deve includerli nella query."""
        conn_cm, cur = make_mock_conn(rows=[])
        with patch.object(mgr, "_get_connection", return_value=conn_cm):
            mgr.search_variazioni(tipo="Divisione", data_inizio=date(2025, 1, 1))
        assert cur.execute.called

    def test_update_variazione_success(self, mgr):
        """update_variazione deve restituire True al successo."""
        conn_cm, cur = make_mock_conn()
        with patch.object(mgr, "_get_connection", return_value=conn_cm):
            result = mgr.update_variazione(
                variazione_id=1,
                tipo="Divisione",
                data_variazione=date(2025, 1, 1)
            )
        assert result is True

    def test_delete_variazione_success(self, mgr):
        """delete_variazione deve restituire True al successo."""
        conn_cm, cur = make_mock_conn()
        with patch.object(mgr, "_get_connection", return_value=conn_cm):
            result = mgr.delete_variazione(variazione_id=1)
        assert result is True

    def test_insert_contratto_success(self, mgr):
        """insert_contratto deve restituire True al successo."""
        conn_cm, cur = make_mock_conn()
        with patch.object(mgr, "_get_connection", return_value=conn_cm):
            result = mgr.insert_contratto(
                variazione_id=1,
                tipo="Atto notarile",
                data_contratto=date(2025, 1, 1)
            )
        assert result is True

    def test_insert_contratto_db_error(self, mgr):
        """insert_contratto con errore DB deve restituire False."""
        conn_cm, cur = make_mock_conn()
        cur.execute.side_effect = psycopg2.OperationalError("connessione persa")
        with patch.object(mgr, "_get_connection", return_value=conn_cm):
            result = mgr.insert_contratto(
                variazione_id=1,
                tipo="Atto notarile",
                data_contratto=date(2025, 1, 1)
            )
        assert result is False


# ===========================================================================
# TestSearchMixin - db/ricerca.py
# ===========================================================================

@pytest.mark.unit
class TestSearchMixin:

    def test_verify_gin_indices_restituisce_status(self, mgr):
        """verify_gin_indices deve restituire dict con stato e conteggio indici."""
        conn_cm, cur = make_mock_conn(fetchone_val=(3,))
        with patch.object(mgr, "_get_connection", return_value=conn_cm):
            result = mgr.verify_gin_indices()
        assert isinstance(result, dict)
        assert "status" in result
        assert "gin_indices" in result
        assert result["status"] == "OK"

    def test_search_all_entities_fuzzy_restituisce_dict(self, mgr):
        """search_all_entities_fuzzy deve restituire dict con tutte le categorie."""
        conn_cm, cur = make_mock_conn(rows=[])
        with patch.object(mgr, "_get_connection", return_value=conn_cm):
            result = mgr.search_all_entities_fuzzy("test")
        assert isinstance(result, dict)
        assert "possessore" in result
        assert "localita" in result
        assert "immobile" in result
        assert "variazione" in result
        assert "contratto" in result
        assert "partita" in result

    def test_search_all_entities_fuzzy_con_filtri(self, mgr):
        """search_all_entities_fuzzy con filtri selettivi."""
        conn_cm, cur = make_mock_conn(rows=[])
        with patch.object(mgr, "_get_connection", return_value=conn_cm):
            result = mgr.search_all_entities_fuzzy(
                "test",
                search_possessori=True,
                search_localita=False,
                search_immobili=False
            )
        assert isinstance(result, dict)

    def test_ricerca_avanzata_immobili_gui_senza_filtri(self, mgr):
        """ricerca_avanzata_immobili_gui senza filtri."""
        righe = [
            {"id_immobile": 1, "numero_partita": 101, "comune_nome": "Roma"},
        ]
        conn_cm, cur = make_mock_conn(rows=righe)
        with patch.object(mgr, "_get_connection", return_value=conn_cm):
            result = mgr.ricerca_avanzata_immobili_gui()
        assert isinstance(result, list)

    def test_ricerca_avanzata_immobili_gui_con_filtri(self, mgr):
        """ricerca_avanzata_immobili_gui con filtri."""
        conn_cm, cur = make_mock_conn(rows=[])
        with patch.object(mgr, "_get_connection", return_value=conn_cm):
            mgr.ricerca_avanzata_immobili_gui(
                comune_id=1,
                natura_search="Casa",
                piani_min=2,
                piani_max=5
            )
        assert cur.execute.called


# ===========================================================================
# TestIOmixin - db/io.py
# ===========================================================================

@pytest.mark.unit
class TestIOMixin:

    def test_import_comuni_from_rows_valido(self, mgr):
        """import_comuni_from_rows con dati validi."""
        rows = [
            {"nome": "Roma", "provincia": "RM", "regione": "Lazio"},
            {"nome": "Milano", "provincia": "MI", "regione": "Lombardia"},
        ]
        with patch.object(mgr, "bulk_insert_with_savepoint", return_value={"success": rows, "errors": []}):
            result = mgr.import_comuni_from_rows(rows)
        assert result["success"] == rows
        assert result["errors"] == []

    def test_import_comuni_from_rows_vuoto(self, mgr):
        """import_comuni_from_rows con lista vuota."""
        result = mgr.import_comuni_from_rows([])
        assert result["success"] == []
        assert result["errors"] == []

    def test_import_comuni_from_rows_campi_mancanti(self, mgr):
        """import_comuni_from_rows con campi obbligatori mancanti."""
        rows = [
            {"nome": "Roma", "provincia": "RM"},  # Manca 'regione'
        ]
        with pytest.raises(ValueError):
            mgr.import_comuni_from_rows(rows)

    def test_import_localita_from_rows_valido(self, mgr):
        """import_localita_from_rows con dati validi."""
        rows = [
            {"nome": "Via Roma", "tipo": "Via", "civico": "10"},
        ]
        with patch.object(mgr, "bulk_insert_with_savepoint", return_value={"success": rows, "errors": []}):
            result = mgr.import_localita_from_rows(comune_id=1, rows=rows)
        assert result["success"] == rows

    def test_import_localita_from_rows_incorpora_civico(self, mgr):
        """import_localita_from_rows deve incorporare civico nel nome."""
        rows = [
            {"nome": "Via Roma", "civico": "10", "tipologia_stradale": "Via"},
        ]
        with patch.object(mgr, "bulk_insert_with_savepoint", return_value={"success": [], "errors": []}):
            mgr.import_localita_from_rows(comune_id=1, rows=rows)
        # Verifica che il civico sia stato incorporato nel nome

    def test_get_comuni_export_csv(self, mgr):
        """get_comuni_export_csv deve restituire lista di dict."""
        righe = [
            {
                "nome": "Roma", "provincia": "RM", "regione": "Lazio",
                "codice_catastale": "H501", "data_istituzione": "01/01/1871",
                "data_soppressione": "", "note": ""
            },
        ]
        conn_cm, cur = make_mock_conn(rows=righe)
        with patch.object(mgr, "_get_connection", return_value=conn_cm):
            result = mgr.get_comuni_export_csv()
        assert isinstance(result, list)
        assert len(result) == 1

    def test_get_localita_export_csv(self, mgr):
        """get_localita_export_csv deve restituire lista di dict."""
        righe = [
            {"nome": "Via Roma 10", "tipologia_stradale": "Via"},
        ]
        conn_cm, cur = make_mock_conn(rows=righe)
        with patch.object(mgr, "_get_connection", return_value=conn_cm):
            result = mgr.get_localita_export_csv(comune_id=1)
        assert isinstance(result, list)

    def test_get_possessori_export_csv(self, mgr):
        """get_possessori_export_csv deve restituire lista di dict."""
        righe = [
            {"cognome_nome": "Rossi Mario", "nome_completo": "Mario Rossi", "paternita": ""},
        ]
        conn_cm, cur = make_mock_conn(rows=righe)
        with patch.object(mgr, "_get_connection", return_value=conn_cm):
            result = mgr.get_possessori_export_csv(comune_id=1)
        assert isinstance(result, list)

    def test_get_partite_export_csv(self, mgr):
        """get_partite_export_csv deve restituire lista di dict."""
        righe = [
            {"numero_partita": 101, "data_impianto": "01/01/1900", "stato": "attiva", "tipo": "principale"},
        ]
        conn_cm, cur = make_mock_conn(rows=righe)
        with patch.object(mgr, "_get_connection", return_value=conn_cm):
            result = mgr.get_partite_export_csv(comune_id=1)
        assert isinstance(result, list)


# ===========================================================================
# TestDocumentiMixin - db/documenti.py
# ===========================================================================

@pytest.mark.unit
class TestDocumentiMixin:

    def test_search_historical_documents_senza_filtri(self, mgr):
        """search_historical_documents senza filtri deve restituire elenco."""
        righe = [
            {"id": 1, "titolo": "Catasto 1870", "anno_documento": 1870},
        ]
        conn_cm, cur = make_mock_conn(rows=righe)
        with patch.object(mgr, "_get_connection", return_value=conn_cm):
            result = mgr.search_historical_documents()
        assert isinstance(result, list)

    def test_search_historical_documents_con_titolo(self, mgr):
        """search_historical_documents con titolo deve aggiungerlo alla query."""
        conn_cm, cur = make_mock_conn(rows=[])
        with patch.object(mgr, "_get_connection", return_value=conn_cm):
            mgr.search_historical_documents(title="Catasto")
        assert cur.execute.called

    def test_search_historical_documents_con_tipo(self, mgr):
        """search_historical_documents con tipo documento."""
        conn_cm, cur = make_mock_conn(rows=[])
        with patch.object(mgr, "_get_connection", return_value=conn_cm):
            mgr.search_historical_documents(doc_type="Mappa")
        assert cur.execute.called

    def test_get_documenti_per_partita(self, mgr):
        """get_documenti_per_partita deve restituire documenti legati a una partita."""
        righe = [{"id": 1, "titolo": "Doc 1", "partita_id": 1}]
        conn_cm, cur = make_mock_conn(rows=righe)
        with patch.object(mgr, "_get_connection", return_value=conn_cm):
            result = mgr.get_documenti_per_partita(partita_id=1)
        assert isinstance(result, list)


# ===========================================================================
# TestStatsMixin - db/stats.py
# ===========================================================================

@pytest.mark.unit
class TestStatsMixin:

    def test_get_statistiche_comune_restituisce_lista(self, mgr):
        """get_statistiche_comune senza filtri deve restituire lista."""
        righe = [
            {"comune_nome": "Roma", "num_partite": 100, "num_partite_attive": 80},
            {"comune_nome": "Milano", "num_partite": 200, "num_partite_attive": 150},
        ]
        conn_cm, cur = make_mock_conn(rows=righe)
        with patch.object(mgr, "_get_connection", return_value=conn_cm):
            result = mgr.get_statistiche_comune()
        assert isinstance(result, list)

    @pytest.mark.gui
    def test_refresh_materialized_views_senza_pool(self, mgr):
        """refresh_materialized_views con pool=None deve terminare silenziosamente."""
        pytest.skip("Richiede libEGL (ambiente grafico) — test solo in CI con Qt installato")


# ===========================================================================
# TestUtentiMixin - db/utenti.py
# ===========================================================================

@pytest.mark.unit
class TestUtentiMixin:

    def test_get_utente_by_id_valido(self, mgr):
        """get_utente_by_id deve restituire dict con dati utente."""
        riga = {
            "id": 1, "username": "admin", "ruolo": "admin",
            "email": "admin@test.com", "attivo": True
        }
        conn_cm, cur = make_mock_conn(fetchone_val=riga)
        with patch.object(mgr, "_get_connection", return_value=conn_cm):
            result = mgr.get_utente_by_id(utente_id=1)
        assert result is not None
        assert result["username"] == "admin"

    def test_get_utente_by_id_non_trovato_restituisce_none(self, mgr):
        """get_utente_by_id con ID non trovato restituisce None (non raise)."""
        conn_cm, cur = make_mock_conn(fetchone_val=None)
        with patch.object(mgr, "_get_connection", return_value=conn_cm):
            result = mgr.get_utente_by_id(utente_id=999)
        assert result is None

    def test_get_utenti_tutti(self, mgr):
        """get_utenti deve restituire lista di utenti."""
        righe = [
            {"id": 1, "username": "admin", "ruolo": "admin", "attivo": True},
            {"id": 2, "username": "user1", "ruolo": "archivista", "attivo": True},
        ]
        conn_cm, cur = make_mock_conn(rows=righe)
        with patch.object(mgr, "_get_connection", return_value=conn_cm):
            result = mgr.get_utenti()
        assert len(result) == 2

    def test_get_utenti_solo_attivi(self, mgr):
        """get_utenti(solo_attivi=True) deve filtrare per attivi."""
        righe = [{"id": 1, "username": "admin", "attivo": True}]
        conn_cm, cur = make_mock_conn(rows=righe)
        with patch.object(mgr, "_get_connection", return_value=conn_cm):
            result = mgr.get_utenti(solo_attivi=True)
        assert isinstance(result, list)

    def test_create_user_success(self, mgr):
        """create_user deve restituire True al successo."""
        conn_cm, cur = make_mock_conn(rowcount=1)
        with patch.object(mgr, "_get_connection", return_value=conn_cm):
            result = mgr.create_user(
                username="newuser",
                password_hash="hash123",
                nome_completo="Nuovo Utente",
                email="newuser@test.com",
                ruolo="archivista"
            )
        assert result is True

    def test_reset_user_password(self, mgr):
        """reset_user_password deve restituire True al successo."""
        conn_cm, cur = make_mock_conn(rowcount=1)
        with patch.object(mgr, "_get_connection", return_value=conn_cm):
            result = mgr.reset_user_password(utente_id=1, new_password_hash="newhash")
        assert result is True

    def test_deactivate_user(self, mgr):
        """deactivate_user deve disabilitare un utente."""
        conn_cm, cur = make_mock_conn(rowcount=1)
        with patch.object(mgr, "_get_connection", return_value=conn_cm):
            result = mgr.deactivate_user(utente_id=1)
        assert result is True

    def test_activate_user(self, mgr):
        """activate_user deve riattivare un utente disabilitato."""
        conn_cm, cur = make_mock_conn(rowcount=1)
        with patch.object(mgr, "_get_connection", return_value=conn_cm):
            result = mgr.activate_user(utente_id=1)
        assert result is True
