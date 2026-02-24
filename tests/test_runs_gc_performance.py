
import os
import shutil
import sys
import time
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add repo root to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from swarm.tools import runs_gc

@pytest.fixture
def temp_runs_dir(tmp_path):
    runs_dir = tmp_path / "runs"
    runs_dir.mkdir()
    return runs_dir

@pytest.fixture
def temp_examples_dir(tmp_path):
    examples_dir = tmp_path / "examples"
    examples_dir.mkdir()
    return examples_dir

def create_dummy_run(runs_dir, run_id, size_bytes=100):
    run_path = runs_dir / run_id
    run_path.mkdir()
    (run_path / "meta.json").write_text("{}")
    (run_path / "data.txt").write_text("x" * size_bytes)
    return run_path

def test_discover_all_runs_compute_size_default(temp_runs_dir, temp_examples_dir):
    create_dummy_run(temp_runs_dir, "run-1", size_bytes=1024)

    with patch("swarm.tools.runs_gc.RUNS_DIR", temp_runs_dir), \
         patch("swarm.tools.runs_gc.EXAMPLES_DIR", temp_examples_dir):

        runs = runs_gc.discover_all_runs()
        assert len(runs) == 1
        assert runs[0].size_bytes >= 1024
        assert runs[0].run_id == "run-1"

def test_discover_all_runs_skip_compute_size(temp_runs_dir, temp_examples_dir):
    create_dummy_run(temp_runs_dir, "run-1", size_bytes=1024)

    with patch("swarm.tools.runs_gc.RUNS_DIR", temp_runs_dir), \
         patch("swarm.tools.runs_gc.EXAMPLES_DIR", temp_examples_dir):

        runs = runs_gc.discover_all_runs(compute_size=False)
        assert len(runs) == 1
        assert runs[0].size_bytes == -1

def test_prune_skips_size_computation_initially(temp_runs_dir, temp_examples_dir):
    # create 10 runs
    for i in range(10):
        create_dummy_run(temp_runs_dir, f"run-{i}", size_bytes=100)

    with patch("swarm.tools.runs_gc.RUNS_DIR", temp_runs_dir), \
         patch("swarm.tools.runs_gc.EXAMPLES_DIR", temp_examples_dir), \
         patch("swarm.tools.runs_gc.discover_all_runs", wraps=runs_gc.discover_all_runs) as mock_discover:

        args = MagicMock()
        args.dry_run = True
        args.keep = 5
        args.days = 0
        args.force = True

        runs_gc.cmd_prune(args)

        # Verify it was called with compute_size=False
        mock_discover.assert_called_with(compute_size=False)

def test_quarantine_skips_size_computation(temp_runs_dir, temp_examples_dir):
    create_dummy_run(temp_runs_dir, "run-corrupt", size_bytes=100)
    # make it corrupt (mocking get_run_info or just relying on implementation details)
    # runs_gc checks corrupt by loading meta.json. If it's empty, it might fail to parse and become corrupt?
    # get_run_info: try json.load. If fails, is_corrupt=True.

    (temp_runs_dir / "run-corrupt" / "meta.json").write_text("{invalid json")

    with patch("swarm.tools.runs_gc.RUNS_DIR", temp_runs_dir), \
         patch("swarm.tools.runs_gc.EXAMPLES_DIR", temp_examples_dir), \
         patch("swarm.tools.runs_gc.discover_all_runs", wraps=runs_gc.discover_all_runs) as mock_discover:

        args = MagicMock()
        args.dry_run = True

        runs_gc.cmd_quarantine(args)

        mock_discover.assert_called_with(compute_size=False)
