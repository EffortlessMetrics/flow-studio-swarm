import pytest
import asyncio
from pathlib import Path
from swarm.api.routes.runs_control import _write_stop_report
from swarm.api.routes.runs_models import StopReportInfo

def test_xss_repro(tmp_path):
    async def run_test():
        runs_root = tmp_path / "runs"
        runs_root.mkdir()
        run_id = "test-run"
        run_dir = runs_root / run_id
        run_dir.mkdir()

        # Payload with script tag
        xss_payload = "<script>alert('xss')</script>"
        # Payload with backticks to try breaking out of code block
        backtick_payload = "```<script>alert('breakout')</script>```"

        stop_info = StopReportInfo(
            last_step_id="step1",
            last_routing_intent=f"intent {backtick_payload}",
            last_tool_calls=[f"call {backtick_payload}"],
            open_assumptions=[f"Assumption {xss_payload}"],
            stop_reason=xss_payload,
            stopped_at="2023-01-01T00:00:00Z"
        )

        state = {
            "flow_id": "flow1",
            "status": "running"
        }

        await _write_stop_report(run_id, runs_root, stop_info, state)

        report_path = run_dir / "stop_report.md"
        content = report_path.read_text()

        print(f"\nReport content:\n{content}")

        # Verify sanitization

        # 1. Stop Reason should be HTML escaped
        # Python's html.escape escapes ' to &#x27; in 3.x
        assert "&lt;script&gt;alert(&#x27;xss&#x27;)&lt;/script&gt;" in content
        # Ensure raw payload is NOT present in the reason line
        assert f"**Reason:** {xss_payload}" not in content

        # 2. Assumptions should be HTML escaped
        assert "- Assumption &lt;script&gt;alert(&#x27;xss&#x27;)&lt;/script&gt;" in content

        # 3. Last Routing Intent should have backticks replaced
        # It is inside a code block, so backticks must be neutralized to prevent breaking out
        # My implementation replaces "```" with "'''"
        expected_intent_content = "intent '''<script>alert('breakout')</script>'''"
        assert expected_intent_content in content
        # Should not contain the original backticks
        assert f"intent {backtick_payload}" not in content

        # 4. Last Tool Calls should have backticks replaced
        # My implementation replaces "`" with "'"
        # Original: call ```<script>alert('breakout')</script>```
        # Expected: call '''<script>alert('breakout')</script>'''
        # And it is wrapped in backticks in markdown: - `...`
        expected_tool_call = "- `call '''<script>alert('breakout')</script>'''`"
        assert expected_tool_call in content

    asyncio.run(run_test())
