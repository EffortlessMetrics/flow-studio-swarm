#!/usr/bin/env python3
"""
Runbook Automation Configuration Loader

Loads and validates configuration for runbook automation from
swarm/config/runbook_automation.yaml.

This module provides:
- Configuration loading with sensible defaults
- Schema validation
- Helper functions for checking feature flags

Usage:
    from swarm.tools.runbook_config import load_config, is_enabled

    config = load_config()
    if is_enabled(config, "actions.incident_pack"):
        # Run incident pack
        pass

See: docs/designs/RUNBOOK_AUTOMATION_DESIGN.md
"""

import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional

# Add swarm package to path for library imports
_SWARM_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_SWARM_ROOT) not in sys.path:
    sys.path.insert(0, str(_SWARM_ROOT))

from swarm.utils.yaml_utils import load_yaml  # noqa: E402

# Default configuration - used when config file is missing or incomplete
DEFAULT_CONFIG: Dict[str, Any] = {
    "version": "1.0",
    "enabled": True,
    "triggers": {
        "on_selftest_failure": True,
        "on_ci_failure": False,
        "manual_dispatch": True,
        "api_dispatch": True,
    },
    "actions": {
        "incident_pack": {
            "enabled": True,
            "timeout_seconds": 300,
        },
        "suggest_remediation": {
            "enabled": True,
            "timeout_seconds": 60,
        },
        "create_issue": {
            "enabled": False,
            "labels": ["selftest", "automated", "incident"],
            "dedupe_window_hours": 24,
        },
    },
    "notifications": {
        "upload_artifacts": {
            "enabled": True,
            "retention_days": 30,
        },
        "post_pr_comment": {
            "enabled": True,
            "include_remediation_preview": True,
            "max_preview_length": 2000,
        },
        "slack_notify": {
            "enabled": False,
            "channel": "#selftest-alerts",
        },
    },
    "artifacts": {
        "max_size_mb": 100,
        "include": [
            "selftest_incident_*.tar.gz",
            "remediation_suggestions.json",
            "remediation_suggestions.txt",
            "git_recent_commits.txt",
            "git_status.txt",
            "git_recent_changes.txt",
            "environment_info.txt",
        ],
    },
    "limits": {
        "workflow_timeout_minutes": 15,
        "max_concurrent": 1,
    },
    "features": {
        "verbose_logging": False,
        "experimental": False,
        "dry_run": False,
    },
}


def _deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    """Deep merge two dictionaries, with override taking precedence."""
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def _find_config_path() -> Path:
    """Find the runbook automation config file.

    Searches in order:
    1. RUNBOOK_CONFIG_PATH environment variable
    2. swarm/config/runbook_automation.yaml (relative to repo root)
    3. Current directory
    """
    # Check environment variable first
    env_path = os.environ.get("RUNBOOK_CONFIG_PATH")
    if env_path:
        return Path(env_path)

    # Try to find repo root
    current = Path.cwd()
    while current != current.parent:
        config_path = current / "swarm" / "config" / "runbook_automation.yaml"
        if config_path.exists():
            return config_path
        current = current.parent

    # Fall back to relative path
    return Path("swarm/config/runbook_automation.yaml")


def load_config(config_path: Optional[Path] = None) -> Dict[str, Any]:
    """Load runbook automation configuration.

    Args:
        config_path: Optional explicit path to config file.
                     If not provided, uses default search path.

    Returns:
        Merged configuration dictionary with defaults.
    """
    if config_path is None:
        config_path = _find_config_path()

    # Start with defaults
    config = DEFAULT_CONFIG.copy()

    # Load from file if it exists
    if config_path.exists():
        with open(config_path) as f:
            file_config = load_yaml(f)
            if file_config:
                config = _deep_merge(config, file_config)

    return config


