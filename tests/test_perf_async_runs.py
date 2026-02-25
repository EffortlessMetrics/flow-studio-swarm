
import asyncio
import time
import pytest
from httpx import AsyncClient, ASGITransport
from swarm.api.services.run_state import RunStateManager
from swarm.api.server import create_app

@pytest.mark.anyio
async def test_list_runs_non_blocking_behavior(monkeypatch):
    """
    Verifies that the list_runs endpoint does NOT block the event loop even if the underlying
    storage operation is slow.

    This test mocks RunStateManager.list_runs with a slow synchronous function (0.5s sleep).
    It runs a concurrent heartbeat task that should update every ~10ms.
    If the endpoint implementation correctly offloads the blocking call (e.g. via run_in_threadpool),
    the heartbeat gap should be small (<0.1s).
    If it blocks the loop, the gap will be large (>0.5s).
    """

    # Create the app (Spec Server)
    app = create_app()

    # Mock list_runs to be slow and synchronous
    def slow_sync_list_runs(self, limit=20):
        # Synchronous sleep blocks the thread
        time.sleep(0.5)
        return []

    monkeypatch.setattr(RunStateManager, "list_runs", slow_sync_list_runs)

    # Monitor blocking via heartbeat
    max_gap = 0.0
    running = True

    async def monitor_heartbeat():
        nonlocal max_gap
        last = time.time()
        while running:
            # Yield control to allow other tasks to run
            await asyncio.sleep(0.01)
            now = time.time()
            gap = now - last
            if gap > max_gap:
                max_gap = gap
            last = now

    monitor_task = asyncio.create_task(monitor_heartbeat())

    # Make request to /api/runs
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        await ac.get("/api/runs")

    # Stop monitoring
    running = False
    await monitor_task

    print(f"Max heartbeat gap: {max_gap:.4f}s")

    # Assert that blocking did NOT occur significantly
    # Ideally gap should be ~0.01s + overhead.
    # We allow up to 0.1s which is much less than the 0.5s sleep.
    assert max_gap < 0.1, f"Event loop was blocked! Max gap: {max_gap:.4f}s (expected < 0.1s)"
