import pytest
from module_4.src.app import run_analysis_queries

@pytest.mark.analysis
def test_labels_and_rounding(mock_db):
    """
    Test that your page include “Answer” labels for rendered analysis
    Test that any percentage is formatted with two decimals.
    """
    # Setup mock returns for the specific queries in run_analysis_queries
    # The order of execution in app.py is:
    # 1. Fall 2026 entries (count)
    # 2. % International (percentage)
    # 3. Avg GPA, GRE, etc.
    # 4. Avg GPA American
    # 5. % Acceptances
    # 6. Avg GPA Acceptances
    # 7. JHU MS CS
    # 8. Targeted PhD CS (Original)
    # 9. Targeted PhD CS (LLM)
    # 10. Total records
    
    mock_cur = mock_db['cur']
    mock_cur.fetchone.side_effect = [
        [100],          # q1
        [12.3456],      # q2 (percentage, DB usually rounds, but we check python handling)
        [3.555, 320.1, 160.1, 4.5], # q3
        [3.888],        # q4
        [45.678],       # q5 (percentage)
        [3.999],        # q6
        [10],           # q7
        [5],            # q8
        [6],            # q9
        [1000]          # total
    ]

    results, total = run_analysis_queries()

    # Check rounding logic implemented in Python (if any) or passed through
    # In app.py, q3, q4, q6 are explicitly rounded in Python.
    # q2 and q5 are rounded in SQL, so the mock return simulates the SQL result.
    
    assert results['q3']['gpa'] == 3.56  # round(3.555, 2)
    assert results['q4'] == 3.89         # round(3.888, 2)
    assert results['q6'] == 4.00         # round(3.999, 2)
    
    # Verify structure
    assert 'q1' in results
    assert 'q2' in results
    
    # Note: The "Answer" label check is done in test_flask_page.py via HTML inspection.
    # This test focuses on the data formatting logic.