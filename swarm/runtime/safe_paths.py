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

# Disallowed characters in git refs: space, control chars, ~, ^, :, ?, *, [, \
# Also can't begin with - (to avoid option parsing issues)
GIT_REF_INVALID_CHARS = re.compile(r"[\s\x00-\x1f\x7f~^:?*\[\\]")


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


def validate_git_ref_format(ref: str, name: str = "git ref") -> str:
    """Validate a string for use as a git reference (branch name, tag).

    Ensures the string is a valid git ref format and not an option flag.

    Args:
        ref: The string to validate.
        name: Name of the variable for error messages.

    Returns:
        The validated ref (same as input).

    Raises:
        ValueError: If the ref is invalid.
    """
    if not ref:
        raise ValueError(f"{name} cannot be empty")

    if ref.startswith("-"):
        raise ValueError(f"{name} cannot start with hyphen: '{ref}'")

    if ".." in ref:
        raise ValueError(f"{name} cannot contain '..': '{ref}'")

    # Check for invalid characters
    if GIT_REF_INVALID_CHARS.search(ref):
        raise ValueError(f"{name} contains invalid characters: '{ref}'")

    if "@{" in ref:
        raise ValueError(f"{name} cannot contain '@{{': '{ref}'")

    return ref
