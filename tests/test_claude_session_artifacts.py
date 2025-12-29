"""Tests for Claude session artifacts and decision parsing.

These tests pin the invariants introduced in the session_runner refactor:
1. parse_routing_decision handles canonical values and aliases
2. Session execution writes committed envelope at canonical path
3. repo_root fallback (engine.repo_root or ctx.repo_root) works correctly
"""

import pytest
from pathlib import Path

from swarm.runtime.types import RoutingDecision
from swarm.runtime.engines.claude.session_runner import parse_routing_decision


class TestParseRoutingDecision:
    """Tests for routing decision parsing with alias support."""

    def test_canonical_advance(self):
        """Canonical 'advance' maps to ADVANCE."""
        assert parse_routing_decision("advance") == RoutingDecision.ADVANCE

    def test_canonical_loop(self):
        """Canonical 'loop' maps to LOOP."""
        assert parse_routing_decision("loop") == RoutingDecision.LOOP

    def test_canonical_terminate(self):
        """Canonical 'terminate' maps to TERMINATE."""
        assert parse_routing_decision("terminate") == RoutingDecision.TERMINATE

    def test_canonical_branch(self):
        """Canonical 'branch' maps to BRANCH."""
        assert parse_routing_decision("branch") == RoutingDecision.BRANCH

    def test_alias_proceed(self):
        """Alias 'proceed' maps to ADVANCE."""
        assert parse_routing_decision("proceed") == RoutingDecision.ADVANCE

    def test_alias_continue(self):
        """Alias 'continue' maps to ADVANCE."""
        assert parse_routing_decision("continue") == RoutingDecision.ADVANCE

    def test_alias_next(self):
        """Alias 'next' maps to ADVANCE."""
        assert parse_routing_decision("next") == RoutingDecision.ADVANCE

    def test_alias_rerun(self):
        """Alias 'rerun' maps to LOOP."""
        assert parse_routing_decision("rerun") == RoutingDecision.LOOP

    def test_alias_retry(self):
        """Alias 'retry' maps to LOOP."""
        assert parse_routing_decision("retry") == RoutingDecision.LOOP

    def test_alias_repeat(self):
        """Alias 'repeat' maps to LOOP."""
        assert parse_routing_decision("repeat") == RoutingDecision.LOOP

    def test_alias_blocked(self):
        """Alias 'blocked' maps to TERMINATE."""
        assert parse_routing_decision("blocked") == RoutingDecision.TERMINATE

    def test_alias_stop(self):
        """Alias 'stop' maps to TERMINATE."""
        assert parse_routing_decision("stop") == RoutingDecision.TERMINATE

    def test_alias_end(self):
        """Alias 'end' maps to TERMINATE."""
        assert parse_routing_decision("end") == RoutingDecision.TERMINATE

    def test_alias_exit(self):
        """Alias 'exit' maps to TERMINATE."""
        assert parse_routing_decision("exit") == RoutingDecision.TERMINATE

    def test_alias_route(self):
        """Alias 'route' maps to BRANCH."""
        assert parse_routing_decision("route") == RoutingDecision.BRANCH

    def test_alias_switch(self):
        """Alias 'switch' maps to BRANCH."""
        assert parse_routing_decision("switch") == RoutingDecision.BRANCH

    def test_alias_redirect(self):
        """Alias 'redirect' maps to BRANCH."""
        assert parse_routing_decision("redirect") == RoutingDecision.BRANCH

    def test_case_insensitive(self):
        """Parsing is case-insensitive."""
        assert parse_routing_decision("ADVANCE") == RoutingDecision.ADVANCE
        assert parse_routing_decision("Proceed") == RoutingDecision.ADVANCE
        assert parse_routing_decision("LOOP") == RoutingDecision.LOOP
        assert parse_routing_decision("Rerun") == RoutingDecision.LOOP

    def test_whitespace_stripped(self):
        """Leading/trailing whitespace is stripped."""
        assert parse_routing_decision("  advance  ") == RoutingDecision.ADVANCE
        assert parse_routing_decision("\tproceed\n") == RoutingDecision.ADVANCE

    def test_unknown_defaults_to_advance(self):
        """Unknown values default to ADVANCE."""
        assert parse_routing_decision("unknown") == RoutingDecision.ADVANCE
        assert parse_routing_decision("foobar") == RoutingDecision.ADVANCE
        assert parse_routing_decision("") == RoutingDecision.ADVANCE


class TestRepoRootFallback:
    """Tests for repo_root fallback behavior in ClaudeStepEngine."""

    def test_engine_uses_own_repo_root_when_set(self):
        """Engine uses self.repo_root when set."""
        from swarm.runtime.engines.claude.engine import ClaudeStepEngine

        engine = ClaudeStepEngine(repo_root=Path("/custom/path"), mode="stub")
        assert engine.repo_root == Path("/custom/path")

    def test_engine_repo_root_can_be_none(self):
        """Engine accepts repo_root=None and doesn't crash."""
        from swarm.runtime.engines.claude.engine import ClaudeStepEngine

        engine = ClaudeStepEngine(repo_root=None, mode="stub")
        assert engine.repo_root is None

    def test_hydrate_context_uses_ctx_repo_root_as_fallback(self):
        """_hydrate_context falls back to ctx.repo_root when engine.repo_root is None."""
        from swarm.runtime.engines.claude.engine import ClaudeStepEngine
        from swarm.runtime.engines.models import StepContext
        from swarm.runtime.types import RunSpec
        import tempfile

        engine = ClaudeStepEngine(repo_root=None, mode="stub")

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create minimal RunSpec
            spec = RunSpec(flow_keys=["signal"])

            ctx = StepContext(
                repo_root=Path(tmpdir),
                run_id="test-run",
                flow_key="signal",
                step_id="1-normalize",
                step_index=1,
                total_steps=6,
                spec=spec,
                flow_title="Signal to Specs",
                step_role="signal-normalizer",
                step_agents=("signal-normalizer",),
                extra={},
            )

            # This should not crash - it should use ctx.repo_root
            hydrated = engine._hydrate_context(ctx)
            # ContextPack may or may not be built depending on existing envelopes,
            # but the call should complete without error
            assert hydrated is not None


class TestSessionEnvelopePaths:
    """Tests for envelope path handling in session execution."""

    def test_committed_envelope_path_format(self):
        """Committed envelope path follows canonical format."""
        from swarm.runtime.path_helpers import handoff_envelope_path
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            run_base = Path(tmpdir)
            step_id = "1-normalize"

            path = handoff_envelope_path(run_base, step_id)

            assert path.name == "1-normalize.json"
            assert "handoff" in str(path)
            assert path.parent.name == "handoff"

    def test_draft_vs_committed_envelope_distinction(self):
        """Draft and committed envelopes have distinct paths."""
        from swarm.runtime.path_helpers import handoff_envelope_path
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            run_base = Path(tmpdir)
            step_id = "1-normalize"

            committed_path = handoff_envelope_path(run_base, step_id)
            draft_path = run_base / "handoff" / f"{step_id}.draft.json"

            assert committed_path != draft_path
            assert "draft" not in committed_path.name
            assert "draft" in draft_path.name
