"""
safe_paths.py - Security utilities for path validation.

This module provides functions to validate and sanitize user inputs that will
be used in file path construction, preventing path traversal attacks.

Usage:
    from swarm.runtime.safe_paths import validate_path_component, validate_relative_path

    run_id = validate_path_component(user_input_run_id)
    base_dir = validate_relative_path(user_input_base_dir)
"""

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
    """Validate a path string is relative and safe from traversal.

    Allows forward slashes but rejects:
    - Absolute paths (starting with / or C:\\)
    - Traversal sequences (..)
    - Empty paths

    Args:
        path: The path string to validate.
        name: Name of the variable for error messages.

    Returns:
        The validated path (same as input).

    Raises:
        ValueError: If path is unsafe.
    """
    if not path:
        raise ValueError(f"{name} cannot be empty")

    # Reject absolute paths (Linux/Unix)
    if path.startswith("/"):
        raise ValueError(f"{name} must be a relative path")

    # Reject absolute paths (Windows)
    if path.startswith("\\"):
        raise ValueError(f"{name} must be a relative path")

    # Check for windows drive letters (e.g. C:)
    if len(path) > 1 and path[1] == ":":
        raise ValueError(f"{name} must be a relative path")

    # Check for traversal
    # Normalize slashes
    normalized = path.replace("\\", "/")
    parts = normalized.split("/")

    if ".." in parts:
        raise ValueError(f"{name} cannot contain traversal sequence '..'")

    return path
