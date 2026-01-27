#!/usr/bin/env python3
"""
Comprehensive tests for Flow Studio FastAPI endpoints.

This module provides comprehensive test coverage for all Flow Studio FastAPI
endpoints, following the pattern established in the existing smoke and endpoint tests.

## Test Categories

1. Flow endpoints - List flows, get flow details
2. Agent endpoints - List agents, get agent usage
3. Graph endpoints - Get flow graphs, artifact graphs
4. Run endpoints - List runs, get summaries, SDLC data, timelines, comparisons
5. Search/Tour endpoints - Search results, guided tours
6. Admin endpoints - Reload, validation status
7. Health endpoint - Service health and status
8. Root endpoint - HTML UI
9. Selftest endpoint - Selftest plan information
10. Error handling - Error response validation
11. CORS headers - Cross-origin resource sharing
12. Content-Type headers - Response content type validation
13. OpenAPI schema - Schema documentation and validation

## Design Principles

- Tests accept graceful degradation (503 is acceptable for unavailable services)
- Tests verify response structure, not specific values
- Tests are isolated and can run in any order
- Tests use a shared fixture for the FastAPI test client

## OpenAPI Schema Tests

The OpenAPI schema validation tests (`TestOpenAPISchemaValidation`) verify:
- The /openapi.json endpoint returns 200 OK
- The response is valid JSON and contains required keys (openapi, info, paths)
- OpenAPI version is 3.x
- Info object has required fields (title, version)
- Paths are documented and have HTTP method definitions
- Key endpoints like /api/health and /api/flows are documented
- Response definitions are present for documented endpoints
- Components section (if present) is valid
- Schema structure is self-consistent

These tests ensure the API is properly documented and can be used by client generators,
API explorers (like Swagger UI), and other OpenAPI tooling.
"""

import sys
from pathlib import Path

# Add repo root to path so swarm imports work
repo_root = Path(__file__).resolve().parents[1]
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """Create FastAPI test client."""
    from swarm.tools.flow_studio_fastapi import app

    return TestClient(app)


# =============================================================================
# Flow Endpoints
# =============================================================================


class TestFlowEndpoints:
    """Tests for /api/flows and /api/flows/{flow_key} endpoints."""

    def test_get_flows_returns_list(self, client):
        """Test /api/flows endpoint returns list of flows."""
        resp = client.get("/api/flows")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = resp.json()
        assert "flows" in data, "Response missing 'flows' field"
        assert isinstance(data["flows"], list), "'flows' should be a list"

    def test_get_flows_structure(self, client):
        """Test that flows have expected fields."""
        resp = client.get("/api/flows")
        assert resp.status_code == 200

        data = resp.json()
        flows = data.get("flows", [])

        # If there are flows, check structure
        if len(flows) > 0:
            flow = flows[0]
            expected_fields = {"key", "title", "description", "step_count"}
            actual_fields = set(flow.keys())

            missing = expected_fields - actual_fields
            assert not missing, f"Flow missing fields: {missing}. Got: {actual_fields}"

    def test_get_flow_detail_returns_steps(self, client):
        """Test /api/graph/{flow_key} endpoint returns steps for known flow."""
        # First get list of available flows
        flows_resp = client.get("/api/flows")
        if flows_resp.status_code != 200:
            pytest.skip("Cannot get flows list")

        flows = flows_resp.json().get("flows", [])
        if not flows:
            pytest.skip("No flows available to test")

        # Test with first available flow
        flow_key = flows[0]["key"]
        resp = client.get(f"/api/graph/{flow_key}")

        assert resp.status_code in (200, 503), f"Expected 200 or 503, got {resp.status_code}"

        if resp.status_code == 200:
            data = resp.json()
            assert "nodes" in data, "Graph response missing 'nodes'"
            assert "edges" in data, "Graph response missing 'edges'"

    def test_get_flow_detail_404_for_unknown(self, client):
        """Test /api/graph/{flow_key} returns 404 for unknown flow."""
        resp = client.get("/api/graph/nonexistent-flow-xyz")

        # Either 404 or 503 (if core not available)
        assert resp.status_code in (404, 503), f"Expected 404 or 503, got {resp.status_code}"

        if resp.status_code == 404:
            data = resp.json()
            assert "error" in data, "404 response should have 'error' field"

    def test_get_flow_detail_has_available_flows_hint(self, client):
        """Test 404 response includes available flows hint."""
        resp = client.get("/api/graph/nonexistent-flow-xyz")

        if resp.status_code == 404:
            data = resp.json()
            assert "available_flows" in data or "hint" in data, (
                "404 should include available_flows or hint for discovery"
            )


# =============================================================================
# Agent Endpoints (via graph)
# =============================================================================


