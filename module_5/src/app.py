"""
Flask application for the Grad School Cafe Data Analysis dashboard.

This module provides a web interface to view analysis results and trigger
the data ingestion pipeline. All SQL queries use psycopg sql.SQL composition
for safe query construction with enforced LIMIT clauses.
"""

import os
import threading

from flask import Flask, render_template
import psycopg
from dotenv import load_dotenv

from module_5.src.run_pipeline import run_full_pipeline
from module_5.src.sql_utils import build_query

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev_key")

# Global lock to handle busy state for data pipeline
pipeline_lock = threading.Lock()


def get_db_connection():
    """Establish and return a connection to the PostgreSQL database."""
    return psycopg.connect(
        host=os.getenv("DB_HOST"),
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
    )


def run_analysis_queries():
    """Run analytical queries against the database for the dashboard.

    All queries use psycopg sql.SQL composition with enforced LIMIT clauses.

    Returns:
        tuple: A dictionary of query results and the total record count.
    """
    conn = get_db_connection()
    cur = conn.cursor()
    results = {}

    # 1. Fall 2026 entries
    cur.execute(build_query(
        "SELECT COUNT(*) FROM applicants WHERE term = 'Fall 2026'",
        limit=1,
    ))
    results['q1'] = cur.fetchone()[0]

    # 2. % International students (not American or Other)
    cur.execute(build_query(
        "SELECT ROUND("
        "(COUNT(*) FILTER (WHERE us_or_international NOT IN ('American', 'Other')) * 100.0) / "
        "NULLIF(COUNT(*), 0), 2) FROM applicants",
        limit=1,
    ))
    results['q2'] = cur.fetchone()[0]

    # 3. Average GPA, GRE, GRE V, GRE AW
    cur.execute(build_query(
        "SELECT AVG(gpa), AVG(gre), AVG(gre_v), AVG(gre_aw) FROM applicants",
        limit=1,
    ))
    metrics = cur.fetchone()
    results['q3'] = {
        'gpa': round(metrics[0], 2) if metrics[0] else 0,
        'gre': round(metrics[1], 2) if metrics[1] else 0,
        'gre_v': round(metrics[2], 2) if metrics[2] else 0,
        'gre_aw': round(metrics[3], 2) if metrics[3] else 0,
    }

    # 4. Average GPA of American students in Fall 2026
    cur.execute(build_query(
        "SELECT AVG(gpa) FROM applicants "
        "WHERE us_or_international = 'American' AND term = 'Fall 2026'",
        limit=1,
    ))
    res4 = cur.fetchone()[0]
    results['q4'] = round(res4, 2) if res4 else 0

    # 5. % Acceptances for Fall 2026
    cur.execute(build_query(
        "SELECT ROUND("
        "(COUNT(*) FILTER (WHERE status ILIKE '%Accepted%' AND term = 'Fall 2026') * 100.0) / "
        "NULLIF(COUNT(*) FILTER (WHERE term = 'Fall 2026'), 0), 2) FROM applicants",
        limit=1,
    ))
    results['q5'] = cur.fetchone()[0]

    # 6. Average GPA of Fall 2026 Acceptances
    cur.execute(build_query(
        "SELECT AVG(gpa) FROM applicants "
        "WHERE term = 'Fall 2026' AND status ILIKE '%Accepted%'",
        limit=1,
    ))
    res6 = cur.fetchone()[0]
    results['q6'] = round(res6, 2) if res6 else 0

    # 7. JHU MS CS entries
    cur.execute(build_query(
        "SELECT COUNT(*) FROM applicants "
        "WHERE (university ILIKE '%Johns Hopkins%' OR university ILIKE '%JHU%') "
        "AND degree ILIKE '%Masters%' "
        "AND (program ILIKE '%Computer Science%' "
        "OR llm_generated_program ILIKE '%Computer Science%')",
        limit=1,
    ))
    results['q7'] = cur.fetchone()[0]

    # 8. Targeted PhD CS Acceptances (Original Fields)
    cur.execute(build_query(
        "SELECT COUNT(*) FROM applicants "
        "WHERE term LIKE '%2025%' AND status ILIKE '%Accepted%' "
        "AND degree ILIKE '%PhD%' "
        "AND (university ILIKE '%Georgetown%' OR university ILIKE '%MIT%' "
        "OR university ILIKE '%Stanford%' OR university ILIKE '%Carnegie Mellon%') "
        "AND program ILIKE '%Computer Science%'",
        limit=1,
    ))
    results['q8'] = cur.fetchone()[0]

    # 9. Targeted PhD CS Acceptances (LLM Fields)
    cur.execute(build_query(
        "SELECT COUNT(*) FROM applicants "
        "WHERE term LIKE '%2025%' AND status ILIKE '%Accepted%' "
        "AND degree ILIKE '%PhD%' "
        "AND (llm_generated_university IN ("
        "'Georgetown University', 'Massachusetts Institute of Technology', "
        "'Stanford University', 'Carnegie Mellon University')) "
        "AND llm_generated_program ILIKE '%Computer Science%'",
        limit=1,
    ))
    results['q9'] = cur.fetchone()[0]

    # Total Records
    cur.execute(build_query(
        "SELECT COUNT(*) FROM applicants",
        limit=1,
    ))
    total_records = cur.fetchone()[0]

    cur.close()
    conn.close()
    return results, total_records


@app.route('/')
def index():
    """Render the main dashboard page with analysis results."""
    analysis_results, total_records = run_analysis_queries()
    return render_template(
        'index.html', results=analysis_results, total_records=total_records,
    )


@app.route('/update_analysis', methods=['POST'])
def update_analysis():
    """Handle update analysis request.

    Returns 200 OK if successful (client can reload), or 409 if busy.
    """
    if pipeline_lock.locked():
        return "Busy", 409
    return "OK", 200


@app.route('/pull_data', methods=['POST'])
def pull_data():
    """Trigger the background data pipeline.

    Executes the full pipeline and returns status.
    Returns 200 on success, 409 if busy, or 500 on error.
    """
    if pipeline_lock.locked():
        return "Busy", 409

    try:
        with pipeline_lock:
            run_full_pipeline()
            return {"ok": True}, 200
    except Exception as exc:  # pylint: disable=broad-exception-caught
        return {"error": str(exc)}, 500


if __name__ == '__main__':  # pragma: no cover
    app.run(debug=True)
