"""Utility functions for safe SQL query construction.

Provides helpers to build SQL queries using psycopg's sql module
and enforce LIMIT clauses with clamped bounds.
"""

from psycopg import sql

DEFAULT_LIMIT = 100
MIN_LIMIT = 1
MAX_LIMIT = 100


def clamp_limit(limit=DEFAULT_LIMIT):
    """Clamp a LIMIT value to the allowed range [1, 100].

    Args:
        limit: Desired LIMIT value.

    Returns:
        int: Clamped value between MIN_LIMIT and MAX_LIMIT.
    """
    return max(MIN_LIMIT, min(MAX_LIMIT, int(limit)))


def build_query(query_str, limit=DEFAULT_LIMIT):
    """Wrap a SQL string in sql.SQL and append a clamped LIMIT clause.

    Args:
        query_str: The SQL query text (without LIMIT).
        limit: Desired LIMIT value (will be clamped to 1-100).

    Returns:
        psycopg.sql.Composed: The composed SQL with LIMIT appended.
    """
    clamped = clamp_limit(limit)
    return sql.SQL("{query} LIMIT {limit}").format(
        query=sql.SQL(query_str),
        limit=sql.Literal(clamped),
    )
