"""
safe_paths.py - Security utilities for path validation.

This module provides functions to validate and sanitize user inputs that will
be used in file path construction, preventing path traversal attacks.

Usage:
    from swarm.runtime.safe_paths import validate_path_component

    run_id = validate_path_component(user_input_run_id)
    flow_key = validate_path_component(user_input_flow_key)
"""

import re

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
    """Validate that a path is relative and safe from traversal.

    Ensures the path does not start with / (or \\ on Windows) and does not
    contain '..' segments.

    Args:
        path: The path string to validate.
        name: Name of the variable for error messages (default: "path").

    Returns:
        The validated path (same as input).

    Raises:
        ValueError: If the path is absolute or contains traversal sequences.
    """
    if not path:
        raise ValueError(f"{name} cannot be empty")

    # Check for absolute path
    # On Windows, absolute paths can start with drive letter (C:) or \
    # On Linux/Mac, start with /
    # We check for generic absolute indicators
    if path.startswith("/") or path.startswith("\\"):
        raise ValueError(f"{name} must be a relative path")

    # Check for drive letter (e.g., C:)
    if len(path) > 1 and path[1] == ":":
        raise ValueError(f"{name} cannot contain drive letter")

    # Check for traversal sequences
    # We split by both forward and backward slashes
    parts = re.split(r"[/\\]", path)
    for part in parts:
        if part == "..":
            raise ValueError(f"{name} cannot contain path traversal '..'")

    return path
