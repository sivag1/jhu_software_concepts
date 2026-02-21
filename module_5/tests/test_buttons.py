import pytest
from module_5.src.app import pipeline_lock

@pytest.mark.buttons
def test_post_pull_data(client, mock_pipeline, mock_db):
    """Test POST /pull-data returns 200 and triggers loader."""
    response = client.post('/pull_data')
    assert response.status_code == 302
    assert response.headers['Location'] == '/'
    mock_pipeline.assert_called_once()

@pytest.mark.buttons
def test_post_update_analysis(client):
    """Test POST /update-analysis returns 200 when not busy."""
    response = client.post('/update_analysis')
    assert response.status_code == 200
    assert response.data == b"OK"

@pytest.mark.buttons
def test_busy_gating_update(client):
    """When a pull is 'in progress', POST /update-analysis returns 409."""
    # Manually acquire the lock to simulate busy state
    pipeline_lock.acquire()
    try:
        response = client.post('/update_analysis')
        assert response.status_code == 409
        assert b"Busy" in response.data
    finally:
        pipeline_lock.release()

@pytest.mark.buttons
def test_busy_gating_pull(client, mock_pipeline):
    """When busy, POST /pull-data returns 409."""
    pipeline_lock.acquire()
    try:
        response = client.post('/pull_data')
        assert response.status_code == 409
        assert b"Busy" in response.data
        # Ensure pipeline was NOT called again
        mock_pipeline.assert_not_called()
    finally:
        pipeline_lock.release()

@pytest.mark.buttons
def test_pull_data_exception(client, mock_pipeline, mock_db):
    """Test that exceptions in pipeline are handled gracefully."""
    mock_pipeline.side_effect = Exception("Scraper failed")
    response = client.post('/pull_data')
    assert response.status_code == 500