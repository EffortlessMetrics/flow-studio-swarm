"""Listing tests for RunStateManager (issues #222, #223).

list_runs() is async so that the filesystem scan does not block the event loop
of the API server that calls it. These tests pin both the async contract and
the summary shape.
"""

from __future__ import annotations

import asyncio
import inspect
import threading

from swarm.api.services.run_state import RunStateManager


def _manager(tmp_path) -> RunStateManager:
    return RunStateManager(runs_root=tmp_path)


async def _seed_then_list(manager, run_ids, flow_id="signal", limit=20):
    """Create each run, then list. Keeps the scenario in one event loop."""
    for run_id in run_ids:
        await manager.create_run(flow_id=flow_id, run_id=run_id)
    return await manager.list_runs(limit=limit)


class TestListRunsAsyncContract:
    """The public surface is consistently async (issue #223)."""

    def test_list_runs_is_a_coroutine_function(self):
        """Regression guard: list_runs used to be sync while its siblings were
        async, so an async endpoint calling it blocked the event loop for the
        duration of the directory scan."""
        assert inspect.iscoroutinefunction(RunStateManager.list_runs)

    def test_public_methods_are_all_async(self):
        for name in ("create_run", "get_run", "update_run", "list_runs"):
            assert inspect.iscoroutinefunction(getattr(RunStateManager, name)), (
                f"{name} should be a coroutine function"
            )

    def test_scan_runs_off_the_event_loop_thread(self, tmp_path):
        """The blocking scan must not execute on the event loop's thread.

        This is the substance of issue #223: the filesystem walk is offloaded
        to a worker thread, so the loop stays free to serve other requests.
        Comparing thread identity fails if the scan is called inline, which a
        wall-clock or task-interleaving assertion would not catch.
        """
        manager = _manager(tmp_path)
        scan_thread = {}
        original = manager._list_runs_sync

        def recording_scan(limit=20):
            scan_thread["ident"] = threading.get_ident()
            return original(limit)

        manager._list_runs_sync = recording_scan

        runs = asyncio.run(_seed_then_list(manager, ["run-thread"]))

        assert len(runs) == 1
        assert scan_thread["ident"] != threading.get_ident(), (
            "list_runs ran the blocking scan on the event loop thread"
        )


class TestListRunsResults:
    """list_runs() reports the runs it can read, and skips the rest."""

    def test_empty_when_runs_root_missing(self, tmp_path):
        manager = RunStateManager(runs_root=tmp_path / "does-not-exist")

        assert asyncio.run(manager.list_runs()) == []

    def test_returns_created_runs(self, tmp_path):
        runs = asyncio.run(_seed_then_list(_manager(tmp_path), ["run-1", "run-2"]))

        assert {r["run_id"] for r in runs} == {"run-1", "run-2"}

    def test_respects_limit(self, tmp_path):
        runs = asyncio.run(
            _seed_then_list(_manager(tmp_path), [f"run-{i}" for i in range(5)], limit=2)
        )

        assert len(runs) == 2

    def test_skips_directories_without_state_file(self, tmp_path):
        """Stray directories under runs_root are not runs."""
        (tmp_path / "not-a-run").mkdir()

        runs = asyncio.run(_seed_then_list(_manager(tmp_path), ["real-run"]))

        assert [r["run_id"] for r in runs] == ["real-run"]

    def test_tolerates_corrupt_state_file(self, tmp_path):
        """A malformed run_state.json is skipped, not fatal."""
        broken = tmp_path / "broken-run"
        broken.mkdir()
        (broken / "run_state.json").write_text("{ not json", encoding="utf-8")

        runs = asyncio.run(_seed_then_list(_manager(tmp_path), ["good-run"]))

        assert [r["run_id"] for r in runs] == ["good-run"]

    def test_summary_shape(self, tmp_path):
        (summary,) = asyncio.run(_seed_then_list(_manager(tmp_path), ["run-shape"]))

        assert set(summary) == {"run_id", "flow_key", "status", "timestamp"}
        assert summary["status"] == "pending"
