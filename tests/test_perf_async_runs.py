import asyncio
import time
import pytest
from unittest.mock import MagicMock, patch
from swarm.api.routes.runs_crud import list_runs
from swarm.api.services.run_state import RunStateManager

@pytest.mark.anyio
async def test_list_runs_blocking_behavior():
    """
    Test if list_runs blocks the event loop.

    This test mocks RunStateManager.list_runs to sleep synchronously.
    If the endpoint calls it synchronously, the event loop will be blocked,
    and a concurrent heartbeat task will not get CPU time.
    """
    # Mock RunStateManager to be slow
    slow_duration = 0.5

    def slow_list_runs(*args, **kwargs):
        time.sleep(slow_duration)
        return []

    # Mock get_state_manager to return our mock
    mock_manager = MagicMock(spec=RunStateManager)
    mock_manager.list_runs = slow_list_runs

    with patch("swarm.api.routes.runs_crud.get_state_manager", return_value=mock_manager):

        counter = 0
        stop_event = asyncio.Event()

        async def heartbeat():
            nonlocal counter
            while not stop_event.is_set():
                counter += 1
                # Small sleep to yield control
                await asyncio.sleep(0.05)

        # Start heartbeat
        heartbeat_task = asyncio.create_task(heartbeat())

        # Run list_runs
        # We start it and await it. If it blocks, heartbeat won't increment much.
        start_time = time.time()
        await list_runs(limit=10)
        duration = time.time() - start_time

        # Stop heartbeat
        stop_event.set()
        await heartbeat_task

        print(f"Duration: {duration:.2f}s, Counter: {counter}")

        # If blocking: counter should be very small (e.g. 0 or 1) because time.sleep blocks everything
        # If non-blocking: counter should be around slow_duration / 0.05 (e.g. 10)

        # We expect the test to FAIL if the implementation is blocking.
        # So we assert that it is NOT blocking.
        # A counter of 2 or less strongly suggests blocking for 0.5s duration.
        assert counter > 2, f"Event loop was blocked! Counter: {counter}. Expected > 2 for {slow_duration}s sleep."
