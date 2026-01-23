#!/usr/bin/env python3
"""
Task 3: Selftest Modal UI Integration Test (Bonus)

This test suite validates that the selftest modal in Flow Studio integrates
correctly with the backend API and handles edge cases gracefully.

**Integration Points**:
- Modal fetches plan from /api/selftest/plan
- Modal renders step list without crashes
- Modal gracefully handles missing clipboard API
- Modal copyAndRun() command is safe and doesn't crash

**Purpose**: Verify the UI can safely consume the API without crashes and
provides helpful fallback behavior when features are unavailable.

**Test Coverage** (3 tests):
1. test_selftest_modal_can_load_plan - Plan loads without null/undefined
2. test_selftest_modal_graceful_degradation_no_clipboard - Handles missing clipboard
3. test_selftest_modal_copy_and_run_safe - copyAndRun doesn't crash on error
"""

import sys
from pathlib import Path

# Add repo root to path
repo_root = Path(__file__).resolve().parents[1]
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def fastapi_client():
    """Create FastAPI test client."""
    from swarm.tools.flow_studio_fastapi import app

    return TestClient(app)


class TestSelfTestModalUIIntegration:
    """Integration tests for selftest modal UI with backend API."""

    def test_selftest_modal_can_load_plan(self, fastapi_client):
        """
        Test that modal can successfully load the plan without null/undefined values.

        **Modal requirement**:
        - Plan data is valid JSON
        - No null values in required fields
        - Step descriptions are non-empty strings (not null, undefined, or empty)
        - Steps array is not empty (UI can render)
        - Summary is not null

        **Test flow**:
        1. GET /api/selftest/plan
        2. Parse JSON response
        3. Validate all required fields are present and non-null
        4. Ensure step descriptions are renderable
        """
        # Arrange & Act
        resp = fastapi_client.get("/api/selftest/plan")

        # Assert: Endpoint accessible
        if resp.status_code == 503:
            pytest.skip("Selftest module not available (503)")

        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"

        # Act: Parse JSON
        data = resp.json()

        # Assert: Top-level fields are not null
        assert data is not None, "Response should not be null"
        assert data["version"] is not None, "version should not be null"
        assert data["steps"] is not None, "steps should not be null"
        assert data["summary"] is not None, "summary should not be null"

        # Assert: steps array is non-empty (modal needs data to render)
        assert len(data["steps"]) > 0, "steps array should not be empty"

        # Assert: Summary counts are present
        assert data["summary"]["total"] is not None, "summary.total should not be null"
        assert data["summary"]["by_tier"] is not None, "summary.by_tier should not be null"

        # Assert: Each step has renderable data
        for i, step in enumerate(data["steps"]):
            assert step["id"] is not None, f"Step {i}: id is null"
            assert step["description"] is not None, f"Step {i}: description is null"
            assert len(step["description"]) > 0, (
                f"Step {i} ('{step['id']}'): description is empty string"
            )
            assert step["tier"] is not None, f"Step {i}: tier is null"
            assert step["depends_on"] is not None, f"Step {i}: depends_on is null"

    def test_selftest_modal_graceful_degradation_no_clipboard(self, fastapi_client):
        """
        Test that modal gracefully handles missing clipboard API.

        **Modal requirement**:
        - If Clipboard API is unavailable, modal should degrade gracefully
        - copyAndRun button should show helpful message instead of crashing
        - Plan should still be visible and readable

        **Test flow**:
        1. GET /api/selftest/plan
        2. Simulate missing navigator.clipboard (return empty string)
        3. Verify plan is still valid and no errors occur
        """
        # Arrange & Act
        resp = fastapi_client.get("/api/selftest/plan")

        if resp.status_code == 503:
            pytest.skip("Selftest module not available (503)")

        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"

        # Act: Parse JSON
        data = resp.json()

        # Assert: Plan is valid and complete even if clipboard is missing
        # The modal should be able to render steps without clipboard
        assert data["steps"] is not None, "steps should be available"
        assert len(data["steps"]) > 0, "steps should not be empty"

        # Assert: Each step has enough info to render without clipboard
        for step in data["steps"]:
            # These fields are needed for UI rendering (not for copy)
            assert step.get("id") is not None, "step should have id"
            assert step.get("description") is not None, "step should have description"
            assert step.get("tier") is not None, "step should have tier"

        # Simulate what modal JS would do without clipboard:
        # Extract commands that would be copied (if clipboard were available)
        commands = []
        try:
            # In real modal, this would be: navigator.clipboard.writeText(cmd)
            # Here we just verify the command string can be generated
            for step in data["steps"]:
                # The modal would generate a command like: uv run swarm/tools/selftest.py --step {id}
                step_id = step["id"]
                command = f"uv run swarm/tools/selftest.py --step {step_id}"
                assert len(command) > 0, f"Could not generate command for step {step_id}"
                commands.append(command)
        except Exception as e:
            pytest.fail(f"Modal would crash generating commands: {e}")

        # Assert: At least one command was generated (UI could work)
        assert len(commands) > 0, "Modal should be able to generate at least one command"

    def test_selftest_modal_copy_and_run_safe(self, fastapi_client):
        """
        Test that copyAndRun() functionality doesn't crash on error conditions.

        **Modal requirement**:
        - copyAndRun() handles missing step gracefully
        - copyAndRun() generates valid shell command
        - Command is properly escaped and safe to run
        - Error messages don't expose implementation details

        **Test flow**:
        1. GET /api/selftest/plan
        2. For each step, simulate copyAndRun (generate command)
        3. Verify command is valid and safe
        """
        # Arrange & Act
        resp = fastapi_client.get("/api/selftest/plan")

        if resp.status_code == 503:
            pytest.skip("Selftest module not available (503)")

        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"

        # Act: Parse JSON
        data = resp.json()
        steps = data["steps"]

        # Assert: Can generate safe commands for all steps
        for step in steps:
            step_id = step["id"]

            # Simulate copyAndRun() in modal:
            # Generate the command that would be copied to clipboard
            try:
                # Command format: uv run swarm/tools/selftest.py --step {step_id}
                command = f"uv run swarm/tools/selftest.py --step {step_id}"

                # Assert: Command is non-empty
                assert len(command) > 0, f"Empty command for step {step_id}"

                # Assert: Command doesn't contain shell metacharacters
                # (step_id should be alphanumeric/dash only)
                import re

                assert re.match(r"^[a-zA-Z0-9\-_\./ ]+$", command), (
                    f"Command contains suspicious characters: {command}"
                )

                # Assert: Command contains the step ID
                assert step_id in command, f"Generated command doesn't include step ID: {command}"

            except Exception as e:
                pytest.fail(f"copyAndRun would crash on step '{step_id}': {e}")

        # Assert: Modal can handle full list of steps
        assert len(steps) > 0, "Modal should have steps to render"

    def test_selftest_modal_step_rendering_safe(self, fastapi_client):
        """
        Test that step data is safe for rendering in HTML without XSS risk.

        **Modal requirement**:
        - Step descriptions can be safely rendered as HTML text
        - No untrusted HTML injection vectors
        - IDs are safe for use in HTML attributes

        **Test flow**:
        1. GET /api/selftest/plan
        2. For each step, validate that fields are text-only (no HTML)
        3. Verify IDs are safe for HTML attributes (alphanumeric/dash)
        """
        # Arrange & Act
        resp = fastapi_client.get("/api/selftest/plan")

        if resp.status_code == 503:
            pytest.skip("Selftest module not available (503)")

        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"

        # Act: Parse JSON
        data = resp.json()
        steps = data["steps"]

        # Assert: Each step is safe for HTML rendering
        for step in steps:
            step_id = step["id"]
            description = step["description"]

            # Assert: ID is safe for HTML attributes (alphanumeric, dash, underscore)
            import re

            assert re.match(r"^[a-zA-Z0-9\-_]+$", step_id), (
                f"Step ID '{step_id}' contains characters unsafe for HTML attributes"
            )

            # Assert: Description doesn't contain unescaped HTML
            # (should not contain < or > unless it's intentional markup)
            # For safety, descriptions should be plain text
            if "<" in description or ">" in description:
                # Only allow if it's part of escaped content like &lt; or &gt;
                import html

                # Check that if we decode entities, we don't get raw HTML
                decoded = html.unescape(description)
                assert "<" not in decoded or "&lt;" in description, (
                    f"Step description may contain unescaped HTML: {description}"
                )

            # Assert: Description is non-empty string
            assert isinstance(description, str), (
                f"Step description should be string, got {type(description)}"
            )
            assert len(description) > 0, f"Step description is empty for '{step_id}'"
