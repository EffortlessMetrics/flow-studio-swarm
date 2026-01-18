"""
safe_paths.py - Security utilities for path validation.

This module provides functions to prevent path traversal vulnerabilities
by validating path components.
"""

import os

def validate_path_component(component: str, name: str = "path component") -> str:
    """
    Validates that a path component does not contain directory separators
    or parent directory references (..).

    Args:
        component: The string to validate.
        name: The name of the field for error messages.

    Returns:
        The validated component string.

    Raises:
        ValueError: If the component is invalid.
    """
    if not isinstance(component, str):
        raise ValueError(f"Invalid {name}: must be a string")

    if not component:
        # Empty string effectively acts as current directory when joined
        # which might not be intended, but is not strictly traversal.
        # However, for IDs, empty is usually invalid.
        return component

    # Check for null bytes
    if "\0" in component:
        raise ValueError(f"Invalid {name}: contains null byte")

    # Check for directory separators
    if os.path.sep in component or (os.path.altsep and os.path.altsep in component):
        raise ValueError(f"Invalid {name}: contains directory separator")

    # Check for traversal parts
    # We check if the component is exactly '.' or '..'
    if component in (".", ".."):
        raise ValueError(f"Invalid {name}: cannot be '.' or '..'")

    return component
