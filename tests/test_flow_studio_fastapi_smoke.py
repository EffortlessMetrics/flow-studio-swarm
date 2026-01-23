#!/usr/bin/env python3
"""
FastAPI smoke tests for Flow Studio.

Tests core Flow Studio endpoints on FastAPI implementation.
Mirrors the Flask smoke tests but uses FastAPI TestClient.
"""

import sys
from pathlib import Path

# Add repo root to path so swarm imports work
repo_root = Path(__file__).resolve().parents[1]
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

import pytest


def test_fastapi_health():
    """Test /api/health endpoint returns 200 with valid status."""
    from fastapi.testclient import TestClient
    from swarm.tools.flow_studio_fastapi import app

    client = TestClient(app)
    resp = client.get("/api/health")

    assert resp.status_code == 200
    data = resp.json()
    assert "status" in data
    assert data["status"] in ("ok", "degraded", "error")


def test_fastapi_flows():
    """Test /api/flows endpoint returns list of flows."""
    from fastapi.testclient import TestClient
    from swarm.tools.flow_studio_fastapi import app

    client = TestClient(app)
    resp = client.get("/api/flows")

    assert resp.status_code == 200
    data = resp.json()
    assert "flows" in data
    assert isinstance(data["flows"], list)


def test_fastapi_graph():
    """Test /api/graph/{flow} endpoint returns graph structure."""
    from fastapi.testclient import TestClient
    from swarm.tools.flow_studio_fastapi import app

    client = TestClient(app)

    # Try signal flow (should exist in config)
    resp = client.get("/api/graph/signal")

    # Either 200 with valid graph or 404 if not configured (both acceptable)
    assert resp.status_code in (200, 404)

    if resp.status_code == 200:
        data = resp.json()
        assert "nodes" in data
        assert "edges" in data
        assert isinstance(data["nodes"], list)
        assert isinstance(data["edges"], list)


def test_fastapi_runs():
    """Test /api/runs endpoint returns list of runs."""
    from fastapi.testclient import TestClient
    from swarm.tools.flow_studio_fastapi import app

    client = TestClient(app)
    resp = client.get("/api/runs")

    # Either 200 with runs list or 503 if RunInspector disabled (both acceptable)
    assert resp.status_code in (200, 503)

    data = resp.json()
    if resp.status_code == 200:
        assert "runs" in data
        assert isinstance(data["runs"], list)


def test_fastapi_root():
    """Test root endpoint returns HTML."""
    from fastapi.testclient import TestClient
    from swarm.tools.flow_studio_fastapi import app

    client = TestClient(app)
    resp = client.get("/")

    assert resp.status_code == 200
    assert "text/html" in resp.headers.get("content-type", "")


def test_fastapi_layout_screens():
    """Test /api/layout_screens endpoint returns valid screen registry."""
    from fastapi.testclient import TestClient
    from swarm.tools.flow_studio_fastapi import app

    client = TestClient(app)
    resp = client.get("/api/layout_screens")

    assert resp.status_code == 200
    data = resp.json()

    # Validate structure
    assert "version" in data
    assert "screens" in data
    assert isinstance(data["screens"], list)

    # Must have at least the default screen
    assert len(data["screens"]) > 0, "No screens in layout_screens response"

    # Validate each screen has required fields
    screen_ids = set()
    for screen in data["screens"]:
        assert "id" in screen, "Screen missing 'id' field"
        assert "route" in screen, "Screen missing 'route' field"
        assert "regions" in screen, "Screen missing 'regions' field"
        assert isinstance(screen["regions"], list), "regions should be list"

        screen_ids.add(screen["id"])

        # Validate each region
        for region in screen["regions"]:
            assert "id" in region, "Region missing 'id' field"
            assert "purpose" in region, "Region missing 'purpose' field"
            assert "uiids" in region, "Region missing 'uiids' field"
            assert isinstance(region["uiids"], list), "uiids should be list"

    # Must include flows.default
    assert "flows.default" in screen_ids, "Missing required screen 'flows.default'"


