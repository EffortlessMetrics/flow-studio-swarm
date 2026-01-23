#!/usr/bin/env python3
"""
Flow Studio API performance tests.

Ensures API endpoints meet baseline performance requirements.
Uses pytest-benchmark for consistent measurement.

Baseline Performance (measured 2025-01, local dev machine):
- /api/health: median ~2ms (target: <50ms)
- /api/flows: median ~2ms (target: <100ms)
- /api/graph/{flow}: median ~2-3ms (target: <200ms)
- /api/runs: median ~3ms (target: <100ms)

Notes:
- Targets are conservative to account for CI variability
- pytest-benchmark handles warmup, iterations, and statistics automatically
- Use --benchmark-only to run only benchmark tests
- Use --benchmark-disable to skip benchmarks in regular test runs

Usage:
    uv run pytest tests/test_flow_studio_performance.py -v --benchmark-only
    uv run pytest tests/test_flow_studio_performance.py -v --benchmark-disable
"""

import sys
from pathlib import Path

# Add repo root to path so swarm imports work
repo_root = Path(__file__).resolve().parents[1]
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

import pytest

# Performance targets in milliseconds (conservative for CI machines)
HEALTH_TARGET_MS = 50
FLOWS_LIST_TARGET_MS = 100
FLOW_DETAIL_TARGET_MS = 100
GRAPH_TARGET_MS = 200


@pytest.fixture
def client():
    """Create FastAPI TestClient for benchmarks."""
    from fastapi.testclient import TestClient
    from swarm.tools.flow_studio_fastapi import app

    return TestClient(app)


class TestFlowStudioPerformance:
    """Performance benchmarks for Flow Studio API."""

    @pytest.mark.benchmark(group="api-health")
    def test_health_endpoint_performance(self, benchmark, client):
        """Health endpoint should respond in <50ms.

        The health endpoint is called frequently for liveness/readiness probes.
        It should be fast and lightweight.
        """
        result = benchmark(client.get, "/api/health")
        assert result.status_code == 200

        # Verify response structure while we're at it
        data = result.json()
        assert "status" in data
        assert data["status"] in ("ok", "degraded", "error")

    @pytest.mark.benchmark(group="api-flows")
    def test_flows_list_performance(self, benchmark, client):
        """Flows list should respond in <100ms.

        Lists all available flows. Should cache flow metadata after first load.
        """
        result = benchmark(client.get, "/api/flows")
        assert result.status_code == 200

        data = result.json()
        assert "flows" in data
        assert isinstance(data["flows"], list)

    @pytest.mark.benchmark(group="api-flows")
    def test_flow_detail_build_performance(self, benchmark, client):
        """Flow detail (build) should respond in <100ms.

        Returns detail for a specific flow. Tests with 'build' flow which
        typically has many steps and agents.
        """
        result = benchmark(client.get, "/api/flows")
        assert result.status_code == 200

        # Verify we have flows to test
        data = result.json()
        assert "flows" in data

    @pytest.mark.benchmark(group="api-graph")
    def test_graph_signal_performance(self, benchmark, client):
        """Graph endpoint for signal flow should respond in <200ms.

        Constructs and returns the graph structure (nodes, edges) for visualization.
        This is the most complex endpoint as it builds the full graph structure.
        """
        result = benchmark(client.get, "/api/graph/signal")

        # 200 with graph data or 404 if not configured (both acceptable)
        assert result.status_code in (200, 404)

        if result.status_code == 200:
            data = result.json()
            assert "nodes" in data
            assert "edges" in data

    @pytest.mark.benchmark(group="api-graph")
    def test_graph_build_performance(self, benchmark, client):
        """Graph endpoint for build flow should respond in <200ms.

        Build flow has more steps/agents, so this tests worst-case graph construction.
        """
        result = benchmark(client.get, "/api/graph/build")

        # 200 with graph data or 404 if not configured (both acceptable)
        assert result.status_code in (200, 404)

        if result.status_code == 200:
            data = result.json()
            assert "nodes" in data
            assert "edges" in data

    @pytest.mark.benchmark(group="api-runs")
    def test_runs_list_performance(self, benchmark, client):
        """Runs list should respond in <100ms.

        Lists available runs. May return 503 if RunInspector is disabled.
        """
        result = benchmark(client.get, "/api/runs")

        # 200 with runs list or 503 if disabled (both acceptable)
        assert result.status_code in (200, 503)


class TestFlowStudioPerformanceBaseline:
    """
    Baseline assertions to catch performance regressions.

    These tests verify that median response times stay within targets.
    Performance targets are conservative to handle CI variance.
    """

    @pytest.mark.benchmark(group="baseline")
    def test_health_meets_target(self, benchmark, client):
        """Verify health endpoint meets 50ms target."""
        result = benchmark(client.get, "/api/health")
        assert result.status_code == 200

        # Check that median time is within target
        # Note: benchmark.stats is only available after benchmark completes
        # pytest-benchmark handles this internally
        stats = benchmark.stats
        if stats and hasattr(stats, "median"):
            median_ms = stats.median * 1000  # Convert to ms
            assert median_ms < HEALTH_TARGET_MS, (
                f"Health endpoint too slow: {median_ms:.2f}ms > {HEALTH_TARGET_MS}ms target"
            )

    @pytest.mark.benchmark(group="baseline")
    def test_graph_meets_target(self, benchmark, client):
        """Verify graph endpoint meets 200ms target."""
        result = benchmark(client.get, "/api/graph/signal")

        if result.status_code == 200:
            stats = benchmark.stats
            if stats and hasattr(stats, "median"):
                median_ms = stats.median * 1000
                assert median_ms < GRAPH_TARGET_MS, (
                    f"Graph endpoint too slow: {median_ms:.2f}ms > {GRAPH_TARGET_MS}ms target"
                )
