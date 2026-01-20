"""
safe_paths.py - Security utilities for path validation.
"""
import re

# Strict allowlist: alphanumeric, underscore, hyphen, dot
# Must not be empty, must not be just dots.
VALID_COMPONENT_PATTERN = re.compile(r"^[a-zA-Z0-9_\-\.]+$")

def validate_path_component(component: str) -> str:
    """
    Validate that a path component is safe to use in a file path.

    Prevents path traversal and injection attacks by enforcing a strict allowlist
    of characters (alphanumeric, _, -, .).

    Explicitly rejects:
    - ".." (parent directory)
    - "." (current directory)
    - Empty strings
    - Strings containing "/" or "\"

    Args:
        component: The path component to validate (e.g., run_id, flow_key).

    Returns:
        The validated component string.

    Raises:
        ValueError: If the component is invalid.
    """
    if not isinstance(component, str):
        raise ValueError("Path component must be a string")

    if not component:
        raise ValueError("Path component cannot be empty")

    if component == "." or component == "..":
        raise ValueError(f"Invalid path component: '{component}'")

    if not VALID_COMPONENT_PATTERN.match(component):
        raise ValueError(f"Invalid path component: '{component}'. Must contain only alphanumeric, _, -, .")

    return component
