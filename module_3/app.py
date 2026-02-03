"""
Flask application for the Grad School Cafe Data Analysis dashboard.

This module provides a web interface to view analysis results and trigger
the data ingestion pipeline.
"""
import os
import subprocess
from flask import Flask, render_template, request, redirect, url_for, flash
import psycopg2
from dotenv import load_dotenv
from run_pipeline import run_full_pipeline

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev_key")

def get_db_connection():
    """Establishes and returns a connection to the PostgreSQL database."""
    return psycopg2.connect(
        host=os.getenv("DB_HOST"),
        database=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD")
    )

def run_analysis_queries():
    """
    Runs analytical queries against the database for the dashboard.

    Returns:
        tuple: A dictionary of query results and the total record count.
    """
    conn = get_db_connection()
    cur = conn.cursor()
    results = {}

    # 1. Fall 2026 entries
    cur.execute("SELECT COUNT(*) FROM applicants WHERE term = 'Fall 2026';")
    results['q1'] = cur.fetchone()[0]

    # 2. % International students (not American or Other)
    cur.execute("""
        SELECT ROUND((COUNT(*) FILTER (WHERE us_or_international NOT IN ('American', 'Other')) * 100.0) / 
        NULLIF(COUNT(*), 0), 2) FROM applicants;
    """)
    results['q2'] = cur.fetchone()[0]

    # 3. Average GPA, GRE, GRE V, GRE AW
    cur.execute("SELECT AVG(gpa), AVG(gre), AVG(gre_v), AVG(gre_aw) FROM applicants;")
    metrics = cur.fetchone()
    results['q3'] = {
        'gpa': round(metrics[0], 2) if metrics[0] else 0,
        'gre': round(metrics[1], 2) if metrics[1] else 0,
        'gre_v': round(metrics[2], 2) if metrics[2] else 0,
        'gre_aw': round(metrics[3], 2) if metrics[3] else 0
    }

    # 4. Average GPA of American students in Fall 2026
    cur.execute("""
        SELECT AVG(gpa) FROM applicants 
        WHERE us_or_international = 'American' AND term = 'Fall 2026';
    """)
    res4 = cur.fetchone()[0]
    results['q4'] = round(res4, 2) if res4 else 0

    # 5. % Acceptances for Fall 2026
    cur.execute("""
        SELECT ROUND((COUNT(*) FILTER (WHERE status ILIKE '%Accepted%' AND term = 'Fall 2026') * 100.0) / 
        NULLIF(COUNT(*) FILTER (WHERE term = 'Fall 2026'), 0), 2) FROM applicants;
    """)
    results['q5'] = cur.fetchone()[0]

    # 6. Average GPA of Fall 2026 Acceptances
    cur.execute("""
        SELECT AVG(gpa) FROM applicants 
        WHERE term = 'Fall 2026' AND status ILIKE '%Accepted%';
    """)
    res6 = cur.fetchone()[0]
    results['q6'] = round(res6, 2) if res6 else 0

    # 7. JHU MS CS entries
    cur.execute("""
        SELECT COUNT(*) FROM applicants 
        WHERE (university ILIKE '%Johns Hopkins%' OR university ILIKE '%JHU%') 
        AND degree ILIKE '%Masters%' AND (program ILIKE '%Computer Science%' OR llm_generated_program ILIKE '%Computer Science%');
    """)
    results['q7'] = cur.fetchone()[0]

    # 8. Targeted PhD CS Acceptances (Original Fields)
    cur.execute("""
        SELECT COUNT(*) FROM applicants 
        WHERE term LIKE '%2025%' AND status ILIKE '%Accepted%' AND degree ILIKE '%PhD%'
        AND (university ILIKE '%Georgetown%' OR university ILIKE '%MIT%' OR university ILIKE '%Stanford%' OR university ILIKE '%Carnegie Mellon%')
        AND program ILIKE '%Computer Science%';
    """)
    results['q8'] = cur.fetchone()[0]

    # 9. Targeted PhD CS Acceptances (LLM Fields)
    cur.execute("""
        SELECT COUNT(*) FROM applicants 
        WHERE term LIKE '%2025%' AND status ILIKE '%Accepted%' AND degree ILIKE '%PhD%'
        AND (llm_generated_university IN ('Georgetown University', 'Massachusetts Institute of Technology', 'Stanford University', 'Carnegie Mellon University'))
        AND llm_generated_program ILIKE '%Computer Science%';
    """)
    results['q9'] = cur.fetchone()[0]

     # Total Records
    cur.execute("SELECT COUNT(*) FROM applicants;")
    total_records = cur.fetchone()[0]

    cur.close()
    conn.close()
    return results, total_records

@app.route('/')
def index():
    """Renders the main dashboard page with analysis results."""
    # This fulfills Part A by passing query results to the template
    analysis_results, total_records = run_analysis_queries()
    return render_template('index.html', results=analysis_results, total_records=total_records)

@app.route('/pull_data', methods=['POST'])
def pull_data():
    """
    Route to trigger the background data pipeline.

    Executes the full pipeline and redirects back to the index page
    with a status message.
    """
    try:
        # Run the data pipeline (Scrape -> Clean -> LLM -> Load)
        run_full_pipeline()
        flash("Data pull completed successfully!", "success")
    except Exception as e:
        flash(f"Data pull failed: {str(e)}", "error")
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)