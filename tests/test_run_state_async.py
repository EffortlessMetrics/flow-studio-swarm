import asyncio

from swarm.api.services.run_state import RunStateManager


def test_run_lifecycle(tmp_path):
    async def _test():
        manager = RunStateManager(runs_root=tmp_path)

        # 1. Create Run
        state = await manager.create_run(flow_id="test-flow")
        run_id = state["run_id"]
        assert state["flow_id"] == "test-flow"
        assert (tmp_path / run_id / "run_state.json").exists()

        # 2. Get Run
        fetched, etag = await manager.get_run(run_id)
        assert fetched["run_id"] == run_id
        assert etag

        # 3. Update Run
        updated, new_etag = await manager.update_run(
            run_id, {"status": "running", "current_step": "step1"}, expected_etag=etag
        )
        assert updated["status"] == "running"
        assert new_etag != etag

        # 4. Get Run again (verify persistence)
        # Clear cache to force disk read
        manager._cache.clear()
        fetched_again, _ = await manager.get_run(run_id)
        assert fetched_again["status"] == "running"

    asyncio.run(_test())


def test_list_runs(tmp_path):
    manager = RunStateManager(runs_root=tmp_path)

    # Create multiple runs (async)
    async def create_runs():
        ids = []
        for i in range(5):
            state = await manager.create_run(flow_id=f"flow-{i}")
            ids.append(state["run_id"])
        return ids

    ids = asyncio.run(create_runs())

    # List runs
    runs = manager.list_runs(limit=10)
    assert len(runs) == 5
    assert {r["run_id"] for r in runs} == set(ids)

    # Test async list runs
    runs_async = asyncio.run(manager.list_runs_async(limit=10))
    assert len(runs_async) == 5
    assert {r["run_id"] for r in runs_async} == set(ids)


def test_concurrent_access(tmp_path):
    async def _test():
        manager = RunStateManager(runs_root=tmp_path)
        state = await manager.create_run(flow_id="concurrent-flow")
        run_id = state["run_id"]

        # Simulate concurrent updates
        async def update_status(status):
            # Retry loop because ETag might mismatch
            for _ in range(10):
                state, etag = await manager.get_run(run_id)
                try:
                    await manager.update_run(
                        run_id, {"status": status}, expected_etag=etag
                    )
                    return
                except ValueError:
                    # ETag mismatch, retry
                    await asyncio.sleep(0.01)
                    continue
            raise RuntimeError("Failed to update status after retries")

        await asyncio.gather(
            update_status("status1"), update_status("status2"), update_status("status3")
        )

        final, _ = await manager.get_run(run_id)
        assert final["status"] in ["status1", "status2", "status3"]

    asyncio.run(_test())
