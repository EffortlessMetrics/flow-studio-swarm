#!/usr/bin/env python3
"""
Route Canonicalization Guardrail Tests.

These tests verify that the API routes follow the canonical pattern (no trailing slashes)
and that the OpenAPI spec correctly documents these canonical routes.

**Background**:
FastAPI router composition can sometimes result in trailing-slash-only routes when
prefix management is not handled correctly. This test suite guards against that regression.

**Contract**:
- POST /api/runs should exist (not POST /api/runs/)
- POST /api/runs/autopilot should exist (not POST /api/runs/autopilot/)
- The canonical routes (without trailing slash) must be documented in OpenAPI

**Test Coverage**:
1. test_canonical_routes_in_openapi - Canonical routes exist in OpenAPI schema
2. test_post_runs_no_trailing_slash - POST /api/runs works (not 404)
3. test_post_autopilot_no_trailing_slash - POST /api/runs/autopilot works (not 404)
"""

import sys
from pathlib import Path

# Add repo root to path
repo_root = Path(__file__).resolve().parents[1]
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

import pytest


@pytest.fixture
def api_app():
    """Create the FastAPI app via create_app factory."""
    from swarm.api.server import create_app

    return create_app()


@pytest.fixture
def api_client(api_app):
    """Create FastAPI test client."""
    from fastapi.testclient import TestClient

    return TestClient(api_app)


class TestRouteCanonicalisation:
    """Guardrail tests for canonical route patterns in OpenAPI."""

    def test_canonical_routes_in_openapi(self, api_app):
        """
        OpenAPI should contain canonical routes without trailing slashes.

        **Contract**:
        - POST /api/runs should exist (for starting runs)
        - POST /api/runs/autopilot should exist (for starting autopilot)
        - GET /api/runs should exist (for listing runs)

        These are the canonical forms. Trailing-slash-only variants would indicate
        a router composition bug.
        """
        openapi = api_app.openapi()
        paths = openapi.get("paths", {})

        # Canonical routes should exist
        assert "/api/runs" in paths, (
            "Canonical route '/api/runs' should exist in OpenAPI. "
            "If only '/api/runs/' exists, there is a router prefix bug."
        )
        assert "/api/runs/autopilot" in paths, (
            "Canonical route '/api/runs/autopilot' should exist in OpenAPI. "
            "If only '/api/runs/autopilot/' exists, there is a router prefix bug."
        )

        # Verify the correct HTTP methods are documented
        runs_path = paths.get("/api/runs", {})
        assert "post" in runs_path, (
            "POST method should be documented for /api/runs"
        )
        assert "get" in runs_path, (
            "GET method should be documented for /api/runs"
        )

        autopilot_path = paths.get("/api/runs/autopilot", {})
        assert "post" in autopilot_path, (
            "POST method should be documented for /api/runs/autopilot"
        )

    def test_trailing_slash_variants_not_primary(self, api_app):
        """
        Trailing-slash variants should not be the ONLY way to access routes.

        **Contract**:
        - If /api/runs/ exists, /api/runs must also exist
        - If /api/runs/autopilot/ exists, /api/runs/autopilot must also exist

        This guards against router composition bugs where the canonical route
        is accidentally omitted.
        """
        openapi = api_app.openapi()
        paths = openapi.get("paths", {})

        # If trailing-slash variants exist, canonical must also exist
        if "/api/runs/" in paths:
            assert "/api/runs" in paths, (
                "If '/api/runs/' exists, canonical '/api/runs' must also exist. "
                "Trailing-slash-only routes indicate a router composition bug."
            )

        if "/api/runs/autopilot/" in paths:
            assert "/api/runs/autopilot" in paths, (
                "If '/api/runs/autopilot/' exists, canonical '/api/runs/autopilot' must also exist. "
                "Trailing-slash-only routes indicate a router composition bug."
            )

    def test_post_runs_endpoint_reachable(self, api_client):
        """
        POST /api/runs should be reachable (not 404 due to missing route).

        This test verifies the route is actually registered, not just documented.
        We expect 422 (validation error due to missing body) or 201 (success),
        but NOT 404 (route not found) or 307 (redirect to trailing slash).
        """
        # POST with empty body - expect validation error (422), not route error (404/307)
        response = api_client.post("/api/runs", json={})

        # 422 = route found, validation failed (expected since flow_id required)
        # 201 = route found, run created (unlikely without valid flow_id)
        # 404 = route NOT found (BUG - indicates missing canonical route)
        # 307 = redirect to /api/runs/ (BUG - indicates wrong prefix config)
        assert response.status_code in (201, 422, 500), (
            f"POST /api/runs returned {response.status_code}. "
            f"Expected 422 (validation) or 201/500 (handled). "
            f"404 or 307 indicates router composition bug. "
            f"Response: {response.text[:200]}"
        )

    def test_post_autopilot_endpoint_reachable(self, api_client):
        """
        POST /api/runs/autopilot should be reachable (not 404 due to missing route).

        This test verifies the route is actually registered, not just documented.
        """
        # POST with empty body
        response = api_client.post("/api/runs/autopilot", json={})

        # 422 = route found, validation failed
        # 201/202 = route found, autopilot started
        # 500 = route found, internal error (acceptable for this test)
        # 404 = route NOT found (BUG)
        # 307 = redirect (BUG)
        assert response.status_code in (201, 202, 422, 500), (
            f"POST /api/runs/autopilot returned {response.status_code}. "
            f"Expected 422 (validation) or 201/202/500 (handled). "
            f"404 or 307 indicates router composition bug. "
            f"Response: {response.text[:200]}"
        )

    def test_get_runs_endpoint_reachable(self, api_client):
        """
        GET /api/runs should be reachable (not 404 due to missing route).

        This test verifies the list runs endpoint is properly registered.
        """
        response = api_client.get("/api/runs")

        # 200 = route found, runs listed
        # 500 = route found, internal error (acceptable for this test)
        # 404 = route NOT found (BUG)
        # 307 = redirect (BUG)
        assert response.status_code in (200, 500), (
            f"GET /api/runs returned {response.status_code}. "
            f"Expected 200 (success) or 500 (internal error). "
            f"404 or 307 indicates router composition bug. "
            f"Response: {response.text[:200]}"
        )

    def test_openapi_documents_all_run_methods(self, api_app):
        """
        Verify all expected HTTP methods are documented for run endpoints.

        **Contract**:
        - /api/runs: GET (list), POST (create)
        - /api/runs/{run_id}: GET (read), DELETE (cancel)
        - /api/runs/autopilot: POST (start)
        """
        openapi = api_app.openapi()
        paths = openapi.get("paths", {})

        # /api/runs should have GET and POST
        runs_path = paths.get("/api/runs", {})
        assert "get" in runs_path, "/api/runs should support GET (list runs)"
        assert "post" in runs_path, "/api/runs should support POST (create run)"

        # /api/runs/autopilot should have POST
        autopilot_path = paths.get("/api/runs/autopilot", {})
        assert "post" in autopilot_path, "/api/runs/autopilot should support POST"

        # /api/runs/{run_id} should exist with GET
        run_id_paths = [p for p in paths if p.startswith("/api/runs/{") and "autopilot" not in p]
        assert len(run_id_paths) > 0, (
            "Expected at least one /api/runs/{run_id} path for individual run access"
        )


