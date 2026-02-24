import datetime
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add the repository root to sys.path to ensure imports work
sys.path.insert(0, str(Path(__file__).parent.parent))

from swarm.tools import runs_gc


def test_discover_all_runs_skips_size_computation():
    """Verify that discover_all_runs skips size computation when compute_size=False."""

    # Mock directories
    mock_runs_dir = MagicMock(spec=Path)
    mock_examples_dir = MagicMock(spec=Path)

    # Setup mock runs
    # Run 1: Active run with meta.json
    run1 = MagicMock(spec=Path)
    run1.name = "run-1"
    run1.is_dir.return_value = True
    run1.stat.return_value.st_mtime = datetime.datetime.now().timestamp()
    (run1 / "meta.json").exists.return_value = True

    # Run 2: Legacy run without meta.json
    run2 = MagicMock(spec=Path)
    run2.name = "run-2"
    run2.is_dir.return_value = True
    run2.stat.return_value.st_mtime = datetime.datetime.now().timestamp()
    (run2 / "meta.json").exists.return_value = False

    mock_runs_dir.exists.return_value = True
    mock_runs_dir.iterdir.return_value = [run1, run2]

    mock_examples_dir.exists.return_value = False

    # Patch dependencies
    with patch("swarm.tools.runs_gc.RUNS_DIR", mock_runs_dir), \
         patch("swarm.tools.runs_gc.EXAMPLES_DIR", mock_examples_dir), \
         patch("swarm.tools.runs_gc.get_dir_size") as mock_get_dir_size:

        # Test compute_size=False
        runs = runs_gc.discover_all_runs(compute_size=False)

        assert len(runs) == 2
        mock_get_dir_size.assert_not_called()
        for run in runs:
            assert run.size_bytes == 0

        # Test compute_size=True
        mock_get_dir_size.reset_mock()
        runs = runs_gc.discover_all_runs(compute_size=True)
        assert mock_get_dir_size.call_count == 2
