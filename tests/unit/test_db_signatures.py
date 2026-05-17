"""
tests/unit/test_db_signatures.py
================================
Unit test che bloccano le SIGNATURE dei metodi DB piu' inclini a drift.

Motivazione: lo Sprint 3.9 (six-hats analisi) ha rivelato che molti
test e widget chiamano metodi rinominati nel rebrand v1.5.0+. Lo script
bin/check_api_drift.py copre i nomi dei metodi; questi test coprono
gli argomenti e i tipi di ritorno tramite mock.

Per ogni metodo critico:
  - Verifica che esista nell'inventario
  - Verifica la signature (parametri positional/keyword + tipo ritorno)
  - Esercita il flusso happy-path con mock cursor

Quando una signature cambia (es. update_possessore da kwargs a dict),
questi test falliscono SUBITO, non scoprendoli mesi dopo nei test
integration skippati.
"""

from __future__ import annotations

import inspect
import logging
from unittest.mock import MagicMock, patch

import pytest


pytestmark = pytest.mark.unit


@pytest.fixture
def mgr(tmp_path):
    """CatastoDBManager via __new__ senza pool, solo logger."""
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
    m.logger = logging.getLogger("test_signatures")
    return m


def _make_conn(*, fetchone_val=None, rowcount=1, rows=None):
    """Costruisce mock connessione + cursore (context-manager-friendly)."""
    cur = MagicMock()
    cur.fetchone.return_value = fetchone_val
    cur.fetchall.return_value = rows or []
    cur.rowcount = rowcount

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
# update_possessore — signature: (possessore_id: int, dati_modificati: Dict)
# ===========================================================================

class TestUpdatePossessoreSignature:
    """Blocca il bug che ha rotto i test integration nello Sprint 3.9:
    update_possessore NON accetta piu' kwargs come 'note=', 'paternita=';
    accetta esclusivamente un dict 'dati_modificati'."""

    def test_method_exists(self, mgr):
        assert callable(getattr(mgr, "update_possessore", None))

    def test_signature_is_positional_dict(self, mgr):
        """L'attesa: update_possessore(possessore_id, dati_modificati: Dict)."""
        sig = inspect.signature(mgr.update_possessore)
        params = list(sig.parameters.values())
        # Self e' rimosso da .signature() su bound methods, ma su unbound
        # potrebbe esserci. Filtriamo per essere robusti.
        params = [p for p in params if p.name != "self"]
        # 2 parametri attesi
        assert len(params) >= 2, (
            f"update_possessore deve avere almeno 2 parametri "
            f"(possessore_id, dati_modificati); trovati: {[p.name for p in params]}"
        )
        names = [p.name for p in params]
        assert "possessore_id" in names
        assert "dati_modificati" in names

    def test_happy_path_with_dict(self, mgr):
        """Una chiave whitelist nel dict (es. paternita) deve far partire la query."""
        conn_cm, cur = _make_conn(rowcount=1)
        with patch.object(mgr, "_get_connection", return_value=conn_cm):
            mgr.update_possessore(
                possessore_id=1,
                dati_modificati={"paternita": "fu Mario"},
            )
        assert cur.execute.called

    def test_rejects_unknown_kwargs(self, mgr):
        """Chiamarlo con kwargs vecchi (es. note=...) deve fallire pulito.
        Questo era proprio il bug originale di test_database_manager.py."""
        with pytest.raises(TypeError):
            mgr.update_possessore(possessore_id=1, note="ignorato")  # type: ignore


# ===========================================================================
# inserisci_immobile — signature: (partita_id, natura, localita_id, ...)
# ===========================================================================

class TestInserisciImmobileSignature:

    def test_method_exists(self, mgr):
        assert callable(getattr(mgr, "inserisci_immobile", None))

    def test_required_params(self, mgr):
        """Il rebrand v1.6.1 ha cristallizzato 3 required: partita_id,
        natura, localita_id. Tipologia/civico/classificazione sono opzionali."""
        sig = inspect.signature(mgr.inserisci_immobile)
        params = sig.parameters
        # I 3 required (no default = required)
        required = [n for n, p in params.items()
                    if n != "self" and p.default is inspect.Parameter.empty]
        assert set(required) == {"partita_id", "natura", "localita_id"}, (
            f"required mismatch: {required}"
        )

    def test_no_alias_create_immobile(self, mgr):
        """Il vecchio nome 'create_immobile' NON deve esistere (rinominato
        nel rebrand v1.5.0; alias rimuoverebbe il segnale di drift)."""
        assert not hasattr(mgr, "create_immobile")


# ===========================================================================
# update_partita — signature: (partita_id, dati_modificati: Dict)
# ===========================================================================

class TestUpdatePartitaSignature:

    def test_method_exists(self, mgr):
        assert callable(getattr(mgr, "update_partita", None))

    def test_signature_takes_dict(self, mgr):
        sig = inspect.signature(mgr.update_partita)
        params = [p for p in sig.parameters.values() if p.name != "self"]
        names = [p.name for p in params]
        assert "partita_id" in names
        assert "dati_modificati" in names


# ===========================================================================
# get_partita_details — l'unico nome attuale (NON get_partita_by_id)
# ===========================================================================

class TestGetPartitaDetailsSignature:

    def test_method_exists(self, mgr):
        assert callable(getattr(mgr, "get_partita_details", None))

    def test_old_alias_not_present(self, mgr):
        """get_partita_by_id era il vecchio nome; rimosso nel rebrand."""
        assert not hasattr(mgr, "get_partita_by_id")


