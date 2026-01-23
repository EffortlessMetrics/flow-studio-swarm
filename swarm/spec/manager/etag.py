from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, Optional

try:
    from swarm.runtime.spec_system.canonical import canonical_json, spec_hash

    CANONICAL_AVAILABLE = True
except ImportError:
    CANONICAL_AVAILABLE = False

    def canonical_json(obj: Any, indent: int | None = None) -> str:
        if indent is not None:
            separators = (",", ": ")
        else:
            separators = (",", ":")
        return json.dumps(
            obj,
            sort_keys=True,
            separators=separators,
            ensure_ascii=False,
            indent=indent,
        )

    def spec_hash(obj: Any, length: int = 12) -> str:
        data = canonical_json(obj).encode("utf-8")
        return hashlib.sha256(data).hexdigest()[:length]


def compute_etag_bytes(content: bytes) -> str:
    """Compute SHA256 ETag from raw bytes."""
    return hashlib.sha256(content).hexdigest()


def compute_file_etag(path: Path) -> Optional[str]:
    """Compute SHA256 ETag from file content."""
    if not path.exists():
        return None
    return compute_etag_bytes(path.read_bytes())


def compute_data_etag(data: Dict[str, Any]) -> str:
    """Compute ETag from data using canonical JSON hashing."""
    return spec_hash(data, length=64)
