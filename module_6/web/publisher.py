"""RabbitMQ publisher for task messages.

Publishes durable messages to a direct exchange with delivery_mode=2
for persistent storage. Connections are opened per-publish and closed
in a finally block to avoid leaking resources.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone

import pika

EXCHANGE = "tasks"
QUEUE = "tasks_q"
ROUTING_KEY = "tasks"


def _open_channel():
    """Open a RabbitMQ connection and declare durable exchange/queue.

    Returns:
        tuple: (connection, channel) pair. Caller must close the connection.
    """
    url = os.environ["RABBITMQ_URL"]
    params = pika.URLParameters(url)
    conn = pika.BlockingConnection(params)
    ch = conn.channel()

    ch.exchange_declare(exchange=EXCHANGE, exchange_type="direct", durable=True)
    ch.queue_declare(queue=QUEUE, durable=True)
    ch.queue_bind(exchange=EXCHANGE, queue=QUEUE, routing_key=ROUTING_KEY)

    return conn, ch


def publish_task(kind: str, payload: dict | None = None, headers: dict | None = None) -> None:
    """Publish a task message to RabbitMQ.

    Args:
        kind: Task type (e.g. 'scrape_new_data', 'recompute_analytics').
        payload: Optional JSON-serializable payload dict.
        headers: Optional AMQP headers dict.

    Raises:
        Exception: Re-raised on publish failure so Flask can return 503.
    """
    body = json.dumps(
        {"kind": kind, "ts": datetime.now(timezone.utc).isoformat(), "payload": payload or {}},
        separators=(",", ":"),
    ).encode("utf-8")

    conn, ch = _open_channel()
    try:
        ch.basic_publish(
            exchange=EXCHANGE,
            routing_key=ROUTING_KEY,
            body=body,
            properties=pika.BasicProperties(delivery_mode=2, headers=headers or {}),
            mandatory=False,
        )
    finally:
        conn.close()
