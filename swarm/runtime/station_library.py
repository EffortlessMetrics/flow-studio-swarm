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
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Set

import yaml

if TYPE_CHECKING:
    from swarm.spec import types as compiler_types

logger = logging.getLogger(__name__)


@dataclass
class StationSpec:
    """Specification for a station/template.

    Attributes:
        station_id: Unique identifier for this station.
        name: Human-readable name.
        description: What this station does.
        category: Category (sidequest, worker, critic, etc.).
        version: Spec version number.

        # Execution config (enriched schema)
        sdk: SDK configuration (model, tools, permissions, etc.).
        identity: Identity configuration (system_append, tone).
        io: Input/output contract (required/optional inputs/outputs).
        handoff: Handoff contract (path_template, required_fields).
        runtime_prompt: Runtime prompt configuration (fragments, template).
        invariants: List of invariant strings.
        routing_hints: Default routing behavior (on_verified, on_unverified, etc.).

        # Existing fields
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
    version: int = 1

    # Execution config (enriched schema)
    sdk: Dict[str, Any] = field(default_factory=dict)
    identity: Dict[str, Any] = field(default_factory=dict)
    io: Dict[str, Any] = field(default_factory=dict)
    handoff: Dict[str, Any] = field(default_factory=dict)
    runtime_prompt: Dict[str, Any] = field(default_factory=dict)
    invariants: List[str] = field(default_factory=list)
    routing_hints: Dict[str, Any] = field(default_factory=dict)

    # Existing fields
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
        "version": spec.version,
        # Enriched schema fields
        "sdk": dict(spec.sdk) if spec.sdk else {},
        "identity": dict(spec.identity) if spec.identity else {},
        "io": dict(spec.io) if spec.io else {},
        "handoff": dict(spec.handoff) if spec.handoff else {},
        "runtime_prompt": dict(spec.runtime_prompt) if spec.runtime_prompt else {},
        "invariants": list(spec.invariants) if spec.invariants else [],
        "routing_hints": dict(spec.routing_hints) if spec.routing_hints else {},
        # Existing fields
        "agent_key": spec.agent_key,
        "template_id": spec.template_id,
        "params_schema": spec.params_schema,
        "default_params": spec.default_params,
        "tags": list(spec.tags),
        "pack_origin": spec.pack_origin,
    }


def station_spec_from_dict(data: Dict[str, Any]) -> StationSpec:
    """Parse StationSpec from dictionary.

    Backward compatible: if new fields are missing, uses sensible defaults.
    """
    return StationSpec(
        station_id=data.get("station_id", data.get("id", "")),
        name=data.get("name", data.get("title", data.get("station_id", data.get("id", "")))),
        description=data.get("description", ""),
        category=data.get("category", "general"),
        version=data.get("version", 1),
        # Enriched schema fields (defaults to empty if not present)
        sdk=dict(data.get("sdk", {})),
        identity=dict(data.get("identity", {})),
        io=dict(data.get("io", {})),
        handoff=dict(data.get("handoff", {})),
        runtime_prompt=dict(data.get("runtime_prompt", {})),
        invariants=list(data.get("invariants", [])),
        routing_hints=dict(data.get("routing_hints", {})),
        # Existing fields
        agent_key=data.get("agent_key"),
        template_id=data.get("template_id"),
        params_schema=data.get("params_schema", {}),
        default_params=data.get("default_params", {}),
        tags=list(data.get("tags", [])),
        pack_origin=data.get("pack_origin", "default"),
    )


def to_compiler_spec(spec: StationSpec) -> "compiler_types.StationSpec":
    """Convert a StationLibrary StationSpec to the compiler's StationSpec.

    This bridges the runtime's StationSpec (used for library management)
    to the compiler's StationSpec (used for prompt compilation and execution).

    Args:
        spec: StationLibrary StationSpec instance.

    Returns:
        Compiler StationSpec instance suitable for prompt compilation.
    """
    from swarm.spec.types import station_spec_from_dict as compiler_from_dict

    return compiler_from_dict({
        "id": spec.station_id,
        "version": spec.version,
        "title": spec.name,
        "category": spec.category,
        "sdk": spec.sdk,
        "identity": spec.identity,
        "io": spec.io,
        "handoff": spec.handoff,
        "runtime_prompt": spec.runtime_prompt,
        "invariants": spec.invariants,
        "routing_hints": spec.routing_hints,
    })


# =============================================================================
# Default Pack Stations
# =============================================================================

# These are the built-in stations that ship with the system.
# They provide core sidequest and utility functionality.

# Default SDK configuration for sidequest stations
_DEFAULT_SDK_SIDEQUEST = {
    "model": "sonnet",
    "permission_mode": "bypassPermissions",
    "allowed_tools": ["Read", "Write", "Edit", "Bash", "Grep", "Glob"],
    "denied_tools": [],
    "max_turns": 8,
    "sandbox": {"enabled": True, "auto_allow_bash": True},
    "context_budget": {"total_chars": 150000, "recent_chars": 50000, "older_chars": 10000},
}

# Default SDK configuration for worker stations
_DEFAULT_SDK_WORKER = {
    "model": "sonnet",
    "permission_mode": "bypassPermissions",
    "allowed_tools": ["Read", "Write", "Edit", "Bash", "Grep", "Glob"],
    "denied_tools": [],
    "max_turns": 12,
    "sandbox": {"enabled": True, "auto_allow_bash": True},
    "context_budget": {"total_chars": 200000, "recent_chars": 60000, "older_chars": 10000},
}

# Default SDK configuration for critic stations
_DEFAULT_SDK_CRITIC = {
    "model": "sonnet",
    "permission_mode": "bypassPermissions",
    "allowed_tools": ["Read", "Grep", "Glob"],
    "denied_tools": ["Write", "Edit", "Bash"],
    "max_turns": 6,
    "sandbox": {"enabled": True, "auto_allow_bash": False},
    "context_budget": {"total_chars": 150000, "recent_chars": 50000, "older_chars": 10000},
}

# Default routing hints
_DEFAULT_ROUTING_HINTS = {
    "on_verified": "advance",
    "on_unverified": "loop",
    "on_partial": "advance_with_concerns",
    "on_blocked": "escalate",
}

# Default handoff configuration
_DEFAULT_HANDOFF = {
    "path_template": "{{run.base}}/handoff/{{step.id}}.draft.json",
    "required_fields": ["status", "summary", "artifacts", "can_further_iteration_help"],
}

DEFAULT_STATIONS: List[Dict[str, Any]] = [
    {
        "station_id": "clarifier",
        "name": "Clarifier",
        "description": "Resolve ambiguity by researching context and documenting assumptions",
        "category": "sidequest",
        "version": 1,
        "agent_key": "clarifier",
        "tags": ["sidequest", "research", "assumptions"],
        "sdk": _DEFAULT_SDK_SIDEQUEST,
        "identity": {
            "system_append": "You are the Clarifier. Your job is to resolve ambiguity by researching the codebase and documenting clear assumptions.",
            "tone": "analytical",
        },
        "io": {
            "required_inputs": [],
            "optional_inputs": ["{{run.base}}/signal/problem_statement.md"],
            "required_outputs": ["{{run.base}}/sidequest/clarifications.md"],
            "optional_outputs": [],
        },
        "handoff": _DEFAULT_HANDOFF,
        "runtime_prompt": {"fragments": [], "template": ""},
        "invariants": ["Document all assumptions explicitly", "Never block on ambiguity"],
        "routing_hints": _DEFAULT_ROUTING_HINTS,
    },
    {
        "station_id": "research",
        "name": "Research",
        "description": "Deep dive into codebase or documentation to gather context",
        "category": "sidequest",
        "version": 1,
        "agent_key": "context-loader",
        "tags": ["sidequest", "research", "context"],
        "sdk": _DEFAULT_SDK_SIDEQUEST,
        "identity": {
            "system_append": "You are the Research station. Your job is to deeply explore the codebase and gather comprehensive context.",
            "tone": "analytical",
        },
        "io": {
            "required_inputs": [],
            "optional_inputs": [],
            "required_outputs": ["{{run.base}}/sidequest/research_findings.md"],
            "optional_outputs": [],
        },
        "handoff": _DEFAULT_HANDOFF,
        "runtime_prompt": {"fragments": [], "template": ""},
        "invariants": ["Load 20-50k tokens of relevant context", "Document sources explicitly"],
        "routing_hints": _DEFAULT_ROUTING_HINTS,
    },
    {
        "station_id": "risk-assessment",
        "name": "Risk Assessment",
        "description": "Evaluate risks in current approach and document mitigations",
        "category": "sidequest",
        "version": 1,
        "agent_key": "risk-analyst",
        "tags": ["sidequest", "risk", "analysis"],
        "sdk": _DEFAULT_SDK_SIDEQUEST,
        "identity": {
            "system_append": "You are the Risk Analyst. Your job is to identify and evaluate risks in the current approach.",
            "tone": "analytical",
        },
        "io": {
            "required_inputs": [],
            "optional_inputs": ["{{run.base}}/plan/adr.md"],
            "required_outputs": ["{{run.base}}/sidequest/risk_assessment.md"],
            "optional_outputs": [],
        },
        "handoff": _DEFAULT_HANDOFF,
        "runtime_prompt": {"fragments": [], "template": ""},
        "invariants": ["Assess security, compliance, data, and performance risks"],
        "routing_hints": _DEFAULT_ROUTING_HINTS,
    },
    {
        "station_id": "policy-check",
        "name": "Policy Check",
        "description": "Verify current work against organizational policies",
        "category": "sidequest",
        "version": 1,
        "agent_key": "policy-analyst",
        "tags": ["sidequest", "policy", "compliance"],
        "sdk": _DEFAULT_SDK_SIDEQUEST,
        "identity": {
            "system_append": "You are the Policy Analyst. Your job is to verify work against organizational policies.",
            "tone": "analytical",
        },
        "io": {
            "required_inputs": [],
            "optional_inputs": ["POLICIES.md"],
            "required_outputs": ["{{run.base}}/sidequest/policy_check.md"],
            "optional_outputs": [],
        },
        "handoff": _DEFAULT_HANDOFF,
        "runtime_prompt": {"fragments": [], "template": ""},
        "invariants": ["Check all applicable policies", "Document any violations"],
        "routing_hints": _DEFAULT_ROUTING_HINTS,
    },
    {
        "station_id": "security-review",
        "name": "Security Review",
        "description": "Quick security assessment of changes",
        "category": "sidequest",
        "version": 1,
        "agent_key": "security-scanner",
        "tags": ["sidequest", "security", "review"],
        "sdk": _DEFAULT_SDK_SIDEQUEST,
        "identity": {
            "system_append": "You are the Security Scanner. Your job is to identify security vulnerabilities in changes.",
            "tone": "critical",
        },
        "io": {
            "required_inputs": [],
            "optional_inputs": [],
            "required_outputs": ["{{run.base}}/sidequest/security_review.md"],
            "optional_outputs": [],
        },
        "handoff": _DEFAULT_HANDOFF,
        "runtime_prompt": {"fragments": [], "template": ""},
        "invariants": ["Check for common vulnerability patterns", "Flag any secrets or credentials"],
        "routing_hints": _DEFAULT_ROUTING_HINTS,
    },
    # Core worker stations (for EXTEND_GRAPH targets)
    {
        "station_id": "code-implementer",
        "name": "Code Implementer",
        "description": "Implement code changes based on specifications",
        "category": "worker",
        "version": 1,
        "agent_key": "code-implementer",
        "tags": ["worker", "implementation", "code"],
        "sdk": _DEFAULT_SDK_WORKER,
        "identity": {
            "system_append": "You are the Code Implementer. Your job is to write production-quality code based on specifications.",
            "tone": "neutral",
        },
        "io": {
            "required_inputs": ["{{run.base}}/plan/work_plan.md"],
            "optional_inputs": ["{{run.base}}/build/test_summary.md"],
            "required_outputs": [],
            "optional_outputs": ["{{run.base}}/build/implementation_notes.md"],
        },
        "handoff": _DEFAULT_HANDOFF,
        "runtime_prompt": {"fragments": [], "template": ""},
        "invariants": ["Follow the work plan", "Write tests alongside code when applicable"],
        "routing_hints": _DEFAULT_ROUTING_HINTS,
    },
    {
        "station_id": "test-author",
        "name": "Test Author",
        "description": "Write tests based on specifications",
        "category": "worker",
        "version": 1,
        "agent_key": "test-author",
        "tags": ["worker", "testing", "code"],
        "sdk": _DEFAULT_SDK_WORKER,
        "identity": {
            "system_append": "You are the Test Author. Your job is to write comprehensive tests based on specifications.",
            "tone": "neutral",
        },
        "io": {
            "required_inputs": ["{{run.base}}/plan/test_plan.md"],
            "optional_inputs": ["{{run.base}}/signal/bdd_scenarios.md"],
            "required_outputs": ["{{run.base}}/build/test_summary.md"],
            "optional_outputs": [],
        },
        "handoff": _DEFAULT_HANDOFF,
        "runtime_prompt": {"fragments": [], "template": ""},
        "invariants": ["Cover all BDD scenarios", "Include edge cases"],
        "routing_hints": _DEFAULT_ROUTING_HINTS,
    },
    {
        "station_id": "code-critic",
        "name": "Code Critic",
        "description": "Review code implementation for issues",
        "category": "critic",
        "version": 1,
        "agent_key": "code-critic",
        "tags": ["critic", "review", "code"],
        "sdk": _DEFAULT_SDK_CRITIC,
        "identity": {
            "system_append": "You are the Code Critic. Your job is to provide harsh, thorough critique of code implementations.",
            "tone": "critical",
        },
        "io": {
            "required_inputs": [],
            "optional_inputs": ["{{run.base}}/plan/adr.md"],
            "required_outputs": ["{{run.base}}/build/code_critique.md"],
            "optional_outputs": [],
        },
        "handoff": _DEFAULT_HANDOFF,
        "runtime_prompt": {"fragments": [], "template": ""},
        "invariants": ["Never fix code yourself", "Provide actionable critique"],
        "routing_hints": {
            "on_verified": "advance",
            "on_unverified": "loop",
            "on_partial": "loop",
            "on_blocked": "escalate",
        },
    },
    {
        "station_id": "test-critic",
        "name": "Test Critic",
        "description": "Review test implementation for coverage and quality",
        "category": "critic",
        "version": 1,
        "agent_key": "test-critic",
        "tags": ["critic", "review", "testing"],
        "sdk": _DEFAULT_SDK_CRITIC,
        "identity": {
            "system_append": "You are the Test Critic. Your job is to critique test coverage and quality.",
            "tone": "critical",
        },
        "io": {
            "required_inputs": ["{{run.base}}/build/test_summary.md"],
            "optional_inputs": ["{{run.base}}/signal/bdd_scenarios.md"],
            "required_outputs": ["{{run.base}}/build/test_critique.md"],
            "optional_outputs": [],
        },
        "handoff": _DEFAULT_HANDOFF,
        "runtime_prompt": {"fragments": [], "template": ""},
        "invariants": ["Never write tests yourself", "Check BDD coverage"],
        "routing_hints": {
            "on_verified": "advance",
            "on_unverified": "loop",
            "on_partial": "loop",
            "on_blocked": "escalate",
        },
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

    def get_compiler_spec(self, station_id: str) -> "compiler_types.StationSpec":
        """Get a station spec in compiler format.

        This converts the runtime StationSpec to the compiler's StationSpec
        type, suitable for prompt compilation and SDK execution.

        Args:
            station_id: Station ID to retrieve.

        Returns:
            Compiler StationSpec instance.

        Raises:
            ValueError: If station not found.
        """
        spec = self.get_station(station_id)
        if not spec:
            raise ValueError(f"Station not found: {station_id}")
        return to_compiler_spec(spec)

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
    "to_compiler_spec",
]
