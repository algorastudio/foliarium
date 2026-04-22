"""
Test per TIER 1 improvements: models, decorator, bulk insert helper, query tagging.
"""

import pytest
from datetime import datetime
from db.models import Partita, Possessore, Localita, Immobile
from db.sql_builder import SafeQuery
from db.base import db_handle_errors
from psycopg2 import sql


class TestDataclassModels:
    """Test che dataclass models funzionano correttamente."""

    def test_partita_creation(self):
        """Partita dataclass crea istanze type-safe."""
        p = Partita(
            id=1,
            numero_partita=123,
            suffisso_partita="A",
            stato="Attiva"
        )
        assert p.id == 1
        assert p.numero_partita == 123
        assert p.suffisso_partita == "A"
        assert p.stato == "Attiva"

    def test_partita_from_dict(self):
        """Partita unpacking da dict (simula DB row)."""
        row = {
            "id": 5,
            "numero_partita": 999,
            "suffisso_partita": None,
            "data_impianto": None,
            "stato": "Inattiva",
            "tipo_partita": None,
            "numero_provenienza": None,
            "comune_id": 10,
            "data_creazione": None,
            "data_modifica": None,
        }
        p = Partita(**row)
        assert p.id == 5
        assert p.numero_partita == 999
        assert p.stato == "Inattiva"
        assert p.comune_id == 10

    def test_possessore_creation(self):
        """Possessore dataclass."""
        poss = Possessore(
            id=1,
            cognome_nome="Rossi Mario",
            nome_completo="Mario Rossi"
        )
        assert poss.cognome_nome == "Rossi Mario"

    def test_localita_with_civico(self):
        """Localita con civico incorporato nel nome."""
        loc = Localita(
            id=1,
            nome="Via Roma 5",
            tipologia_stradale="Via",
            comune_id=2
        )
        assert "5" in loc.nome


class TestSafeQuery:
    """Test SQL builder (no ORM, just safe query construction)."""

    def test_insert_query(self):
        """INSERT query builder."""
        query = SafeQuery.insert("partita", ["numero_partita", "stato"])
        # Dovrebbe essere sql.SQL object
        assert isinstance(query, sql.SQL)

    def test_select_query(self):
        """SELECT query builder."""
        query = SafeQuery.select(["id", "numero_partita"], "partita")
        assert isinstance(query, sql.SQL)

    def test_where_clause(self):
        """WHERE clause builder."""
        where_sql, values = SafeQuery.where_clause({
            "numero_partita": 123,
            "stato": "Attiva"
        })
        assert isinstance(where_sql, sql.SQL)
        assert len(values) == 2
        assert 123 in values
        assert "Attiva" in values

    def test_empty_where_clause(self):
        """Empty WHERE clause returns empty tuple."""
        where_sql, values = SafeQuery.where_clause({})
        assert isinstance(where_sql, sql.SQL)
        assert len(values) == 0


class TestErrorHandlerDecorator:
    """Test @db_handle_errors decorator."""

    def test_decorator_exists(self):
        """Decorator è definito e importabile."""
        assert callable(db_handle_errors)

    def test_decorator_preserves_function_name(self):
        """Decorator preserva __name__ della funzione."""
        @db_handle_errors
        def test_func(self):
            return "hello"

        assert test_func.__name__ == "test_func"

    def test_decorator_preserves_return_value(self):
        """Decorator non altera il valore di ritorno."""
        class MockDB:
            logger = None

        @db_handle_errors
        def test_func(self):
            return 42

        result = test_func(MockDB())
        assert result == 42


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
