import os
import json
import time
import pytest
from pathlib import Path
from swarm.api.services.run_state import RunStateManager

class TestRunStateManagerOptimization:
    @pytest.fixture
    def manager(self, tmp_path):
        return RunStateManager(tmp_path)

    def test_list_runs_ordering_and_filtering(self, manager, tmp_path):
        """Verify list_runs sorts by mtime and skips invalid dirs."""
        
        # 1. Create older valid run
        run1 = tmp_path / "run1"
        run1.mkdir()
        (run1 / "run_state.json").write_text(json.dumps({"id": "run1", "status": "completed"}), encoding="utf-8")
        # Set mtime to 1 hour ago
        older_time = time.time() - 3600
        os.utime(run1, (older_time, older_time))

        # 2. Create newer valid run
        run2 = tmp_path / "run2"
        run2.mkdir()
        (run2 / "run_state.json").write_text(json.dumps({"id": "run2", "status": "running"}), encoding="utf-8")
        # Set mtime to now
        newer_time = time.time()
        os.utime(run2, (newer_time, newer_time))

        # 3. Create run directory WITHOUT state file (should be skipped)
        # Even if it has newest mtime
        run_invalid = tmp_path / "run_invalid"
        run_invalid.mkdir()
        os.utime(run_invalid, (newer_time + 10, newer_time + 10))

        # 4. Create run directory with state file but NEWEST (should be first)
        run3 = tmp_path / "run3"
        run3.mkdir()
        (run3 / "run_state.json").write_text(json.dumps({"id": "run3", "status": "pending"}), encoding="utf-8")
        future_time = time.time() + 60
        os.utime(run3, (future_time, future_time))

        # Run list_runs
        runs = manager.list_runs(limit=10)

        # Expect: run3 (newest), run2 (now), run1 (old). run_invalid skipped.
        assert len(runs) == 3
        assert runs[0]["id"] == "run3"
        assert runs[1]["id"] == "run2"
        assert runs[2]["id"] == "run1"

    def test_list_runs_limit(self, manager, tmp_path):
        """Verify limit works with filtering."""
        
        # Create 5 valid runs
        for i in range(5):
            d = tmp_path / f"run{i}"
            d.mkdir()
            (d / "run_state.json").write_text(json.dumps({"id": f"run{i}"}), encoding="utf-8")
            # Ensure distinct mtimes
            t = time.time() - (i * 10)
            os.utime(d, (t, t))
            
        # Create invalid dir in between
        inv = tmp_path / "invalid"
        inv.mkdir()
        t = time.time() - 5 # between run0 and run1
        os.utime(inv, (t, t))

        runs = manager.list_runs(limit=2)
        assert len(runs) == 2
        # sorted by mtime descending (run0 is newest)
        assert runs[0]["id"] == "run0"
        assert runs[1]["id"] == "run1"
