"""Tests for stepwise build golden examples.

This module validates that the golden stepwise build examples exist and have
the expected structure. These examples demonstrate full Signal -> Plan -> Build
SDLC runs for both Gemini and Claude backends.

## Test Coverage

### Example Existence (2 tests)
1. test_stepwise_build_gemini_exists - Verify stepwise-build-gemini/ exists
2. test_stepwise_build_claude_exists - Verify stepwise-build-claude/ exists

### Example Structure (4 tests)
3. test_gemini_example_has_required_files - spec.json, meta.json, events.jsonl
4. test_claude_example_has_required_files - spec.json, meta.json, events.jsonl
5. test_claude_example_has_flow_directories - signal/, plan/, build/ dirs
6. test_claude_example_has_transcripts_and_receipts - llm/ and receipts/ subdirs

### Content Validation (4 tests)
7. test_gemini_events_contain_build_steps - events.jsonl has build flow events
8. test_claude_receipts_have_build_steps - build/receipts/ has step receipts
9. test_spec_contains_build_flow - spec.json includes "build" in flow_keys
10. test_meta_has_succeeded_status - meta.json shows succeeded status
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Add repo root to path for imports
repo_root = Path(__file__).resolve().parents[1]
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

# Example directories
EXAMPLES_DIR = repo_root / "swarm" / "examples"
GEMINI_BUILD_EXAMPLE = EXAMPLES_DIR / "stepwise-build-gemini"
CLAUDE_BUILD_EXAMPLE = EXAMPLES_DIR / "stepwise-build-claude"


# -----------------------------------------------------------------------------
# Test Class: Example Existence
# -----------------------------------------------------------------------------


class TestExampleExistence:
    """Tests that golden examples exist."""

    def test_stepwise_build_gemini_exists(self) -> None:
        """stepwise-build-gemini/ directory exists."""
        assert GEMINI_BUILD_EXAMPLE.exists(), (
            f"Golden example should exist at {GEMINI_BUILD_EXAMPLE}"
        )
        assert GEMINI_BUILD_EXAMPLE.is_dir(), (
            f"Golden example should be a directory at {GEMINI_BUILD_EXAMPLE}"
        )

    def test_stepwise_build_claude_exists(self) -> None:
        """stepwise-build-claude/ directory exists."""
        assert CLAUDE_BUILD_EXAMPLE.exists(), (
            f"Golden example should exist at {CLAUDE_BUILD_EXAMPLE}"
        )
        assert CLAUDE_BUILD_EXAMPLE.is_dir(), (
            f"Golden example should be a directory at {CLAUDE_BUILD_EXAMPLE}"
        )


# -----------------------------------------------------------------------------
# Test Class: Example Structure
# -----------------------------------------------------------------------------


class TestExampleStructure:
    """Tests for golden example directory structure."""

    REQUIRED_FILES = ["spec.json", "meta.json", "events.jsonl", "README.md"]

    def test_gemini_example_has_required_files(self) -> None:
        """stepwise-build-gemini/ has all required files."""
        for filename in self.REQUIRED_FILES:
            filepath = GEMINI_BUILD_EXAMPLE / filename
            assert filepath.exists(), (
                f"Required file '{filename}' should exist in {GEMINI_BUILD_EXAMPLE}"
            )

    def test_claude_example_has_required_files(self) -> None:
        """stepwise-build-claude/ has all required files."""
        for filename in self.REQUIRED_FILES:
            filepath = CLAUDE_BUILD_EXAMPLE / filename
            assert filepath.exists(), (
                f"Required file '{filename}' should exist in {CLAUDE_BUILD_EXAMPLE}"
            )

    def test_claude_example_has_flow_directories(self) -> None:
        """stepwise-build-claude/ has signal/, plan/, build/ directories."""
        flow_dirs = ["signal", "plan", "build"]
        for flow_dir in flow_dirs:
            dirpath = CLAUDE_BUILD_EXAMPLE / flow_dir
            assert dirpath.exists(), (
                f"Flow directory '{flow_dir}/' should exist in {CLAUDE_BUILD_EXAMPLE}"
            )
            assert dirpath.is_dir(), f"'{flow_dir}' should be a directory in {CLAUDE_BUILD_EXAMPLE}"

    def test_claude_example_has_transcripts_and_receipts(self) -> None:
        """stepwise-build-claude/ flow directories have llm/ and receipts/ subdirs."""
        for flow in ["signal", "plan", "build"]:
            llm_dir = CLAUDE_BUILD_EXAMPLE / flow / "llm"
            receipts_dir = CLAUDE_BUILD_EXAMPLE / flow / "receipts"

            assert llm_dir.exists(), f"Transcript directory should exist at {llm_dir}"
            assert receipts_dir.exists(), f"Receipts directory should exist at {receipts_dir}"

            # Should have at least one file in each
            llm_files = list(llm_dir.glob("*.jsonl"))
            receipt_files = list(receipts_dir.glob("*.json"))

            assert len(llm_files) > 0, f"Should have at least one transcript in {llm_dir}"
            assert len(receipt_files) > 0, f"Should have at least one receipt in {receipts_dir}"


# -----------------------------------------------------------------------------
# Test Class: Content Validation
# -----------------------------------------------------------------------------


class TestContentValidation:
    """Tests for golden example content."""

    def test_gemini_events_contain_build_steps(self) -> None:
        """events.jsonl in Gemini example contains build flow events."""
        events_file = GEMINI_BUILD_EXAMPLE / "events.jsonl"

        with events_file.open("r", encoding="utf-8") as f:
            events = [json.loads(line) for line in f if line.strip()]

        # Should have events for build flow
        build_events = [e for e in events if e.get("flow_key") == "build"]
        assert len(build_events) > 0, "events.jsonl should contain events with flow_key='build'"

        # Should have step_start and step_end events
        step_starts = [e for e in events if e.get("kind") == "step_start"]
        step_ends = [e for e in events if e.get("kind") == "step_end"]

        assert len(step_starts) > 0, "Should have step_start events"
        assert len(step_ends) > 0, "Should have step_end events"

    def test_claude_receipts_have_build_steps(self) -> None:
        """build/receipts/ in Claude example has receipts for build steps."""
        receipts_dir = CLAUDE_BUILD_EXAMPLE / "build" / "receipts"
        receipt_files = list(receipts_dir.glob("*.json"))

        assert len(receipt_files) > 0, f"Should have receipts in {receipts_dir}"

        # Check at least one receipt has build-related content
        for receipt_file in receipt_files:
            with receipt_file.open("r", encoding="utf-8") as f:
                receipt = json.load(f)

            assert receipt.get("flow_key") == "build", (
                f"Receipt {receipt_file.name} should have flow_key='build'"
            )
            assert "step_id" in receipt, f"Receipt {receipt_file.name} should have step_id"
            assert "status" in receipt, f"Receipt {receipt_file.name} should have status"

    def test_spec_contains_build_flow(self) -> None:
        """spec.json includes 'build' in flow_keys."""
        for example_dir in [GEMINI_BUILD_EXAMPLE, CLAUDE_BUILD_EXAMPLE]:
            spec_file = example_dir / "spec.json"

            with spec_file.open("r", encoding="utf-8") as f:
                spec = json.load(f)

            assert "flow_keys" in spec, f"spec.json in {example_dir.name} should have flow_keys"
            assert "build" in spec["flow_keys"], (
                f"spec.json in {example_dir.name} should include 'build' flow"
            )

    def test_meta_has_succeeded_status(self) -> None:
        """meta.json shows succeeded status."""
        for example_dir in [GEMINI_BUILD_EXAMPLE, CLAUDE_BUILD_EXAMPLE]:
            meta_file = example_dir / "meta.json"

            with meta_file.open("r", encoding="utf-8") as f:
                meta = json.load(f)

            assert meta.get("status") == "succeeded", (
                f"meta.json in {example_dir.name} should have status='succeeded'"
            )

    def test_route_decision_events_exist(self) -> None:
        """events.jsonl contains route_decision events for microloops."""
        events_file = GEMINI_BUILD_EXAMPLE / "events.jsonl"

        with events_file.open("r", encoding="utf-8") as f:
            events = [json.loads(line) for line in f if line.strip()]

        route_decisions = [e for e in events if e.get("kind") == "route_decision"]
        assert len(route_decisions) > 0, "events.jsonl should contain route_decision events"

        # Check at least one microloop route decision exists
        microloop_decisions = [
            e for e in route_decisions if "loop" in e.get("payload", {}).get("reason", "").lower()
        ]
        # Microloops hit max_iterations in stub mode, so we should see those
        max_iter_decisions = [
            e
            for e in route_decisions
            if "max_iterations" in e.get("payload", {}).get("reason", "").lower()
        ]

        # Either should work - we're just verifying routing happened
        assert len(microloop_decisions) > 0 or len(max_iter_decisions) > 0, (
            "Should have microloop-related route_decision events"
        )
