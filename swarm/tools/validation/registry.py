# swarm/tools/validation/registry.py
"""Registry and config file parsing for swarm validation."""

import sys
from pathlib import Path
from typing import Any, Dict

from swarm.tools.validation.constants import EXIT_FATAL_ERROR
from swarm.tools.validation.helpers import AGENTS_MD, ROOT


def parse_agents_registry() -> Dict[str, Dict[str, Any]]:
    """
    Parse swarm/AGENTS.md pipe table and return agent metadata.

    Returns:
        Dict mapping agent key -> metadata dict

    Raises:
        SystemExit: If AGENTS.md not found or unparseable
    """
    if not AGENTS_MD.is_file():
        print(f"ERROR: {AGENTS_MD} not found (required for validation)", file=sys.stderr)
        sys.exit(EXIT_FATAL_ERROR)

    agents: Dict[str, Dict[str, Any]] = {}
    in_table = False
    line_number = 0

    try:
        with AGENTS_MD.open(encoding="utf-8") as f:
            for line_number, line in enumerate(f, start=1):
                line = line.rstrip("\n")

                # Detect table header (new format with role_family and color)
                if line.startswith("| Key") and "Role Family" in line and "Color" in line and "Short Role" in line:
                    in_table = True
                    continue

                # Fallback: old format header (for backward compatibility during migration)
                if line.startswith("| Key") and "Category" in line and "Short Role" in line and "Role Family" not in line:
                    # Old format without color - log warning and continue
                    print(f"WARNING: {AGENTS_MD} uses old format without Role Family/Color columns", file=sys.stderr)
                    in_table = True
                    continue

                # Skip separator row
                if in_table and line.startswith("|---"):
                    continue

                # Parse table row
                if in_table:
                    if not line.strip():
                        continue
                    if not line.startswith("|"):
                        break

                    cols = [c.strip() for c in line.strip("|").split("|")]

                    # New format: Key | Flows | Role Family | Color | Source | Short Role
                    if len(cols) == 6:
                        key, flows, role_family, color, source, role = cols
                        key = key.strip()

                        if not key or key == "Key":
                            continue

                        agents[key] = {
                            "flows": flows.strip(),
                            "role_family": role_family.strip(),
                            "color": color.strip(),
                            "source": source.strip(),
                            "role": role.strip(),
                            "line": line_number
                        }
                    # Old format: Key | Flows | Category | Source | Short Role
                    elif len(cols) == 5:
                        key, flows, category, source, role = cols
                        key = key.strip()

                        if not key or key == "Key":
                            continue

                        agents[key] = {
                            "flows": flows.strip(),
                            "category": category.strip(),
                            "source": source.strip(),
                            "role": role.strip(),
                            "line": line_number
                        }
                    else:
                        continue
    except Exception as e:
        print(f"ERROR: Failed to parse {AGENTS_MD}: {e}", file=sys.stderr)
        sys.exit(EXIT_FATAL_ERROR)

    return agents


def parse_config_files() -> Dict[str, Dict[str, Any]]:
    """
    Parse all agent config YAML files (raw YAML, no frontmatter).

    Returns:
        Dict mapping agent key → config dict
    """
    config_dir = ROOT / "swarm" / "config" / "agents"
    configs: Dict[str, Dict[str, Any]] = {}

    if not config_dir.is_dir():
        return configs

    for config_file in config_dir.glob("*.yaml"):
        try:
            content = config_file.read_text(encoding="utf-8")
            # Parse raw YAML config (not frontmatter format)
            parsed = _parse_raw_yaml(content)
            key = parsed.get("key", config_file.stem)
            configs[key] = {**parsed, "file_path": str(config_file)}
        except Exception:
            # Skip unparseable configs; they'll be caught elsewhere
            pass

    return configs


def _parse_raw_yaml(content: str) -> Dict[str, Any]:
    """
    Parse raw YAML config file (simple key: value format, no frontmatter).

    Returns:
        Dict of parsed fields
    """
    result: Dict[str, Any] = {}
    for line in content.split("\n"):
        line = line.rstrip()
        if not line or line.startswith("#"):
            continue

        # Match key: value
        if ":" not in line:
            continue

        parts = line.split(":", 1)
        key = parts[0].strip()
        value = parts[1].strip()

        # Remove quotes if present
        if value.startswith('"') and value.endswith('"'):
            value = value[1:-1]
        elif value.startswith("'") and value.endswith("'"):
            value = value[1:-1]

        result[key] = value

    return result
