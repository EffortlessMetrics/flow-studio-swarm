from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional


def load_artifact_catalog(repo_root: Path) -> Dict[str, Any]:
    catalog_path = repo_root / "swarm" / "meta" / "artifact_catalog.json"
    if not catalog_path.exists():
        return {"flows": {}}
    with catalog_path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def build_artifact_graph(
    flow_key: str,
    flow: Dict[str, Any],
    repo_root: Path,
    run_inspector: Optional[Any],
    run_id: Optional[str],
) -> Dict[str, Any]:
    artifact_catalog = load_artifact_catalog(repo_root)
    flow_catalog = artifact_catalog.get("flows", {}).get(flow_key, {})
    decision_artifact = flow_catalog.get("decision_artifact")
    step_catalog = flow_catalog.get("steps", {})

    artifact_status: Dict[str, str] = {}
    if run_id and run_inspector is not None:
        try:
            flow_result = run_inspector.get_flow_status(run_id, flow_key)
            for step_id, step_result in flow_result.steps.items():
                for artifact in step_result.artifacts:
                    artifact_status[f"{step_id}:{artifact.path}"] = artifact.status.value
        except Exception:
            pass

    nodes: List[Dict[str, Any]] = []
    edges: List[Dict[str, Any]] = []

    for idx, step in enumerate(flow.get("steps", [])):
        nid = f"step:{flow_key}:{step['id']}"
        nodes.append(
            {
                "data": {
                    "id": nid,
                    "label": step["title"],
                    "type": "step",
                    "flow": flow_key,
                    "step_id": step["id"],
                    "order": idx,
                    "role": step.get("role", ""),
                }
            }
        )

    steps = flow.get("steps", [])
    for i in range(len(steps) - 1):
        a = steps[i]
        b = steps[i + 1]
        edges.append(
            {
                "data": {
                    "id": f"edge:step:{a['id']}->{b['id']}",
                    "source": f"step:{flow_key}:{a['id']}",
                    "target": f"step:{flow_key}:{b['id']}",
                    "type": "step-sequence",
                }
            }
        )

    for step in steps:
        step_node_id = f"step:{flow_key}:{step['id']}"
        step_artifacts = step_catalog.get(step["id"], {})
        required_artifacts = step_artifacts.get("required", [])
        optional_artifacts = step_artifacts.get("optional", [])
        note = step_artifacts.get("note")

        for artifact in required_artifacts:
            artifact_id = f"artifact:{flow_key}:{step['id']}:{artifact}"
            status_key = f"{step['id']}:{artifact}"
            status = artifact_status.get(status_key, "unknown")
            is_decision = artifact == decision_artifact

            nodes.append(
                {
                    "data": {
                        "id": artifact_id,
                        "label": artifact,
                        "type": "artifact",
                        "flow": flow_key,
                        "step_id": step["id"],
                        "filename": artifact,
                        "required": True,
                        "status": status,
                        "is_decision": is_decision,
                        "note": note,
                    }
                }
            )

            edges.append(
                {
                    "data": {
                        "id": f"edge:step:{step['id']}->artifact:{artifact}",
                        "source": step_node_id,
                        "target": artifact_id,
                        "type": "step-artifact",
                    }
                }
            )

        for artifact in optional_artifacts:
            artifact_id = f"artifact:{flow_key}:{step['id']}:{artifact}"
            status_key = f"{step['id']}:{artifact}"
            status = artifact_status.get(status_key, "unknown")

            nodes.append(
                {
                    "data": {
                        "id": artifact_id,
                        "label": artifact,
                        "type": "artifact",
                        "flow": flow_key,
                        "step_id": step["id"],
                        "filename": artifact,
                        "required": False,
                        "status": status,
                        "is_decision": False,
                        "note": note,
                    }
                }
            )

            edges.append(
                {
                    "data": {
                        "id": f"edge:step:{step['id']}->artifact:{artifact}",
                        "source": step_node_id,
                        "target": artifact_id,
                        "type": "step-artifact",
                    }
                }
            )

    return {"nodes": nodes, "edges": edges}


def search(
    flows_cache: Dict[str, Any],
    agents_cache: Dict[str, Any],
    query: str,
    agent_flow_index: Optional[Dict[str, List[str]]] = None,
) -> Dict[str, Any]:
    """Search flows, steps, agents, and artifacts.

    Args:
        flows_cache: Dict of flow_key -> flow data
        agents_cache: Dict of agent_key -> agent data
        query: Search query string
        agent_flow_index: Optional pre-computed index mapping agent_key -> [flow_keys].
            When provided, enables O(1) agent-to-flow lookups instead of O(N*M) scan.
    """
    query = query.lower().strip()
    if not query:
        return {"results": [], "query": ""}

    results: List[Dict[str, Any]] = []
    max_results = 8

    for flow_key, flow in flows_cache.items():
        if len(results) >= max_results:
            break
        if query in flow_key.lower() or query in flow["title"].lower():
            results.append(
                {
                    "type": "flow",
                    "id": flow_key,
                    "label": flow["title"],
                    "match": query,
                }
            )

    for flow_key, flow in flows_cache.items():
        if len(results) >= max_results:
            break
        for step in flow.get("steps", []):
            if len(results) >= max_results:
                break
            if query in step["id"].lower() or query in step["title"].lower():
                results.append(
                    {
                        "type": "step",
                        "flow": flow_key,
                        "id": step["id"],
                        "label": step["title"],
                        "match": query,
                    }
                )

    for agent_key, agent in agents_cache.items():
        if len(results) >= max_results:
            break
        short_role = agent.get("short_role", "")
        if query in agent_key.lower() or query in short_role.lower():
            if agent_flow_index and agent_key in agent_flow_index:
                # O(1) lookup via pre-computed index - copy to prevent mutation
                agent_flows = list(agent_flow_index[agent_key])
            else:
                # O(N*M) fallback for backward compatibility
                agent_flows = []
                for flow_key, flow in flows_cache.items():
                    for step in flow.get("steps", []):
                        if agent_key in step.get("agents", []):
                            agent_flows.append(flow_key)
                            break
            results.append(
                {
                    "type": "agent",
                    "key": agent_key,
                    "label": agent_key,
                    "flows": agent_flows,
                    "match": query,
                }
            )

    common_artifacts = [
        ("signal", "normalize_input", "problem_statement.md"),
        ("signal", "author_requirements", "requirements.md"),
        ("signal", "author_bdd", "bdd_scenarios.feature"),
        ("signal", "assess_risk", "risk_assessment.md"),
        ("plan", "author_adr", "adr.md"),
        ("plan", "design_interfaces", "api_contracts.yaml"),
        ("plan", "design_observability", "observability_spec.md"),
        ("plan", "author_test_strategy", "test_plan.md"),
        ("plan", "author_work_plan", "work_plan.md"),
        ("build", "author_tests", "test_summary.md"),
        ("build", "implement_code", "impl_changes_summary.md"),
        ("build", "self_review", "build_receipt.json"),
        ("gate", "check_receipts", "receipt_audit.md"),
        ("gate", "decide_merge", "merge_decision.md"),
        ("deploy", "verify_deployment", "verification_report.md"),
        ("wisdom", "audit_artifacts", "artifact_audit.md"),
        ("wisdom", "synthesize_learnings", "learnings.md"),
    ]
    for flow, step, filename in common_artifacts:
        if len(results) >= max_results:
            break
        if query in filename.lower():
            results.append(
                {
                    "type": "artifact",
                    "flow": flow,
                    "step": step,
                    "file": filename,
                    "match": query,
                }
            )

    return {"results": results, "query": query}
