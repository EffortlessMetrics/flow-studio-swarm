
import sys
import time
import shutil
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock
import tempfile
import os

# Ensure we can import swarm
sys.path.insert(0, str(Path(__file__).parent.parent))

from swarm.tools import runs_gc

class TestRunsGCPerf(unittest.TestCase):
    def setUp(self):
        self.test_dir = Path(tempfile.mkdtemp())
        self.runs_dir = self.test_dir / "runs"
        self.examples_dir = self.test_dir / "examples"
        self.runs_dir.mkdir()
        self.examples_dir.mkdir()

        # Create many fake runs
        self.num_runs = 100
        self.files_per_run = 10

        for i in range(self.num_runs):
            run_path = self.runs_dir / f"run_{i}"
            run_path.mkdir()
            # Create a meta.json
            (run_path / "meta.json").write_text('{"tags": []}')
            # Create some dummy files
            for j in range(self.files_per_run):
                (run_path / f"file_{j}.txt").write_text("x" * 1000)

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_performance_difference(self):
        # Patch the directories in runs_gc module
        with patch("swarm.tools.runs_gc.RUNS_DIR", self.runs_dir), \
             patch("swarm.tools.runs_gc.EXAMPLES_DIR", self.examples_dir):

            # Measure with compute_size=True (default)
            start_time = time.time()
            runs_full = runs_gc.discover_all_runs(compute_size=True)
            time_full = time.time() - start_time

            # Measure with compute_size=False
            start_time = time.time()
            runs_fast = runs_gc.discover_all_runs(compute_size=False)
            time_fast = time.time() - start_time

            print(f"\nTime with compute_size=True: {time_full:.4f}s")
            print(f"Time with compute_size=False: {time_fast:.4f}s")

            # Assert fast is faster (it should be, significantly)
            # We use a relaxed assertion because file system caching might affect things,
            # but usually the difference is large enough.
            # With 100 runs * 10 files, stat calls add up.
            self.assertLess(time_fast, time_full)

            # Verify correctness
            self.assertEqual(len(runs_full), self.num_runs)
            self.assertEqual(len(runs_fast), self.num_runs)

            # Check sizes
            total_size_full = sum(r.size_bytes for r in runs_full)
            total_size_fast = sum(r.size_bytes for r in runs_fast)

            self.assertGreater(total_size_full, 0)
            self.assertEqual(total_size_fast, 0)

            # Verify individual run size matches expected
            # 10 files * 1000 bytes + meta.json (~14 bytes)
            # roughly 10014 bytes per run
            self.assertGreater(runs_full[0].size_bytes, 10000)
            self.assertEqual(runs_fast[0].size_bytes, 0)

    def test_cmd_prune_logic(self):
         # Test that size is calculated for deleted items in prune
         with patch("swarm.tools.runs_gc.RUNS_DIR", self.runs_dir), \
              patch("swarm.tools.runs_gc.EXAMPLES_DIR", self.examples_dir), \
              patch("swarm.tools.runs_gc.is_retention_enabled", return_value=True), \
              patch("swarm.tools.runs_gc.get_retention_days", return_value=0), \
              patch("swarm.tools.runs_gc.get_max_count", return_value=0), \
              patch("swarm.tools.runs_gc.is_dry_run_enabled", return_value=True): # Dry run to avoid actual deletion

            # We force everything to be deleted by setting retention days to 0 and max count to 0
            # Note: runs_gc.cmd_prune sorts by mtime.

            # Mock args
            args = MagicMock()
            args.dry_run = True
            args.days = 0 # Delete everything older than 0 days (all created just now might be 0 days old)
            # RunInfo.age_days calculation uses datetime.now() - mtime.
            # Created files have current mtime, so age is ~0.
            # If we set days=-1, we ensure deletion.
            args.days = -1
            args.keep = 0
            args.force = True

            # We need to capture logging to verify "Space to free"
            with self.assertLogs("swarm.tools.runs_gc", level="INFO") as cm:
                runs_gc.cmd_prune(args)

            # Verify that "Space to free" is not "0 B" (unless runs are empty, but they are not)
            space_log = next((line for line in cm.output if "Space to free" in line), None)
            self.assertIsNotNone(space_log)
            self.assertNotIn("0 B", space_log)
            print(f"Prune log: {space_log}")

if __name__ == "__main__":
    unittest.main()
