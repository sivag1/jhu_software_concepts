# Module 6 — Deploy Anywhere

Microservice refactor of the Grad School Cafe Data Analysis dashboard.
The web tier (Flask) is decoupled from data-modifying work via RabbitMQ,
with a background worker handling scraping and analytics recomputation.

## Architecture

| Service    | Description                              | Port  |
|------------|------------------------------------------|-------|
| **web**    | Flask dashboard (read-only DB access)    | 8080  |
| **worker** | RabbitMQ consumer (scrape, analytics)    | —     |
| **db**     | PostgreSQL 16                            | 5432  |
| **rabbitmq** | RabbitMQ 3.13 with management UI      | 15672 |

## Quick Start

```bash
# 1. Clone and navigate
cd module_6

# 2. Copy and edit environment variables
cp .env.example .env

# 3. Build and start all services
docker compose up --build

# 4. Visit the dashboard
# App:      http://localhost:8080
# RabbitMQ: http://localhost:15672 (guest/guest)
```

## Docker Hub

Images are published to Docker Hub:

- `<your-dockerhub-username>/module_6:web-v1`
- `<your-dockerhub-username>/module_6:worker-v1`

### Pull and run from registry

```bash
docker pull <your-dockerhub-username>/module_6:web-v1
docker pull <your-dockerhub-username>/module_6:worker-v1
```

## Data Flow

```
User clicks "Pull Data" button
  → Flask POST /scrape
    → publish_task("scrape_new_data") to RabbitMQ
      → Worker consumer picks up message
        → Scrapes GradCafe for new records
        → INSERT INTO applicants ... ON CONFLICT DO NOTHING
        → Updates ingestion_watermarks
        → basic_ack

User clicks "Update Analysis" button
  → Flask POST /recompute
    → publish_task("recompute_analytics") to RabbitMQ
      → Worker refreshes analytics_summary materialized view
        → basic_ack
```

## Running Tests

```bash
pip install -r requirements-test.txt
cd module_6
python -m pytest -v
```

Tests enforce 100% code coverage on the Flask app (`web/app/__init__.py`).

## Environment Variables

| Variable          | Description                        | Example                                          |
|-------------------|------------------------------------|--------------------------------------------------|
| POSTGRES_USER     | PostgreSQL username                | gradcafe                                         |
| POSTGRES_PASSWORD | PostgreSQL password                | gradcafe_secret                                  |
| POSTGRES_DB       | PostgreSQL database name           | gradcafe                                         |
| DATABASE_URL      | Full PostgreSQL connection string  | postgresql://gradcafe:gradcafe_secret@db:5432/gradcafe |
| RABBITMQ_URL      | AMQP connection string             | amqp://guest:guest@rabbitmq:5672/%2F             |
| FLASK_SECRET      | Flask session secret key           | dev-secret-key                                   |
| SEED_JSON         | Path to seed data JSON             | /data/applicant_data.json                        |
| TARGET_TABLE      | Target DB table                    | applicants                                       |
| ID_KEY            | Unique key for dedup               | url                                              |

## Project Structure

```
module_6/
├── docker-compose.yml
├── .env / .env.example
├── README.md
├── pytest.ini
├── .coveragerc
├── requirements-test.txt
├── web/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── run.py
│   ├── publisher.py
│   └── app/
│       ├── __init__.py
│       └── templates/
│           └── index.html
├── worker/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── consumer.py
│   └── etl/
│       ├── incremental_scraper.py
│       └── query_data.py
├── db/
│   ├── init.sql
│   └── load_data.py
├── data/
│   └── applicant_data.json
├── docs/
└── tests/
    ├── conftest.py
    ├── test_flask_page.py
    ├── test_buttons.py
    ├── test_analysis_format.py
    ├── test_db_insert.py
    └── test_integration_end_to_end.py
```
