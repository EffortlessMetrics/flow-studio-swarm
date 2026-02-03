
import sys
from unittest.mock import MagicMock, patch
from pathlib import Path
import pytest

# Add repo root to path
sys.path.insert(0, ".")

from swarm.tools import runs_gc

def test_discover_runs_calculates_size_by_default():
    """Verify that discovery calculates size by default (for list command)."""

    mock_run_path = MagicMock(spec=Path)
    mock_run_path.name = "run-123"
    mock_run_path.is_dir.return_value = True
    # mock stat for mtime
    mock_stat = MagicMock()
    mock_stat.st_mtime = 1600000000
    mock_run_path.stat.return_value = mock_stat

    # Mock META_FILE existence (false -> legacy run)
    (mock_run_path / runs_gc.META_FILE).exists.return_value = False

    with patch("swarm.tools.runs_gc.RUNS_DIR") as mock_runs_dir, \
         patch("swarm.tools.runs_gc.EXAMPLES_DIR") as mock_examples_dir, \
         patch("swarm.tools.runs_gc.get_dir_size") as mock_get_dir_size:

        mock_runs_dir.exists.return_value = True
        mock_runs_dir.iterdir.return_value = [mock_run_path]
        mock_examples_dir.exists.return_value = False

        # Run discovery
        runs = runs_gc.discover_all_runs()

        assert len(runs) == 1
        # Currently, get_dir_size is called
        mock_get_dir_size.assert_called_once_with(mock_run_path)


def test_prune_does_not_calculate_size_during_discovery():
    """Verify that pruning does not trigger expensive size calculation for all runs."""

    mock_run_path = MagicMock(spec=Path)
    mock_run_path.name = "run-123"
    mock_run_path.is_dir.return_value = True
    # mock stat for mtime
    mock_stat = MagicMock()
    mock_stat.st_mtime = 1600000000
    mock_run_path.stat.return_value = mock_stat

    # Mock META_FILE existence (false -> legacy run)
    (mock_run_path / runs_gc.META_FILE).exists.return_value = False

    with patch("swarm.tools.runs_gc.RUNS_DIR") as mock_runs_dir, \
         patch("swarm.tools.runs_gc.EXAMPLES_DIR") as mock_examples_dir, \
         patch("swarm.tools.runs_gc.get_dir_size") as mock_get_dir_size:

        mock_runs_dir.exists.return_value = True
        mock_runs_dir.iterdir.return_value = [mock_run_path]
        mock_examples_dir.exists.return_value = False

        # Run discovery with compute_size=False (what prune uses)
        runs = runs_gc.discover_all_runs(compute_size=False)

        assert len(runs) == 1
        # It should NOT be called
        mock_get_dir_size.assert_not_called()

        # And size_bytes should be 0
        assert runs[0].size_bytes == 0

def test_cmd_prune_calculates_size_for_deleted_items():
    """Verify that cmd_prune calculates size only for deleted items."""

    # Mock RunInfo to be returned by discover_all_runs
    mock_run = MagicMock()
    mock_run.run_id = "run-1"
    mock_run.path = Path("/tmp/run-1")
    mock_run.age_days = 100 # Older than default retention
    mock_run.size_bytes = 0 # Initially 0
    mock_run.run_type = "legacy"
    mock_run.tags = []

    # Mock mtime for sorting
    mock_run.mtime = MagicMock()

    with patch("swarm.tools.runs_gc.discover_all_runs", return_value=[mock_run]) as mock_discover, \
         patch("swarm.tools.runs_gc.should_preserve_run", return_value=(False, "")), \
         patch("swarm.tools.runs_gc.get_dir_size", return_value=1024) as mock_get_dir_size, \
         patch("swarm.tools.runs_gc.shutil.rmtree"), \
         patch("swarm.tools.runs_gc.get_retention_days", return_value=30), \
         patch("swarm.tools.runs_gc.get_max_count", return_value=100), \
         patch("swarm.tools.runs_gc.is_retention_enabled", return_value=True):

         args = MagicMock()
         args.dry_run = False
         args.days = None
         args.keep = None
         args.force = False

         runs_gc.cmd_prune(args)

         # Verify discover called with compute_size=False
         mock_discover.assert_called_with(compute_size=False)

         # Verification that size was computed for the deleted run
         mock_get_dir_size.assert_called_with(mock_run.path)
         assert mock_run.size_bytes == 1024