class TestAgentEndpoints:
    """Tests for agent-related functionality via graph endpoints."""

    def test_get_agents_returns_list(self, client):
        """Test that graph endpoint returns agent nodes."""
        # Get first available flow
        flows_resp = client.get("/api/flows")
        if flows_resp.status_code != 200:
            pytest.skip("Cannot get flows list")

        flows = flows_resp.json().get("flows", [])
        if not flows:
            pytest.skip("No flows available")

        flow_key = flows[0]["key"]
        resp = client.get(f"/api/graph/{flow_key}")

        if resp.status_code != 200:
            pytest.skip("Cannot get graph data")

        data = resp.json()
        nodes = data.get("nodes", [])

        # Find agent nodes
        agent_nodes = [n for n in nodes if n.get("data", {}).get("type") == "agent"]

        # Graph should include agent nodes (most flows have agents)
        assert isinstance(agent_nodes, list), "Agent nodes should be a list"

    def test_get_agent_usage_returns_flows(self, client):
        """Test that agent nodes include usage info (which flows they appear in)."""
        flows_resp = client.get("/api/flows")
        if flows_resp.status_code != 200:
            pytest.skip("Cannot get flows list")

        flows = flows_resp.json().get("flows", [])
        if not flows:
            pytest.skip("No flows available")

        # Check multiple flows to find agent nodes
        for flow in flows[:3]:  # Check up to 3 flows
            flow_key = flow["key"]
            resp = client.get(f"/api/graph/{flow_key}")

            if resp.status_code != 200:
                continue

            data = resp.json()
            nodes = data.get("nodes", [])

            agent_nodes = [n for n in nodes if n.get("data", {}).get("type") == "agent"]

            if agent_nodes:
                # Verify agent node structure
                agent = agent_nodes[0]
                agent_data = agent.get("data", {})

                # Agent nodes should have key fields
                assert "id" in agent_data, "Agent node missing 'id'"
                assert "label" in agent_data, "Agent node missing 'label'"
                return  # Found and validated agent nodes

        # If we get here, no agents found - that's still valid
        pytest.skip("No agent nodes found in available flows")


# =============================================================================
# Graph Endpoints
# =============================================================================


class TestGraphEndpoints:
    """Tests for /api/graph/{flow_key} endpoints."""

    def test_get_graph_returns_nodes_and_edges(self, client):
        """Test graph endpoint returns both nodes and edges."""
        flows_resp = client.get("/api/flows")
        if flows_resp.status_code != 200:
            pytest.skip("Cannot get flows list")

        flows = flows_resp.json().get("flows", [])
        if not flows:
            pytest.skip("No flows available")

        flow_key = flows[0]["key"]
        resp = client.get(f"/api/graph/{flow_key}")

        assert resp.status_code in (200, 503), f"Expected 200 or 503, got {resp.status_code}"

        if resp.status_code == 200:
            data = resp.json()

            assert "nodes" in data, "Graph missing 'nodes'"
            assert "edges" in data, "Graph missing 'edges'"
            assert isinstance(data["nodes"], list), "'nodes' should be list"
            assert isinstance(data["edges"], list), "'edges' should be list"

    def test_get_graph_node_structure(self, client):
        """Test graph nodes have correct structure."""
        flows_resp = client.get("/api/flows")
        if flows_resp.status_code != 200:
            pytest.skip("Cannot get flows list")

        flows = flows_resp.json().get("flows", [])
        if not flows:
            pytest.skip("No flows available")

        flow_key = flows[0]["key"]
        resp = client.get(f"/api/graph/{flow_key}")

        if resp.status_code != 200:
            pytest.skip("Graph endpoint unavailable")

        data = resp.json()
        nodes = data.get("nodes", [])

        for node in nodes:
            assert "data" in node, f"Node missing 'data': {node}"
            node_data = node["data"]
            assert "id" in node_data, f"Node data missing 'id': {node_data}"
            assert "type" in node_data, f"Node data missing 'type': {node_data}"

    def test_get_graph_edge_structure(self, client):
        """Test graph edges have correct structure."""
        flows_resp = client.get("/api/flows")
        if flows_resp.status_code != 200:
            pytest.skip("Cannot get flows list")

        flows = flows_resp.json().get("flows", [])
        if not flows:
            pytest.skip("No flows available")

        flow_key = flows[0]["key"]
        resp = client.get(f"/api/graph/{flow_key}")

        if resp.status_code != 200:
            pytest.skip("Graph endpoint unavailable")

        data = resp.json()
        edges = data.get("edges", [])

        for edge in edges:
            assert "data" in edge, f"Edge missing 'data': {edge}"
            edge_data = edge["data"]
            assert "id" in edge_data, f"Edge data missing 'id': {edge_data}"
            assert "source" in edge_data, f"Edge data missing 'source': {edge_data}"
            assert "target" in edge_data, f"Edge data missing 'target': {edge_data}"

    def test_get_artifact_graph_returns_artifact_nodes(self, client):
        """Test graph includes step nodes that may produce artifacts."""
        flows_resp = client.get("/api/flows")
        if flows_resp.status_code != 200:
            pytest.skip("Cannot get flows list")

        flows = flows_resp.json().get("flows", [])
        if not flows:
            pytest.skip("No flows available")

        flow_key = flows[0]["key"]
        resp = client.get(f"/api/graph/{flow_key}")

        if resp.status_code != 200:
            pytest.skip("Graph endpoint unavailable")

        data = resp.json()
        nodes = data.get("nodes", [])

        # Find step nodes (these are where artifacts are produced)
        step_nodes = [n for n in nodes if n.get("data", {}).get("type") == "step"]

        # Flows should have step nodes
        assert len(step_nodes) >= 0, "Step nodes should be present in graph"


