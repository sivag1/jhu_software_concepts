import pytest
import subprocess
from unittest.mock import patch, MagicMock
from module_4.src.run_pipeline import run_full_pipeline, run_step

@pytest.mark.pipeline
def test_run_step_success():
    """Test that run_step calls subprocess.run correctly."""
    with patch("subprocess.run") as mock_run, \
         patch("os.path.exists", return_value=True):
        run_step("Test Step", "dummy_script.py")
        mock_run.assert_called_once()

@pytest.mark.pipeline
def test_run_step_file_not_found():
    """Test that run_step raises FileNotFoundError if script is missing."""
    with patch("os.path.exists", return_value=False):
        with pytest.raises(FileNotFoundError):
            run_step("Test Step", "missing_script.py")

@pytest.mark.pipeline
def test_run_full_pipeline():
    """Test that run_full_pipeline executes the sequence of steps."""
    # Patch run_step to verify the sequence without running subprocesses
    with patch("module_4.src.run_pipeline.run_step") as mock_step:
        run_full_pipeline()
        # Verify it was called 4 times (Scrape, Clean, LLM, Load)
        assert mock_step.call_count == 4

@pytest.mark.pipeline
def test_run_step_failure():
    """Test that run_step raises RuntimeError on subprocess failure."""
    with patch("subprocess.run") as mock_run, \
         patch("os.path.exists", return_value=True):
        # Simulate a non-zero exit code
        mock_run.side_effect = subprocess.CalledProcessError(1, ["cmd"])
        with pytest.raises(RuntimeError):
            run_step("Test Step", "dummy_path.py")