class TestRouteCanonicalSummary:
    """Summary test that documents the canonical route structure."""

    def test_canonical_route_summary(self, api_app):
        """
        Summary test documenting expected canonical routes.

        This test serves as living documentation of the expected route structure.
        """
        openapi = api_app.openapi()
        paths = openapi.get("paths", {})

        # Document expected canonical routes (without trailing slash)
        expected_canonical = [
            "/api/runs",           # POST: create, GET: list
            "/api/runs/autopilot", # POST: start autopilot
        ]

        missing = []
        for route in expected_canonical:
            if route not in paths:
                missing.append(route)

        assert not missing, (
            f"Missing canonical routes in OpenAPI: {missing}\n"
            f"These routes should exist without trailing slashes.\n"
            f"Actual paths containing 'runs': {[p for p in paths if 'runs' in p]}"
        )

        # Log the actual routes for visibility
        runs_routes = sorted([p for p in paths if "/runs" in p])
        print(f"\n[INFO] Runs-related routes in OpenAPI: {runs_routes}")


class TestOperationIdUniqueness:
    """Guardrail tests for unique operation IDs in OpenAPI schema."""

    def test_openapi_operation_ids_unique(self, api_app):
        """
        All OpenAPI operation IDs must be unique.

        **Background**:
        FastAPI auto-generates operation IDs from function names. When multiple
        endpoints share the same function name (e.g., `list_runs` in server.py
        and in runs_crud.py), this causes duplicate operation ID warnings.

        **Contract**:
        - Every operation in the OpenAPI schema must have a unique operationId
        - Duplicates indicate either:
          1. Duplicate endpoints (same path + method) - serious bug
          2. Same function name used in multiple route modules - naming issue

        **Fix Options**:
        - Add explicit `operation_id="unique_name"` to the route decorator
        - Rename the handler function to be unique
        - Remove duplicate route definitions
        """
        from collections import Counter

        openapi = api_app.openapi()
        paths = openapi.get("paths", {})

        # Collect all operation IDs
        operation_ids = []
        op_id_to_routes = {}  # For debugging: map op_id to its routes

        for path, methods in paths.items():
            for method, operation in methods.items():
                if method in ("parameters", "servers"):
                    continue  # Skip non-method keys
                op_id = operation.get("operationId")
                if op_id:
                    operation_ids.append(op_id)
                    if op_id not in op_id_to_routes:
                        op_id_to_routes[op_id] = []
                    op_id_to_routes[op_id].append(f"{method.upper()} {path}")

        # Find duplicates
        duplicates = {k: v for k, v in Counter(operation_ids).items() if v > 1}

        if duplicates:
            # Build detailed error message
            dup_details = []
            for op_id, count in duplicates.items():
                routes = op_id_to_routes.get(op_id, [])
                dup_details.append(f"  {op_id} ({count} occurrences): {routes}")

            assert False, (
                f"Duplicate OpenAPI operation IDs found:\n"
                + "\n".join(dup_details)
                + "\n\nFix by adding explicit operation_id to route decorators "
                "or removing duplicate endpoints."
            )

    def test_no_duplicate_routes(self, api_app):
        """
        No duplicate route paths with the same HTTP method.

        **Contract**:
        - Each (method, path) combination must be unique
        - Duplicates indicate router composition bugs (e.g., same route registered twice)
        """
        from collections import Counter
        from fastapi.routing import APIRoute

        routes = []
        for route in api_app.routes:
            if isinstance(route, APIRoute):
                # Get methods excluding HEAD and OPTIONS (auto-generated)
                methods = tuple(
                    sorted(m for m in route.methods if m not in {"HEAD", "OPTIONS"})
                )
                routes.append((methods, route.path))

        duplicates = {k: v for k, v in Counter(routes).items() if v > 1}

        if duplicates:
            dup_details = [f"  {methods} {path} ({count}x)" for (methods, path), count in duplicates.items()]
            assert False, (
                f"Duplicate route registrations found:\n"
                + "\n".join(dup_details)
                + "\n\nThis indicates a router composition bug - check include_router calls."
            )
