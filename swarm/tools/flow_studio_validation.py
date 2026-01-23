"""
flow_studio_validation.py - Integration of validation data into Flow Studio

Provides utilities to load and integrate validation data from validate_swarm.py
into Flow Studio for governance overlays and FR status displays.

This module is optional; Flow Studio gracefully degrades if validation data
is unavailable.
"""

import json
import logging
import subprocess
from functools import lru_cache

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def get_validation_data():
    """
    Load validation JSON output from validate_swarm.py, cached.

    Returns:
        dict: Validation data with schema {
            "version": "1.0.0",
            "summary": {...},
            "agents": {<agent_key>: {...}},
            "flows": {<flow_key>: {...}},
            ...
        }

    Returns None if validation data unavailable or error occurs.
    """
    try:
        result = subprocess.run(
            ["uv", "run", "swarm/tools/validate_swarm.py", "--json"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0:
            return json.loads(result.stdout)
    except subprocess.TimeoutExpired:
        logger.warning("Validation timeout - skipping governance overlay data")
    except (json.JSONDecodeError, FileNotFoundError) as e:
        logger.warning(f"Failed to load validation data: {e}")
    except Exception as e:
        logger.warning(f"Unexpected error loading validation data: {e}")

    return None


def get_agent_fr_status(validation_data, agent_key):
    """
    Extract FR (Functional Requirement) status for a specific agent.

    Args:
        validation_data: Output from get_validation_data()
        agent_key: Agent key (e.g., 'code-implementer')

    Returns:
        dict with keys: {
            "checks": {<fr_id>: {"status": "pass|fail|warn", "message": "..."}},
            "has_issues": bool,
            "has_warnings": bool,
            "issues": [{"error_type": "...", "problem": "..."}]
        }

        Returns None if no data available for this agent.
    """
    if not validation_data or agent_key not in validation_data.get("agents", {}):
        return None

    agent = validation_data["agents"][agent_key]
    return {
        "checks": agent.get("checks", {}),
        "has_issues": agent.get("has_issues", False),
        "has_warnings": agent.get("has_warnings", False),
        "issues": agent.get("issues", []),
    }


def get_flow_fr_status(validation_data, flow_key):
    """
    Extract FR status for a specific flow.

    Args:
        validation_data: Output from get_validation_data()
        flow_key: Flow key (e.g., 'build', 'deploy')

    Returns:
        dict with keys: {
            "checks": {<fr_id>: {"status": "pass|fail|warn", "message": "..."}},
            "has_issues": bool,
            "has_warnings": bool,
            "issues": [...]
        }

        Returns None if no data available for this flow.
    """
    if not validation_data or flow_key not in validation_data.get("flows", {}):
        return None

    flow = validation_data["flows"][flow_key]
    return {
        "checks": flow.get("checks", {}),
        "has_issues": flow.get("has_issues", False),
        "has_warnings": flow.get("has_warnings", False),
        "issues": flow.get("issues", []),
    }


def get_validation_summary(validation_data):
    """
    Get overall validation summary.

    Args:
        validation_data: Output from get_validation_data()

    Returns:
        dict with keys: {
            "status": "PASS|FAIL",
            "total_checks": int,
            "passed": int,
            "failed": int,
            "warnings": int,
            "agents_with_issues": [...],
            "flows_with_issues": [...]
        }

        Returns None if validation_data is None.
    """
    if not validation_data:
        return None

    return validation_data.get("summary", {})


def format_fr_badges_html(checks):
    """
    Format FR checks as HTML badge strings for frontend rendering.

    Args:
        checks: Dict of {<fr_id>: {"status": "pass|fail|warn", "message": "..."}}

    Returns:
        HTML string ready for insertion into details panel
    """
    if not checks:
        return '<div class="fr-none">No governance data</div>'

    badges_html = []
    for fr_id, check in checks.items():
        status = check.get("status", "unknown")
        message = check.get("message", fr_id)
        title = f'title="{message}"' if message else ""
        badges_html.append(f'<span class="fr-badge fr-{status}" {title}>{fr_id}</span>')

    return f'<div class="fr-badges">{" ".join(badges_html)}</div>'


def get_agents_with_issues(validation_data):
    """
    Get list of agent keys that have governance issues.

    Args:
        validation_data: Output from get_validation_data()

    Returns:
        List of agent keys with issues, or empty list if no data
    """
    if not validation_data:
        return []

    return validation_data.get("summary", {}).get("agents_with_issues", [])


def get_flows_with_issues(validation_data):
    """
    Get list of flow keys that have governance issues.

    Args:
        validation_data: Output from get_validation_data()

    Returns:
        List of flow keys with issues, or empty list if no data
    """
    if not validation_data:
        return []

    return validation_data.get("summary", {}).get("flows_with_issues", [])


def clear_validation_cache():
    """
    Clear the cached validation data.

    Useful for testing or forcing a refresh.
    """
    get_validation_data.cache_clear()
