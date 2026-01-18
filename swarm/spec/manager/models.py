from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ValidationError:
    """Structured validation error."""

    path: str  # JSON path to the error location
    message: str  # Human-readable error message
    schema_path: Optional[str] = None  # Path in schema where validation failed
    value: Optional[Any] = None  # The invalid value

    def __str__(self) -> str:
        if self.path:
            return f"[{self.path}] {self.message}"
        return self.message


@dataclass
class ValidationResult:
    """Result of spec validation."""

    valid: bool
    errors: List[ValidationError] = field(default_factory=list)
    warnings: List[ValidationError] = field(default_factory=list)

    def __bool__(self) -> bool:
        return self.valid


@dataclass
class FlowGraph:
    """Flow graph specification data.

    Corresponds to flow_graph.schema.json.
    """

    id: str
    version: int
    title: str
    flow_number: int
    nodes: List[Dict[str, Any]]
    edges: List[Dict[str, Any]]
    description: str = ""
    policy: Optional[Dict[str, Any]] = None
    subflows: Optional[List[Dict[str, Any]]] = None
    defaults: Optional[Dict[str, Any]] = None
    on_complete: Optional[Dict[str, Any]] = None
    on_failure: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None
    _etag: Optional[str] = None  # Computed ETag for concurrency control

    @classmethod
    def from_dict(cls, data: Dict[str, Any], etag: Optional[str] = None) -> "FlowGraph":
        """Create FlowGraph from dictionary."""
        return cls(
            id=data["id"],
            version=data["version"],
            title=data["title"],
            flow_number=data["flow_number"],
            nodes=data.get("nodes", []),
            edges=data.get("edges", []),
            description=data.get("description", ""),
            policy=data.get("policy"),
            subflows=data.get("subflows"),
            defaults=data.get("defaults"),
            on_complete=data.get("on_complete"),
            on_failure=data.get("on_failure"),
            metadata=data.get("metadata"),
            _etag=etag,
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        result = {
            "id": self.id,
            "version": self.version,
            "title": self.title,
            "flow_number": self.flow_number,
            "nodes": self.nodes,
            "edges": self.edges,
        }
        if self.description:
            result["description"] = self.description
        if self.policy:
            result["policy"] = self.policy
        if self.subflows:
            result["subflows"] = self.subflows
        if self.defaults:
            result["defaults"] = self.defaults
        if self.on_complete:
            result["on_complete"] = self.on_complete
        if self.on_failure:
            result["on_failure"] = self.on_failure
        if self.metadata:
            result["metadata"] = self.metadata
        return result

    @property
    def etag(self) -> Optional[str]:
        """Get the computed ETag."""
        return self._etag


@dataclass
class StepTemplate:
    """Step template specification data.

    Corresponds to step_template.schema.json.
    """

    id: str
    version: int
    title: str
    station_id: str
    objective: Dict[str, Any]
    description: str = ""
    station_version: Optional[int] = None
    io_overrides: Optional[Dict[str, Any]] = None
    routing_defaults: Optional[Dict[str, Any]] = None
    ui_defaults: Optional[Dict[str, Any]] = None
    constraints: Optional[Dict[str, Any]] = None
    parameters: Optional[Dict[str, Any]] = None
    tags: Optional[List[str]] = None
    category: Optional[str] = None
    deprecated: bool = False
    replaced_by: Optional[str] = None
    _etag: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any], etag: Optional[str] = None) -> "StepTemplate":
        """Create StepTemplate from dictionary."""
        return cls(
            id=data["id"],
            version=data["version"],
            title=data["title"],
            station_id=data["station_id"],
            objective=data["objective"],
            description=data.get("description", ""),
            station_version=data.get("station_version"),
            io_overrides=data.get("io_overrides"),
            routing_defaults=data.get("routing_defaults"),
            ui_defaults=data.get("ui_defaults"),
            constraints=data.get("constraints"),
            parameters=data.get("parameters"),
            tags=data.get("tags"),
            category=data.get("category"),
            deprecated=data.get("deprecated", False),
            replaced_by=data.get("replaced_by"),
            _etag=etag,
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        result = {
            "id": self.id,
            "version": self.version,
            "title": self.title,
            "station_id": self.station_id,
            "objective": self.objective,
        }
        if self.description:
            result["description"] = self.description
        if self.station_version:
            result["station_version"] = self.station_version
        if self.io_overrides:
            result["io_overrides"] = self.io_overrides
        if self.routing_defaults:
            result["routing_defaults"] = self.routing_defaults
        if self.ui_defaults:
            result["ui_defaults"] = self.ui_defaults
        if self.constraints:
            result["constraints"] = self.constraints
        if self.parameters:
            result["parameters"] = self.parameters
        if self.tags:
            result["tags"] = self.tags
        if self.category:
            result["category"] = self.category
        if self.deprecated:
            result["deprecated"] = self.deprecated
        if self.replaced_by:
            result["replaced_by"] = self.replaced_by
        return result

    @property
    def etag(self) -> Optional[str]:
        """Get the computed ETag."""
        return self._etag
