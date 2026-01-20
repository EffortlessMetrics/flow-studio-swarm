"""
safe_paths.py - Security utilities for path handling.

This module provides validation functions to prevent path traversal attacks.
"""
import re

# Allow alphanumeric, underscore, hyphen, and dot.
# Explicitly reject anything that contains '..'
_SAFE_COMPONENT_PATTERN = re.compile(r"^[a-zA-Z0-9_\-\.]+$")

def validate_path_component(component: str) -> str:
    """Validate a path component to prevent traversal attacks.

    Args:
        component: The path component to validate (e.g. run_id, flow_key).

    Returns:
        The component if valid.

    Raises:
        ValueError: If the component is invalid or contains traversal attempts.
    """
    if not component:
         raise ValueError("Path component cannot be empty")

    if ".." in component:
        raise ValueError(f"Path traversal attempt detected: {component}")

    if not _SAFE_COMPONENT_PATTERN.match(component):
        raise ValueError(f"Invalid characters in path component: {component}")

    return component
