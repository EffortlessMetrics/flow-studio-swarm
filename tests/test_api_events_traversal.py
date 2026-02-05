
import pytest
import os
import json
import asyncio
from pathlib import Path
from swarm.api.routes.events import generate_run_events
from unittest.mock import MagicMock

@pytest.mark.anyio
async def test_generate_run_events_traversal_blocked(tmp_path):
    # Setup runs_root
    runs_root = tmp_path / "swarm" / "runs"
    runs_root.mkdir(parents=True, exist_ok=True)

    # Create a secret file outside runs_root
    secret_dir = tmp_path / "secret"
    secret_dir.mkdir()

    (secret_dir / "run_state.json").write_text(json.dumps({"status": "running"}))
    (secret_dir / "events.jsonl").write_text(json.dumps({"event": "secret_event", "data": "TOP_SECRET"}) + "\n")

    # Construct traversal run_id: ../../secret
    traversal_id = "../../secret"

    # Verify that calling generate_run_events raises ValueError due to path validation
    # It might fail due to "traversal sequence" check or "invalid characters" check depending on exact input
    with pytest.raises(ValueError, match="(traversal sequence|invalid characters)"):
        async for _ in generate_run_events(traversal_id, runs_root, poll_interval=0.1):
            pass

@pytest.mark.anyio
async def test_generate_run_events_valid_id(tmp_path):
    # Test with a valid ID to ensure we didn't break normal functionality
    runs_root = tmp_path / "swarm" / "runs"
    runs_root.mkdir(parents=True, exist_ok=True)

    run_id = "valid-run-123"
    run_dir = runs_root / run_id
    run_dir.mkdir()

    (run_dir / "run_state.json").write_text(json.dumps({"status": "running"}))
    (run_dir / "events.jsonl").write_text(json.dumps({"event": "test", "data": "test_data"}) + "\n")

    events = []
    try:
        async with asyncio.timeout(1):
            async for event_str in generate_run_events(run_id, runs_root, poll_interval=0.1):
                events.append(event_str)
                if "test_data" in event_str:
                    break
    except TimeoutError:
        pass

    combined = "".join(events)
    assert "test_data" in combined
