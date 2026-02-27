"""Load applicant data from JSON into PostgreSQL.

Reads NDJSON or JSON-array data from a file and inserts into the applicants
table using parameterized queries. Supports both initial seed and incremental
loads with ON CONFLICT (url) DO NOTHING for idempotency.

Also creates the ingestion_watermarks table for tracking incremental loads.
"""

from __future__ import annotations

import json
import os
import sys

import psycopg
from psycopg import sql


def load_data(json_path=None, db_url=None):
    """Load data from a JSON file into the applicants table.

    Args:
        json_path: Path to JSON/NDJSON file. Defaults to SEED_JSON env var.
        db_url: PostgreSQL connection string. Defaults to DATABASE_URL env var.
    """
    json_path = json_path or os.environ.get("SEED_JSON", "/data/applicant_data.json")
    db_url = db_url or os.environ.get("DATABASE_URL", "")

    if not os.path.exists(json_path):
        print(f"Error: File {json_path} not found.")
        return

    # Read data — support JSON array, NDJSON, and concatenated JSON objects
    with open(json_path, "r", encoding="utf-8") as f:
        content = f.read().strip()
        if content.startswith("["):
            data = json.loads(content)
        else:
            # Try NDJSON first (one object per line)
            try:
                data = [json.loads(line) for line in content.splitlines() if line.strip()]
            except json.JSONDecodeError:
                # Concatenated multi-line JSON objects — wrap in array with commas
                # Insert commas between adjacent top-level objects: "}\n{" -> "},\n{"
                wrapped = "[" + content.replace("}\n{", "},\n{") + "]"
                data = json.loads(wrapped)

    conn = psycopg.connect(db_url)
    cur = conn.cursor()

    # Ensure watermarks table exists
    cur.execute(sql.SQL(
        "CREATE TABLE IF NOT EXISTS ingestion_watermarks ("
        "source TEXT PRIMARY KEY, "
        "last_seen TEXT, "
        "updated_at TIMESTAMPTZ DEFAULT now())"
    ))

    insert_sql = sql.SQL(
        "INSERT INTO applicants "
        "(program, university, degree, status, term, us_or_international, "
        "comments, decision_date, date_added, url, "
        "gpa, gre, gre_v, gre_aw, llm_generated_program, llm_generated_university) "
        "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) "
        "ON CONFLICT (url) DO NOTHING"
    )

    count = 0
    for entry in data:
        cur.execute(insert_sql, (
            entry.get("program"),
            entry.get("university"),
            entry.get("degree"),
            entry.get("status"),
            entry.get("term"),
            entry.get("US/International"),
            entry.get("comments"),
            entry.get("decisionDate") or None,
            entry.get("date_added") or None,
            entry.get("url"),
            entry.get("gpa"),
            entry.get("greScore"),
            entry.get("greV"),
            entry.get("greAW"),
            entry.get("llm-generated-program"),
            entry.get("llm-generated-university"),
        ))
        count += 1

    conn.commit()
    print(f"Loaded {count} records (duplicates skipped via ON CONFLICT).")
    cur.close()
    conn.close()


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else None
    load_data(json_path=path)
