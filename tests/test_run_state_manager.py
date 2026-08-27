"""Lifecycle tests for RunStateManager (issue #222).

Covers create/get/update, ETag concurrency control, and disk persistence.
Listing behaviour lives in test_run_state_manager_listing.py.

Async methods are driven with asyncio.run(), matching the convention used by
the other async tests in this suite (no pytest-asyncio dependency). Each test
runs its whole scenario inside a single event loop, because the manager keeps
per-run asyncio.Lock objects that must not be shared across loops.
"""

from __future__ import annotations

import asyncio
import json

import pytest

from swarm.api.services.run_state import RunStateManager


def _manager(tmp_path) -> RunStateManager:
    return RunStateManager(runs_root=tmp_path)


async def _steps(*actions):
    """Await each action in order, collecting results.

    Each action is called with the list of results so far, so a later step can
    use an earlier step's output (an ETag, say). Keeping the whole scenario in
    one call means it also stays in one event loop, which matters because the
    manager holds per-run asyncio.Lock objects.
    """
    results = []
    for action in actions:
        results.append(await action(results))
    return results


class TestCreateRun:
    """create_run() persists a well-formed initial state."""

    def test_creates_state_with_generated_run_id(self, tmp_path):
        manager = _manager(tmp_path)

        state = asyncio.run(manager.create_run(flow_id="signal"))

        assert state["flow_id"] == "signal"
        assert state["status"] == "pending"
        assert state["run_id"].startswith("signal-")
        assert state["completed_steps"] == []
        assert state["error"] is None

    def test_honours_explicit_run_id_and_records_inputs(self, tmp_path):
        manager = _manager(tmp_path)

        state = asyncio.run(
            manager.create_run(
                flow_id="gate",
                run_id="run-ctx",
                context={"issue": 222},
                start_step="1",
            )
        )

        assert state["run_id"] == "run-ctx"
        assert state["context"] == {"issue": 222}
        assert state["current_step"] == "1"

    def test_writes_state_to_disk(self, tmp_path):
        manager = _manager(tmp_path)

        asyncio.run(manager.create_run(flow_id="plan", run_id="run-disk"))

        state_path = tmp_path / "run-disk" / "run_state.json"
        assert state_path.exists()
        assert json.loads(state_path.read_text())["flow_id"] == "plan"

    def test_rejects_path_traversal_in_flow_id(self, tmp_path):
        manager = _manager(tmp_path)

        with pytest.raises(ValueError):
            asyncio.run(manager.create_run(flow_id="../escape"))


class TestGetRun:
    """get_run() returns state plus a content-derived ETag."""

    def test_returns_created_state_and_etag(self, tmp_path):
        manager = _manager(tmp_path)

        _, (state, etag) = asyncio.run(
            _steps(
                lambda _: manager.create_run(flow_id="signal", run_id="run-get"),
                lambda _: manager.get_run("run-get"),
            )
        )

        assert state["run_id"] == "run-get"
        assert etag

    def test_reads_through_to_disk_when_cache_is_cold(self, tmp_path):
        """A fresh manager must recover state written by a previous process."""
        writer = _manager(tmp_path)
        reader = _manager(tmp_path)  # separate instance: empty in-memory cache

        _, (state, _) = asyncio.run(
            _steps(
                lambda _: writer.create_run(flow_id="signal", run_id="run-cold"),
                lambda _: reader.get_run("run-cold"),
            )
        )

        assert state["run_id"] == "run-cold"

    def test_missing_run_raises_file_not_found(self, tmp_path):
        manager = _manager(tmp_path)

        with pytest.raises(FileNotFoundError):
            asyncio.run(manager.get_run("no-such-run"))


class TestUpdateRun:
    """update_run() applies changes under optimistic concurrency control."""

    def test_applies_updates_and_bumps_timestamp(self, tmp_path):
        manager = _manager(tmp_path)

        created, (updated, _) = asyncio.run(
            _steps(
                lambda _: manager.create_run(flow_id="build", run_id="run-upd"),
                lambda _: manager.update_run("run-upd", {"status": "running"}),
            )
        )

        assert updated["status"] == "running"
        assert updated["updated_at"] >= created["created_at"]

    def test_update_is_persisted(self, tmp_path):
        manager = _manager(tmp_path)

        asyncio.run(
            _steps(
                lambda _: manager.create_run(flow_id="build", run_id="run-persist"),
                lambda _: manager.update_run("run-persist", {"status": "completed"}),
            )
        )

        on_disk = json.loads((tmp_path / "run-persist" / "run_state.json").read_text())
        assert on_disk["status"] == "completed"

    def test_matching_etag_is_accepted(self, tmp_path):
        manager = _manager(tmp_path)

        results = asyncio.run(
            _steps(
                lambda _: manager.create_run(flow_id="build", run_id="run-etag-ok"),
                lambda _: manager.get_run("run-etag-ok"),
                lambda r: manager.update_run(
                    "run-etag-ok", {"status": "running"}, expected_etag=r[1][1]
                ),
            )
        )

        state, _ = results[2]
        assert state["status"] == "running"

    def test_stale_etag_is_rejected(self, tmp_path):
        """A second writer using a pre-update ETag must be refused."""
        manager = _manager(tmp_path)

        with pytest.raises(ValueError, match="ETag mismatch"):
            asyncio.run(
                _steps(
                    lambda _: manager.create_run(flow_id="build", run_id="run-stale"),
                    lambda _: manager.get_run("run-stale"),
                    # First writer wins, which invalidates the ETag read above.
                    lambda _: manager.update_run("run-stale", {"status": "running"}),
                    # Second writer still presents that now-stale ETag (r[1][1]).
                    lambda r: manager.update_run(
                        "run-stale", {"status": "failed"}, expected_etag=r[1][1]
                    ),
                )
            )

    def test_etag_changes_when_state_changes(self, tmp_path):
        manager = _manager(tmp_path)

        results = asyncio.run(
            _steps(
                lambda _: manager.create_run(flow_id="build", run_id="run-etag-diff"),
                lambda _: manager.get_run("run-etag-diff"),
                lambda _: manager.update_run("run-etag-diff", {"status": "running"}),
            )
        )

        before = results[1][1]
        after = results[2][1]
        assert before != after
