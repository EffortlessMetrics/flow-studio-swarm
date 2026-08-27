"""
Tests for RunStateManager (swarm/api/services/run_state.py).

Covers the public surface of the run state service:

- create_run: id generation, explicit ids, optional params, directory creation
- get_run: cache and disk reads, ETag stability, missing runs
- update_run: ETag validation, concurrent-update rejection, timestamp bumps
- list_runs: ordering, limit, malformed state tolerance
- _save_state: atomic write behaviour (tmp file -> rename, no tmp left behind)
- locking: concurrent get/update against the same run

Async methods are driven with asyncio.run(), matching the convention used by
tests/test_security_path_traversal.py (the suite does not depend on
pytest-asyncio).
"""

import asyncio
import json
from pathlib import Path

import pytest
from swarm.api.services.run_state import RunStateManager


@pytest.fixture
def manager(tmp_path):
    """A RunStateManager rooted at an empty temp directory."""
    return RunStateManager(runs_root=tmp_path / "runs")


def read_state_file(runs_root: Path, run_id: str) -> dict:
    """Read a run's persisted state straight off disk."""
    return json.loads((runs_root / run_id / "run_state.json").read_text(encoding="utf-8"))


# ============================================================================
# create_run
# ============================================================================


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


# ============================================================================
# get_run
# ============================================================================


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


# ============================================================================
# update_run
# ============================================================================


class TestUpdateRun:
    """Tests for run state updates and ETag concurrency control."""

    def test_update_run_applies_updates(self, manager):
        """Supplied fields are merged into the state."""
        asyncio.run(manager.create_run("3-build", run_id="my-run"))

        state, _ = asyncio.run(manager.update_run("my-run", {"status": "running"}))

        assert state["status"] == "running"

    def test_update_run_persists_to_disk(self, manager):
        """Updates are durable, not cache-only."""
        asyncio.run(manager.create_run("3-build", run_id="my-run"))
        asyncio.run(manager.update_run("my-run", {"status": "running"}))

        assert read_state_file(manager.runs_root, "my-run")["status"] == "running"

    def test_update_run_bumps_updated_at(self, manager):
        """updated_at advances on every update."""
        created = asyncio.run(manager.create_run("3-build", run_id="my-run"))
        original = created["updated_at"]

        updated, _ = asyncio.run(manager.update_run("my-run", {"status": "running"}))

        assert updated["updated_at"] >= original

    def test_update_run_accepts_matching_etag(self, manager):
        """An update carrying the current ETag succeeds."""
        asyncio.run(manager.create_run("3-build", run_id="my-run"))
        _, etag = asyncio.run(manager.get_run("my-run"))

        state, _ = asyncio.run(
            manager.update_run("my-run", {"status": "running"}, expected_etag=etag)
        )

        assert state["status"] == "running"

    def test_update_run_rejects_stale_etag(self, manager):
        """An update carrying a stale ETag is refused."""
        asyncio.run(manager.create_run("3-build", run_id="my-run"))

        with pytest.raises(ValueError, match="ETag mismatch"):
            asyncio.run(
                manager.update_run("my-run", {"status": "running"}, expected_etag="stale")
            )

    def test_concurrent_update_with_same_etag_loses(self, manager):
        """Two writers holding the same ETag: the second one is rejected.

        This is the lost-update scenario ETags exist to prevent.
        """
        asyncio.run(manager.create_run("3-build", run_id="my-run"))
        _, shared_etag = asyncio.run(manager.get_run("my-run"))

        async def race():
            await manager.update_run("my-run", {"status": "running"}, expected_etag=shared_etag)
            # Second writer still holds the pre-update ETag.
            await manager.update_run("my-run", {"status": "failed"}, expected_etag=shared_etag)

        with pytest.raises(ValueError, match="ETag mismatch"):
            asyncio.run(race())

        # The first write stands; the second never landed.
        assert read_state_file(manager.runs_root, "my-run")["status"] == "running"

    def test_update_run_without_etag_skips_the_check(self, manager):
        """Omitting expected_etag is a deliberate last-writer-wins update."""
        asyncio.run(manager.create_run("3-build", run_id="my-run"))
        asyncio.run(manager.update_run("my-run", {"status": "running"}))

        state, _ = asyncio.run(manager.update_run("my-run", {"status": "completed"}))

        assert state["status"] == "completed"

    def test_update_run_raises_for_missing_run(self, manager):
        """Updating an unknown run raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError, match="not found"):
            asyncio.run(manager.update_run("does-not-exist", {"status": "running"}))

    def test_update_run_rejects_path_traversal(self, manager):
        """run_id is validated before it is used as a path component."""
        with pytest.raises(ValueError, match="run_id"):
            asyncio.run(manager.update_run("../etc/passwd", {"status": "running"}))


# ============================================================================
# Locking
# ============================================================================


class TestLocking:
    """Tests for per-run lock behaviour."""

    def test_lock_is_reused_per_run(self, manager):
        """The same run id always maps to the same lock object."""
        assert manager._get_lock("my-run") is manager._get_lock("my-run")

    def test_locks_are_distinct_per_run(self, manager):
        """Different runs get independent locks."""
        assert manager._get_lock("run-a") is not manager._get_lock("run-b")

    def test_concurrent_updates_are_serialized(self, manager):
        """Interleaved updates to one run do not corrupt state.

        Each update is applied under the run lock, so a batch of concurrent
        updates leaves the state consistent and the final value is one of the
        submitted ones.
        """
        asyncio.run(manager.create_run("3-build", run_id="my-run"))

        async def hammer():
            await asyncio.gather(
                *(manager.update_run("my-run", {"status": f"step-{i}"}) for i in range(10))
            )

        asyncio.run(hammer())

        final = read_state_file(manager.runs_root, "my-run")
        assert final["status"] in {f"step-{i}" for i in range(10)}
        assert final["run_id"] == "my-run"


# ============================================================================
# _save_state / atomic writes
# ============================================================================


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


# ============================================================================
# list_runs
# ============================================================================


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
            import os

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
