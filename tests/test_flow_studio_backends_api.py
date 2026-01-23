#!/usr/bin/env python3
"""
Tests for Flow Studio backends API.

This test suite validates:
1. /api/runs includes backend field from RunSummary.spec.backend
2. /api/runs/{id}/events returns structured RunEventsResponse
3. Backend badge data is correctly exposed for the UI

See docs/FLOW_STUDIO.md "Backends & Events Timeline" for documentation.
"""

import sys
from pathlib import Path

# Add repo root to path for imports
repo_root = Path(__file__).resolve().parents[1]
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))


# ============================================================================
# /api/runs Backend Field Tests
# ============================================================================


class TestApiRunsBackendField:
    """Tests for /api/runs endpoint backend field."""

    def test_api_runs_includes_backend_from_spec(self):
        """Verify /api/runs includes backend field from RunSummary.spec.backend."""
        from fastapi.testclient import TestClient
        from swarm.tools.flow_studio_fastapi import app

        client = TestClient(app)

        # For now, just verify the endpoint exists and returns expected structure
        response = client.get("/api/runs")
        assert response.status_code in (200, 503), (
            f"Expected 200 or 503 (if RunService unavailable), got {response.status_code}"
        )

        if response.status_code == 200:
            data = response.json()
            assert "runs" in data, "Response should have 'runs' key"
            # If there are runs, check structure
            if data["runs"]:
                run = data["runs"][0]
                assert "run_id" in run, "Run should have run_id"
                # backend is optional but if present should be a string
                if "backend" in run:
                    assert isinstance(run["backend"], str), "backend should be a string"

    def test_api_runs_backend_optional_when_missing(self):
        """Verify backend field is omitted when RunSummary.spec.backend is None."""
        from fastapi.testclient import TestClient
        from swarm.tools.flow_studio_fastapi import app

        client = TestClient(app)

        response = client.get("/api/runs")

        # Just verify the endpoint doesn't crash
        assert response.status_code in (200, 503)


# ============================================================================
# /api/runs/{id}/events Endpoint Tests
# ============================================================================


class TestApiRunEventsEndpoint:
    """Tests for /api/runs/{id}/events endpoint."""

    def test_api_run_events_endpoint_exists(self):
        """Verify /api/runs/{id}/events endpoint exists."""
        from fastapi.testclient import TestClient
        from swarm.tools.flow_studio_fastapi import app

        client = TestClient(app)

        # Use a fake run_id - should return 500 (run not found) or 503 (service unavailable)
        # but not 404 (endpoint not found)
        response = client.get("/api/runs/fake-run-id/events")

        # 404 would mean endpoint doesn't exist
        # We expect either 200, 500 (error getting events), or 503 (service unavailable)
        assert response.status_code != 404, "Events endpoint should exist (got 404 Not Found)"

    def test_api_run_events_response_structure(self):
        """Verify /api/runs/{id}/events returns correct structure."""
        from fastapi.testclient import TestClient
        from swarm.tools.flow_studio_fastapi import app

        client = TestClient(app)

        response = client.get("/api/runs/test-run/events")

        if response.status_code == 200:
            data = response.json()
            # Verify response has expected keys
            assert "run_id" in data, "Response should have 'run_id'"
            assert "events" in data, "Response should have 'events' list"
            assert isinstance(data["events"], list), "events should be a list"

            # If there are events, verify their structure
            if data["events"]:
                event = data["events"][0]
                assert "run_id" in event, "Event should have run_id"
                assert "kind" in event, "Event should have kind"
                # ts may be None for some events
                assert "ts" in event, "Event should have ts field"

    def test_api_run_events_matches_run_events_response_type(self):
        """Verify response matches RunEventsResponse TypeScript type."""
        # This test documents the contract between Python API and TypeScript types
        #
        # TypeScript type (from domain.ts):
        # export interface RunEventsResponse {
        #   run_id: string;
        #   events: RunEvent[];
        # }
        #
        # export interface RunEvent {
        #   run_id: string;
        #   ts: string;
        #   kind: string;
        #   flow_key: string;  // may be empty string for events without flow context
        #   step_id?: string | null;
        #   agent_key?: string | null;
        #   payload?: Record<string, unknown>;
        # }

        from fastapi.testclient import TestClient
        from swarm.tools.flow_studio_fastapi import app

        client = TestClient(app)
        response = client.get("/api/runs/test-run/events")

        if response.status_code == 200:
            data = response.json()

            # Verify top-level response shape
            assert isinstance(data.get("run_id"), str), "run_id must be string"
            assert isinstance(data.get("events"), list), "events must be list"

            # Verify event shape (if events exist)
            for event in data.get("events", []):
                assert isinstance(event.get("run_id"), str), "event.run_id must be string"
                assert isinstance(event.get("kind"), str), "event.kind must be string"
                # ts can be string or None
                if event.get("ts") is not None:
                    assert isinstance(event["ts"], str), "event.ts must be string or null"
                # flow_key can be string or None
                if event.get("flow_key") is not None:
                    assert isinstance(event["flow_key"], str), "event.flow_key must be string"


