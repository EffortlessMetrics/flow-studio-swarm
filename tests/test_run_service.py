"""
Tests for the swarm/runtime module.

Tests cover:
- types.py: Dataclasses and serialization
- storage.py: Disk I/O operations
- backends.py: Backend abstraction
- service.py: RunService orchestration
"""

from datetime import datetime, timezone

from swarm.runtime import storage
from swarm.runtime.service import RunService
from swarm.runtime.types import (
    RunEvent,
    RunSpec,
    RunStatus,
    RunSummary,
    SDLCStatus,
    generate_run_id,
    run_event_from_dict,
    run_event_to_dict,
    run_spec_from_dict,
    run_spec_to_dict,
    run_summary_from_dict,
    run_summary_to_dict,
)


class TestTypes:
    """Test core type definitions and serialization."""

    def test_generate_run_id(self):
        """Run IDs should be unique and follow expected format."""
        id1 = generate_run_id()
        id2 = generate_run_id()

        assert id1 != id2
        assert id1.startswith("run-")
        # Format: run-YYYYMMDD-HHMMSS-XXXXXX
        parts = id1.split("-")
        assert len(parts) == 4
        assert len(parts[1]) == 8  # YYYYMMDD
        assert len(parts[2]) == 6  # HHMMSS
        assert len(parts[3]) == 6  # hex suffix

    def test_run_spec_roundtrip(self):
        """RunSpec should serialize and deserialize correctly."""
        spec = RunSpec(
            flow_keys=["signal", "build"],
            profile_id="baseline",
            backend="claude-harness",
            initiator="test",
            params={"foo": "bar"},
        )

        data = run_spec_to_dict(spec)
        restored = run_spec_from_dict(data)

        assert restored.flow_keys == spec.flow_keys
        assert restored.profile_id == spec.profile_id
        assert restored.backend == spec.backend
        assert restored.initiator == spec.initiator
        assert restored.params == spec.params

    def test_run_summary_roundtrip(self):
        """RunSummary should serialize and deserialize correctly."""
        now = datetime.now(timezone.utc)
        summary = RunSummary(
            id="run-test-123",
            spec=RunSpec(flow_keys=["signal"], backend="claude-harness", initiator="test"),
            status=RunStatus.SUCCEEDED,
            sdlc_status=SDLCStatus.OK,
            created_at=now,
            updated_at=now,
            completed_at=now,
            is_exemplar=True,
            tags=["test", "golden"],
        )

        data = run_summary_to_dict(summary)
        restored = run_summary_from_dict(data)

        assert restored.id == summary.id
        assert restored.status == summary.status
        assert restored.sdlc_status == summary.sdlc_status
        assert restored.is_exemplar == summary.is_exemplar
        assert restored.tags == summary.tags

    def test_run_event_roundtrip(self):
        """RunEvent should serialize and deserialize correctly."""
        now = datetime.now(timezone.utc)
        event = RunEvent(
            run_id="run-test-123",
            ts=now,
            kind="flow_start",
            flow_key="signal",
            step_id="normalize",
            payload={"foo": "bar"},
        )

        data = run_event_to_dict(event)
        restored = run_event_from_dict(data)

        assert restored.run_id == event.run_id
        assert restored.kind == event.kind
        assert restored.flow_key == event.flow_key
        assert restored.step_id == event.step_id
        assert restored.payload == event.payload


