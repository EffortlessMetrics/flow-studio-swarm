"""
Tests for RunStateManager storage, listing, and locking.

Covers the durability and concurrency contracts of
swarm/api/services/run_state.py:

- _save_state: atomic tmp -> rename writes
- list_runs: async offload, ordering, limits, malformed-state tolerance
- per-run locks: serialized read-modify-write

CRUD behavior lives in test_run_state_crud.py.
"""

import asyncio
import inspect
import json
import os
import threading
from unittest.mock import patch

from run_state_helpers import make_manager, write_run
from swarm.api.services import run_state as run_state_module
from swarm.api.services.run_state import RunStateManager


class TestSaveState:
    """Tests for the atomic write behavior of _save_state()."""

    def test_write_goes_through_tmp_file_rename(self, tmp_path):
        """State reaches its final path via os.replace from a tmp file.

        A partially written run_state.json must never be observable, so the
        write must land on a temp path and be renamed - not written in place.
        """
        manager = make_manager(tmp_path)
        renames = []
        real_replace = os.replace

        def recording_replace(src, dst):
            renames.append((str(src), str(dst)))
            return real_replace(src, dst)

        with patch.object(run_state_module.os, "replace", recording_replace):
            asyncio.run(manager.create_run(flow_id="3-build", run_id="r1"))

        state_path = manager.runs_root / "r1" / "run_state.json"
        assert renames, "_save_state should rename a tmp file into place"
        src, dst = renames[-1]
        assert dst == str(state_path)
        assert src != dst and src.endswith(".tmp")

        assert state_path.exists()
        assert list((manager.runs_root / "r1").glob("*.tmp")) == []

    def test_save_state_refreshes_cache(self, tmp_path):
        """_save_state updates the in-memory cache alongside disk."""
        manager = make_manager(tmp_path)
        asyncio.run(manager.create_run(flow_id="3-build", run_id="r1"))

        asyncio.run(manager._save_state("r1", {"run_id": "r1", "status": "done"}))

        assert manager._cache["r1"]["status"] == "done"
        on_disk = json.loads(
            (manager.runs_root / "r1" / "run_state.json").read_text(encoding="utf-8")
        )
        assert on_disk["status"] == "done"


