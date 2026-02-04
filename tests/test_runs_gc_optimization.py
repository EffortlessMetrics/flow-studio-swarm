import unittest
from unittest.mock import MagicMock, patch, call
from pathlib import Path
import sys
from dataclasses import replace

# Adjust path if necessary, though swarm.tools should be importable
from swarm.tools import runs_gc
from swarm.tools.runs_gc import RunInfo

class TestRunsGCOptimization(unittest.TestCase):
    def setUp(self):
        # Setup common mocks
        self.mock_runs_dir_patcher = patch('swarm.tools.runs_gc.RUNS_DIR')
        self.mock_runs_dir = self.mock_runs_dir_patcher.start()
        self.mock_runs_dir.exists.return_value = True

        self.mock_examples_dir_patcher = patch('swarm.tools.runs_gc.EXAMPLES_DIR')
        self.mock_examples_dir = self.mock_examples_dir_patcher.start()
        self.mock_examples_dir.exists.return_value = False

    def tearDown(self):
        self.mock_runs_dir_patcher.stop()
        self.mock_examples_dir_patcher.stop()

    def test_discover_all_runs_computes_size_by_default(self):
        """Verify that discover_all_runs currently calls get_dir_size."""
        with patch('swarm.tools.runs_gc.get_dir_size') as mock_size:
            mock_size.return_value = 1024

            # Mock a run directory
            mock_run = MagicMock()
            mock_run.is_dir.return_value = True
            mock_run.name = "run_1"
            self.mock_runs_dir.iterdir.return_value = [mock_run]

            # Mock meta file existence
            mock_meta = MagicMock()
            mock_meta.exists.return_value = True
            mock_run.__truediv__.return_value = mock_meta

            # Mock open for meta file
            with patch('builtins.open', unittest.mock.mock_open(read_data='{"tags": []}')):
                runs = runs_gc.discover_all_runs()

            self.assertEqual(len(runs), 1)
            self.assertTrue(mock_size.called)
            self.assertEqual(runs[0].size_bytes, 1024)

    def test_discover_all_runs_skips_size_when_requested(self):
        """Verify that discover_all_runs(compute_size=False) skips get_dir_size."""
        with patch('swarm.tools.runs_gc.get_dir_size') as mock_size:
            # Mock a run directory
            mock_run = MagicMock()
            mock_run.is_dir.return_value = True
            mock_run.name = "run_1"
            self.mock_runs_dir.iterdir.return_value = [mock_run]

            # Mock meta file existence
            mock_meta = MagicMock()
            mock_meta.exists.return_value = True
            mock_run.__truediv__.return_value = mock_meta

            # Mock open for meta file
            with patch('builtins.open', unittest.mock.mock_open(read_data='{"tags": []}')):
                runs = runs_gc.discover_all_runs(compute_size=False)

            self.assertEqual(len(runs), 1)
            mock_size.assert_not_called()
            self.assertEqual(runs[0].size_bytes, 0)

    def test_get_run_info_respects_compute_size(self):
        """Verify get_run_info respects compute_size argument."""
        with patch('swarm.tools.runs_gc.get_dir_size') as mock_size:
            mock_size.return_value = 2048
            path = MagicMock()
            path.__truediv__.return_value.exists.return_value = False

            # compute_size=True (default)
            info = runs_gc.get_run_info("run_id", path, "active")
            mock_size.assert_called_with(path)
            self.assertEqual(info.size_bytes, 2048)

            mock_size.reset_mock()

            # compute_size=False
            info = runs_gc.get_run_info("run_id", path, "active", compute_size=False)
            mock_size.assert_not_called()
            self.assertEqual(info.size_bytes, 0)

    def test_prune_optimizes_size_calculation(self):
        """Verify cmd_prune calculates size ONLY for deleted runs."""
        # Setup mocks for cmd_prune
        args = MagicMock()
        args.days = 30
        args.keep = 100
        args.dry_run = True
        args.force = False
        args.verbose = False

        # Mock get_retention_days/etc
        with patch('swarm.tools.runs_gc.get_retention_days', return_value=30), \
             patch('swarm.tools.runs_gc.get_max_count', return_value=100), \
             patch('swarm.tools.runs_gc.is_retention_enabled', return_value=True), \
             patch('swarm.tools.runs_gc.discover_all_runs') as mock_discover, \
             patch('swarm.tools.runs_gc.get_dir_size') as mock_size, \
             patch('swarm.tools.runs_gc.should_preserve_run', return_value=(False, "")):

            # Setup runs: 1 old run (should be deleted), 1 new run (kept)
            # Old run needs age > 30 days
            from datetime import datetime, timezone, timedelta
            now = datetime.now(timezone.utc)

            run_old = MagicMock(spec=RunInfo)
            run_old.run_id = "old_run"
            run_old.path = Path("/path/old")
            run_old.age_days = 31
            run_old.size_bytes = 0 # Initial size
            run_old.mtime = now - timedelta(days=31)

            run_new = MagicMock(spec=RunInfo)
            run_new.run_id = "new_run"
            run_new.path = Path("/path/new")
            run_new.age_days = 1
            run_new.size_bytes = 0 # Initial size
            run_new.mtime = now - timedelta(days=1)

            # return copies because cmd_prune modifies them? no, it appends to lists.
            # But it modifies size_bytes.
            mock_discover.return_value = [run_old, run_new]

            mock_size.return_value = 500

            runs_gc.cmd_prune(args)

            # verify discover called with compute_size=False
            mock_discover.assert_called_with(compute_size=False)

            # verify get_dir_size called ONLY for old run
            mock_size.assert_called_once_with(run_old.path)

            # verify size was updated
            self.assertEqual(run_old.size_bytes, 500)
            self.assertEqual(run_new.size_bytes, 0) # Should verify it wasn't updated

    def test_quarantine_skips_size_calculation(self):
        """Verify cmd_quarantine skips size calculation."""
        args = MagicMock()
        args.dry_run = True

        with patch('swarm.tools.runs_gc.discover_all_runs') as mock_discover:
            mock_discover.return_value = []

            runs_gc.cmd_quarantine(args)

            mock_discover.assert_called_with(compute_size=False)
