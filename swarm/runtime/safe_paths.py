"""
safe_paths.py - Utilities for preventing path traversal vulnerabilities.

This module provides validation functions to ensure that user-supplied strings
can be safely used as file path components (e.g. run IDs, flow keys, step IDs).
"""

from __future__ import annotations

import os
import re

# Allow alphanumeric, hyphen, underscore, dot.
# This prevents path traversal (.. is caught by dot check logic or implicit strictness if we are careful)
# and command injection (;, &, | etc are not allowed).
SAFE_PATTERN = re.compile(r"^[a-zA-Z0-9_\-\.]+$")

def validate_path_component(component: str) -> str:
    """Validates that a path component is safe to use in a file path.

    Prevents path traversal by ensuring the component contains no separators
    or directory traversal tokens. Also enforces strict character set
    (alphanumeric, -, _, .) to prevent command injection and other issues.

    Args:
        component: The string to validate (e.g. run_id, flow_key).

    Returns:
        The validated component string.

    Raises:
        ValueError: If the component contains invalid characters or patterns.
    """
    if not component:
        raise ValueError("Path component cannot be empty")

    if not SAFE_PATTERN.match(component):
        raise ValueError(f"Invalid path component: '{component}' (contains invalid characters)")

    # Even with regex, double check for traversal just in case regex is permissive for dots
    if ".." in component:
         raise ValueError(f"Invalid path component: '{component}' (contains traversal)")

    if component == "." or component == "..":
        raise ValueError(f"Invalid path component: '{component}'")

    return component
