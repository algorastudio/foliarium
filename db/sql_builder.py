"""
db/sql_builder.py — Safe SQL query builder (no ORM).
Previene SQL injection usando psycopg2.sql module.

Uso:
    query = SafeQuery.insert("partita", ["numero", "stato"])
    cur.execute(query, (123, "Attiva"))
"""

from typing import List, Dict, Any, Tuple, Optional
from psycopg2 import sql


class SafeQuery:
    """Builder per query SQL sicure (no SQL injection)."""

    @staticmethod
    def insert(
        table: str,
        columns: List[str],
        schema: str = "public"
    ) -> sql.SQL:
        """
        Build INSERT ... VALUES statement safely.

        Args:
            table: Table name
            columns: List of column names
            schema: Schema name (default 'public')

        Returns:
            psycopg2.sql.SQL object ready for cur.execute(query, values)

        Example:
            query = SafeQuery.insert("partita", ["numero_partita", "stato"])
            cur.execute(query, (123, "Attiva"))
        """
        cols = sql.SQL(", ").join([sql.Identifier(c) for c in columns])
        placeholders = sql.SQL(", ").join([sql.Placeholder()] * len(columns))
        return sql.SQL("INSERT INTO {}.{} ({}) VALUES ({})").format(
            sql.Identifier(schema),
            sql.Identifier(table),
            cols,
            placeholders
        )

    @staticmethod
    def update(
        table: str,
        columns: List[str],
        schema: str = "public"
    ) -> sql.SQL:
        """
        Build UPDATE statement safely.

        Returns SQL without WHERE clause; append manually:
            query = SafeQuery.update("partita", ["stato", "data_modifica"])
            full_query = sql.SQL("{} WHERE id = %s").format(query)
            cur.execute(full_query, ("Inattiva", now(), partita_id))
        """
        set_clause = sql.SQL(", ").join([
            sql.SQL("{} = {}").format(sql.Identifier(c), sql.Placeholder())
            for c in columns
        ])
        return sql.SQL("UPDATE {}.{} SET {}").format(
            sql.Identifier(schema),
            sql.Identifier(table),
            set_clause
        )

    @staticmethod
    def select(
        columns: List[str],
        table: str,
        schema: str = "public"
    ) -> sql.SQL:
        """
        Build SELECT statement safely (no WHERE).

        Example:
            query = SafeQuery.select(["id", "numero_partita"], "partita")
            full_query = sql.SQL("{} WHERE stato = %s").format(query)
            cur.execute(full_query, ("Attiva",))
        """
        cols = sql.SQL(", ").join([sql.Identifier(c) for c in columns])
        return sql.SQL("SELECT {} FROM {}.{}").format(
            cols,
            sql.Identifier(schema),
            sql.Identifier(table)
        )

    @staticmethod
    def where_clause(conditions: Dict[str, Any]) -> Tuple[sql.SQL, List[Any]]:
        """
        Build safe WHERE clause from dict.

        Args:
            conditions: {"column": value, ...} dict

        Returns:
            (sql_fragment, values_list)

        Example:
            where_sql, where_vals = SafeQuery.where_clause({
                "numero_partita": 123,
                "stato": "Attiva"
            })
            full_query = sql.SQL("SELECT * FROM partita WHERE {}").format(where_sql)
            cur.execute(full_query, tuple(where_vals))
        """
        if not conditions:
            return sql.SQL(""), []

        clauses = []
        values = []
        for col, val in conditions.items():
            clauses.append(sql.SQL("{} = {}").format(
                sql.Identifier(col),
                sql.Placeholder()
            ))
            values.append(val)

        where_clause = sql.SQL(" AND ").join(clauses)
        return where_clause, values

    @staticmethod
    def delete(
        table: str,
        schema: str = "public"
    ) -> sql.SQL:
        """
        Build DELETE statement safely (no WHERE).

        Example:
            query = SafeQuery.delete("partita")
            full_query = sql.SQL("{} WHERE id = %s").format(query)
            cur.execute(full_query, (partita_id,))
        """
        return sql.SQL("DELETE FROM {}.{}").format(
            sql.Identifier(schema),
            sql.Identifier(table)
        )
