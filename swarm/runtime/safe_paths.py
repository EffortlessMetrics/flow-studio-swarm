"""
safe_paths.py - Security utilities for path validation.

This module provides functions to validate and sanitize user inputs that will
be used in file path construction, preventing path traversal attacks.

Usage:
    from swarm.runtime.safe_paths import validate_path_component

    run_id = validate_path_component(user_input_run_id)
    flow_key = validate_path_component(user_input_flow_key)
"""

import os
import re
from pathlib import Path

# Allowlist: alphanumeric, underscore, hyphen, dot
# Strictly no slashes or backslashes
VALID_COMPONENT_PATTERN = re.compile(r"^[a-zA-Z0-9_\-\.]+$")


def validate_path_component(component: str, name: str = "path component") -> str:
    """Validate a string for use as a single path component.

    Ensures the string contains only safe characters and is not a traversal sequence.

    Args:
        component: The string to validate.
        name: Name of the variable for error messages (default: "path component").

    Returns:
        The validated component (same as input).

    Raises:
        ValueError: If the component contains invalid characters, is empty,
                    or is a traversal sequence like '..' or '.'.
    """
    if not component:
        raise ValueError(f"{name} cannot be empty")

    # Explicitly reject traversal sequences
    if component == ".." or component == ".":
        raise ValueError(f"{name} cannot be traversal sequence '{component}'")

    # Check against allowlist
    if not VALID_COMPONENT_PATTERN.match(component):
        raise ValueError(f"{name} contains invalid characters: '{component}'")

    return component


def validate_relative_path(path: str, name: str = "path") -> str:
    """Validate that a path is relative and safe (no traversal).

    Args:
        path: The path string to validate.
        name: Name of the variable for error messages.

    Returns:
        The validated path.

    Raises:
        ValueError: If path is absolute or attempts traversal.
    """
    if not path:
        raise ValueError(f"{name} cannot be empty")

    p = Path(path)
    if p.is_absolute():
        raise ValueError(f"{name} must be relative, not absolute")

    # Check for traversal using os.path.normpath logic
    # We want to ensure the normalized path doesn't start with ..
    normalized = os.path.normpath(path)
    if normalized.startswith("..") or "/../" in normalized.replace("\\", "/"):
        raise ValueError(f"{name} cannot traverse outside root")

    return path
