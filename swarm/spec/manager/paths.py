from __future__ import annotations

from pathlib import Path
from typing import Optional


DEFAULT_SPEC_DIR = "swarm/spec"  # Legacy YAML location
DEFAULT_SPECS_DIR = "swarm/specs"  # New JSON location (runtime truth)
DEFAULT_FLOWS_SUBDIR = "flows"
DEFAULT_STATIONS_SUBDIR = "stations"
DEFAULT_TEMPLATES_SUBDIR = "templates"
DEFAULT_SCHEMAS_SUBDIR = "schemas"


def resolve_repo_root(repo_root: Optional[Path]) -> Path:
    """Resolve repository root path."""
    if repo_root:
        return Path(repo_root).resolve()

    # Try to find repo root from current directory
    cwd = Path.cwd()
    for parent in [cwd] + list(cwd.parents):
        if (parent / "swarm" / "spec").exists():
            return parent
        if (parent / ".git").exists():
            return parent

    # Fall back to current directory
    return cwd


def flows_dir(specs_dir: Path) -> Path:
    """Get flows directory (new JSON store)."""
    return specs_dir / DEFAULT_FLOWS_SUBDIR


def stations_dir(specs_dir: Path) -> Path:
    """Get stations directory (new JSON store)."""
    return specs_dir / DEFAULT_STATIONS_SUBDIR


def templates_dir(specs_dir: Path) -> Path:
    """Get templates directory (new JSON store)."""
    return specs_dir / DEFAULT_TEMPLATES_SUBDIR


def schemas_dir(specs_dir: Path, spec_dir: Path) -> Path:
    """Get schemas directory (new JSON store, fallback to legacy)."""
    new_schemas = specs_dir / DEFAULT_SCHEMAS_SUBDIR
    if new_schemas.exists():
        return new_schemas
    return spec_dir / DEFAULT_SCHEMAS_SUBDIR


def flow_path(specs_dir: Path, flow_id: str) -> Path:
    """Get path to flow JSON file."""
    return flows_dir(specs_dir) / f"{flow_id}.json"


def flow_ui_path(specs_dir: Path, flow_id: str) -> Path:
    """Get path to flow UI overlay file."""
    return flows_dir(specs_dir) / f"{flow_id}.ui.json"


def flow_graph_path(specs_dir: Path, spec_dir: Path, flow_id: str) -> Path:
    """Get path to flow graph file (legacy path structure)."""
    new_path = flow_path(specs_dir, flow_id)
    if new_path.exists():
        return new_path
    return spec_dir / DEFAULT_FLOWS_SUBDIR / flow_id / "graph.json"


def station_path(specs_dir: Path, station_id: str) -> Path:
    """Get path to station JSON file."""
    return stations_dir(specs_dir) / f"{station_id}.json"


def template_path(specs_dir: Path, template_id: str) -> Path:
    """Get path to template file."""
    return templates_dir(specs_dir) / f"{template_id}.json"


def schema_path(schemas_dir_path: Path, schema_name: str) -> Path:
    """Get path to schema file."""
    if not schema_name.endswith(".schema.json"):
        schema_name = f"{schema_name}.schema.json"
    return schemas_dir_path / schema_name
