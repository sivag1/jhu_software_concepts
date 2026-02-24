"""End-to-end integration tests for the Flask dashboard."""

import pytest
from unittest.mock import MagicMock


@pytest.mark.integration
def test_end_to_end_flow(client, mock_publisher, mock_db):
    """Full flow: scrape -> recompute -> render."""
    # 1. POST /scrape succeeds
    resp_scrape = client.post("/scrape")
    assert resp_scrape.status_code == 202
    assert resp_scrape.get_json()["status"] == "queued"

    # 2. POST /recompute succeeds
    resp_recompute = client.post("/recompute")
    assert resp_recompute.status_code == 202
    assert resp_recompute.get_json()["status"] == "queued"

    # 3. GET / renders page
    mock_db["cur"].fetchone.side_effect = [
        [100], [12.0], [3.5, 320.0, 160.0, 4.5], [3.8],
        [45.0], [3.9], [10], [5], [6], [1000],
    ]

    with pytest.MonkeyPatch.context() as m:
        mock_render = MagicMock(return_value="ok")
        m.setattr("app.render_template", mock_render)
        resp_page = client.get("/")

        args, kwargs = mock_render.call_args
        assert kwargs["total_records"] == 1000
        assert "results" in kwargs


@pytest.mark.integration
def test_scrape_then_recompute(client, mock_publisher, mock_db):
    """Verify both tasks can be queued in succession."""
    r1 = client.post("/scrape")
    r2 = client.post("/recompute")
    assert r1.status_code == 202
    assert r2.status_code == 202
    assert mock_publisher.call_count == 2
