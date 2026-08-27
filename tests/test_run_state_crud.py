"""
Tests for RunStateManager CRUD operations (swarm/api/services/run_state.py).

Covers run creation, retrieval, and update - including the ETag precondition
that guards against lost updates. Storage, listing, and locking behavior live
in test_run_state_storage.py.

The manager exposes an async API and the repo has no asyncio pytest plugin
configured, so coroutines are driven with asyncio.run() (matching
tests/test_run_tailer.py).
"""

import asyncio
import json

import pytest
from run_state_helpers import make_manager, write_run


class TestCreateRun:
    """Tests for create_run()."""

    def test_creates_state_file_and_defaults(self, tmp_path):
        """create_run persists state and fills in default fields."""
        manager = make_manager(tmp_path)

        state = asyncio.run(manager.create_run(flow_id="3-build"))

        assert state["flow_id"] == "3-build"
        assert state["status"] == "pending"
        assert state["completed_steps"] == []
        assert state["context"] == {}
        assert state["current_step"] is None
        assert state["created_at"] == state["updated_at"]

        state_file = manager.runs_root / state["run_id"] / "run_state.json"
        assert state_file.exists()
        assert json.loads(state_file.read_text(encoding="utf-8")) == state

    def test_generated_run_id_is_prefixed_by_flow(self, tmp_path):
        """A generated run_id starts with the flow_id and is unique per call."""
        manager = make_manager(tmp_path)

        first = asyncio.run(manager.create_run(flow_id="signal"))
        second = asyncio.run(manager.create_run(flow_id="signal"))

        assert first["run_id"].startswith("signal-")
        assert second["run_id"].startswith("signal-")
        assert first["run_id"] != second["run_id"]

    def test_honors_optional_parameters(self, tmp_path):
        """Explicit run_id, context, and start_step are preserved."""
        manager = make_manager(tmp_path)

        state = asyncio.run(
            manager.create_run(
                flow_id="3-build",
                run_id="my-run",
                context={"issue": 42},
                start_step="2",
            )
        )

        assert state["run_id"] == "my-run"
        assert state["context"] == {"issue": 42}
        assert state["current_step"] == "2"

    @pytest.mark.parametrize("bad_flow_id", ["../escape", "a/b", ""])
    def test_rejects_unsafe_flow_id(self, tmp_path, bad_flow_id):
        """Path components are validated before touching the filesystem."""
        manager = make_manager(tmp_path)

        with pytest.raises(Exception):
            asyncio.run(manager.create_run(flow_id=bad_flow_id))

    def test_rejects_unsafe_run_id(self, tmp_path):
        """An explicit run_id is validated too."""
        manager = make_manager(tmp_path)

        with pytest.raises(Exception):
            asyncio.run(manager.create_run(flow_id="3-build", run_id="../escape"))


class TestGetRun:
    """Tests for get_run()."""

    def test_returns_state_and_stable_etag(self, tmp_path):
        """get_run returns the state plus an ETag that is stable for that state."""
        manager = make_manager(tmp_path)
        created = asyncio.run(manager.create_run(flow_id="3-build", run_id="r1"))

        state, etag = asyncio.run(manager.get_run("r1"))

        assert state == created
        assert etag
        _, etag_again = asyncio.run(manager.get_run("r1"))
        assert etag_again == etag

    def test_reads_through_to_disk_on_cache_miss(self, tmp_path):
        """A run written outside the manager is loaded from disk and cached."""
        manager = make_manager(tmp_path)
        write_run(manager.runs_root, "external", status="running")

        state, _ = asyncio.run(manager.get_run("external"))

        assert state["status"] == "running"
        assert "external" in manager._cache

    def test_cache_wins_over_disk(self, tmp_path):
        """Once cached, get_run serves the cached state.

        This documents current behavior: the in-memory cache is authoritative
        for the process that owns it, so an out-of-band disk edit is not
        picked up by a subsequent get_run.
        """
        manager = make_manager(tmp_path)
        asyncio.run(manager.create_run(flow_id="3-build", run_id="r1"))

        write_run(manager.runs_root, "r1", status="clobbered")

        state, _ = asyncio.run(manager.get_run("r1"))
        assert state["status"] == "pending"

    def test_missing_run_raises(self, tmp_path):
        """An unknown run_id raises FileNotFoundError."""
        manager = make_manager(tmp_path)

        with pytest.raises(FileNotFoundError, match="nope"):
            asyncio.run(manager.get_run("nope"))

    def test_rejects_unsafe_run_id(self, tmp_path):
        """Traversal attempts are rejected before any disk access."""
        manager = make_manager(tmp_path)

        with pytest.raises(Exception):
            asyncio.run(manager.get_run("../../etc/passwd"))


class TestUpdateRun:
    """Tests for update_run() and its ETag precondition."""

    def test_applies_updates_and_bumps_updated_at(self, tmp_path):
        """Updates are merged, persisted, and stamped with a new updated_at."""
        manager = make_manager(tmp_path)
        created = asyncio.run(manager.create_run(flow_id="3-build", run_id="r1"))

        state, etag = asyncio.run(manager.update_run("r1", {"status": "running"}))

        assert state["status"] == "running"
        assert state["flow_id"] == created["flow_id"]
        assert state["updated_at"] >= created["updated_at"]

        on_disk = json.loads(
            (manager.runs_root / "r1" / "run_state.json").read_text(encoding="utf-8")
        )
        assert on_disk["status"] == "running"

        _, current_etag = asyncio.run(manager.get_run("r1"))
        assert current_etag == etag

    def test_matching_etag_is_accepted(self, tmp_path):
        """An update carrying the current ETag succeeds."""
        manager = make_manager(tmp_path)
        asyncio.run(manager.create_run(flow_id="3-build", run_id="r1"))
        _, etag = asyncio.run(manager.get_run("r1"))

        state, _ = asyncio.run(manager.update_run("r1", {"status": "running"}, expected_etag=etag))

        assert state["status"] == "running"

    def test_stale_etag_is_rejected(self, tmp_path):
        """A stale ETag raises and leaves state untouched (lost-update guard)."""
        manager = make_manager(tmp_path)
        asyncio.run(manager.create_run(flow_id="3-build", run_id="r1"))
        _, stale_etag = asyncio.run(manager.get_run("r1"))

        # Someone else writes first, invalidating the caller's ETag.
        asyncio.run(manager.update_run("r1", {"status": "running"}))

        with pytest.raises(ValueError, match="ETag mismatch"):
            asyncio.run(manager.update_run("r1", {"status": "failed"}, expected_etag=stale_etag))

        state, _ = asyncio.run(manager.get_run("r1"))
        assert state["status"] == "running"

    def test_missing_run_raises(self, tmp_path):
        """Updating an unknown run raises FileNotFoundError."""
        manager = make_manager(tmp_path)

        with pytest.raises(FileNotFoundError):
            asyncio.run(manager.update_run("nope", {"status": "running"}))