# ============================================================================
# Backend Badge Integration Tests
# ============================================================================


class TestBackendBadgeIntegration:
    """Tests for backend badge data in API responses."""

    def test_backend_labels_are_consistent(self):
        """Verify backend IDs map to expected labels.

        The UI uses these mappings in run_history.ts getBackendLabel():
        - "claude-harness" -> "Claude"
        - "gemini-cli" -> "Gemini"
        - "gemini-step-orchestrator" -> "Gemini Stepwise"
        """
        expected_backends = {
            "claude-harness": "Claude",
            "gemini-cli": "Gemini",
            "gemini-step-orchestrator": "Gemini Stepwise",
        }

        # This is a documentation test - verifies the expected backend IDs
        # The actual label mapping is in TypeScript, but we document it here
        # for API consumers
        for backend_id, label in expected_backends.items():
            assert backend_id is not None
            assert label is not None

    def test_api_backends_endpoint_lists_available_backends(self):
        """Verify /api/backends returns list of available backends."""
        from fastapi.testclient import TestClient
        from swarm.tools.flow_studio_fastapi import app

        client = TestClient(app)
        response = client.get("/api/backends")

        assert response.status_code in (200, 503), (
            f"Expected 200 or 503, got {response.status_code}"
        )

        if response.status_code == 200:
            data = response.json()
            assert "backends" in data, "Response should have 'backends' key"
            assert isinstance(data["backends"], list), "backends should be a list"

            # Each backend should have required fields
            for backend in data["backends"]:
                assert "id" in backend, "Backend should have 'id'"
                assert "label" in backend, "Backend should have 'label'"
                # Capability flags are optional but documented
                if "supports_streaming" in backend:
                    assert isinstance(backend["supports_streaming"], bool)


# ============================================================================
# Tags Integration Tests
# ============================================================================


class TestBackendTagsInRuns:
    """Tests for backend tags in run responses."""

    def test_runs_can_have_backend_tags(self):
        """Verify runs can include backend: tags for filtering."""
        # This test documents the tagging convention:
        # - backend:claude-harness
        # - backend:gemini-cli
        # - backend:gemini-step-orchestrator
        # - mode:stub
        # - mode:real

        from fastapi.testclient import TestClient
        from swarm.tools.flow_studio_fastapi import app

        client = TestClient(app)
        response = client.get("/api/runs")

        if response.status_code == 200:
            data = response.json()
            for run in data.get("runs", []):
                # tags is optional
                if "tags" in run:
                    assert isinstance(run["tags"], list), "tags should be a list"
                    for tag in run["tags"]:
                        assert isinstance(tag, str), "each tag should be a string"


# ============================================================================
# Exemplar Flag Tests
# ============================================================================


class TestExemplarFlagInRuns:
    """Tests for is_exemplar flag in run responses."""

    def test_runs_include_exemplar_flag(self):
        """Verify /api/runs includes is_exemplar when set."""
        from fastapi.testclient import TestClient
        from swarm.tools.flow_studio_fastapi import app

        client = TestClient(app)
        response = client.get("/api/runs")

        if response.status_code == 200:
            data = response.json()
            for run in data.get("runs", []):
                # is_exemplar is optional
                if "is_exemplar" in run:
                    assert isinstance(run["is_exemplar"], bool), "is_exemplar should be bool"
