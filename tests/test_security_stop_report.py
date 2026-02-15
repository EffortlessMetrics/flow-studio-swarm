import asyncio
import shutil
import tempfile
from pathlib import Path
from swarm.api.routes.runs_control import _write_stop_report
from swarm.api.routes.runs_models import StopReportInfo

def test_write_stop_report_sanitization():
    """Test that stop report sanitizes user input."""
    temp_dir = tempfile.mkdtemp()
    runs_root = Path(temp_dir)

    async def run_test():
        run_id = "test-run-xss"

        # Create run directory
        run_dir = runs_root / run_id
        run_dir.mkdir(parents=True)

        # malicious inputs
        malicious_reason = "<script>alert('xss')</script>"

        stop_info = StopReportInfo(
            last_step_id="step-1",
            last_routing_intent="intent",
            last_tool_calls=["/bin/ls"],
            open_assumptions=["<img src=x onerror=alert(1)>"],
            stop_reason=malicious_reason,
            stopped_at="2023-01-01T00:00:00Z",
        )

        state = {
            "flow_id": "flow-1",
            "status": "running",
            "completed_steps": [],
            "pending_steps": [],
        }

        await _write_stop_report(run_id, runs_root, stop_info, state)

        report_path = run_dir / "stop_report.md"
        content = report_path.read_text(encoding="utf-8")

        print(f"Content:\n{content}")

        # Assertions - these will fail if not sanitized
        if "<script>" in content:
            raise AssertionError("XSS payload found in stop report (reason)")

        if "<img" in content:
            raise AssertionError("XSS payload found in stop report (assumptions)")

    try:
        asyncio.run(run_test())
    finally:
        shutil.rmtree(temp_dir)