class TestStorage:
    """Test disk I/O operations."""

    def test_create_and_read_spec(self, tmp_path):
        """Should write and read RunSpec correctly."""
        run_id = "test-run-001"
        spec = RunSpec(
            flow_keys=["signal"],
            backend="claude-harness",
            initiator="test",
        )

        storage.write_spec(run_id, spec, runs_dir=tmp_path)
        restored = storage.read_spec(run_id, runs_dir=tmp_path)

        assert restored is not None
        assert restored.flow_keys == spec.flow_keys

    def test_create_and_read_summary(self, tmp_path):
        """Should write and read RunSummary correctly."""
        run_id = "test-run-002"
        now = datetime.now(timezone.utc)
        summary = RunSummary(
            id=run_id,
            spec=RunSpec(flow_keys=["signal"], backend="claude-harness", initiator="test"),
            status=RunStatus.PENDING,
            sdlc_status=SDLCStatus.UNKNOWN,
            created_at=now,
            updated_at=now,
        )

        storage.write_summary(run_id, summary, runs_dir=tmp_path)
        restored = storage.read_summary(run_id, runs_dir=tmp_path)

        assert restored is not None
        assert restored.id == run_id
        assert restored.status == RunStatus.PENDING

    def test_update_summary(self, tmp_path):
        """Should partially update RunSummary fields."""
        run_id = "test-run-003"
        now = datetime.now(timezone.utc)
        summary = RunSummary(
            id=run_id,
            spec=RunSpec(flow_keys=["signal"], backend="claude-harness", initiator="test"),
            status=RunStatus.PENDING,
            sdlc_status=SDLCStatus.UNKNOWN,
            created_at=now,
            updated_at=now,
        )

        storage.write_summary(run_id, summary, runs_dir=tmp_path)
        updated = storage.update_summary(run_id, {"status": "running"}, runs_dir=tmp_path)

        assert updated is not None
        assert updated.status == RunStatus.RUNNING

    def test_append_and_read_events(self, tmp_path):
        """Should append and read events correctly."""
        run_id = "test-run-004"
        now = datetime.now(timezone.utc)

        event1 = RunEvent(run_id=run_id, ts=now, kind="start", flow_key="signal")
        event2 = RunEvent(run_id=run_id, ts=now, kind="end", flow_key="signal")

        storage.append_event(run_id, event1, runs_dir=tmp_path)
        storage.append_event(run_id, event2, runs_dir=tmp_path)

        events = storage.read_events(run_id, runs_dir=tmp_path)

        assert len(events) == 2
        assert events[0].kind == "start"
        assert events[1].kind == "end"

    def test_list_runs(self, tmp_path):
        """Should list runs that have meta.json."""
        # Create two runs with meta.json
        for run_id in ["run-a", "run-b"]:
            now = datetime.now(timezone.utc)
            summary = RunSummary(
                id=run_id,
                spec=RunSpec(flow_keys=["signal"], backend="claude-harness", initiator="test"),
                status=RunStatus.PENDING,
                sdlc_status=SDLCStatus.UNKNOWN,
                created_at=now,
                updated_at=now,
            )
            storage.write_summary(run_id, summary, runs_dir=tmp_path)

        runs = storage.list_runs(runs_dir=tmp_path)
        assert len(runs) == 2
        assert "run-a" in runs
        assert "run-b" in runs

    def test_discover_legacy_runs(self, tmp_path):
        """Should find runs with flow dirs but no meta.json."""
        # Create a legacy run (has signal/ dir but no meta.json)
        legacy_path = tmp_path / "legacy-run"
        (legacy_path / "signal").mkdir(parents=True)

        # Create a normal run (has meta.json)
        now = datetime.now(timezone.utc)
        normal_summary = RunSummary(
            id="normal-run",
            spec=RunSpec(flow_keys=["signal"], backend="claude-harness", initiator="test"),
            status=RunStatus.PENDING,
            sdlc_status=SDLCStatus.UNKNOWN,
            created_at=now,
            updated_at=now,
        )
        storage.write_summary("normal-run", normal_summary, runs_dir=tmp_path)

        legacy = storage.discover_legacy_runs(runs_dir=tmp_path)
        assert "legacy-run" in legacy
        assert "normal-run" not in legacy

    def test_run_exists(self, tmp_path):
        """Should check if run exists by meta.json presence."""
        run_id = "exists-test"

        assert not storage.run_exists(run_id, runs_dir=tmp_path)

        now = datetime.now(timezone.utc)
        summary = RunSummary(
            id=run_id,
            spec=RunSpec(flow_keys=["signal"], backend="claude-harness", initiator="test"),
            status=RunStatus.PENDING,
            sdlc_status=SDLCStatus.UNKNOWN,
            created_at=now,
            updated_at=now,
        )
        storage.write_summary(run_id, summary, runs_dir=tmp_path)

        assert storage.run_exists(run_id, runs_dir=tmp_path)


