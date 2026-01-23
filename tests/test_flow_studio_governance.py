"""Flow Studio governance tests - prevent silent drift.

These tests enforce alignment between:
- swarm/meta/artifact_catalog.json (spec)
- swarm/config/flows/*.yaml (config)
- Flow Studio API (implementation)
- swarm/examples/ (example runs)

Prevents catalog/config/API drift by validating bijections and contracts.

## Test Coverage (12 tests)

### Meta Alignment Tests (4 tests)
1. test_flow_keys_bijection - Flow keys match between catalog and config
2. test_step_ids_bijection - Step IDs match between catalog and config
3. test_example_runs_discoverable - Example runs have valid metadata
4. test_decision_artifacts_consistent - Decision artifacts match expected values

### API Contract Tests (8 tests)
5. test_api_health - Health endpoint returns flow/agent counts
6. test_api_flows_list - Flows list endpoint returns all 6 flows
7. test_api_flow_detail - Flow detail endpoint returns steps/agents
8. test_api_graph_structure - Graph endpoint returns nodes/edges
9. test_api_runs_list - Runs list includes health-check example
10. test_api_run_summary - Run summary includes flow status
11. test_api_agent_usage - Agent usage shows flows where agent is used
12. test_api_tours - Tours list includes at least one tour

## Purpose
Catches drift when:
- Adding/removing flows (catalog ↔ config mismatch)
- Changing flow steps (catalog ↔ config mismatch)
- Modifying API response structure (API contract violations)
- Moving/removing example runs (discoverability failures)
"""

import json
import sys
from pathlib import Path

import pytest

import yaml

# Import FastAPI app for API tests
sys.path.insert(0, str(Path(__file__).parent.parent))
from fastapi.testclient import TestClient
from swarm.tools.flow_studio_fastapi import app


@pytest.fixture
def client():
    """FastAPI test client for Flow Studio."""
    return TestClient(app)


@pytest.fixture
def artifact_catalog():
    """Load artifact catalog."""
    catalog_path = Path(__file__).parent.parent / "swarm" / "meta" / "artifact_catalog.json"
    with open(catalog_path) as f:
        return json.load(f)


@pytest.fixture
def flow_configs():
    """Load all SDLC flow config YAMLs (excluding demo/test flows)."""
    from swarm.config.flow_registry import get_sdlc_flow_keys

    config_dir = Path(__file__).parent.parent / "swarm" / "config" / "flows"
    sdlc_keys = set(get_sdlc_flow_keys())
    configs = {}
    for yaml_file in config_dir.glob("*.yaml"):
        flow_key = yaml_file.stem
        # Only include SDLC flows, not demo/test flows
        if flow_key in sdlc_keys:
            with open(yaml_file) as f:
                configs[flow_key] = yaml.safe_load(f)
    return configs


# ============================================================================
# Meta Alignment Tests (4 tests)
# ============================================================================


def test_flow_keys_bijection(artifact_catalog, flow_configs):
    """Every flow in catalog exists in config and vice versa."""
    catalog_flows = set(artifact_catalog["flows"].keys())
    config_flows = set(flow_configs.keys())

    # Expected canonical SDLC flows (7 flows including review)
    expected_flows = {"signal", "plan", "build", "review", "gate", "deploy", "wisdom"}

    # Catalog must match expected
    assert catalog_flows == expected_flows, (
        f"Catalog flows {catalog_flows} != expected {expected_flows}"
    )

    # Config must match expected
    assert config_flows == expected_flows, (
        f"Config flows {config_flows} != expected {expected_flows}"
    )

    # Bijection: catalog ↔ config
    assert catalog_flows == config_flows, (
        f"Flow key mismatch:\n"
        f"  Catalog: {catalog_flows}\n"
        f"  Config:  {config_flows}\n"
        f"  In catalog but not config: {catalog_flows - config_flows}\n"
        f"  In config but not catalog: {config_flows - catalog_flows}"
    )


