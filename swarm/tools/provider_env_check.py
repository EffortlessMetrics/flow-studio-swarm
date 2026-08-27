#!/usr/bin/env python3
"""
provider_env_check.py - Validate provider environment variables for stepwise backends.

This selftest step reads engine configurations from runtime.yaml and checks if
required environment variables are present for each non-stub engine.

The step always PASSes (it's informational), but logs clear warnings about
missing configuration to help users understand their setup.

## Usage

Run directly:
    uv run swarm/tools/provider_env_check.py

Run via selftest:
    uv run swarm/tools/selftest.py --step provider-env-check

## Output

Prints a table showing:
- Engine name
- Provider
- Mode
- Required env vars
- Status (OK/MISSING/STUB)

Exit codes:
    0 - Always (step is informational, never blocks)
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any, Dict, List

# Add repo root to path so `swarm.config.*` resolves. This script is executed
# by path rather than as a module, so the repo root is not on sys.path and the
# preferred package import below would otherwise always fall through.
_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

# Kept for the direct-execution fallback below, which imports runtime_config
# as a top-level module.
sys.path.insert(0, str(Path(__file__).parent.parent / "config"))

try:
    from swarm.config.runtime_config import (
        get_available_engines,
        get_engine_env,
        get_engine_mode,
        get_engine_provider,
        get_engine_required_env_keys,
    )
except ImportError:
    # Fallback for direct execution
    from runtime_config import (
        get_available_engines,
        get_engine_env,
        get_engine_mode,
        get_engine_provider,
        get_engine_required_env_keys,
    )


def check_env_var(key: str, engine_env: Dict[str, str]) -> bool:
    """
    Check if an environment variable is available.

    The variable can come from:
    1. System environment
    2. Engine-specific env config (e.g., ANTHROPIC_BASE_URL for claude-glm)

    Args:
        key: Environment variable name to check
        engine_env: Engine-specific env overrides from config

    Returns:
        True if the variable is available from any source
    """
    # Check system environment first
    if os.environ.get(key):
        return True
    # Check engine-specific env config
    if key in engine_env and engine_env[key]:
        return True
    return False


def get_engine_status(engine_id: str) -> Dict[str, Any]:
    """
    Get status information for an engine.

    Returns:
        Dict with engine configuration and env var status
    """
    mode = get_engine_mode(engine_id)
    provider = get_engine_provider(engine_id)
    required_keys = get_engine_required_env_keys(engine_id)
    engine_env = get_engine_env(engine_id)

    # Check each required env var
    env_status = {}
    for key in required_keys:
        env_status[key] = check_env_var(key, engine_env)

    # Overall status
    if mode == "stub":
        overall = "STUB"
    elif all(env_status.values()) if env_status else True:
        overall = "OK"
    else:
        overall = "MISSING"

    return {
        "engine_id": engine_id,
        "mode": mode,
        "provider": provider or "(none)",
        "required_keys": required_keys,
        "env_status": env_status,
        "overall": overall,
    }


def format_table(engine_statuses: List[Dict[str, Any]]) -> str:
    """
    Format engine statuses as a readable table.

    Args:
        engine_statuses: List of status dicts from get_engine_status

    Returns:
        Formatted table string
    """
    lines = []

    # Header
    lines.append("-" * 80)
    lines.append("PROVIDER ENVIRONMENT VALIDATION")
    lines.append("-" * 80)
    lines.append("")

    # Column headers
    header = f"{'Engine':<15} {'Provider':<18} {'Mode':<8} {'Status':<10} {'Env Vars'}"
    lines.append(header)
    lines.append("-" * 80)

    # Status rows
    has_warnings = False
    for status in engine_statuses:
        engine_id = status["engine_id"]
        provider = status["provider"]
        mode = status["mode"]
        overall = status["overall"]

        # Format env vars column
        if not status["required_keys"]:
            env_col = "(none required)"
        else:
            env_parts = []
            for key, present in status["env_status"].items():
                marker = "[OK]" if present else "[MISSING]"
                env_parts.append(f"{key} {marker}")
            env_col = ", ".join(env_parts)

        # Truncate env_col if too long
        if len(env_col) > 40:
            env_col = env_col[:37] + "..."

        row = f"{engine_id:<15} {provider:<18} {mode:<8} {overall:<10} {env_col}"
        lines.append(row)

        if overall == "MISSING":
            has_warnings = True

    lines.append("-" * 80)

    # Summary
    lines.append("")
    stub_count = sum(1 for s in engine_statuses if s["overall"] == "STUB")
    ok_count = sum(1 for s in engine_statuses if s["overall"] == "OK")
    missing_count = sum(1 for s in engine_statuses if s["overall"] == "MISSING")

    lines.append(f"Summary: {ok_count} OK, {stub_count} STUB, {missing_count} MISSING")

    if has_warnings:
        lines.append("")
        lines.append("Note: Engines with MISSING env vars will fail when invoked in non-stub mode.")
        lines.append("      Set the required environment variables or switch to stub mode.")
        lines.append("")
        lines.append("To switch an engine to stub mode, set:")
        lines.append("  SWARM_<ENGINE>_STEP_ENGINE_MODE=stub")
        lines.append("Or globally:")
        lines.append("  SWARM_STEP_ENGINE_STUB=1")
    else:
        lines.append("")
        lines.append("All non-stub engines have required environment variables configured.")

    return "\n".join(lines)


def main() -> int:
    """
    Main entry point.

    Returns:
        0 always (this is an informational check)
    """
    engines = get_available_engines()

    if not engines:
        print("No engines configured in runtime.yaml")
        return 0

    # Get status for all engines
    statuses = [get_engine_status(engine_id) for engine_id in engines]

    # Print formatted table
    print(format_table(statuses))

    # Always return 0 - this is informational only
    return 0


if __name__ == "__main__":
    sys.exit(main())