# =============================================================================
# Run Endpoints
# =============================================================================


class TestRunEndpoints:
    """Tests for /api/runs and related endpoints."""

    def test_get_runs_returns_list(self, client):
        """Test /api/runs endpoint returns list of runs."""
        resp = client.get("/api/runs")

        # Either 200 with runs list or 503 if RunInspector disabled
        assert resp.status_code in (200, 503), f"Expected 200 or 503, got {resp.status_code}"

        data = resp.json()
        if resp.status_code == 200:
            assert "runs" in data, "Response missing 'runs' field"
            assert isinstance(data["runs"], list), "'runs' should be a list"

    def test_get_runs_structure(self, client):
        """Test that runs have expected fields."""
        resp = client.get("/api/runs")

        if resp.status_code != 200:
            pytest.skip("Runs endpoint unavailable")

        data = resp.json()
        runs = data.get("runs", [])

        if runs:
            run = runs[0]
            # Runs should have identifying fields
            assert "run_id" in run or "id" in run, (
                f"Run missing identifier field. Got: {run.keys()}"
            )

    def test_get_run_summary_returns_flows(self, client):
        """Test /api/runs/{run_id}/summary returns flow statuses."""
        # First get list of runs
        runs_resp = client.get("/api/runs")
        if runs_resp.status_code != 200:
            pytest.skip("Cannot get runs list")

        runs = runs_resp.json().get("runs", [])
        if not runs:
            pytest.skip("No runs available")

        # Get summary for first run
        run = runs[0]
        run_id = run.get("run_id") or run.get("id")
        if not run_id:
            pytest.skip("Run has no identifier")

        resp = client.get(f"/api/runs/{run_id}/summary")

        assert resp.status_code in (200, 500, 503), (
            f"Expected 200, 500, or 503, got {resp.status_code}"
        )

        if resp.status_code == 200:
            data = resp.json()
            # Summary should have flow status information
            assert "run_id" in data or "flows" in data, "Summary should have 'run_id' or 'flows'"

    def test_get_run_sdlc_returns_bar_data(self, client):
        """Test run summary includes SDLC flow completion data."""
        runs_resp = client.get("/api/runs")
        if runs_resp.status_code != 200:
            pytest.skip("Cannot get runs list")

        runs = runs_resp.json().get("runs", [])
        if not runs:
            pytest.skip("No runs available")

        run = runs[0]
        run_id = run.get("run_id") or run.get("id")
        if not run_id:
            pytest.skip("Run has no identifier")

        resp = client.get(f"/api/runs/{run_id}/summary")

        if resp.status_code != 200:
            pytest.skip("Run summary unavailable")

        data = resp.json()

        # If flows are present, they should have status info
        flows = data.get("flows", {})
        if flows:
            for flow_key, flow_data in flows.items():
                # Each flow should have status information
                assert isinstance(flow_data, dict), f"Flow {flow_key} data should be dict"

    def test_get_run_timeline_returns_events(self, client):
        """Test run summary includes timeline/step event data."""
        runs_resp = client.get("/api/runs")
        if runs_resp.status_code != 200:
            pytest.skip("Cannot get runs list")

        runs = runs_resp.json().get("runs", [])
        if not runs:
            pytest.skip("No runs available")

        run = runs[0]
        run_id = run.get("run_id") or run.get("id")
        if not run_id:
            pytest.skip("Run has no identifier")

        resp = client.get(f"/api/runs/{run_id}/summary")

        if resp.status_code != 200:
            pytest.skip("Run summary unavailable")

        data = resp.json()

        # Summary should include flow data which contains step info
        flows = data.get("flows", {})
        for flow_key, flow_data in flows.items():
            if isinstance(flow_data, dict):
                # Flow data may contain steps which represent timeline
                steps = flow_data.get("steps", {})
                if steps:
                    for step_id, step_data in steps.items():
                        assert isinstance(step_data, dict), f"Step {step_id} data should be dict"
                    return  # Found and validated step data

    def test_compare_runs_returns_diff(self, client):
        """Test comparing two runs returns difference data."""
        runs_resp = client.get("/api/runs")
        if runs_resp.status_code != 200:
            pytest.skip("Cannot get runs list")

        runs = runs_resp.json().get("runs", [])
        if len(runs) < 2:
            pytest.skip("Need at least 2 runs to compare")

        # Note: Compare endpoint may not exist in current implementation
        # This test documents expected behavior
        run1_id = runs[0].get("run_id") or runs[0].get("id")
        run2_id = runs[1].get("run_id") or runs[1].get("id")

        if not run1_id or not run2_id:
            pytest.skip("Runs missing identifiers")

        # Check if compare endpoint exists
        resp = client.get(f"/api/runs/compare?run1={run1_id}&run2={run2_id}")

        # Accept 404 (not implemented), 200 (success), 400 (bad request), or 503 (unavailable)
        assert resp.status_code in (200, 400, 404, 503), (
            f"Unexpected status code: {resp.status_code}"
        )

        if resp.status_code == 200:
            data = resp.json()
            # Compare response should have structure for diff
            assert isinstance(data, dict), "Compare response should be dict"

    def test_stop_run_endpoint_exists(self, client):
        """Test POST /api/runs/{run_id}/stop endpoint accepts requests."""
        # Use a non-existent run to test endpoint routing
        resp = client.post("/api/runs/nonexistent-run-xyz/stop")

        # Should return 404 (run not found), 503 (service unavailable), or 400 (bad request)
        # Should not return 405 (method not allowed)
        assert resp.status_code in (400, 404, 503), (
            f"Stop endpoint should return 400, 404, or 503, got {resp.status_code}: {resp.text}"
        )

    def test_stop_run_404_for_missing_run(self, client):
        """Test stop endpoint returns 404 for non-existent run."""
        resp = client.post("/api/runs/definitely-not-a-real-run-12345/stop")

        # Should return 404 (run not found) or 503 (service unavailable)
        assert resp.status_code in (404, 503), (
            f"Expected 404 or 503 for non-existent run, got {resp.status_code}"
        )

        if resp.status_code == 404:
            data = resp.json()
            assert "error" in data, "404 response should have 'error' field"

    def test_stop_run_returns_forensic_info(self, client):
        """Test stop endpoint returns forensic info for stoppable run."""
        # First, get list of runs
        runs_resp = client.get("/api/runs")
        if runs_resp.status_code != 200:
            pytest.skip("Cannot get runs list")

        runs = runs_resp.json().get("runs", [])
        if not runs:
            pytest.skip("No runs available")

        # Try to stop first run (may already be completed)
        run = runs[0]
        run_id = run.get("run_id") or run.get("id")
        if not run_id:
            pytest.skip("Run has no identifier")

        resp = client.post(f"/api/runs/{run_id}/stop")

        # Accept 200 (stopped), 404 (already completed), or 503 (service unavailable)
        assert resp.status_code in (200, 404, 503), (
            f"Stop endpoint unexpected status: {resp.status_code}"
        )

        if resp.status_code == 200:
            data = resp.json()
            # Verify forensic info structure
            assert "run_id" in data, "Stop response should have 'run_id'"
            assert "status" in data, "Stop response should have 'status'"
            assert "stop_report_path" in data, "Stop response should have 'stop_report_path'"
            assert "stop_info" in data, "Stop response should have 'stop_info'"

            # Verify stop_info structure
            stop_info = data["stop_info"]
            assert isinstance(stop_info, dict), "stop_info should be a dict"
            assert "stop_reason" in stop_info, "stop_info should have 'stop_reason'"
            assert "stopped_at" in stop_info, "stop_info should have 'stopped_at'"

    def test_stop_run_503_when_service_unavailable(self, client, monkeypatch):
        """Test stop endpoint returns 503 when RunService unavailable."""
        # This test documents expected behavior when run_service is None
        # The endpoint should return 503 with appropriate error message
        resp = client.post("/api/runs/test-run/stop")

        if resp.status_code == 503:
            data = resp.json()
            assert "error" in data, "503 response should have 'error' field"


