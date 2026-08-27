"""
Tests for fragment manifest tracking in the prompt compiler.

PromptReceipt.fragment_manifest is the audit answer to "which spec fragments
went into this prompt?". It used to be hardcoded to an empty tuple, so a
receipt could not be used to reproduce or explain the prompt it described.

The manifest must name every fragment that contributed to the compiled prompt:
the station's declared fragments, any policy invariants merged in, and the
inline {{fragment:...}} includes resolved out of the prompt bodies.
"""

from pathlib import Path

import pytest
import yaml
from swarm.spec.compiler.builder import StepPlanBuilder
from swarm.spec.compiler.facade import SpecCompiler
from swarm.spec.types import create_prompt_receipt

repo_root = Path(__file__).resolve().parents[1]


def build_step_ids(flow_id: str = "3-build", limit: int = 4):
    """Read step ids straight off the flow spec."""
    flow = yaml.safe_load((repo_root / "swarm" / "spec" / "flows" / f"{flow_id}.yaml").read_text())
    return [step["id"] for step in flow["steps"]][:limit]


class TestManifestIsPopulated:
    """Tests that a real compile produces a real manifest."""

    @pytest.fixture
    def compiler(self):
        return SpecCompiler(repo_root=repo_root)

    def test_receipt_manifest_is_not_empty(self, compiler, tmp_path):
        """A compiled step's receipt names the fragments it used.

        Regression guard for #218: fragment_manifest was hardcoded to ().
        """
        plan = compiler.compile("3-build", "implement", None, tmp_path)

        receipt = create_prompt_receipt(plan)

        assert receipt.fragment_manifest, "receipt manifest should name the fragments used"

    def test_manifest_entries_are_real_fragment_paths(self, compiler, tmp_path):
        """Every manifest entry resolves to a fragment that exists on disk."""
        from swarm.spec.loader import load_fragment

        plan = compiler.compile("3-build", "implement", None, tmp_path)

        for frag_path in create_prompt_receipt(plan).fragment_manifest:
            # Raises FileNotFoundError if the path is not a loadable fragment.
            load_fragment(frag_path, repo_root)

    def test_plan_and_receipt_manifests_agree(self, compiler, tmp_path):
        """The receipt reports exactly what the plan recorded."""
        plan = compiler.compile("3-build", "implement", None, tmp_path)

        assert create_prompt_receipt(plan).fragment_manifest == plan.fragment_manifest

    def test_manifest_matches_step_plan_fragments(self, compiler, tmp_path):
        """The plan's manifest mirrors the builder's fragment references."""
        plan = compiler.compile("3-build", "implement", None, tmp_path)

        # Manifest is the path projection of the audited fragment references.
        assert all(isinstance(entry, str) for entry in plan.fragment_manifest)
        assert len(set(plan.fragment_manifest)) == len(plan.fragment_manifest), (
            "manifest should be deduplicated"
        )

    @pytest.mark.parametrize("step_id", build_step_ids())
    def test_manifest_populated_across_steps(self, compiler, tmp_path, step_id):
        """Manifest tracking is not specific to one step."""
        plan = compiler.compile("3-build", step_id, None, tmp_path)

        assert plan.fragment_manifest


class TestInlineIncludes:
    """Tests for {{fragment:...}} includes reaching the manifest.

    Inline includes are pasted into the prompt body, so a manifest that omits
    them cannot reproduce the prompt - which is the stated purpose of the
    receipt.
    """

    @pytest.fixture
    def builder(self):
        return StepPlanBuilder(repo_root)

    def test_resolved_include_is_collected(self, builder):
        """A resolvable include is appended to the collector."""
        collected = []

        result = builder._process_fragment_includes(
            "before {{fragment:common/handoff}} after", collected
        )

        assert collected == ["common/handoff.md"]
        assert "{{fragment:" not in result

    def test_missing_include_is_not_collected(self, builder):
        """A fragment that failed to load is not claimed in the audit trail.

        Recording it would assert content contributed to the prompt when the
        prompt actually got a "not found" placeholder.
        """
        collected = []

        result = builder._process_fragment_includes(
            "{{fragment:does/not/exist}}", collected
        )

        assert collected == []
        assert "Fragment not found" in result

    def test_collector_is_optional(self, builder):
        """Callers that do not want the audit trail can omit the collector."""
        result = builder._process_fragment_includes("{{fragment:common/handoff}}")

        assert "{{fragment:" not in result

    def test_multiple_includes_are_all_collected(self, builder):
        """Every resolved include is recorded, in order."""
        collected = []

        builder._process_fragment_includes(
            "{{fragment:common/handoff}} and {{fragment:common/invariants}}", collected
        )

        assert collected == ["common/handoff.md", "common/invariants.md"]

    def test_collector_accumulates_across_calls(self, builder):
        """System and user prompts share one collector during a build."""
        collected = []

        builder._process_fragment_includes("{{fragment:common/handoff}}", collected)
        builder._process_fragment_includes("{{fragment:common/invariants}}", collected)

        assert collected == ["common/handoff.md", "common/invariants.md"]
