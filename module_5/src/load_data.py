"""
Module to load applicant data into a PostgreSQL database.

This script reads a JSON file containing applicant data, connects to a
PostgreSQL database, recreates the 'applicants' table, and inserts the data.
All SQL uses psycopg sql.SQL composition for safe query construction.
"""

import json
import os

import psycopg
from dotenv import load_dotenv
from psycopg import sql

# Load environment variables from .env file.
load_dotenv()

# Database connection parameters.
DB_PARAMS = {
    "host": os.getenv("DB_HOST"),
    "dbname": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
}


def load_data():
    """Load data from a JSON file into the PostgreSQL database.

    Steps:
    1. Reads newline-delimited JSON data from a file.
    2. Connects to the PostgreSQL database using environment variables.
    3. Drops the existing 'applicants' table and creates a new one.
    4. Inserts the parsed JSON data into the table.
    """
    conn = None
    try:
        # 1. Load Data from JSON file (NDJSON format).
        with open('../module_2/llm_extend_applicant_data.json', 'r', encoding='utf-8') as f:
            data = []
            for line in f:
                line = line.strip()
                if line:
                    data.append(json.loads(line))

        # 2. Connect to PostgreSQL.
        conn = psycopg.connect(**DB_PARAMS)
        cur = conn.cursor()
        print("Connected to PostgreSQL successfully.")

        # 3. Create the Table using sql.SQL composition (DDL - no LIMIT needed).
        create_table_query = sql.SQL(
            "DROP TABLE IF EXISTS applicants; "
            "CREATE TABLE applicants ("
            "p_id SERIAL PRIMARY KEY, "
            "program TEXT, university TEXT, degree TEXT, status TEXT, "
            "term TEXT, us_or_international TEXT, comments TEXT, "
            "decision_date TEXT, date_added DATE, url TEXT, "
            "gpa FLOAT, gre FLOAT, gre_v FLOAT, gre_aw FLOAT, "
            "llm_generated_program TEXT, llm_generated_university TEXT)"
        )
        cur.execute(create_table_query)

        # 4. Insert Data using parameterized queries for safe value binding.
        insert_query = sql.SQL(
            "INSERT INTO applicants ("
            "program, university, degree, status, term, us_or_international, "
            "comments, decision_date, date_added, url, "
            "gpa, gre, gre_v, gre_aw, "
            "llm_generated_program, llm_generated_university"
            ") VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
        )

        for entry in data:
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
                entry.get('url'),
                entry.get('gpa'),
                entry.get('greScore'),
                entry.get('greV'),
                entry.get('greAW'),
                entry.get('llm-generated-program'),
                entry.get('llm-generated-university'),
            ))

        conn.commit()
        print(f"Successfully loaded {len(data)} records into the database.")

    except Exception as exc:  # pylint: disable=broad-exception-caught
        print(f"Error: {exc}")
    finally:
        if conn:
            cur.close()
            conn.close()


if __name__ == "__main__":
    load_data()
