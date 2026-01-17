from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional

from .paths import schema_path


def load_schema(
    schema_name: str,
    schemas_dir: Path,
    cache: Dict[str, Dict[str, Any]],
    logger: logging.Logger,
) -> Optional[Dict[str, Any]]:
    """Load a JSON schema by name."""
    if schema_name in cache:
        return cache[schema_name]

    path = schema_path(schemas_dir, schema_name)
    if not path.exists():
        logger.debug("Schema not found: %s", path)
        return None

    try:
        with open(path, "r", encoding="utf-8") as f:
            schema = json.load(f)
        cache[schema_name] = schema
        return schema
    except (json.JSONDecodeError, OSError) as e:
        logger.warning("Failed to load schema %s: %s", schema_name, e)
        return None