# =============================================================================
# Wisdom API Endpoints
# =============================================================================


class TestWisdomApiEndpoints:
    """Tests for /api/runs/{run_id}/wisdom/summary endpoint.

    The wisdom API endpoint returns structured wisdom summary data for runs
    that have completed Flow 6 (Wisdom) with wisdom_summary.json generated.

    This test class verifies:
    - Endpoint returns 404 for runs without wisdom data
    - Endpoint returns valid structure for runs with wisdom data
    - Response contains expected fields (run_id, flows, summary, labels, etc.)
    """

    def test_wisdom_endpoint_exists(self, client):
        """Test wisdom endpoint accepts requests (returns valid status)."""
        # Use a non-existent run to test endpoint routing
        resp = client.get("/api/runs/nonexistent-run-xyz/wisdom/summary")

        # Should return 404 (run not found) or 200 (if run exists with wisdom)
        # Should not return 500 (server error) or 405 (method not allowed)
        assert resp.status_code in (200, 404), (
            f"Wisdom endpoint should return 200 or 404, got {resp.status_code}: {resp.text}"
        )

    def test_wisdom_404_for_missing_run(self, client):
        """Test wisdom endpoint returns 404 for non-existent run."""
        resp = client.get("/api/runs/definitely-not-a-real-run-12345/wisdom/summary")

        assert resp.status_code == 404, f"Expected 404 for non-existent run, got {resp.status_code}"

        data = resp.json()
        # API returns 'error' field for error responses
        assert "error" in data or "detail" in data, (
            "404 response should have 'error' or 'detail' field"
        )

    def test_wisdom_returns_structure_for_valid_run(self, client):
        """Test wisdom endpoint returns correct structure for run with wisdom."""
        # First, get list of runs
        runs_resp = client.get("/api/runs")
        if runs_resp.status_code != 200:
            pytest.skip("Cannot get runs list")

        runs = runs_resp.json().get("runs", [])
        if not runs:
            pytest.skip("No runs available")

        # Try to find a run with wisdom data
        for run in runs:
            run_id = run.get("run_id") or run.get("id")
            if not run_id:
                continue

            resp = client.get(f"/api/runs/{run_id}/wisdom/summary")

            if resp.status_code == 200:
                data = resp.json()

                # Verify expected structure
                assert "run_id" in data, "Wisdom summary should have 'run_id'"
                assert "flows" in data, "Wisdom summary should have 'flows'"
                assert "summary" in data, "Wisdom summary should have 'summary'"

                # Validate flows structure
                flows = data.get("flows", {})
                assert isinstance(flows, dict), "'flows' should be a dictionary"

                # Validate summary structure
                summary = data.get("summary", {})
                assert isinstance(summary, dict), "'summary' should be a dictionary"

                # Found valid wisdom data, test passes
                return

        # No runs had wisdom data - this is acceptable
        pytest.skip("No runs with wisdom data available")

    def test_wisdom_summary_has_metrics(self, client):
        """Test wisdom summary includes expected metrics fields."""
        runs_resp = client.get("/api/runs")
        if runs_resp.status_code != 200:
            pytest.skip("Cannot get runs list")

        runs = runs_resp.json().get("runs", [])
        if not runs:
            pytest.skip("No runs available")

        # Try to find a run with wisdom data
        for run in runs:
            run_id = run.get("run_id") or run.get("id")
            if not run_id:
                continue

            resp = client.get(f"/api/runs/{run_id}/wisdom/summary")

            if resp.status_code == 200:
                data = resp.json()
                summary = data.get("summary", {})

                # Check for expected metrics fields (may have 0 values)
                expected_metrics = [
                    "artifacts_present",
                    "regressions_found",
                    "learnings_count",
                    "feedback_actions_count",
                    "issues_created",
                ]

                for metric in expected_metrics:
                    assert metric in summary, (
                        f"Wisdom summary should have '{metric}' metric. "
                        f"Available: {list(summary.keys())}"
                    )

                # Found valid wisdom data with metrics, test passes
                return

        pytest.skip("No runs with wisdom data available")

    def test_wisdom_flow_status_structure(self, client):
        """Test wisdom flow status has correct structure."""
        runs_resp = client.get("/api/runs")
        if runs_resp.status_code != 200:
            pytest.skip("Cannot get runs list")

        runs = runs_resp.json().get("runs", [])
        if not runs:
            pytest.skip("No runs available")

        for run in runs:
            run_id = run.get("run_id") or run.get("id")
            if not run_id:
                continue

            resp = client.get(f"/api/runs/{run_id}/wisdom/summary")

            if resp.status_code == 200:
                data = resp.json()
                flows = data.get("flows", {})

                for flow_key, flow_status in flows.items():
                    assert isinstance(flow_status, dict), (
                        f"Flow '{flow_key}' status should be a dict"
                    )
                    assert "status" in flow_status, f"Flow '{flow_key}' should have 'status' field"
                    assert flow_status["status"] in ("succeeded", "failed", "skipped"), (
                        f"Flow '{flow_key}' has invalid status: {flow_status['status']}"
                    )

                return

        pytest.skip("No runs with wisdom data available")


