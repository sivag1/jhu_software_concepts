"""RabbitMQ consumer for background task processing.

Connects to RabbitMQ, consumes from tasks_q with prefetch_count=1,
routes messages by 'kind', and acks only after successful DB commit.
Each message is processed in its own database transaction.
"""

from __future__ import annotations

import json
import logging
import os
import re
import time
import urllib.request
import urllib.parse

import pika
import psycopg
from psycopg import sql
from bs4 import BeautifulSoup

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger(__name__)

EXCHANGE = "tasks"
QUEUE = "tasks_q"
ROUTING_KEY = "tasks"


# ---------------------------------------------------------------------------
# Scraper (adapted from module_5 GradCafeScraper)
# ---------------------------------------------------------------------------

def _fetch_page(page_num):
    """Fetch a single page of GradCafe results."""
    base_url = "https://www.thegradcafe.com/survey/index.php"
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/119.0.0.0 Safari/537.36"
        ),
    }
    params = {"q": "", "t": "a", "o": "", "page": page_num}
    url = f"{base_url}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req) as resp:
        return resp.read()


def _parse_decision(text):
    """Parse decision status and date."""
    dec = re.search(r"(Accepted|Rejected|Wait listed|Interview)", text, re.I)
    date = re.search(r"on\s*(.*)", text, re.I)
    return (dec.group(1) if dec else "Unknown", date.group(1) if date else None)


def _determine_degree(prog):
    """Determine degree type from program text."""
    if "PhD" in prog:
        return "PhD"
    if "Masters" in prog:
        return "Masters"
    return "Other"


def _parse_stats(stats_text):
    """Parse GPA, GRE scores, term, and student type from raw stats text."""
    data = {}

    gpa_match = re.search(r"GPA\s*([\d.]+)", stats_text, re.I)
    if gpa_match:
        data["gpa"] = gpa_match.group(1)

    gre_match = re.search(r"GRE\s*(\d+)", stats_text, re.I)
    if gre_match:
        data["greScore"] = gre_match.group(1)

    gre_v_match = re.search(r"GRE V\s*(\d+)", stats_text, re.I)
    if gre_v_match:
        data["greV"] = gre_v_match.group(1)

    gre_aw_match = re.search(r"GRE AW\s*([\d.]+)", stats_text, re.I)
    if gre_aw_match:
        data["greAW"] = gre_aw_match.group(1)

    if "International" in stats_text:
        data["US/International"] = "International"
    elif "American" in stats_text:
        data["US/International"] = "American"

    sem_year = re.search(r"(Fall|Spring|Summer|Winter)\s*(\d{4})", stats_text, re.I)
    if sem_year:
        data["term"] = sem_year.group(1) + " " + sem_year.group(2)

    return data


def _scrape_new_records(existing_urls, max_pages=50):
    """Scrape GradCafe for records not already in existing_urls.

    Returns a list of record dicts.
    """
    records = []
    for page in range(1, max_pages + 1):
        try:
            html = _fetch_page(page)
        except Exception as exc:
            log.warning("Failed to fetch page %d: %s", page, exc)
            break

        soup = BeautifulSoup(html, "html.parser")
        table = soup.find("table")
        if not table:
            break

        rows = table.find_all("tr")
        stop = False
        for i in range(1, len(rows)):
            tds = rows[i].find_all("td")
            if len(tds) < 4:
                continue

            link = rows[i].find("a", href=re.compile(r"/result/\d+"))
            entry_url = None
            if link and "href" in link.attrs:
                path = link["href"]
                entry_url = f"https://www.thegradcafe.com{path}" if path.startswith("/") else path

            if entry_url and entry_url in existing_urls:
                log.info("Found existing record %s — stopping.", entry_url)
                stop = True
                break

            decision, dec_date = _parse_decision(tds[3].get_text(strip=True))
            comments = ""
            if i + 2 < len(rows) and len(rows[i + 2].find_all("td")) == 1:
                comments = rows[i + 2].get_text(strip=True)[:500]

            # Collect raw text from this row and adjacent rows for stats parsing
            stats_text = rows[i].get_text(" ", strip=True)
            if i + 1 < len(rows):
                stats_text += " " + rows[i + 1].get_text(" ", strip=True)
            if i + 2 < len(rows):
                stats_text += " " + rows[i + 2].get_text(" ", strip=True)
            parsed = _parse_stats(stats_text)

            records.append({
                "university": re.sub(r"Report$", "", tds[0].get_text(strip=True)).strip(),
                "program": tds[1].get_text(strip=True),
                "degree": _determine_degree(tds[1].get_text(strip=True)),
                "status": decision,
                "decisionDate": dec_date,
                "date_added": tds[2].get_text(strip=True),
                "url": entry_url,
                "comments": comments,
                "term": parsed.get("term"),
                "US/International": parsed.get("US/International"),
                "gpa": parsed.get("gpa"),
                "greScore": parsed.get("greScore"),
                "greV": parsed.get("greV"),
                "greAW": parsed.get("greAW"),
            })

        if stop:
            break
        time.sleep(1)

    log.info("Scraped %d new records.", len(records))
    return records


# ---------------------------------------------------------------------------
# Task handlers
# ---------------------------------------------------------------------------

def _get_db_conn():
    """Return a psycopg connection from DATABASE_URL."""
    return psycopg.connect(os.environ["DATABASE_URL"])


def handle_scrape_new_data(payload):
    """Scrape new data, insert into DB with idempotent upserts, update watermark."""
    conn = _get_db_conn()
    try:
        cur = conn.cursor()

        # Read watermark
        cur.execute(sql.SQL(
            "SELECT last_seen FROM ingestion_watermarks WHERE source = %s"
        ), ("gradcafe",))
        row = cur.fetchone()
        last_seen = row[0] if row else None

        # Fetch existing URLs for dedup
        cur.execute(sql.SQL(
            "SELECT url FROM applicants WHERE url IS NOT NULL "
            "ORDER BY date_added DESC LIMIT {limit}"
        ).format(limit=sql.Literal(100)))
        existing_urls = {r[0] for r in cur.fetchall()}

        # Scrape
        records = _scrape_new_records(existing_urls)
        if not records:
            log.info("No new records to insert.")
            conn.commit()
            return

        # Batch insert with ON CONFLICT DO NOTHING
        insert_sql = sql.SQL(
            "INSERT INTO applicants "
            "(program, university, degree, status, term, us_or_international, "
            "comments, decision_date, date_added, url, "
            "gpa, gre, gre_v, gre_aw, llm_generated_program, llm_generated_university) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) "
            "ON CONFLICT (url) DO NOTHING"
        )

        max_url = last_seen
        for rec in records:
            cur.execute(insert_sql, (
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

        # Update watermark
        if max_url:
            cur.execute(sql.SQL(
                "INSERT INTO ingestion_watermarks (source, last_seen) "
                "VALUES (%s, %s) "
                "ON CONFLICT (source) DO UPDATE SET last_seen = EXCLUDED.last_seen, "
                "updated_at = now()"
            ), ("gradcafe", max_url))

        conn.commit()
        log.info("Inserted up to %d new records.", len(records))
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def handle_recompute_analytics(payload):
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

    except Exception as exc:
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
