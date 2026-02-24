"""Tests for database insert behaviour and idempotency."""

import pytest


@pytest.mark.db
def test_simple_query_function(mock_db):
    """run_analysis_queries returns a dict with expected keys."""
    from app import create_app
    application = create_app(test_config={"TESTING": True})
    results, total = application.run_analysis_queries()
    assert isinstance(results, dict)
    assert "q1" in results
    assert total is not None


@pytest.mark.db
def test_query_none_handling(mock_db):
    """Handles None values from DB gracefully (returns 0)."""
    from app import create_app
    application = create_app(test_config={"TESTING": True})
    mock_db["cur"].fetchone.side_effect = [
        [0], [0], [None, None, None, None], [None],
        [0], [None], [0], [0], [0], [0],
    ]
    results, total = application.run_analysis_queries()
    assert results["q3"]["gpa"] == 0
    assert results["q4"] == 0
    assert results["q6"] == 0
