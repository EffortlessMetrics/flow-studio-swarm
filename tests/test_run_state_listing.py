"""
Tests for RunStateManager listing and durable writes.

Covers list_runs (ordering, limit, malformed-state tolerance) and
_save_state atomic write behaviour. See tests/run_state_support.py for
shared setup.
"""

import asyncio
import json
import os

import pytest
from run_state_support import manager, read_state_file  # noqa: F401


class TestAtomicWrites:
    """Tests for durable, atomic state persistence."""

    def test_save_leaves_no_temp_file(self, manager):
        """The tmp file is renamed away, not left behind."""
        asyncio.run(manager.create_run("3-build", run_id="my-run"))

        run_dir = manager.runs_root / "my-run"
        assert (run_dir / "run_state.json").exists()
        assert list(run_dir.glob("*.tmp")) == []

    def test_save_writes_valid_json(self, manager):
        """Persisted state round-trips through JSON."""
        asyncio.run(manager.create_run("3-build", run_id="my-run"))
        asyncio.run(manager.update_run("my-run", {"context": {"nested": ["a", 1]}}))

        assert read_state_file(manager.runs_root, "my-run")["context"] == {"nested": ["a", 1]}

    def test_save_creates_parent_directories(self, manager):
        """Saving into a not-yet-existing runs_root works."""
        assert not manager.runs_root.exists()

        asyncio.run(manager.create_run("3-build", run_id="my-run"))

        assert (manager.runs_root / "my-run" / "run_state.json").exists()

    def test_cache_matches_disk_after_update(self, manager):
        """The cache is not allowed to drift from what was persisted."""
        asyncio.run(manager.create_run("3-build", run_id="my-run"))
        asyncio.run(manager.update_run("my-run", {"status": "running"}))

        assert manager._cache["my-run"] == read_state_file(manager.runs_root, "my-run")


class TestListRuns:
    """Tests for run listing."""

    def test_list_runs_is_awaitable(self, manager):
        """list_runs is async, matching the rest of the public surface.

        Regression guard for #223: a sync list_runs blocks the event loop when
        called from an async endpoint.
        """
        assert asyncio.iscoroutinefunction(manager.list_runs)

    def test_list_runs_empty_when_root_missing(self, manager):
        """No runs_root yet means an empty list, not an error."""
        assert asyncio.run(manager.list_runs()) == []

    def test_list_runs_returns_created_runs(self, manager):
        """Created runs show up in the listing."""
        asyncio.run(manager.create_run("3-build", run_id="run-a"))
        asyncio.run(manager.create_run("3-build", run_id="run-b"))

        listed = asyncio.run(manager.list_runs())

        assert {entry["run_id"] for entry in listed} == {"run-a", "run-b"}

    def test_list_runs_projects_summary_fields(self, manager):
        """Listing returns the summary projection, not the full state."""
        asyncio.run(manager.create_run("3-build", run_id="run-a"))

        entry = asyncio.run(manager.list_runs())[0]

        assert set(entry) == {"run_id", "flow_key", "status", "timestamp"}
        assert entry["flow_key"] == "build"
        assert entry["status"] == "pending"

    def test_list_runs_honours_limit(self, manager):
        """The limit caps how many entries are returned."""
        for index in range(5):
            asyncio.run(manager.create_run("3-build", run_id=f"run-{index}"))

        assert len(asyncio.run(manager.list_runs(limit=2))) == 2

    def test_list_runs_orders_newest_first(self, manager):
        """Entries are ordered by directory mtime, newest first."""
        for index in range(3):
            asyncio.run(manager.create_run("3-build", run_id=f"run-{index}"))

        # Make the ordering explicit rather than relying on creation timing.
        for index, mtime in enumerate([100.0, 300.0, 200.0]):
            os.utime(manager.runs_root / f"run-{index}", (mtime, mtime))

        listed = asyncio.run(manager.list_runs())

        assert [entry["run_id"] for entry in listed] == ["run-1", "run-2", "run-0"]

    def test_list_runs_skips_directories_without_state(self, manager):
        """Directories that are not runs are ignored."""
        asyncio.run(manager.create_run("3-build", run_id="run-a"))
        (manager.runs_root / "not-a-run").mkdir()

        listed = asyncio.run(manager.list_runs())

        assert [entry["run_id"] for entry in listed] == ["run-a"]

    def test_list_runs_tolerates_malformed_state(self, manager):
        """A corrupt run_state.json is skipped, not fatal."""
        asyncio.run(manager.create_run("3-build", run_id="run-a"))

        broken = manager.runs_root / "broken"
        broken.mkdir()
        (broken / "run_state.json").write_text("{not json", encoding="utf-8")

        listed = asyncio.run(manager.list_runs())

        assert [entry["run_id"] for entry in listed] == ["run-a"]

    def test_list_runs_falls_back_to_directory_name(self, manager):
        """A state file missing run_id falls back to the directory name."""
        run_dir = manager.runs_root / "orphan"
        run_dir.mkdir(parents=True)
        (run_dir / "run_state.json").write_text(json.dumps({"status": "done"}), encoding="utf-8")

        entry = asyncio.run(manager.list_runs())[0]

        assert entry["run_id"] == "orphan"
        assert entry["flow_key"] is None