class TestRunService:
    """Test RunService orchestration."""

    def test_singleton(self, tmp_path):
        """RunService should be a singleton."""
        RunService.reset()  # Clear any existing instance

        service1 = RunService.get_instance(tmp_path)
        service2 = RunService.get_instance(tmp_path)

        assert service1 is service2

        RunService.reset()  # Clean up

    def test_list_backends(self, tmp_path):
        """Should list available backends."""
        RunService.reset()
        service = RunService.get_instance(tmp_path)

        backends = service.list_backends()

        assert len(backends) >= 1
        backend_ids = [b.id for b in backends]
        assert "claude-harness" in backend_ids

        RunService.reset()

    def test_get_run_not_found(self, tmp_path):
        """Should return None for non-existent run."""
        RunService.reset()
        service = RunService.get_instance(tmp_path)

        result = service.get_run("non-existent-run")
        assert result is None

        RunService.reset()

    def test_mark_exemplar(self, tmp_path, monkeypatch):
        """Should mark and unmark runs as exemplars."""
        # Patch RUNS_DIR to use tmp_path
        monkeypatch.setattr(storage, "RUNS_DIR", tmp_path)

        RunService.reset()
        service = RunService.get_instance(tmp_path)

        # Create a run
        run_id = "exemplar-test"
        now = datetime.now(timezone.utc)
        summary = RunSummary(
            id=run_id,
            spec=RunSpec(flow_keys=["signal"], backend="claude-harness", initiator="test"),
            status=RunStatus.SUCCEEDED,
            sdlc_status=SDLCStatus.OK,
            created_at=now,
            updated_at=now,
        )
        storage.write_summary(run_id, summary)

        # Mark as exemplar
        result = service.mark_exemplar(run_id, True)
        assert result is True

        updated = service.get_run(run_id)
        assert updated is not None
        assert updated.is_exemplar is True

        # Unmark
        service.mark_exemplar(run_id, False)
        updated = service.get_run(run_id)
        assert updated.is_exemplar is False

        RunService.reset()

    def test_list_exemplars(self, tmp_path, monkeypatch):
        """Should list only exemplar runs."""
        # Patch RUNS_DIR to use tmp_path
        monkeypatch.setattr(storage, "RUNS_DIR", tmp_path)

        RunService.reset()
        service = RunService.get_instance(tmp_path)

        now = datetime.now(timezone.utc)

        # Create normal run
        normal_summary = RunSummary(
            id="normal-run",
            spec=RunSpec(flow_keys=["signal"], backend="claude-harness", initiator="test"),
            status=RunStatus.SUCCEEDED,
            sdlc_status=SDLCStatus.OK,
            created_at=now,
            updated_at=now,
            is_exemplar=False,
        )
        storage.write_summary("normal-run", normal_summary)

        # Create exemplar run
        exemplar_summary = RunSummary(
            id="exemplar-run",
            spec=RunSpec(flow_keys=["signal"], backend="claude-harness", initiator="test"),
            status=RunStatus.SUCCEEDED,
            sdlc_status=SDLCStatus.OK,
            created_at=now,
            updated_at=now,
            is_exemplar=True,
        )
        storage.write_summary("exemplar-run", exemplar_summary)

        exemplars = service.list_exemplars()
        assert len(exemplars) == 1
        assert exemplars[0].id == "exemplar-run"

        RunService.reset()