def is_enabled(config: Dict[str, Any], path: str) -> bool:
    """Check if a feature is enabled in the config.

    Args:
        config: Configuration dictionary.
        path: Dot-separated path to the setting, e.g., "actions.incident_pack".

    Returns:
        True if enabled, False otherwise.
    """
    # First check master enabled flag
    if not config.get("enabled", True):
        return False

    # Navigate to the specified path
    parts = path.split(".")
    current = config

    for part in parts:
        if not isinstance(current, dict):
            return False
        current = current.get(part)
        if current is None:
            return False

    # If current is a dict, check for "enabled" key
    if isinstance(current, dict):
        return current.get("enabled", False)

    # If current is a bool, return it directly
    if isinstance(current, bool):
        return current

    return False


def get_setting(config: Dict[str, Any], path: str, default: Any = None) -> Any:
    """Get a setting value from the config.

    Args:
        config: Configuration dictionary.
        path: Dot-separated path to the setting.
        default: Default value if path not found.

    Returns:
        The setting value or default.
    """
    parts = path.split(".")
    current = config

    for part in parts:
        if not isinstance(current, dict):
            return default
        current = current.get(part)
        if current is None:
            return default

    return current


def validate_config(config: Dict[str, Any]) -> list[str]:
    """Validate configuration and return list of errors.

    Args:
        config: Configuration dictionary to validate.

    Returns:
        List of error messages (empty if valid).
    """
    errors = []

    # Check version
    version = config.get("version")
    if version != "1.0":
        errors.append(f"Unsupported config version: {version} (expected 1.0)")

    # Check required sections exist
    required_sections = ["triggers", "actions", "notifications", "limits"]
    for section in required_sections:
        if section not in config:
            errors.append(f"Missing required section: {section}")

    # Validate timeout values are positive
    timeout_paths = [
        ("actions.incident_pack.timeout_seconds", 300),
        ("actions.suggest_remediation.timeout_seconds", 60),
        ("limits.workflow_timeout_minutes", 15),
    ]
    for path, default in timeout_paths:
        value = get_setting(config, path, default)
        if not isinstance(value, (int, float)) or value <= 0:
            errors.append(f"Invalid timeout at {path}: must be positive number")

    # Validate retention days
    retention = get_setting(config, "notifications.upload_artifacts.retention_days", 30)
    if not isinstance(retention, int) or retention < 1 or retention > 90:
        errors.append("Invalid retention_days: must be integer between 1 and 90")

    return errors


def get_config_summary(config: Dict[str, Any]) -> str:
    """Generate a human-readable summary of the configuration.

    Args:
        config: Configuration dictionary.

    Returns:
        Multi-line summary string.
    """
    lines = [
        "Runbook Automation Configuration",
        "=" * 40,
        f"Version: {config.get('version', 'unknown')}",
        f"Enabled: {config.get('enabled', False)}",
        "",
        "Triggers:",
    ]

    triggers = config.get("triggers", {})
    for key, value in triggers.items():
        status = "enabled" if value else "disabled"
        lines.append(f"  - {key}: {status}")

    lines.append("")
    lines.append("Actions:")

    actions = config.get("actions", {})
    for key, value in actions.items():
        if isinstance(value, dict):
            status = "enabled" if value.get("enabled", False) else "disabled"
        else:
            status = "enabled" if value else "disabled"
        lines.append(f"  - {key}: {status}")

    lines.append("")
    lines.append("Notifications:")

    notifications = config.get("notifications", {})
    for key, value in notifications.items():
        if isinstance(value, dict):
            status = "enabled" if value.get("enabled", False) else "disabled"
        else:
            status = "enabled" if value else "disabled"
        lines.append(f"  - {key}: {status}")

    return "\n".join(lines)


if __name__ == "__main__":
    # When run directly, print config summary
    import sys

    config = load_config()
    errors = validate_config(config)

    if errors:
        print("Configuration errors:")
        for error in errors:
            print(f"  - {error}")
        sys.exit(1)

    print(get_config_summary(config))
