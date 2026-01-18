from __future__ import annotations

import logging
import os
import shutil
import tempfile
from pathlib import Path


def atomic_write(
    path: Path,
    content: str,
    create_backup: bool = True,
    logger: logging.Logger | None = None,
) -> None:
    """Atomically write content to a file."""
    if logger is None:
        logger = logging.getLogger(__name__)

    # Ensure parent directory exists
    path.parent.mkdir(parents=True, exist_ok=True)

    # Create backup if requested
    if create_backup and path.exists():
        backup_path = path.with_suffix(path.suffix + ".bak")
        shutil.copy2(path, backup_path)
        logger.debug("Created backup: %s", backup_path)

    # Write to temp file in same directory (for same-filesystem rename)
    fd, tmp_path = tempfile.mkstemp(
        suffix=".tmp",
        prefix=path.stem + "_",
        dir=path.parent,
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)

        # Atomic rename
        os.replace(tmp_path, path)
        logger.debug("Atomic write complete: %s", path)

    except Exception:
        # Clean up temp file on failure
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise
