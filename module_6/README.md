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

Images are published to [avis777/module_6](https://hub.docker.com/r/avis777/module_6) on Docker Hub:

- `avis777/module_6:v1-web`
- `avis777/module_6:v1-worker`
- `avis777/module_6:v1-db`
- `avis777/module_6:v1-rabbitmq`

### Pull and run from registry

```bash
docker pull avis777/module_6:v1-web
docker pull avis777/module_6:v1-worker
docker pull avis777/module_6:v1-db
docker pull avis777/module_6:v1-rabbitmq
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

## Linting

```bash
# From repo root — requires pylint installed
pylint module_6/web/ module_6/worker/ module_6/db/
```

Pylint configuration lives in the repo-root `.pylintrc`. Current target: **10.00/10**.

## Running Tests

```bash
# Install test dependencies
pip install -r requirements-test.txt

# Run all tests with coverage (from repo root)
pytest module_6/tests/ -v

# Run tests by marker
pytest module_6/tests/ -m web -v
pytest module_6/tests/ -m buttons -v
pytest module_6/tests/ -m analysis -v
pytest module_6/tests/ -m db -v
pytest module_6/tests/ -m integration -v
```

Tests enforce 100% code coverage on the Flask app (`web/app/__init__.py`).
Coverage settings are configured in `pytest.ini` (addopts) and `.coveragerc`.

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
