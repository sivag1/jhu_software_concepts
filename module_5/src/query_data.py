"""
Module to query the applicant database and generate analysis metrics.

This script connects to the PostgreSQL database and executes various SQL queries
to answer specific questions about the applicant data. All queries use psycopg
sql.SQL composition with enforced LIMIT clauses.
"""

import os

import psycopg
from dotenv import load_dotenv

from module_5.src.sql_utils import build_query

# Load environment variables
load_dotenv()

DB_PARAMS = {
    "host": os.getenv("DB_HOST"),
    "dbname": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
}


def run_queries():
    """Execute a series of SQL queries to analyze applicant data.

    Calculates metrics including total entries for specific terms,
    demographics, average GPA and GRE scores, and acceptance rates.
    All queries use psycopg sql.SQL composition with enforced LIMIT clauses.
    """
    conn = None
    try:
        conn = psycopg.connect(**DB_PARAMS)
        cur = conn.cursor()

        # 1. Fall 2025 entries
        cur.execute(build_query(
            "SELECT COUNT(*) FROM applicants WHERE term = 'Fall 2025'",
            limit=1,
        ))
        q1 = cur.fetchone()[0]

        # 2. % International students (Not American or Other)
        cur.execute(build_query(
            "SELECT ROUND("
            "(COUNT(*) FILTER (WHERE us_or_international NOT IN ('American', 'Other')) * 100.0)"
            " / COUNT(*), 2) FROM applicants",
            limit=1,
        ))
        q2 = cur.fetchone()[0]

        # 3. Average metrics (GPA, GRE, GRE V, GRE AW)
        cur.execute(build_query(
            "SELECT AVG(gpa), AVG(gre), AVG(gre_v), AVG(gre_aw) FROM applicants",
            limit=1,
        ))
        q3 = cur.fetchone()

        # 4. Average GPA of American students in Fall 2025
        cur.execute(build_query(
            "SELECT AVG(gpa) FROM applicants "
            "WHERE us_or_international = 'American' AND term = 'Fall 2025'",
            limit=1,
        ))
        q4 = cur.fetchone()[0]

        # 5. % Acceptances for Fall 2025
        cur.execute(build_query(
            "SELECT ROUND("
            "(COUNT(*) FILTER (WHERE status ILIKE '%Accepted%' AND term = 'Fall 2025') * 100.0)"
            " / NULLIF(COUNT(*) FILTER (WHERE term = 'Fall 2025'), 0), 2) FROM applicants",
            limit=1,
        ))
        q5 = cur.fetchone()[0]

        # 6. Average GPA of Fall 2025 Acceptances
        cur.execute(build_query(
            "SELECT AVG(gpa) FROM applicants "
            "WHERE term = 'Fall 2025' AND status ILIKE '%Accepted%'",
            limit=1,
        ))
        q6 = cur.fetchone()[0]

        # 7. JHU MS CS entries
        cur.execute(build_query(
            "SELECT COUNT(*) FROM applicants "
            "WHERE (university ILIKE '%Johns Hopkins%' OR university ILIKE '%JHU%') "
            "AND (program ILIKE '%Computer Science%' "
            "OR llm_generated_program ILIKE '%Computer Science%') "
            "AND degree ILIKE '%Masters%'",
            limit=1,
        ))
        q7 = cur.fetchone()[0]

        # 8. Specific Universities PhD CS Acceptances 2025 (Standard Fields)
        cur.execute(build_query(
            "SELECT COUNT(*) FROM applicants "
            "WHERE term LIKE '%2025%' AND status ILIKE '%Accepted%' "
            "AND (university ILIKE '%Georgetown%' OR university ILIKE '%MIT%' "
            "OR university ILIKE '%Stanford%' OR university ILIKE '%Carnegie Mellon%') "
            "AND program ILIKE '%Computer Science%' AND degree ILIKE '%PhD%'",
            limit=1,
        ))
        q8 = cur.fetchone()[0]

        # 9. Same as Q8 but using LLM Generated Fields
        cur.execute(build_query(
            "SELECT COUNT(*) FROM applicants "
            "WHERE term LIKE '%2025%' AND status ILIKE '%Accepted%' "
            "AND (llm_generated_university IN ("
            "'Georgetown University', 'Massachusetts Institute of Technology', "
            "'Stanford University', 'Carnegie Mellon University')) "
            "AND llm_generated_program ILIKE '%Computer Science%' "
            "AND degree ILIKE '%PhD%'",
            limit=1,
        ))
        q9 = cur.fetchone()[0]

        # 10. Average GRE Quant score for MIT applicants
        cur.execute(build_query(
            "SELECT AVG(gre) FROM applicants "
            "WHERE university ILIKE '%MIT%' "
            "OR llm_generated_university = 'Massachusetts Institute of Technology'",
            limit=1,
        ))
        q10 = cur.fetchone()[0]

        # 11. University with highest average GPA for accepted students
        cur.execute(build_query(
            "SELECT university, AVG(gpa) as avg_gpa FROM applicants "
            "WHERE status ILIKE '%Accepted%' AND gpa IS NOT NULL "
            "GROUP BY university ORDER BY avg_gpa DESC",
            limit=1,
        ))
        q11 = cur.fetchone()

        # Display Results
        print("--- Assignment Analysis Results ---")
        print(f"1. Fall 2025 entries: {q1}")
        print(f"2. % International: {q2}%")
        print(f"3. Avg GPA/GRE/GRE_V/GRE_AW: {q3}")
        print(f"4. Avg GPA American (Fall 2025): {q4}")
        print(f"5. % Accepted (Fall 2025): {q5}%")
        print(f"6. Avg GPA Accepted (Fall 2025): {q6}")
        print(f"7. JHU MS CS entries: {q7}")
        print(f"8. Target PhD CS Acceptances (Original): {q8}")
        print(f"9. Target PhD CS Acceptances (LLM): {q9}")
        print("\n--- Curiosity Questions ---")
        print(f"10. Avg GRE for MIT: {q10}")
        print(f"11. Top School by GPA: {q11}")

    except Exception as exc:  # pylint: disable=broad-exception-caught
        print(f"Error: {exc}")
    finally:
        if conn:
            cur.close()
            conn.close()


if __name__ == "__main__":
    run_queries()
