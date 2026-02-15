import asyncio
import tempfile
import shutil
from pathlib import Path
from typing import Any, Dict
import html

# Remove pytest-asyncio dependency to avoid CI issues
import pytest
from swarm.api.routes.runs_control import _write_stop_report
from swarm.api.routes.runs_models import StopReportInfo

def test_write_stop_report_sanitization():
    """Verify that _write_stop_report sanitizes inputs to prevent Markdown/HTML injection."""

    async def run_test():
        # Create a temporary directory for runs
        with tempfile.TemporaryDirectory() as temp_dir:
            runs_root = Path(temp_dir)
            run_id = "test-run-sanitization"
            (runs_root / run_id).mkdir(parents=True)

            # Malicious content
            malicious_reason = "User<script>alert('xss')</script>"
            malicious_intent = "```\nprint('pwned')\n```"
            malicious_tool_call = "rm -rf /`whoami`"
            malicious_assumption = "User assumes <bold>validity</bold>"

            stop_info = StopReportInfo(
                last_step_id="step-1",
                last_routing_intent=malicious_intent,
                stop_reason=malicious_reason,
                last_tool_calls=[malicious_tool_call],
                open_assumptions=[malicious_assumption],
                stopped_at="2023-01-01T00:00:00Z"
            )

            state: Dict[str, Any] = {
                "flow_id": "flow-1",
                "status": "stopping",
                "current_step": "step-1"
            }

            # Generate report
            report_path_str = await _write_stop_report(run_id, runs_root, stop_info, state)

            # Read the generated report
            report_path = runs_root.parent / report_path_str
            content = report_path.read_text(encoding="utf-8")

            # 1. Check reason sanitization (HTML escaping)
            escaped_reason = html.escape(malicious_reason)
            assert escaped_reason in content, "Reason should be HTML escaped"
            assert malicious_reason not in content, "Raw reason should not be present"

            # 2. Check intent sanitization (backtick removal/replacement)
            assert malicious_intent not in content, "Raw intent with backticks should not be present"
            assert "print('pwned')" in content, "Intent content should be preserved"

            # 3. Check assumption sanitization
            escaped_assumption = html.escape(malicious_assumption)
            assert escaped_assumption in content, "Assumption should be HTML escaped"
            assert malicious_assumption not in content, "Raw assumption should not be present"

    # Run the async test function synchronously
    asyncio.run(run_test())

if __name__ == "__main__":
    test_write_stop_report_sanitization()
