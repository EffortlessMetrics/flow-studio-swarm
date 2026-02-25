"""
safe_paths.py - Security utilities for path validation.

This module provides functions to validate and sanitize user inputs that will
be used in file path construction, preventing path traversal attacks.

Usage:
    from swarm.runtime.safe_paths import validate_path_component, validate_relative_path

    run_id = validate_path_component(user_input_run_id)
    flow_key = validate_path_component(user_input_flow_key)
    path = validate_relative_path(user_input_path)
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
    """Validate a relative path string.

    Ensures the path is relative (no leading slash) and contains no traversal
    sequences ('..'). Components must be safe.

    Args:
        path: The path string to validate.
        name: Name of the variable for error messages.

    Returns:
        The validated path.

    Raises:
        ValueError: If path is absolute, contains traversal, or invalid characters.
    """
    if not path:
        raise ValueError(f"{name} cannot be empty")

    if path.startswith("/"):
        raise ValueError(f"{name} must be a relative path")

    # Split by / (normalize backslashes first just in case)
    parts = path.replace("\\", "/").split("/")

    for part in parts:
        if not part or part == ".":
            continue

        if part == "..":
            raise ValueError(f"{name} cannot contain traversal sequence '..'")

        # Check against allowlist for the component
        if not VALID_COMPONENT_PATTERN.match(part):
            raise ValueError(f"{name} contains invalid characters in component '{part}'")

    return path
