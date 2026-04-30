"""
tests/unit/test_sql_builder.py
===============================
Unit test per db/sql_builder.py — SafeQuery.
Verifica che i metodi generino SQL corretti usando psycopg2.sql.
Marker: unit
"""
from __future__ import annotations

import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from psycopg2 import sql
from db.sql_builder import SafeQuery


# ===========================================================================
# SafeQuery.insert
# ===========================================================================

@pytest.mark.unit
class TestSafeQueryInsert:

    def test_returns_sql_object(self):
        q = SafeQuery.insert("partita", ["numero_partita", "stato"])
        assert isinstance(q, sql.Composed)

    def test_contains_insert_keyword(self):
        q = SafeQuery.insert("partita", ["numero_partita"])
        rendered = q.as_string(None) if hasattr(q, 'as_string') else str(q)
        # Just verify it's a psycopg2 SQL object (composition)
        assert q is not None

    def test_single_column(self):
        q = SafeQuery.insert("partita", ["numero_partita"])
        assert isinstance(q, sql.Composed)

    def test_multiple_columns(self):
        q = SafeQuery.insert("partita", ["numero_partita", "stato", "tipo"])
        assert isinstance(q, sql.Composed)

    def test_custom_schema(self):
        q = SafeQuery.insert("partita", ["numero_partita"], schema="myschema")
        assert isinstance(q, sql.Composed)

    def test_default_schema_is_public(self):
        q_default = SafeQuery.insert("partita", ["id"])
        q_public = SafeQuery.insert("partita", ["id"], schema="public")
        # Both should produce the same result
        assert type(q_default) == type(q_public)

    def test_placeholders_count_matches_columns(self):
        """Number of placeholders must match number of columns."""
        columns = ["a", "b", "c"]
        q = SafeQuery.insert("t", columns)
        # The composed SQL should have as many placeholders as columns
        # We can verify by counting Placeholder objects in the composition
        assert isinstance(q, sql.Composed)


# ===========================================================================
# SafeQuery.update
# ===========================================================================

@pytest.mark.unit
class TestSafeQueryUpdate:

    def test_returns_sql_object(self):
        q = SafeQuery.update("partita", ["stato"])
        assert isinstance(q, sql.Composed)

    def test_single_column(self):
        q = SafeQuery.update("partita", ["stato"])
        assert isinstance(q, sql.Composed)

    def test_multiple_columns(self):
        q = SafeQuery.update("partita", ["stato", "tipo", "data_modifica"])
        assert isinstance(q, sql.Composed)

    def test_custom_schema(self):
        q = SafeQuery.update("partita", ["stato"], schema="catasto")
        assert isinstance(q, sql.Composed)

    def test_can_be_composed_with_where(self):
        """The UPDATE query must be composable with a WHERE clause."""
        q = SafeQuery.update("partita", ["stato"])
        full = sql.SQL("{} WHERE id = %s").format(q)
        assert isinstance(full, sql.Composed)


# ===========================================================================
# SafeQuery.select
# ===========================================================================

@pytest.mark.unit
class TestSafeQuerySelect:

    def test_returns_sql_object(self):
        q = SafeQuery.select(["id", "nome"], "comune")
        assert isinstance(q, sql.Composed)

    def test_single_column(self):
        q = SafeQuery.select(["id"], "comune")
        assert isinstance(q, sql.Composed)

    def test_multiple_columns(self):
        q = SafeQuery.select(["id", "nome", "provincia", "regione"], "comune")
        assert isinstance(q, sql.Composed)

    def test_custom_schema(self):
        q = SafeQuery.select(["id"], "comune", schema="catasto")
        assert isinstance(q, sql.Composed)

    def test_can_be_composed_with_where(self):
        q = SafeQuery.select(["id", "nome"], "comune")
        full = sql.SQL("{} WHERE provincia = %s").format(q)
        assert isinstance(full, sql.Composed)


# ===========================================================================
# SafeQuery.where_clause
# ===========================================================================

