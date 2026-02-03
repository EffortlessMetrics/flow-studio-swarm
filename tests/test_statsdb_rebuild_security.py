import json
import tempfile
from pathlib import Path
from swarm.runtime.statsdb.rebuild import StatsDBRebuildMixin

# Create a dummy class that mixes in StatsDBRebuildMixin
class RebuildTester(StatsDBRebuildMixin):
    def ingest_events(self, events, run_id):
        # Mock ingestion
        return len(events)

def test_rebuild_traversal_blocked():
    """Test that path traversal attempts in rebuild_from_events are blocked."""

    # Setup temporary directory structure
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        runs_dir = root / "runs"
        runs_dir.mkdir()

        # Create a malicious "outside" directory
        secret_dir = root / "secret"
        secret_dir.mkdir()

        # Create a fake events.jsonl in the secret directory
        secret_events = secret_dir / "events.jsonl"
        with open(secret_events, "w") as f:
            f.write(json.dumps({"type": "secret_event", "data": "hacked"}) + "\n")

        tester = RebuildTester()

        # Attempt path traversal: run_id = "../secret" relative to runs_dir
        # This should fail validation and return an error result
        result = tester.rebuild_from_events(run_id="../secret", runs_dir=runs_dir)

        assert result["success"] is False
        assert result["events_ingested"] == 0
        assert "run_id" in result["error"] or "traversal sequence" in result["error"] or "invalid characters" in result["error"]

        # Verify legitimate run still works
        valid_run_dir = runs_dir / "valid_run"
        valid_run_dir.mkdir()
        valid_events = valid_run_dir / "events.jsonl"
        with open(valid_events, "w") as f:
            f.write(json.dumps({"type": "valid_event"}) + "\n")

        result_valid = tester.rebuild_from_events(run_id="valid_run", runs_dir=runs_dir)
        assert result_valid["success"] is True
        assert result_valid["events_ingested"] == 1
