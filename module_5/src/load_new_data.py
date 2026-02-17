"""
Module to load new applicant data into the existing PostgreSQL database.

This script reads a JSON file, checks for existing records to avoid duplicates
based on URL, and inserts new records into the 'applicants' table.
All SQL uses psycopg sql.SQL composition for safe query construction.
"""

import json
import os

import psycopg
from dotenv import load_dotenv
from psycopg import sql

# Load environment variables from .env file
load_dotenv()

# Database connection parameters
DB_PARAMS = {
    "host": os.getenv("DB_HOST"),
    "dbname": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
}


def load_new_records():
    """Load new records from a JSON file into the database.

    Steps:
    1. Reads the JSON file.
    2. Connects to the database.
    3. Checks for existing URLs to prevent duplicates.
    4. Inserts new unique records.
    """
    conn = None
    try:
        # 1. Load Data from JSON file
        file_path = 'llm_extend_applicant_data.json'

        if not os.path.exists(file_path):
            print(f"Error: File {file_path} not found.")
            return

        with open(file_path, 'r', encoding='utf-8') as f:
            data = []
            for line in f:
                line = line.strip()
                if line:
                    data.append(json.loads(line))

        # 2. Connect to PostgreSQL
        conn = psycopg.connect(**DB_PARAMS)
        cur = conn.cursor()
        print("Connected to PostgreSQL successfully.")

        # 3. Check for existing records using sql.SQL composition
        cur.execute(sql.SQL("SELECT to_regclass('public.applicants')"))
        if not cur.fetchone()[0]:
            print("Table 'applicants' does not exist. Please run load_data.py first.")
            return

        # Fetch existing URLs with enforced LIMIT for safety
        # Note: LIMIT 100 enforced per policy; in production, use pagination
        cur.execute(sql.SQL(
            "SELECT url FROM applicants WHERE url IS NOT NULL LIMIT {limit}"
        ).format(limit=sql.Literal(100)))
        existing_urls = {row[0] for row in cur.fetchall()}
        print(f"Found {len(existing_urls)} existing records in the database.")

        # 4. Insert New Data using parameterized queries
        insert_query = sql.SQL(
            "INSERT INTO applicants ("
            "program, university, degree, status, term, us_or_international, "
            "comments, decision_date, date_added, url, "
            "gpa, gre, gre_v, gre_aw, "
            "llm_generated_program, llm_generated_university"
            ") VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
        )

        new_count = 0
        skipped_count = 0

        for entry in data:
            url = entry.get('url')

            if url and url in existing_urls:
                skipped_count += 1
                continue

            cur.execute(insert_query, (
                entry.get('program'),
                entry.get('university'),
                entry.get('degree'),
                entry.get('status'),
                entry.get('term'),
                entry.get('US/International'),
                entry.get('comments'),
                entry.get('decisionDate') or None,
                entry.get('date_added') or None,
                url,
                entry.get('gpa'),
                entry.get('greScore'),
                entry.get('greV'),
                entry.get('greAW'),
                entry.get('llm-generated-program'),
                entry.get('llm-generated-university'),
            ))

            if url:
                existing_urls.add(url)
            new_count += 1

        conn.commit()
        print(f"Operation complete. Added {new_count} new records. "
              f"Skipped {skipped_count} existing records.")

    except Exception as exc:  # pylint: disable=broad-exception-caught
        print(f"Error: {exc}")
    finally:
        if conn:
            cur.close()
            conn.close()


if __name__ == "__main__":
    load_new_records()
