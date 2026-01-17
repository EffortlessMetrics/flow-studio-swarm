from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional

# Canonical event kinds (the "truth" names)
CANONICAL_EVENT_KINDS = frozenset(
    {
        # Run lifecycle
        "run_created",
        "run_started",
        "run_completed",
        "run_stop_requested",
        # Step lifecycle
        "step_start",
        "step_end",
        # Tool lifecycle
        "tool_start",
        "tool_end",
        # Data events
        "file_changes",
        "route_decision",
    }
)

# Alias map: legacy_name -> canonical_name
# Entries map to canonical names; missing keys mean name is already canonical
EVENT_KIND_ALIASES: Dict[str, str] = {
    # Run aliases
    "run_start": "run_started",
    "run_end": "run_completed",
    "run_cancelled": "run_completed",  # Status indicates actual outcome
    "run_failed": "run_completed",  # Status indicates actual outcome
    # Step aliases
    "step_complete": "step_end",
    "step_error": "step_end",  # Status indicates actual outcome
}


def normalize_event_kind(kind: str) -> str:
    """Normalize an event kind to its canonical form.

    Args:
        kind: The event kind string (may be legacy alias).

    Returns:
        The canonical event kind.
    """
    return EVENT_KIND_ALIASES.get(kind, kind)


def parse_event_ts(ts_str: Any) -> Optional[datetime]:
    """Parse event timestamp string to datetime.

    Args:
        ts_str: ISO format timestamp string, datetime, or None.

    Returns:
        Parsed datetime in UTC, or None if parsing fails.
    """
    if ts_str is None:
        return None
    if isinstance(ts_str, datetime):
        return ts_str
    if not isinstance(ts_str, str):
        return None

    try:
        # Handle ISO format with or without timezone
        if ts_str.endswith("Z"):
            ts_str = ts_str[:-1] + "+00:00"
        dt = datetime.fromisoformat(ts_str)
        # Ensure UTC timezone
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except (ValueError, TypeError):
        return None
