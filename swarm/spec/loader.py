"""
loader.py - Load and validate specs from YAML files.

The loader reads StationSpecs, FlowSpecs, and Fragments from the
swarm/spec/ directory hierarchy.
"""

from __future__ import annotations

import json
import logging
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Optional

import yaml

from .types import (
    FlowSpec,
    StationSpec,
    flow_spec_from_dict,
    station_spec_from_dict,
)

logger = logging.getLogger(__name__)

# Default spec directory relative to repo root
DEFAULT_SPEC_DIR = "swarm/spec"


def get_spec_root(repo_root: Optional[Path] = None) -> Path:
    """Get the spec directory root."""
    if repo_root:
        return repo_root / DEFAULT_SPEC_DIR
    # Try to find repo root
    cwd = Path.cwd()
    for parent in [cwd] + list(cwd.parents):
        if (parent / "swarm" / "spec").exists():
            return parent / "swarm" / "spec"
    return cwd / DEFAULT_SPEC_DIR


# =============================================================================
# Station Loading
# =============================================================================


def load_station(station_id: str, repo_root: Optional[Path] = None) -> StationSpec:
    """Load a station spec by ID.

    Args:
        station_id: The station identifier (e.g., "code-implementer").
        repo_root: Optional repository root path.

    Returns:
        Parsed StationSpec.

    Raises:
        FileNotFoundError: If station spec file not found.
        ValueError: If spec is invalid.
    """
    spec_root = get_spec_root(repo_root)
    station_path = spec_root / "stations" / f"{station_id}.yaml"

    if not station_path.exists():
        raise FileNotFoundError(f"Station spec not found: {station_path}")

    try:
        with open(station_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        if not data:
            raise ValueError(f"Empty station spec: {station_path}")

        return station_spec_from_dict(data)

    except yaml.YAMLError as e:
        raise ValueError(f"Invalid YAML in station spec {station_path}: {e}")


@lru_cache(maxsize=64)
def load_station_cached(station_id: str, repo_root_str: str) -> StationSpec:
    """Cached version of load_station for repeated access."""
    return load_station(station_id, Path(repo_root_str) if repo_root_str else None)


def list_stations(repo_root: Optional[Path] = None) -> List[str]:
    """List all available station IDs.

    Args:
        repo_root: Optional repository root path.

    Returns:
        List of station IDs (without .yaml extension).
    """
    spec_root = get_spec_root(repo_root)
    stations_dir = spec_root / "stations"

    if not stations_dir.exists():
        return []

    return sorted([
        p.stem for p in stations_dir.glob("*.yaml")
        if not p.name.startswith("_")
    ])


# =============================================================================
# Flow Loading
# =============================================================================


def load_flow(flow_id: str, repo_root: Optional[Path] = None) -> FlowSpec:
    """Load a flow spec by ID.

    Args:
        flow_id: The flow identifier (e.g., "3-build").
        repo_root: Optional repository root path.

    Returns:
        Parsed FlowSpec.

    Raises:
        FileNotFoundError: If flow spec file not found.
        ValueError: If spec is invalid.
    """
    spec_root = get_spec_root(repo_root)
    flow_path = spec_root / "flows" / f"{flow_id}.yaml"

    if not flow_path.exists():
        raise FileNotFoundError(f"Flow spec not found: {flow_path}")

    try:
        with open(flow_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        if not data:
            raise ValueError(f"Empty flow spec: {flow_path}")

        return flow_spec_from_dict(data)

    except yaml.YAMLError as e:
        raise ValueError(f"Invalid YAML in flow spec {flow_path}: {e}")


@lru_cache(maxsize=16)
def load_flow_cached(flow_id: str, repo_root_str: str) -> FlowSpec:
    """Cached version of load_flow for repeated access."""
    return load_flow(flow_id, Path(repo_root_str) if repo_root_str else None)


def list_flows(repo_root: Optional[Path] = None) -> List[str]:
    """List all available flow IDs.

    Args:
        repo_root: Optional repository root path.

    Returns:
        List of flow IDs (without .yaml extension).
    """
    spec_root = get_spec_root(repo_root)
    flows_dir = spec_root / "flows"

    if not flows_dir.exists():
        return []

    return sorted([
        p.stem for p in flows_dir.glob("*.yaml")
        if not p.name.startswith("_")
    ])


# =============================================================================
# Fragment Loading
# =============================================================================


def load_fragment(fragment_path: str, repo_root: Optional[Path] = None) -> str:
    """Load a prompt fragment by path.

    Args:
        fragment_path: Relative path within fragments/ (e.g., "common/invariants.md").
        repo_root: Optional repository root path.

    Returns:
        Fragment content as string.

    Raises:
        FileNotFoundError: If fragment file not found.
    """
    spec_root = get_spec_root(repo_root)
    full_path = spec_root / "fragments" / fragment_path

    if not full_path.exists():
        raise FileNotFoundError(f"Fragment not found: {full_path}")

    return full_path.read_text(encoding="utf-8")


def load_fragments(
    fragment_paths: List[str],
    repo_root: Optional[Path] = None,
    separator: str = "\n\n---\n\n",
) -> str:
    """Load and concatenate multiple fragments.

    Args:
        fragment_paths: List of relative paths within fragments/.
        repo_root: Optional repository root path.
        separator: String to insert between fragments.

    Returns:
        Concatenated content of all fragments.

    Note:
        Missing fragments are logged as warnings but do not raise errors.
        This allows graceful degradation when optional fragments are absent.
    """
    contents: List[str] = []

    for frag_path in fragment_paths:
        try:
            content = load_fragment(frag_path, repo_root)
            if content.strip():
                contents.append(content.strip())
        except FileNotFoundError:
            logger.warning("Fragment not found (skipping): %s", frag_path)

    return separator.join(contents)


@lru_cache(maxsize=64)
def load_fragment_cached(fragment_path: str, repo_root_str: str) -> str:
    """Cached version of load_fragment for repeated access."""
    return load_fragment(fragment_path, Path(repo_root_str) if repo_root_str else None)


def list_fragments(repo_root: Optional[Path] = None) -> List[str]:
    """List all available fragment paths.

    Args:
        repo_root: Optional repository root path.

    Returns:
        List of relative fragment paths.
    """
    spec_root = get_spec_root(repo_root)
    fragments_dir = spec_root / "fragments"

    if not fragments_dir.exists():
        return []

    fragments = []
    for md_file in fragments_dir.rglob("*.md"):
        rel_path = md_file.relative_to(fragments_dir)
        fragments.append(str(rel_path).replace("\\", "/"))

    return sorted(fragments)


# =============================================================================
# Validation
# =============================================================================


def validate_specs(repo_root: Optional[Path] = None) -> Dict[str, List[str]]:
    """Validate all specs in the repository.

    Checks:
    - All YAML files parse correctly
    - Required fields are present
    - Station references in flows exist
    - Fragment references exist

    Args:
        repo_root: Optional repository root path.

    Returns:
        Dict with "errors" and "warnings" lists.
    """
    errors: List[str] = []
    warnings: List[str] = []

    spec_root = get_spec_root(repo_root)

    # Load schema for validation if jsonschema is available
    try:
        import jsonschema
        schema_available = True

        station_schema_path = spec_root / "schemas" / "station.schema.json"
        flow_schema_path = spec_root / "schemas" / "flow.schema.json"

        station_schema = None
        flow_schema = None

        if station_schema_path.exists():
            with open(station_schema_path, "r", encoding="utf-8") as f:
                station_schema = json.load(f)

        if flow_schema_path.exists():
            with open(flow_schema_path, "r", encoding="utf-8") as f:
                flow_schema = json.load(f)

    except ImportError:
        schema_available = False
        station_schema = None
        flow_schema = None
        warnings.append("jsonschema not installed - skipping JSON Schema validation")

    # Validate stations
    station_ids = set()
    for station_id in list_stations(repo_root):
        try:
            station = load_station(station_id, repo_root)
            station_ids.add(station_id)

            # JSON Schema validation
            if schema_available and station_schema:
                station_path = spec_root / "stations" / f"{station_id}.yaml"
                with open(station_path, "r", encoding="utf-8") as f:
                    raw_data = yaml.safe_load(f)
                try:
                    jsonschema.validate(raw_data, station_schema)
                except jsonschema.ValidationError as ve:
                    errors.append(f"Station {station_id}: Schema validation failed - {ve.message}")

            # Check fragment references
            for frag in station.runtime_prompt.fragments:
                try:
                    load_fragment(frag, repo_root)
                except FileNotFoundError:
                    errors.append(f"Station {station_id}: Fragment not found - {frag}")

        except FileNotFoundError as e:
            errors.append(f"Station {station_id}: {e}")
        except ValueError as e:
            errors.append(f"Station {station_id}: {e}")

    # Validate flows
    for flow_id in list_flows(repo_root):
        try:
            flow = load_flow(flow_id, repo_root)

            # JSON Schema validation
            if schema_available and flow_schema:
                flow_path = spec_root / "flows" / f"{flow_id}.yaml"
                with open(flow_path, "r", encoding="utf-8") as f:
                    raw_data = yaml.safe_load(f)
                try:
                    jsonschema.validate(raw_data, flow_schema)
                except jsonschema.ValidationError as ve:
                    errors.append(f"Flow {flow_id}: Schema validation failed - {ve.message}")

            # Check station references
            for step in flow.steps:
                if step.station not in station_ids:
                    errors.append(f"Flow {flow_id}, step {step.id}: Unknown station - {step.station}")

            # Check routing consistency
            step_ids = {s.id for s in flow.steps}
            for step in flow.steps:
                if step.routing.next and step.routing.next not in step_ids:
                    errors.append(f"Flow {flow_id}, step {step.id}: Unknown next step - {step.routing.next}")
                if step.routing.loop_target and step.routing.loop_target not in step_ids:
                    errors.append(f"Flow {flow_id}, step {step.id}: Unknown loop_target - {step.routing.loop_target}")

        except FileNotFoundError as e:
            errors.append(f"Flow {flow_id}: {e}")
        except ValueError as e:
            errors.append(f"Flow {flow_id}: {e}")

    return {"errors": errors, "warnings": warnings}


# =============================================================================
# CLI Entry Point
# =============================================================================


def main():
    """CLI entry point for spec validation and listing."""
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="Spec loader CLI")
    parser.add_argument("command", choices=["lint", "list", "render"],
                        help="Command to run")
    parser.add_argument("--type", choices=["stations", "flows", "fragments"],
                        help="Type to list")
    parser.add_argument("--station", help="Station ID for render")
    parser.add_argument("--flow", help="Flow ID for render")
    parser.add_argument("--step", help="Step ID for render")

    args = parser.parse_args()

    if args.command == "lint":
        results = validate_specs()
        for warning in results["warnings"]:
            print(f"WARNING: {warning}")
        for error in results["errors"]:
            print(f"ERROR: {error}")

        if results["errors"]:
            print(f"\n{len(results['errors'])} error(s) found")
            sys.exit(1)
        else:
            print("All specs valid")
            sys.exit(0)

    elif args.command == "list":
        if args.type == "stations":
            for s in list_stations():
                print(s)
        elif args.type == "flows":
            for f in list_flows():
                print(f)
        elif args.type == "fragments":
            for f in list_fragments():
                print(f)
        else:
            print("Stations:")
            for s in list_stations():
                print(f"  {s}")
            print("\nFlows:")
            for f in list_flows():
                print(f"  {f}")
            print("\nFragments:")
            for f in list_fragments():
                print(f"  {f}")

    elif args.command == "render":
        if not args.station:
            print("--station required for render")
            sys.exit(1)
        # Render will be implemented in compiler
        print("Render not yet implemented - use spec_compiler")


if __name__ == "__main__":
    main()
