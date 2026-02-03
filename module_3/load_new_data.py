import psycopg2
import json
import os
from dotenv import load_dotenv
from psycopg2 import sql

# Load environment variables from .env file
load_dotenv()

# Database connection parameters
DB_PARAMS = {
    "host": os.getenv("DB_HOST"),
    "database": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD")
}

def load_new_records():
    conn = None
    try:
        # 1. Load Data from JSON file
        # Using the same file path as load_data.py
        file_path = 'llm_extend_applicant_data.json'
        
        if not os.path.exists(file_path):
            print(f"Error: File {file_path} not found.")
            return

        with open(file_path, 'r', encoding='utf-8') as f:
            data = []
            for line in f:
                line = line.strip()
                if line:  # Skip empty lines
                    data.append(json.loads(line))
        
        # 2. Connect to PostgreSQL
        conn = psycopg2.connect(**DB_PARAMS)
        cur = conn.cursor()
        print("Connected to PostgreSQL successfully.")

        # 3. Check for existing records
        # Check if table exists
        cur.execute("SELECT to_regclass('public.applicants');")
        if not cur.fetchone()[0]:
            print("Table 'applicants' does not exist. Please run load_data.py first.")
            return

        # Fetch all existing URLs to check against
        cur.execute("SELECT url FROM applicants WHERE url IS NOT NULL")
        existing_urls = {row[0] for row in cur.fetchall()}
        print(f"Found {len(existing_urls)} existing records in the database.")

        # 4. Insert New Data
        insert_query = sql.SQL("""
            INSERT INTO applicants (
                program, university, degree, status, term, us_or_international,
                comments, decision_date, date_added, url, 
                gpa, gre, gre_v, gre_aw, 
                llm_generated_program, llm_generated_university
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """)

        new_count = 0
        skipped_count = 0

        for entry in data:
            url = entry.get('url')
            
            # Check if record exists in DB (or if we just added it in this batch)
            if url and url in existing_urls:
                skipped_count += 1
                continue
            
            # Insert new record
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
                entry.get('llm-generated-university')
            ))
            
            # Add to set to handle duplicates within the file itself
            if url:
                existing_urls.add(url)
            new_count += 1

        conn.commit()
        print(f"Operation complete. Added {new_count} new records. Skipped {skipped_count} existing records.")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        if conn:
            cur.close()
            conn.close()

if __name__ == "__main__":
    load_new_records()
