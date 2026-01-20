#!/usr/bin/env python3
"""
DEPRECATED - ARCHIVED AS OF 2025-01

This Flask backend for Flow Studio is archived and no longer maintained.

Production Flow Studio uses FastAPI: swarm/tools/flow_studio_fastapi.py

This file is preserved for reference only. It shows the legacy Flask
architecture and may be useful for:
- Understanding the migration from Flask to FastAPI
- Reference for templates/flowstudio-only (which continues to use Flask)
- Historical context for the Flow Studio evolution

DO NOT USE THIS FILE IN PRODUCTION.
DO NOT IMPORT FROM THIS FILE.

If you need Flow Studio, run: make flow-studio
This will start the FastAPI backend automatically.

If you're maintaining templates/flowstudio-only, this file is NOT relevant
to you. That template has its own Flask implementation.

flow_studio.py - Local web UI for swarm flows.

- Visualize flows → steps → agents as a node graph
- Learn how flows and agents fit together
- Keep YAML as the source of truth

Reads:
  - Flows:  swarm/config/flows/*.yaml
  - Agents: swarm/config/agents/*.yaml

Usage (from repo root):

    uv run swarm/tools/flow_studio.py

Then open:

    http://localhost:5000/

Dependencies:
  - Flask
  - PyYAML

Install via:

    uv add flask pyyaml
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Tuple

from flask import Flask, Response, jsonify, request

from swarm.utils.yaml_utils import load_yaml

# Import HTML template loader for Flow Studio UI
try:
    from swarm.tools.flow_studio_ui import get_index_html
except ImportError:
    # Fallback: use embedded constant if UI module not available
    get_index_html = None

# Import status provider for governance status endpoint
try:
    from status_provider import StatusProvider
    _STATUS_PROVIDER = None  # Lazily initialized
except ImportError:
    _STATUS_PROVIDER = None

# Import validation data provider for FR governance overlays
try:
    from flow_studio_validation import get_validation_data
    _VALIDATION_DATA = None  # Lazily initialized
except ImportError:
    _VALIDATION_DATA = None
    get_validation_data = None

# Import run inspector for artifact status overlay
try:
    # Try relative import first (when run as script from tools dir)
    from run_inspector import RunInspector
except ImportError:
    try:
        # Try absolute import (when imported as module)
        from swarm.tools.run_inspector import RunInspector
    except ImportError:
        RunInspector = None

_RUN_INSPECTOR = None  # Lazily initialized


# ---------------------------------------------------------------------------
# Paths & IR
# ---------------------------------------------------------------------------

# Import FlowStudioConfig for centralized path management
try:
    from swarm.flowstudio.config import FlowStudioConfig
    _CONFIG = FlowStudioConfig.from_file(Path(__file__), levels_up=3)
except ImportError:
    # Fallback if flowstudio module not available
    _CONFIG = None

# Legacy path constants (for backward compatibility)
REPO_ROOT = Path(__file__).resolve().parents[2]
AGENT_CONFIG_DIR = _CONFIG.agents_dir if _CONFIG else REPO_ROOT / "swarm" / "config" / "agents"
FLOW_CONFIG_DIR = _CONFIG.flows_dir if _CONFIG else REPO_ROOT / "swarm" / "config" / "flows"
TOUR_CONFIG_DIR = _CONFIG.tours_dir if _CONFIG else REPO_ROOT / "swarm" / "config" / "tours"
ARTIFACT_CATALOG_PATH = _CONFIG.artifact_catalog if _CONFIG else REPO_ROOT / "swarm" / "meta" / "artifact_catalog.json"

# Artifact catalog cache
_ARTIFACT_CATALOG: Dict[str, Any] = {}


@dataclass
class Agent:
    key: str
    category: str
    color: str
    model: str
    short_role: str


@dataclass
class Step:
    id: str
    title: str
    role: str
    agents: List[str]


@dataclass
class Flow:
    key: str
    title: str
    description: str
    steps: List[Step]


@dataclass
class TourStep:
    """A single step in a guided tour."""
    target_type: str  # "flow" or "step"
    target_flow: str
    target_step: str  # empty for flow-level targets
    title: str
    text: str
    action: str  # "select_flow" or "select_step"


@dataclass
class Tour:
    """A guided tour through the flow studio."""
    id: str
    title: str
    description: str
    steps: List[TourStep]


_AGENTS: Dict[str, Agent] = {}
_FLOWS: Dict[str, Flow] = {}
_TOURS: Dict[str, Tour] = {}


# ---------------------------------------------------------------------------
# Loading config
# ---------------------------------------------------------------------------

def _safe_load_yaml(path: Path) -> Dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    data = load_yaml(text)
    if data is None:
        return {}
    if not isinstance(data, dict):
        raise ValueError(f"Expected dict at top level in {path}, got {type(data)}")
    return data


def load_agents() -> Dict[str, Agent]:
    agents: Dict[str, Agent] = {}
    if not AGENT_CONFIG_DIR.exists():
        return agents

    for cfg_path in sorted(AGENT_CONFIG_DIR.glob("*.yaml")):
        data = _safe_load_yaml(cfg_path)
        key = data.get("key")
        if not key:
            continue
        agents[key] = Agent(
            key=key,
            category=data.get("category", ""),
            color=data.get("color", ""),
            model=data.get("model", "inherit"),
            short_role=(data.get("short_role") or "").strip(),
        )
    return agents


def load_flows() -> Dict[str, Flow]:
    flows: Dict[str, Flow] = {}
    if not FLOW_CONFIG_DIR.exists():
        return flows

    for cfg_path in sorted(FLOW_CONFIG_DIR.glob("*.yaml")):
        data = _safe_load_yaml(cfg_path)
        key = data.get("key")
        if not key:
            continue

        title = data.get("title", key)
        description = (data.get("description") or "").strip()
        steps_raw = data.get("steps") or []

        steps: List[Step] = []
        for raw in steps_raw:
            if not isinstance(raw, dict):
                continue
            sid = raw.get("id")
            if not sid:
                continue
            stitle = raw.get("title", sid)
            role = (raw.get("role") or raw.get("description") or "").strip()
            agents_list: List[str] = []
            for a in raw.get("agents") or []:
                if isinstance(a, str):
                    agents_list.append(a.strip())
            steps.append(
                Step(
                    id=sid,
                    title=stitle,
                    role=role,
                    agents=agents_list,
                )
            )

        flows[key] = Flow(
            key=key,
            title=title,
            description=description,
            steps=steps,
        )

    return flows


def load_artifact_catalog() -> Dict[str, Any]:
    """Load the artifact catalog from swarm/meta/artifact_catalog.json."""
    import json
    if not ARTIFACT_CATALOG_PATH.exists():
        return {"flows": {}}
    with open(ARTIFACT_CATALOG_PATH) as f:
        return json.load(f)


def load_tours() -> Dict[str, Tour]:
    """Load all tour configurations from swarm/config/tours/*.yaml."""
    tours: Dict[str, Tour] = {}
    if not TOUR_CONFIG_DIR.exists():
        return tours

    for cfg_path in sorted(TOUR_CONFIG_DIR.glob("*.yaml")):
        try:
            data = _safe_load_yaml(cfg_path)
            tour_id = data.get("id")
            if not tour_id:
                continue

            tour_steps: List[TourStep] = []
            for raw_step in data.get("steps") or []:
                if not isinstance(raw_step, dict):
                    continue
                target = raw_step.get("target") or {}
                tour_steps.append(
                    TourStep(
                        target_type=target.get("type", "flow"),
                        target_flow=target.get("flow", ""),
                        target_step=target.get("step", ""),
                        title=raw_step.get("title", ""),
                        text=raw_step.get("text", ""),
                        action=raw_step.get("action", "select_flow"),
                    )
                )

            tours[tour_id] = Tour(
                id=tour_id,
                title=data.get("title", tour_id),
                description=(data.get("description") or "").strip(),
                steps=tour_steps,
            )
        except Exception:
            # Skip malformed tour files
            continue

    return tours


def reload_from_disk() -> Tuple[Dict[str, Agent], Dict[str, Flow]]:
    global _AGENTS, _FLOWS, _ARTIFACT_CATALOG, _TOURS
    _AGENTS = load_agents()
    _FLOWS = load_flows()
    _ARTIFACT_CATALOG = load_artifact_catalog()
    _TOURS = load_tours()
    return _AGENTS, _FLOWS


# ---------------------------------------------------------------------------
# Graph construction (for Cytoscape)
# ---------------------------------------------------------------------------

def build_flow_graph(flow_key: str) -> Dict[str, Any]:
    """
    Build a simple graph for one flow.

    Nodes:
      - step nodes:  id=step:<flow>:<step_id>
      - agent nodes: id=agent:<agent_key>

    Edges:
      - step[i] -> step[i+1]
      - step -> agent
    """
    if flow_key not in _FLOWS:
        raise KeyError(f"Unknown flow {flow_key!r}")

    flow = _FLOWS[flow_key]

    nodes: List[Dict[str, Any]] = []
    edges: List[Dict[str, Any]] = []

    # Step nodes
    for idx, step in enumerate(flow.steps):
        nid = f"step:{flow.key}:{step.id}"
        nodes.append(
            {
                "data": {
                    "id": nid,
                    "label": step.title,
                    "type": "step",
                    "flow": flow.key,
                    "step_id": step.id,
                    "order": idx,
                }
            }
        )

    # Step ordering edges
    for i in range(len(flow.steps) - 1):
        a = flow.steps[i]
        b = flow.steps[i + 1]
        edges.append(
            {
                "data": {
                    "id": f"edge:step:{a.id}->{b.id}",
                    "source": f"step:{flow.key}:{a.id}",
                    "target": f"step:{flow.key}:{b.id}",
                    "type": "step-sequence",
                }
            }
        )

    # Agent nodes + step->agent edges
    seen_agents: Dict[str, bool] = {}

    for step in flow.steps:
        step_node_id = f"step:{flow.key}:{step.id}"
        for agent_key in step.agents:
            if agent_key not in seen_agents:
                seen_agents[agent_key] = True
                a = _AGENTS.get(agent_key)
                if a:
                    node_data = {
                        "id": f"agent:{agent_key}",
                        "label": a.key,
                        "type": "agent",
                        "agent_key": a.key,
                        "category": a.category,
                        "color": a.color,
                        "model": a.model,
                        "short_role": a.short_role,
                    }
                    # Add FR status if validation data available
                    if _VALIDATION_DATA:
                        from flow_studio_validation import get_agent_fr_status
                        fr_status = get_agent_fr_status(_VALIDATION_DATA, agent_key)
                        if fr_status:
                            node_data["fr_status"] = fr_status
                    nodes.append({"data": node_data})
                else:
                    node_data = {
                        "id": f"agent:{agent_key}",
                        "label": agent_key,
                        "type": "agent",
                        "agent_key": agent_key,
                        "category": "unknown",
                        "color": "#9ca3af",
                        "model": "inherit",
                        "short_role": "",
                    }
                    # Add FR status if validation data available
                    if _VALIDATION_DATA:
                        from flow_studio_validation import get_agent_fr_status
                        fr_status = get_agent_fr_status(_VALIDATION_DATA, agent_key)
                        if fr_status:
                            node_data["fr_status"] = fr_status
                    nodes.append({"data": node_data})

            edges.append(
                {
                    "data": {
                        "id": f"edge:step:{step.id}->agent:{agent_key}",
                        "source": step_node_id,
                        "target": f"agent:{agent_key}",
                        "type": "step-agent",
                    }
                }
            )

    return {"nodes": nodes, "edges": edges}




def build_artifact_graph(flow_key: str, run_id: str = None) -> Dict[str, Any]:
    """
    Build an artifact-centric graph for one flow.

    Nodes:
      - step nodes:     id=step:<flow>:<step_id>
      - artifact nodes: id=artifact:<flow>:<step_id>:<filename>

    Edges:
      - step[i] -> step[i+1] (solid)
      - step -> artifact (dotted, produces relationship)
    """
    if flow_key not in _FLOWS:
        raise KeyError(f"Unknown flow {flow_key!r}")

    flow = _FLOWS[flow_key]
    flow_catalog = _ARTIFACT_CATALOG.get("flows", {}).get(flow_key, {})
    decision_artifact = flow_catalog.get("decision_artifact")
    step_catalog = flow_catalog.get("steps", {})

    # Get artifact status from run inspector if run_id provided
    artifact_status: Dict[str, str] = {}  # filename -> "present" | "missing"
    if run_id and _RUN_INSPECTOR is not None:
        try:
            flow_result = _RUN_INSPECTOR.get_flow_status(run_id, flow_key)
            for step_id, step_result in flow_result.steps.items():
                for artifact in step_result.artifacts:
                    artifact_status[f"{step_id}:{artifact.path}"] = artifact.status.value
        except Exception:
            pass  # Graceful degradation if run inspector fails

    nodes: List[Dict[str, Any]] = []
    edges: List[Dict[str, Any]] = []

    # Step nodes
    for idx, step in enumerate(flow.steps):
        nid = f"step:{flow.key}:{step.id}"
        nodes.append(
            {
                "data": {
                    "id": nid,
                    "label": step.title,
                    "type": "step",
                    "flow": flow.key,
                    "step_id": step.id,
                    "order": idx,
                    "role": step.role,
                }
            }
        )

    # Step ordering edges
    for i in range(len(flow.steps) - 1):
        a = flow.steps[i]
        b = flow.steps[i + 1]
        edges.append(
            {
                "data": {
                    "id": f"edge:step:{a.id}->{b.id}",
                    "source": f"step:{flow.key}:{a.id}",
                    "target": f"step:{flow.key}:{b.id}",
                    "type": "step-sequence",
                }
            }
        )

    # Artifact nodes + step->artifact edges
    for step in flow.steps:
        step_node_id = f"step:{flow.key}:{step.id}"
        step_artifacts = step_catalog.get(step.id, {})
        required_artifacts = step_artifacts.get("required", [])
        optional_artifacts = step_artifacts.get("optional", [])
        note = step_artifacts.get("note")

        for artifact in required_artifacts:
            artifact_id = f"artifact:{flow.key}:{step.id}:{artifact}"
            status_key = f"{step.id}:{artifact}"
            status = artifact_status.get(status_key, "unknown")
            is_decision = (artifact == decision_artifact)

            nodes.append(
                {
                    "data": {
                        "id": artifact_id,
                        "label": artifact,
                        "type": "artifact",
                        "flow": flow.key,
                        "step_id": step.id,
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
                        "id": f"edge:step:{step.id}->artifact:{artifact}",
                        "source": step_node_id,
                        "target": artifact_id,
                        "type": "step-artifact",
                    }
                }
            )

        for artifact in optional_artifacts:
            artifact_id = f"artifact:{flow.key}:{step.id}:{artifact}"
            status_key = f"{step.id}:{artifact}"
            status = artifact_status.get(status_key, "unknown")

            nodes.append(
                {
                    "data": {
                        "id": artifact_id,
                        "label": artifact,
                        "type": "artifact",
                        "flow": flow.key,
                        "step_id": step.id,
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
                        "id": f"edge:step:{step.id}->artifact:{artifact}",
                        "source": step_node_id,
                        "target": artifact_id,
                        "type": "step-artifact",
                    }
                }
            )

    return {"nodes": nodes, "edges": edges}


# ---------------------------------------------------------------------------
# Flask app
# ---------------------------------------------------------------------------

def create_app() -> Flask:
    app = Flask(__name__)
    reload_from_disk()

    # Initialize status provider
    global _STATUS_PROVIDER
    if _STATUS_PROVIDER is None:
        try:
            _STATUS_PROVIDER = StatusProvider(repo_root=REPO_ROOT, cache_ttl_seconds=30)
        except Exception:
            # StatusProvider not available (graceful degradation)
            _STATUS_PROVIDER = None

    # Initialize run inspector
    global _RUN_INSPECTOR
    if _RUN_INSPECTOR is None and RunInspector is not None:
        try:
            _RUN_INSPECTOR = RunInspector(repo_root=REPO_ROOT)
        except Exception:
            # RunInspector not available (graceful degradation)
            _RUN_INSPECTOR = None

    # Initialize validation data provider
    global _VALIDATION_DATA
    if _VALIDATION_DATA is None and get_validation_data is not None:
        try:
            _VALIDATION_DATA = get_validation_data()
        except Exception:
            # Validation data not available (graceful degradation)
            _VALIDATION_DATA = None

    # Initialize FlowStudioCore
    try:
        from swarm.flowstudio.core import FlowStudioCore
        _core = FlowStudioCore(config=_CONFIG)
        _core.reload()
    except ImportError:
        _core = None

    @app.route("/")
    def index() -> Response:
        """Serve the Flow Studio UI."""
        return Response(get_index_html(), mimetype="text/html")

    @app.route("/api/health")
    def api_health() -> Response:
        import datetime

        # Get selftest status if available
        selftest_status = None
        try:
            if _STATUS_PROVIDER:
                status = _STATUS_PROVIDER.get_status(force_refresh=False)
                if hasattr(status, "selftest_summary"):
                    selftest_status = status.selftest_summary
        except Exception:
            pass  # Graceful degradation

        return jsonify(
            {
                "status": "ok",
                "version": "2.0.0",
                "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "flows": len(_FLOWS),
                "agents": len(_AGENTS),
                "selftest_status": selftest_status,
                "capabilities": {
                    "runs": _RUN_INSPECTOR is not None,
                    "timeline": _RUN_INSPECTOR is not None,
                    "governance": _STATUS_PROVIDER is not None,
                    "validation": _VALIDATION_DATA is not None
                }
            }
        )

    @app.route("/api/validation")
    def api_validation() -> Response:
        """Return cached validation data (FR status badges and governance info)."""
        if _VALIDATION_DATA is not None:
            return jsonify({"data": _VALIDATION_DATA})
        return jsonify({"data": None, "error": "validation data not available"}), 503

    @app.route("/platform/status")
    def platform_status() -> Response:
        """Get current governance status."""
        if _STATUS_PROVIDER is None:
            return jsonify(
                {
                    "error": "Status provider not available",
                    "timestamp": None,
                    "service": "demo-swarm",
                }
            ), 503

        try:
            status = _STATUS_PROVIDER.get_status(force_refresh=False)
            return jsonify(status.to_dict())
        except Exception as e:
            return jsonify(
                {
                    "error": f"Failed to compute status: {str(e)}",
                    "service": "demo-swarm",
                }
            ), 500

    @app.route("/platform/status/refresh", methods=["POST"])
    def platform_status_refresh() -> Response:
        """Force refresh of governance status (bypasses cache)."""
        if _STATUS_PROVIDER is None:
            return jsonify(
                {
                    "error": "Status provider not available",
                    "timestamp": None,
                    "service": "demo-swarm",
                }
            ), 503

        try:
            status = _STATUS_PROVIDER.get_status(force_refresh=True)
            return jsonify(status.to_dict())
        except Exception as e:
            return jsonify(
                {
                    "error": f"Failed to compute status: {str(e)}",
                    "service": "demo-swarm",
                }
            ), 500

    @app.route("/api/reload", methods=["POST"])
    def api_reload() -> Response:
        agents, flows = reload_from_disk()
        return jsonify(
            {
                "status": "ok",
                "flows": len(flows),
                "agents": len(agents),
            }
        )

    @app.route("/api/selftest/plan")
    def api_selftest_plan() -> Response:
        """Get selftest plan with all steps, tiers, and AC IDs."""
        try:
            import os
            import sys
            # Add swarm/tools to path so selftest modules can be imported
            tools_path = os.path.dirname(os.path.abspath(__file__))
            if tools_path not in sys.path:
                sys.path.insert(0, tools_path)

            from selftest import get_selftest_plan_json
            plan = get_selftest_plan_json()
            return jsonify(plan)
        except (ImportError, SystemExit):
            return jsonify(
                {"error": "Selftest module not available"}
            ), 503
        except Exception as e:
            return jsonify(
                {"error": f"Failed to get selftest plan: {str(e)}"}
            ), 500

    @app.route("/api/flows")
    def api_flows() -> Response:
        flows = []
        for f in _FLOWS.values():
            flows.append(
                {
                    "key": f.key,
                    "title": f.title,
                    "description": f.description,
                    "step_count": len(f.steps),
                }
            )
        return jsonify({"flows": flows})

    @app.route("/api/flows/<flow_key>")
    def api_flow_detail(flow_key: str) -> Response:
        flow = _FLOWS.get(flow_key)
        if not flow:
            available = sorted(_FLOWS.keys())
            return jsonify({
                "error": f"Flow '{flow_key}' not found",
                "available_flows": available,
                "hint": f"Available flows: {', '.join(available)}" if available else "No flows loaded"
            }), 404

        steps = []
        used_agents: Dict[str, bool] = {}
        for s in flow.steps:
            steps.append(
                {
                    "id": s.id,
                    "title": s.title,
                    "role": s.role,
                    "agents": s.agents,
                }
            )
            for ak in s.agents:
                used_agents[ak] = True

        agents: Dict[str, Any] = {}
        for ak in sorted(used_agents.keys()):
            a = _AGENTS.get(ak)
            if a:
                agents[ak] = asdict(a)
            else:
                agents[ak] = {
                    "key": ak,
                    "category": "unknown",
                    "color": "#9ca3af",
                    "model": "inherit",
                    "short_role": "",
                }

        return jsonify(
            {
                "flow": {
                    "key": flow.key,
                    "title": flow.title,
                    "description": flow.description,
                },
                "steps": steps,
                "agents": agents,
            }
        )

    @app.route("/api/agents")
    def api_agents() -> Response:
        return jsonify({"agents": [asdict(a) for a in _AGENTS.values()]})

    @app.route("/api/agents/<agent_key>/usage")
    def api_agent_usage(agent_key: str) -> Response:
        """
        Get usage information for an agent: which flows and steps it appears in.

        Returns:
            JSON with agent key and list of usage entries (flow, step, step_title).
        """
        usage: List[Dict[str, Any]] = []

        for flow in _FLOWS.values():
            for step in flow.steps:
                if agent_key in step.agents:
                    usage.append({
                        "flow": flow.key,
                        "flow_title": flow.title,
                        "step": step.id,
                        "step_title": step.title,
                    })

        return jsonify({
            "agent": agent_key,
            "usage": usage,
        })

    @app.route("/api/graph/<flow_key>")
    def api_graph(flow_key: str) -> Response:
        if flow_key not in _FLOWS:
            available = sorted(_FLOWS.keys())
            return jsonify({
                "error": f"Flow '{flow_key}' not found",
                "available_flows": available,
                "hint": f"Available flows: {', '.join(available)}" if available else "No flows loaded"
            }), 404
        graph = build_flow_graph(flow_key)
        return jsonify(graph)

    @app.route("/api/graph/<flow_key>/artifacts")
    def api_graph_artifacts(flow_key: str) -> Response:
        """
        Get artifact-centric graph for a flow.

        Query params:
          - run_id: Optional run ID to overlay artifact status
        """
        if flow_key not in _FLOWS:
            available = sorted(_FLOWS.keys())
            return jsonify({
                "error": f"Flow '{flow_key}' not found",
                "available_flows": available,
                "hint": f"Available flows: {', '.join(available)}" if available else "No flows loaded"
            }), 404
        run_id = request.args.get("run_id")
        graph = build_artifact_graph(flow_key, run_id)
        return jsonify(graph)


    # -------------------------------------------------------------------------
    # Run Inspector API endpoints
    # -------------------------------------------------------------------------

    @app.route("/api/runs")
    def api_runs() -> Response:
        """List all available runs (examples + active)."""
        if _RUN_INSPECTOR is None:
            return jsonify({"error": "Run inspector not available", "runs": []}), 503
        runs = _RUN_INSPECTOR.list_runs()
        return jsonify({"runs": runs})

    @app.route("/api/runs/<run_id>/sdlc")
    def api_run_sdlc(run_id: str) -> Response:
        """Get SDLC bar data for a run."""
        if _RUN_INSPECTOR is None:
            return jsonify({"error": "Run inspector not available"}), 503
        bar = _RUN_INSPECTOR.get_sdlc_bar(run_id)
        return jsonify({"run_id": run_id, "sdlc": bar})

    @app.route("/api/runs/<run_id>/summary")
    def api_run_summary(run_id: str) -> Response:
        """Get full run summary."""
        if _RUN_INSPECTOR is None:
            return jsonify({"error": "Run inspector not available"}), 503
        summary = _RUN_INSPECTOR.get_run_summary(run_id)
        return jsonify(_RUN_INSPECTOR.to_dict(summary))

    @app.route("/api/runs/<run_id>/flows/<flow_key>")
    def api_run_flow(run_id: str, flow_key: str) -> Response:
        """Get flow status for a run."""
        if _RUN_INSPECTOR is None:
            return jsonify({"error": "Run inspector not available"}), 503
        result = _RUN_INSPECTOR.get_flow_status(run_id, flow_key)
        return jsonify(_RUN_INSPECTOR.to_dict(result))

    @app.route("/api/runs/<run_id>/flows/<flow_key>/steps/<step_id>")
    def api_run_step(run_id: str, flow_key: str, step_id: str) -> Response:
        """Get step status for a run."""
        if _RUN_INSPECTOR is None:
            return jsonify({"error": "Run inspector not available"}), 503
        result = _RUN_INSPECTOR.get_step_status(run_id, flow_key, step_id)

        # Add timing if available
        step_timing = None
        if _RUN_INSPECTOR:
            flow_timing = _RUN_INSPECTOR.get_flow_timing(run_id, flow_key)
            if flow_timing:
                for st in flow_timing.steps:
                    if st.step_id == step_id:
                        step_timing = _RUN_INSPECTOR.to_dict(st)
                        break

        step_dict = _RUN_INSPECTOR.to_dict(result)
        step_dict["timing"] = step_timing
        return jsonify(step_dict)

    @app.route("/api/runs/<run_id>/timeline")
    def api_run_timeline(run_id: str) -> Response:
        """Get chronological event timeline for a run."""
        if _RUN_INSPECTOR is None:
            return jsonify({"error": "RunInspector not available"}), 503

        timeline = _RUN_INSPECTOR.get_run_timeline(run_id)
        return jsonify({
            "run_id": run_id,
            "events": [_RUN_INSPECTOR.to_dict(e) for e in timeline]
        })

    @app.route("/api/runs/<run_id>/timing")
    def api_run_timing(run_id: str) -> Response:
        """Get timing summary for a run."""
        if _RUN_INSPECTOR is None:
            return jsonify({"error": "RunInspector not available"}), 503

        timing = _RUN_INSPECTOR.get_run_timing(run_id)
        if timing is None:
            return jsonify({"run_id": run_id, "timing": None, "message": "No timing data available"})

        return jsonify({
            "run_id": run_id,
            "timing": _RUN_INSPECTOR.to_dict(timing)
        })

    @app.route("/api/runs/<run_id>/flows/<flow_key>/timing")
    def api_flow_timing(run_id: str, flow_key: str) -> Response:
        """Get timing for a specific flow in a run."""
        if _RUN_INSPECTOR is None:
            return jsonify({"error": "RunInspector not available"}), 503

        timing = _RUN_INSPECTOR.get_flow_timing(run_id, flow_key)
        if timing is None:
            return jsonify({
                "run_id": run_id,
                "flow_key": flow_key,
                "timing": None,
                "message": "No timing data available"
            })

        return jsonify({
            "run_id": run_id,
            "flow_key": flow_key,
            "timing": _RUN_INSPECTOR.to_dict(timing)
        })

    # API Compare endpoint
    @app.route("/api/runs/compare")
    def api_runs_compare() -> Response:
        """Compare two runs for a specific flow."""
        if _RUN_INSPECTOR is None:
            return jsonify({"error": "Run inspector not available"}), 503
        run_a = request.args.get("run_a")
        run_b = request.args.get("run_b")
        flow_key = request.args.get("flow")
        if not run_a or not run_b or not flow_key:
            return jsonify({"error": "Missing required parameters: run_a, run_b, flow"}), 400
        if _RUN_INSPECTOR.get_run_path(run_a) is None:
            return jsonify({"error": f"Run '{run_a}' not found"}), 404
        if _RUN_INSPECTOR.get_run_path(run_b) is None:
            return jsonify({"error": f"Run '{run_b}' not found"}), 404
        if flow_key not in _RUN_INSPECTOR.catalog.get("flows", {}):
            return jsonify({"error": f"Flow '{flow_key}' not found in catalog"}), 404
        result = _RUN_INSPECTOR.compare_flows(run_a, run_b, flow_key)
        return jsonify(result)


    # -------------------------------------------------------------------------
    # Search API endpoint
    # -------------------------------------------------------------------------

    @app.route("/api/search")
    def api_search() -> Response:
        """Search across flows, steps, agents, and artifacts."""
        query = request.args.get("q", "").lower().strip()
        if not query:
            return jsonify({"results": [], "query": ""})

        results: List[Dict[str, Any]] = []
        max_results = 8

        # Search flows
        for flow_key, flow in _FLOWS.items():
            if len(results) >= max_results:
                break
            if query in flow_key.lower() or query in flow.title.lower():
                results.append({
                    "type": "flow",
                    "id": flow_key,
                    "label": flow.title,
                    "match": query
                })

        # Search steps
        for flow_key, flow in _FLOWS.items():
            if len(results) >= max_results:
                break
            for step in flow.steps:
                if len(results) >= max_results:
                    break
                if query in step.id.lower() or query in step.title.lower():
                    results.append({
                        "type": "step",
                        "flow": flow_key,
                        "id": step.id,
                        "label": step.title,
                        "match": query
                    })

        # Search agents
        for agent_key, agent in _AGENTS.items():
            if len(results) >= max_results:
                break
            if query in agent_key.lower() or query in agent.short_role.lower():
                # Find which flows this agent belongs to
                agent_flows = []
                for flow_key, flow in _FLOWS.items():
                    for step in flow.steps:
                        if agent_key in step.agents:
                            agent_flows.append(flow_key)
                            break
                results.append({
                    "type": "agent",
                    "key": agent_key,
                    "label": agent_key,
                    "flows": agent_flows,
                    "match": query
                })

        # Search artifacts (common artifact filenames)
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
                results.append({
                    "type": "artifact",
                    "flow": flow,
                    "step": step,
                    "file": filename,
                    "match": query
                })

        return jsonify({"results": results, "query": query})

    # -------------------------------------------------------------------------
    # Guided Tours API endpoints
    # -------------------------------------------------------------------------

    @app.route("/api/tours")
    def api_tours() -> Response:
        """List all available guided tours."""
        tours = []
        for tour in _TOURS.values():
            tours.append(
                {
                    "id": tour.id,
                    "title": tour.title,
                    "description": tour.description,
                    "step_count": len(tour.steps),
                }
            )
        return jsonify({"tours": tours})

    @app.route("/api/tours/<tour_id>")
    def api_tour_detail(tour_id: str) -> Response:
        """Get full tour definition with all steps."""
        tour = _TOURS.get(tour_id)
        if not tour:
            available = sorted(_TOURS.keys())
            return jsonify({
                "error": f"Tour '{tour_id}' not found",
                "available_tours": available,
                "hint": f"Available tours: {', '.join(available)}" if available else "No tours loaded"
            }), 404

        steps = []
        for step in tour.steps:
            steps.append(
                {
                    "target": {
                        "type": step.target_type,
                        "flow": step.target_flow,
                        "step": step.target_step,
                    },
                    "title": step.title,
                    "text": step.text,
                    "action": step.action,
                }
            )

        return jsonify(
            {
                "id": tour.id,
                "title": tour.title,
                "description": tour.description,
                "steps": steps,
            }
        )

    return app



# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

def main() -> None:
    """Run Flow Studio server with configurable host and port."""
    import argparse

    parser = argparse.ArgumentParser(
        prog="flow_studio",
        description=(
            "Flow Studio - Local web UI for swarm flows.\n\n"
            "Visualize flows, steps, and agents as a node graph.\n"
            "Reads from swarm/config/flows/*.yaml and swarm/config/agents/*.yaml."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--host",
        type=str,
        default="127.0.0.1",
        help="Host to bind to (default: 127.0.0.1)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=5000,
        help="Port to bind to (default: 5000)",
    )
    parser.add_argument(
        "--no-debug",
        action="store_true",
        help="Disable Flask debug mode",
    )

    args = parser.parse_args()

    app = create_app()
    app.run(host=args.host, port=args.port, debug=not args.no_debug)


if __name__ == "__main__":
    main()
