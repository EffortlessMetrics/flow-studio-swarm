from __future__ import annotations

import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)


def create_core() -> Optional[Any]:
    try:
        from swarm.flowstudio.core import FlowStudioCore
    except ImportError:
        return None

    try:
        core = FlowStudioCore()
        core.reload()
        return core
    except Exception:
        logger.exception("Failed to initialize FlowStudioCore")
        return None