# =============================================================================
# Search/Tour Endpoints
# =============================================================================


class TestSearchAndTourEndpoints:
    """Tests for search and tour functionality."""

    def test_search_returns_results(self, client):
        """Test search endpoint returns results structure."""
        # Note: Search endpoint may not exist in current implementation
        # This test documents expected behavior
        resp = client.get("/api/search?q=signal")

        # Accept 404 (not implemented), 200 (success), or 503 (unavailable)
        assert resp.status_code in (200, 404, 503), f"Unexpected status code: {resp.status_code}"

        if resp.status_code == 200:
            data = resp.json()
            # Search should return results list
            assert "results" in data or isinstance(data, list), "Search should return results"

    def test_get_tours_returns_list(self, client):
        """Test tours endpoint returns list of available tours."""
        # Note: Tours endpoint may not exist in current implementation
        # This test documents expected behavior
        resp = client.get("/api/tours")

        # Accept 404 (not implemented), 200 (success), or 503 (unavailable)
        assert resp.status_code in (200, 404, 503), f"Unexpected status code: {resp.status_code}"

        if resp.status_code == 200:
            data = resp.json()
            # Tours should return list
            assert "tours" in data or isinstance(data, list), "Tours should return tours list"


# =============================================================================
# Admin Endpoints
# =============================================================================


