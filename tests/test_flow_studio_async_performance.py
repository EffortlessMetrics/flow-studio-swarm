
import asyncio
import time
import pytest
from unittest.mock import MagicMock, patch
from swarm.api.routes.runs_crud import list_runs, RunSummary, RunListResponse

async def heartbeat():
    """Check if event loop is blocked."""
    last_time = time.time()
    try:
        while True:
            await asyncio.sleep(0.05)
            current_time = time.time()
            diff = current_time - last_time
            if diff > 0.15:
                raise RuntimeError(f"Event loop blocked for {diff:.3f}s")
            last_time = current_time
    except asyncio.CancelledError:
        # Check one last time on cancellation
        current_time = time.time()
        diff = current_time - last_time
        if diff > 0.15:
             raise RuntimeError(f"Event loop blocked for {diff:.3f}s (on cancel)")
        raise

@pytest.mark.anyio
async def test_list_runs_non_blocking():
    # Mock slow list_runs
    def slow_list_runs(limit=20):
        time.sleep(0.5) # Simulate blocking I/O
        return []

    mock_manager = MagicMock()
    mock_manager.list_runs = slow_list_runs

    with patch("swarm.api.routes.runs_crud.get_state_manager", return_value=mock_manager):
        print("Starting heartbeat...")
        task = asyncio.create_task(heartbeat())

        # Give heartbeat a chance to start and record initial time
        await asyncio.sleep(0.1)

        print("Calling list_runs...")
        start = time.time()

        # This will block if not optimized
        await list_runs(limit=10)

        duration = time.time() - start
        print(f"list_runs took {duration:.3f}s")

        # Yield to let heartbeat check the time
        await asyncio.sleep(0.1)

        # Check if heartbeat failed
        if task.done():
            exc = task.exception()
            if exc:
                print(f"Heartbeat failed with: {exc}")
                raise exc

        # Clean up
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        except RuntimeError as e:
            if "Event loop blocked" in str(e):
                pytest.fail(str(e))
            raise
