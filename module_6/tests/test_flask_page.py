"""Tests for Flask page rendering and route existence."""

import pytest


@pytest.mark.web
def test_app_factory_config(client):
    """Assert a testable Flask app is created with required routes."""
    from app import create_app
    application = create_app(test_config={"TESTING": True})
    assert application.config["TESTING"] is True
    adapter = application.url_map.bind("")
    assert adapter.match("/", method="GET")
    assert adapter.match("/scrape", method="POST")
    assert adapter.match("/recompute", method="POST")


@pytest.mark.web
def test_get_analysis_page_load(client, monkeypatch):
    """GET / returns 200 with buttons and Analysis content."""
    mock_html = """
    <html><body>
        <h1>Analysis</h1>
        <button>Pull Data</button>
        <button>Update Analysis</button>
        <p>Answer: 10</p>
    </body></html>
    """
    monkeypatch.setattr("app.psycopg.connect", lambda *a, **k: _mock_conn())
    monkeypatch.setattr("app.render_template", lambda t, **k: mock_html)

    response = client.get("/")
    assert response.status_code == 200
    assert b"Pull Data" in response.data
    assert b"Update Analysis" in response.data
    assert b"Analysis" in response.data
    assert b"Answer:" in response.data


def _mock_conn():
    """Return a mock connection with cursor that returns zeros."""
    from unittest.mock import MagicMock
    conn = MagicMock()
    cur = MagicMock()
    conn.cursor.return_value = cur
    cur.fetchone.return_value = [0, 0, 0, 0]
    return conn