class TestListRuns:
    """Tests for list_runs()."""

    def test_is_async(self, tmp_path):
        """list_runs is awaitable, matching the rest of the public surface."""
        manager = make_manager(tmp_path)
        assert inspect.iscoroutinefunction(manager.list_runs)

    def test_disk_walk_runs_off_the_event_loop(self, tmp_path):
        """The blocking scan runs in a worker thread, not the loop thread.

        Regression guard for #223. `async def` alone is not enough: calling
        the blocking implementation directly inside the coroutine would still
        stall the FastAPI event loop on disk I/O. Assert the work actually
        lands on a different thread.
        """
        manager = make_manager(tmp_path)
        write_run(manager.runs_root, "r1")

        worker_threads = []
        original = manager._list_runs_sync

        def recording_sync(limit=20):
            worker_threads.append(threading.get_ident())
            return original(limit)

        manager._list_runs_sync = recording_sync

        async def call():
            loop_thread = threading.get_ident()
            runs = await manager.list_runs()
            return loop_thread, runs

        loop_thread, runs = asyncio.run(call())

        assert [r["run_id"] for r in runs] == ["r1"]
        assert worker_threads, "the blocking scan should have been invoked"
        assert worker_threads[0] != loop_thread, (
            "list_runs ran its blocking disk walk on the event loop thread; "
            "it must be offloaded (asyncio.to_thread)"
        )

    def test_empty_when_root_missing(self, tmp_path):
        """A missing runs root yields an empty list rather than raising."""
        manager = RunStateManager(runs_root=tmp_path / "absent")

        assert asyncio.run(manager.list_runs()) == []

    def test_returns_summaries(self, tmp_path):
        """Each entry is a summary, not the full state."""
        manager = make_manager(tmp_path)
        write_run(manager.runs_root, "r1", flow_id="3-build", status="running")

        runs = asyncio.run(manager.list_runs())

        assert len(runs) == 1
        assert runs[0] == {
            "run_id": "r1",
            "flow_key": "build",
            "status": "running",
            "timestamp": "2026-01-01T00:00:00+00:00",
        }

    def test_respects_limit(self, tmp_path):
        """No more than `limit` runs are returned."""
        manager = make_manager(tmp_path)
        for i in range(5):
            write_run(manager.runs_root, f"r{i}")

        assert len(asyncio.run(manager.list_runs(limit=2))) == 2

    def test_orders_newest_first(self, tmp_path):
        """Runs are ordered by directory mtime, newest first."""
        manager = make_manager(tmp_path)
        for i in range(3):
            write_run(manager.runs_root, f"r{i}")

        # Stamp explicit, increasing mtimes so ordering is deterministic.
        for i in range(3):
            run_dir = manager.runs_root / f"r{i}"
            os.utime(run_dir, (1_000_000 + i * 10, 1_000_000 + i * 10))

        runs = asyncio.run(manager.list_runs())

        assert [r["run_id"] for r in runs] == ["r2", "r1", "r0"]

    def test_skips_directories_without_state(self, tmp_path):
        """Directories lacking run_state.json are not runs."""
        manager = make_manager(tmp_path)
        write_run(manager.runs_root, "real")
        (manager.runs_root / "not-a-run").mkdir()

        runs = asyncio.run(manager.list_runs())

        assert [r["run_id"] for r in runs] == ["real"]

    def test_tolerates_malformed_state(self, tmp_path):
        """A corrupt run_state.json is skipped, not fatal."""
        manager = make_manager(tmp_path)
        write_run(manager.runs_root, "good")
        bad_dir = manager.runs_root / "bad"
        bad_dir.mkdir()
        (bad_dir / "run_state.json").write_text("{not json", encoding="utf-8")

        runs = asyncio.run(manager.list_runs())

        assert [r["run_id"] for r in runs] == ["good"]


class TestLocking:
    """Tests for per-run lock behavior."""

    def test_lock_is_stable_per_run_and_distinct_across_runs(self, tmp_path):
        """Each run gets its own lock, reused across calls."""
        manager = make_manager(tmp_path)

        lock_a = manager._get_lock("a")
        assert manager._get_lock("a") is lock_a
        assert manager._get_lock("b") is not lock_a

    def test_update_critical_section_is_serialized(self, tmp_path):
        """Concurrent update_run calls never overlap their read-modify-write.

        The instrumented _save_state yields control mid-section. Without the
        per-run lock, a second update_run enters while the first is suspended
        and the recorded depth exceeds 1.
        """
        manager = make_manager(tmp_path)
        asyncio.run(manager.create_run(flow_id="3-build", run_id="r1"))

        original_save = manager._save_state
        depth = 0
        observed_depths = []

        async def instrumented_save(run_id, state):
            nonlocal depth
            depth += 1
            observed_depths.append(depth)
            # Yield: an unserialized implementation interleaves here.
            await asyncio.sleep(0)
            await original_save(run_id, state)
            depth -= 1

        manager._save_state = instrumented_save

        async def run_updates():
            await asyncio.gather(*(manager.update_run("r1", {f"key{i}": i}) for i in range(5)))

        asyncio.run(run_updates())

        assert observed_depths, "instrumented save should have been exercised"
        assert max(observed_depths) == 1, (
            f"update_run critical sections overlapped (max depth "
            f"{max(observed_depths)}); the per-run lock is not serializing writes"
        )

    def test_concurrent_updates_all_land(self, tmp_path):
        """Every concurrent update is reflected in the final persisted state."""
        manager = make_manager(tmp_path)
        asyncio.run(manager.create_run(flow_id="3-build", run_id="r1"))

        async def run_updates():
            await asyncio.gather(*(manager.update_run("r1", {f"key{i}": i}) for i in range(10)))
            return await manager.get_run("r1")

        state, _ = asyncio.run(run_updates())

        for i in range(10):
            assert state[f"key{i}"] == i
