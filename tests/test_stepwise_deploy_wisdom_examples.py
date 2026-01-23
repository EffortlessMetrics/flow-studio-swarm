"""Tests for stepwise Deploy and Wisdom golden examples.

These tests validate the structure and content of the stepwise Deploy and
full SDLC (including Wisdom) golden examples.
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

EXAMPLES_DIR = repo_root / "swarm" / "examples"

# -----------------------------------------------------------------------------
# Example Existence Tests
# -----------------------------------------------------------------------------


class TestDeployExampleExists:
    """Verify stepwise-deploy-claude example exists with expected structure."""

    @pytest.fixture
    def deploy_example(self) -> Path:
        return EXAMPLES_DIR / "stepwise-deploy-claude"

    def test_example_directory_exists(self, deploy_example: Path) -> None:
        """Example directory should exist."""
        assert deploy_example.exists(), f"Missing: {deploy_example}"
        assert deploy_example.is_dir()

    def test_has_required_root_files(self, deploy_example: Path) -> None:
        """Example should have spec.json, meta.json, events.jsonl."""
        assert (deploy_example / "spec.json").exists()
        assert (deploy_example / "meta.json").exists()
        assert (deploy_example / "events.jsonl").exists()
        assert (deploy_example / "README.md").exists()

    def test_has_flow_directories(self, deploy_example: Path) -> None:
        """Example should have directories for all included flows."""
        for flow in ["signal", "plan", "build", "gate", "deploy"]:
            flow_dir = deploy_example / flow
            assert flow_dir.exists(), f"Missing flow directory: {flow}"
            assert (flow_dir / "llm").exists(), f"Missing llm/ in {flow}"
            assert (flow_dir / "receipts").exists(), f"Missing receipts/ in {flow}"

    def test_deploy_flow_has_receipts(self, deploy_example: Path) -> None:
        """Deploy flow should have receipts for all 5 steps."""
        receipts_dir = deploy_example / "deploy" / "receipts"
        receipt_files = list(receipts_dir.glob("*.json"))
        assert len(receipt_files) >= 5, f"Expected 5 deploy receipts, got {len(receipt_files)}"

    def test_spec_includes_deploy_flow(self, deploy_example: Path) -> None:
        """spec.json should include deploy in flow_keys."""
        with open(deploy_example / "spec.json") as f:
            spec = json.load(f)
        assert "deploy" in spec.get("flow_keys", [])

    def test_meta_has_succeeded_status(self, deploy_example: Path) -> None:
        """meta.json should show succeeded status."""
        with open(deploy_example / "meta.json") as f:
            meta = json.load(f)
        assert meta.get("status") == "succeeded"


class TestSDLCExampleExists:
    """Verify stepwise-sdlc-claude example exists with expected structure."""

    @pytest.fixture
    def sdlc_example(self) -> Path:
        return EXAMPLES_DIR / "stepwise-sdlc-claude"

    def test_example_directory_exists(self, sdlc_example: Path) -> None:
        """Example directory should exist."""
        assert sdlc_example.exists(), f"Missing: {sdlc_example}"
        assert sdlc_example.is_dir()

    def test_has_required_root_files(self, sdlc_example: Path) -> None:
        """Example should have spec.json, meta.json, events.jsonl."""
        assert (sdlc_example / "spec.json").exists()
        assert (sdlc_example / "meta.json").exists()
        assert (sdlc_example / "events.jsonl").exists()
        assert (sdlc_example / "README.md").exists()

    def test_has_all_six_flow_directories(self, sdlc_example: Path) -> None:
        """Example should have directories for all 6 flows."""
        for flow in ["signal", "plan", "build", "gate", "deploy", "wisdom"]:
            flow_dir = sdlc_example / flow
            assert flow_dir.exists(), f"Missing flow directory: {flow}"
            assert (flow_dir / "llm").exists(), f"Missing llm/ in {flow}"
            assert (flow_dir / "receipts").exists(), f"Missing receipts/ in {flow}"

    def test_wisdom_flow_has_receipts(self, sdlc_example: Path) -> None:
        """Wisdom flow should have receipts for all 6 steps."""
        receipts_dir = sdlc_example / "wisdom" / "receipts"
        receipt_files = list(receipts_dir.glob("*.json"))
        assert len(receipt_files) >= 6, f"Expected 6 wisdom receipts, got {len(receipt_files)}"

    def test_spec_includes_all_flows(self, sdlc_example: Path) -> None:
        """spec.json should include all 6 flows."""
        with open(sdlc_example / "spec.json") as f:
            spec = json.load(f)
        expected_flows = ["signal", "plan", "build", "gate", "deploy", "wisdom"]
        for flow in expected_flows:
            assert flow in spec.get("flow_keys", []), f"Missing {flow} in flow_keys"

    def test_meta_has_succeeded_status(self, sdlc_example: Path) -> None:
        """meta.json should show succeeded status."""
        with open(sdlc_example / "meta.json") as f:
            meta = json.load(f)
        assert meta.get("status") == "succeeded"


# -----------------------------------------------------------------------------
# Content Validation Tests
# -----------------------------------------------------------------------------


class TestDeployReceiptContent:
    """Validate Deploy flow receipt content."""

    @pytest.fixture
    def deploy_receipts(self) -> Path:
        return EXAMPLES_DIR / "stepwise-deploy-claude" / "deploy" / "receipts"

    def test_receipts_have_correct_flow_key(self, deploy_receipts: Path) -> None:
        """All deploy receipts should have flow_key='deploy'."""
        for receipt_file in deploy_receipts.glob("*.json"):
            with open(receipt_file) as f:
                receipt = json.load(f)
            assert receipt.get("flow_key") == "deploy", f"Wrong flow_key in {receipt_file.name}"

    def test_receipts_have_engine_metadata(self, deploy_receipts: Path) -> None:
        """All deploy receipts should have engine, mode, provider."""
        for receipt_file in deploy_receipts.glob("*.json"):
            with open(receipt_file) as f:
                receipt = json.load(f)
            assert "engine" in receipt, f"Missing engine in {receipt_file.name}"
            assert "mode" in receipt, f"Missing mode in {receipt_file.name}"
            assert "provider" in receipt, f"Missing provider in {receipt_file.name}"


class TestWisdomReceiptContent:
    """Validate Wisdom flow receipt content."""

    @pytest.fixture
    def wisdom_receipts(self) -> Path:
        return EXAMPLES_DIR / "stepwise-sdlc-claude" / "wisdom" / "receipts"

    def test_receipts_have_correct_flow_key(self, wisdom_receipts: Path) -> None:
        """All wisdom receipts should have flow_key='wisdom'."""
        for receipt_file in wisdom_receipts.glob("*.json"):
            with open(receipt_file) as f:
                receipt = json.load(f)
            assert receipt.get("flow_key") == "wisdom", f"Wrong flow_key in {receipt_file.name}"

    def test_receipts_have_engine_metadata(self, wisdom_receipts: Path) -> None:
        """All wisdom receipts should have engine, mode, provider."""
        for receipt_file in wisdom_receipts.glob("*.json"):
            with open(receipt_file) as f:
                receipt = json.load(f)
            assert "engine" in receipt, f"Missing engine in {receipt_file.name}"
            assert "mode" in receipt, f"Missing mode in {receipt_file.name}"
            assert "provider" in receipt, f"Missing provider in {receipt_file.name}"


# -----------------------------------------------------------------------------
# Events Stream Tests
# -----------------------------------------------------------------------------


class TestEventsStream:
    """Validate events.jsonl content in examples."""

    def test_deploy_events_contain_deploy_steps(self) -> None:
        """Deploy example events should contain deploy flow events."""
        events_file = EXAMPLES_DIR / "stepwise-deploy-claude" / "events.jsonl"
        with open(events_file) as f:
            events = [json.loads(line) for line in f if line.strip()]

        deploy_events = [e for e in events if e.get("flow_key") == "deploy"]
        assert len(deploy_events) > 0, "No deploy events found"

        # Check for step_start events in deploy flow
        deploy_starts = [e for e in deploy_events if e.get("kind") == "step_start"]
        assert len(deploy_starts) >= 5, (
            f"Expected 5 deploy step_start events, got {len(deploy_starts)}"
        )

    def test_sdlc_events_contain_wisdom_steps(self) -> None:
        """Full SDLC example events should contain wisdom flow events."""
        events_file = EXAMPLES_DIR / "stepwise-sdlc-claude" / "events.jsonl"
        with open(events_file) as f:
            events = [json.loads(line) for line in f if line.strip()]

        wisdom_events = [e for e in events if e.get("flow_key") == "wisdom"]
        assert len(wisdom_events) > 0, "No wisdom events found"

        # Check for step_start events in wisdom flow
        wisdom_starts = [e for e in wisdom_events if e.get("kind") == "step_start"]
        assert len(wisdom_starts) >= 6, (
            f"Expected 6 wisdom step_start events, got {len(wisdom_starts)}"
        )

    def test_route_decision_events_exist(self) -> None:
        """Both examples should have route_decision events."""
        for example_name in ["stepwise-deploy-claude", "stepwise-sdlc-claude"]:
            events_file = EXAMPLES_DIR / example_name / "events.jsonl"
            with open(events_file) as f:
                events = [json.loads(line) for line in f if line.strip()]

            route_decisions = [e for e in events if e.get("kind") == "route_decision"]
            assert len(route_decisions) > 0, f"No route_decision events in {example_name}"
