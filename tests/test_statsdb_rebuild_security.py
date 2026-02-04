import pytest
import tempfile
from pathlib import Path
from unittest.mock import MagicMock
from swarm.runtime.statsdb.rebuild import rebuild_stats_db, StatsDBRebuildMixin
from swarm.runtime.db import StatsDB

def test_statsdb_rebuild_path_validation(tmp_path):
    """Test that StatsDB rebuild validates run_id against path traversal."""
    # We can use StatsDB since it inherits from StatsDBRebuildMixin
    # or we can mock it. Using StatsDB is cleaner if we can skip actual DB init.
    # StatsDB(db_path=None) uses in-memory DB which is fine.

    db = StatsDB(db_path=None)

    # traversal sequences should raise ValueError
    with pytest.raises(ValueError, match="run_id"):
        db.rebuild_from_events("../etc/passwd", runs_dir=tmp_path)

    with pytest.raises(ValueError, match="run_id"):
        db.rebuild_from_events("..", runs_dir=tmp_path)

    with pytest.raises(ValueError, match="run_id"):
        db.rebuild_from_events("foo/bar", runs_dir=tmp_path)

def test_rebuild_stats_db_path_validation(tmp_path):
    """Test that rebuild_stats_db validates run_ids against path traversal."""

    # rebuild_stats_db catches exceptions and adds them to the error list

    result = rebuild_stats_db(runs_dir=tmp_path, run_ids=["../etc/passwd"], db_path=None)
    assert len(result["errors"]) == 1
    assert "run_id" in result["errors"][0]["error"]
    assert "../etc/passwd" in result["errors"][0]["run_id"]

    result = rebuild_stats_db(runs_dir=tmp_path, run_ids=["foo/bar"], db_path=None)
    assert len(result["errors"]) == 1
    assert "run_id" in result["errors"][0]["error"]
    assert "foo/bar" in result["errors"][0]["run_id"]