def test_step_ids_bijection(artifact_catalog, flow_configs):
    """Every step in catalog exists in flow config YAML."""
    for flow_key, catalog_flow in artifact_catalog["flows"].items():
        catalog_steps = set(catalog_flow["steps"].keys())

        # Extract step IDs from config
        config_steps = set()
        if flow_key in flow_configs and "steps" in flow_configs[flow_key]:
            for step in flow_configs[flow_key]["steps"]:
                config_steps.add(step["id"])

        # Catalog steps must be subset of config steps
        # (config may have more detail, catalog is curated)
        missing_steps = catalog_steps - config_steps
        assert not missing_steps, (
            f"Flow '{flow_key}': catalog steps missing from config: {missing_steps}\n"
            f"  Catalog steps: {sorted(catalog_steps)}\n"
            f"  Config steps:  {sorted(config_steps)}"
        )


def test_example_runs_discoverable(artifact_catalog):
    """Example runs are present and have required metadata."""
    examples_dir = Path(__file__).parent.parent / "swarm" / "examples"

    # Health-check example must exist
    health_check_dir = examples_dir / "health-check"
    assert health_check_dir.exists(), f"health-check example missing: {health_check_dir}"

    # Must have run.json
    run_json = health_check_dir / "run.json"
    assert run_json.exists(), f"health-check/run.json missing: {run_json}"

    # Validate run.json schema
    with open(run_json) as f:
        run_data = json.load(f)

    required_fields = {"title", "description", "tags"}
    missing_fields = required_fields - set(run_data.keys())
    assert not missing_fields, f"health-check/run.json missing fields: {missing_fields}"

    # Tags should be non-empty list
    assert isinstance(run_data["tags"], list), "tags must be a list"
    assert len(run_data["tags"]) > 0, "tags must not be empty"


def test_decision_artifacts_consistent(artifact_catalog):
    """Each flow's decision artifact matches expected terminal artifact."""
    expected_decision_artifacts = {
        "signal": "problem_statement.md",
        "plan": "implementation_plan.md",  # Plan's decision artifact is implementation_plan
        "build": "build_receipt.json",
        "review": "review_receipt.json",  # Review's decision artifact is review_receipt
        "gate": "merge_recommendation.md",
        "deploy": "deployment_decision.md",
        "wisdom": "learnings.md",  # Wisdom's decision artifact is learnings
    }

    for flow_key, expected_artifact in expected_decision_artifacts.items():
        catalog_flow = artifact_catalog["flows"][flow_key]
        actual_artifact = catalog_flow.get("decision_artifact")

        assert actual_artifact == expected_artifact, (
            f"Flow '{flow_key}': decision artifact mismatch:\n"
            f"  Expected: {expected_artifact}\n"
            f"  Actual:   {actual_artifact}"
        )


# ============================================================================
# API Contract Tests (8 tests)
# ============================================================================


def test_api_health(client):
    """GET /api/health returns 200 with flows and agents."""
    from swarm.config.flow_registry import get_total_flows

    response = client.get("/api/health")
    assert response.status_code == 200, f"Health check failed: {response.status_code}"

    data = response.json()
    assert "flows" in data, "Health response missing 'flows'"
    assert "agents" in data, "Health response missing 'agents'"

    # Flows should be a number matching registry (includes demo flows)
    assert isinstance(data["flows"], int), "'flows' should be an integer"
    expected_flows = get_total_flows()
    assert data["flows"] == expected_flows, f"Expected {expected_flows} flows, got {data['flows']}"


def test_api_flows_list(client):
    """GET /api/flows returns 200 with all flows from registry."""
    from swarm.config.flow_registry import get_total_flows

    response = client.get("/api/flows")
    assert response.status_code == 200, f"Flows list failed: {response.status_code}"

    data = response.json()
    assert "flows" in data, "Response missing 'flows' key"
    flows = data["flows"]

    assert isinstance(flows, list), "Flows response should be a list"
    expected_flows = get_total_flows()
    assert len(flows) == expected_flows, f"Expected {expected_flows} flows, got {len(flows)}"

    # Each flow should have key, title, description
    for flow in flows:
        assert "key" in flow, f"Flow missing 'key': {flow}"
        assert "title" in flow, f"Flow missing 'title': {flow}"
        assert "description" in flow, f"Flow missing 'description': {flow}"


