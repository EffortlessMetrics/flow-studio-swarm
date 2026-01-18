#!/usr/bin/env python3
"""
FlowStudioCore - Unified business logic for Flow Studio.

This module extracts the core behavior of Flow Studio into reusable dataclasses
and a single FlowStudioCore class that can be used by multiple adapters
(Flask, FastAPI, CLI, etc.).

Responsibilities:
- Load flows, agents, artifacts, tours from disk
- Compute flow graphs for visualization
- Track run status and artifact presence
- Provide validation snapshots

All dataclasses have to_dict() methods for JSON serialization.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

# Import loaders from the existing flow_studio module
# We'll use these to avoid reimplementing the wheel


@dataclass
class FlowSummary:
    """Summary of a single flow for list view."""
    key: str
    title: str
    description: str
    step_count: int

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class GraphPayload:
    """Graph data for visualization (nodes and edges)."""
    nodes: List[Dict[str, Any]] = field(default_factory=list)
    edges: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class FlowStatusDetail:
    """Status summary for a single flow in a run."""
    status: str  # "complete", "partial", "missing", "not_started", "n/a"
    required_present: int = 0
    required_total: int = 0
    optional_present: int = 0
    optional_total: int = 0
    artifacts: List[Dict[str, Any]] = field(default_factory=list)
    note: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class RunSummary:
    """Summary of a complete run with all flow statuses."""
    run_id: str
    run_type: str  # "active" or "example"
    path: str
    flows: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ValidationSnapshot:
    """Snapshot of validation/governance status."""
    timestamp: str
    service: str
    governance: Dict[str, Any] = field(default_factory=dict)
    flows: Dict[str, Any] = field(default_factory=dict)
    agents: Dict[str, Any] = field(default_factory=dict)
    hints: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class FlowStudioCore:
    """
    Core business logic for Flow Studio.

    This class orchestrates loading flows, agents, and artifacts from disk,
    and provides methods for generating graphs, listing runs, and computing status.

    It is independent of any web framework and can be used by Flask, FastAPI,
    CLI tools, or other adapters.
    """

    def __init__(self, config: Optional[Any] = None):
        """
        Initialize FlowStudioCore.

        Args:
            config: Optional FlowStudioConfig. If None, uses defaults from flow_studio module.
        """
        self.config = config
        self._agents_cache: Dict[str, Any] = {}
        self._flows_cache: Dict[str, Any] = {}
        self._tours_cache: Dict[str, Any] = {}
        self._artifact_catalog_cache: Dict[str, Any] = {}
        self._run_inspector: Optional[Any] = None
        self._status_provider: Optional[Any] = None
        self._validation_data: Optional[Dict[str, Any]] = None

    def _get_repo_root(self) -> Path:
        """Get repository root path."""
        if self.config and hasattr(self.config, 'repo_root'):
            return Path(self.config.repo_root)
        return Path(__file__).resolve().parents[2]

    def _get_agents_dir(self) -> Path:
        """Get agents config directory."""
        if self.config and hasattr(self.config, 'agents_dir'):
            return Path(self.config.agents_dir)
        return self._get_repo_root() / "swarm" / "config" / "agents"

    def _get_flows_dir(self) -> Path:
        """Get flows config directory."""
        if self.config and hasattr(self.config, 'flows_dir'):
            return Path(self.config.flows_dir)
        return self._get_repo_root() / "swarm" / "config" / "flows"

    def _get_tours_dir(self) -> Path:
        """Get tours config directory."""
        if self.config and hasattr(self.config, 'tours_dir'):
            return Path(self.config.tours_dir)
        return self._get_repo_root() / "swarm" / "config" / "tours"

    def _safe_load_yaml(self, path: Path) -> Dict[str, Any]:
        """Safely load YAML from a file."""
        text = path.read_text(encoding="utf-8")
        data = yaml.safe_load(text)
        if data is None:
            return {}
        if not isinstance(data, dict):
            raise ValueError(f"Expected dict at top level in {path}, got {type(data)}")
        return data

    def load_flows(self) -> Dict[str, Any]:
        """
        Load all flows from swarm/config/flows/*.yaml.

        Returns:
            Dictionary of flows keyed by flow key.
        """
        flows: Dict[str, Any] = {}
        flows_dir = self._get_flows_dir()

        if not flows_dir.exists():
            return flows

        for cfg_path in sorted(flows_dir.glob("*.yaml")):
            data = self._safe_load_yaml(cfg_path)
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
                steps.append({
                    "id": sid,
                    "title": stitle,
                    "role": role,
                    "agents": agents_list,
                    "_search_id": sid.lower(),
                    "_search_title": stitle.lower(),
                })

            flows[key] = {
                "key": key,
                "title": title,
                "description": description,
                "steps": steps,
                "_search_key": key.lower(),
                "_search_title": title.lower(),
            }

        return flows

    def load_agents(self) -> Dict[str, Any]:
        """
        Load all agents from swarm/config/agents/*.yaml.

        Returns:
            Dictionary of agents keyed by agent key.
        """
        agents: Dict[str, Any] = {}
        agents_dir = self._get_agents_dir()

        if not agents_dir.exists():
            return agents

        for cfg_path in sorted(agents_dir.glob("*.yaml")):
            data = self._safe_load_yaml(cfg_path)
            key = data.get("key")
            if not key:
                continue

            agents[key] = {
                "key": key,
                "category": data.get("category", ""),
                "color": data.get("color", ""),
                "model": data.get("model", "inherit"),
                "short_role": (data.get("short_role") or "").strip(),
                "_search_key": key.lower(),
                "_search_role": (data.get("short_role") or "").strip().lower(),
            }

        return agents

    def reload(self) -> tuple[Dict[str, Any], Dict[str, Any]]:
        """
        Reload flows and agents from disk.

        Returns:
            Tuple of (agents_dict, flows_dict)
        """
        self._agents_cache = self.load_agents()
        self._flows_cache = self.load_flows()
        return self._agents_cache, self._flows_cache

    def list_flows(self) -> List[FlowSummary]:
        """
        List all flows as summaries.

        Returns:
            List of FlowSummary objects.
        """
        if not self._flows_cache:
            self._flows_cache = self.load_flows()

        flows: List[FlowSummary] = []
        for flow_data in self._flows_cache.values():
            flows.append(FlowSummary(
                key=flow_data["key"],
                title=flow_data["title"],
                description=flow_data["description"],
                step_count=len(flow_data.get("steps", [])),
            ))
        return flows

    def get_flow_graph(self, flow_key: str) -> GraphPayload:
        """
        Build a graph (nodes and edges) for a flow.

        Args:
            flow_key: Key of the flow to visualize.

        Returns:
            GraphPayload with nodes and edges for Cytoscape.

        Raises:
            KeyError: If flow not found.
        """
        if not self._flows_cache:
            self._flows_cache = self.load_flows()
        if not self._agents_cache:
            self._agents_cache = self.load_agents()

        if flow_key not in self._flows_cache:
            raise KeyError(f"Unknown flow {flow_key!r}")

        flow = self._flows_cache[flow_key]
        nodes: List[Dict[str, Any]] = []
        edges: List[Dict[str, Any]] = []

        # Step nodes
        for idx, step in enumerate(flow.get("steps", [])):
            nid = f"step:{flow_key}:{step['id']}"
            nodes.append({
                "data": {
                    "id": nid,
                    "label": step["title"],
                    "type": "step",
                    "flow": flow_key,
                    "step_id": step["id"],
                    "order": idx,
                }
            })

        # Step ordering edges
        steps = flow.get("steps", [])
        for i in range(len(steps) - 1):
            a = steps[i]
            b = steps[i + 1]
            edges.append({
                "data": {
                    "id": f"edge:step:{a['id']}->{b['id']}",
                    "source": f"step:{flow_key}:{a['id']}",
                    "target": f"step:{flow_key}:{b['id']}",
                    "type": "step-sequence",
                }
            })

        # Agent nodes + step->agent edges
        seen_agents: Dict[str, bool] = {}

        for step in flow.get("steps", []):
            step_node_id = f"step:{flow_key}:{step['id']}"
            for agent_key in step.get("agents", []):
                if agent_key not in seen_agents:
                    seen_agents[agent_key] = True
                    a = self._agents_cache.get(agent_key)
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
                            "color": "#9ca3af",
                            "model": "inherit",
                            "short_role": "",
                        }
                        nodes.append({"data": node_data})

                edges.append({
                    "data": {
                        "id": f"edge:step:{step['id']}->agent:{agent_key}",
                        "source": step_node_id,
                        "target": f"agent:{agent_key}",
                        "type": "step-agent",
                    }
                })

        return GraphPayload(nodes=nodes, edges=edges)

    def list_runs(self) -> List[Dict[str, Any]]:
        """
        List all available runs (active + examples).

        Delegates to RunService for unified run discovery and metadata.
        Falls back to RunInspector if RunService is unavailable.

        Returns:
            List of run dictionaries with run_id, run_type, path, metadata.
        """
        # Try to use RunService for unified run listing
        try:
            from swarm.runtime.service import RunService
            repo_root = self._get_repo_root()
            service = RunService.get_instance(repo_root)
            summaries = service.list_runs(
                include_legacy=True,
                include_examples=True,
            )

            # Convert RunSummary objects to backward-compatible dict format
            runs = []
            for summary in summaries:
                # Determine run_type from tags
                if "example" in summary.tags:
                    run_type = "example"
                else:
                    run_type = "active"

                run_data = {
                    "run_id": summary.id,
                    "run_type": run_type,
                    "path": summary.path or "",
                }

                # Add optional metadata
                if summary.title:
                    run_data["title"] = summary.title
                if summary.description:
                    run_data["description"] = summary.description
                # Extract tags (excluding type markers)
                filtered_tags = [t for t in summary.tags if t not in ("example", "legacy")]
                if filtered_tags:
                    run_data["tags"] = filtered_tags

                runs.append(run_data)

            return runs
        except ImportError:
            # Fall back to RunInspector
            try:
                if self._run_inspector is None:
                    from swarm.tools.run_inspector import RunInspector
                    repo_root = self._get_repo_root()
                    self._run_inspector = RunInspector(repo_root=repo_root)

                return self._run_inspector.list_runs()
            except ImportError:
                return []

    def get_run_summary(self, run_id: str) -> RunSummary:
        """
        Get full status summary for a run.

        Args:
            run_id: Run identifier.

        Returns:
            RunSummary with flow and step statuses.
        """
        # Try to import and use RunInspector
        try:
            if self._run_inspector is None:
                from swarm.tools.run_inspector import RunInspector
                repo_root = self._get_repo_root()
                self._run_inspector = RunInspector(repo_root=repo_root)

            result = self._run_inspector.get_run_summary(run_id)

            # Convert to RunSummary, converting nested objects to dicts
            flows_dict = {}
            for flow_key, flow_result in result.flows.items():
                steps_dict = {}
                for step_id, step_result in flow_result.steps.items():
                    steps_dict[step_id] = {
                        "status": step_result.status.value,
                        "required_present": step_result.required_present,
                        "required_total": step_result.required_total,
                        "optional_present": step_result.optional_present,
                        "optional_total": step_result.optional_total,
                        "artifacts": [
                            {
                                "path": art.path,
                                "status": art.status.value,
                                "required": art.required,
                            }
                            for art in step_result.artifacts
                        ],
                        "note": step_result.note,
                    }

                flows_dict[flow_key] = {
                    "flow_key": flow_result.flow_key,
                    "status": flow_result.status.value,
                    "title": flow_result.title,
                    "decision_artifact": flow_result.decision_artifact,
                    "decision_present": flow_result.decision_present,
                    "steps": steps_dict,
                }

            return RunSummary(
                run_id=result.run_id,
                run_type=result.run_type,
                path=result.path,
                flows=flows_dict,
            )
        except ImportError:
            return RunSummary(
                run_id=run_id,
                run_type="unknown",
                path="",
                flows={},
            )

    def get_validation_snapshot(self) -> ValidationSnapshot:
        """
        Get current validation/governance status.

        Returns:
            ValidationSnapshot with overall status and details.
        """
        # Try to import and use StatusProvider
        try:
            if self._status_provider is None:
                from swarm.tools.status_provider import StatusProvider
                repo_root = self._get_repo_root()
                # Use default TTL from env var (5 min for UI, set lower for CI)
                self._status_provider = StatusProvider(repo_root=repo_root)

            status = self._status_provider.get_status(force_refresh=False)

            return ValidationSnapshot(
                timestamp=status.timestamp,
                service=status.service,
                governance=status.governance,
                flows=status.flows if hasattr(status, 'flows') else {},
                agents=status.agents if hasattr(status, 'agents') else {},
                hints=status.hints if hasattr(status, 'hints') else {},
            )
        except ImportError:
            from datetime import datetime, timezone
            return ValidationSnapshot(
                timestamp=datetime.now(timezone.utc).isoformat(timespec="seconds"),
                service="flow-studio",
                governance={},
                flows={},
                agents={},
                hints={},
            )
