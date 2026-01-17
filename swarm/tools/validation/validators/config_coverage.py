# swarm/tools/validation/validators/config_coverage.py
"""
FR-CONF-001: Config Coverage Validation

Validates that config files in swarm/config/agents/ align with AGENTS.md registry.

Checks:
- Every domain agent in AGENTS.md has a config YAML
- Every config YAML corresponds to an agent in AGENTS.md
- Config fields (category, color, source) match registry

Note: If swarm/config/agents/ directory doesn't exist, this check is skipped.
This allows the validator to work on repos that don't use the config system.
"""

from pathlib import Path
from typing import Any, Dict

from swarm.validator import ValidationResult
from swarm.tools.validation.helpers import ROOT, AGENTS_MD
from swarm.tools.validation.constants import BUILT_IN_AGENTS


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


def validate_config_coverage(registry: Dict[str, Dict[str, Any]]) -> ValidationResult:
    """
    Validate that config files align with AGENTS.md registry.

    Checks:
    - Every domain agent in AGENTS.md has a config YAML
    - Every config YAML corresponds to an agent in AGENTS.md
    - Config fields (category, color, source) match registry

    Note: If swarm/config/agents/ directory doesn't exist, this check is skipped.
    This allows the validator to work on repos that don't use the config system.
    """
    result = ValidationResult()

    # Skip config validation if config directory doesn't exist
    config_dir = ROOT / "swarm" / "config" / "agents"
    if not config_dir.is_dir():
        return result

    configs = parse_config_files()

    # Check registry → config
    for key, meta in registry.items():
        # Skip built-in agents
        if key in BUILT_IN_AGENTS:
            continue

        # Skip non-project agents
        if meta.get("source") != "project/user":
            continue

        if key not in configs:
            location = f"swarm/AGENTS.md:line {meta.get('line', '?')}"
            problem = f"Agent '{key}' is registered but swarm/config/agents/{key}.yaml does not exist"
            fix_action = f"Create swarm/config/agents/{key}.yaml with agent metadata, or remove entry from AGENTS.md"

            result.add_error(
                "CONFIG",
                location,
                problem,
                fix_action,
                line_number=meta.get("line"),
                file_path=str(AGENTS_MD)
            )
            continue

        # Verify config fields match registry
        config = configs[key]
        registry_category = meta.get("role_family")
        config_category = config.get("category")

        if config_category != registry_category:
            location = f"swarm/config/agents/{key}.yaml"
            problem = f"config 'category' is '{config_category}' but AGENTS.md role_family is '{registry_category}'"
            fix_action = "Update 'category' in config to match role_family in AGENTS.md"

            result.add_error(
                "CONFIG",
                location,
                problem,
                fix_action,
                file_path=config.get("file_path")
            )

        registry_color = meta.get("color")
        config_color = config.get("color")

        if config_color != registry_color:
            location = f"swarm/config/agents/{key}.yaml"
            problem = f"config 'color' is '{config_color}' but AGENTS.md color is '{registry_color}'"
            fix_action = "Update 'color' in config to match AGENTS.md"

            result.add_error(
                "CONFIG",
                location,
                problem,
                fix_action,
                file_path=config.get("file_path")
            )

    # Check config → registry
    if config_dir.is_dir():
        for config_file in config_dir.glob("*.yaml"):
            key = config_file.stem
            if key not in registry:
                problem = f"config exists for '{key}' but agent is not in swarm/AGENTS.md"
                fix_action = f"Add entry for '{key}' to AGENTS.md or delete swarm/config/agents/{key}.yaml"

                result.add_error(
                    "CONFIG",
                    f"swarm/config/agents/{key}.yaml",
                    problem,
                    fix_action,
                    file_path=str(config_file)
                )

    return result