def test_api_flow_detail(client):
    """GET /api/flows/build returns 200 with key, title, steps."""
    response = client.get("/api/flows/build")
    assert response.status_code == 200, f"Flow detail failed: {response.status_code}"

    data = response.json()
    assert "flow" in data, "Response missing 'flow' key"
    assert "steps" in data, "Response missing 'steps' key"

    flow = data["flow"]
    assert flow["key"] == "build", f"Expected key 'build', got {flow.get('key')}"
    assert "title" in flow, "Flow detail missing 'title'"

    # Steps should be a list
    steps = data["steps"]
    assert isinstance(steps, list), "'steps' should be a list"
    assert len(steps) > 0, "Flow should have at least one step"


def test_api_graph_structure(client):
    """GET /api/graph/signal returns 200 with nodes and edges."""
    response = client.get("/api/graph/signal")
    assert response.status_code == 200, f"Graph structure failed: {response.status_code}"

    data = response.json()
    assert "nodes" in data, "Graph response missing 'nodes'"
    assert "edges" in data, "Graph response missing 'edges'"

    # Nodes should be a list with data.id and data.type
    assert isinstance(data["nodes"], list), "'nodes' should be a list"
    assert len(data["nodes"]) > 0, "Graph should have at least one node"

    for node in data["nodes"]:
        assert "data" in node, f"Node missing 'data': {node}"
        assert "id" in node["data"], f"Node data missing 'id': {node}"
        assert "type" in node["data"], f"Node data missing 'type': {node}"


def test_api_runs_list(client):
    """GET /api/runs returns 200 with health-check in list."""
    response = client.get("/api/runs")
    assert response.status_code == 200, f"Runs list failed: {response.status_code}"

    data = response.json()
    assert "runs" in data, "Response missing 'runs' key"
    runs = data["runs"]

    assert isinstance(runs, list), "Runs response should be a list"

    # Health-check should appear in list
    run_ids = [run["run_id"] for run in runs]
    assert "health-check" in run_ids, f"health-check example not found in runs list: {run_ids}"


def test_api_run_summary(client):
    """GET /api/runs/health-check/summary returns 200 with run_id and flows."""
    response = client.get("/api/runs/health-check/summary")
    assert response.status_code == 200, f"Run summary failed: {response.status_code}"

    data = response.json()
    assert "run_id" in data, "Run summary missing 'run_id'"
    assert data["run_id"] == "health-check", (
        f"Expected run_id 'health-check', got {data.get('run_id')}"
    )

    assert "flows" in data, "Run summary missing 'flows'"
    assert isinstance(data["flows"], dict), "'flows' should be a dict"


def test_api_agent_usage(client, flow_configs):
    """GET /api/agents/code-implementer/usage returns 200 with agent and usage."""
    response = client.get("/api/agents/code-implementer/usage")
    assert response.status_code == 200, f"Agent usage failed: {response.status_code}"

    data = response.json()
    assert "agent" in data, "Agent usage missing 'agent'"
    assert data["agent"] == "code-implementer", (
        f"Expected agent 'code-implementer', got {data.get('agent')}"
    )

    assert "usage" in data, "Agent usage missing 'usage'"
    assert isinstance(data["usage"], list), "'usage' should be a list"

    # code-implementer should be used in build flow
    flow_keys = [u["flow"] for u in data["usage"]]
    assert "build" in flow_keys, f"code-implementer should be used in 'build' flow: {flow_keys}"


def test_api_tours(client):
    """GET /api/tours returns 200 with at least 1 tour."""
    response = client.get("/api/tours")
    assert response.status_code == 200, f"Tours list failed: {response.status_code}"

    data = response.json()
    assert "tours" in data, "Response missing 'tours' key"
    tours = data["tours"]

    assert isinstance(tours, list), "Tours response should be a list"
    assert len(tours) >= 1, f"Expected at least 1 tour, got {len(tours)}"

    # Each tour should have id, title, description
    for tour in tours:
        assert "id" in tour, f"Tour missing 'id': {tour}"
        assert "title" in tour, f"Tour missing 'title': {tour}"
        assert "description" in tour, f"Tour missing 'description': {tour}"
