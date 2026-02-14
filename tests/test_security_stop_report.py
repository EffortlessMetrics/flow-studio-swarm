import pytest
import asyncio
import html
from pathlib import Path
from swarm.api.routes.runs_control import _write_stop_report
from swarm.api.routes.runs_models import StopReportInfo

def test_write_stop_report_sanitization(tmp_path):
    """Test that stop report sanitizes user input."""

    run_id = "test-run"
    runs_root = tmp_path / "runs"
    runs_root.mkdir()
    (runs_root / run_id).mkdir()

    # Malicious inputs
    malicious_reason = "<script>alert('xss')</script>"
    malicious_intent = "Normal intent\n```\n<script>alert(1)</script>\n```"

    malicious_tool = "tool` && rm -rf /"
    malicious_assumption = "**Bold** and <img src=x onerror=alert(1)>"

    stop_info = StopReportInfo(
        last_step_id="step-1",
        last_routing_intent=malicious_intent,
        last_tool_calls=[malicious_tool],
        open_assumptions=[malicious_assumption],
        stop_reason=malicious_reason,
        stopped_at="2023-10-27T10:00:00Z"
    )

    state = {
        "flow_id": "test-flow",
        "status": "stopping",
        "completed_steps": [],
        "pending_steps": []
    }

    async def run_test():
        report_path_str = await _write_stop_report(run_id, runs_root, stop_info, state)

        report_path = runs_root.parent / report_path_str
        content = report_path.read_text()

        print("\n--- Report Content ---\n")
        print(content)
        print("\n----------------------\n")

        # 1. Reason should be HTML escaped
        assert "<script>" not in content
        assert html.escape(malicious_reason) in content

        # 2. Tool calls should have backticks replaced and then HTML escaped
        # "tool` && rm -rf /" -> "tool' && rm -rf /" -> escaped
        expected_tool = html.escape("tool' && rm -rf /")
        assert expected_tool in content
        assert "`tool`" not in content

        # 3. Assumptions should be HTML escaped
        assert "<img" not in content
        assert html.escape(malicious_assumption) in content

        # 4. Routing intent should not break code block and be escaped
        assert "```" in content
        # The intent contained ``` so it should be replaced by ''' or similar, then escaped
        # "Normal intent\n'''\n<script>alert(1)</script>\n'''" -> escaped
        expected_intent_part = html.escape("'''")
        assert expected_intent_part in content
        assert html.escape("<script>alert(1)</script>") in content

    asyncio.run(run_test())
