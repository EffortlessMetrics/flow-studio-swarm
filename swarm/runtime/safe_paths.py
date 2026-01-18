"""
safe_paths.py - Security helpers for path manipulation.

This module provides functions to safely join paths and prevent path traversal
attacks. It ensures that user-provided input cannot escape the intended
directory.
"""

import os
from pathlib import Path
from typing import Union

def safe_join(base_dir: Union[str, Path], *paths: str) -> Path:
    """
    Safely join one or more path components to a base directory.

    Ensures that the resulting path is within the base directory.
    Raises ValueError if the path traverses outside the base directory.

    Args:
        base_dir: The trusted base directory.
        paths: Path components to append (e.g. from user input).

    Returns:
        The resolved absolute path.
    """
    base = Path(base_dir).resolve()
    final_path = base

    for part in paths:
        # Strip leading slashes/drive letters to prevent absolute path reset
        # e.g. Path("/a") / "/b" -> "/b", but we want "/a/b"
        clean_part = part.lstrip(os.sep)
        if os.altsep:
            clean_part = clean_part.lstrip(os.altsep)

        final_path = final_path / clean_part

    resolved_path = final_path.resolve()

    if not resolved_path.is_relative_to(base):
        raise ValueError(f"Path traversal detected: {resolved_path} is not within {base}")

    return resolved_path


def validate_filename(filename: str) -> str:
    """
    Validate that a filename is safe (no path separators).

    Args:
        filename: The filename to check.

    Returns:
        The filename if safe.

    Raises:
        ValueError: If filename contains path separators.
    """
    if os.sep in filename or (os.altsep and os.altsep in filename):
        raise ValueError(f"Invalid filename: {filename}")
    return filename
