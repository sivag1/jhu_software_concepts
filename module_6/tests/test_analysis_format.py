"""Tests for analysis query formatting and rounding."""

import pytest


@pytest.fixture
def mock_query_results():
    """Standard list of mock DB results for analysis queries."""
    return [
        [100],                          # q1
        [12.35],                        # q2
        [3.555, 320.1, 160.1, 4.5],    # q3
        [3.888],                        # q4
        [45.68],                        # q5
        [3.999],                        # q6
        [10],                           # q7
        [5],                            # q8
        [6],                            # q9
        [1000],                         # total
    ]


@pytest.mark.analysis
def test_labels_and_rounding(mock_db, mock_query_results):
    """Verify that metrics are rounded to two decimal places."""
    from app import create_app
    application = create_app(test_config={"TESTING": True})
    mock_db["cur"].fetchone.side_effect = mock_query_results

    results, total = application.run_analysis_queries()

    assert results["q3"]["gpa"] == 3.56
    assert results["q4"] == 3.89
    assert results["q6"] == 4.00
    assert "q1" in results
    assert "q2" in results


@pytest.mark.analysis
def test_page_formatting_integration(client, mock_db, monkeypatch):
    """Verify page includes 'Answer' labels and formatted percentages."""
    mock_db["cur"].fetchone.side_effect = [
        [100], [12.35], [3.555, 320.1, 160.1, 4.5], [3.888],
        [45.68], [3.999], [10], [5], [6], [1000],
    ]

    def mock_render(template, **kwargs):
        results = kwargs.get("results", {})
        return f"<html><body>Answer: {results.get('q2')}%</body></html>"

    monkeypatch.setattr("app.render_template", mock_render)

    response = client.get("/")
    assert response.status_code == 200
    assert b"Answer:" in response.data
    assert b"12.35%" in response.data
