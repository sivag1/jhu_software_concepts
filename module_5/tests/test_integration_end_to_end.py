import pytest
from unittest.mock import MagicMock

@pytest.mark.integration
def test_end_to_end_flow(client, mock_pipeline, in_memory_db):
    """
    End-to-end (pull -> update -> Render)
    1. Inject a fake scraper that returns multiple records (simulated via mock_pipeline side effect).
    2. POST /pull-data succeeds and rows are in DB.
    3. POST /update-analysis succeeds.
    4. GET /analysis shows updated analysis.
    """
    
    # 1. Inject fake scraper behavior
    def fake_scraper_pipeline():
        # Simulate inserting 2 records into the in-memory mock DB
        in_memory_db.execute("INSERT INTO applicants ...", ('rec1',))
        in_memory_db.execute("INSERT INTO applicants ...", ('rec2',))

    mock_pipeline.side_effect = fake_scraper_pipeline

    # 2. POST /pull-data
    resp_pull = client.post('/pull_data')
    assert resp_pull.status_code == 302
    assert len(in_memory_db.rows) == 2

    # 3. POST /update-analysis
    resp_update = client.post('/update_analysis')
    assert resp_update.status_code == 200

    # 4. GET /analysis (root)
    # We need to ensure the DB returns the count based on our inserted rows
    # The in_memory_db fixture handles fetchone by returning [len(rows)]
    # So run_analysis_queries will see count = 2
    
    # We need to patch render_template to verify the context passed to it
    with pytest.MonkeyPatch.context() as m:
        mock_render = MagicMock(return_value="ok")
        m.setattr('module_5.src.app.render_template', mock_render)
        client.get('/')
        
        # Verify total_records passed to template matches our DB state
        args, kwargs = mock_render.call_args
        assert kwargs['total_records'] == 2