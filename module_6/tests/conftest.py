"""Pytest fixtures for module_6 web app tests."""

import sys
import os

# Add the web directory to sys.path so we can import app and publisher
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "web")))

from unittest.mock import MagicMock, patch

import pytest

from app import create_app


@pytest.fixture
def client():
    """Flask test client with mocked DB and publisher."""
    application = create_app(test_config={"TESTING": True})
    application.config["TESTING"] = True
    with application.test_client() as c:
        yield c


@pytest.fixture
def mock_db():
    """Mock psycopg.connect and return mock conn/cur for assertions."""
    with patch("app.psycopg.connect") as mock_connect:
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cur
        mock_cur.fetchone.return_value = [0, 0, 0, 0]
        yield {"conn": mock_conn, "cur": mock_cur}


@pytest.fixture
def mock_publisher():
    """Mock the publish_task function used by Flask routes."""
    with patch("app.publish_task") as mock_pub:
        yield mock_pub


class MockDBState:
    """Simple in-memory DB simulator for integration tests."""

    def __init__(self):
        self.rows = []

    def execute(self, query, params=None):
        if hasattr(query, "as_string"):
            try:
                query_str = query.as_string(None)
            except TypeError:
                query_str = str(query)
        else:
            query_str = str(query)
        if "INSERT" in query_str:
            self.rows.append(params)

    def fetchone(self):
        return [len(self.rows), 0, 0, 0]


@pytest.fixture
def in_memory_db():
    """Stateful mock DB for insert/count integration tests."""
    db_state = MockDBState()
    with patch("app.psycopg.connect") as mock_connect:
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cur
        mock_cur.execute.side_effect = db_state.execute
        mock_cur.fetchone.side_effect = db_state.fetchone
        yield db_state