# ===========================================================================
# create_partita — signature: 5 required (comune_id, numero, tipo, stato,
# data_impianto) + numero_provenienza opzionale
# ===========================================================================

class TestCreatePartitaSignature:

    def test_method_exists(self, mgr):
        assert callable(getattr(mgr, "create_partita", None))

    def test_required_params(self, mgr):
        """create_partita richiede 5 args; test_data_validation_errors del
        vecchio test_database_manager.py la chiamava con 3 → era rotto."""
        sig = inspect.signature(mgr.create_partita)
        required = [n for n, p in sig.parameters.items()
                    if n != "self" and p.default is inspect.Parameter.empty]
        assert "comune_id" in required
        assert "numero_partita" in required
        assert "tipo" in required
        assert "stato" in required
        assert "data_impianto" in required


# ===========================================================================
# get_localita_by_comune — NON _per_comune (drift trovato in
# foliarium/ui/dialogs/partita.py:1885 nello Sprint 3.9)
# ===========================================================================

class TestGetLocalitaSignature:

    def test_canonical_name_is_by(self, mgr):
        """L'unico nome attuale e' get_localita_by_comune."""
        assert callable(getattr(mgr, "get_localita_by_comune", None))

    def test_no_per_comune_alias(self, mgr):
        """get_localita_per_comune NON deve esistere (era il bug fixato)."""
        assert not hasattr(mgr, "get_localita_per_comune")


# ===========================================================================
# aggiungi_comune — signature: (nome_comune, provincia, regione, ...)
# ===========================================================================

class TestAggiungiComuneSignature:

    def test_method_exists(self, mgr):
        assert callable(getattr(mgr, "aggiungi_comune", None))

    def test_first_three_required(self, mgr):
        """nome_comune, provincia, regione sono i 3 required."""
        sig = inspect.signature(mgr.aggiungi_comune)
        required = [n for n, p in sig.parameters.items()
                    if n != "self" and p.default is inspect.Parameter.empty]
        assert required[:3] == ["nome_comune", "provincia", "regione"]


# ===========================================================================
# get_all_comuni_details — nome attuale (NON get_all_comuni)
# ===========================================================================

class TestGetAllComuniSignature:

    def test_canonical_name(self, mgr):
        assert callable(getattr(mgr, "get_all_comuni_details", None))

    def test_old_alias_removed(self, mgr):
        """get_all_comuni rimosso nel rebrand v1.5.0."""
        assert not hasattr(mgr, "get_all_comuni")


# ===========================================================================
# update_comune — signature: (comune_id, dati_modificati: Dict)
# ===========================================================================

class TestUpdateComuneSignature:

    def test_method_exists(self, mgr):
        assert callable(getattr(mgr, "update_comune", None))

    def test_signature_takes_dict(self, mgr):
        sig = inspect.signature(mgr.update_comune)
        params = [p.name for p in sig.parameters.values() if p.name != "self"]
        assert "comune_id" in params
        assert "dati_modificati" in params


# ===========================================================================
# ricerca_avanzata_immobili_gui — nome attuale (NON _possessori_gui)
# ===========================================================================

class TestRicercaAvanzataSignature:

    def test_immobili_gui_exists(self, mgr):
        assert callable(getattr(mgr, "ricerca_avanzata_immobili_gui", None))

    def test_possessori_gui_removed(self, mgr):
        """ricerca_avanzata_possessori_gui rimosso nel rebrand."""
        assert not hasattr(mgr, "ricerca_avanzata_possessori_gui")


# ===========================================================================
# Protocol compliance — CatastoDBManager deve soddisfare DBManagerProtocol
# ===========================================================================

class TestProtocolCompliance:
    """Verifica che il contract foliarium.protocols.DBManagerProtocol sia
    rispettato dal CatastoDBManager attuale. Se un metodo viene rimosso
    da db/* senza aggiornare il Protocol, questi test falliscono.
    """

    def test_catasto_db_manager_satisfies_protocol(self, mgr):
        """isinstance check con @runtime_checkable Protocol."""
        from foliarium.protocols import DBManagerProtocol
        assert isinstance(mgr, DBManagerProtocol), (
            "CatastoDBManager non soddisfa piu' DBManagerProtocol: "
            "qualche metodo richiesto manca. Confronta foliarium/protocols.py "
            "con i mixin db/ per individuare il drift."
        )

    def test_comune_ops_protocol(self, mgr):
        from foliarium.protocols import ComuneOpsProtocol
        assert isinstance(mgr, ComuneOpsProtocol)

    def test_possessore_ops_protocol(self, mgr):
        from foliarium.protocols import PossessoreOpsProtocol
        assert isinstance(mgr, PossessoreOpsProtocol)

    def test_partita_ops_protocol(self, mgr):
        from foliarium.protocols import PartitaOpsProtocol
        assert isinstance(mgr, PartitaOpsProtocol)

    def test_immobile_ops_protocol(self, mgr):
        from foliarium.protocols import ImmobileOpsProtocol
        assert isinstance(mgr, ImmobileOpsProtocol)

    def test_localita_ops_protocol(self, mgr):
        from foliarium.protocols import LocalitaOpsProtocol
        assert isinstance(mgr, LocalitaOpsProtocol)