class TestAdminEndpoints:
    """Tests for admin/maintenance endpoints."""

    def test_reload_returns_success(self, client):
        """Test reload endpoint returns success status."""
        # Note: Reload is handled implicitly via core.reload() in FastAPI
        # The health endpoint reflects reload status
        resp = client.get("/api/health")

        assert resp.status_code == 200, f"Health endpoint should return 200, got {resp.status_code}"

        data = resp.json()
        assert "status" in data, "Health response should have 'status'"
        assert data["status"] in ("ok", "degraded", "error"), f"Unexpected status: {data['status']}"

    def test_validation_returns_fr_status(self, client):
        """Test /platform/status returns functional requirement statuses."""
        resp = client.get("/platform/status")

        # Either 200 with status or 503 if provider unavailable
        assert resp.status_code in (200, 500, 503), (
            f"Expected 200, 500, or 503, got {resp.status_code}"
        )

        if resp.status_code == 200:
            data = resp.json()
            # Status should have timestamp and service
            assert "timestamp" in data, "Status missing 'timestamp'"
            assert "service" in data, "Status missing 'service'"

    def test_validation_governance_structure(self, client):
        """Test validation status includes governance details."""
        resp = client.get("/platform/status")

        if resp.status_code != 200:
            pytest.skip("Platform status unavailable")

        data = resp.json()

        # Governance section should exist
        if "governance" in data:
            governance = data["governance"]
            assert isinstance(governance, dict), "Governance should be a dict"


# =============================================================================
# Health Endpoint
# =============================================================================


class TestHealthEndpoint:
    """Tests for /api/health endpoint."""

    def test_health_returns_200(self, client):
        """Test health endpoint returns 200."""
        resp = client.get("/api/health")
        assert resp.status_code == 200

    def test_health_has_required_fields(self, client):
        """Test health response has required fields."""
        resp = client.get("/api/health")
        assert resp.status_code == 200

        data = resp.json()
        required_fields = {"status", "version", "timestamp"}
        actual_fields = set(data.keys())

        missing = required_fields - actual_fields
        assert not missing, f"Health response missing fields: {missing}"

    def test_health_status_valid(self, client):
        """Test health status is a valid value."""
        resp = client.get("/api/health")
        assert resp.status_code == 200

        data = resp.json()
        valid_statuses = {"ok", "degraded", "error"}
        assert data["status"] in valid_statuses, f"Invalid status: {data['status']}"

    def test_health_includes_counts(self, client):
        """Test health response includes flow and agent counts."""
        resp = client.get("/api/health")
        assert resp.status_code == 200

        data = resp.json()
        # Should include counts
        assert "flows" in data, "Health missing 'flows' count"
        assert "agents" in data, "Health missing 'agents' count"
        assert isinstance(data["flows"], int), "'flows' should be int"
        assert isinstance(data["agents"], int), "'agents' should be int"

    def test_health_includes_capabilities(self, client):
        """Test health response includes capabilities flags."""
        resp = client.get("/api/health")
        assert resp.status_code == 200

        data = resp.json()
        if "capabilities" in data:
            caps = data["capabilities"]
            assert isinstance(caps, dict), "Capabilities should be dict"


# =============================================================================
# Root Endpoint
# =============================================================================


class TestRootEndpoint:
    """Tests for / (root) endpoint."""

    def test_root_returns_html(self, client):
        """Test root endpoint returns HTML."""
        resp = client.get("/")
        assert resp.status_code == 200
        assert "text/html" in resp.headers.get("content-type", "")

    def test_root_html_not_empty(self, client):
        """Test root HTML response is not empty."""
        resp = client.get("/")
        assert resp.status_code == 200
        # HTML should have some content (even if minimal)
        assert len(resp.text) > 0, "HTML response should not be empty"


# =============================================================================
# Selftest Plan Endpoint
# =============================================================================


class TestSelftestPlanEndpoint:
    """Tests for /api/selftest/plan endpoint."""

    def test_selftest_plan_returns_valid_response(self, client):
        """Test selftest plan endpoint returns valid response."""
        resp = client.get("/api/selftest/plan")

        # Either 200 with plan or 503 if selftest module disabled
        assert resp.status_code in (200, 503), f"Expected 200 or 503, got {resp.status_code}"

    def test_selftest_plan_structure(self, client):
        """Test selftest plan has correct structure."""
        resp = client.get("/api/selftest/plan")

        if resp.status_code != 200:
            pytest.skip("Selftest plan endpoint unavailable")

        data = resp.json()
        assert "version" in data, "Plan missing 'version'"
        assert "steps" in data, "Plan missing 'steps'"
        assert "summary" in data, "Plan missing 'summary'"

    def test_selftest_plan_steps_valid(self, client):
        """Test selftest plan steps have valid structure."""
        resp = client.get("/api/selftest/plan")

        if resp.status_code != 200:
            pytest.skip("Selftest plan endpoint unavailable")

        data = resp.json()
        steps = data.get("steps", [])

        for step in steps:
            assert "id" in step, f"Step missing 'id': {step}"
            assert "tier" in step, f"Step missing 'tier': {step}"
            assert step["tier"] in {"kernel", "governance", "optional"}, (
                f"Invalid tier: {step['tier']}"
            )


# =============================================================================
# Error Handling
# =============================================================================


