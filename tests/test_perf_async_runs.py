"""
Tests for asynchronous performance of run listing.
"""
import asyncio
import time
from unittest.mock import MagicMock, patch

import pytest
from swarm.api.routes import runs_crud


class MockRunStateManager:
    def list_runs(self, limit=20):
        # Simulate blocking I/O
        time.sleep(0.5)
        return []

@pytest.mark.anyio
async def test_list_runs_non_blocking():
    """Verify that list_runs does not block the event loop."""

    # We use a heartbeat coroutine to detect blocking
    heartbeats = []

    async def heartbeat():
        while True:
            heartbeats.append(time.time())
            await asyncio.sleep(0.05)

    # Start heartbeat
    heartbeat_task = asyncio.create_task(heartbeat())

    # Patch the state manager to use our blocking mock
    with patch("swarm.api.routes.runs_crud.get_state_manager", return_value=MockRunStateManager()):
        # Call the endpoint handler
        # Since we modified it to use asyncio.to_thread, the sleep(0.5) should happen in a thread
        # and not block our heartbeat loop.
        await runs_crud.list_runs(limit=10)

    # Stop heartbeat
    heartbeat_task.cancel()
    try:
        await heartbeat_task
    except asyncio.CancelledError:
        pass

    # Analyze heartbeats
    # If the loop was blocked for 0.5s, we would see a gap > 0.5s in timestamps
    max_gap = 0
    if len(heartbeats) < 2:
        pytest.fail("Heartbeat did not run enough times")

    for i in range(1, len(heartbeats)):
        gap = heartbeats[i] - heartbeats[i-1]
        max_gap = max(max_gap, gap)

    # 0.5s sleep + some overhead. If it blocked, gap would be ~0.5s.
    # If it didn't block, gap should be close to 0.05s (sleep time) + overhead.
    # Let's be generous and say < 0.2s means it didn't block for the full 0.5s.

    print(f"Max heartbeat gap: {max_gap:.3f}s")
    assert max_gap < 0.3, f"Event loop was blocked! Max gap: {max_gap:.3f}s (expected < 0.3s)"
