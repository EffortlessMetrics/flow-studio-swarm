
import sys
import os
from pathlib import Path
import pytest
import shutil

# Ensure we can import swarm
sys.path.append(os.getcwd())
try:
    from swarm.api.routes.runs_control import _write_stop_report
    from swarm.api.routes.runs_models import StopReportInfo
except ImportError:
    # If ran from wrong directory
    sys.path.append(str(Path(__file__).parent.parent))
    from swarm.api.routes.runs_control import _write_stop_report
    from swarm.api.routes.runs_models import StopReportInfo

@pytest.mark.anyio
async def test_write_stop_report_security():
    """
    Verify that _write_stop_report properly escapes user inputs to prevent
    Markdown injection and Stored XSS.
    """
    # Setup
    runs_root = Path("./test_runs_security")
    if runs_root.exists():
        shutil.rmtree(runs_root)
    runs_root.mkdir(parents=True, exist_ok=True)

    run_id = "test_run_security"
    (runs_root / run_id).mkdir(exist_ok=True)

    # Malicious content
    malicious_intent = "```\n<script>alert('XSS')</script>\n```"
    malicious_tool_call = "` rm -rf /"
    malicious_assumption = "<script>alert('Assumption')</script>"
    malicious_reason = "**bold** <script>"

    stop_info = StopReportInfo(
        last_step_id="step_1",
        last_routing_intent=malicious_intent,
        last_tool_calls=[malicious_tool_call],
        open_assumptions=[malicious_assumption],
        stop_reason=malicious_reason,
        stopped_at="2023-01-01T00:00:00Z",
    )

    state = {
        "flow_id": "test_flow",
        "status": "stopped",
        "completed_steps": [],
        "pending_steps": [],
    }

    # Execute
    report_path_str = await _write_stop_report(
        run_id=run_id,
        runs_root=runs_root,
        stop_info=stop_info,
        state=state,
    )

    # report_path_str is relative to runs_root.parent, which is "." in this case
    report_path = Path(report_path_str)
    content = report_path.read_text()

    print("\n--- Generated Report Content ---\n")
    print(content)
    print("\n--------------------------------\n")

    # Verify Intent Escaping
    # Should use 4 backticks because input has 3
    assert "````" in content
    assert malicious_intent in content # The content itself should be there
    # But it should be wrapped in delimiters
    expected_intent_block = "````\n" + malicious_intent + "\n````"
    assert expected_intent_block in content

    # Verify Tool Call Escaping
    # Should be wrapped in double backticks
    assert "`` ` rm -rf / ``" in content

    # Verify Assumption Escaping
    # Should be HTML escaped (including quotes)
    expected_assumption = "&lt;script&gt;alert(&#x27;Assumption&#x27;)&lt;/script&gt;"
    assert expected_assumption in content
    assert "<script>" not in content.split("Open Assumptions/Decisions")[1]

    # Verify Reason Escaping
    assert "&lt;script&gt;" in content
    # Note: html.escape does not escape markdown characters like *, so **bold** remains **bold**
    # But <script> becomes &lt;script&gt;

    # Cleanup
    shutil.rmtree(runs_root)

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_write_stop_report_security())