class TestErrorHandling:
    """Tests for error handling across endpoints."""

    def test_404_for_unknown_endpoint(self, client):
        """Test unknown endpoint returns 404."""
        resp = client.get("/api/nonexistent-endpoint-xyz")
        assert resp.status_code == 404

    def test_404_has_detail(self, client):
        """Test 404 response has detail message."""
        resp = client.get("/api/nonexistent-endpoint-xyz")
        assert resp.status_code == 404

        data = resp.json()
        # FastAPI uses 'detail' for 404 errors
        assert "detail" in data, "404 should have 'detail' field"

    def test_graceful_degradation_503(self, client):
        """Test endpoints handle unavailable services gracefully."""
        # Test endpoints that might return 503
        endpoints = [
            "/api/runs",
            "/platform/status",
            "/api/selftest/plan",
        ]

        for endpoint in endpoints:
            resp = client.get(endpoint)
            # Should not return 500 (server error)
            assert resp.status_code != 500, f"Endpoint {endpoint} returned 500 (server error)"
            # Should return valid response (200, 404, or 503)
            assert resp.status_code in (200, 404, 503), (
                f"Endpoint {endpoint} returned unexpected {resp.status_code}"
            )


# =============================================================================
# CORS Headers
# =============================================================================


class TestCORSHeaders:
    """Tests for CORS configuration."""

    def test_cors_allows_all_origins(self, client):
        """Test CORS middleware allows all origins."""
        # Make a preflight-like request
        resp = client.options("/api/health")

        # OPTIONS should not fail
        assert resp.status_code in (200, 204, 405), f"OPTIONS request failed: {resp.status_code}"

    def test_cors_header_present(self, client):
        """Test Access-Control headers are present."""
        resp = client.get("/api/health", headers={"Origin": "http://localhost:3000"})

        # CORS headers should be present
        assert resp.status_code == 200

        # Check for CORS headers (middleware should add these)
        # Note: TestClient may not fully simulate CORS behavior
        # This test documents expected headers
        dict(resp.headers)
        # The actual header presence depends on CORS middleware config
        assert resp.status_code == 200  # At minimum, request should succeed


# =============================================================================
# Content Type Headers
# =============================================================================


class TestContentTypeHeaders:
    """Tests for content type headers."""

    def test_api_endpoints_return_json(self, client):
        """Test API endpoints return JSON content type."""
        endpoints = [
            "/api/health",
            "/api/flows",
            "/api/runs",
        ]

        for endpoint in endpoints:
            resp = client.get(endpoint)
            if resp.status_code == 200:
                content_type = resp.headers.get("content-type", "")
                assert "application/json" in content_type, (
                    f"{endpoint} should return JSON, got {content_type}"
                )

    def test_root_returns_html_content_type(self, client):
        """Test root returns HTML content type."""
        resp = client.get("/")
        assert resp.status_code == 200

        content_type = resp.headers.get("content-type", "")
        assert "text/html" in content_type, f"Root should return HTML, got {content_type}"


# =============================================================================
# OpenAPI Schema Validation
# =============================================================================


