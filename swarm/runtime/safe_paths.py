"""
safe_paths.py - Security utilities for path validation.

This module provides functions to validate path components to prevent
path traversal and other file system attacks.
"""

import re
from typing import Optional

# Strict alphanumeric allowlist plus _, -, .
# This prevents directory traversal (..) and special characters
SAFE_COMPONENT_PATTERN = re.compile(r"^[a-zA-Z0-9_\-\.]+$")

def validate_path_component(component: str, name: str = "path component") -> str:
    """Validate a path component against a strict allowlist.

    Args:
        component: The string to validate (e.g., run_id, flow_key, step_id).
        name: The name of the field for error messages.

    Returns:
        The validated component string.

    Raises:
        ValueError: If the component contains invalid characters or is empty.
    """
    if not component:
        raise ValueError(f"{name} cannot be empty")

    if component == "." or component == "..":
        raise ValueError(f"{name} cannot be '.' or '..'")

    if not SAFE_COMPONENT_PATTERN.match(component):
        raise ValueError(
            f"{name} contains invalid characters. "
            "Only alphanumeric characters, underscores, hyphens, and dots are allowed."
        )

    return component
