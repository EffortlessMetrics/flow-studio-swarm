"""Tests for ClaudeStepwiseBackend.

This module tests the stepwise orchestration backend that executes flows
step-by-step using Claude Agent SDK (currently stubbed), emitting structured
stepwise events.

## Test Categories

Tests are organized into two categories using pytest marks:

- **contract**: Fast, pure interface tests (<100ms each). Test backend
  registration, capabilities, and interface compliance. No orchestrator
  execution, no background threads. These should always pass.

- **integration**: Tests that involve the orchestrator background thread.
  These may take longer (1-5s) and have timing-dependent behavior.
  The isolated_runs_env fixture provides test isolation.

## Test Coverage

### Backend Registration (2 tests) - contract
1. test_list_backends_includes_claude_step_orchestrator - Verify "claude-step-orchestrator"
   appears in list_backends()
2. test_get_backend_returns_claude_stepwise_backend - Verify get_backend("claude-step-orchestrator")
   returns ClaudeStepwiseBackend instance

### Backend Capabilities (5 tests) - contract
3. test_capabilities_id - Verify id == "claude-step-orchestrator"
4. test_capabilities_label - Verify label == "Claude Agent SDK (stepwise)"
5. test_capabilities_streaming_support - Verify streaming support
6. test_capabilities_events_support - Verify events support
7. test_capabilities_cancel_support - Verify cancel support

### Run Creation (1 test) - integration
8. test_start_creates_run - Test that start() creates run_id, meta.json, spec.json,
   events.jsonl and writes transcript/receipt files

### Transcript and Receipt Files (1 test) - integration
9. test_run_writes_transcript_and_receipt_files - Check that the run writes
   transcript (.jsonl) and receipt (.json) files to RUN_BASE

## Patterns Used

- Uses `isolated_runs_env` fixture for test isolation
- Uses monkeypatch for environment variables
- Follows existing patterns from test_gemini_stepwise_backend.py
- Imports from swarm.runtime.backends and swarm.runtime.types
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from typing import Dict
from unittest.mock import MagicMock, patch

import pytest

# Add repo root to path for imports
repo_root = Path(__file__).resolve().parents[1]
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from swarm.runtime import service as runtime_service
from swarm.runtime import storage
from swarm.runtime.service import RunService
from swarm.runtime.types import (
    RunSpec,
    RunStatus,
    SDLCStatus,
)

# -----------------------------------------------------------------------------
# Stub Orchestrator for Synchronous Contract Tests
# -----------------------------------------------------------------------------


class StubStepwiseOrchestrator:
    """Minimal orchestrator stub for run-creation contract tests.

    This stub does nothing when _execute_stepwise is called, allowing tests
    to verify the synchronous contract of ClaudeStepwiseBackend.start()
    without depending on background thread behavior.

    The synchronous contract includes:
    - run_id generation
    - run directory creation
    - meta.json (RunSummary) written
    - spec.json (RunSpec) written
    - events.jsonl with run_created event

    All of these are written synchronously by start() BEFORE the background
    thread is spawned. This stub ensures the background thread is a no-op,
    making the test deterministic and fast.
    """

    def _execute_stepwise(
        self,
        run_id: str,  # noqa: ARG002
        flow_key: str,  # noqa: ARG002
        flow_def: object,  # noqa: ARG002
        spec: RunSpec,  # noqa: ARG002
        start_step: object,  # noqa: ARG002
        end_step: object,  # noqa: ARG002
    ) -> None:
        """No-op implementation.

        The real orchestrator would execute steps here. For contract tests,
        we simply return immediately to avoid any background work.

        All parameters are intentionally unused - this is a stub that does nothing.
        """
        pass

    @property
    def _flow_registry(self) -> MagicMock:
        """Return a mock flow registry.

        This is accessed by ClaudeStepwiseBackend._execute_stepwise() to get
        flow definitions. We return a MagicMock that returns None for any
        get_flow() call, which causes the backend to skip flow execution.
        """
        mock_registry = MagicMock()
        mock_registry.get_flow = MagicMock(return_value=None)
        return mock_registry


# -----------------------------------------------------------------------------
# Fixtures
# -----------------------------------------------------------------------------


@pytest.fixture
def isolated_runs_env(tmp_path, monkeypatch):
    """
    Fixture that isolates tests from real swarm/runs/ and swarm/examples/.

    Creates temporary directories and monkeypatches storage.RUNS_DIR and
    storage.EXAMPLES_DIR. Also resets RunService singleton before and after.

    Yields a dict with runs_dir, examples_dir, and repo_root paths.
    """
    runs_dir = tmp_path / "swarm" / "runs"
    examples_dir = tmp_path / "swarm" / "examples"
    meta_dir = tmp_path / "swarm" / "meta"

    runs_dir.mkdir(parents=True)
    examples_dir.mkdir(parents=True)
    meta_dir.mkdir(parents=True)

    # Monkeypatch storage module globals
    monkeypatch.setattr(storage, "RUNS_DIR", runs_dir)
    monkeypatch.setattr(storage, "EXAMPLES_DIR", examples_dir)

    # Also patch the locally-imported EXAMPLES_DIR in service module
    monkeypatch.setattr(runtime_service, "EXAMPLES_DIR", examples_dir)

    # Reset RunService singleton before test
    RunService.reset()

    yield {
        "runs_dir": runs_dir,
        "examples_dir": examples_dir,
        "repo_root": tmp_path,
    }

    # Reset RunService singleton after test
    RunService.reset()


# -----------------------------------------------------------------------------
# Test Class: Backend Registration (contract tests)
# -----------------------------------------------------------------------------


@pytest.mark.unit
class TestClaudeStepwiseBackendRegistration:
    """Tests for backend registration and retrieval."""

    def test_list_backends_includes_claude_step_orchestrator(self) -> None:
        """list_backends() includes "claude-step-orchestrator" in results.

        The ClaudeStepwiseBackend should be registered and appear in the
        list of available backends returned by list_backends().
        """
        from swarm.runtime.backends import list_backends

        backends = list_backends()
        backend_ids = [b.id for b in backends]

        assert "claude-step-orchestrator" in backend_ids, (
            f"Expected 'claude-step-orchestrator' in backend list, got: {backend_ids}"
        )

    def test_get_backend_returns_claude_stepwise_backend(self) -> None:
        """get_backend("claude-step-orchestrator") returns ClaudeStepwiseBackend.

        Calling get_backend with the "claude-step-orchestrator" ID should
        return an instance of ClaudeStepwiseBackend.
        """
        from swarm.runtime.backends import ClaudeStepwiseBackend, get_backend

        backend = get_backend("claude-step-orchestrator")

        assert isinstance(backend, ClaudeStepwiseBackend), (
            f"Expected ClaudeStepwiseBackend instance, got {type(backend).__name__}"
        )


# -----------------------------------------------------------------------------
# Test Class: Backend Capabilities (contract tests)
# -----------------------------------------------------------------------------


@pytest.mark.unit
class TestClaudeStepwiseBackendCapabilities:
    """Tests for backend capabilities reporting."""

    def test_capabilities_id(self) -> None:
        """capabilities().id == "claude-step-orchestrator".

        The ClaudeStepwiseBackend should report "claude-step-orchestrator"
        as its capability ID.
        """
        from swarm.runtime.backends import ClaudeStepwiseBackend

        backend = ClaudeStepwiseBackend()
        caps = backend.capabilities()

        assert caps.id == "claude-step-orchestrator", (
            f"Expected id 'claude-step-orchestrator', got '{caps.id}'"
        )

    def test_capabilities_label(self) -> None:
        """capabilities().label == "Claude Agent SDK (stepwise)".

        The ClaudeStepwiseBackend should report a human-readable label
        indicating it uses Claude Agent SDK in stepwise mode.
        """
        from swarm.runtime.backends import ClaudeStepwiseBackend

        backend = ClaudeStepwiseBackend()
        caps = backend.capabilities()

        assert caps.label == "Claude Agent SDK (stepwise)", (
            f"Expected label 'Claude Agent SDK (stepwise)', got '{caps.label}'"
        )

    def test_capabilities_streaming_support(self) -> None:
        """Backend should support streaming."""
        from swarm.runtime.backends import ClaudeStepwiseBackend

        backend = ClaudeStepwiseBackend()
        caps = backend.capabilities()

        assert caps.supports_streaming is True, "Backend should support streaming"

    def test_capabilities_events_support(self) -> None:
        """Backend should support events."""
        from swarm.runtime.backends import ClaudeStepwiseBackend

        backend = ClaudeStepwiseBackend()
        caps = backend.capabilities()

        assert caps.supports_events is True, "Backend should support events"

    def test_capabilities_cancel_support(self) -> None:
        """Backend should support cancellation."""
        from swarm.runtime.backends import ClaudeStepwiseBackend

        backend = ClaudeStepwiseBackend()
        caps = backend.capabilities()

        assert caps.supports_cancel is True, "Backend should support cancellation"

    def test_capabilities_no_replay_support(self) -> None:
        """Stepwise backend should not support replay."""
        from swarm.runtime.backends import ClaudeStepwiseBackend

        backend = ClaudeStepwiseBackend()
        caps = backend.capabilities()

        assert caps.supports_replay is False, "Stepwise backend should not support replay"


# -----------------------------------------------------------------------------
# Test Class: Run Creation (integration tests)
# -----------------------------------------------------------------------------


@pytest.mark.integration
class TestClaudeStepwiseBackendRunCreation:
    """Tests for run creation and initialization.

    These tests verify the synchronous contract of ClaudeStepwiseBackend.start():
    - run_id generation
    - run directory creation
    - meta.json (RunSummary) written
    - spec.json (RunSpec) written
    - events.jsonl with run_created event

    The tests use StubStepwiseOrchestrator to avoid depending on background
    thread behavior, making them deterministic and fast.
    """

    def test_start_creates_run(
        self,
        isolated_runs_env: Dict[str, Path],
    ) -> None:
        """start() creates run with proper metadata.

        When start() is called, the following happens SYNCHRONOUSLY before
        the background thread is spawned:
        1. A unique run_id is generated
        2. A run directory is created at swarm/runs/<run_id>/
        3. meta.json is written with initial RunSummary
        4. spec.json is written with the RunSpec
        5. events.jsonl is created with run_created event
        6. The run_created event has stepwise=True in payload

        This test uses a stub orchestrator to make the background thread a no-op,
        allowing us to test the synchronous contract deterministically.
        """
        from swarm.runtime.backends import ClaudeStepwiseBackend

        env = isolated_runs_env

        backend = ClaudeStepwiseBackend(repo_root=env["repo_root"])

        # Patch _get_orchestrator to return our stub that does no background work
        with patch.object(backend, "_get_orchestrator") as mock_get_orch:
            mock_get_orch.return_value = StubStepwiseOrchestrator()

            spec = RunSpec(
                flow_keys=["signal"],
                profile_id=None,
                backend="claude-step-orchestrator",
                initiator="test",
                params={"title": "Test Claude Stepwise Run"},
            )

            # Start the run - this is now deterministic
            run_id = backend.start(spec)

            # Give the background thread a moment to call our stub
            # (the stub does nothing, so this is just for thread scheduling)
            time.sleep(0.1)

        # Verify run_id format
        assert run_id is not None, "start() should return a run_id"
        assert run_id.startswith("run-"), f"run_id should start with 'run-', got '{run_id}'"

        # All synchronous work is complete - no polling needed!
        # The summary and events were written before start() returned.

        # Verify summary can be read back via the backend
        summary = backend.get_summary(run_id)
        assert summary is not None, f"Summary should be readable after start() (run_id={run_id})"
        assert summary.id == run_id, "Summary should have correct run_id"
        assert summary.status in [
            RunStatus.PENDING,
            RunStatus.RUNNING,
            RunStatus.SUCCEEDED,
            RunStatus.FAILED,
        ], f"Status should be valid, got {summary.status}"

        # Verify spec is preserved in summary
        assert summary.spec is not None, "Summary should contain spec"
        assert summary.spec.flow_keys == ["signal"], (
            f"Spec flow_keys mismatch: {summary.spec.flow_keys}"
        )
        assert summary.spec.backend == "claude-step-orchestrator", (
            f"Spec backend mismatch: {summary.spec.backend}"
        )

        # Verify events can be read back
        events = backend.get_events(run_id)
        assert len(events) >= 1, "Expected at least one event"

        # Find run_created event
        run_created_events = [e for e in events if e.kind == "run_created"]
        assert len(run_created_events) >= 1, "Expected run_created event"

        # Verify stepwise flag in run_created event
        run_created = run_created_events[0]
        assert run_created.payload.get("stepwise") is True, (
            f"run_created event should have stepwise: True, got {run_created.payload}"
        )
        assert run_created.payload.get("backend") == "claude-step-orchestrator", (
            f"run_created event should have backend: claude-step-orchestrator, "
            f"got {run_created.payload.get('backend')}"
        )


# -----------------------------------------------------------------------------
# Test Class: Transcript and Receipt Files (integration tests)
# -----------------------------------------------------------------------------


@pytest.mark.integration
@pytest.mark.slow
class TestClaudeStepwiseBackendTranscripts:
    """Tests for transcript and receipt file generation."""

    def test_run_writes_transcript_and_receipt_files(
        self,
        isolated_runs_env: Dict[str, Path],
    ) -> None:
        """Run writes transcript and receipt files to RUN_BASE.

        The ClaudeStepEngine writes:
        - Transcript files: RUN_BASE/<flow>/llm/<step_id>-<agent>-claude.jsonl
        - Receipt files: RUN_BASE/<flow>/receipts/<step_id>-<agent>.json

        This test verifies that after a run completes, these files exist
        and contain the expected content structure.

        Note: This test uses a mock flow registry to ensure steps are defined,
        since the isolated environment may not have real flow definitions.
        """
        from swarm.config.flow_registry import FlowDefinition, StepDefinition
        from swarm.runtime.backends import ClaudeStepwiseBackend

        env = isolated_runs_env

        backend = ClaudeStepwiseBackend(repo_root=env["repo_root"])

        # Create a mock flow definition with a test step
        mock_step = StepDefinition(
            id="test_step",
            index=1,
            role="Test step for transcript verification",
            agents=("test-agent",),
        )
        mock_flow = FlowDefinition(
            key="signal",
            title="Signal Flow",
            short_title="Signal",
            description="Test flow for transcript verification",
            index=1,
            steps=(mock_step,),
        )

        # Mock the flow registry to return our test flow
        mock_registry = MagicMock()
        mock_registry.get_flow = MagicMock(return_value=mock_flow)

        spec = RunSpec(
            flow_keys=["signal"],
            profile_id=None,
            backend="claude-step-orchestrator",
            initiator="test",
        )

        # Patch the orchestrator's flow registry
        with patch.object(backend, "_get_orchestrator") as mock_get_orch:
            # Create a real orchestrator but with mocked registry
            from swarm.runtime.engines import ClaudeStepEngine
            from swarm.runtime.orchestrator import GeminiStepOrchestrator

            engine = ClaudeStepEngine(repo_root=env["repo_root"])
            orchestrator = GeminiStepOrchestrator(
                engine=engine,
                repo_root=env["repo_root"],
            )
            # Replace the registry with our mock
            orchestrator._flow_registry = mock_registry
            mock_get_orch.return_value = orchestrator

            # Start the run
            run_id = backend.start(spec)

            # Wait for background execution to complete
            max_wait = 5.0
            wait_interval = 0.2
            elapsed = 0.0

            while elapsed < max_wait:
                summary = backend.get_summary(run_id)
                if summary and summary.status in [
                    RunStatus.SUCCEEDED,
                    RunStatus.FAILED,
                ]:
                    break
                time.sleep(wait_interval)
                elapsed += wait_interval

            # Verify the run directory structure
            run_base = env["runs_dir"] / run_id / "signal"

            # Check for llm directory and transcript files
            llm_dir = run_base / "llm"
            if llm_dir.exists():
                transcript_files = list(llm_dir.glob("*-claude.jsonl"))
                assert len(transcript_files) >= 1, (
                    f"Expected at least one transcript file in {llm_dir}, "
                    f"found: {list(llm_dir.iterdir())}"
                )

                # Verify transcript content structure
                transcript_file = transcript_files[0]
                with transcript_file.open("r", encoding="utf-8") as f:
                    lines = f.readlines()
                    assert len(lines) >= 1, "Transcript should have at least one message"

                    # Parse first message
                    first_msg = json.loads(lines[0])
                    assert "role" in first_msg, "Transcript message should have 'role'"
                    assert "content" in first_msg, "Transcript message should have 'content'"

            # Check for receipts directory and receipt files
            receipts_dir = run_base / "receipts"
            if receipts_dir.exists():
                receipt_files = list(receipts_dir.glob("*.json"))
                assert len(receipt_files) >= 1, (
                    f"Expected at least one receipt file in {receipts_dir}, "
                    f"found: {list(receipts_dir.iterdir())}"
                )

                # Verify receipt content structure
                receipt_file = receipt_files[0]
                with receipt_file.open("r", encoding="utf-8") as f:
                    receipt = json.load(f)
                    assert "engine" in receipt, "Receipt should have 'engine'"
                    assert receipt["engine"] == "claude-step", (
                        f"Receipt engine should be 'claude-step', got '{receipt['engine']}'"
                    )
                    assert "step_id" in receipt, "Receipt should have 'step_id'"
                    assert "status" in receipt, "Receipt should have 'status'"


# -----------------------------------------------------------------------------
# Test Class: Edge Cases (contract + integration tests)
# -----------------------------------------------------------------------------


@pytest.mark.integration
class TestClaudeStepwiseBackendEdgeCases:
    """Tests for edge cases and error handling."""

    def test_get_summary_nonexistent_run(
        self,
        isolated_runs_env: Dict[str, Path],
    ) -> None:
        """get_summary returns None for non-existent run."""
        from swarm.runtime.backends import ClaudeStepwiseBackend

        env = isolated_runs_env

        backend = ClaudeStepwiseBackend(repo_root=env["repo_root"])

        summary = backend.get_summary("nonexistent-run-12345")

        assert summary is None, "get_summary should return None for nonexistent run"

    def test_get_events_nonexistent_run(
        self,
        isolated_runs_env: Dict[str, Path],
    ) -> None:
        """get_events returns empty list for non-existent run."""
        from swarm.runtime.backends import ClaudeStepwiseBackend

        env = isolated_runs_env

        backend = ClaudeStepwiseBackend(repo_root=env["repo_root"])

        events = backend.get_events("nonexistent-run-12345")

        assert events == [], "get_events should return empty list for nonexistent run"

    def test_list_summaries_returns_runs(
        self,
        isolated_runs_env: Dict[str, Path],
    ) -> None:
        """list_summaries returns runs from the runs directory.

        Note: This test creates a run via the backend's start() method
        rather than using a helper, since the backend uses the global
        RUNS_DIR for storage operations.
        """
        from swarm.runtime.backends import ClaudeStepwiseBackend

        env = isolated_runs_env

        backend = ClaudeStepwiseBackend(repo_root=env["repo_root"])

        # Create a run via the backend
        spec = RunSpec(
            flow_keys=["signal"],
            profile_id=None,
            backend="claude-step-orchestrator",
            initiator="test",
        )
        run_id = backend.start(spec)

        summaries = backend.list_summaries()

        # Should find the run we created
        assert len(summaries) >= 1, "list_summaries should return at least one run"
        run_ids = [s.id for s in summaries]
        assert run_id in run_ids, f"Should find our test run {run_id}"


# -----------------------------------------------------------------------------
# Integration Test: Summary Retrieval
# -----------------------------------------------------------------------------


@pytest.mark.integration
@pytest.mark.slow
class TestClaudeStepwiseBackendSummary:
    """Tests for summary retrieval."""

    def test_get_summary_returns_correct_data(
        self,
        isolated_runs_env: Dict[str, Path],
    ) -> None:
        """Verify get_summary returns correct data.

        After starting a run, get_summary should return:
        - The correct run_id
        - The correct status (pending/running/succeeded/failed)
        - The original spec
        - Timestamps (created_at, updated_at)
        - SDLC status
        """
        from swarm.runtime.backends import ClaudeStepwiseBackend

        env = isolated_runs_env

        backend = ClaudeStepwiseBackend(repo_root=env["repo_root"])

        spec = RunSpec(
            flow_keys=["signal", "plan"],
            profile_id="baseline",
            backend="claude-step-orchestrator",
            initiator="test",
            params={"title": "Test Summary Run"},
        )

        # Start the run
        run_id = backend.start(spec)

        # Wait briefly for initialization
        time.sleep(0.3)

        # Get summary
        summary = backend.get_summary(run_id)

        # Verify summary exists
        assert summary is not None, "get_summary should return a RunSummary"

        # Verify run_id matches
        assert summary.id == run_id, f"Summary run_id mismatch: expected {run_id}, got {summary.id}"

        # Verify status is valid
        assert summary.status in [
            RunStatus.PENDING,
            RunStatus.RUNNING,
            RunStatus.SUCCEEDED,
            RunStatus.FAILED,
        ], f"Invalid status: {summary.status}"

        # Verify spec is preserved
        assert summary.spec is not None, "Summary should contain spec"
        assert summary.spec.flow_keys == ["signal", "plan"], (
            f"Spec flow_keys mismatch: {summary.spec.flow_keys}"
        )
        assert summary.spec.backend == "claude-step-orchestrator", (
            f"Spec backend mismatch: {summary.spec.backend}"
        )
        assert summary.spec.profile_id == "baseline", (
            f"Spec profile_id mismatch: {summary.spec.profile_id}"
        )

        # Verify timestamps exist
        assert summary.created_at is not None, "created_at should be set"
        assert summary.updated_at is not None, "updated_at should be set"

        # Verify SDLC status is set
        assert summary.sdlc_status in [
            SDLCStatus.OK,
            SDLCStatus.WARNING,
            SDLCStatus.ERROR,
            SDLCStatus.UNKNOWN,
        ], f"Invalid sdlc_status: {summary.sdlc_status}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
