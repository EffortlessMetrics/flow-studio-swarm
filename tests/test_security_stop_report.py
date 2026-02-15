import pytest
from pathlib import Path
import json
import asyncio
from swarm.api.services.run_state import RunStateManager
from swarm.api.routes.runs_control import stop_run, StopRequest
from swarm.api.routes import runs_control

# Use the inner async function runner pattern for stability in this environment
def run_async(coro):
    return asyncio.run(coro)

def test_stop_report_xss_vulnerability_repro(tmp_path):
    async def _test():
        # Setup
        runs_root = tmp_path / "runs"
        runs_root.mkdir()
        state_manager = RunStateManager(runs_root)

        # Create a run
        await state_manager.create_run(flow_id="test-flow", run_id="test-run")
        await state_manager.update_run("test-run", {"status": "running"})

        # Patch get_state_manager
        original_get_state_manager = runs_control.get_state_manager
        runs_control.get_state_manager = lambda: state_manager

        try:
            # Malicious inputs
            malicious_reason = "<script>alert('XSS')</script>"

            # Call stop_run
            request = StopRequest(reason=malicious_reason)
            await stop_run("test-run", request, if_match=None)

            # Verify stop report content
            report_path = runs_root / "test-run" / "stop_report.md"
            assert report_path.exists()

            content = report_path.read_text()

            # Vulnerability check: The script tag should be escaped
            assert malicious_reason not in content
            assert "&lt;script&gt;alert(&#x27;XSS&#x27;)&lt;/script&gt;" in content

        finally:
            runs_control.get_state_manager = original_get_state_manager

    run_async(_test())
