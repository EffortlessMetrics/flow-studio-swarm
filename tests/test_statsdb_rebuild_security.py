import pytest
from pathlib import Path
from swarm.runtime.statsdb.rebuild import rebuild_stats_db, StatsDBRebuildMixin
from swarm.runtime.db import StatsDB

def test_rebuild_stats_db_traversal(tmp_path):
    """Test that rebuild_stats_db catches path traversal attempts."""
    runs_dir = tmp_path / "runs"
    runs_dir.mkdir()

    # Create a malicious "run" outside of runs_dir
    secret_dir = tmp_path / "secret"
    secret_dir.mkdir()
    (secret_dir / "events.jsonl").write_text('{"event": "test"}')

    traversal_id = "../secret"

    # Run the rebuild
    stats = rebuild_stats_db(
        runs_dir=runs_dir,
        db_path=tmp_path / "db.duckdb",
        run_ids=[traversal_id]
    )

    # Check that an error was recorded
    assert len(stats["errors"]) == 1
    assert stats["errors"][0]["run_id"] == traversal_id
    assert "run_id" in stats["errors"][0]["error"]
    assert "invalid characters" in stats["errors"][0]["error"] or "traversal sequence" in stats["errors"][0]["error"]

    # Ensure no events were ingested
    assert stats["events_ingested"] == 0


def test_mixin_rebuild_from_events_traversal(tmp_path):
    """Test that StatsDBRebuildMixin.rebuild_from_events catches path traversal attempts."""
    runs_dir = tmp_path / "runs"
    runs_dir.mkdir()

    # Create a malicious "run" outside of runs_dir
    secret_dir = tmp_path / "secret"
    secret_dir.mkdir()
    (secret_dir / "events.jsonl").write_text('{"event": "test"}')

    traversal_id = "../secret"

    # Use the mixin (mocking it or using StatsDB which inherits it)
    # StatsDB inherits StatsDBRebuildMixin
    db = StatsDB(db_path=tmp_path / "db.duckdb")

    result = db.rebuild_from_events(
        run_id=traversal_id,
        runs_dir=runs_dir
    )

    assert result["success"] is False
    assert "run_id" in result["error"]
    assert "invalid characters" in result["error"] or "traversal sequence" in result["error"]
    assert result["events_ingested"] == 0

    db.close()
