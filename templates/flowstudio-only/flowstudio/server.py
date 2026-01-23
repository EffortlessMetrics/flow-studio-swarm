"""
Flow Studio Flask server.

Minimal Flask application providing API endpoints for flow visualization.
Serves both the API and an embedded HTML UI for interactive graph exploration.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from flask import Flask, Response, jsonify

import yaml

from .config import FlowStudioConfig, get_default_config


def safe_load_yaml(path: Path) -> Dict[str, Any]:
    """Safely load YAML from a file."""
    text = path.read_text(encoding="utf-8")
    data = yaml.safe_load(text)
    if data is None:
        return {}
    if not isinstance(data, dict):
        raise ValueError(f"Expected dict at top level in {path}, got {type(data)}")
    return data


def load_flows(config: FlowStudioConfig) -> Dict[str, Any]:
    """
    Load all flows from config/flows/*.yaml.

    Returns:
        Dictionary of flows keyed by flow key.
    """
    flows: Dict[str, Any] = {}

    if not config.flows_dir.exists():
        return flows

    for cfg_path in sorted(config.flows_dir.glob("*.yaml")):
        data = safe_load_yaml(cfg_path)
        key = data.get("key")
        if not key:
            continue

        title = data.get("title", key)
        description = (data.get("description") or "").strip()
        steps_raw = data.get("steps") or []

        steps: List[Dict[str, Any]] = []
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
                {
                    "id": sid,
                    "title": stitle,
                    "role": role,
                    "agents": agents_list,
                }
            )

        flows[key] = {
            "key": key,
            "title": title,
            "description": description,
            "steps": steps,
        }

    return flows


def load_agents(config: FlowStudioConfig) -> Dict[str, Any]:
    """
    Load all agents from config/agents/*.yaml.

    Returns:
        Dictionary of agents keyed by agent key.
    """
    agents: Dict[str, Any] = {}

    if not config.agents_dir.exists():
        return agents

    for cfg_path in sorted(config.agents_dir.glob("*.yaml")):
        data = safe_load_yaml(cfg_path)
        key = data.get("key")
        if not key:
            continue

        agents[key] = {
            "key": key,
            "category": data.get("category", ""),
            "color": data.get("color", "gray"),
            "model": data.get("model", "inherit"),
            "short_role": (data.get("short_role") or "").strip(),
        }

    return agents


def build_graph(flow_key: str, flows: Dict[str, Any], agents: Dict[str, Any]) -> Dict[str, Any]:
    """
    Build a graph (nodes and edges) for a flow.

    Args:
        flow_key: Key of the flow to visualize.
        flows: Dictionary of all flows.
        agents: Dictionary of all agents.

    Returns:
        Dictionary with 'nodes' and 'edges' for Cytoscape.

    Raises:
        KeyError: If flow not found.
    """
    if flow_key not in flows:
        raise KeyError(f"Unknown flow {flow_key!r}")

    flow = flows[flow_key]
    nodes: List[Dict[str, Any]] = []
    edges: List[Dict[str, Any]] = []

    # Step nodes
    for idx, step in enumerate(flow.get("steps", [])):
        nid = f"step:{flow_key}:{step['id']}"
        nodes.append(
            {
                "data": {
                    "id": nid,
                    "label": step.get("title", step["id"]),
                    "type": "step",
                    "flow": flow_key,
                    "step_id": step["id"],
                    "order": idx,
                    "role": step.get("role", ""),
                }
            }
        )

    # Step ordering edges
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

    # Agent nodes + step->agent edges
    seen_agents: Dict[str, bool] = {}

    for step in flow.get("steps", []):
        step_node_id = f"step:{flow_key}:{step['id']}"
        for agent_key in step.get("agents", []):
            if agent_key not in seen_agents:
                seen_agents[agent_key] = True
                a = agents.get(agent_key)
                if a:
                    node_data = {
                        "id": f"agent:{agent_key}",
                        "label": a["key"],
                        "type": "agent",
                        "agent_key": a["key"],
                        "category": a["category"],
                        "color": a["color"],
                        "model": a["model"],
                        "short_role": a["short_role"],
                    }
                    nodes.append({"data": node_data})
                else:
                    node_data = {
                        "id": f"agent:{agent_key}",
                        "label": agent_key,
                        "type": "agent",
                        "agent_key": agent_key,
                        "category": "unknown",
                        "color": "gray",
                        "model": "inherit",
                        "short_role": "",
                    }
                    nodes.append({"data": node_data})

            edges.append(
                {
                    "data": {
                        "id": f"edge:step:{step['id']}->agent:{agent_key}",
                        "source": step_node_id,
                        "target": f"agent:{agent_key}",
                        "type": "step-agent",
                    }
                }
            )

    return {"nodes": nodes, "edges": edges}


def create_app(config: Optional[FlowStudioConfig] = None) -> Flask:
    """
    Create and configure the Flask application.

    Args:
        config: Optional FlowStudioConfig. If None, uses default config.

    Returns:
        Configured Flask application.
    """
    if config is None:
        config = get_default_config()

    app = Flask(__name__)

    # Cache for flows and agents
    _cache: Dict[str, Any] = {"flows": {}, "agents": {}}

    def reload_data() -> None:
        """Reload flows and agents from disk."""
        _cache["flows"] = load_flows(config)
        _cache["agents"] = load_agents(config)

    # Initial load
    reload_data()

    @app.route("/")
    def index() -> Response:
        """Serve the main UI page."""
        # TODO: Embed full Cytoscape.js UI here
        # For now, return a minimal placeholder
        html = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Flow Studio</title>
    <style>
        body { font-family: system-ui, sans-serif; margin: 2rem; }
        h1 { color: #333; }
        .flow-list { list-style: none; padding: 0; }
        .flow-list li { margin: 0.5rem 0; }
        .flow-list a { color: #0066cc; text-decoration: none; }
        .flow-list a:hover { text-decoration: underline; }
        pre { background: #f5f5f5; padding: 1rem; border-radius: 4px; overflow-x: auto; }
        #graph { width: 100%; height: 500px; border: 1px solid #ccc; margin-top: 1rem; }
    </style>
    <!-- TODO: Add Cytoscape.js for graph visualization -->
    <script src="https://cdnjs.cloudflare.com/ajax/libs/cytoscape/3.28.1/cytoscape.min.js"></script>
</head>
<body>
    <h1>Flow Studio</h1>
    <p>Visualize any YAML-defined flow graph.</p>

    <h2>Available Flows</h2>
    <div id="flow-list">Loading...</div>

    <h2>Graph</h2>
    <div id="graph"></div>

    <script>
        // Color mapping for agent categories
        const colorMap = {
            'yellow': '#fbbf24',
            'purple': '#a855f7',
            'green': '#22c55e',
            'red': '#ef4444',
            'blue': '#3b82f6',
            'orange': '#f97316',
            'pink': '#ec4899',
            'cyan': '#06b6d4',
            'gray': '#9ca3af',
        };

        let cy = null;

        async function loadFlows() {
            const resp = await fetch('/api/flows');
            const flows = await resp.json();

            const list = document.getElementById('flow-list');
            if (flows.length === 0) {
                list.innerHTML = '<p>No flows found. Add YAML files to config/flows/</p>';
                return;
            }

            list.innerHTML = '<ul class="flow-list">' + flows.map(f =>
                `<li><a href="#" onclick="loadGraph('${f.key}')">${f.title}</a> - ${f.description} (${f.step_count} steps)</li>`
            ).join('') + '</ul>';

            // Load first flow by default
            if (flows.length > 0) {
                loadGraph(flows[0].key);
            }
        }

        async function loadGraph(flowKey) {
            const resp = await fetch('/api/graph/' + flowKey);
            const graph = await resp.json();

            if (cy) {
                cy.destroy();
            }

            cy = cytoscape({
                container: document.getElementById('graph'),
                elements: [...graph.nodes, ...graph.edges],
                style: [
                    {
                        selector: 'node[type="step"]',
                        style: {
                            'background-color': '#14b8a6',
                            'label': 'data(label)',
                            'color': '#fff',
                            'text-valign': 'center',
                            'text-halign': 'center',
                            'shape': 'round-rectangle',
                            'width': 'label',
                            'height': 40,
                            'padding': '10px',
                        }
                    },
                    {
                        selector: 'node[type="agent"]',
                        style: {
                            'background-color': function(ele) {
                                return colorMap[ele.data('color')] || '#9ca3af';
                            },
                            'label': 'data(label)',
                            'color': '#fff',
                            'text-valign': 'center',
                            'text-halign': 'center',
                            'shape': 'ellipse',
                            'width': 'label',
                            'height': 40,
                            'padding': '10px',
                        }
                    },
                    {
                        selector: 'edge[type="step-sequence"]',
                        style: {
                            'width': 3,
                            'line-color': '#14b8a6',
                            'target-arrow-color': '#14b8a6',
                            'target-arrow-shape': 'triangle',
                            'curve-style': 'bezier',
                        }
                    },
                    {
                        selector: 'edge[type="step-agent"]',
                        style: {
                            'width': 1,
                            'line-color': '#9ca3af',
                            'line-style': 'dashed',
                            'target-arrow-shape': 'none',
                            'curve-style': 'bezier',
                        }
                    },
                ],
                layout: {
                    name: 'breadthfirst',
                    directed: true,
                    padding: 30,
                    spacingFactor: 1.5,
                }
            });
        }

        loadFlows();
    </script>
</body>
</html>
"""
        return Response(html, mimetype="text/html")

    @app.route("/api/flows")
    def api_flows() -> Response:
        """List all available flows."""
        flows_list = [
            {
                "key": f["key"],
                "title": f["title"],
                "description": f["description"],
                "step_count": len(f.get("steps", [])),
            }
            for f in _cache["flows"].values()
        ]
        return jsonify(flows_list)

    @app.route("/api/graph/<flow_key>")
    def api_graph(flow_key: str) -> Response:
        """Get graph data for a specific flow."""
        try:
            graph = build_graph(flow_key, _cache["flows"], _cache["agents"])
            return jsonify(graph)
        except KeyError as e:
            return jsonify({"error": str(e)}), 404

    @app.route("/api/reload", methods=["POST"])
    def api_reload() -> Response:
        """Reload flows and agents from disk."""
        reload_data()
        return jsonify(
            {
                "status": "ok",
                "flows": len(_cache["flows"]),
                "agents": len(_cache["agents"]),
            }
        )

    @app.route("/health")
    def health() -> Response:
        """Health check endpoint."""
        return jsonify(
            {
                "status": "ok",
                "flows": len(_cache["flows"]),
                "agents": len(_cache["agents"]),
            }
        )

    return app


def main() -> None:
    """Run the Flask development server."""
    import argparse

    parser = argparse.ArgumentParser(description="Flow Studio - Visualize YAML flow graphs")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind to")
    parser.add_argument("--port", type=int, default=5000, help="Port to bind to")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    parser.add_argument("--config-dir", type=str, help="Path to config directory")

    args = parser.parse_args()

    if args.config_dir:
        config = FlowStudioConfig.from_project_root(Path(args.config_dir))
    else:
        config = get_default_config()

    errors = config.validate()
    if errors:
        print("Configuration errors:")
        for e in errors:
            print(f"  - {e}")
        print("\nMake sure config/flows/ and config/agents/ directories exist.")
        return

    app = create_app(config)
    print(f"Starting Flow Studio at http://{args.host}:{args.port}")
    app.run(host=args.host, port=args.port, debug=args.debug)


if __name__ == "__main__":
    main()
