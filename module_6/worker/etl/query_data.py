"""Standalone query runner for applicant analytics.

Connects to PostgreSQL via DATABASE_URL and prints analysis metrics.
All queries use psycopg sql.SQL composition with enforced LIMIT clauses.
"""

from __future__ import annotations

import os

import psycopg
from psycopg import sql


def clamp_limit(limit=100):
    """Clamp a LIMIT value to [1, 100]."""
    return max(1, min(100, int(limit)))


def build_query(query_str, limit=100):
    """Wrap a SQL string with a clamped LIMIT clause."""
    clamped = clamp_limit(limit)
    return sql.SQL("{query} LIMIT {limit}").format(
        query=sql.SQL(query_str),
        limit=sql.Literal(clamped),
    )


def run_queries():
    """Execute analysis queries and print results."""
    conn = psycopg.connect(os.environ["DATABASE_URL"])
    cur = conn.cursor()

    cur.execute(build_query("SELECT COUNT(*) FROM applicants WHERE term = 'Fall 2026'", 1))
    print(f"1. Fall 2026 entries: {cur.fetchone()[0]}")

    cur.execute(build_query(
        "SELECT ROUND("
        "(COUNT(*) FILTER (WHERE us_or_international NOT IN ('American','Other')) * 100.0)"
        " / NULLIF(COUNT(*),0), 2) FROM applicants", 1))
    print(f"2. % International: {cur.fetchone()[0]}%")

    cur.execute(build_query(
        "SELECT AVG(gpa), AVG(gre), AVG(gre_v), AVG(gre_aw) FROM applicants", 1))
    print(f"3. Avg GPA/GRE/GRE_V/GRE_AW: {cur.fetchone()}")

    cur.execute(build_query(
        "SELECT AVG(gpa) FROM applicants "
        "WHERE us_or_international='American' AND term='Fall 2026'", 1))
    print(f"4. Avg GPA American (Fall 2026): {cur.fetchone()[0]}")

    cur.execute(build_query(
        "SELECT ROUND("
        "(COUNT(*) FILTER (WHERE status ILIKE '%Accepted%' AND term='Fall 2026') * 100.0)"
        " / NULLIF(COUNT(*) FILTER (WHERE term='Fall 2026'),0), 2) FROM applicants", 1))
    print(f"5. % Accepted (Fall 2026): {cur.fetchone()[0]}%")

    cur.execute(build_query(
        "SELECT AVG(gpa) FROM applicants "
        "WHERE term='Fall 2026' AND status ILIKE '%Accepted%'", 1))
    print(f"6. Avg GPA Accepted (Fall 2026): {cur.fetchone()[0]}")

    cur.execute(build_query(
        "SELECT COUNT(*) FROM applicants "
        "WHERE (university ILIKE '%Johns Hopkins%' OR university ILIKE '%JHU%') "
        "AND (program ILIKE '%Computer Science%' OR llm_generated_program ILIKE '%Computer Science%') "
        "AND degree ILIKE '%Masters%'", 1))
    print(f"7. JHU MS CS entries: {cur.fetchone()[0]}")

    cur.execute(build_query(
        "SELECT COUNT(*) FROM applicants "
        "WHERE term LIKE '%2025%' AND status ILIKE '%Accepted%' "
        "AND (university ILIKE '%Georgetown%' OR university ILIKE '%MIT%' "
        "OR university ILIKE '%Stanford%' OR university ILIKE '%Carnegie Mellon%') "
        "AND program ILIKE '%Computer Science%' AND degree ILIKE '%PhD%'", 1))
    print(f"8. Target PhD CS Acceptances (Original): {cur.fetchone()[0]}")

    cur.execute(build_query(
        "SELECT COUNT(*) FROM applicants "
        "WHERE term LIKE '%2025%' AND status ILIKE '%Accepted%' "
        "AND llm_generated_university IN ("
        "'Georgetown University','Massachusetts Institute of Technology',"
        "'Stanford University','Carnegie Mellon University') "
        "AND llm_generated_program ILIKE '%Computer Science%' "
        "AND degree ILIKE '%PhD%'", 1))
    print(f"9. Target PhD CS Acceptances (LLM): {cur.fetchone()[0]}")

    cur.close()
    conn.close()


if __name__ == "__main__":
    run_queries()
