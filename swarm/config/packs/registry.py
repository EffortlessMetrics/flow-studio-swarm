"""Registry for station and flow pack content."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Set

from swarm.utils.yaml_utils import load_yaml

if TYPE_CHECKING:
    from swarm.runtime.station_library import StationLibrary

logger = logging.getLogger(__name__)


@dataclass
class StationSpec:
    """Specification for a station/template."""

    station_id: str
    name: str
    description: str = ""
    category: str = "general"
    agent_key: Optional[str] = None
    template_id: Optional[str] = None
    params_schema: Dict[str, Any] = field(default_factory=dict)
    default_params: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    pack_origin: str = "default"


def station_spec_to_dict(spec: StationSpec) -> Dict[str, Any]:
    """Convert StationSpec to dictionary."""
    return {
        "station_id": spec.station_id,
        "name": spec.name,
        "description": spec.description,
        "category": spec.category,
        "agent_key": spec.agent_key,
        "template_id": spec.template_id,
        "params_schema": spec.params_schema,
        "default_params": spec.default_params,
        "tags": list(spec.tags),
        "pack_origin": spec.pack_origin,
    }


def station_spec_from_dict(data: Dict[str, Any]) -> StationSpec:
    """Parse StationSpec from dictionary."""
    return StationSpec(
        station_id=data.get("station_id", ""),
        name=data.get("name", data.get("station_id", "")),
        description=data.get("description", ""),
        category=data.get("category", "general"),
        agent_key=data.get("agent_key"),
        template_id=data.get("template_id"),
        params_schema=data.get("params_schema", {}),
        default_params=data.get("default_params", {}),
        tags=list(data.get("tags", [])),
        pack_origin=data.get("pack_origin", "default"),
    )


@dataclass
class FlowNode:
    """A node in a flow specification."""

    node_id: str
    template_id: str
    params: Dict[str, Any] = field(default_factory=dict)
    overrides: Dict[str, Any] = field(default_factory=dict)


@dataclass
class FlowEdge:
    """An edge in a flow specification."""

    edge_id: str
    from_node: str
    to_node: str
    edge_type: str = "sequence"
    priority: int = 50
    condition: Optional[Dict[str, Any]] = None


@dataclass
class FlowPolicy:
    """Policy configuration for a flow."""

    max_loop_iterations: int = 50
    suggested_sidequests: List[str] = field(default_factory=list)


@dataclass
class FlowSpecData:
    """Complete flow specification from pack."""

    id: str
    name: str
    description: str = ""
    version: int = 1
    nodes: List[FlowNode] = field(default_factory=list)
    edges: List[FlowEdge] = field(default_factory=list)
    policy: FlowPolicy = field(default_factory=FlowPolicy)
    pack_origin: str = "default"


def flow_node_from_dict(data: Dict[str, Any]) -> FlowNode:
    """Parse FlowNode from dictionary."""
    return FlowNode(
        node_id=data.get("node_id", ""),
        template_id=data.get("template_id", ""),
        params=data.get("params", {}),
        overrides=data.get("overrides", {}),
    )


def flow_edge_from_dict(data: Dict[str, Any]) -> FlowEdge:
    """Parse FlowEdge from dictionary."""
    return FlowEdge(
        edge_id=data.get("edge_id", ""),
        from_node=data.get("from", ""),
        to_node=data.get("to", ""),
        edge_type=data.get("type", "sequence"),
        priority=data.get("priority", 50),
        condition=data.get("condition"),
    )


def flow_spec_from_dict(data: Dict[str, Any], pack_origin: str = "default") -> FlowSpecData:
    """Parse FlowSpecData from dictionary."""
    nodes = [flow_node_from_dict(n) for n in data.get("nodes", [])]
    edges = [flow_edge_from_dict(e) for e in data.get("edges", [])]

    policy_data = data.get("policy", {})
    policy = FlowPolicy(
        max_loop_iterations=policy_data.get("max_loop_iterations", 50),
        suggested_sidequests=policy_data.get("suggested_sidequests", []),
    )

    return FlowSpecData(
        id=data.get("id", ""),
        name=data.get("name", data.get("id", "")),
        description=data.get("description", ""),
        version=data.get("version", 1),
        nodes=nodes,
        edges=edges,
        policy=policy,
        pack_origin=pack_origin,
    )


def flow_spec_to_dict(spec: FlowSpecData) -> Dict[str, Any]:
    """Convert FlowSpecData to dictionary."""
    return {
        "id": spec.id,
        "name": spec.name,
        "description": spec.description,
        "version": spec.version,
        "nodes": [
            {
                "node_id": n.node_id,
                "template_id": n.template_id,
                "params": n.params,
                "overrides": n.overrides,
            }
            for n in spec.nodes
        ],
        "edges": [
            {
                "edge_id": e.edge_id,
                "from": e.from_node,
                "to": e.to_node,
                "type": e.edge_type,
                "priority": e.priority,
                "condition": e.condition,
            }
            for e in spec.edges
        ],
        "policy": {
            "max_loop_iterations": spec.policy.max_loop_iterations,
            "suggested_sidequests": spec.policy.suggested_sidequests,
        },
        "pack_origin": spec.pack_origin,
    }


class PackRegistry:
    """Registry for loading and managing packs."""

    def __init__(self, repo_root: Optional[Path] = None):
        """Initialize the pack registry."""
        self._repo_root = repo_root
        self._stations: Dict[str, StationSpec] = {}
        self._flows: Dict[str, FlowSpecData] = {}
        self._by_category: Dict[str, List[str]] = {}
        self._by_tag: Dict[str, Set[str]] = {}
        self._loaded = False
        self._station_library: Optional["StationLibrary"] = None

    def load(self) -> None:
        """Load all pack contents."""
        if self._loaded:
            return

        self._load_stations()
        self._load_flows()
        self._loaded = True

    def _get_packs_dir(self) -> Path:
        """Get the packs directory path."""
        if self._repo_root:
            return self._repo_root / "swarm" / "packs"
        return Path(__file__).resolve().parents[2] / "packs"

    def _load_stations(self) -> int:
        """Load station specs from pack directories."""
        count = 0
        packs_dir = self._get_packs_dir()
        stations_dir = packs_dir / "stations"

        if not stations_dir.exists():
            logger.debug("Stations directory not found: %s", stations_dir)
            return count

        for yaml_file in stations_dir.glob("*.yaml"):
            try:
                with open(yaml_file, "r", encoding="utf-8") as f:
                    data = load_yaml(f)

                if isinstance(data, list):
                    for item in data:
                        spec = station_spec_from_dict(item)
                        spec.pack_origin = f"pack:{yaml_file.stem}"
                        self._register_station(spec)
                        count += 1
                elif isinstance(data, dict):
                    spec = station_spec_from_dict(data)
                    spec.pack_origin = f"pack:{yaml_file.stem}"
                    self._register_station(spec)
                    count += 1
            except Exception as e:
                logger.warning("Failed to load station from %s: %s", yaml_file, e)

        for json_file in stations_dir.glob("*.json"):
            try:
                with open(json_file, "r", encoding="utf-8") as f:
                    data = json.load(f)

                if isinstance(data, list):
                    for item in data:
                        spec = station_spec_from_dict(item)
                        spec.pack_origin = f"pack:{json_file.stem}"
                        self._register_station(spec)
                        count += 1
                elif isinstance(data, dict):
                    spec = station_spec_from_dict(data)
                    spec.pack_origin = f"pack:{json_file.stem}"
                    self._register_station(spec)
                    count += 1
            except Exception as e:
                logger.warning("Failed to load station from %s: %s", json_file, e)

        if count > 0:
            logger.info("Loaded %d stations from pack", count)

        return count

    def _load_flows(self) -> int:
        """Load flow specs from pack directories."""
        count = 0
        packs_dir = self._get_packs_dir()
        flows_dir = packs_dir / "flows"

        if not flows_dir.exists():
            logger.debug("Flows directory not found: %s", flows_dir)
            return count

        for json_file in flows_dir.glob("*.json"):
            try:
                with open(json_file, "r", encoding="utf-8") as f:
                    data = json.load(f)

                spec = flow_spec_from_dict(data, pack_origin=f"pack:{json_file.stem}")
                self._flows[spec.id] = spec
                count += 1
            except Exception as e:
                logger.warning("Failed to load flow from %s: %s", json_file, e)

        for yaml_file in flows_dir.glob("*.yaml"):
            try:
                with open(yaml_file, "r", encoding="utf-8") as f:
                    data = load_yaml(f)

                if data:
                    spec = flow_spec_from_dict(data, pack_origin=f"pack:{yaml_file.stem}")
                    self._flows[spec.id] = spec
                    count += 1
            except Exception as e:
                logger.warning("Failed to load flow from %s: %s", yaml_file, e)

        if count > 0:
            logger.info("Loaded %d flows from pack", count)

        return count

    def _register_station(self, spec: StationSpec) -> None:
        """Register a station in the registry."""
        self._stations[spec.station_id] = spec

        if spec.category not in self._by_category:
            self._by_category[spec.category] = []
        if spec.station_id not in self._by_category[spec.category]:
            self._by_category[spec.category].append(spec.station_id)

        for tag in spec.tags:
            if tag not in self._by_tag:
                self._by_tag[tag] = set()
            self._by_tag[tag].add(spec.station_id)

    def has_station(self, station_id: str) -> bool:
        """Check if a station exists in the registry."""
        self.load()
        return station_id in self._stations

    def get_station(self, station_id: str) -> Optional[StationSpec]:
        """Get a station specification."""
        self.load()
        return self._stations.get(station_id)

    def get_stations_by_category(self, category: str) -> List[StationSpec]:
        """Get all stations in a category."""
        self.load()
        station_ids = self._by_category.get(category, [])
        return [self._stations[sid] for sid in station_ids if sid in self._stations]

    def get_stations_by_tag(self, tag: str) -> List[StationSpec]:
        """Get all stations with a tag."""
        self.load()
        station_ids = self._by_tag.get(tag, set())
        return [self._stations[sid] for sid in station_ids if sid in self._stations]

    def get_all_stations(self) -> List[StationSpec]:
        """Get all stations in the registry."""
        self.load()
        return list(self._stations.values())

    def list_station_ids(self) -> List[str]:
        """Get all station IDs."""
        self.load()
        return list(self._stations.keys())

    def list_categories(self) -> List[str]:
        """Get all station categories."""
        self.load()
        return list(self._by_category.keys())

    def list_tags(self) -> List[str]:
        """Get all station tags."""
        self.load()
        return list(self._by_tag.keys())

    def has_flow(self, flow_id: str) -> bool:
        """Check if a flow exists in the registry."""
        self.load()
        return flow_id in self._flows

    def get_flow(self, flow_id: str) -> Optional[FlowSpecData]:
        """Get a flow specification."""
        self.load()
        return self._flows.get(flow_id)

    def get_all_flows(self) -> List[FlowSpecData]:
        """Get all flows in the registry."""
        self.load()
        return list(self._flows.values())

    def list_flow_ids(self) -> List[str]:
        """Get all flow IDs."""
        self.load()
        return list(self._flows.keys())

    def get_station_library(self) -> "StationLibrary":
        """Get a StationLibrary instance populated from this registry."""
        if self._station_library is not None:
            return self._station_library

        from swarm.runtime.station_library import StationLibrary
        from swarm.runtime.station_library import StationSpec as LibraryStationSpec

        self.load()

        library = StationLibrary()

        for spec in self._stations.values():
            lib_spec = LibraryStationSpec(
                station_id=spec.station_id,
                name=spec.name,
                description=spec.description,
                category=spec.category,
                agent_key=spec.agent_key,
                template_id=spec.template_id,
                params_schema=spec.params_schema,
                default_params=spec.default_params,
                tags=list(spec.tags),
                pack_origin=spec.pack_origin,
            )
            library._register_station(lib_spec)

        self._station_library = library
        return library

    def to_dict(self) -> Dict[str, Any]:
        """Serialize registry state."""
        self.load()
        return {
            "stations": {sid: station_spec_to_dict(spec) for sid, spec in self._stations.items()},
            "flows": {fid: flow_spec_to_dict(spec) for fid, spec in self._flows.items()},
            "categories": dict(self._by_category),
            "tags": {tag: list(ids) for tag, ids in self._by_tag.items()},
        }


def load_pack_registry(repo_root: Optional[Path] = None) -> PackRegistry:
    """Load a pack registry with all pack contents."""
    registry = PackRegistry(repo_root=repo_root)
    registry.load()
    return registry
