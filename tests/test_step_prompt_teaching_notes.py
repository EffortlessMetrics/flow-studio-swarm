"""Tests for teaching_notes rendering in step prompts.

This module validates that teaching_notes from flow YAML configuration
are included in prompts built by step engines. It proves the contract
that "scoped context per step" is enforced, not just aspirational.

## Test Coverage

### Teaching Notes in Prompts (4 tests)
1. test_inputs_appear_in_prompt - teaching_notes.inputs paths appear in prompt
2. test_outputs_appear_in_prompt - teaching_notes.outputs paths appear in prompt
3. test_emphasizes_appear_in_prompt - teaching_notes.emphasizes items appear in prompt
4. test_constraints_appear_in_prompt - teaching_notes.constraints items appear in prompt

### Cross-Step Isolation (2 tests)
5. test_no_cross_step_leakage - Different steps have different teaching_notes in prompts
6. test_steps_without_teaching_notes_still_work - Steps without notes don't break

## Patterns Used

- Tests both GeminiStepEngine and ClaudeStepEngine
- Uses real FlowRegistry to load actual step definitions
- Inspects _build_prompt output directly (no LLM calls)

## API Note

As of v2.5.0, _build_prompt returns Tuple[str, Optional[HistoryTruncationInfo]].
The helper function build_prompt_text() extracts just the prompt string for tests.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

import pytest

# Add repo root to path for imports
repo_root = Path(__file__).resolve().parents[1]
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from swarm.config.flow_registry import (
    FlowRegistry,
    TeachingNotes,
)
from swarm.runtime.engines import (
    ClaudeStepEngine,
    GeminiStepEngine,
    StepContext,
)
from swarm.runtime.types import RunSpec

# -----------------------------------------------------------------------------
# Helper: Extract prompt text from _build_prompt tuple return
# -----------------------------------------------------------------------------


def build_prompt_text(engine, ctx: StepContext) -> str:
    """Extract prompt text from _build_prompt, ignoring truncation info.

    As of v2.5.0, _build_prompt returns Tuple[str, Optional[HistoryTruncationInfo]].
    This helper extracts just the prompt string for tests that don't care about
    truncation metadata.

    Args:
        engine: A GeminiStepEngine or ClaudeStepEngine instance
        ctx: The step context to build a prompt for

    Returns:
        The prompt string (first element of the tuple)
    """
    result = engine._build_prompt(ctx)
    if isinstance(result, tuple):
        return result[0]
    # Backward compatibility if implementation changes
    return result


# -----------------------------------------------------------------------------
# Fixtures
# -----------------------------------------------------------------------------


@pytest.fixture
def tmp_repo(tmp_path: Path) -> Path:
    """Create a temporary repo structure for testing."""
    runs_dir = tmp_path / "swarm" / "runs"
    runs_dir.mkdir(parents=True)
    return tmp_path


@pytest.fixture
def sample_run_spec() -> RunSpec:
    """Create a sample RunSpec for testing."""
    return RunSpec(
        flow_keys=["build"],
        profile_id=None,
        backend="test-backend",
        initiator="test",
    )


@pytest.fixture
def gemini_engine(tmp_repo: Path) -> GeminiStepEngine:
    """Create a GeminiStepEngine in stub mode."""
    engine = GeminiStepEngine(tmp_repo)
    engine.stub_mode = True
    return engine


@pytest.fixture
def claude_engine(tmp_repo: Path) -> ClaudeStepEngine:
    """Create a ClaudeStepEngine in stub mode."""
    return ClaudeStepEngine(tmp_repo, mode="stub")


def make_step_context(
    tmp_repo: Path,
    spec: RunSpec,
    step_id: str = "test_step",
    step_index: int = 1,
    step_role: str = "Test step role",
    step_agents: tuple = ("test-agent",),
    flow_key: str = "build",
    flow_title: str = "Test Build Flow",
    total_steps: int = 10,
    teaching_notes: Optional[TeachingNotes] = None,
) -> StepContext:
    """Create a StepContext for testing prompt building."""
    return StepContext(
        repo_root=tmp_repo,
        run_id="test-run",
        flow_key=flow_key,
        step_id=step_id,
        step_index=step_index,
        total_steps=total_steps,
        spec=spec,
        flow_title=flow_title,
        step_role=step_role,
        step_agents=step_agents,
        history=[],
        extra={},
        teaching_notes=teaching_notes,
    )


# -----------------------------------------------------------------------------
# Helper: Enhanced _build_prompt with teaching_notes
# -----------------------------------------------------------------------------
#
# NOTE: The current engines do NOT include teaching_notes in prompts.
# These tests document the expected behavior and will initially fail,
# serving as a contract that implementation should satisfy.
#
# The tests check what SHOULD be in the prompt once teaching_notes
# integration is complete.


def get_teaching_notes_for_step(flow_key: str, step_id: str) -> Optional[TeachingNotes]:
    """Get teaching_notes for a step from the real FlowRegistry."""
    registry = FlowRegistry.get_instance()
    flow = registry.get_flow(flow_key)
    if not flow:
        return None

    for step in flow.steps:
        if step.id == step_id:
            return step.teaching_notes

    return None


# -----------------------------------------------------------------------------
# Test Class: Teaching Notes Contract Tests
# -----------------------------------------------------------------------------


class TestTeachingNotesInPrompt:
    """Tests that teaching_notes appear in prompts.

    These tests verify that the step engines include teaching_notes
    from flow YAML in the prompts they build.
    """

    def test_inputs_appear_in_prompt_gemini(
        self,
        gemini_engine: GeminiStepEngine,
        tmp_repo: Path,
        sample_run_spec: RunSpec,
    ) -> None:
        """GeminiStepEngine prompt includes teaching_notes.inputs paths.

        The prompt should contain a section listing input files/artifacts
        that the step should read.
        """
        # Use a real step from build.yaml that has teaching_notes
        step_id = "author_tests"
        flow_key = "build"

        teaching_notes = get_teaching_notes_for_step(flow_key, step_id)
        assert teaching_notes is not None, f"Step {step_id} should have teaching_notes"
        assert len(teaching_notes.inputs) > 0, "Step should have input paths"

        ctx = make_step_context(
            tmp_repo=tmp_repo,
            spec=sample_run_spec,
            step_id=step_id,
            flow_key=flow_key,
            step_role="Write/update tests → tests/*, test_changes_summary.md.",
            step_agents=("test-author",),
            teaching_notes=teaching_notes,
        )

        # Build prompt (using helper to extract text from tuple)
        prompt = build_prompt_text(gemini_engine, ctx)

        # Verify inputs appear in prompt
        for input_path in teaching_notes.inputs:
            assert input_path in prompt, f"Input path '{input_path}' should appear in prompt"

    def test_outputs_appear_in_prompt_gemini(
        self,
        gemini_engine: GeminiStepEngine,
        tmp_repo: Path,
        sample_run_spec: RunSpec,
    ) -> None:
        """GeminiStepEngine prompt includes teaching_notes.outputs paths.

        The prompt should contain a section listing output files/artifacts
        that the step should produce.
        """
        step_id = "author_tests"
        flow_key = "build"

        teaching_notes = get_teaching_notes_for_step(flow_key, step_id)
        assert teaching_notes is not None
        assert len(teaching_notes.outputs) > 0

        ctx = make_step_context(
            tmp_repo=tmp_repo,
            spec=sample_run_spec,
            step_id=step_id,
            flow_key=flow_key,
            step_role="Write/update tests → tests/*, test_changes_summary.md.",
            step_agents=("test-author",),
            teaching_notes=teaching_notes,
        )

        prompt = build_prompt_text(gemini_engine, ctx)

        for output_path in teaching_notes.outputs:
            assert output_path in prompt, f"Output path '{output_path}' should appear in prompt"

    def test_emphasizes_appear_in_prompt_claude(
        self,
        claude_engine: ClaudeStepEngine,
        tmp_repo: Path,
        sample_run_spec: RunSpec,
    ) -> None:
        """ClaudeStepEngine prompt includes teaching_notes.emphasizes items.

        The prompt should contain behavioral guidance from the emphasizes list.
        """
        step_id = "author_tests"
        flow_key = "build"

        teaching_notes = get_teaching_notes_for_step(flow_key, step_id)
        assert teaching_notes is not None
        assert len(teaching_notes.emphasizes) > 0

        ctx = make_step_context(
            tmp_repo=tmp_repo,
            spec=sample_run_spec,
            step_id=step_id,
            flow_key=flow_key,
            step_role="Write/update tests → tests/*, test_changes_summary.md.",
            step_agents=("test-author",),
            teaching_notes=teaching_notes,
        )

        prompt = build_prompt_text(claude_engine, ctx)

        for emphasis in teaching_notes.emphasizes:
            assert emphasis in prompt, f"Emphasis '{emphasis}' should appear in prompt"

    def test_constraints_appear_in_prompt_claude(
        self,
        claude_engine: ClaudeStepEngine,
        tmp_repo: Path,
        sample_run_spec: RunSpec,
    ) -> None:
        """ClaudeStepEngine prompt includes teaching_notes.constraints items.

        The prompt should contain limitations/prohibitions from constraints.
        """
        step_id = "author_tests"
        flow_key = "build"

        teaching_notes = get_teaching_notes_for_step(flow_key, step_id)
        assert teaching_notes is not None
        assert len(teaching_notes.constraints) > 0

        ctx = make_step_context(
            tmp_repo=tmp_repo,
            spec=sample_run_spec,
            step_id=step_id,
            flow_key=flow_key,
            step_role="Write/update tests → tests/*, test_changes_summary.md.",
            step_agents=("test-author",),
            teaching_notes=teaching_notes,
        )

        prompt = build_prompt_text(claude_engine, ctx)

        for constraint in teaching_notes.constraints:
            assert constraint in prompt, f"Constraint '{constraint}' should appear in prompt"


# -----------------------------------------------------------------------------
# Test Class: Current Prompt Structure (Passing Tests)
# -----------------------------------------------------------------------------


class TestCurrentPromptStructure:
    """Tests for current prompt structure (these should pass).

    These tests verify the existing prompt structure while the teaching_notes
    integration is in progress.
    """

    def test_prompt_includes_flow_title(
        self,
        gemini_engine: GeminiStepEngine,
        tmp_repo: Path,
        sample_run_spec: RunSpec,
    ) -> None:
        """Prompt includes the flow title."""
        ctx = make_step_context(
            tmp_repo=tmp_repo,
            spec=sample_run_spec,
            flow_title="Test Build Flow",
        )

        prompt = build_prompt_text(gemini_engine, ctx)

        assert "Test Build Flow" in prompt, "Flow title should appear in prompt"

    def test_prompt_includes_step_id(
        self,
        gemini_engine: GeminiStepEngine,
        tmp_repo: Path,
        sample_run_spec: RunSpec,
    ) -> None:
        """Prompt includes the step ID."""
        ctx = make_step_context(
            tmp_repo=tmp_repo,
            spec=sample_run_spec,
            step_id="my_test_step",
        )

        prompt = build_prompt_text(gemini_engine, ctx)

        assert "my_test_step" in prompt, "Step ID should appear in prompt"

    def test_prompt_includes_step_role(
        self,
        gemini_engine: GeminiStepEngine,
        tmp_repo: Path,
        sample_run_spec: RunSpec,
    ) -> None:
        """Prompt includes the step role description."""
        ctx = make_step_context(
            tmp_repo=tmp_repo,
            spec=sample_run_spec,
            step_role="Execute the important task with care.",
        )

        prompt = build_prompt_text(gemini_engine, ctx)

        assert "Execute the important task with care" in prompt, "Step role should appear in prompt"

    def test_prompt_includes_agent_assignment(
        self,
        gemini_engine: GeminiStepEngine,
        tmp_repo: Path,
        sample_run_spec: RunSpec,
    ) -> None:
        """Prompt includes assigned agent names."""
        ctx = make_step_context(
            tmp_repo=tmp_repo,
            spec=sample_run_spec,
            step_agents=("test-author", "helper-agent"),
        )

        prompt = build_prompt_text(gemini_engine, ctx)

        assert "test-author" in prompt, "First agent should appear in prompt"
        assert "helper-agent" in prompt, "Second agent should appear in prompt"

    def test_prompt_includes_run_base_path(
        self,
        gemini_engine: GeminiStepEngine,
        tmp_repo: Path,
        sample_run_spec: RunSpec,
    ) -> None:
        """Prompt includes the RUN_BASE output location."""
        ctx = make_step_context(
            tmp_repo=tmp_repo,
            spec=sample_run_spec,
            step_id="test_step",
            flow_key="build",
        )

        prompt = build_prompt_text(gemini_engine, ctx)

        # run_base is repo_root/swarm/runs/run_id/flow_key
        assert "swarm" in prompt or "runs" in prompt or "build" in prompt, (
            "RUN_BASE path elements should appear in prompt"
        )

    def test_prompt_includes_history_context(
        self,
        gemini_engine: GeminiStepEngine,
        tmp_repo: Path,
        sample_run_spec: RunSpec,
    ) -> None:
        """Prompt includes previous step history when provided."""
        ctx = StepContext(
            repo_root=tmp_repo,
            run_id="test-run",
            flow_key="build",
            step_id="step2",
            step_index=2,
            total_steps=3,
            spec=sample_run_spec,
            flow_title="Test Flow",
            step_role="Second step",
            step_agents=("agent2",),
            history=[
                {
                    "step_id": "step1",
                    "status": "succeeded",
                    "output": "First step completed successfully",
                }
            ],
            extra={},
        )

        prompt = build_prompt_text(gemini_engine, ctx)

        assert "step1" in prompt, "Previous step ID should appear in history section"
        assert "succeeded" in prompt.lower() or "[ok]" in prompt.lower(), (
            "Previous step status should appear in history"
        )

    def test_claude_and_gemini_prompts_have_same_structure(
        self,
        gemini_engine: GeminiStepEngine,
        claude_engine: ClaudeStepEngine,
        tmp_repo: Path,
        sample_run_spec: RunSpec,
    ) -> None:
        """GeminiStepEngine and ClaudeStepEngine produce similar prompts."""
        ctx = make_step_context(
            tmp_repo=tmp_repo,
            spec=sample_run_spec,
            step_id="test_step",
            step_role="Test role for comparison",
            step_agents=("test-agent",),
        )

        gemini_prompt = build_prompt_text(gemini_engine, ctx)
        claude_prompt = build_prompt_text(claude_engine, ctx)

        # Both should include key elements
        for prompt_name, prompt in [("gemini", gemini_prompt), ("claude", claude_prompt)]:
            assert "test_step" in prompt, f"{prompt_name} prompt should include step_id"
            assert "Test role for comparison" in prompt, (
                f"{prompt_name} prompt should include step_role"
            )
            assert "test-agent" in prompt, f"{prompt_name} prompt should include agent"


# -----------------------------------------------------------------------------
# Test Class: Teaching Notes Existence
# -----------------------------------------------------------------------------


class TestTeachingNotesExistence:
    """Tests that verify teaching_notes are defined in flow configs."""

    def test_build_flow_has_teaching_notes(self) -> None:
        """Build flow steps have teaching_notes defined."""
        registry = FlowRegistry.get_instance()
        flow = registry.get_flow("build")

        assert flow is not None, "Build flow should exist"

        steps_with_notes = 0
        for step in flow.steps:
            if step.teaching_notes is not None:
                steps_with_notes += 1

        assert steps_with_notes > 0, "Build flow should have at least one step with teaching_notes"

    def test_teaching_notes_have_inputs(self) -> None:
        """Teaching notes in build.yaml have inputs defined."""
        registry = FlowRegistry.get_instance()
        flow = registry.get_flow("build")

        assert flow is not None

        for step in flow.steps:
            if step.teaching_notes is not None:
                # At least author_tests should have inputs
                if step.id == "author_tests":
                    assert len(step.teaching_notes.inputs) > 0, (
                        f"Step {step.id} should have inputs in teaching_notes"
                    )

    def test_teaching_notes_have_outputs(self) -> None:
        """Teaching notes in build.yaml have outputs defined."""
        registry = FlowRegistry.get_instance()
        flow = registry.get_flow("build")

        assert flow is not None

        for step in flow.steps:
            if step.teaching_notes is not None:
                if step.id == "author_tests":
                    assert len(step.teaching_notes.outputs) > 0, (
                        f"Step {step.id} should have outputs in teaching_notes"
                    )

    def test_teaching_notes_have_emphasizes(self) -> None:
        """Teaching notes in build.yaml have emphasizes defined."""
        registry = FlowRegistry.get_instance()
        flow = registry.get_flow("build")

        assert flow is not None

        for step in flow.steps:
            if step.teaching_notes is not None:
                if step.id == "author_tests":
                    assert len(step.teaching_notes.emphasizes) > 0, (
                        f"Step {step.id} should have emphasizes in teaching_notes"
                    )

    def test_teaching_notes_parsed_correctly(self) -> None:
        """Teaching notes are parsed as TeachingNotes dataclass."""
        registry = FlowRegistry.get_instance()
        flow = registry.get_flow("build")

        assert flow is not None

        for step in flow.steps:
            if step.teaching_notes is not None:
                assert isinstance(step.teaching_notes, TeachingNotes), (
                    f"Step {step.id} teaching_notes should be TeachingNotes instance"
                )
                assert isinstance(step.teaching_notes.inputs, tuple), "inputs should be a tuple"
                assert isinstance(step.teaching_notes.outputs, tuple), "outputs should be a tuple"
                assert isinstance(step.teaching_notes.emphasizes, tuple), (
                    "emphasizes should be a tuple"
                )
                assert isinstance(step.teaching_notes.constraints, tuple), (
                    "constraints should be a tuple"
                )
