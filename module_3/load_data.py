import psycopg2
import json
import os
from dotenv import load_dotenv
from psycopg2 import sql

# Load environment variables from .env file
load_dotenv()

# Database connection parameters for your Windows local Postgres
DB_PARAMS = {
    "host": os.getenv("DB_HOST"),
    "database": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD")
}

def load_data():
    conn = None
    try:
        # 1. Load Data from JSON file
        # Handle newline-delimited JSON (NDJSON) format
        with open('../module_2/llm_extend_applicant_data.json', 'r', encoding='utf-8') as f:
            data = []
            for line in f:
                line = line.strip()
                if line:  # Skip empty lines
                    data.append(json.loads(line))
        
        # 2. Connect to PostgreSQL
        conn = psycopg2.connect(**DB_PARAMS)
        cur = conn.cursor()
        print("Connected to PostgreSQL successfully.")

        # 3. Create the Table
        create_table_query = """
        DROP TABLE IF EXISTS applicants;
        CREATE TABLE applicants (
            p_id SERIAL PRIMARY KEY,
            program TEXT,
            university TEXT,
            degree TEXT,
            status TEXT,
            term TEXT,
            us_or_international TEXT,
            comments TEXT,
            decision_date TEXT,
            date_added DATE,
            url TEXT,
            gpa FLOAT,
            gre FLOAT,
            gre_v FLOAT,
            gre_aw FLOAT,
            llm_generated_program TEXT,
            llm_generated_university TEXT
        );
        """
        cur.execute(create_table_query)

        # 4. Insert Data from JSON list
        for entry in data:
            insert_query = sql.SQL("""
                INSERT INTO applicants (
                    program, university, degree, status, term, us_or_international,
                    comments, decision_date, date_added, url, 
                    gpa, gre, gre_v, gre_aw, 
                    llm_generated_program, llm_generated_university
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """)
            
            # Using entry.get('key') prevents the script from crashing if a field is missing
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
                entry.get('llm-generated-university')
            ))

        conn.commit()
        print(f"Successfully loaded {len(data)} records into the database.")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        if conn:
            cur.close()
            conn.close()

if __name__ == "__main__":
    load_data()