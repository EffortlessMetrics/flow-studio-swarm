"""
station_library.py - Registry of available stations and templates.

This module provides a StationLibrary that aggregates stations from:
1. Default pack (built-in stations shipped with the system)
2. Repo pack (custom stations defined in the repository)
3. Installed packs (optional external packs)

The library is used by:
- EXTEND_GRAPH validation: ensure proposed targets exist
- Node resolution: get execution specs for stations
- UI: display available stations for flow editing

Usage:
    from swarm.runtime.station_library import StationLibrary, load_station_library

    # Load library from repo
    library = load_station_library(repo_root)

    # Validate a station exists
    if library.has_station("clarifier"):
        spec = library.get_station("clarifier")

    # Get all stations for a category
    sidequests = library.get_stations_by_category("sidequest")
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

import yaml

logger = logging.getLogger(__name__)


@dataclass
class StationSpec:
    """Specification for a station/template.

    Attributes:
        station_id: Unique identifier for this station.
        name: Human-readable name.
        description: What this station does.
        category: Category (sidequest, worker, critic, etc.).
        agent_key: Default agent to execute.
        template_id: Template identifier if different from station_id.
        params_schema: JSON Schema for parameters (optional).
        default_params: Default parameter values.
        tags: Tags for filtering/search.
        pack_origin: Which pack this station came from.
    """
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


# =============================================================================
# Default Pack Stations
# =============================================================================

# These are the built-in stations that ship with the system.
# They provide core sidequest and utility functionality.

DEFAULT_STATIONS: List[Dict[str, Any]] = [
    {
        "station_id": "clarifier",
        "name": "Clarifier",
        "description": "Resolve ambiguity by researching context and documenting assumptions",
        "category": "sidequest",
        "agent_key": "clarifier",
        "tags": ["sidequest", "research", "assumptions"],
    },
    {
        "station_id": "research",
        "name": "Research",
        "description": "Deep dive into codebase or documentation to gather context",
        "category": "sidequest",
        "agent_key": "context-loader",
        "tags": ["sidequest", "research", "context"],
    },
    {
        "station_id": "risk-assessment",
        "name": "Risk Assessment",
        "description": "Evaluate risks in current approach and document mitigations",
        "category": "sidequest",
        "agent_key": "risk-analyst",
        "tags": ["sidequest", "risk", "analysis"],
    },
    {
        "station_id": "policy-check",
        "name": "Policy Check",
        "description": "Verify current work against organizational policies",
        "category": "sidequest",
        "agent_key": "policy-analyst",
        "tags": ["sidequest", "policy", "compliance"],
    },
    {
        "station_id": "security-review",
        "name": "Security Review",
        "description": "Quick security assessment of changes",
        "category": "sidequest",
        "agent_key": "security-scanner",
        "tags": ["sidequest", "security", "review"],
    },
    # Core worker stations (for EXTEND_GRAPH targets)
    {
        "station_id": "code-implementer",
        "name": "Code Implementer",
        "description": "Implement code changes based on specifications",
        "category": "worker",
        "agent_key": "code-implementer",
        "tags": ["worker", "implementation", "code"],
    },
    {
        "station_id": "test-author",
        "name": "Test Author",
        "description": "Write tests based on specifications",
        "category": "worker",
        "agent_key": "test-author",
        "tags": ["worker", "testing", "code"],
    },
    {
        "station_id": "code-critic",
        "name": "Code Critic",
        "description": "Review code implementation for issues",
        "category": "critic",
        "agent_key": "code-critic",
        "tags": ["critic", "review", "code"],
    },
    {
        "station_id": "test-critic",
        "name": "Test Critic",
        "description": "Review test implementation for coverage and quality",
        "category": "critic",
        "agent_key": "test-critic",
        "tags": ["critic", "review", "testing"],
    },
]


class StationLibrary:
    """Registry of available stations and templates.

    The library aggregates stations from multiple sources:
    1. Default pack (built-in)
    2. Repo pack (swarm/packs/ or swarm/specs/stations/)
    3. Installed packs (optional)

    Usage:
        library = StationLibrary()
        library.load_default_pack()
        library.load_repo_pack(repo_root)

        if library.has_station("clarifier"):
            spec = library.get_station("clarifier")
    """

    def __init__(self):
        """Initialize an empty station library."""
        self._stations: Dict[str, StationSpec] = {}
        self._by_category: Dict[str, List[str]] = {}
        self._by_tag: Dict[str, Set[str]] = {}

    def load_default_pack(self) -> int:
        """Load built-in default stations.

        Returns:
            Number of stations loaded.
        """
        count = 0
        for station_data in DEFAULT_STATIONS:
            spec = station_spec_from_dict(station_data)
            spec.pack_origin = "default"
            self._register_station(spec)
            count += 1

        logger.info("Loaded %d default stations", count)
        return count

    def load_repo_pack(self, repo_root: Path) -> int:
        """Load stations from repository pack.

        Looks for stations in:
        - swarm/packs/stations/*.yaml
        - swarm/packs/stations/*.json
        - swarm/specs/stations/*.yaml (legacy)

        Args:
            repo_root: Repository root path.

        Returns:
            Number of stations loaded.
        """
        count = 0

        # Try multiple locations
        pack_dirs = [
            repo_root / "swarm" / "packs" / "stations",
            repo_root / "swarm" / "specs" / "stations",
        ]

        for pack_dir in pack_dirs:
            if not pack_dir.exists():
                continue

            # Load YAML files
            for yaml_file in pack_dir.glob("*.yaml"):
                try:
                    with open(yaml_file, "r") as f:
                        data = yaml.safe_load(f)

                    if isinstance(data, list):
                        for item in data:
                            spec = station_spec_from_dict(item)
                            spec.pack_origin = f"repo:{pack_dir.name}"
                            self._register_station(spec)
                            count += 1
                    elif isinstance(data, dict):
                        spec = station_spec_from_dict(data)
                        spec.pack_origin = f"repo:{pack_dir.name}"
                        self._register_station(spec)
                        count += 1
                except Exception as e:
                    logger.warning("Failed to load station from %s: %s", yaml_file, e)

            # Load JSON files
            for json_file in pack_dir.glob("*.json"):
                try:
                    with open(json_file, "r") as f:
                        data = json.load(f)

                    if isinstance(data, list):
                        for item in data:
                            spec = station_spec_from_dict(item)
                            spec.pack_origin = f"repo:{pack_dir.name}"
                            self._register_station(spec)
                            count += 1
                    elif isinstance(data, dict):
                        spec = station_spec_from_dict(data)
                        spec.pack_origin = f"repo:{pack_dir.name}"
                        self._register_station(spec)
                        count += 1
                except Exception as e:
                    logger.warning("Failed to load station from %s: %s", json_file, e)

        if count > 0:
            logger.info("Loaded %d repo stations", count)

        return count

    def _register_station(self, spec: StationSpec) -> None:
        """Register a station in the library.

        Args:
            spec: Station specification to register.
        """
        self._stations[spec.station_id] = spec

        # Index by category
        if spec.category not in self._by_category:
            self._by_category[spec.category] = []
        if spec.station_id not in self._by_category[spec.category]:
            self._by_category[spec.category].append(spec.station_id)

        # Index by tags
        for tag in spec.tags:
            if tag not in self._by_tag:
                self._by_tag[tag] = set()
            self._by_tag[tag].add(spec.station_id)

    def has_station(self, station_id: str) -> bool:
        """Check if a station exists in the library.

        Args:
            station_id: Station ID to check.

        Returns:
            True if station exists.
        """
        return station_id in self._stations

    def get_station(self, station_id: str) -> Optional[StationSpec]:
        """Get a station specification.

        Args:
            station_id: Station ID to retrieve.

        Returns:
            StationSpec if found, None otherwise.
        """
        return self._stations.get(station_id)

    def get_stations_by_category(self, category: str) -> List[StationSpec]:
        """Get all stations in a category.

        Args:
            category: Category to filter by.

        Returns:
            List of station specs in that category.
        """
        station_ids = self._by_category.get(category, [])
        return [self._stations[sid] for sid in station_ids if sid in self._stations]

    def get_stations_by_tag(self, tag: str) -> List[StationSpec]:
        """Get all stations with a tag.

        Args:
            tag: Tag to filter by.

        Returns:
            List of station specs with that tag.
        """
        station_ids = self._by_tag.get(tag, set())
        return [self._stations[sid] for sid in station_ids if sid in self._stations]

    def list_all_stations(self) -> List[StationSpec]:
        """Get all stations in the library.

        Returns:
            List of all station specs.
        """
        return list(self._stations.values())

    def list_station_ids(self) -> List[str]:
        """Get all station IDs.

        Returns:
            List of station IDs.
        """
        return list(self._stations.keys())

    def validate_target(self, target_id: str) -> bool:
        """Validate that a target exists for EXTEND_GRAPH.

        This is the primary validation method used by Navigator
        when evaluating EXTEND_GRAPH proposals.

        Args:
            target_id: The proposed target station/template ID.

        Returns:
            True if the target is valid and can be executed.
        """
        return self.has_station(target_id)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize library state.

        Returns:
            Dictionary representation of the library.
        """
        return {
            "stations": {
                sid: station_spec_to_dict(spec)
                for sid, spec in self._stations.items()
            },
            "categories": dict(self._by_category),
            "tags": {tag: list(ids) for tag, ids in self._by_tag.items()},
        }


def load_station_library(repo_root: Optional[Path] = None) -> StationLibrary:
    """Load a station library with default and repo packs.

    This is the standard way to create a StationLibrary for use
    in the runtime.

    Args:
        repo_root: Optional repository root. If None, only loads defaults.

    Returns:
        Configured StationLibrary instance.
    """
    library = StationLibrary()
    library.load_default_pack()

    if repo_root:
        library.load_repo_pack(repo_root)

    return library


__all__ = [
    "StationSpec",
    "StationLibrary",
    "load_station_library",
    "station_spec_to_dict",
    "station_spec_from_dict",
]
