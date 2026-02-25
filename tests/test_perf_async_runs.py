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
        # Increased to 1.0s to ensure heartbeat has plenty of time to run multiple times
        time.sleep(1.0)
        return []

@pytest.mark.anyio
async def test_list_runs_non_blocking():
    """Verify that list_runs does not block the event loop."""

    # We use a heartbeat coroutine to detect blocking
    heartbeats = []

    async def heartbeat():
        while True:
            heartbeats.append(time.time())
            # Decreased interval to capture more samples
            await asyncio.sleep(0.05)

    # Start heartbeat
    heartbeat_task = asyncio.create_task(heartbeat())

    # Give the loop a moment to start the heartbeat task
    await asyncio.sleep(0.1)

    # Patch the state manager to use our blocking mock
    with patch("swarm.api.routes.runs_crud.get_state_manager", return_value=MockRunStateManager()):
        # Call the endpoint handler
        # Since we modified it to use asyncio.to_thread, the sleep(1.0) should happen in a thread
        # and not block our heartbeat loop.
        await runs_crud.list_runs(limit=10)

    # Stop heartbeat
    heartbeat_task.cancel()
    try:
        await heartbeat_task
    except asyncio.CancelledError:
        pass

    # Analyze heartbeats
    # We expect multiple heartbeats during the 1.0s sleep if non-blocking.
    # If blocked, we might see 0 or 1 heartbeat (the initial one).
    print(f"Heartbeats captured: {len(heartbeats)}")

    if len(heartbeats) < 5:
        # If fewer than 5 heartbeats in >1.0s (expected ~20), something is wrong/blocked
        # or the test environment is extremely slow.
        # Check gaps.
        max_gap = 0
        if len(heartbeats) >= 2:
            for i in range(1, len(heartbeats)):
                gap = heartbeats[i] - heartbeats[i-1]
                max_gap = max(max_gap, gap)
            print(f"Max heartbeat gap: {max_gap:.3f}s")

            # If gap is near 1.0s, it blocked.
            if max_gap > 0.8:
                 pytest.fail(f"Event loop was blocked! Max gap: {max_gap:.3f}s")

        # If we just didn't get enough heartbeats but no huge gap (maybe just slow start?),
        # fail with context.
        if len(heartbeats) < 2:
             pytest.fail(f"Heartbeat did not run enough times (count={len(heartbeats)}) to verify non-blocking behavior")

    # If we have enough heartbeats, check the gap just in case
    max_gap = 0
    for i in range(1, len(heartbeats)):
        gap = heartbeats[i] - heartbeats[i-1]
        max_gap = max(max_gap, gap)

    print(f"Max heartbeat gap: {max_gap:.3f}s")
    # 1.0s sleep. If blocked, gap ~1.0s. If not, gap ~0.05s.
    assert max_gap < 0.5, f"Event loop was blocked! Max gap: {max_gap:.3f}s (expected < 0.5s)"
