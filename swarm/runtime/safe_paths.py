"""Path security validation utilities.

This module provides functions to validate path components to prevent path traversal
and injection attacks. It enforces a strict allowlist of characters.
"""

import re

# Strict allowlist: alphanumeric, underscore, hyphen, period.
# This prevents directory traversal (..) and other shell injection characters.
# Note: '.' is allowed, but we explicitly check for '..' in validate_path_component.
SAFE_COMPONENT_PATTERN = re.compile(r"^[a-zA-Z0-9_\-\.]+$")


def validate_path_component(component: str, name: str = "path component") -> str:
    """
    Validates that a path component contains only allowed characters.

    Args:
        component: The path component string to validate.
        name: The name of the field (for error messages).

    Returns:
        The validated component string.

    Raises:
        ValueError: If the component is empty or contains invalid characters or '..'.
    """
    if not component:
        raise ValueError(f"{name} cannot be empty")

    if ".." in component:
        raise ValueError(f"Invalid {name}: '{component}'. Path traversal ('..') is not allowed.")

    if not SAFE_COMPONENT_PATTERN.match(component):
        raise ValueError(f"Invalid {name}: '{component}'. Must contain only alphanumeric characters, '_', '-', or '.'.")

    return component
