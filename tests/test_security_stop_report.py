import pytest
from pathlib import Path
from swarm.api.routes.runs_control import _write_stop_report
from swarm.api.routes.runs_models import StopReportInfo

@pytest.mark.anyio
async def test_stop_report_sanitization(tmp_path: Path):
    """Test that stop report content is correctly sanitized to prevent XSS/Markdown injection."""
    run_id = "test-run-1"
    runs_root = tmp_path / "runs"
    runs_root.mkdir()
    (runs_root / run_id).mkdir()

    # Malicious inputs
    malicious_reason = "<script>alert('xss')</script>"
    malicious_flow_id = "flow-1 <bold>"
    malicious_intent = "```\nprint('hack')\n```"

    stop_info = StopReportInfo(
        last_step_id="step-1",
        last_routing_intent=malicious_intent,
        stop_reason=malicious_reason,
        stopped_at="2023-01-01T00:00:00Z"
    )

    state = {
        "flow_id": malicious_flow_id,
        "status": "stopped",
        "context": {}
    }

    report_path_str = await _write_stop_report(run_id, runs_root, stop_info, state)
    report_path = runs_root.parent / report_path_str

    content = report_path.read_text(encoding="utf-8")

    # Verify fix: content IS escaped
    # html.escape escapes ' to &#x27; by default in newer Python versions
    assert "&lt;script&gt;alert(&#x27;xss&#x27;)&lt;/script&gt;" in content
    assert malicious_reason not in content

    assert "flow-1 &lt;bold&gt;" in content
    assert malicious_flow_id not in content

    # Verify backticks are replaced to prevent breakout
    assert "'''\nprint('hack')\n'''" in content
    assert malicious_intent not in content
