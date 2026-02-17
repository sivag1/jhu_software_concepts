import pytest
import sys
import os

# Add the parent directory to sys.path so 'module_5' can be imported as a package
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from unittest.mock import MagicMock, patch

from module_5.src.app import app

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

@pytest.fixture
def mock_db():
    """
    Mocks psycopg connect and cursor.
    Returns a dictionary containing the mock connection and cursor for assertions.
    """
    with patch('module_5.src.app.psycopg.connect') as mock_connect:
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        
        mock_connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cur
        
        # Default behavior for fetchone to avoid TypeErrors in app logic
        mock_cur.fetchone.return_value = [0, 0, 0, 0] 
        
        yield {'conn': mock_conn, 'cur': mock_cur}

@pytest.fixture
def mock_pipeline():
    """Mocks the run_full_pipeline function."""
    with patch('module_5.src.app.run_full_pipeline') as mock_pipe:
        yield mock_pipe

@pytest.fixture
def mock_render():
    """Mocks render_template to inspect context without parsing HTML."""
    with patch('module_5.src.app.render_template') as mock_render:
        # Return a dummy string so the route returns a valid response
        mock_render.return_value = "<html><body>Analysis Answer: 10</body></html>"
        yield mock_render

class MockDBState:
    """Helper to simulate a simple in-memory DB for integration tests."""
    def __init__(self):
        self.rows = []

    def execute(self, query, params=None):
        # Convert sql.Composed/SQL objects to string for pattern matching.
        # sql.Literal.as_string() requires a real connection, so catch TypeError.
        if hasattr(query, 'as_string'):
            try:
                query_str = query.as_string(None)
            except TypeError:
                query_str = str(query)
        else:
            query_str = str(query)
        if "INSERT" in query_str:
            self.rows.append(params)
        elif "SELECT COUNT(*)" in query_str:
            return
        
    def fetchone(self):
        return [len(self.rows), 0, 0, 0]

@pytest.fixture
def in_memory_db():
    """
    A more advanced mock that stores state for DB tests.
    """
    db_state = MockDBState()
    with patch('module_5.src.app.psycopg.connect') as mock_connect:
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cur
        
        mock_cur.execute.side_effect = db_state.execute
        mock_cur.fetchone.side_effect = db_state.fetchone
        
        yield db_state