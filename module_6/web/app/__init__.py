"""Flask application factory for Grad School Cafe Data Analysis dashboard.

All SQL queries use psycopg sql.SQL composition for safe query construction
with enforced LIMIT clauses. Long-running tasks are published to RabbitMQ
and processed asynchronously by the worker service.
"""

from __future__ import annotations

import os

from flask import Flask, jsonify, render_template, current_app
import psycopg
from psycopg import sql

from publisher import publish_task


def create_app(test_config=None):
    """Create and configure the Flask application.

    Args:
        test_config: Optional dict of config overrides for testing.

    Returns:
        Flask: Configured Flask application instance.
    """
    app = Flask(__name__)
    app.secret_key = os.environ.get("FLASK_SECRET", "dev-key")

    if test_config:
        app.config.update(test_config)

    # ------------------------------------------------------------------ helpers
    def get_db_connection():
        """Return a psycopg connection using DATABASE_URL."""
        return psycopg.connect(os.environ.get("DATABASE_URL", ""))

    def clamp_limit(limit=100):
        """Clamp a LIMIT value to [1, 100]."""
        return max(1, min(100, int(limit)))

    def build_query(query_str, limit=100):
        """Wrap a SQL string in sql.SQL and append a clamped LIMIT."""
        clamped = clamp_limit(limit)
        return sql.SQL("{query} LIMIT {limit}").format(
            query=sql.SQL(query_str),
            limit=sql.Literal(clamped),
        )

    def run_analysis_queries():
        """Run analytical queries and return (results_dict, total_records)."""
        conn = get_db_connection()
        cur = conn.cursor()
        results = {}

        stmt = build_query(
            "SELECT COUNT(*) FROM applicants WHERE term = %s", limit=1,
        )
        cur.execute(stmt, ("Fall 2026",))
        results["q1"] = cur.fetchone()[0]

        stmt = build_query(
            "SELECT ROUND("
            "(COUNT(*) FILTER (WHERE us_or_international NOT IN (%s, %s)) * 100.0) / "
            "NULLIF(COUNT(*), 0), 2) FROM applicants",
            limit=1,
        )
        cur.execute(stmt, ("American", "Other"))
        results["q2"] = cur.fetchone()[0]

        stmt = build_query(
            "SELECT AVG(gpa), AVG(gre), AVG(gre_v), AVG(gre_aw) FROM applicants",
            limit=1,
        )
        cur.execute(stmt)
        metrics = cur.fetchone()
        results["q3"] = {
            "gpa": round(metrics[0], 2) if metrics[0] else 0,
            "gre": round(metrics[1], 2) if metrics[1] else 0,
            "gre_v": round(metrics[2], 2) if metrics[2] else 0,
            "gre_aw": round(metrics[3], 2) if metrics[3] else 0,
        }

        stmt = build_query(
            "SELECT AVG(gpa) FROM applicants "
            "WHERE us_or_international = %s AND term = %s",
            limit=1,
        )
        cur.execute(stmt, ("American", "Fall 2026"))
        res4 = cur.fetchone()[0]
        results["q4"] = round(res4, 2) if res4 else 0

        stmt = build_query(
            "SELECT ROUND("
            "(COUNT(*) FILTER (WHERE status ILIKE %s AND term = %s) * 100.0) / "
            "NULLIF(COUNT(*) FILTER (WHERE term = %s), 0), 2) FROM applicants",
            limit=1,
        )
        cur.execute(stmt, ("%Accepted%", "Fall 2026", "Fall 2026"))
        results["q5"] = cur.fetchone()[0]

        stmt = build_query(
            "SELECT AVG(gpa) FROM applicants "
            "WHERE term = %s AND status ILIKE %s",
            limit=1,
        )
        cur.execute(stmt, ("Fall 2026", "%Accepted%"))
        res6 = cur.fetchone()[0]
        results["q6"] = round(res6, 2) if res6 else 0

        stmt = build_query(
            "SELECT COUNT(*) FROM applicants "
            "WHERE (university ILIKE %s OR university ILIKE %s) "
            "AND degree ILIKE %s "
            "AND (program ILIKE %s "
            "OR llm_generated_program ILIKE %s)",
            limit=1,
        )
        cur.execute(stmt, (
            "%Johns Hopkins%", "%JHU%", "%Masters%",
            "%Computer Science%", "%Computer Science%",
        ))
        results["q7"] = cur.fetchone()[0]

        stmt = build_query(
            "SELECT COUNT(*) FROM applicants "
            "WHERE term LIKE %s AND status ILIKE %s "
            "AND degree ILIKE %s "
            "AND (university ILIKE %s OR university ILIKE %s "
            "OR university ILIKE %s OR university ILIKE %s) "
            "AND program ILIKE %s",
            limit=1,
        )
        cur.execute(stmt, (
            "%2025%", "%Accepted%", "%PhD%",
            "%Georgetown%", "%MIT%", "%Stanford%", "%Carnegie Mellon%",
            "%Computer Science%",
        ))
        results["q8"] = cur.fetchone()[0]

        stmt = build_query(
            "SELECT COUNT(*) FROM applicants "
            "WHERE term LIKE %s AND status ILIKE %s "
            "AND degree ILIKE %s "
            "AND llm_generated_university IN (%s, %s, %s, %s) "
            "AND llm_generated_program ILIKE %s",
            limit=1,
        )
        cur.execute(stmt, (
            "%2025%", "%Accepted%", "%PhD%",
            "Georgetown University", "Massachusetts Institute of Technology",
            "Stanford University", "Carnegie Mellon University",
            "%Computer Science%",
        ))
        results["q9"] = cur.fetchone()[0]

        stmt = build_query("SELECT COUNT(*) FROM applicants", limit=1)
        cur.execute(stmt)
        total_records = cur.fetchone()[0]

        cur.close()
        conn.close()
        return results, total_records

    # Attach helpers to app so tests can access them
    app.get_db_connection = get_db_connection
    app.run_analysis_queries = run_analysis_queries
    app.build_query = build_query

    # ------------------------------------------------------------------ routes
    @app.route("/")
    def index():
        """Render the main dashboard with analysis results."""
        analysis_results, total_records = run_analysis_queries()
        return render_template(
            "index.html", results=analysis_results, total_records=total_records,
        )

    @app.route("/scrape", methods=["POST"])
    def enqueue_scrape():
        """Publish a scrape_new_data task to RabbitMQ and return 202."""
        try:
            publish_task("scrape_new_data", payload={})
            return jsonify({"status": "queued", "task": "scrape_new_data"}), 202
        except Exception:
            current_app.logger.exception("Failed to publish scrape_new_data")
            return jsonify({"error": "publish_failed"}), 503

    @app.route("/recompute", methods=["POST"])
    def enqueue_recompute():
        """Publish a recompute_analytics task to RabbitMQ and return 202."""
        try:
            publish_task("recompute_analytics", payload={})
            return jsonify({"status": "queued", "task": "recompute_analytics"}), 202
        except Exception:
            current_app.logger.exception("Failed to publish recompute_analytics")
            return jsonify({"error": "publish_failed"}), 503

    return app