class TestRunServiceCaching:
    """Test RunService caching behavior for terminal runs.

    Note: These tests monkeypatch storage.RUNS_DIR to use tmp_path, ensuring
    test isolation. The monkeypatched RUNS_DIR is used by storage functions
    when called without explicit runs_dir parameter.
    """

    def test_cache_hit_for_terminal_run(self, tmp_path, monkeypatch):
        """Should cache terminal runs and avoid repeated disk reads."""
        monkeypatch.setattr(storage, "RUNS_DIR", tmp_path)

        RunService.reset()
        service = RunService.get_instance(tmp_path)

        # Create a terminal run (in real directory for service to find)
        run_id = "cache-test-succeeded"
        now = datetime.now(timezone.utc)
        summary = RunSummary(
            id=run_id,
            spec=RunSpec(flow_keys=["signal"], backend="claude-harness", initiator="test"),
            status=RunStatus.SUCCEEDED,
            sdlc_status=SDLCStatus.OK,
            created_at=now,
            updated_at=now,
        )
        storage.write_summary(run_id, summary)  # Use default runs_dir

        try:
            # First call: should read from disk and cache
            result1 = service.get_run(run_id)
            assert result1 is not None
            assert result1.status == RunStatus.SUCCEEDED

            # Verify it's in the cache
            assert run_id in service._summary_cache

            # Second call: should hit cache (same object)
            result2 = service.get_run(run_id)
            assert result2 is result1
        finally:
            # Cleanup
            import shutil
            run_path = storage.get_run_path(run_id)
            if run_path.exists():
                shutil.rmtree(run_path)
            RunService.reset()

    def test_no_cache_for_non_terminal_run(self, tmp_path, monkeypatch):
        """Should NOT cache non-terminal runs (PENDING, RUNNING)."""
        monkeypatch.setattr(storage, "RUNS_DIR", tmp_path)

        RunService.reset()
        service = RunService.get_instance(tmp_path)

        # Create a non-terminal run
        run_id = "cache-test-running"
        now = datetime.now(timezone.utc)
        summary = RunSummary(
            id=run_id,
            spec=RunSpec(flow_keys=["signal"], backend="claude-harness", initiator="test"),
            status=RunStatus.RUNNING,
            sdlc_status=SDLCStatus.UNKNOWN,
            created_at=now,
            updated_at=now,
        )
        storage.write_summary(run_id, summary)  # Use default runs_dir

        try:
            # Call get_run
            result = service.get_run(run_id)
            assert result is not None
            assert result.status == RunStatus.RUNNING

            # Should NOT be cached
            assert run_id not in service._summary_cache
        finally:
            # Cleanup
            import shutil
            run_path = storage.get_run_path(run_id)
            if run_path.exists():
                shutil.rmtree(run_path)
            RunService.reset()

    def test_cache_invalidation_on_mark_exemplar(self, tmp_path, monkeypatch):
        """Cache should be invalidated when marking as exemplar."""
        monkeypatch.setattr(storage, "RUNS_DIR", tmp_path)

        RunService.reset()
        service = RunService.get_instance(tmp_path)

        # Create and cache a terminal run
        run_id = "cache-invalidate-test"
        now = datetime.now(timezone.utc)
        summary = RunSummary(
            id=run_id,
            spec=RunSpec(flow_keys=["signal"], backend="claude-harness", initiator="test"),
            status=RunStatus.SUCCEEDED,
            sdlc_status=SDLCStatus.OK,
            created_at=now,
            updated_at=now,
            is_exemplar=False,
        )
        storage.write_summary(run_id, summary)  # Use default runs_dir

        try:
            # Populate cache
            service.get_run(run_id)
            assert run_id in service._summary_cache

            # Mark as exemplar (should invalidate cache)
            service.mark_exemplar(run_id, True)
            assert run_id not in service._summary_cache

            # Next get_run should re-read from disk and see updated value
            result = service.get_run(run_id)
            assert result.is_exemplar is True
        finally:
            # Cleanup
            import shutil
            run_path = storage.get_run_path(run_id)
            if run_path.exists():
                shutil.rmtree(run_path)
            RunService.reset()

    def test_cache_invalidation_on_add_tag(self, tmp_path, monkeypatch):
        """Cache should be invalidated when adding a tag."""
        monkeypatch.setattr(storage, "RUNS_DIR", tmp_path)

        RunService.reset()
        service = RunService.get_instance(tmp_path)

        run_id = "cache-tag-test"
        now = datetime.now(timezone.utc)
        summary = RunSummary(
            id=run_id,
            spec=RunSpec(flow_keys=["signal"], backend="claude-harness", initiator="test"),
            status=RunStatus.FAILED,
            sdlc_status=SDLCStatus.ERROR,
            created_at=now,
            updated_at=now,
            tags=[],
        )
        storage.write_summary(run_id, summary)  # Use default runs_dir

        try:
            # Populate cache
            service.get_run(run_id)
            assert run_id in service._summary_cache

            # Add tag (should invalidate cache)
            service.add_tag(run_id, "important")
            assert run_id not in service._summary_cache

            # Next get_run should see updated tags
            result = service.get_run(run_id)
            assert "important" in result.tags
        finally:
            # Cleanup
            import shutil
            run_path = storage.get_run_path(run_id)
            if run_path.exists():
                shutil.rmtree(run_path)
            RunService.reset()

    def test_cache_invalidation_on_remove_tag(self, tmp_path, monkeypatch):
        """Cache should be invalidated when removing a tag."""
        monkeypatch.setattr(storage, "RUNS_DIR", tmp_path)

        RunService.reset()
        service = RunService.get_instance(tmp_path)

        run_id = "cache-remove-tag-test"
        now = datetime.now(timezone.utc)
        summary = RunSummary(
            id=run_id,
            spec=RunSpec(flow_keys=["signal"], backend="claude-harness", initiator="test"),
            status=RunStatus.FAILED,
            sdlc_status=SDLCStatus.ERROR,
            created_at=now,
            updated_at=now,
            tags=["to-remove", "keep"],
        )
        storage.write_summary(run_id, summary)

        try:
            # Populate cache
            service.get_run(run_id)
            assert run_id in service._summary_cache

            # Remove tag (should invalidate cache)
            service.remove_tag(run_id, "to-remove")
            assert run_id not in service._summary_cache

            # Next get_run should see updated tags
            result = service.get_run(run_id)
            assert "to-remove" not in result.tags
            assert "keep" in result.tags
        finally:
            # Cleanup
            import shutil
            run_path = storage.get_run_path(run_id)
            if run_path.exists():
                shutil.rmtree(run_path)
            RunService.reset()

    def test_remove_tag_noop_if_not_present(self, tmp_path, monkeypatch):
        """remove_tag should not invalidate cache if tag wasn't present."""
        monkeypatch.setattr(storage, "RUNS_DIR", tmp_path)

        RunService.reset()
        service = RunService.get_instance(tmp_path)

        run_id = "cache-remove-noop-test"
        now = datetime.now(timezone.utc)
        summary = RunSummary(
            id=run_id,
            spec=RunSpec(flow_keys=["signal"], backend="claude-harness", initiator="test"),
            status=RunStatus.FAILED,
            sdlc_status=SDLCStatus.ERROR,
            created_at=now,
            updated_at=now,
            tags=["existing"],
        )
        storage.write_summary(run_id, summary)

        try:
            # Populate cache
            cached = service.get_run(run_id)
            assert run_id in service._summary_cache

            # Try to remove non-existent tag (should NOT invalidate cache)
            service.remove_tag(run_id, "non-existent")
            assert run_id in service._summary_cache

            # Should still be the same cached object
            assert service.get_run(run_id) is cached
        finally:
            # Cleanup
            import shutil
            run_path = storage.get_run_path(run_id)
            if run_path.exists():
                shutil.rmtree(run_path)
            RunService.reset()

    def test_clear_cache(self, tmp_path, monkeypatch):
        """Should clear entire cache when clear_cache() called."""
        monkeypatch.setattr(storage, "RUNS_DIR", tmp_path)

        RunService.reset()
        service = RunService.get_instance(tmp_path)

        # Create multiple terminal runs
        now = datetime.now(timezone.utc)
        run_ids = []
        for i in range(3):
            run_id = f"clear-cache-test-{i}"
            run_ids.append(run_id)
            summary = RunSummary(
                id=run_id,
                spec=RunSpec(flow_keys=["signal"], backend="claude-harness", initiator="test"),
                status=RunStatus.CANCELED,
                sdlc_status=SDLCStatus.UNKNOWN,
                created_at=now,
                updated_at=now,
            )
            storage.write_summary(run_id, summary)  # Use default runs_dir
            service.get_run(run_id)

        try:
            # All should be cached
            assert len(service._summary_cache) == 3

            # Clear cache
            service.clear_cache()
            assert len(service._summary_cache) == 0
        finally:
            # Cleanup
            import shutil
            for run_id in run_ids:
                run_path = storage.get_run_path(run_id)
                if run_path.exists():
                    shutil.rmtree(run_path)
            RunService.reset()

    def test_reset_clears_cache(self, tmp_path, monkeypatch):
        """RunService.reset() should clear the cache for test isolation."""
        monkeypatch.setattr(storage, "RUNS_DIR", tmp_path)

        RunService.reset()
        service = RunService.get_instance(tmp_path)

        # Create and cache a run
        run_id = "reset-cache-test"
        now = datetime.now(timezone.utc)
        summary = RunSummary(
            id=run_id,
            spec=RunSpec(flow_keys=["signal"], backend="claude-harness", initiator="test"),
            status=RunStatus.SUCCEEDED,
            sdlc_status=SDLCStatus.OK,
            created_at=now,
            updated_at=now,
        )
        storage.write_summary(run_id, summary)  # Use default runs_dir
        service.get_run(run_id)

        try:
            assert len(service._summary_cache) == 1

            # Reset should clear the cache
            RunService.reset()

            # New instance should have empty cache
            new_service = RunService.get_instance(tmp_path)
            assert len(new_service._summary_cache) == 0
        finally:
            # Cleanup
            import shutil
            run_path = storage.get_run_path(run_id)
            if run_path.exists():
                shutil.rmtree(run_path)
            RunService.reset()