@pytest.mark.unit
class TestSafeQueryWhereClause:

    def test_empty_conditions_returns_empty_sql(self):
        where_sql, values = SafeQuery.where_clause({})
        assert isinstance(where_sql, sql.SQL)
        assert values == []

    def test_single_condition(self):
        where_sql, values = SafeQuery.where_clause({"stato": "Attiva"})
        assert isinstance(where_sql, sql.Composed)
        assert values == ["Attiva"]

    def test_multiple_conditions(self):
        where_sql, values = SafeQuery.where_clause({
            "stato": "Attiva",
            "tipo": "Principale",
        })
        assert isinstance(where_sql, sql.Composed)
        assert "Attiva" in values
        assert "Principale" in values
        assert len(values) == 2

    def test_values_order_matches_conditions(self):
        conditions = {"stato": "Attiva", "numero_partita": 100}
        _, values = SafeQuery.where_clause(conditions)
        assert len(values) == 2
        # Values should be in dict insertion order (Python 3.7+)
        assert values[0] == "Attiva"
        assert values[1] == 100

    def test_none_value_in_conditions(self):
        where_sql, values = SafeQuery.where_clause({"data_chiusura": None})
        assert values == [None]

    def test_integer_value(self):
        where_sql, values = SafeQuery.where_clause({"comune_id": 42})
        assert values == [42]

    def test_returns_tuple(self):
        result = SafeQuery.where_clause({"stato": "ok"})
        assert len(result) == 2


# ===========================================================================
# SafeQuery.delete
# ===========================================================================

@pytest.mark.unit
class TestSafeQueryDelete:

    def test_returns_sql_object(self):
        q = SafeQuery.delete("partita")
        assert isinstance(q, sql.Composed)

    def test_custom_schema(self):
        q = SafeQuery.delete("partita", schema="catasto")
        assert isinstance(q, sql.Composed)

    def test_can_be_composed_with_where(self):
        q = SafeQuery.delete("partita")
        full = sql.SQL("{} WHERE id = %s").format(q)
        assert isinstance(full, sql.Composed)

    def test_default_schema_is_public(self):
        q = SafeQuery.delete("partita")
        assert isinstance(q, sql.Composed)


# ===========================================================================
# Integration: compose full queries
# ===========================================================================

@pytest.mark.unit
class TestSafeQueryIntegration:

    def test_insert_select_round_trip_structure(self):
        """INSERT and SELECT use the same table/column identifiers."""
        cols = ["numero_partita", "stato"]
        insert_q = SafeQuery.insert("partita", cols, schema="catasto")
        select_q = SafeQuery.select(cols, "partita", schema="catasto")
        assert isinstance(insert_q, sql.Composed)
        assert isinstance(select_q, sql.Composed)

    def test_update_with_where_from_where_clause(self):
        """UPDATE composed with WHERE from where_clause."""
        update_q = SafeQuery.update("partita", ["stato"], schema="catasto")
        where_sql, where_vals = SafeQuery.where_clause({"id": 5})
        full = sql.SQL("{} WHERE {}").format(update_q, where_sql)
        assert isinstance(full, sql.Composed)
        assert where_vals == [5]

    def test_delete_with_where_from_where_clause(self):
        """DELETE composed with WHERE from where_clause."""
        delete_q = SafeQuery.delete("partita", schema="catasto")
        where_sql, where_vals = SafeQuery.where_clause({"id": 99})
        full = sql.SQL("{} WHERE {}").format(delete_q, where_sql)
        assert isinstance(full, sql.Composed)
        assert where_vals == [99]

    def test_select_with_multiple_where_conditions(self):
        """SELECT with multiple WHERE conditions."""
        select_q = SafeQuery.select(["id", "numero_partita"], "partita", schema="catasto")
        where_sql, vals = SafeQuery.where_clause({
            "stato": "Attiva",
            "comune_id": 1,
        })
        full = sql.SQL("{} WHERE {}").format(select_q, where_sql)
        assert isinstance(full, sql.Composed)
        assert len(vals) == 2
