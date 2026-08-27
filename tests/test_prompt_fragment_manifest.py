"""
Tests for fragment manifest tracking in the prompt compiler (issue #218).

A PromptReceipt must record which fragments contributed to a compiled prompt,
and at what content hash, so a prompt can be traced back to its sources from
the receipt alone.

Coverage:
- fragment_manifest_from_plan renders `path@hash` audit entries
- the builder records inline {{fragment:...}} includes, not just declared ones
- PromptPlan carries the manifest through to create_prompt_receipt
"""

from swarm.spec.compiler.builder import StepPlanBuilder
from swarm.spec.compiler.models import FragmentReference, StepPlan, fragment_manifest_from_plan
from swarm.spec.types import PromptPlan, VerificationRequirements, create_prompt_receipt


def make_step_plan(**overrides) -> StepPlan:
    """Build a minimal StepPlan for manifest tests."""
    defaults = dict(
        step_id="3",
        station_id="code-implementer",
        system_prompt="",
        user_prompt="",
        allowed_tools=(),
        permission_mode="default",
        max_turns=1,
        output_schema={},
        prompt_hash="hash",
        prompt_hash_v2="hash2",
    )
    defaults.update(overrides)
    return StepPlan(**defaults)


class TestFragmentManifestFromPlan:
    """Tests for fragment_manifest_from_plan()."""

    def test_renders_path_at_hash(self):
        plan = make_step_plan(
            fragments_used=(
                FragmentReference(path="git_safety_rules.md", hash="abc123", version=""),
            )
        )

        assert fragment_manifest_from_plan(plan) == ("git_safety_rules.md@abc123",)

    def test_hashless_fragment_degrades_to_bare_path(self):
        """A fragment without a hash is still recorded, not dropped."""
        plan = make_step_plan(
            fragments_used=(FragmentReference(path="output_format.md", hash="", version=""),)
        )

        assert fragment_manifest_from_plan(plan) == ("output_format.md",)

    def test_preserves_order(self):
        plan = make_step_plan(
            fragments_used=(
                FragmentReference(path="b.md", hash="2", version=""),
                FragmentReference(path="a.md", hash="1", version=""),
            )
        )

        assert fragment_manifest_from_plan(plan) == ("b.md@2", "a.md@1")

    def test_empty_when_no_fragments(self):
        assert fragment_manifest_from_plan(make_step_plan()) == ()

    def test_distinguishes_same_path_at_different_content(self):
        """The hash is what makes a receipt reproducible, not just the path."""
        before = make_step_plan(
            fragments_used=(FragmentReference(path="f.md", hash="aaa", version=""),)
        )
        after = make_step_plan(
            fragments_used=(FragmentReference(path="f.md", hash="bbb", version=""),)
        )

        assert fragment_manifest_from_plan(before) != fragment_manifest_from_plan(after)


class TestInlineIncludeTracking:
    """The builder records inline {{fragment:...}} includes for audit."""

    def test_reports_resolved_include(self, tmp_path):
        frag_dir = tmp_path / "swarm" / "specs" / "fragments"
        frag_dir.mkdir(parents=True)
        (frag_dir / "git_safety_rules.md").write_text("SAFE GIT", encoding="utf-8")

        builder = StepPlanBuilder(tmp_path)
        rendered, resolved = builder._process_fragment_includes(
            "before {{fragment:git_safety_rules}} after"
        )

        assert "SAFE GIT" in rendered
        assert resolved == ["git_safety_rules.md"]

    def test_missing_include_is_not_recorded(self, tmp_path):
        """An unresolved include must not appear in the audit manifest."""
        (tmp_path / "swarm" / "specs" / "fragments").mkdir(parents=True)

        builder = StepPlanBuilder(tmp_path)
        rendered, resolved = builder._process_fragment_includes("{{fragment:nope}}")

        assert "Fragment not found" in rendered
        assert resolved == []

    def test_no_includes_yields_empty_list(self, tmp_path):
        builder = StepPlanBuilder(tmp_path)
        rendered, resolved = builder._process_fragment_includes("plain prompt")

        assert rendered == "plain prompt"
        assert resolved == []

    def test_records_each_occurrence(self, tmp_path):
        frag_dir = tmp_path / "swarm" / "specs" / "fragments"
        frag_dir.mkdir(parents=True)
        (frag_dir / "a.md").write_text("A", encoding="utf-8")
        (frag_dir / "b.md").write_text("B", encoding="utf-8")

        builder = StepPlanBuilder(tmp_path)
        _, resolved = builder._process_fragment_includes(
            "{{fragment:a}} {{fragment:b}} {{fragment:a}}"
        )

        assert resolved == ["a.md", "b.md", "a.md"]


class TestReceiptCarriesManifest:
    """create_prompt_receipt propagates the manifest from the plan."""

    def make_prompt_plan(self, manifest) -> PromptPlan:
        return PromptPlan(
            station_id="code-implementer",
            station_version=1,
            flow_id="3-build",
            flow_version=1,
            step_id="3",
            prompt_hash="hash",
            model="claude-sonnet-4",
            permission_mode="default",
            allowed_tools=("Read", "Write"),
            max_turns=10,
            sandbox_enabled=True,
            cwd=".",
            system_append="",
            user_prompt="",
            compiled_at="2026-01-01T00:00:00+00:00",
            context_pack_size=0,
            verification=VerificationRequirements(),
            fragment_manifest=manifest,
        )

    def test_manifest_reaches_the_receipt(self):
        plan = self.make_prompt_plan(("git_safety_rules.md@abc123", "output_format.md@def456"))

        receipt = create_prompt_receipt(plan)

        assert receipt.fragment_manifest == (
            "git_safety_rules.md@abc123",
            "output_format.md@def456",
        )

    def test_empty_manifest_is_preserved(self):
        receipt = create_prompt_receipt(self.make_prompt_plan(()))

        assert receipt.fragment_manifest == ()

    def test_default_plan_has_empty_manifest(self):
        """PromptPlan without an explicit manifest still constructs."""
        plan = PromptPlan(
            station_id="s",
            station_version=1,
            flow_id="3-build",
            flow_version=1,
            step_id="3",
            prompt_hash="hash",
            model="claude-sonnet-4",
            permission_mode="default",
            allowed_tools=(),
            max_turns=1,
            sandbox_enabled=True,
            cwd=".",
            system_append="",
            user_prompt="",
            compiled_at="2026-01-01T00:00:00+00:00",
            context_pack_size=0,
        )

        assert plan.fragment_manifest == ()
        assert create_prompt_receipt(plan).fragment_manifest == ()
