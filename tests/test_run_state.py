"""
Tests for RunStateManager creation and retrieval.

Covers create_run (id generation, explicit ids, optional params, path
validation) and get_run (cache and disk reads, ETag stability, missing
runs). See tests/run_state_support.py for shared setup.
"""

import asyncio

import pytest
from run_state_support import manager, read_state_file  # noqa: F401

from swarm.api.services.run_state import RunStateManager


class TestCreateRun:
    """Tests for run creation."""

    def test_create_run_generates_run_id(self, manager):
        """A run created without an explicit id gets a generated one."""
        state = asyncio.run(manager.create_run("3-build"))

        assert state["run_id"].startswith("3-build-")
        assert state["flow_id"] == "3-build"
        assert state["status"] == "pending"

    def test_create_run_honours_explicit_run_id(self, manager):
        """An explicit run_id is used verbatim."""
        state = asyncio.run(manager.create_run("3-build", run_id="my-run"))

        assert state["run_id"] == "my-run"

    def test_create_run_persists_state_to_disk(self, manager):
        """Created state is written under runs_root/<run_id>/run_state.json."""
        asyncio.run(manager.create_run("3-build", run_id="my-run"))

        on_disk = read_state_file(manager.runs_root, "my-run")
        assert on_disk["run_id"] == "my-run"
        assert on_disk["flow_id"] == "3-build"

    def test_create_run_records_optional_params(self, manager):
        """context and start_step are recorded on the initial state."""
        state = asyncio.run(
            manager.create_run(
                "3-build",
                run_id="my-run",
                context={"issue": "223"},
                start_step="step-0",
            )
        )

        assert state["context"] == {"issue": "223"}
        assert state["current_step"] == "step-0"

    def test_create_run_defaults_empty_context(self, manager):
        """Omitting context yields an empty dict, not None."""
        state = asyncio.run(manager.create_run("3-build", run_id="my-run"))

        assert state["context"] == {}
        assert state["current_step"] is None

    def test_create_run_generates_unique_ids(self, manager):
        """Two runs of the same flow do not collide."""
        first = asyncio.run(manager.create_run("3-build"))
        second = asyncio.run(manager.create_run("3-build"))

        assert first["run_id"] != second["run_id"]

    def test_create_run_rejects_path_traversal(self, manager):
        """Path components are validated before touching the filesystem."""
        with pytest.raises(ValueError, match="flow_id"):
            asyncio.run(manager.create_run("../etc/passwd"))

        with pytest.raises(ValueError, match="run_id"):
            asyncio.run(manager.create_run("3-build", run_id="../escape"))


class TestGetRun:
    """Tests for run state retrieval."""

    def test_get_run_returns_state_and_etag(self, manager):
        """get_run returns the state plus a non-empty ETag."""
        asyncio.run(manager.create_run("3-build", run_id="my-run"))

        state, etag = asyncio.run(manager.get_run("my-run"))

        assert state["run_id"] == "my-run"
        assert etag

    def test_get_run_etag_is_stable_for_unchanged_state(self, manager):
        """Repeated reads of unchanged state produce the same ETag."""
        asyncio.run(manager.create_run("3-build", run_id="my-run"))

        _, first = asyncio.run(manager.get_run("my-run"))
        _, second = asyncio.run(manager.get_run("my-run"))

        assert first == second

    def test_get_run_etag_changes_after_update(self, manager):
        """Mutating state produces a different ETag."""
        asyncio.run(manager.create_run("3-build", run_id="my-run"))
        _, before = asyncio.run(manager.get_run("my-run"))

        asyncio.run(manager.update_run("my-run", {"status": "running"}))
        _, after = asyncio.run(manager.get_run("my-run"))

        assert before != after

    def test_get_run_reads_from_disk_when_cache_is_cold(self, tmp_path):
        """A fresh manager loads state written by a previous instance."""
        runs_root = tmp_path / "runs"
        asyncio.run(RunStateManager(runs_root).create_run("3-build", run_id="my-run"))

        cold = RunStateManager(runs_root)
        state, _ = asyncio.run(cold.get_run("my-run"))

        assert state["run_id"] == "my-run"

    def test_get_run_populates_cache(self, tmp_path):
        """A disk read warms the in-memory cache."""
        runs_root = tmp_path / "runs"
        asyncio.run(RunStateManager(runs_root).create_run("3-build", run_id="my-run"))

        cold = RunStateManager(runs_root)
        assert "my-run" not in cold._cache

        asyncio.run(cold.get_run("my-run"))
        assert "my-run" in cold._cache

    def test_get_run_raises_for_missing_run(self, manager):
        """An unknown run id raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError, match="not found"):
            asyncio.run(manager.get_run("does-not-exist"))

    def test_get_run_rejects_path_traversal(self, manager):
        """run_id is validated before it is used as a path component."""
        with pytest.raises(ValueError, match="run_id"):
            asyncio.run(manager.get_run("../etc/passwd"))
