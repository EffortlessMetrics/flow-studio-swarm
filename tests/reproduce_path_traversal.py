
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
from swarm.runtime.statsdb.rebuild import StatsDBRebuildMixin

class MockDB(StatsDBRebuildMixin):
    def ingest_events(self, events, run_id):
        return len(events)

def test_rebuild_path_traversal(tmp_path):
    """Verify that rebuild_from_events allows path traversal if run_id is not validated."""

    # Setup directories
    runs_dir = tmp_path / "runs"
    runs_dir.mkdir()

    # Create a "secret" file outside runs_dir
    secret_dir = tmp_path / "secrets"
    secret_dir.mkdir()
    secret_file = secret_dir / "events.jsonl"
    secret_file.write_text('{"event": "secret_leaked", "seq": 1}\n')

    # Initialize Mixin
    db = MockDB()

    # Attack payload: run_id that traverses out of runs_dir into secrets
    # effectively: runs_dir / "../secrets"
    traversal_run_id = "../secrets"

    # Execute rebuild
    result = db.rebuild_from_events(traversal_run_id, runs_dir=runs_dir)

    # Verification: accessing "events.jsonl" in secrets dir should succeed
    # confirming the traversal
    assert result["success"] is True
    assert result["events_ingested"] == 1

if __name__ == "__main__":
    # Manually run the test function with a temp dir
    import shutil
    import tempfile

    tmp = Path(tempfile.mkdtemp())
    try:
        test_rebuild_path_traversal(tmp)
        print("Vulnerability confirmed: Path traversal succeeded.")
    finally:
        shutil.rmtree(tmp)
