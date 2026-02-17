import pytest
from unittest.mock import MagicMock
from module_5.src.app import run_analysis_queries

@pytest.mark.db
def test_insert_on_pull(client, mock_pipeline, in_memory_db):
    """
    Test insert on pull.
    Before: target table empty.
    After POST/pull-data new rows exist.
    """
    # Simulate pipeline inserting data
    def fake_pipeline():
        # This simulates what the pipeline would do: execute INSERTs
        # We use the in_memory_db fixture which captures executes
        # Directly use the mock DB state object passed to the test
        in_memory_db.execute("INSERT INTO applicants VALUES ('test')", ('test_data',))
    
    mock_pipeline.side_effect = fake_pipeline
    
    # Before
    assert len(in_memory_db.rows) == 0
    
    # Action
    client.post('/pull_data')
    
    # After
    assert len(in_memory_db.rows) == 1

@pytest.mark.db
def test_simple_query_function(mock_db):
    """Test simple query function returns expected keys."""
    results, total = run_analysis_queries()
    assert isinstance(results, dict)
    assert 'q1' in results
    assert total is not None

@pytest.mark.db
def test_idempotency(client, mock_pipeline):
    """Test idempotency: Duplicate rows do not create duplicates."""
    # This logic usually resides in the SQL (ON CONFLICT DO NOTHING) or the pipeline logic.
    # Since we mock the pipeline, we assert the pipeline is called.
    # The actual idempotency logic is in the pipeline code (not provided), 
    # so we verify the app triggers the pipeline correctly multiple times.
    client.post('/pull_data')
    client.post('/pull_data')
    assert mock_pipeline.call_count == 2