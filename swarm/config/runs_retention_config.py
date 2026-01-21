"""Runs retention configuration registry.

Provides centralized configuration for run artifact cleanup policies.
Environment variables take precedence over YAML config.

Usage:
    from swarm.config.runs_retention_config import (
        get_retention_days,
        get_max_count,
        is_retention_enabled,
        get_preserve_patterns,
        is_dry_run_enabled,
        should_quarantine_corrupt,
    )
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from swarm.utils.yaml_utils import load_yaml

_CONFIG_PATH = Path(__file__).parent / "runs_retention.yaml"
_cached_config: Optional[Dict[str, Any]] = None


def _default_config() -> Dict[str, Any]:
    """Return default configuration if file doesn't exist."""
    return {
        "version": "1.0",
        "policy": {
            "enabled": True,
            "default_retention_days": 30,
            "strict_mode": False,
        },
        "runs": {
            "max_count": 300,
            "max_total_size_mb": 2000,
            "preserve": {
                "named_runs": ["demo-health-check", "demo-run"],
                "prefixes": ["stepwise-", "baseline-"],
                "tags": ["pinned", "golden"],
            },
            "preserve_examples": True,
        },
        "flows": {},
        "features": {
            "dry_run": False,
            "log_deletions": True,
            "archive_before_delete": False,
            "quarantine_corrupt": True,
        },
    }


def _load_config() -> Dict[str, Any]:
    """Load runs_retention.yaml with caching."""
    global _cached_config
    if _cached_config is not None:
        return _cached_config

    if _CONFIG_PATH.exists():
        with open(_CONFIG_PATH, encoding="utf-8") as f:
            _cached_config = load_yaml(f) or _default_config()
    else:
        _cached_config = _default_config()

    return _cached_config


def reload_config() -> None:
    """Force reload of configuration (useful for testing)."""
    global _cached_config
    _cached_config = None
    _load_config()


def is_retention_enabled() -> bool:
    """Check if retention policy is enabled."""
    env_val = os.environ.get("SWARM_RUNS_RETENTION_ENABLED")
    if env_val is not None:
        return env_val.lower() in ("1", "true", "yes")

    config = _load_config()
    policy = config.get("policy", {})
    return policy.get("enabled", True)


def get_retention_days(flow: Optional[str] = None) -> int:
    """Get retention days for runs (or specific flow).

    Args:
        flow: Flow key (signal, plan, build, etc.)
              If None, returns default policy.

    Returns:
        Days to retain runs.
    """
    # Environment override takes precedence
    env_val = os.environ.get("SWARM_RUNS_RETENTION_DAYS")
    if env_val is not None:
        try:
            return int(env_val)
        except ValueError:
            pass

    config = _load_config()

    # Check flow-specific override
    if flow:
        flows = config.get("flows", {})
        flow_config = flows.get(flow.lower(), {})
        if "retention_days" in flow_config:
            return flow_config["retention_days"]

    # Fall back to default
    policy = config.get("policy", {})
    return policy.get("default_retention_days", 30)


def get_max_count() -> int:
    """Get maximum number of runs to keep."""
    env_val = os.environ.get("SWARM_RUNS_MAX_COUNT")
    if env_val is not None:
        try:
            return int(env_val)
        except ValueError:
            pass

    config = _load_config()
    runs = config.get("runs", {})
    return runs.get("max_count", 300)


def get_max_total_size_mb() -> int:
    """Get max total size for swarm/runs/ directory in MB."""
    config = _load_config()
    runs = config.get("runs", {})
    return runs.get("max_total_size_mb", 2000)


def get_preserve_patterns() -> Dict[str, Any]:
    """Get patterns to preserve (don't delete)."""
    config = _load_config()
    runs = config.get("runs", {})
    return runs.get("preserve", {})


def get_preserved_named_runs() -> List[str]:
    """Get list of named runs to always preserve."""
    patterns = get_preserve_patterns()
    return patterns.get("named_runs", [])


def get_preserved_prefixes() -> List[str]:
    """Get list of prefixes to always preserve."""
    patterns = get_preserve_patterns()
    return patterns.get("prefixes", [])


def get_preserved_tags() -> List[str]:
    """Get list of tags that mark runs for preservation."""
    patterns = get_preserve_patterns()
    return patterns.get("tags", [])


def should_preserve_examples() -> bool:
    """Check if example runs should be preserved."""
    config = _load_config()
    runs = config.get("runs", {})
    return runs.get("preserve_examples", True)


def is_strict_mode() -> bool:
    """Check if strict mode is enabled (fail on errors)."""
    config = _load_config()
    policy = config.get("policy", {})
    return policy.get("strict_mode", False)


def is_dry_run_enabled() -> bool:
    """Check if dry-run mode is enabled."""
    env_val = os.environ.get("SWARM_RUNS_DRY_RUN")
    if env_val is not None:
        return env_val.lower() in ("1", "true", "yes")

    config = _load_config()
    features = config.get("features", {})
    return features.get("dry_run", False)


def should_log_deletions() -> bool:
    """Check if deletions should be logged."""
    config = _load_config()
    features = config.get("features", {})
    return features.get("log_deletions", True)


def should_quarantine_corrupt() -> bool:
    """Check if corrupt runs should be quarantined instead of deleted."""
    config = _load_config()
    features = config.get("features", {})
    return features.get("quarantine_corrupt", True)
