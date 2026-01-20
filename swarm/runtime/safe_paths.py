"""
safe_paths.py - Utilities for validating file path components.

This module provides functions to validate user-supplied path components
(like run IDs, flow keys, step IDs) to prevent directory traversal
and injection attacks.
"""

import re

# Allow alphanumeric, underscore, hyphen, dot.
# This pattern PERMITS multiple dots (like 'v1.2.3'), but we must
# separately ensure no directory traversal ('..') occurs.
SAFE_COMPONENT_PATTERN = re.compile(r"^[a-zA-Z0-9_\-\.]+$")


def validate_path_component(component: str, name: str = "path component") -> str:
    """
    Validates that a path component is safe to use in a file path.
    Allowed characters: a-z, A-Z, 0-9, _, -, .
    Specifically rejects '..' and empty strings.

    Args:
        component: The string to validate.
        name: The name of the field for error messages.

    Returns:
        The validated component (unchanged).

    Raises:
        ValueError: If the component is invalid.
    """
    if not component:
        raise ValueError(f"{name} cannot be empty")

    if not isinstance(component, str):
        raise ValueError(f"{name} must be a string")

    # Reject directory traversal attempts explicitly
    if ".." in component:
        raise ValueError(f"Invalid {name}: '{component}'. Traversal sequences ('..') are not allowed.")

    # Check against allowed characters
    if not SAFE_COMPONENT_PATTERN.match(component):
        raise ValueError(f"Invalid {name}: '{component}'. Must contain only alphanumeric characters, '_', '-', or '.'.")

    return component
