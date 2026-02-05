import pytest
import asyncio
from pathlib import Path
from swarm.api.routes.events import generate_run_events

@pytest.mark.anyio
async def test_generate_run_events_traversal(tmp_path):
    """Test that generate_run_events raises ValueError for path traversal."""
    runs_root = tmp_path / "runs"
    runs_root.mkdir()

    # These should raise ValueError immediately
    with pytest.raises(ValueError, match="run_id"):
        gen = generate_run_events("../etc", runs_root)
        await gen.__anext__()

    with pytest.raises(ValueError, match="run_id"):
        gen = generate_run_events("..", runs_root)
        await gen.__anext__()

    with pytest.raises(ValueError, match="run_id"):
        gen = generate_run_events("foo/bar", runs_root)
        await gen.__anext__()

@pytest.mark.anyio
async def test_generate_run_events_valid(tmp_path):
    """Test that valid run_id works (at least starts)."""
    runs_root = tmp_path / "runs"
    runs_root.mkdir()

    run_id = "valid-run"
    (runs_root / run_id).mkdir()

    gen = generate_run_events(run_id, runs_root)
    # First event is 'connected'
    event = await gen.__anext__()
    assert "connected" in event
