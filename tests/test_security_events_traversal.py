
import pytest
from pathlib import Path
from swarm.api.routes.events import generate_run_events

@pytest.mark.anyio
async def test_generate_run_events_traversal_check():
    """
    Verify that generate_run_events validates run_id to prevent path traversal.
    """
    # Use a dummy path; we expect validation failure before file access
    runs_root = Path("/tmp/runs")

    # Try with a traversal payload
    traversal_id = "../etc/passwd"

    # We expect a ValueError due to validate_path_component
    # If the vulnerability exists, this might raise FileNotFoundError or nothing (empty generator)
    # instead of ValueError.
    try:
        # We need to iterate to execute the generator
        async for _ in generate_run_events(traversal_id, runs_root):
            pass
    except ValueError as e:
        # This is what we WANT (after fix)
        assert "run_id" in str(e) or "traversal" in str(e) or "invalid characters" in str(e)
        return

    # If we get here, no ValueError was raised
    pytest.fail("generate_run_events did not raise ValueError for traversal path '../etc/passwd'")

@pytest.mark.anyio
async def test_generate_run_events_valid_id():
    """
    Verify that a valid run_id doesn't raise ValueError (it might raise FileNotFoundError or just be empty).
    """
    runs_root = Path("/tmp/runs")
    valid_id = "valid-run-id"

    try:
        async for _ in generate_run_events(valid_id, runs_root):
            pass
    except ValueError:
        pytest.fail("generate_run_events raised ValueError for valid run_id")
    except Exception:
        # Other errors (like FileNotFoundError) are expected since /tmp/runs doesn't exist
        pass
