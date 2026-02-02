import asyncio
import time
import pytest
from pathlib import Path
from swarm.api.services.run_state import RunStateManager

def test_list_runs_async_non_blocking(tmp_path):
    async def run_test():
        manager = RunStateManager(tmp_path)

        # We need to monkeypatch list_runs to be slow
        original_list_runs = manager.list_runs

        def slow_list_runs(limit=20):
            time.sleep(0.5) # Blocking sleep
            return original_list_runs(limit)

        manager.list_runs = slow_list_runs

        # Define a background task that updates a counter
        counter = 0
        async def background_task():
            nonlocal counter
            while True:
                counter += 1
                await asyncio.sleep(0.1)

        task = asyncio.create_task(background_task())

        # Run list_runs_async
        if not hasattr(manager, 'list_runs_async'):
             task.cancel()
             return "NOT_IMPLEMENTED"

        start_time = time.time()
        await manager.list_runs_async()
        duration = time.time() - start_time

        # Cancel background task
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

        return duration, counter

    result = asyncio.run(run_test())

    if result == "NOT_IMPLEMENTED":
        # For TDD: we expect this initially, but the test should assert it exists eventually.
        # So failure is correct here for now.
        pytest.fail("list_runs_async not implemented")

    duration, counter = result

    # Verification
    # If it was blocking, the background task wouldn't have run much.
    # We sleep 0.5s. Background task increments every 0.1s.
    # It should have incremented at least 4-5 times.
    # Allowing for some overhead/scheduling jitter, > 2 is safe.
    assert duration >= 0.5
    assert counter >= 3, f"Background task was blocked! Counter: {counter}"
