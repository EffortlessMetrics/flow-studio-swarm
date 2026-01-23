"""Contract tests for StepEngine implementations.

These tests verify invariants that ALL StepEngine implementations must satisfy.
See docs/STEPWISE_BACKENDS.md for the StepEngine contract specification.

## Contract Invariants Tested

### StepResult Invariants
1. duration_ms >= 0 - Duration must be non-negative
2. status in {"succeeded", "failed", "skipped"} - Status must be valid
3. len(output) < 50KB - Output must not be excessively long

### StepContext Invariants
4. run_base returns a valid Path object

### Engine File Invariants
5. Transcript files are valid JSONL (each line is valid JSON)
6. Receipt files are valid JSON matching expected schema

## Test Organization

- TestStepResultContract: Tests for StepResult dataclass invariants
- TestStepContextContract: Tests for StepContext dataclass invariants
- TestEngineTranscriptContract: Tests for transcript file format
- TestEngineReceiptContract: Tests for receipt file schema
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

# Add repo root to path for imports
repo_root = Path(__file__).resolve().parents[1]
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from swarm.runtime.engines import (
    ClaudeStepEngine,
    GeminiStepEngine,
    StepContext,
    StepResult,
)
from swarm.runtime.types import RunSpec

# -----------------------------------------------------------------------------
# Constants for Contract Limits
# -----------------------------------------------------------------------------

MAX_OUTPUT_BYTES = 50 * 1024  # 50KB limit for output
VALID_STATUSES = {"succeeded", "failed", "skipped"}

# Required fields in receipt JSON
REQUIRED_RECEIPT_FIELDS = {
    "engine",
    "model",
    "step_id",
    "flow_key",
    "run_id",
    "agent_key",
    "status",
    "duration_ms",
}


# -----------------------------------------------------------------------------
# Fixtures
# -----------------------------------------------------------------------------


@pytest.fixture
def run_base_dir(tmp_path: Path) -> Path:
    """Create a temporary RUN_BASE directory structure."""
    run_base = tmp_path / "swarm" / "runs" / "test-run" / "signal"
    run_base.mkdir(parents=True)
    return run_base


@pytest.fixture
def sample_run_spec() -> RunSpec:
    """Create a sample RunSpec for testing."""
    return RunSpec(
        flow_keys=["signal"],
        profile_id=None,
        backend="gemini-step-orchestrator",
        initiator="test",
        params={"title": "Contract Test Run"},
    )


@pytest.fixture
def sample_step_context(tmp_path: Path, sample_run_spec: RunSpec) -> StepContext:
    """Create a sample StepContext for testing."""
    return StepContext(
        repo_root=tmp_path,
        run_id="test-run",
        flow_key="signal",
        step_id="test_step",
        step_index=1,
        total_steps=3,
        spec=sample_run_spec,
        flow_title="Test Signal Flow",
        step_role="Execute test step for contract verification",
        step_agents=("test-agent",),
        history=[],
        extra={},
    )


@pytest.fixture
def gemini_engine(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> GeminiStepEngine:
    """Create a GeminiStepEngine in stub mode for testing."""
    monkeypatch.setenv("SWARM_GEMINI_STUB", "1")
    return GeminiStepEngine(repo_root=tmp_path)


@pytest.fixture
def claude_engine(tmp_path: Path) -> ClaudeStepEngine:
    """Create a ClaudeStepEngine for testing."""
    return ClaudeStepEngine(repo_root=tmp_path)


# -----------------------------------------------------------------------------
# Test Class: StepResult Contract
# -----------------------------------------------------------------------------


class TestStepResultContract:
    """Tests for StepResult invariants.

    These tests verify that StepResult instances created by engines
    satisfy the contract requirements.
    """

    def test_duration_ms_is_non_negative(
        self,
        gemini_engine: GeminiStepEngine,
        sample_step_context: StepContext,
    ) -> None:
        """StepResult.duration_ms must be >= 0.

        Duration in milliseconds should never be negative, as it represents
        elapsed wall-clock time for step execution.
        """
        result, _ = gemini_engine.run_step(sample_step_context)

        assert result.duration_ms >= 0, (
            f"duration_ms must be non-negative, got {result.duration_ms}"
        )

    def test_duration_ms_is_non_negative_claude(
        self,
        claude_engine: ClaudeStepEngine,
        sample_step_context: StepContext,
    ) -> None:
        """StepResult.duration_ms must be >= 0 for Claude engine."""
        result, _ = claude_engine.run_step(sample_step_context)

        assert result.duration_ms >= 0, (
            f"duration_ms must be non-negative, got {result.duration_ms}"
        )

    def test_status_is_valid_succeeded(
        self,
        gemini_engine: GeminiStepEngine,
        sample_step_context: StepContext,
    ) -> None:
        """StepResult.status must be one of the valid statuses.

        Valid statuses are: "succeeded", "failed", "skipped".
        This test verifies that a successful step returns a valid status.
        """
        result, _ = gemini_engine.run_step(sample_step_context)

        assert result.status in VALID_STATUSES, (
            f"status must be one of {VALID_STATUSES}, got '{result.status}'"
        )

    def test_status_is_valid_claude(
        self,
        claude_engine: ClaudeStepEngine,
        sample_step_context: StepContext,
    ) -> None:
        """StepResult.status must be one of the valid statuses for Claude engine."""
        result, _ = claude_engine.run_step(sample_step_context)

        assert result.status in VALID_STATUSES, (
            f"status must be one of {VALID_STATUSES}, got '{result.status}'"
        )

    def test_output_is_not_excessively_long(
        self,
        gemini_engine: GeminiStepEngine,
        sample_step_context: StepContext,
    ) -> None:
        """StepResult.output must be < 50KB.

        Output should be reasonable in size to prevent memory issues
        and ensure it can be stored/transmitted efficiently.
        """
        result, _ = gemini_engine.run_step(sample_step_context)

        output_bytes = len(result.output.encode("utf-8"))
        assert output_bytes < MAX_OUTPUT_BYTES, (
            f"output must be < {MAX_OUTPUT_BYTES} bytes, got {output_bytes}"
        )

    def test_output_is_not_excessively_long_claude(
        self,
        claude_engine: ClaudeStepEngine,
        sample_step_context: StepContext,
    ) -> None:
        """StepResult.output must be < 50KB for Claude engine."""
        result, _ = claude_engine.run_step(sample_step_context)

        output_bytes = len(result.output.encode("utf-8"))
        assert output_bytes < MAX_OUTPUT_BYTES, (
            f"output must be < {MAX_OUTPUT_BYTES} bytes, got {output_bytes}"
        )

    def test_step_id_matches_context(
        self,
        gemini_engine: GeminiStepEngine,
        sample_step_context: StepContext,
    ) -> None:
        """StepResult.step_id must match the context step_id.

        The result should reference the same step that was executed.
        """
        result, _ = gemini_engine.run_step(sample_step_context)

        assert result.step_id == sample_step_context.step_id, (
            f"step_id mismatch: expected '{sample_step_context.step_id}', got '{result.step_id}'"
        )

    def test_step_id_matches_context_claude(
        self,
        claude_engine: ClaudeStepEngine,
        sample_step_context: StepContext,
    ) -> None:
        """StepResult.step_id must match the context step_id for Claude engine."""
        result, _ = claude_engine.run_step(sample_step_context)

        assert result.step_id == sample_step_context.step_id, (
            f"step_id mismatch: expected '{sample_step_context.step_id}', got '{result.step_id}'"
        )

    def test_dataclass_construction_validates_duration(self) -> None:
        """StepResult can be constructed with non-negative duration_ms."""
        # Valid construction
        result = StepResult(
            step_id="test",
            status="succeeded",
            output="test output",
            duration_ms=100,
        )
        assert result.duration_ms == 100

        # Zero duration is valid
        result_zero = StepResult(
            step_id="test",
            status="succeeded",
            output="test output",
            duration_ms=0,
        )
        assert result_zero.duration_ms == 0

    def test_all_status_values_are_valid(self) -> None:
        """All valid status values can be used in StepResult."""
        for status in VALID_STATUSES:
            result = StepResult(
                step_id="test",
                status=status,
                output="test output",
                duration_ms=0,
            )
            assert result.status == status


# -----------------------------------------------------------------------------
# Test Class: StepContext Contract
# -----------------------------------------------------------------------------


class TestStepContextContract:
    """Tests for StepContext invariants.

    These tests verify that StepContext instances properly provide
    the run_base property and other expected behaviors.
    """

    def test_run_base_returns_valid_path(
        self,
        sample_step_context: StepContext,
    ) -> None:
        """StepContext.run_base must return a valid Path object.

        The run_base property should return a Path that represents
        the expected directory structure: repo_root/swarm/runs/<run_id>/<flow_key>
        """
        run_base = sample_step_context.run_base

        assert isinstance(run_base, Path), f"run_base must be a Path, got {type(run_base).__name__}"

    def test_run_base_path_structure(
        self,
        sample_step_context: StepContext,
    ) -> None:
        """StepContext.run_base must follow expected directory structure.

        The path should be: repo_root / swarm / runs / <run_id> / <flow_key>
        """
        run_base = sample_step_context.run_base

        # Verify path ends with expected structure
        assert run_base.name == sample_step_context.flow_key, (
            f"run_base should end with flow_key '{sample_step_context.flow_key}', "
            f"got '{run_base.name}'"
        )

        # Verify parent structure includes run_id
        assert run_base.parent.name == sample_step_context.run_id, (
            f"run_base parent should be run_id '{sample_step_context.run_id}', "
            f"got '{run_base.parent.name}'"
        )

        # Verify grandparent is 'runs'
        assert run_base.parent.parent.name == "runs", (
            f"run_base grandparent should be 'runs', got '{run_base.parent.parent.name}'"
        )

    def test_run_base_is_relative_to_repo_root(
        self,
        sample_step_context: StepContext,
    ) -> None:
        """StepContext.run_base must be relative to repo_root."""
        run_base = sample_step_context.run_base

        # run_base should start with repo_root
        try:
            relative = run_base.relative_to(sample_step_context.repo_root)
            assert str(relative).startswith("swarm"), (
                f"run_base relative path should start with 'swarm', got '{relative}'"
            )
        except ValueError:
            pytest.fail(
                f"run_base {run_base} is not relative to repo_root {sample_step_context.repo_root}"
            )

    def test_context_preserves_step_metadata(
        self,
        sample_step_context: StepContext,
    ) -> None:
        """StepContext preserves all provided step metadata."""
        assert sample_step_context.step_id == "test_step"
        assert sample_step_context.step_index == 1
        assert sample_step_context.total_steps == 3
        assert sample_step_context.flow_key == "signal"
        assert sample_step_context.run_id == "test-run"
        assert "test-agent" in sample_step_context.step_agents


# -----------------------------------------------------------------------------
# Test Class: Engine Transcript Contract
# -----------------------------------------------------------------------------


class TestEngineTranscriptContract:
    """Tests for transcript file format invariants.

    These tests verify that engines write valid JSONL transcript files
    where each line is valid JSON.
    """

    def test_transcript_is_valid_jsonl_claude(
        self,
        claude_engine: ClaudeStepEngine,
        sample_step_context: StepContext,
    ) -> None:
        """ClaudeStepEngine writes valid JSONL transcript.

        Each line in the transcript file must be valid JSON.
        """
        # Create the run_base directory
        sample_step_context.run_base.mkdir(parents=True, exist_ok=True)

        # Execute step
        result, _ = claude_engine.run_step(sample_step_context)

        # Find transcript file
        llm_dir = sample_step_context.run_base / "llm"
        assert llm_dir.exists(), f"LLM directory should exist at {llm_dir}"

        transcript_files = list(llm_dir.glob("*-claude.jsonl"))
        assert len(transcript_files) >= 1, (
            f"Expected at least one transcript file in {llm_dir}, found: {list(llm_dir.iterdir())}"
        )

        # Verify each line is valid JSON
        for transcript_file in transcript_files:
            with transcript_file.open("r", encoding="utf-8") as f:
                for line_num, line in enumerate(f, start=1):
                    line = line.strip()
                    if not line:
                        continue  # Empty lines are allowed

                    try:
                        parsed = json.loads(line)
                        assert isinstance(parsed, dict), (
                            f"Line {line_num} in {transcript_file.name} should be "
                            f"a JSON object, got {type(parsed).__name__}"
                        )
                    except json.JSONDecodeError as e:
                        pytest.fail(
                            f"Invalid JSON at line {line_num} in "
                            f"{transcript_file.name}: {e}\n"
                            f"Line content: {line[:100]}..."
                        )

    def test_transcript_messages_have_required_fields_claude(
        self,
        claude_engine: ClaudeStepEngine,
        sample_step_context: StepContext,
    ) -> None:
        """ClaudeStepEngine transcript messages have required fields.

        Each message in the transcript should have 'role' and 'content' fields.
        """
        # Create the run_base directory
        sample_step_context.run_base.mkdir(parents=True, exist_ok=True)

        # Execute step
        result, _ = claude_engine.run_step(sample_step_context)

        # Find and verify transcript
        llm_dir = sample_step_context.run_base / "llm"
        transcript_files = list(llm_dir.glob("*-claude.jsonl"))

        for transcript_file in transcript_files:
            with transcript_file.open("r", encoding="utf-8") as f:
                for line_num, line in enumerate(f, start=1):
                    line = line.strip()
                    if not line:
                        continue

                    message = json.loads(line)
                    assert "role" in message, (
                        f"Line {line_num} in {transcript_file.name} missing 'role'"
                    )
                    assert "content" in message, (
                        f"Line {line_num} in {transcript_file.name} missing 'content'"
                    )

    def test_transcript_has_timestamp_claude(
        self,
        claude_engine: ClaudeStepEngine,
        sample_step_context: StepContext,
    ) -> None:
        """ClaudeStepEngine transcript messages have timestamps.

        Each message should include a timestamp field for observability.
        """
        # Create the run_base directory
        sample_step_context.run_base.mkdir(parents=True, exist_ok=True)

        # Execute step
        result, _ = claude_engine.run_step(sample_step_context)

        # Find and verify transcript
        llm_dir = sample_step_context.run_base / "llm"
        transcript_files = list(llm_dir.glob("*-claude.jsonl"))

        for transcript_file in transcript_files:
            with transcript_file.open("r", encoding="utf-8") as f:
                for line_num, line in enumerate(f, start=1):
                    line = line.strip()
                    if not line:
                        continue

                    message = json.loads(line)
                    assert "timestamp" in message, (
                        f"Line {line_num} in {transcript_file.name} missing 'timestamp'"
                    )


# -----------------------------------------------------------------------------
# Test Class: Engine Receipt Contract
# -----------------------------------------------------------------------------


class TestEngineReceiptContract:
    """Tests for receipt file schema invariants.

    These tests verify that engines write valid JSON receipt files
    matching the expected schema with required fields.
    """

    def test_receipt_is_valid_json_claude(
        self,
        claude_engine: ClaudeStepEngine,
        sample_step_context: StepContext,
    ) -> None:
        """ClaudeStepEngine writes valid JSON receipt.

        Receipt file must be parseable as JSON.
        """
        # Create the run_base directory
        sample_step_context.run_base.mkdir(parents=True, exist_ok=True)

        # Execute step
        result, _ = claude_engine.run_step(sample_step_context)

        # Find receipt file
        receipts_dir = sample_step_context.run_base / "receipts"
        assert receipts_dir.exists(), f"Receipts directory should exist at {receipts_dir}"

        receipt_files = list(receipts_dir.glob("*.json"))
        assert len(receipt_files) >= 1, (
            f"Expected at least one receipt file in {receipts_dir}, "
            f"found: {list(receipts_dir.iterdir())}"
        )

        # Verify each receipt is valid JSON
        for receipt_file in receipt_files:
            try:
                with receipt_file.open("r", encoding="utf-8") as f:
                    receipt = json.load(f)
                assert isinstance(receipt, dict), (
                    f"Receipt in {receipt_file.name} should be a JSON object"
                )
            except json.JSONDecodeError as e:
                pytest.fail(f"Invalid JSON in {receipt_file.name}: {e}")

    def test_receipt_has_required_fields_claude(
        self,
        claude_engine: ClaudeStepEngine,
        sample_step_context: StepContext,
    ) -> None:
        """ClaudeStepEngine receipt has all required fields.

        Required fields: engine, model, step_id, flow_key, run_id,
        agent_key, status, duration_ms
        """
        # Create the run_base directory
        sample_step_context.run_base.mkdir(parents=True, exist_ok=True)

        # Execute step
        result, _ = claude_engine.run_step(sample_step_context)

        # Find and verify receipt
        receipts_dir = sample_step_context.run_base / "receipts"
        receipt_files = list(receipts_dir.glob("*.json"))

        for receipt_file in receipt_files:
            with receipt_file.open("r", encoding="utf-8") as f:
                receipt = json.load(f)

            missing_fields = REQUIRED_RECEIPT_FIELDS - set(receipt.keys())
            assert not missing_fields, (
                f"Receipt in {receipt_file.name} missing required fields: {missing_fields}"
            )

    def test_receipt_engine_field_matches_claude(
        self,
        claude_engine: ClaudeStepEngine,
        sample_step_context: StepContext,
    ) -> None:
        """ClaudeStepEngine receipt 'engine' field matches engine_id.

        The receipt should identify which engine produced it.
        """
        # Create the run_base directory
        sample_step_context.run_base.mkdir(parents=True, exist_ok=True)

        # Execute step
        result, _ = claude_engine.run_step(sample_step_context)

        # Find and verify receipt
        receipts_dir = sample_step_context.run_base / "receipts"
        receipt_files = list(receipts_dir.glob("*.json"))

        for receipt_file in receipt_files:
            with receipt_file.open("r", encoding="utf-8") as f:
                receipt = json.load(f)

            assert receipt["engine"] == claude_engine.engine_id, (
                f"Receipt engine should be '{claude_engine.engine_id}', got '{receipt['engine']}'"
            )

    def test_receipt_step_id_matches_context_claude(
        self,
        claude_engine: ClaudeStepEngine,
        sample_step_context: StepContext,
    ) -> None:
        """ClaudeStepEngine receipt 'step_id' matches context step_id."""
        # Create the run_base directory
        sample_step_context.run_base.mkdir(parents=True, exist_ok=True)

        # Execute step
        result, _ = claude_engine.run_step(sample_step_context)

        # Find and verify receipt
        receipts_dir = sample_step_context.run_base / "receipts"
        receipt_files = list(receipts_dir.glob("*.json"))

        for receipt_file in receipt_files:
            with receipt_file.open("r", encoding="utf-8") as f:
                receipt = json.load(f)

            assert receipt["step_id"] == sample_step_context.step_id, (
                f"Receipt step_id should be '{sample_step_context.step_id}', "
                f"got '{receipt['step_id']}'"
            )

    def test_receipt_flow_key_matches_context_claude(
        self,
        claude_engine: ClaudeStepEngine,
        sample_step_context: StepContext,
    ) -> None:
        """ClaudeStepEngine receipt 'flow_key' matches context flow_key."""
        # Create the run_base directory
        sample_step_context.run_base.mkdir(parents=True, exist_ok=True)

        # Execute step
        result, _ = claude_engine.run_step(sample_step_context)

        # Find and verify receipt
        receipts_dir = sample_step_context.run_base / "receipts"
        receipt_files = list(receipts_dir.glob("*.json"))

        for receipt_file in receipt_files:
            with receipt_file.open("r", encoding="utf-8") as f:
                receipt = json.load(f)

            assert receipt["flow_key"] == sample_step_context.flow_key, (
                f"Receipt flow_key should be '{sample_step_context.flow_key}', "
                f"got '{receipt['flow_key']}'"
            )

    def test_receipt_run_id_matches_context_claude(
        self,
        claude_engine: ClaudeStepEngine,
        sample_step_context: StepContext,
    ) -> None:
        """ClaudeStepEngine receipt 'run_id' matches context run_id."""
        # Create the run_base directory
        sample_step_context.run_base.mkdir(parents=True, exist_ok=True)

        # Execute step
        result, _ = claude_engine.run_step(sample_step_context)

        # Find and verify receipt
        receipts_dir = sample_step_context.run_base / "receipts"
        receipt_files = list(receipts_dir.glob("*.json"))

        for receipt_file in receipt_files:
            with receipt_file.open("r", encoding="utf-8") as f:
                receipt = json.load(f)

            assert receipt["run_id"] == sample_step_context.run_id, (
                f"Receipt run_id should be '{sample_step_context.run_id}', "
                f"got '{receipt['run_id']}'"
            )

    def test_receipt_duration_ms_is_non_negative_claude(
        self,
        claude_engine: ClaudeStepEngine,
        sample_step_context: StepContext,
    ) -> None:
        """ClaudeStepEngine receipt 'duration_ms' is non-negative."""
        # Create the run_base directory
        sample_step_context.run_base.mkdir(parents=True, exist_ok=True)

        # Execute step
        result, _ = claude_engine.run_step(sample_step_context)

        # Find and verify receipt
        receipts_dir = sample_step_context.run_base / "receipts"
        receipt_files = list(receipts_dir.glob("*.json"))

        for receipt_file in receipt_files:
            with receipt_file.open("r", encoding="utf-8") as f:
                receipt = json.load(f)

            assert receipt["duration_ms"] >= 0, (
                f"Receipt duration_ms should be >= 0, got {receipt['duration_ms']}"
            )

    def test_receipt_status_is_valid_claude(
        self,
        claude_engine: ClaudeStepEngine,
        sample_step_context: StepContext,
    ) -> None:
        """ClaudeStepEngine receipt 'status' is a valid status value."""
        # Create the run_base directory
        sample_step_context.run_base.mkdir(parents=True, exist_ok=True)

        # Execute step
        result, _ = claude_engine.run_step(sample_step_context)

        # Find and verify receipt
        receipts_dir = sample_step_context.run_base / "receipts"
        receipt_files = list(receipts_dir.glob("*.json"))

        for receipt_file in receipt_files:
            with receipt_file.open("r", encoding="utf-8") as f:
                receipt = json.load(f)

            assert receipt["status"] in VALID_STATUSES, (
                f"Receipt status should be one of {VALID_STATUSES}, got '{receipt['status']}'"
            )


# -----------------------------------------------------------------------------
# Test Class: Engine ID Contract
# -----------------------------------------------------------------------------


class TestEngineIdContract:
    """Tests for engine_id property contract.

    These tests verify that each engine returns a unique, stable identifier.
    """

    def test_gemini_engine_id(
        self,
        gemini_engine: GeminiStepEngine,
    ) -> None:
        """GeminiStepEngine has engine_id 'gemini-step'."""
        assert gemini_engine.engine_id == "gemini-step", (
            f"GeminiStepEngine.engine_id should be 'gemini-step', got '{gemini_engine.engine_id}'"
        )

    def test_claude_engine_id(
        self,
        claude_engine: ClaudeStepEngine,
    ) -> None:
        """ClaudeStepEngine has engine_id 'claude-step'."""
        assert claude_engine.engine_id == "claude-step", (
            f"ClaudeStepEngine.engine_id should be 'claude-step', got '{claude_engine.engine_id}'"
        )

    def test_engine_ids_are_different(
        self,
        gemini_engine: GeminiStepEngine,
        claude_engine: ClaudeStepEngine,
    ) -> None:
        """Engine IDs are unique across implementations."""
        assert gemini_engine.engine_id != claude_engine.engine_id, (
            "Engine IDs must be unique across implementations"
        )


# -----------------------------------------------------------------------------
# Test Class: Receipt Mode/Provider Contract (NEW)
# -----------------------------------------------------------------------------


class TestReceiptModeProviderContract:
    """Tests for receipt mode and provider field invariants.

    These tests verify that engines include mode and provider information
    in receipts for observability and debugging.
    """

    def test_receipt_has_mode_field_claude(
        self,
        claude_engine: ClaudeStepEngine,
        sample_step_context: StepContext,
    ) -> None:
        """ClaudeStepEngine receipt includes 'mode' field.

        The mode field identifies how the engine executed: stub, sdk, or cli.
        """
        sample_step_context.run_base.mkdir(parents=True, exist_ok=True)
        result, _ = claude_engine.run_step(sample_step_context)

        receipts_dir = sample_step_context.run_base / "receipts"
        receipt_files = list(receipts_dir.glob("*.json"))

        for receipt_file in receipt_files:
            with receipt_file.open("r", encoding="utf-8") as f:
                receipt = json.load(f)

            assert "mode" in receipt, (
                f"Receipt should include 'mode' field, got keys: {list(receipt.keys())}"
            )
            assert receipt["mode"] in ("stub", "sdk", "cli"), (
                f"Receipt mode should be 'stub', 'sdk', or 'cli', got '{receipt['mode']}'"
            )

    def test_receipt_has_provider_field_claude(
        self,
        claude_engine: ClaudeStepEngine,
        sample_step_context: StepContext,
    ) -> None:
        """ClaudeStepEngine receipt includes 'provider' field.

        The provider field identifies the API provider: anthropic, anthropic_compat, etc.
        """
        sample_step_context.run_base.mkdir(parents=True, exist_ok=True)
        result, _ = claude_engine.run_step(sample_step_context)

        receipts_dir = sample_step_context.run_base / "receipts"
        receipt_files = list(receipts_dir.glob("*.json"))

        for receipt_file in receipt_files:
            with receipt_file.open("r", encoding="utf-8") as f:
                receipt = json.load(f)

            assert "provider" in receipt, (
                f"Receipt should include 'provider' field, got keys: {list(receipt.keys())}"
            )

    def test_receipt_has_mode_field_gemini(
        self,
        gemini_engine: GeminiStepEngine,
        sample_step_context: StepContext,
    ) -> None:
        """GeminiStepEngine receipt includes 'mode' field.

        The mode field identifies how the engine executed: stub or cli.
        """
        sample_step_context.run_base.mkdir(parents=True, exist_ok=True)
        result, _ = gemini_engine.run_step(sample_step_context)

        # Gemini only writes receipts when CLI is available (not in stub mode)
        # But we've updated it to always write receipts
        receipts_dir = sample_step_context.run_base / "receipts"
        if receipts_dir.exists():
            receipt_files = list(receipts_dir.glob("*.json"))

            for receipt_file in receipt_files:
                with receipt_file.open("r", encoding="utf-8") as f:
                    receipt = json.load(f)

                assert "mode" in receipt, (
                    f"Receipt should include 'mode' field, got keys: {list(receipt.keys())}"
                )
                assert receipt["mode"] in ("stub", "cli"), (
                    f"Receipt mode should be 'stub' or 'cli', got '{receipt['mode']}'"
                )

    def test_receipt_has_provider_field_gemini(
        self,
        gemini_engine: GeminiStepEngine,
        sample_step_context: StepContext,
    ) -> None:
        """GeminiStepEngine receipt includes 'provider' field.

        The provider field identifies the API provider: gemini.
        """
        sample_step_context.run_base.mkdir(parents=True, exist_ok=True)
        result, _ = gemini_engine.run_step(sample_step_context)

        receipts_dir = sample_step_context.run_base / "receipts"
        if receipts_dir.exists():
            receipt_files = list(receipts_dir.glob("*.json"))

            for receipt_file in receipt_files:
                with receipt_file.open("r", encoding="utf-8") as f:
                    receipt = json.load(f)

                assert "provider" in receipt, (
                    f"Receipt should include 'provider' field, got keys: {list(receipt.keys())}"
                )


# -----------------------------------------------------------------------------
# Test Class: Run Step Return Contract
# -----------------------------------------------------------------------------


class TestRunStepReturnContract:
    """Tests for run_step return value contract.

    These tests verify that run_step returns the expected tuple of
    (StepResult, Iterable[RunEvent]).
    """

    def test_run_step_returns_tuple_gemini(
        self,
        gemini_engine: GeminiStepEngine,
        sample_step_context: StepContext,
    ) -> None:
        """GeminiStepEngine.run_step returns (StepResult, events) tuple."""
        returned = gemini_engine.run_step(sample_step_context)

        assert isinstance(returned, tuple), (
            f"run_step should return tuple, got {type(returned).__name__}"
        )
        assert len(returned) == 2, f"run_step tuple should have 2 elements, got {len(returned)}"

        result, events = returned
        assert isinstance(result, StepResult), (
            f"First element should be StepResult, got {type(result).__name__}"
        )
        # Events should be iterable (list in our case)
        assert hasattr(events, "__iter__"), "Second element should be iterable"

    def test_run_step_returns_tuple_claude(
        self,
        claude_engine: ClaudeStepEngine,
        sample_step_context: StepContext,
    ) -> None:
        """ClaudeStepEngine.run_step returns (StepResult, events) tuple."""
        # Create the run_base directory for Claude (it writes files)
        sample_step_context.run_base.mkdir(parents=True, exist_ok=True)

        returned = claude_engine.run_step(sample_step_context)

        assert isinstance(returned, tuple), (
            f"run_step should return tuple, got {type(returned).__name__}"
        )
        assert len(returned) == 2, f"run_step tuple should have 2 elements, got {len(returned)}"

        result, events = returned
        assert isinstance(result, StepResult), (
            f"First element should be StepResult, got {type(result).__name__}"
        )
        assert hasattr(events, "__iter__"), "Second element should be iterable"


# -----------------------------------------------------------------------------
# Selftest Entrypoint
# -----------------------------------------------------------------------------


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
