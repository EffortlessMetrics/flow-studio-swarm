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


def validate_relative_path(path_str: str, name: str = "path") -> str:
    """Validate a string for use as a relative path.

    Ensures the string is not an absolute path and does not contain traversal sequences.

    Args:
        path_str: The string to validate.
        name: Name of the variable for error messages (default: "path").

    Returns:
        The validated path string (same as input).

    Raises:
        ValueError: If the path is absolute or contains a traversal sequence like '..'.
    """
    if not path_str:
        raise ValueError(f"{name} cannot be empty")

    import os
    if os.path.isabs(path_str):
        raise ValueError(f"{name} cannot be an absolute path: '{path_str}'")

    # Reject any component that is exactly '..'
    # Handling different path separators
    normalized_path = path_str.replace("\\", "/")
    parts = normalized_path.split("/")

    if ".." in parts:
        raise ValueError(f"{name} cannot contain traversal sequence '..'")

    return path_str


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
