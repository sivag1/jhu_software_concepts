"""Tests for scrape and recompute button endpoints."""

import pytest


@pytest.mark.buttons
def test_post_scrape_queued(client, mock_publisher, mock_db):
    """POST /scrape returns 202 with queued status."""
    response = client.post("/scrape")
    assert response.status_code == 202
    data = response.get_json()
    assert data["status"] == "queued"
    assert data["task"] == "scrape_new_data"
    mock_publisher.assert_called_once_with("scrape_new_data", payload={})


@pytest.mark.buttons
def test_post_recompute_queued(client, mock_publisher, mock_db):
    """POST /recompute returns 202 with queued status."""
    response = client.post("/recompute")
    assert response.status_code == 202
    data = response.get_json()
    assert data["status"] == "queued"
    assert data["task"] == "recompute_analytics"
    mock_publisher.assert_called_once_with("recompute_analytics", payload={})


@pytest.mark.buttons
def test_scrape_publish_failure(client, mock_publisher, mock_db):
    """POST /scrape returns 503 when publish fails."""
    mock_publisher.side_effect = Exception("RabbitMQ down")
    response = client.post("/scrape")
    assert response.status_code == 503
    data = response.get_json()
    assert data["error"] == "publish_failed"


@pytest.mark.buttons
def test_recompute_publish_failure(client, mock_publisher, mock_db):
    """POST /recompute returns 503 when publish fails."""
    mock_publisher.side_effect = Exception("RabbitMQ down")
    response = client.post("/recompute")
    assert response.status_code == 503
    data = response.get_json()
    assert data["error"] == "publish_failed"
