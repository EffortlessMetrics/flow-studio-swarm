"""
safe_paths.py - Utilities for secure path handling.
"""
import re

# Strict allowlist: alphanumeric, underscore, hyphen, dot.
# No slashes, backslashes, or null bytes.
SAFE_COMPONENT_PATTERN = re.compile(r"^[a-zA-Z0-9_\-\.]+$")

def validate_path_component(component: str, name: str = "component") -> str:
    """Validate that a path component contains only safe characters.

    Prevents path traversal and injection attacks by enforcing a strict allowlist.

    Args:
        component: The string to validate (e.g., run_id, flow_key).
        name: Name of the variable for error messages.

    Returns:
        The validated component string.

    Raises:
        ValueError: If the component contains invalid characters.
    """
    if not component:
        raise ValueError(f"{name} cannot be empty")

    if not SAFE_COMPONENT_PATTERN.match(component):
        raise ValueError(f"Invalid {name}: '{component}'. Must contain only alphanumeric characters, '_', '-', or '.'.")

    if ".." in component:
        raise ValueError(f"Invalid {name}: '{component}'. Path traversal sequence '..' is not allowed.")

    return component
