"""RabbitMQ consumer for background task processing.

Connects to RabbitMQ, consumes from tasks_q with prefetch_count=1,
routes messages by 'kind', and acks only after successful DB commit.
Each message is processed in its own database transaction.
"""

from __future__ import annotations

import json
import logging
import os
import time

import pika
import psycopg
from psycopg import sql

from etl.incremental_scraper import scrape_new_records

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger(__name__)

EXCHANGE = "tasks"
QUEUE = "tasks_q"
ROUTING_KEY = "tasks"


# ---------------------------------------------------------------------------
# Task handlers
# ---------------------------------------------------------------------------

def _get_db_conn():
    """Return a psycopg connection from DATABASE_URL."""
    return psycopg.connect(os.environ["DATABASE_URL"])


def _fetch_existing_urls(cur, limit=100):
    """Return a set of known applicant URLs from the database."""
    cur.execute(sql.SQL(
        "SELECT url FROM applicants WHERE url IS NOT NULL "
        "ORDER BY date_added DESC LIMIT {limit}"
    ).format(limit=sql.Literal(limit)))
    return {r[0] for r in cur.fetchall()}


def _insert_records(cur, records):
    """Batch-insert records with ON CONFLICT DO NOTHING. Return max URL."""
    insert_stmt = sql.SQL(
        "INSERT INTO applicants "
        "(program, university, degree, status, term, us_or_international, "
        "comments, decision_date, date_added, url, "
        "gpa, gre, gre_v, gre_aw, llm_generated_program, llm_generated_university) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) "
        "ON CONFLICT (url) DO NOTHING"
    )

    max_url = None
    for rec in records:
        cur.execute(insert_stmt, (
            rec.get("program"),
            rec.get("university"),
            rec.get("degree"),
            rec.get("status"),
            rec.get("term"),
            rec.get("US/International"),
            rec.get("comments"),
            rec.get("decisionDate"),
            rec.get("date_added"),
            rec.get("url"),
            rec.get("gpa"),
            rec.get("greScore"),
            rec.get("greV"),
            rec.get("greAW"),
            rec.get("llm-generated-program"),
            rec.get("llm-generated-university"),
        ))
        url = rec.get("url") or ""
        if url > (max_url or ""):
            max_url = url

    return max_url


def _update_watermark(cur, max_url):
    """Upsert the ingestion watermark for gradcafe."""
    if max_url:
        cur.execute(sql.SQL(
            "INSERT INTO ingestion_watermarks (source, last_seen) "
            "VALUES (%s, %s) "
            "ON CONFLICT (source) DO UPDATE SET last_seen = EXCLUDED.last_seen, "
            "updated_at = now()"
        ), ("gradcafe", max_url))


def handle_scrape_new_data(_payload):
    """Scrape new data, insert into DB with idempotent upserts, update watermark."""
    conn = _get_db_conn()
    try:
        cur = conn.cursor()
        existing_urls = _fetch_existing_urls(cur)

        records = scrape_new_records(existing_urls)
        if not records:
            log.info("No new records to insert.")
            conn.commit()
            return

        max_url = _insert_records(cur, records)
        _update_watermark(cur, max_url)

        conn.commit()
        log.info("Inserted up to %d new records.", len(records))
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def handle_recompute_analytics(_payload):
    """Refresh the analytics_summary materialized view."""
    conn = _get_db_conn()
    try:
        cur = conn.cursor()
        cur.execute(sql.SQL("REFRESH MATERIALIZED VIEW analytics_summary"))
        conn.commit()
        log.info("Refreshed analytics_summary materialized view.")
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Message dispatcher
# ---------------------------------------------------------------------------

TASK_MAP = {
    "scrape_new_data": handle_scrape_new_data,
    "recompute_analytics": handle_recompute_analytics,
}


def on_message(ch, method, _properties, body):
    """Callback for each consumed message. Routes by 'kind' field."""
    msg = {}
    try:
        msg = json.loads(body)
        kind = msg.get("kind", "")
        payload = msg.get("payload", {})
        log.info("Received task: %s", kind)

        handler = TASK_MAP.get(kind)
        if handler is None:
            log.warning("Unknown task kind: %s — nacking.", kind)
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
            return

        handler(payload)
        ch.basic_ack(delivery_tag=method.delivery_tag)
        log.info("Task %s completed and acked.", kind)

    except (json.JSONDecodeError, KeyError, psycopg.Error) as exc:
        log.exception("Task %s failed: %s", msg.get("kind", "?"), exc)
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)


def main():
    """Connect to RabbitMQ and start consuming."""
    url = os.environ["RABBITMQ_URL"]
    params = pika.URLParameters(url)

    log.info("Connecting to RabbitMQ...")
    retries = 10
    for attempt in range(1, retries + 1):
        try:
            connection = pika.BlockingConnection(params)
            break
        except pika.exceptions.AMQPConnectionError:
            if attempt == retries:
                log.error("Could not connect to RabbitMQ after %d attempts", retries)
                raise
            log.warning("RabbitMQ not ready, retrying in 3s... (%d/%d)", attempt, retries)
            time.sleep(3)
    channel = connection.channel()

    channel.exchange_declare(exchange=EXCHANGE, exchange_type="direct", durable=True)
    channel.queue_declare(queue=QUEUE, durable=True)
    channel.queue_bind(exchange=EXCHANGE, queue=QUEUE, routing_key=ROUTING_KEY)
    channel.basic_qos(prefetch_count=1)

    channel.basic_consume(queue=QUEUE, on_message_callback=on_message)

    log.info("Worker ready — waiting for tasks on %s ...", QUEUE)
    channel.start_consuming()


if __name__ == "__main__":
    main()
