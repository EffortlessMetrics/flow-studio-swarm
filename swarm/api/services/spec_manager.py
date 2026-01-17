"""
SpecManager - Centralized Spec Management Service.

Manages spec loading, caching, and mutations for:
- Flow graphs (swarm/spec/flows/*.yaml)
- Templates (swarm/spec/templates/*.yaml)
- Run state (swarm/runs/*/run_state.json)

The SpecManager is the single source of truth for flow graphs, templates,
and run state. It handles:
- Loading specs from YAML files
- Computing ETags for optimistic concurrency
- Validating spec mutations
- Compiling PromptPlans
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, AsyncGenerator, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class SpecManager:
    """Manages spec loading, caching, and mutations.

    The SpecManager is the single source of truth for flow graphs, templates,
    and run state. It handles:
    - Loading specs from YAML files
    - Computing ETags for optimistic concurrency
    - Validating spec mutations
    - Compiling PromptPlans

    Attributes:
        repo_root: Repository root path.
        spec_root: Path to spec directory (swarm/spec).
        runs_root: Path to runs directory (swarm/runs).
        _flow_cache: Cached flow graphs with ETags.
        _template_cache: Cached templates with ETags.
    """

    def __init__(self, repo_root: Optional[Path] = None):
        """Initialize the SpecManager.

        Args:
            repo_root: Repository root path. If not provided, auto-detects
                by walking up from current file.
        """
        if repo_root is None:
            repo_root = self._find_repo_root()

        self.repo_root = repo_root
        self.spec_root = repo_root / "swarm" / "spec"
        self.runs_root = repo_root / "swarm" / "runs"
        self.flows_config = repo_root / "swarm" / "config" / "flows"

        self._flow_cache: Dict[str, Tuple[Dict[str, Any], str]] = {}
        self._template_cache: Dict[str, Tuple[Dict[str, Any], str]] = {}
        self._run_state_cache: Dict[str, Tuple[Dict[str, Any], str]] = {}

        logger.info("SpecManager initialized with repo_root=%s", repo_root)

    @staticmethod
    def _find_repo_root() -> Path:
        """Find repository root by looking for .git directory.

        The .git directory is the most reliable indicator of repo root,
        as there may be CLAUDE.md files in subdirectories.
        """
        current = Path(__file__).resolve()
        for parent in current.parents:
            if (parent / ".git").exists():
                return parent
        # Fallback: look for root CLAUDE.md (only at actual roots)
        for parent in current.parents:
            if (parent / "CLAUDE.md").exists() and (parent / "swarm").exists():
                return parent
        raise RuntimeError("Could not find repository root")

    def _compute_etag(self, data: Any) -> str:
        """Compute ETag hash for data.

        Args:
            data: Data to hash (will be JSON serialized).

        Returns:
            Shortened SHA256 hash as ETag.
        """
        content = json.dumps(data, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    # -------------------------------------------------------------------------
    # Flow Graph Operations
    # -------------------------------------------------------------------------

    def list_flows(self) -> List[Dict[str, Any]]:
        """List all available flow graphs.

        Returns:
            List of flow summaries with id, title, flow_number, version.
        """
        flows = []

        # Check for flow graph specs in swarm/spec/flows/
        flow_graphs_dir = self.spec_root / "flows"
        if flow_graphs_dir.exists():
            for yaml_file in flow_graphs_dir.glob("*.yaml"):
                try:
                    flow_data = self._load_yaml(yaml_file)
                    flows.append(
                        {
                            "id": flow_data.get("id", yaml_file.stem),
                            "title": flow_data.get("title", yaml_file.stem),
                            "flow_number": flow_data.get("flow_number"),
                            "version": flow_data.get("version", 1),
                            "description": flow_data.get("description", ""),
                        }
                    )
                except Exception as e:
                    logger.warning("Failed to load flow %s: %s", yaml_file, e)

        # Also check config/flows for legacy flow definitions
        if self.flows_config.exists():
            for yaml_file in self.flows_config.glob("*.yaml"):
                flow_id = yaml_file.stem
                # Skip if already loaded from spec/flows
                if any(f["id"] == flow_id for f in flows):
                    continue
                try:
                    flow_data = self._load_yaml(yaml_file)
                    flows.append(
                        {
                            "id": flow_id,
                            "title": flow_data.get("name", flow_id),
                            "flow_number": flow_data.get("flow_number"),
                            "version": flow_data.get("version", 1),
                            "description": flow_data.get("description", ""),
                        }
                    )
                except Exception as e:
                    logger.warning("Failed to load flow config %s: %s", yaml_file, e)

        # Sort by flow_number
        flows.sort(key=lambda f: f.get("flow_number") or 99)
        return flows

    def get_flow(self, flow_id: str) -> Tuple[Dict[str, Any], str]:
        """Get a flow graph by ID.

        Args:
            flow_id: Flow identifier.

        Returns:
            Tuple of (flow_data, etag).

        Raises:
            FileNotFoundError: If flow not found.
        """
        # Check cache
        if flow_id in self._flow_cache:
            return self._flow_cache[flow_id]

        # Try spec/flows first
        flow_file = self.spec_root / "flows" / f"{flow_id}.yaml"
        if not flow_file.exists():
            # Try config/flows
            flow_file = self.flows_config / f"{flow_id}.yaml"

        if not flow_file.exists():
            raise FileNotFoundError(f"Flow '{flow_id}' not found")

        flow_data = self._load_yaml(flow_file)
        etag = self._compute_etag(flow_data)

        self._flow_cache[flow_id] = (flow_data, etag)
        return flow_data, etag

    def update_flow(
        self,
        flow_id: str,
        patch_operations: List[Dict[str, Any]],
        expected_etag: str,
    ) -> Tuple[Dict[str, Any], str]:
        """Update a flow graph with JSON Patch operations.

        Args:
            flow_id: Flow identifier.
            patch_operations: List of JSON Patch operations.
            expected_etag: Expected ETag for optimistic concurrency.

        Returns:
            Tuple of (updated_flow_data, new_etag).

        Raises:
            FileNotFoundError: If flow not found.
            ValueError: If ETag mismatch (concurrent modification).
        """
        flow_data, current_etag = self.get_flow(flow_id)

        if current_etag != expected_etag:
            raise ValueError(f"ETag mismatch: expected {expected_etag}, got {current_etag}")

        # Apply JSON Patch operations
        import copy

        updated_data = copy.deepcopy(flow_data)

        for op in patch_operations:
            operation = op.get("op")
            path = op.get("path", "").split("/")[1:]  # Skip empty first element
            value = op.get("value")

            if operation == "replace":
                self._set_nested(updated_data, path, value)
            elif operation == "add":
                self._add_nested(updated_data, path, value)
            elif operation == "remove":
                self._remove_nested(updated_data, path)
            else:
                raise ValueError(f"Unsupported patch operation: {operation}")

        # Validate the updated flow
        validation_errors = self.validate_flow(updated_data)
        if validation_errors:
            raise ValueError(f"Validation failed: {validation_errors}")

        # Save to file
        flow_file = self.spec_root / "flows" / f"{flow_id}.yaml"
        if not flow_file.exists():
            flow_file = self.flows_config / f"{flow_id}.yaml"

        self._save_yaml(flow_file, updated_data)

        # Update cache
        new_etag = self._compute_etag(updated_data)
        self._flow_cache[flow_id] = (updated_data, new_etag)

        return updated_data, new_etag

    def validate_flow(self, flow_data: Dict[str, Any]) -> List[str]:
        """Validate a flow graph against the schema.

        Args:
            flow_data: Flow graph data to validate.

        Returns:
            List of validation error messages (empty if valid).
        """
        errors = []

        # Required fields
        required = ["id", "version", "title"]
        for field in required:
            if field not in flow_data:
                errors.append(f"Missing required field: {field}")

        # Validate nodes
        nodes = flow_data.get("nodes", [])
        node_ids = set()
        for node in nodes:
            node_id = node.get("node_id")
            if not node_id:
                errors.append("Node missing node_id")
            elif node_id in node_ids:
                errors.append(f"Duplicate node_id: {node_id}")
            else:
                node_ids.add(node_id)

            if not node.get("template_id"):
                errors.append(f"Node {node_id} missing template_id")

        # Validate edges
        edges = flow_data.get("edges", [])
        for edge in edges:
            edge_id = edge.get("edge_id")
            from_node = edge.get("from")
            to_node = edge.get("to")

            if not edge_id:
                errors.append("Edge missing edge_id")
            if from_node and from_node not in node_ids:
                errors.append(f"Edge {edge_id} references unknown from node: {from_node}")
            if to_node and to_node not in node_ids:
                errors.append(f"Edge {edge_id} references unknown to node: {to_node}")

        return errors

    # -------------------------------------------------------------------------
    # Template Operations
    # -------------------------------------------------------------------------

    def list_templates(self) -> List[Dict[str, Any]]:
        """List all available step templates.

        Returns:
            List of template summaries.
        """
        templates = []

        templates_dir = self.spec_root / "templates"
        if templates_dir.exists():
            for yaml_file in templates_dir.glob("*.yaml"):
                try:
                    template_data = self._load_yaml(yaml_file)
                    templates.append(
                        {
                            "id": template_data.get("id", yaml_file.stem),
                            "title": template_data.get("title", yaml_file.stem),
                            "station_id": template_data.get("station_id"),
                            "category": template_data.get("category"),
                            "tags": template_data.get("tags", []),
                            "description": template_data.get("description", ""),
                        }
                    )
                except Exception as e:
                    logger.warning("Failed to load template %s: %s", yaml_file, e)

        # Also load station specs as implicit templates
        stations_dir = self.spec_root / "stations"
        if stations_dir.exists():
            for yaml_file in stations_dir.glob("*.yaml"):
                station_id = yaml_file.stem
                # Skip if already have explicit template
                if any(t["id"] == station_id for t in templates):
                    continue
                try:
                    station_data = self._load_yaml(yaml_file)
                    templates.append(
                        {
                            "id": station_id,
                            "title": station_data.get("title", station_id),
                            "station_id": station_id,
                            "category": station_data.get("category", "custom"),
                            "tags": [],
                            "description": station_data.get("description", ""),
                        }
                    )
                except Exception as e:
                    logger.warning("Failed to load station %s: %s", yaml_file, e)

        return templates

    def get_template(self, template_id: str) -> Tuple[Dict[str, Any], str]:
        """Get a template by ID.

        Args:
            template_id: Template identifier.

        Returns:
            Tuple of (template_data, etag).

        Raises:
            FileNotFoundError: If template not found.
        """
        if template_id in self._template_cache:
            return self._template_cache[template_id]

        # Try templates first
        template_file = self.spec_root / "templates" / f"{template_id}.yaml"
        if not template_file.exists():
            # Try stations
            template_file = self.spec_root / "stations" / f"{template_id}.yaml"

        if not template_file.exists():
            raise FileNotFoundError(f"Template '{template_id}' not found")

        template_data = self._load_yaml(template_file)
        etag = self._compute_etag(template_data)

        self._template_cache[template_id] = (template_data, etag)
        return template_data, etag

    # -------------------------------------------------------------------------
    # Compilation
    # -------------------------------------------------------------------------

    def compile_prompt_plan(
        self,
        flow_id: str,
        step_id: str,
        run_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Compile a PromptPlan for a flow step.

        Args:
            flow_id: Flow identifier.
            step_id: Step identifier within the flow.
            run_id: Optional run ID for context.

        Returns:
            Compiled PromptPlan dictionary.
        """
        try:
            from swarm.spec.compiler import compile_prompt

            run_base = self.runs_root / (run_id or "preview")

            plan = compile_prompt(
                flow_id=flow_id,
                step_id=step_id,
                context_pack=None,
                run_base=run_base,
                repo_root=self.repo_root,
            )

            # Convert to dict
            return {
                "station_id": plan.station_id,
                "station_version": plan.station_version,
                "flow_id": plan.flow_id,
                "flow_version": plan.flow_version,
                "step_id": plan.step_id,
                "prompt_hash": plan.prompt_hash,
                "model": plan.model,
                "permission_mode": plan.permission_mode,
                "allowed_tools": list(plan.allowed_tools),
                "max_turns": plan.max_turns,
                "sandbox_enabled": plan.sandbox_enabled,
                "cwd": plan.cwd,
                "system_append": plan.system_append[:500] + "..."
                if len(plan.system_append) > 500
                else plan.system_append,
                "user_prompt": plan.user_prompt[:500] + "..."
                if len(plan.user_prompt) > 500
                else plan.user_prompt,
                "compiled_at": plan.compiled_at,
            }
        except ImportError:
            logger.warning("SpecCompiler not available, returning mock data")
            return {
                "station_id": "mock-station",
                "flow_id": flow_id,
                "step_id": step_id,
                "prompt_hash": "mock-hash",
                "compiled_at": datetime.now(timezone.utc).isoformat(),
            }
        except Exception as e:
            logger.error("Failed to compile prompt plan: %s", e)
            raise

    # -------------------------------------------------------------------------
    # Run State Operations
    # -------------------------------------------------------------------------

    def get_run_state(self, run_id: str) -> Tuple[Dict[str, Any], str]:
        """Get the state of a run.

        Args:
            run_id: Run identifier.

        Returns:
            Tuple of (run_state, etag).

        Raises:
            FileNotFoundError: If run not found.
        """
        if run_id in self._run_state_cache:
            return self._run_state_cache[run_id]

        run_dir = self.runs_root / run_id
        state_file = run_dir / "run_state.json"

        if not state_file.exists():
            raise FileNotFoundError(f"Run '{run_id}' not found")

        state_data = json.loads(state_file.read_text(encoding="utf-8"))
        etag = self._compute_etag(state_data)

        self._run_state_cache[run_id] = (state_data, etag)
        return state_data, etag

    def list_runs(self, limit: int = 20) -> List[Dict[str, Any]]:
        """List recent runs.

        Args:
            limit: Maximum number of runs to return.

        Returns:
            List of run summaries, most recent first.
        """
        runs = []

        if not self.runs_root.exists():
            return runs

        for run_dir in sorted(self.runs_root.iterdir(), reverse=True):
            if not run_dir.is_dir():
                continue

            state_file = run_dir / "run_state.json"
            if state_file.exists():
                try:
                    state = json.loads(state_file.read_text(encoding="utf-8"))
                    runs.append(
                        {
                            "run_id": state.get("run_id", run_dir.name),
                            "flow_key": state.get("flow_key"),
                            "status": state.get("status"),
                            "timestamp": state.get("timestamp"),
                        }
                    )
                except Exception as e:
                    logger.warning("Failed to load run state %s: %s", run_dir, e)

            if len(runs) >= limit:
                break

        return runs

    # -------------------------------------------------------------------------
    # SSE Event Stream
    # -------------------------------------------------------------------------

    async def stream_run_events(self, run_id: str) -> AsyncGenerator[str, None]:
        """Stream Server-Sent Events for a run.

        Args:
            run_id: Run identifier.

        Yields:
            SSE formatted event strings.
        """
        run_dir = self.runs_root / run_id
        events_file = run_dir / "events.jsonl"

        # Send initial connection event
        yield f"data: {json.dumps({'event': 'connected', 'run_id': run_id})}\n\n"

        # Track file position for incremental reading
        last_position = 0

        while True:
            try:
                state, _ = self.get_run_state(run_id)
                status = state.get("status", "pending")

                # Read new events from file
                if events_file.exists():
                    with open(events_file, "r", encoding="utf-8") as f:
                        f.seek(last_position)
                        for line in f:
                            if line.strip():
                                yield f"data: {line.strip()}\n\n"
                        last_position = f.tell()

                # Send heartbeat with current state
                yield f"data: {json.dumps({'event': 'heartbeat', 'status': status, 'timestamp': datetime.now(timezone.utc).isoformat()})}\n\n"

                # Stop streaming if run is complete
                if status in ("succeeded", "failed", "canceled"):
                    yield f"data: {json.dumps({'event': 'complete', 'status': status})}\n\n"
                    break

                await asyncio.sleep(1)  # Poll interval

            except FileNotFoundError:
                yield f"data: {json.dumps({'event': 'error', 'message': 'Run not found'})}\n\n"
                break
            except Exception as e:
                yield f"data: {json.dumps({'event': 'error', 'message': str(e)})}\n\n"
                await asyncio.sleep(5)  # Back off on error

    # -------------------------------------------------------------------------
    # YAML Helpers
    # -------------------------------------------------------------------------

    def _load_yaml(self, path: Path) -> Dict[str, Any]:
        """Load a YAML file.

        Args:
            path: Path to YAML file.

        Returns:
            Parsed YAML data.
        """
        import yaml

        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}

    def _save_yaml(self, path: Path, data: Dict[str, Any]) -> None:
        """Save data to a YAML file.

        Args:
            path: Path to YAML file.
            data: Data to save.
        """
        import yaml

        with open(path, "w", encoding="utf-8") as f:
            yaml.safe_dump(data, f, default_flow_style=False, sort_keys=False)

    # -------------------------------------------------------------------------
    # JSON Patch Helpers
    # -------------------------------------------------------------------------

    def _set_nested(self, data: Dict, path: List[str], value: Any) -> None:
        """Set a nested value in a dictionary."""
        for key in path[:-1]:
            if key.isdigit():
                data = data[int(key)]
            else:
                data = data.setdefault(key, {})

        final_key = path[-1]
        if final_key.isdigit():
            data[int(final_key)] = value
        else:
            data[final_key] = value

    def _add_nested(self, data: Dict, path: List[str], value: Any) -> None:
        """Add a value at a nested path."""
        for key in path[:-1]:
            if key.isdigit():
                data = data[int(key)]
            else:
                data = data.setdefault(key, {})

        final_key = path[-1]
        if final_key == "-":
            # Append to array
            data.append(value)
        elif final_key.isdigit():
            data.insert(int(final_key), value)
        else:
            data[final_key] = value

    def _remove_nested(self, data: Dict, path: List[str]) -> None:
        """Remove a value at a nested path."""
        for key in path[:-1]:
            if key.isdigit():
                data = data[int(key)]
            else:
                data = data[key]

        final_key = path[-1]
        if final_key.isdigit():
            del data[int(final_key)]
        else:
            del data[final_key]


# =============================================================================
# Global SpecManager instance
# =============================================================================

_spec_manager: Optional[SpecManager] = None


def get_spec_manager() -> SpecManager:
    """Get the global SpecManager instance.

    Raises:
        RuntimeError: If set_spec_manager() was never called.
    """
    if _spec_manager is None:
        raise RuntimeError(
            "SpecManager not initialized. Call set_spec_manager() first, "
            "or use create_app() which handles initialization."
        )
    return _spec_manager


def set_spec_manager(manager: SpecManager) -> None:
    """Set the global SpecManager instance.

    Used by create_app() to inject a configured instance.
    """
    global _spec_manager
    _spec_manager = manager


def clear_spec_manager() -> None:
    """Clear the global SpecManager instance.

    Intended for tests only - allows resetting singleton state between tests.
    """
    global _spec_manager
    _spec_manager = None
