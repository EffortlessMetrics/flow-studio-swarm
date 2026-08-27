"""
Tests for RunStateManager updates, ETag concurrency, and locking.

ETags are the service's optimistic-concurrency control: a writer holding
a stale ETag must lose rather than silently overwrite. See
tests/run_state_support.py for shared setup.
"""

import asyncio

import pytest
from run_state_support import manager, read_state_file  # noqa: F401


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