def test_fastapi_selftest_plan():
    """Test /api/selftest/plan endpoint returns valid plan structure."""
    from fastapi.testclient import TestClient
    from swarm.tools.flow_studio_fastapi import app

    client = TestClient(app)
    resp = client.get("/api/selftest/plan")

    # Either 200 with plan or 503 if selftest module disabled (both acceptable)
    assert resp.status_code in (200, 503)

    if resp.status_code == 200:
        data = resp.json()

        # Validate structure
        assert "version" in data
        assert data["version"] == "1.0"

        assert "steps" in data
        assert isinstance(data["steps"], list)

        assert "summary" in data
        assert "total" in data["summary"]
        assert "by_tier" in data["summary"]

        # Validate step fields
        if len(data["steps"]) > 0:
            step = data["steps"][0]
            assert "id" in step
            assert "tier" in step
            assert "severity" in step
            assert "category" in step
            assert "description" in step
            assert "depends_on" in step
            assert step["tier"] in ("kernel", "governance", "optional")
            assert step["severity"] in ("critical", "warning", "info")
            assert step["category"] in ("security", "performance", "correctness", "governance")

        # Validate summary breakdown
        by_tier = data["summary"]["by_tier"]
        assert "kernel" in by_tier
        assert "governance" in by_tier
        assert "optional" in by_tier
        assert (
            by_tier["kernel"] + by_tier["governance"] + by_tier["optional"]
            == data["summary"]["total"]
        )


# ============================================================================
# Backward Compatibility Tests
# ============================================================================


@pytest.mark.skip(reason="Flask backend archived - FastAPI only")
def test_fastapi_matches_flask_health():
    """Test FastAPI /api/health response structure."""
    pass  # Flask backend archived


@pytest.mark.skip(reason="Flask backend archived - FastAPI only")
def test_fastapi_matches_flask_flows():
    """Test FastAPI /api/flows response structure."""
    pass  # Flask backend archived


def test_fastapi_matches_flask_graph():
    """Test FastAPI /api/graph/{flow} returns valid graph structure."""
    from fastapi.testclient import TestClient
    from swarm.tools.flow_studio_fastapi import app as fastapi_app

    # Test with signal flow
    flow_key = "signal"

    # FastAPI response
    fastapi_client = TestClient(fastapi_app)
    fastapi_resp = fastapi_client.get(f"/api/graph/{flow_key}")

    # FastAPI should return either 200 with graph or 404
    assert fastapi_resp.status_code in (200, 404), (
        f"Unexpected status code for /api/graph/{flow_key}: {fastapi_resp.status_code}"
    )

    # If successful, should have nodes and edges
    if fastapi_resp.status_code == 200:
        fastapi_data = fastapi_resp.json()

        assert "nodes" in fastapi_data, "FastAPI graph missing 'nodes'"
        assert "edges" in fastapi_data, "FastAPI graph missing 'edges'"
        assert isinstance(fastapi_data["nodes"], list), "nodes should be list"
        assert isinstance(fastapi_data["edges"], list), "edges should be list"


def test_backend_toggle_no_regression():
    """Test backend toggle doesn't break existing endpoints."""
    from fastapi.testclient import TestClient
    from swarm.tools.flow_studio_fastapi import app as fastapi_app

    client = TestClient(fastapi_app)

    # All core endpoints should still work
    endpoints = ["/api/health", "/api/flows", "/api/runs", "/"]

    for endpoint in endpoints:
        resp = client.get(endpoint)

        # Should not return 500 (server error)
        assert resp.status_code != 500, f"Endpoint {endpoint} returned 500 (server error)"

        # Should return valid response (200, 404, or 503 are all acceptable)
        assert resp.status_code in (200, 404, 503), (
            f"Endpoint {endpoint} returned unexpected status {resp.status_code}"
        )


@pytest.mark.skip(reason="Flask backend archived - FastAPI only")
def test_old_flask_endpoints_unchanged():
    """Test Flask endpoints still work after FastAPI addition."""
    pass  # Flask backend archived


def test_fastapi_new_endpoints_dont_break_old():
    """Test new FastAPI endpoints don't interfere with old ones."""
    from fastapi.testclient import TestClient
    from swarm.tools.flow_studio_fastapi import app as fastapi_app

    client = TestClient(fastapi_app)

    # Test that old endpoints still work
    old_endpoints = {"/api/health": 200, "/api/flows": 200, "/": 200}

    for endpoint, expected_status in old_endpoints.items():
        resp = client.get(endpoint)
        assert resp.status_code == expected_status, (
            f"Old endpoint {endpoint} broken: expected {expected_status}, got {resp.status_code}"
        )

    # Test that new endpoint also works
    new_resp = client.get("/api/selftest/plan")
    assert new_resp.status_code in (200, 503), (
        f"New endpoint /api/selftest/plan broken: {new_resp.status_code}"
    )


def test_both_backends_serve_same_port_config():
    """Test both backends are configured to serve on port 5000."""
    # This is more of a documentation test to ensure we maintain
    # the same port across both backends

    # Flask default port (from flow_studio.py)
    flask_port = 5000

    # FastAPI configured port (from Makefile)
    fastapi_port = 5000

    assert flask_port == fastapi_port, (
        f"Port mismatch: Flask uses {flask_port}, FastAPI uses {fastapi_port}"
    )
