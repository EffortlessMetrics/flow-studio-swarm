import asyncio
import json
import shutil
import tempfile
import os
from pathlib import Path
from datetime import datetime, timezone
import pytest
from swarm.api.services.run_state import RunStateManager

class TestRunStateManager:
    @pytest.fixture
    def runs_root(self):
        """Create a temporary directory for runs."""
        temp_dir = tempfile.mkdtemp()
        yield Path(temp_dir)
        shutil.rmtree(temp_dir)

    @pytest.fixture
    def state_manager(self, runs_root):
        """Create a RunStateManager instance."""
        return RunStateManager(runs_root)

    def create_dummy_run(self, runs_root, run_id, flow_id, status="pending", offset_minutes=0):
        """Helper to create a dummy run directory and state file."""
        run_dir = runs_root / run_id
        run_dir.mkdir(parents=True, exist_ok=True)

        # Create a timestamp with offset
        ts = datetime.now(timezone.utc).timestamp() - (offset_minutes * 60)
        created_at = datetime.fromtimestamp(ts, timezone.utc).isoformat()

        state = {
            "run_id": run_id,
            "flow_id": flow_id,
            "status": status,
            "created_at": created_at,
            "updated_at": created_at,
        }

        (run_dir / "run_state.json").write_text(json.dumps(state))

        # Touch the directory to update mtime for sorting
        os.utime(run_dir, (ts, ts))

        return state

    def test_list_runs_async_matches_sync(self, state_manager, runs_root):
        """Verify that list_runs_async returns the same data as list_runs."""

        async def run_test():
            # Create a few runs
            self.create_dummy_run(runs_root, "run-1", "flow-a", "succeeded", 10)
            self.create_dummy_run(runs_root, "run-2", "flow-b", "failed", 5)
            self.create_dummy_run(runs_root, "run-3", "flow-c", "pending", 0) # Newest

            # Sync call
            sync_runs = state_manager.list_runs(limit=10)

            # Async call
            async_runs = await state_manager.list_runs_async(limit=10)

            # Verify results
            assert len(sync_runs) == 3
            assert len(async_runs) == 3
            assert sync_runs == async_runs

            # Verify sorting (newest first)
            assert async_runs[0]["run_id"] == "run-3"
            assert async_runs[1]["run_id"] == "run-2"
            assert async_runs[2]["run_id"] == "run-1"

        asyncio.run(run_test())

    def test_list_runs_async_limit(self, state_manager, runs_root):
        """Verify limit works in async version."""

        async def run_test():
            for i in range(5):
                self.create_dummy_run(runs_root, f"run-{i}", "flow-x", offset_minutes=i)

            async_runs = await state_manager.list_runs_async(limit=2)
            assert len(async_runs) == 2

        asyncio.run(run_test())