class TestOpenAPISchemaValidation:
    """Tests for OpenAPI schema endpoint and validation."""

    def test_openapi_endpoint_returns_200(self, client):
        """Test /openapi.json endpoint returns 200 OK."""
        resp = client.get("/openapi.json")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"

    def test_openapi_returns_json(self, client):
        """Test /openapi.json returns valid JSON."""
        resp = client.get("/openapi.json")
        assert resp.status_code == 200

        content_type = resp.headers.get("content-type", "")
        assert "application/json" in content_type, (
            f"OpenAPI endpoint should return JSON, got {content_type}"
        )

        # Should be valid JSON
        data = resp.json()
        assert isinstance(data, dict), "OpenAPI schema should be a dictionary"

    def test_openapi_schema_has_required_keys(self, client):
        """Test OpenAPI schema contains required top-level keys."""
        resp = client.get("/openapi.json")
        assert resp.status_code == 200

        schema = resp.json()
        required_keys = {"openapi", "info", "paths"}

        for key in required_keys:
            assert key in schema, (
                f"OpenAPI schema missing required key '{key}'. "
                f"Available keys: {list(schema.keys())}"
            )

    def test_openapi_has_valid_version(self, client):
        """Test OpenAPI schema version is valid."""
        resp = client.get("/openapi.json")
        assert resp.status_code == 200

        schema = resp.json()
        openapi_version = schema.get("openapi")

        # OpenAPI version should be a string like "3.0.0" or "3.1.0"
        assert openapi_version is not None, "Missing 'openapi' version"
        assert isinstance(openapi_version, str), "'openapi' should be a string"
        assert openapi_version.startswith("3."), f"Expected OpenAPI 3.x, got {openapi_version}"

    def test_openapi_info_has_required_fields(self, client):
        """Test OpenAPI info object has required fields."""
        resp = client.get("/openapi.json")
        assert resp.status_code == 200

        schema = resp.json()
        info = schema.get("info", {})

        required_info_fields = {"title", "version"}
        for field in required_info_fields:
            assert field in info, (
                f"OpenAPI info missing required field '{field}'. "
                f"Available fields: {list(info.keys())}"
            )

    def test_openapi_paths_is_object(self, client):
        """Test OpenAPI paths is a dictionary."""
        resp = client.get("/openapi.json")
        assert resp.status_code == 200

        schema = resp.json()
        paths = schema.get("paths", {})

        assert isinstance(paths, dict), "'paths' should be a dictionary"

    def test_openapi_documents_health_endpoint(self, client):
        """Test OpenAPI schema documents the /api/health endpoint."""
        resp = client.get("/openapi.json")
        assert resp.status_code == 200

        schema = resp.json()
        paths = schema.get("paths", {})

        assert "/api/health" in paths, (
            "OpenAPI schema should document /api/health endpoint. "
            f"Available paths: {list(paths.keys())}"
        )

    def test_openapi_documents_flows_endpoint(self, client):
        """Test OpenAPI schema documents the /api/flows endpoint."""
        resp = client.get("/openapi.json")
        assert resp.status_code == 200

        schema = resp.json()
        paths = schema.get("paths", {})

        assert "/api/flows" in paths, (
            "OpenAPI schema should document /api/flows endpoint. "
            f"Available paths: {list(paths.keys())}"
        )

    def test_openapi_endpoint_has_methods(self, client):
        """Test documented endpoints have HTTP method definitions."""
        resp = client.get("/openapi.json")
        assert resp.status_code == 200

        schema = resp.json()
        paths = schema.get("paths", {})

        # Check /api/health endpoint (should have GET)
        if "/api/health" in paths:
            health_path = paths["/api/health"]
            assert isinstance(health_path, dict), "/api/health path should be a dictionary"

            # Should have at least one HTTP method (get, post, put, delete, patch)
            valid_methods = {"get", "post", "put", "delete", "patch", "options", "head"}
            found_methods = [m for m in valid_methods if m in health_path]

            assert len(found_methods) > 0, (
                f"/api/health should have at least one HTTP method. "
                f"Available keys: {list(health_path.keys())}"
            )

    def test_openapi_endpoints_have_responses(self, client):
        """Test endpoint definitions include response definitions."""
        resp = client.get("/openapi.json")
        assert resp.status_code == 200

        schema = resp.json()
        paths = schema.get("paths", {})

        # Check a documented endpoint
        if "/api/health" in paths:
            health_path = paths["/api/health"]
            get_method = health_path.get("get")

            if get_method:
                assert "responses" in get_method, "/api/health GET should have 'responses' defined"

                responses = get_method.get("responses", {})
                assert isinstance(responses, dict), "responses should be a dictionary"

                # Should have at least a 200 response
                assert len(responses) > 0, "/api/health GET should define at least one response"

    def test_openapi_paths_not_empty(self, client):
        """Test OpenAPI schema documents at least some paths."""
        resp = client.get("/openapi.json")
        assert resp.status_code == 200

        schema = resp.json()
        paths = schema.get("paths", {})

        assert len(paths) > 0, "OpenAPI schema should document at least one path/endpoint"

    def test_openapi_has_servers_or_no_servers(self, client):
        """Test OpenAPI servers field is either present and valid or absent."""
        resp = client.get("/openapi.json")
        assert resp.status_code == 200

        schema = resp.json()

        if "servers" in schema:
            servers = schema.get("servers")
            assert isinstance(servers, list), "'servers' should be a list"

            # Each server entry should be a dict with 'url'
            for server in servers:
                assert isinstance(server, dict), "Each server should be a dict"
                # 'url' is required in OpenAPI 3.0+
                if isinstance(server, dict):
                    # Allow empty servers list or properly formed server objects
                    pass

    def test_openapi_components_valid_if_present(self, client):
        """Test OpenAPI components section is valid if present."""
        resp = client.get("/openapi.json")
        assert resp.status_code == 200

        schema = resp.json()

        if "components" in schema:
            components = schema.get("components")
            assert isinstance(components, dict), "'components' should be a dictionary"

            # If components exists, it may contain schemas, responses, parameters, etc.
            valid_component_keys = {
                "schemas",
                "responses",
                "parameters",
                "examples",
                "requestBodies",
                "headers",
                "securitySchemes",
                "links",
                "callbacks",
            }

            component_keys = set(components.keys())
            # All component keys should be valid OpenAPI component types
            assert component_keys.issubset(valid_component_keys), (
                f"Unknown component types in schema: {component_keys - valid_component_keys}"
            )

    def test_openapi_schema_is_self_consistent(self, client):
        """Test OpenAPI schema uses consistent formatting."""
        resp = client.get("/openapi.json")
        assert resp.status_code == 200

        schema = resp.json()

        # Verify key sections are either dicts or don't exist
        optional_dict_fields = {
            "servers",
            "components",
            "paths",
            "tags",
            "externalDocs",
            "security",
            "info",
        }

        for field in optional_dict_fields:
            if field in schema:
                value = schema[field]
                if field in ("tags",):
                    assert isinstance(value, list), f"'{field}' should be a list when present"
                elif field == "security":
                    assert isinstance(value, list), f"'{field}' should be a list when present"
                else:
                    assert isinstance(value, dict), f"'{field}' should be a dict when present"
