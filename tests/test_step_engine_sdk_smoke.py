"""Optional SDK smoke test for ClaudeStepEngine.

This test verifies real SDK mode works when ANTHROPIC_API_KEY is available.
Skips automatically if the key is not set (safe for CI).

Run manually with:
    ANTHROPIC_API_KEY=sk-... uv run pytest tests/test_step_engine_sdk_smoke.py -v
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

# Add repo root to path for imports
repo_root = Path(__file__).resolve().parents[1]
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from swarm.runtime.engines import ClaudeStepEngine, StepContext
from swarm.runtime.types import RunSpec

# Skip if no API key available
pytestmark = pytest.mark.skipif(
    not os.environ.get("ANTHROPIC_API_KEY"),
    reason="ANTHROPIC_API_KEY not set - skipping SDK smoke test",
)


@pytest.fixture
def sdk_engine(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> ClaudeStepEngine:
    """Create a ClaudeStepEngine in SDK mode."""
    monkeypatch.setenv("SWARM_CLAUDE_STEP_ENGINE_MODE", "sdk")
    return ClaudeStepEngine(repo_root=tmp_path)


@pytest.fixture
def minimal_context(tmp_path: Path) -> StepContext:
    """Create a minimal StepContext for smoke testing."""
    run_spec = RunSpec(
        flow_keys=["signal"],
        profile_id=None,
        backend="claude-step-orchestrator",
        initiator="sdk-smoke-test",
        params={},
    )
    return StepContext(
        repo_root=tmp_path,
        run_id="sdk-smoke-test-run",
        flow_key="signal",
        step_id="smoke_test",
        step_index=1,
        total_steps=1,
        spec=run_spec,
        flow_title="SDK Smoke Test",
        step_role="Respond with a single word: 'OK'",
        step_agents=("test-agent",),
        history=[],
        extra={},
    )


class TestClaudeSDKSmoke:
    """Smoke tests for ClaudeStepEngine SDK mode.

    These tests make real API calls and cost tokens.
    Only run when explicitly testing SDK integration.
    """

    def test_sdk_mode_produces_receipt(
        self,
        sdk_engine: ClaudeStepEngine,
        minimal_context: StepContext,
        tmp_path: Path,
    ) -> None:
        """SDK mode writes a valid receipt with correct metadata."""
        # Create run directory structure
        run_base = tmp_path / "swarm" / "runs" / "sdk-smoke-test-run" / "signal"
        run_base.mkdir(parents=True)
        (run_base / "llm").mkdir()
        (run_base / "receipts").mkdir()

        # Execute step
        result = sdk_engine.run_step(minimal_context)

        # Verify result structure
        assert result.status in {"succeeded", "failed"}
        assert result.duration_ms >= 0

        # Check receipt was written
        receipt_path = run_base / "receipts" / "smoke_test-test-agent.json"
        assert receipt_path.exists(), "Receipt file should be created"

        # Parse and validate receipt
        import json

        with open(receipt_path) as f:
            receipt = json.load(f)

        assert receipt["engine"] == "claude-step"
        assert receipt["mode"] == "sdk", "Mode should be 'sdk' for SDK execution"
        assert receipt["provider"] in {"anthropic", "anthropic_compat"}
        assert receipt["step_id"] == "smoke_test"
        assert receipt["flow_key"] == "signal"
        assert receipt["status"] in {"succeeded", "failed"}

    def test_sdk_mode_produces_transcript(
        self,
        sdk_engine: ClaudeStepEngine,
        minimal_context: StepContext,
        tmp_path: Path,
    ) -> None:
        """SDK mode writes a valid JSONL transcript."""
        # Create run directory structure
        run_base = tmp_path / "swarm" / "runs" / "sdk-smoke-test-run" / "signal"
        run_base.mkdir(parents=True)
        (run_base / "llm").mkdir()
        (run_base / "receipts").mkdir()

        # Execute step
        sdk_engine.run_step(minimal_context)

        # Check transcript was written
        transcript_path = run_base / "llm" / "smoke_test-test-agent-claude.jsonl"
        assert transcript_path.exists(), "Transcript file should be created"

        # Parse and validate JSONL
        import json

        with open(transcript_path) as f:
            lines = [line.strip() for line in f if line.strip()]

        assert len(lines) > 0, "Transcript should have at least one message"

        for line in lines:
            msg = json.loads(line)  # Should parse as valid JSON
            assert "role" in msg, "Each message should have a role"
            assert "content" in msg, "Each message should have content"

    def test_sdk_mode_reports_tokens(
        self,
        sdk_engine: ClaudeStepEngine,
        minimal_context: StepContext,
        tmp_path: Path,
    ) -> None:
        """SDK mode receipt includes token usage."""
        # Create run directory structure
        run_base = tmp_path / "swarm" / "runs" / "sdk-smoke-test-run" / "signal"
        run_base.mkdir(parents=True)
        (run_base / "llm").mkdir()
        (run_base / "receipts").mkdir()

        # Execute step
        sdk_engine.run_step(minimal_context)

        # Load receipt and check tokens
        import json

        receipt_path = run_base / "receipts" / "smoke_test-test-agent.json"
        with open(receipt_path) as f:
            receipt = json.load(f)

        # SDK mode should report token usage
        assert "tokens" in receipt, "Receipt should include token usage"
        tokens = receipt["tokens"]
        assert tokens.get("prompt", 0) > 0 or tokens.get("total", 0) > 0, (
            "SDK mode should report non-zero token usage"
        )
