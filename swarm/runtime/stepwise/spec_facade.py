"""
spec_facade.py - Cached access to FlowSpec and StationSpec.

This module provides a facade for loading and caching spec-first types:
- FlowSpec: Flow definition from swarm/spec/flows/
- StationSpec: Station definition from swarm/spec/stations/

The facade abstracts away the file I/O and caching, making specs available
to routing, verification, and orchestration without repeated loading.

Future: When Graph IR becomes authoritative, this facade can be extended
with a GraphSpecFacade implementation that reads from JSON specs instead.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from swarm.config.flow_registry import get_flow_spec_id
from swarm.runtime.router import FlowGraph, Edge, NodeConfig, EdgeCondition

# Conditional imports for spec module (may not be available in all environments)
try:
    from swarm.spec.loader import load_flow, load_station
    from swarm.spec.types import FlowSpec, RoutingKind, StationSpec

    SPEC_AVAILABLE = True
except ImportError:
    SPEC_AVAILABLE = False
    FlowSpec = None  # type: ignore
    RoutingKind = None  # type: ignore
    StationSpec = None  # type: ignore

    def load_flow(flow_id: str, repo_root: Path) -> Any:
        raise ImportError("swarm.spec module not available")

    def load_station(station_id: str, repo_root: Path) -> Any:
        raise ImportError("swarm.spec module not available")


logger = logging.getLogger(__name__)


class SpecFacade:
    """Facade for loading and caching FlowSpec and StationSpec.

    Provides thread-safe caching of specs to avoid repeated file I/O.
    Returns None for missing specs rather than raising exceptions.

    Attributes:
        repo_root: Repository root path.
    """

    def __init__(self, repo_root: Path):
        """Initialize the facade.

        Args:
            repo_root: Repository root path.
        """
        self._repo_root = repo_root
        self._flow_cache: Dict[str, Any] = {}
        self._station_cache: Dict[str, Any] = {}
        self._flow_graph_cache: Dict[str, Optional[FlowGraph]] = {}

    @property
    def spec_available(self) -> bool:
        """Check if the spec module is available."""
        return SPEC_AVAILABLE

    def load_flow_spec(self, flow_key: str) -> Optional[Any]:
        """Load FlowSpec from swarm/spec/flows/{flow_id}.yaml.

        Uses caching to avoid repeated file I/O.

        Args:
            flow_key: The flow key (e.g., "build", "plan").

        Returns:
            Loaded FlowSpec or None if not available.
        """
        if not SPEC_AVAILABLE:
            logger.debug("Spec module not available, skipping FlowSpec load")
            return None

        if flow_key in self._flow_cache:
            return self._flow_cache[flow_key]

        # Map flow_key to spec flow_id (e.g., "build" -> "3-build")
        flow_id = get_flow_spec_id(flow_key)

        try:
            flow_spec = load_flow(flow_id, self._repo_root)
            self._flow_cache[flow_key] = flow_spec
            logger.debug("Loaded FlowSpec for %s (id=%s)", flow_key, flow_id)
            return flow_spec
        except FileNotFoundError:
            logger.debug("FlowSpec not found for %s", flow_key)
            self._flow_cache[flow_key] = None
            return None
        except Exception as e:
            logger.warning("Failed to load FlowSpec for %s: %s", flow_key, e)
            self._flow_cache[flow_key] = None
            return None

    def load_station_spec(self, station_id: str) -> Optional[Any]:
        """Load StationSpec from swarm/spec/stations/{station_id}.yaml.

        Uses caching to avoid repeated file I/O.

        Args:
            station_id: The station identifier (e.g., "code-implementer").

        Returns:
            Loaded StationSpec or None if not available.
        """
        if not SPEC_AVAILABLE:
            return None

        if station_id in self._station_cache:
            return self._station_cache[station_id]

        try:
            station_spec = load_station(station_id, self._repo_root)
            self._station_cache[station_id] = station_spec
            logger.debug("Loaded StationSpec for %s", station_id)
            return station_spec
        except FileNotFoundError:
            logger.debug("StationSpec not found for %s", station_id)
            self._station_cache[station_id] = None
            return None
        except Exception as e:
            logger.warning("Failed to load StationSpec for %s: %s", station_id, e)
            self._station_cache[station_id] = None
            return None

    def build_flow_graph(self, flow_key: str) -> Optional[FlowGraph]:
        """Build a FlowGraph from FlowSpec for Navigator context.

        The Navigator needs a FlowGraph to extract candidate edges and
        make routing decisions. This method converts FlowSpec step routing
        into graph edges.

        Args:
            flow_key: The flow key to build graph for.

        Returns:
            FlowGraph if spec is available, None otherwise.
        """
        if flow_key in self._flow_graph_cache:
            return self._flow_graph_cache[flow_key]

        flow_spec = self.load_flow_spec(flow_key)
        if flow_spec is None:
            self._flow_graph_cache[flow_key] = None
            return None

        try:
            nodes: Dict[str, NodeConfig] = {}
            edges: List[Edge] = []

            for step in flow_spec.steps:
                # Create node
                nodes[step.id] = NodeConfig(
                    node_id=step.id,
                    template_id=step.station or step.id,
                    max_iterations=getattr(step.routing, "max_iterations", None),
                    exit_on=(
                        {"status": list(step.routing.loop_success_values)}
                        if step.routing.loop_success_values
                        else None
                    ),
                )

                # Create edges from routing
                routing = step.routing
                routing_kind = (
                    routing.kind.value
                    if hasattr(routing.kind, "value")
                    else str(routing.kind)
                )

                # Next edge (linear/terminal/branch default)
                if routing.next:
                    edges.append(
                        Edge(
                            edge_id=f"{step.id}->next",
                            from_node=step.id,
                            to_node=routing.next,
                            edge_type="sequence",
                            priority=50,
                        )
                    )

                # Loop edge (for microloops)
                if routing.loop_target:
                    # Loop edge with exit condition
                    exit_condition = None
                    if routing.loop_success_values:
                        exit_condition = EdgeCondition(
                            field="status",
                            operator="not_in",
                            value=list(routing.loop_success_values),
                        )
                    edges.append(
                        Edge(
                            edge_id=f"{step.id}->loop",
                            from_node=step.id,
                            to_node=routing.loop_target,
                            edge_type="loop",
                            priority=40,  # Lower priority than advance
                            condition=exit_condition,
                        )
                    )

            graph = FlowGraph(
                graph_id=flow_key,
                nodes=nodes,
                edges=edges,
                policy={
                    "max_loop_iterations": 10,  # Default fuse
                },
            )
            self._flow_graph_cache[flow_key] = graph
            return graph

        except Exception as e:
            logger.debug("Failed to build FlowGraph for %s: %s", flow_key, e)
            self._flow_graph_cache[flow_key] = None
            return None

    def clear_cache(self) -> None:
        """Clear all cached specs.

        Useful for testing or when spec files are modified during runtime.
        """
        self._flow_cache.clear()
        self._station_cache.clear()
        self._flow_graph_cache.clear()


# Module-level convenience functions for simple use cases
_default_facade: Optional[SpecFacade] = None


def get_facade(repo_root: Optional[Path] = None) -> SpecFacade:
    """Get or create a module-level SpecFacade.

    Args:
        repo_root: Repository root path. Uses auto-detection if not provided.

    Returns:
        SpecFacade instance.
    """
    global _default_facade
    if _default_facade is None or (repo_root and _default_facade._repo_root != repo_root):
        if repo_root is None:
            repo_root = Path(__file__).resolve().parents[3]
        _default_facade = SpecFacade(repo_root)
    return _default_facade


def load_flow_spec(flow_key: str, repo_root: Optional[Path] = None) -> Optional[Any]:
    """Convenience function to load a FlowSpec."""
    return get_facade(repo_root).load_flow_spec(flow_key)


def load_station_spec(station_id: str, repo_root: Optional[Path] = None) -> Optional[Any]:
    """Convenience function to load a StationSpec."""
    return get_facade(repo_root).load_station_spec(station_id)


__all__ = [
    "SpecFacade",
    "get_facade",
    "load_flow_spec",
    "load_station_spec",
    "SPEC_AVAILABLE",
]
