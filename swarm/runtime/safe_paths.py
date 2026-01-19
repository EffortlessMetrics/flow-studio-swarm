"""
safe_paths.py - Security utilities for path handling.

This module provides functions to validate path components and prevent
directory traversal attacks.
"""

import re

# Allow alphanumeric, underscore, hyphen, dot.
# Reject anything else to be safe.
# Explicitly reject '..' and '.'
SAFE_COMPONENT_PATTERN = re.compile(r"^[a-zA-Z0-9_\-\.]+$")


class PathSecurityError(ValueError):
    """Raised when a path component is invalid/unsafe."""


def validate_path_component(component: str, name: str = "path component") -> str:
    """Validate a single path component (directory/file name).

    Ensures the component:
    1. Is not empty
    2. Does not contain path separators
    3. Is not '.' or '..'
    4. Matches allowed characters (alphanumeric, _, -, .)

    Args:
        component: The string to validate.
        name: Name of the variable for error messages.

    Returns:
        The validated component string.

    Raises:
        PathSecurityError: If the component is invalid.
    """
    if not isinstance(component, str):
        raise PathSecurityError(f"{name} must be a string")

    if not component:
        raise PathSecurityError(f"{name} cannot be empty")

    if component in (".", ".."):
        raise PathSecurityError(f"{name} cannot be '.' or '..'")

    if "/" in component or "\\" in component:
        raise PathSecurityError(f"{name} cannot contain path separators")

    if not SAFE_COMPONENT_PATTERN.match(component):
        raise PathSecurityError(
            f"{name} contains invalid characters: '{component}'. Allowed: a-z, A-Z, 0-9, _, -, ."
        )

    # Double check for traversal sequences inside the component
    if ".." in component:
        raise PathSecurityError(f"{name} cannot contain '..'")

    return component
