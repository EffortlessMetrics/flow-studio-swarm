from __future__ import annotations

from typing import Any, Dict, Optional


def load_validation_data() -> Optional[Dict[str, Any]]:
    try:
        from swarm.tools.flow_studio_validation import get_validation_data
    except ImportError:
        return None

    try:
        return get_validation_data()
    except Exception:
        return None
