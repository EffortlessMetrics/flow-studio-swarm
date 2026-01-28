
    def test_list_runs_paginated_returns_total_and_slice(self, tmp_path, monkeypatch):
        """Paginated listing should return total count and requested slice."""
        RunService.reset()
        service = RunService.get_instance(tmp_path)

        now = datetime.now(timezone.utc)

        # Create 5 runs with IDs that sort lexicographically
        run_ids = []
        for i in range(5):
            run_id = f"run-20260120-{100000 + i:06d}-aaaaaa"
            run_ids.append(run_id)
            summary = RunSummary(
                id=run_id,
                spec=RunSpec(flow_keys=["signal"], backend="claude-harness", initiator="test"),
                status=RunStatus.SUCCEEDED,
                sdlc_status=SDLCStatus.OK,
                created_at=now,
                updated_at=now,
            )
            storage.write_summary(run_id, summary, runs_dir=tmp_path)

        # Inject garbage
        potential_ids = run_ids + ["garbage-1", "garbage-2"]

        # Mock storage functions to use only our test runs
        monkeypatch.setattr(storage, "list_runs", lambda runs_dir=None: run_ids)
        monkeypatch.setattr(storage, "list_potential_runs", lambda runs_dir=None: potential_ids)
        monkeypatch.setattr(storage, "run_exists", lambda rid, runs_dir=None: rid in run_ids)
        monkeypatch.setattr(storage, "is_legacy_run", lambda rid, runs_dir=None: False)
        monkeypatch.setattr(storage, "discover_example_runs", lambda: [])
        monkeypatch.setattr(storage, "discover_legacy_runs", lambda runs_dir=None: [])
        monkeypatch.setattr(storage, "scan_runs", lambda runs_dir=None: (run_ids, []))
        # Also patch read_summary to use our tmp_path
        orig_read_summary = storage.read_summary
        monkeypatch.setattr(
            storage,
            "read_summary",
            lambda rid, runs_dir=None: orig_read_summary(rid, runs_dir=tmp_path),
        )

        # Get first page (limit=2, offset=0)
        runs, total = service.list_runs_paginated(limit=2, offset=0)
        # Total should include garbage (overestimation)
        assert total == 7
        assert len(runs) == 2

        # Get second page (limit=2, offset=2)
        runs, total = service.list_runs_paginated(limit=2, offset=2)
        assert total == 7
        assert len(runs) == 2

        # Get last page (limit=2, offset=4)
        runs, total = service.list_runs_paginated(limit=2, offset=4)
        assert total == 7
        assert len(runs) == 1  # Only one run remaining

        RunService.reset()
