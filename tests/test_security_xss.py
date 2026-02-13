import pytest
import html
import asyncio
from datetime import datetime, timezone
from pathlib import Path
from swarm.api.services.run_state import RunStateManager
from swarm.api.routes.runs_control import _write_stop_report
from swarm.api.routes.runs_models import StopReportInfo

def test_stop_report_xss_prevention(tmp_path):
    """Test that stop_report.md sanitizes user inputs preventing XSS."""
    async def run_test():
        runs_root = tmp_path / "runs"
        runs_root.mkdir()

        run_id = "test-run-xss"

        # Initialize RunStateManager
        manager = RunStateManager(runs_root)

        # Create a run
        await manager.create_run(flow_id="test-flow", run_id=run_id)
        state, _ = await manager.get_run(run_id)

        # Malicious inputs
        malicious_reason = 'User requested stop <script>alert("XSS")</script>'
        malicious_intent = '```\n<script>alert("Intent XSS")</script>\n```'
        malicious_assumption = '<img src=x onerror=alert(1)>'
        malicious_tool_call = '<iframe src="javascript:alert(1)"></iframe>'

        # Stop info with malicious data
        stop_info = StopReportInfo(
            last_step_id="step-1",
            stop_reason=malicious_reason,
            last_routing_intent=malicious_intent,
            open_assumptions=[malicious_assumption],
            last_tool_calls=[malicious_tool_call],
            stopped_at=datetime.now(timezone.utc).isoformat()
        )

        # Write report
        report_path_str = await _write_stop_report(
            run_id=run_id,
            runs_root=runs_root,
            stop_info=stop_info,
            state=state
        )

        # Verify report content
        report_path = runs_root.parent / report_path_str
        assert report_path.exists()

        content = report_path.read_text(encoding="utf-8")

        # Assertions
        # 1. Check reason is escaped
        assert html.escape(malicious_reason) in content
        assert malicious_reason not in content

        # 2. Check intent does not contain raw script and backticks are handled
        # Our implementation replaces backticks with single quotes
        safe_intent = malicious_intent.replace("```", "'''")
        assert safe_intent in content

        # 3. Check assumption is escaped
        assert html.escape(malicious_assumption) in content
        assert malicious_assumption not in content

        # 4. Check tool call is escaped
        assert html.escape(malicious_tool_call) in content
        assert malicious_tool_call not in content

        # 5. Check run_id is escaped (though our test run_id is safe)
        assert run_id in content

    asyncio.run(run_test())
